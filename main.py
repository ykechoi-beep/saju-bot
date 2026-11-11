import os
import httpx
import asyncio
import requests
import re
import random
import time
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
import uuid
from sajupy import calculate_saju
from google import genai

app = FastAPI()
os.makedirs("/tmp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/tmp/static"), name="static")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def draw_stars(draw, width, height):
    for _ in range(80):
        x, y = random.randint(0, width), random.randint(0, height)
        r = random.randint(1, 3)
        draw.ellipse([x, y, x+r, y+r], fill=(255, 255, 255))

def parse_date(date_str: str, time_str: str):
    # 날짜 파싱 (YYYY, MM, DD)
    date_nums = re.findall(r'\d+', date_str)
    year, month, day = 1990, 1, 1
    if len(date_nums) >= 3:
        year, month, day = int(date_nums[0]), int(date_nums[1]), int(date_nums[2])
        
    # 시간 파싱 (HH, MM)
    hour_24, minute = 12, 0
    time_nums = re.findall(r'\d+', time_str)
    if time_nums:
        raw_hour = int(time_nums[0])
        if len(time_nums) > 1: minute = int(time_nums[1])
        if "오후" in time_str and raw_hour < 12: hour_24 = raw_hour + 12
        elif "오전" in time_str and raw_hour == 12: hour_24 = 0
        else: hour_24 = raw_hour
        
    return year, month, day, hour_24, minute

@app.get("/")
async def root():
    return {"message": "서버 정상 작동 중"}

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    user_request = body.get("userRequest", {})
    callback_url = user_request.get("callbackUrl")
    action = body.get("action", {})
    params = action.get("params", {})
    block_name = user_request.get("block", {}).get("name", "")
    utterance = user_request.get("utterance", "")
    
    base_url = str(request.base_url).rstrip('/')
    
    immediate_response = {
        "version": "2.0",
        "useCallback": True,
        "template": {"outputs": [{"simpleText": {"text": "🔮 분석을 준비합니다..."}}]}
    }
    
    if callback_url:
        background_tasks.add_task(route_process, callback_url, base_url, block_name, params, utterance)
        
    return JSONResponse(content=immediate_response)

async def route_process(callback_url: str, base_url: str, block_name: str, params: dict, utterance: str):
    if "메인메뉴" in block_name or "웰컴" in block_name:
        await process_main_menu(callback_url, base_url)
    elif "사주" in block_name:
        birth_date = params.get("birthDate", "")
        birth_time = params.get("birthTime", "")
        
        # 💡 만약 사용자가 그냥 "사주" 버튼을 눌러서 날짜가 없으면 폼 이미지 전송
        if not birth_date:
            await process_saju_input_form(callback_url, base_url)
        else:
            # 날짜와 시간이 모두 있으면 결과 전송
            await process_saju_result(callback_url, base_url, birth_date, birth_time)

# --- 메인 메뉴 ---
async def process_main_menu(callback_url: str, base_url: str):
    img = Image.new('RGB', (800, 400), color=(10, 10, 25))
    draw = ImageDraw.Draw(img)
    draw_stars(draw, 800, 400)
    try:
        font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 50)
        font_sub = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
    except: font_title = font_sub = None
    draw.text((180, 120), "🌌 소윤의 사주타로", font=font_title, fill=(255, 215, 0))
    draw.text((230, 220), "당신의 우주를 분석해드립니다", font=font_sub, fill=(200, 200, 200))

    filename = f"main_{uuid.uuid4().hex[:8]}.png"
    img.save(f"/tmp/static/{filename}")
    
    payload = {
        "version": "2.0",
        "template": {
            "outputs": [
                {"basicCard": {
                    "title": "환영합니다!",
                    "description": "원하시는 서비스를 아래 버튼에서 선택해주세요.",
                    "thumbnail": {"imageUrl": f"{base_url}/static/{filename}", "fixedRatio": True, "width": 800, "height": 400},
                    "buttons": [
                        {"action": "message", "label": "🔮 사주 보기", "messageText": "사주"},
                        {"action": "message", "label": "🃏 타로 보기", "messageText": "타로"},
                        {"action": "message", "label": "💑 궁합 보기", "messageText": "궁합"}
                    ]
                }}
            ]
        }
    }
    async with httpx.AsyncClient() as client_http:
        await client_http.post(callback_url, json=payload)

