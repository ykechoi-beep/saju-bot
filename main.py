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
        
        api_key = os.getenv("KASI_API_KEY")
        
        # 테스트를 위해 1990년 1월 1일 날짜로 호출합니다.
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
        
        if response.status_code == 200:
            data = response.json()
            # KASI API 응답 구조에서 'item' 부분만 추출합니다.
            item = data['response']['body']['items']['item']
            
            # 데이터 추출 (예: 음력 12월 5일, 병인일 등)
            lun_year = item.get('lunYear', '알수없음')
            lun_month = item.get('lunMonth', '알수없음')
            lun_day = item.get('lunDay', '알수없음')
            lun_iljin = item.get('lunIljin', '알수없음')
            
            # 예쁘게 글자 조합하기
            result_text = (
                f"입력하신 양력 1990년 1월 1일의 천문학적 분석 결과입니다.\n\n"
                f"🌙 음력 날짜: {lun_year}년 {lun_month}월 {lun_day}일\n"
                f"✨ 일진(기운): {lun_iljin}\n\n"
                f"*(이 데이터를 바탕으로 사주 풀이가 진행됩니다.)*"
            )
        else:
            result_text = "KASI API 통신에 실패했습니다. API 키를 확인해주세요."

        # 카카오톡으로 보낼 카드 만들기
        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "textCard": {
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
