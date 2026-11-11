import os
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx
import asyncio

app = FastAPI()

# 테스트용 간단한 엔드포인트 (나중에 사주 로직으로 대체)
@app.get("/")
async def root():
    return {"message": "소윤의 천문사주 서버가 정상 작동 중입니다!"}

# 카카오톡 스킬 서버 엔드포인트
@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    user_request = body.get("userRequest", {})
    utterance = user_request.get("utterance", "")
    callback_url = user_request.get("callbackUrl")
    
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "🕯️ 우주의 기운을 모아 분석하고 있습니다. 잠시만 기다려주세요..."
                    }
                }
            ]
        }
    }
    
    if callback_url:
        background_tasks.add_task(process_saju, callback_url, utterance)
    
    return JSONResponse(content=immediate_response)

async def process_saju(callback_url: str, utterance: str):
    try:
        print(f"백그라운드 연산 시작: {utterance}")
        await asyncio.sleep(2) # 연산 시간 가정
        
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": f"'{utterance}'에 대한 분석이 완료되었습니다. (임시 결과)"}}
                ]
            }
        }
        
        print(f"콜백 URL로 전송 시도: {callback_url}")
        async with httpx.AsyncClient() as client:
            response = await client.post(callback_url, json=payload)
            print(f"카카오 응답 코드: {response.status_code}")
            
    except Exception as e:
        print(f"에러 발생: {e}") # 에러를 로그에 확실히 남깁니다.
        await client.post(callback_url, json=payload)
