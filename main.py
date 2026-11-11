import os
import httpx
import asyncio
import uuid
import random
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

os.makedirs("/tmp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/tmp/static"), name="static")

@app.get("/")
async def root():
    return {"message": "소윤의 사주타로 서버 정상 작동 중"}

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    user_request = body.get("userRequest", {})
    callback_url = user_request.get("callbackUrl")
    base_url = str(request.base_url).rstrip('/')
    
    # 1차 즉시 응답
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {"outputs": [{"simpleText": {"text": "🌌 소윤의 사주타로에 오신 것을 환영합니다..."}}]}
    }
    
    if callback_url:
        background_tasks.add_task(process_main_menu, callback_url, base_url)
        
    return JSONResponse(content=immediate_response)

async def process_main_menu(callback_url: str, base_url: str):
    try:
        # 💡 1. 예쁜 메인 메뉴 이미지 생성
        img = Image.new('RGB', (800, 400), color=(10, 10, 25)) # 어두운 우주 배경
        draw = ImageDraw.Draw(img)
        
        # 별빛 배경 뿌리기
        for _ in range(80):
            x, y = random.randint(0, 800), random.randint(0, 400)
            r = random.randint(1, 3)
            draw.ellipse([x, y, x+r, y+r], fill=(255, 255, 255))
            
        try:
            font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 50)
            font_sub = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
        except:
            font_title = font_sub = None
            
        # 타이틀 및 안내 문구
        draw.text((180, 120), "🌌 소윤의 사주타로", font=font_title, fill=(255, 215, 0))
        draw.text((230, 220), "당신의 우주를 분석해드립니다", font=font_sub, fill=(200, 200, 200))

        # 이미지 저장 및 URL 생성
        filename = f"main_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/tmp/static/{filename}"
        img.save(filepath)
        image_url = f"{base_url}/static/{filename}"

        # 💡 2. 카카오톡 메인 메뉴 카드 전송 (버튼 3개)
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "basicCard": {
                            "title": "환영합니다!",
                            "description": "원하시는 서비스를 아래 버튼에서 선택해주세요.",
                            "thumbnail": {
                                "imageUrl": image_url,
                                "fixedRatio": True,
                                "width": 800,
                                "height": 400
                            },
                            "buttons": [
                                # ⚠️ 아래 blockId에 오픈빌더에서 만드신 실제 블록 ID를 넣어주세요!
                                {"action": "block", "label": "🔮 사주 보기", "blockId": "사주블록ID입력"},
                                {"action": "block", "label": "🃏 타로 보기", "blockId": "타로블록ID입력"},
                                {"action": "block", "label": "💑 궁합 보기", "blockId": "궁합블록ID입력"}
                            ]
                        }
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client_http:
            await client_http.post(callback_url, json=payload)
            print("메인 메뉴 전송 완료!")
            
    except Exception as e:
        print(f"메인 메뉴 에러: {e}")
