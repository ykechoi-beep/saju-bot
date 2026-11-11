import os
import random
import requests
import time
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from sajupy import calculate_saju
from google import genai

app = FastAPI()

# Gemini AI 클라이언트 초기화
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# AI 풀이 함수
def get_ai_response(prompt: str) -> str:
    model_candidates = ['gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-1.5-flash']
    for model_name in model_candidates:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                if response.text: return response.text
            except Exception as e:
                if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(2 ** attempt)
                    continue
                else: 
                    print(f"AI 에러: {e}")
                    break
    return "현재 우주의 기운이 혼잡하여 분석이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."

# 💡 화면 깨짐 방지를 위해 HTML을 HEAD, TAIL로 분리하여 완벽하게 조립합니다.
HTML_HEAD = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>소윤의 사주타로</title>
    <style>
        body { background-color: #f4e8d3; color: #333; font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; text-align: center; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { color: #b8860b; font-size: 28px; margin-bottom: 10px; letter-spacing: -1px; font-weight: 800; }
        .welcome { color: #8b4513; font-size: 15px; margin-bottom: 30px; font-weight: 700; line-height: 1.5; }
        .form-group { background: #fff; border: 2px solid #d4af37; border-radius: 12px; padding: 40px 20px 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 20px; box-sizing: border-box; }
        .input-row { display: flex; justify-content: center; align-items: center; gap: 6px; margin-bottom: 20px; width: 100%; box-sizing: border-box; }
        input[type="number"] { padding: 15px 5px; border: 2px solid #d4af37; border-radius: 10px; background: #fafafa; color: #333; width: 23%; max-width: 85px; height: 55px; text-align: center; font-family: 'Malgun Gothic', sans-serif; font-size: 20px; font-weight: bold; box-sizing: border-box; }
        input::placeholder { color: #aaa; font-weight: normal;}
        .radio-group { margin-bottom: 15px; font-size: 15px; display: flex; justify-content: center; gap: 15px; }
        .radio-group label { cursor: pointer; display: flex; align-items: center; gap: 5px;}
        .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        button { background: #b8860b; color: #fff; border: none; padding: 15px; border-radius: 8px; font-family: 'Malgun Gothic', sans-serif; font-weight: 700; font-size: 15px; cursor: pointer; transition: background 0.1s; }
        button:active { background: #5c4000; transform: scale(0.98); }
        .result-box { background: #fff; padding: 25px 20px; border-radius: 12px; margin-top: 20px; text-align: left; border: 2px solid #b8860b; box-shadow: 0 4px 10px rgba(0,0,0,0.08); }
        .result-title { color: #b8860b; font-size: 20px; font-weight: bold; border-bottom: 2px dashed #d4af37; padding-bottom: 15px; text-align: center; }
        .saju-text { font-size: 18px; font-weight: bold; color: #8b4513; margin: 20px 0; text-align: center; background: #fdf5e6; padding: 15px; border-radius: 8px; line-height: 1.5; }
        .ai-comment { line-height: 1.7; font-size: 15px; color: #444; }
        .back-btn { display: inline-block; margin-top: 25px; color: #8b4513; text-decoration: none; font-weight: bold; border: 1px solid #8b4513; padding: 10px 20px; border-radius: 8px; text-align: center; width: 100%; box-sizing: border-box; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 소윤의 사주타로</h1>
        <div class="welcome">환영합니다.<br>당신의 삶의 좌표를 찾아드립니다.</div>
"""

HTML_TAIL = """
    </div>
</body>
</html>
"""

@app.get("/saju", response_class=HTMLResponse)
async def saju_page():
    form_html = """
        <form action="/saju/result" method="get">
            <div class="form-group">
                <div class="input-row">
                    <input type="number" name="year" placeholder="년" required>
                    <input type="number" name="month" placeholder="월" required>
                    <input type="number" name="day" placeholder="일" required>
                    <input type="number" name="hour" placeholder="시" required>
                </div>
                
                <div class="radio-group">
                    <label><input type="radio" name="calendar" value="양력" checked> 양력</label>
                    <label><input type="radio" name="calendar" value="음력"> 음력</label>
                </div>
                
                <div class="radio-group">
                    <label><input type="radio" name="gender" value="남성" checked> 남성</label>
                    <label><input type="radio" name="gender" value="여성"> 여성</label>
                </div>
                
                <p style="color:#8b4513; font-size:14px; font-weight:bold; margin-bottom:15px; margin-top: 25px;">▼ 원하시는 운세를 선택해주세요 ▼</p>
                <div class="menu-grid">
                    <button type="submit" name="fortune_type" value="today">오늘의 운세</button>
                    <button type="submit" name="fortune_type" value="month">이달의 운세</button>
                    <button type="submit" name="fortune_type" value="year1">1년 운세</button>
                    <button type="submit" name="fortune_type" value="year5">5년 운세</button>
                    <button type="submit" name="fortune_type" value="year10">10년 운세</button>
                    <button type="submit" name="fortune_type" value="life">평생 운세</button>
                </div>
            </div>
        </form>
    """
    return HTMLResponse(content=HTML_HEAD + form_html + HTML_TAIL)

@app.get("/saju/result", response_class=HTMLResponse)
async def saju_result(year: int, month: int, day: int, hour: int, calendar: str, gender: str, fortune_type: str):
    try:
        fortune_map = {
            "today": "오늘의 운세", "month": "이달의 운세", "year1": "1년 운세",
            "year5": "5년 운세", "year10": "10년 운세", "life": "평생 운세"
        }
        fortune_type_kr = fortune_map.get(fortune_type, "오늘의 운세")

        saju_result = calculate_saju(year, month, day, hour, 0)
        hanja_to_hangul = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계", "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"}
        def conv_kr(t): return "".join([hanja_to_hangul.get(char, char) for char in t])
        saju_text = f"{conv_kr(saju_result['year_pillar'])} {conv_kr(saju_result['month_pillar'])} {conv_kr(saju_result['day_pillar'])} {conv_kr(saju_result['hour_pillar'])}"

        prompt = f"너는 친절하고 신비로운 분위기의 동양 명리학 사주 상담가야. {gender}의 사주팔자({saju_text})를 바탕으로 '{fortune_type_kr}'에 대한 조언을 4문장 이내로 따뜻하고 긍정적으로 해줘. 참고로 입력된 생년월일시는 '{calendar}' 기준이야. 한자보다는 한글로 풀어서 설명해줘."
        ai_comment = get_ai_response(prompt)

        result_html = f"""
        <div class="result-box">
            <div class="result-title">🔮 {fortune_type_kr} 분석 결과</div>
            <div class="saju-text">사주팔자: {saju_text}</div>
            <div class="ai-comment">{ai_comment}</div>
            <div style="text-align:center;">
                <a href="/saju" class="back-btn">← 다시 입력하기</a>
            </div>
        </div>
        """
        
        return HTMLResponse(content=HTML_HEAD + result_html + HTML_TAIL)
        
    except Exception as e:
        error_html = f"""
        <div class="result-box">
            <h2 style="color:red;">분석 중 오류가 발생했습니다.</h2>
            <p>{str(e)}</p>
            <a href="/saju" class="back-btn">← 돌아가기</a>
        </div>
        """
        return HTMLResponse(content=HTML_HEAD + error_html + HTML_TAIL)
