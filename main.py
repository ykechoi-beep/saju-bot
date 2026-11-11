import os
import httpx
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "서버 정상 작동 중"}

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    
    # 💡 디버깅: 카카오가 보낸 모든 데이터를 로그에 강제로 출력합니다.
    print(f"========== 카카오가 보낸 데이터 ==========", flush=True)
    print(body, flush=True)
    print(f"========================================", flush=True)

    user_request = body.get("userRequest", {})
    callback_url = user_request.get("callbackUrl")
    
    print(f"추출된 콜백 URL: {callback_url}", flush=True)

    # 1차 응답
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {"outputs": [{"simpleText": {"text": "메뉴를 불러오는 중입니다..."}}]}
    }
    
    if callback_url:
        background_tasks.add_task(send_menu, callback_url)
    else:
        print("🚨 에러: 콜백 URL이 없습니다. 오픈빌더 콜백 설정을 확인하세요.", flush=True)

    return JSONResponse(content=immediate_response)

async def send_menu(callback_url: str):
    try:
        print("백그라운드 메뉴 전송 시작...", flush=True)
        
        # 이미지 없이 텍스트 버튼만 먼저 테스트
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "textCard": {
                            "title": "소윤의 사주타로",
                            "description": "원하시는 메뉴를 선택해주세요.",
                            "buttons": [
                                {"action": "message", "label": "🔮 사주 보기", "messageText": "사주"},
                                {"action": "message", "label": "🃏 타로 보기", "messageText": "타로"},
                                {"action": "message", "label": "💑 궁합 보기", "messageText": "궁합"}
                            ]
                        }
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(callback_url, json=payload)
            print(f"✅ 메뉴 전송 완료! 상태코드: {res.status_code}", flush=True)
            
    except Exception as e:
        print(f"🚨 백그라운드 에러: {e}", flush=True)
