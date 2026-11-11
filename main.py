import os
import httpx
import asyncio
import requests
import re
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
import uuid
from sajupy import calculate_saju

app = FastAPI()

os.makedirs("/tmp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/tmp/static"), name="static")

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
            "outputs": [{"simpleText": {"text": f"🕯️ {birth_date} {birth_time}의 우주의 기운을 모아 분석하고 있습니다..."}}]
        }
    }
    
    if callback_url:
        background_tasks.add_task(process_saju, callback_url, base_url, birth_date, birth_time)
        
    return JSONResponse(content=immediate_response)

async def process_saju(callback_url: str, base_url: str, birth_date: str, birth_time: str):
    try:
        # 1. 날짜 추출
        numbers = re.findall(r'\d+', birth_date)
        if len(numbers) >= 3:
            year = int(numbers[0])
            month = int(numbers[1])
            day = int(numbers[2])
        else:
            year, month, day = 1990, 1, 1

        # 2. 시간 추출 및 24시간제 변환
        hour_24 = 12
        minute = 0
        is_pm = "오후" in birth_time
        is_am = "오전" in birth_time
        time_numbers = re.findall(r'\d+', birth_time)
        if time_numbers:
            raw_hour = int(time_numbers[0])
            if len(time_numbers) > 1:
                minute = int(time_numbers[1])
            if is_pm and raw_hour < 12:
                hour_24 = raw_hour + 12
            elif is_am and raw_hour == 12:
                hour_24 = 0
            else:
                hour_24 = raw_hour

        # 3. KASI API 호출 (음력 변환)
        api_key = os.getenv("KASI_API_KEY")
        url = "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
        params = {
            'serviceKey': api_key, 
            'solYear': str(year), 
            'solMonth': str(month).zfill(2), 
            'solDay': str(day).zfill(2), 
            '_type': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        item = data['response']['body']['items']['item']
        
        lun_date = f"{item.get('lunYear')}년 {item.get('lunMonth')}월 {item.get('lunDay')}일"
        iljin_raw = item.get('lunIljin', '알수없음')
        iljin = iljin_raw.split('(')[0] if iljin_raw else '알수없음'

        # 4. sajupy를 이용한 사주팔자 계산
        saju_text = "계산 불가"
        try:
            saju_result = calculate_saju(year, month, day, hour_24, minute)
            year_pillar = saju_result.get('year_pillar', '?')
            month_pillar = saju_result.get('month_pillar', '?')
            day_pillar = saju_result.get('day_pillar', '?')
            hour_pillar = saju_result.get('hour_pillar', '?')
            
            # 💡 [핵심] 한자를 한글 발음으로 변환하는 사전 (이미지 깨짐 방지)
            hanja_to_hangul = {
                "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
                "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"
            }
            
            # 계산된 8글자에서 한자를 찾아 한글로 치환
            def convert_to_korean(text):
                for hanja, hangul in hanja_to_hangul.items():
                    text = text.replace(hanja, hangul)
                return text
                
            year_pillar_kr = convert_to_korean(year_pillar)
            month_pillar_kr = convert_to_korean(month_pillar)
            day_pillar_kr = convert_to_korean(day_pillar)
            hour_pillar_kr = convert_to_korean(hour_pillar)
            
            saju_text = f"{year_pillar_kr} {month_pillar_kr} {day_pillar_kr} {hour_pillar_kr}"
            
        except Exception as e:
            print(f"사주 계산 실패: {e}")

        # 5. 파이썬으로 RPG 대시보드 이미지 그리기
        img = Image.new('RGB', (800, 550), color=(30, 30, 45)) 
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
            font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
            font_saju = ImageFont.truetype("NanumGothic-Regular.ttf", 35)
        except Exception as font_e:
            print(f"폰트 로드 실패: {font_e}")
            font_title = font_text = font_saju = None 

        # 이미지에 글씨 쓰기 (이제 한글로 변환된 사주팔자가 잘 나옵니다)
        draw.text((50, 40), "천문학 사주 분석 결과", font=font_title, fill=(255, 215, 0)) 
        draw.text((50, 120), f"양력 입력: {year}년 {month}월 {day}일", font=font_text, fill=(200, 200, 200))
        draw.text((50, 170), f"출생 시간: {birth_time}", font=font_text, fill=(200, 200, 200)) 
        draw.text((50, 220), f"음력 변환: {lun_date}", font=font_text, fill=(255, 255, 255))
        
        draw.text((50, 290), f"사주팔자: {saju_text}", font=font_saju, fill=(0, 255, 255)) 
        draw.text((50, 360), f"일진(기운): {iljin}", font=font_text, fill=(255, 255, 255))
        
        draw.rectangle([50, 450, 750, 480], fill=(100, 100, 100))
        draw.rectangle([50, 450, 550, 480], fill=(0, 255, 127))

        # 6. 이미지 저장 및 URL 만들기
        filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/tmp/static/{filename}"
        img.save(filepath)
        image_url = f"{base_url}/static/{filename}"

        # 7. 카카오톡으로 이미지 카드 전송
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": f"{year}년 {month}월 {day}일 천문학 사주",
                            "description": f"사주팔자: {saju_text}", # 카드 설명도 한글로 변경
                            "thumbnail": {
                                "imageUrl": image_url,
                                "fixedRatio": True,
                                "width": 800,
                                "height": 550
                            },
                            "buttons": [
                                {"action": "message", "label": "다시 분석하기", "messageText": "사주 봐줘"}
                            ]
                        }
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=payload)
            print("이미지 전송 완료!")
            
    except Exception as e:
        print(f"에러 발생: {e}")
