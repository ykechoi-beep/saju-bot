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
    
    # 💡 날짜와 시간을 모두 가져옵니다.
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
        # 💡 시간도 함께 넘겨줍니다.
        background_tasks.add_task(process_saju, callback_url, base_url, birth_date, birth_time)
        
    return JSONResponse(content=immediate_response)

async def process_saju(callback_url: str, base_url: str, birth_date: str, birth_time: str):
    try:
        # 1. KASI API 호출을 위해 날짜 쪼개기
        try:
            numbers = re.findall(r'\d+', birth_date)
            if len(numbers) >= 3:
                year = numbers[0]
                month = numbers[1].zfill(2)
                day = numbers[2].zfill(2)
            else:
                year, month, day = "1990", "01", "01"
        except:
            year, month, day = "1990", "01", "01"

        api_key = os.getenv("KASI_API_KEY")
        url = "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
        params = {
            'serviceKey': api_key, 
            'solYear': year, 
            'solMonth': month, 
            'solDay': day, 
            '_type': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        item = data['response']['body']['items']['item']
        
        lun_date = f"{item.get('lunYear')}년 {item.get('lunMonth')}월 {item.get('lunDay')}일"
        iljin_raw = item.get('lunIljin', '알수없음')
        iljin = iljin_raw.split('(')[0] if iljin_raw else '알수없음'

        # 2. 파이썬으로 RPG 대시보드 이미지 그리기
        img = Image.new('RGB', (800, 450), color=(30, 30, 45)) # 높이를 450으로 살짝 늘렸습니다.
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
            font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
        except Exception as font_e:
            print(f"폰트 로드 실패: {font_e}")
            font_title = font_text = None 

        draw.text((50, 40), "천문학 사주 분석 결과", font=font_title, fill=(255, 215, 0)) 
        draw.text((50, 120), f"양력 입력: {year}년 {month}월 {day}일", font=font_text, fill=(200, 200, 200))
        # 💡 입력받은 시간을 이미지에 추가합니다.
        draw.text((50, 170), f"출생 시간: {birth_time}", font=font_text, fill=(200, 200, 200)) 
        draw.text((50, 220), f"음력 변환: {lun_date}", font=font_text, fill=(255, 255, 255))
        draw.text((50, 270), f"일진(기운): {iljin}", font=font_text, fill=(255, 255, 255))
        
        draw.rectangle([50, 350, 750, 380], fill=(100, 100, 100))
        draw.rectangle([50, 350, 550, 380], fill=(0, 255, 127))

        # 3. 이미지 저장 및 URL 만들기
        filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/tmp/static/{filename}"
        img.save(filepath)
        image_url = f"{base_url}/static/{filename}"

        # 4. 카카오톡으로 이미지 카드 전송
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": f"{year}년 {month}월 {day}일 천문학 사주",
                            "description": f"출생 시간: {birth_time}",
                            "thumbnail": {
                                "imageUrl": image_url,
                                "fixedRatio": True,
                                "width": 800,
                                "height": 450
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
