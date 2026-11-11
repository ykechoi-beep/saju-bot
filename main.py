import os
import httpx
import asyncio
import requests # KASI API 호출용
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "소윤의 천문사주 서버가 정상 작동 중입니다!"}

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
        
        # ==========================================
        # 💡 여기서 KASI API를 호출합니다.
        # ==========================================
        api_key = os.getenv("KASI_API_KEY")
        
        # 예시: 음양력 변환 API (실제 사용하시는 API URL로 변경하셔도 됩니다)
        # 테스트를 위해 1990년 1월 1일 날짜로 호출해 봅니다.
        url = "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
        params = {
            'serviceKey': api_key,
            'solYear': '1990',
            'solMonth': '01',
            'solDay': '01',
            '_type': 'json'
        }
        
        print("KASI API 호출 중...")
        response = requests.get(url, params=params, timeout=10)
        print(f"KASI API 응답 코드: {response.status_code}")
        
        # 응답 데이터를 텍스트로 변환 (성공 시)
        if response.status_code == 200:
            # JSON 데이터를 문자열로 잘라서 보여줍니다 (보기 좋게)
            data_text = str(response.json())[:200] + "..." 
            result_text = f"KASI API 통신 성공! 🌌\n\n응답 데이터:\n{data_text}"
        else:
            result_text = "KASI API 통신에 실패했습니다. API 키를 확인해주세요."

        # ==========================================
        # 💡 카카오톡으로 보낼 예쁜 카드(JSON) 만들기
        # ==========================================
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "textCard": {  # 텍스트 카드 형식 사용
                            "title": "🌌 천문학 사주 분석 결과",
                            "description": result_text,
                            "buttons": [
                                {
                                    "action": "message",
                                    "label": "다시 분석하기",
                                    "messageText": "사주 봐줘"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        print(f"콜백 URL로 전송 시도: {callback_url}")
        async with httpx.AsyncClient() as client:
            res = await client.post(callback_url, json=payload)
            print(f"카카오 응답 코드: {res.status_code}")
            
    except Exception as e:
        print(f"에러 발생: {e}")
