import os
import httpx
import asyncio
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
import uuid

app = FastAPI()

# 이미지를 저장할 static 폴더 생성 및 설정
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "소윤의 사주타로 서버가 정상 작동 중입니다!"}

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    user_request = body.get("userRequest", {})
    callback_url = user_request.get("callbackUrl")
    
    # 현재 서버의 기본 주소를 추출 (이미지 URL을 만들기 위함)
    base_url = str(request.base_url).rstrip('/')
    
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {
            "outputs": [{"simpleText": {"text": "🕯️ 우주의 기운을 모아 분석하고 있습니다..."}}]
        }
    }
    
    if callback_url:
        background_tasks.add_task(process_saju, callback_url, base_url)
        
    return JSONResponse(content=immediate_response)

async def process_saju(callback_url: str, base_url: str):
    try:
        # 1. KASI API 호출
        api_key = os.getenv("KASI_API_KEY")
        url = "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
        params = {'serviceKey': api_key, 'solYear': '1990', 'solMonth': '01', 'solDay': '01', '_type': 'json'}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        item = data['response']['body']['items']['item']
        lun_date = f"{item.get('lunYear')}년 {item.get('lunMonth')}월 {item.get('lunDay')}일"
        iljin = item.get('lunIljin', '알수없음')

        # 2. 파이썬으로 RPG 대시보드 이미지 그리기 (Pillow 사용)
        img = Image.new('RGB', (800, 400), color=(30, 30, 45)) # 어두운 남색 배경
        draw = ImageDraw.Draw(img)
        
        # 폰트 불러오기 (업로드하신 파일 이름과 정확히 일치해야 합니다)
        try:
            font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
            font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
        except Exception as font_e:
            print(f"폰트 로드 실패: {font_e}")
            font_title = font_text = None # 폰트가 없으면 기본 폰트 사용 (한글 깨짐)

        # 글씨 쓰기
        draw.text((50, 50), "🌌 명리학 사주 분석 결과", font=font_title, fill=(255, 215, 0)) # 노란색 제목
        draw.text((50, 150), f"🌙 음력 날짜: {lun_date}", font=font_text, fill=(255, 255, 255))
        draw.text((50, 220), f"✨ 일진(기운): {iljin}", font=font_text, fill=(255, 255, 255))
        
        # 게이지 바 그리기 (예시)
        draw.rectangle([50, 300, 750, 330], fill=(100, 100, 100)) # 배경 바
        draw.rectangle([50, 300, 550, 330], fill=(0, 255, 127)) # 채워진 바 (재물운 예시)

        # 3. 이미지 저장 및 URL 만들기
        filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
        filepath = f"static/{filename}"
        img.save(filepath)
        image_url = f"{base_url}/static/{filename}"

        # 4. 카카오톡으로 이미지 카드(BasicCard) 전송
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": "당신의 명리학 사주",
                            "description": "KASI 데이터를 바탕으로 분석한 결과입니다.",
                            "thumbnail": {
                                "imageUrl": image_url,
                                "fixedRatio": True,
                                "width": 800,
                                "height": 400
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