# --- 사주 입력 폼 UI ---
async def process_saju_input_form(callback_url: str, base_url: str):
    img = Image.new('RGB', (800, 500), color=(20, 20, 40))
    draw = ImageDraw.Draw(img)
    draw_stars(draw, 800, 500)
    try:
        font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
        font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 30)
        font_box = ImageFont.truetype("NanumGothic-Regular.ttf", 35)
    except: font_title = font_text = font_box = None

    draw.text((200, 50), "🔮 사주 정보 입력", font=font_title, fill=(255, 215, 0))
    draw.text((150, 120), "아래 순서대로 채팅창에 입력해주세요.", font=font_text, fill=(200, 200, 200))
    
    draw.rectangle([100, 200, 700, 280], outline=(0, 255, 255), width=3)
    draw.text((150, 225), "[ YYYY-MM-DD ]  [ HH:MM ]", font=font_box, fill=(0, 255, 255))
    
    draw.text((150, 320), "예시: 1995-05-05 15:30", font=font_text, fill=(150, 150, 150))
    draw.text((150, 380), "입력 후 바로 엔터를 눌러주세요!", font=font_text, fill=(255, 105, 180))

    filename = f"form_{uuid.uuid4().hex[:8]}.png"
    img.save(f"/tmp/static/{filename}")

    payload = {
        "version": "2.0",
        "template": {
            "outputs": [
                {"basicCard": {
                    "title": "생년월일시 입력",
                    "description": "박스 안의 형식대로 채팅창에 입력해주세요.",
                    "thumbnail": {"imageUrl": f"{base_url}/static/{filename}", "fixedRatio": True, "width": 800, "height": 500}
                }}
            ]
        }
    }
    async with httpx.AsyncClient() as client_http:
        await client_http.post(callback_url, json=payload)

# --- 사주 결과 ---
async def process_saju_result(callback_url: str, base_url: str, birth_date: str, birth_time: str):
    year, month, day, hour_24, minute = parse_date(birth_date, birth_time)
    saju_result = calculate_saju(year, month, day, hour_24, minute)
    hanja_to_hangul = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계", "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"}
    def conv_kr(t): return "".join([hanja_to_hangul.get(char, char) for char in t])
    saju_text = f"{conv_kr(saju_result['year_pillar'])} {conv_kr(saju_result['month_pillar'])} {conv_kr(saju_result['day_pillar'])} {conv_kr(saju_result['hour_pillar'])}"

    img = Image.new('RGB', (800, 600), color=(15, 15, 30))
    draw = ImageDraw.Draw(img)
    draw_stars(draw, 800, 600)
    try:
        font_title = ImageFont.truetype("NanumGothic-Regular.ttf", 40)
        font_text = ImageFont.truetype("NanumGothic-Regular.ttf", 28)
        font_saju = ImageFont.truetype("NanumGothic-Regular.ttf", 35)
    except: font_title = font_text = font_saju = None 
    
    draw.text((50, 40), "🌌 사주 일력창", font=font_title, fill=(255, 215, 0)) 
    draw.text((50, 100), f"입력: {birth_date} {birth_time}", font=font_text, fill=(200, 200, 200))
    draw.text((50, 150), f"사주: {saju_text}", font=font_saju, fill=(0, 255, 255)) 
    
    draw.text((50, 230), "재물운", font=font_text, fill=(255, 255, 255))
    draw.rectangle([150, 235, 700, 255], fill=(50, 50, 50))
    draw.rectangle([150, 235, 150 + random.randint(200, 550), 255], fill=(255, 215, 0))
    draw.text((50, 290), "애정운", font=font_text, fill=(255, 255, 255))
    draw.rectangle([150, 295, 700, 315], fill=(50, 50, 50))
    draw.rectangle([150, 295, 150 + random.randint(200, 550), 315], fill=(255, 105, 180))

    filename = f"saju_{uuid.uuid4().hex[:8]}.png"
    img.save(f"/tmp/static/{filename}")

    payload = {
        "version": "2.0",
        "template": {
            "outputs": [
                {"basicCard": {
                    "title": "사주 분석 완료",
                    "description": "아래 메뉴를 눌러 상세 운세를 확인하세요.",
                    "thumbnail": {"imageUrl": f"{base_url}/static/{filename}", "fixedRatio": True, "width": 800, "height": 600}
                }}
            ],
            "quickReplies": [
                {"action": "message", "label": "오늘의 운세", "messageText": f"오늘의 운세 {saju_text}"},
                {"action": "message", "label": "이달의 운세", "messageText": f"이달의 운세 {saju_text}"},
                {"action": "message", "label": "1년 운세", "messageText": f"1년 운세 {saju_text}"},
                {"action": "message", "label": "5년 운세", "messageText": f"5년 운세 {saju_text}"},
                {"action": "message", "label": "10년 운세", "messageText": f"10년 운세 {saju_text}"},
                {"action": "message", "label": "평생 운세", "messageText": f"평생 운세 {saju_text}"}
            ]
        }
    }
    async with httpx.AsyncClient() as client_http:
        await client_http.post(callback_url, json=payload)
