import os
import httpx
import asyncio
import requests
import re
import random
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
import uuid
from sajupy import calculate_saju
from google import genai  # 💡 최신 구글 라이브러리로 변경

app = FastAPI()

os.makedirs("/tmp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/tmp/static"), name="static")

# 💡 최신 SDK 클라이언트 초기화
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 💡 최신 SDK에 맞춘 AI 호출 함수 (최신 모델명 사용)
def get_ai_comment_with_fallback(prompt: str) -> str:
    # 최신 SDK에서 지원하는 모델 목록 (최신순)
    model_candidates = [
        'gemini-2.5-flash',       # ⭐ 최우선 모델
        'gemini-2.0-flash',       # 1차 백업
        'gemini-1.5-flash'        # 2차 백업
    ]
    
    for model_name in model_candidates:
        try:
            print(f"AI 모델 시도 중: {model_name}")
            # 최신 SDK 호출 방식
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response.text:
                print(f"✅ AI 모델 성공: {model_name}")
                return response.text
        except Exception as e:
            print(f"❌ {model_name} 실패: {e}")
            continue
            
    return "현재 AI 모델을 불러올 수 없습니다. 잠시 후 다시 시도해 주세요."

@app.get("/")
async def root():
    return {"message": "소윤의 천문사주 서버가 정상 작동 중입니다!"}

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    user_request = body.get("userRequest", {})
    callback_url = user_request.get("callbackUrl")
    
    action = body.get("action", {})
    params = action.get("params", {})
    
    birth_date = params.get("birthDate", "1990-01-01") 
    birth_time = params.get("birthTime", "시간 모름") 
    
    base_url = str(request.base_url).rstrip('/')
    
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {
            "outputs": [{"simpleText": {"text": f"🕯️ {birth_date} {birth_time}의 천체 궤적과 AI 사주를 분석하고 있습니다. (약 5초 소요)"}}]
        }
    }
    
    if callback_url:
        background_tasks.add_task(process_saju, callback_url, base_url, birth_date, birth_time)
        
    return JSONResponse(content=immediate_response)

async def process_saju(callback_url: str, base_url: str, birth_date: str, birth_time: str):
    try:
        # 1. 날짜 및 시간 추출
        numbers = re.findall(r'\d+', birth_date)
        if len(numbers) >= 3:
            year, month, day = int(numbers[0]), int(numbers[1]), int(numbers[2])
        else:
            year, month, day = 1990, 1, 1

        hour_24, minute = 12, 0
        is_pm = "오후" in birth_time
        is_am = "오전" in birth_time
        time_numbers = re.findall(r'\d+', birth_time)
        if time_numbers:
            raw_hour = int(time_numbers[0])
            if len(time_numbers) > 1: minute = int(time_numbers[1])
            if is_pm and raw_hour < 12: hour_24 = raw_hour + 12
            elif is_am and raw_hour == 12: hour_24 = 0
            else: hour_24 = raw_hour

        # 2. KASI API (음력 변환)
        api_key = os.getenv("KASI_API_KEY")
        url = "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
        params = {'serviceKey': api_key, 'solYear': str(year), 'solMonth': str(month).zfill(2), 'solDay': str(day).zfill(2), '_type': 'json'}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        item = data['response']['body']['items']['item']
        lun_date = f"{item.get('lunYear')}년 {item.get('lunMonth')}월 {item.get('lunDay')}일"

        # 3. sajupy 사주팔자 계산 및 한글화
        saju_result = calculate_saju(year, month, day, hour_24, minute)
        hanja_to_hangul = {
            "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
            "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"
        }
        def conv_kr(t): return "".join([hanja_to_hangul.get(char, char) for char in t])
        
        saju_text = f"{conv_kr(saju_result['year_pillar'])} {conv_kr(saju_result['month_pillar'])} {conv_kr(saju_result['day_pillar'])} {conv_kr(saju_result['hour_pillar'])}"

        # 4. AI 사주 풀이
        ai_comment = "사주 분석 결과를 불러오지 못했습니다."
        try:
            prompt = f"너는 친절하고 신비로운 분위기의 사주 상담가야. 다음 사주팔자를 바탕으로 사용자에게 3문장 이내로 따뜻하고 긍정적인 조언을 해줘. (사주팔자: {saju_text})"
            ai_comment = get_ai_comment_with_fallback(prompt)
        except Exception as e:
            print(f"AI 풀이 최종 에러: {e}")
            ai_comment = f"⚠️ AI 에러 발생: {str(e)}"

        # 5. UI 고도화: 별빛 배경 및 RPG 게이지 3개 그리기
        img = Image.new('RGB', (800, 600), color=(15, 15, 30))
        draw = ImageDraw.Draw(img)
        
        for _ in range(50):
            x, y = random.randint(0, 800), random.randint(0, 600)
            r = random.randint(1, 2)
            draw.ellipse([x, y, x+r, y+r], fill=(255, 255, 255))

        try:
            font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
            font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 28)
            font_saju = ImageFont.truetype("NanumGothic-Regular.ttf", 35)
        except:
            font_title = font_text = font_saju = None 

        draw.text((50, 40), "🌌 천문학 사주 분석 결과", font=font_title, fill=(255, 215, 0)) 
        draw.text((50, 100), f"양력: {year}년 {month}월 {day}일 {birth_time}", font=font_text, fill=(200, 200, 200))
        draw.text((50, 140), f"음력: {lun_date}", font=font_text, fill=(200, 200, 200))
        draw.text((50, 200), f"사주: {saju_text}", font=font_saju, fill=(0, 255, 255)) 
        
        draw.text((50, 280), "재물운", font=font_text, fill=(255, 255, 255))
        draw.rectangle([150, 285, 700, 305], fill=(50, 50, 50))
        draw.rectangle([150, 285, 150 + random.randint(200, 550), 305], fill=(255, 215, 0))

        draw.text((50, 340), "애정운", font=font_text, fill=(255, 255, 255))
        draw.rectangle([150, 345, 700, 365], fill=(50, 50, 50))
        draw.rectangle([150, 345, 150 + random.randint(200, 550), 365], fill=(255, 105, 180))

        draw.text((50, 400), "건강운", font=font_text, fill=(255, 255, 255))
        draw.rectangle([150, 405, 700, 425], fill=(50, 50, 50))
        draw.rectangle([150, 405, 150 + random.randint(200, 550), 425], fill=(0, 255, 127))

        # 6. 이미지 저장 및 URL 생성
        filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/tmp/static/{filename}"
        img.save(filepath)
        image_url = f"{base_url}/static/{filename}"

        # 7. 카카오톡 카드 전송
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": f"{year}년 {month}월 {day}일 사주",
                            "description": "천체 궤적과 사주팔자를 분석한 결과입니다.",
                            "thumbnail": {"imageUrl": image_url, "fixedRatio": True, "width": 800, "height": 600}
                        }
                    },
                    {
                        "textCard": {
                            "title": "🔮 AI 사주 마스터의 조언",
                            "description": ai_comment,
                            "buttons": [{"action": "message", "label": "다시 분석하기", "messageText": "사주 봐줘"}]
                        }
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client_http:
            res = await client_http.post(callback_url, json=payload)
            print(f"카카오 응답 코드: {res.status_code}")
            if res.status_code == 200:
                print("이미지 및 AI 풀이 전송 완료!")
            else:
                print(f"전송 실패: {res.text}")
            
    except Exception as e:
        print(f"에러 발생: {e}")
