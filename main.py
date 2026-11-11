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

# AI 풀이 함수 (재시도 로직 포함)
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
                else: break
    return "현재 우주의 기운이 혼잡하여 분석이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."

# --- 동양 테마의 세련된 웹페이지 디자인 (HTML/CSS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>소윤의 사주타로</title>
    <style>
        body { 
            background-color: #f4e8d3; /* 조금 더 진한 한지 느낌 배경 */
            color: #333; 
            font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; /* 맑은 고딕 적용 */
            text-align: center; 
            padding: 20px; 
            margin: 0;
        }
        .container {
            max-width: 500px;
            margin: 0 auto;
        }
        h1 { 
            color: #b8860b; /* 황금빛 */
            font-size: 28px;
            margin-bottom: 10px;
            letter-spacing: -1px;
            font-weight: 800;
        }
        .welcome { 
            color: #8b4513; /* 동양적인 갈색 */
            font-size: 15px;
            margin-bottom: 30px;
            font-weight: 700;
            line-height: 1.5;
        }
        .form-group { 
            background: #fff; 
            border: 2px solid #d4af37; /* 황금색 테두리 */
            border-radius: 12px; 
            padding: 30px 20px 20px 20px; /* 위쪽 여백을 충분히 줌 */
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            box-sizing: border-box;
        }
        .input-row { 
            display: flex; 
            justify-content: center; 
            align-items: center;
            gap: 6px; 
            margin-bottom: 20px;
            width: 100%;
            box-sizing: border-box;
        }
        input[type="number"] { 
            padding: 12px 2px; 
            border: 1px solid #ccc; 
            border-radius: 8px; 
            background: #fafafa; 
            color: #333; 
            width: 22%; /* 고정 픽셀 대신 %로 변경하여 테두리 뚫림 방지 */
            max-width: 80px;
            text-align: center; 
            font-family: 'Malgun Gothic', sans-serif;
            font-size: 16px;
            box-sizing: border-box;
        }
        input::placeholder { color: #aaa; }
        
        .radio-group { 
            margin-bottom: 15px; 
            font-size: 15px;
            display: flex;
            justify-content: center;
            gap: 15px;
        }
        .radio-group label { cursor: pointer; display: flex; align-items: center; gap: 5px;}
        
        .menu-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 10px; 
            margin-top: 15px; 
        }
        button { 
            background: #b8860b; /* 황금빛 버튼 */
            color: #fff; 
            border: none; 
            padding: 15px; 
            border-radius: 8px; 
            font-family: 'Malgun Gothic', sans-serif;
            font-weight: 700; 
            font-size: 15px;
            cursor: pointer; 
            transition: background 0.3s;
        }
        button:hover { background: #8b6508; }
        
        .result-box { 
            background: #fff; 
            padding: 25px 20px; 
            border-radius: 12px; 
            margin-top: 20px; 
            text-align: left; 
            border: 2px solid #b8860b; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        }
        .result-title { 
            color: #b8860b; 
            font-size: 20px; 
            font-weight: bold;
            border-bottom: 2px dashed #d4af37; 
            padding-bottom: 15px;
            text-align: center;
        }
        .saju-text { 
            font-size: 18px; 
            font-weight: bold; 
            color: #8b4513; 
            margin: 20px 0; 
            text-align: center; 
            background: #fdf5e6; 
            padding: 15px; 
            border-radius: 8px;
            line-height: 1.5;
        }
        .ai-comment { 
            line-height: 1.7; 
            font-size: 15px;
            color: #444;
        }
        
        .back-btn { 
            display: inline-block; 
            margin-top: 25px; 
            color: #8b4513; 
            text-decoration: none; 
            font-weight: bold; 
            border: 1px solid #8b4513; 
            padding: 10px 20px; 
            border-radius: 8px;
            text-align: center;
            width: 100%;
            box-sizing: border-box;
        }
        .back-btn:hover { background: #fdf5e6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 소윤의 사주타로</h1>
        <div class="welcome">환영합니다.<br>당신의 삶의 좌표를 찾아드립니다.</div>

        {% if not result %}
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
                    <button name="fortune_type" value="오늘의 운세">오늘의 운세</button>
                    <button name="fortune_type" value="이달의 운세">이달의 운세</button>
                    <button name="fortune_type" value="1년 운세">1년 운세</button>
                    <button name="fortune_type" value="5년 운세">5년 운세</button>
                    <button name="fortune_type" value="10년 운세">10년 운세</button>
                    <button name="fortune_type" value="평생 운세">평생 운세</button>
                </div>
            </div>
        </form>
        {% endif %}

        {% if result %}
        <div class="result-box">
            <div class="result-title">🔮 {{ result.type }} 분석 결과</div>
            <div class="saju-text">{{ result.saju_text }}</div>
            <div class="ai-comment">{{ result.ai_comment }}</div>
            <div style="text-align:center;">
                <a href="/saju" class="back-btn">← 다시 입력하기</a>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- 1. 사주 메인 화면 (입력 폼) ---
@app.get("/saju", response_class=HTMLResponse)
async def saju_page():
    # 초기 접속 시 result 변수 없이 템플릿 렌더링
    html = HTML_TEMPLATE.replace("{% if not result %}", "").replace("{% endif %}", "").replace("{% if result %}", "<div style='display:none;'>").replace("{{ result.type }}", "").replace("{{ result.saju_text }}", "").replace("{{ result.ai_comment }}", "")
    return HTMLResponse(content=html)

# --- 2. 사주 결과 화면 (버튼 클릭 시) ---
@app.get("/saju/result", response_class=HTMLResponse)
async def saju_result(year: int, month: int, day: int, hour: int, calendar: str, gender: str, fortune_type: str):
    try:
        # 사주 계산 (sajupy는 기본적으로 양력 기준으로 계산합니다. 음력 처리는 추후 고도화 필요)
        saju_result = calculate_saju(year, month, day, hour, 0)
        hanja_to_hangul = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계", "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"}
        def conv_kr(t): return "".join([hanja_to_hangul.get(char, char) for char in t])
        saju_text = f"{conv_kr(saju_result['year_pillar'])} {conv_kr(saju_result['month_pillar'])} {conv_kr(saju_result['day_pillar'])} {conv_kr(saju_result['hour_pillar'])}"

        # AI 프롬프트 작성 (음력/양력 정보 포함)
        prompt = f"너는 친절하고 신비로운 분위기의 동양 명리학 사주 상담가야. {gender}의 사주팔자({saju_text})를 바탕으로 '{fortune_type}'에 대한 조언을 4문장 이내로 따뜻하고 긍정적으로 해줘. 참고로 입력된 생년월일시는 '{calendar}' 기준이야. 한자보다는 한글로 풀어서 설명해줘."
        ai_comment = get_ai_response(prompt)

        # 결과 HTML 렌더링 (입력 폼 숨기고 결과창 보여주기)
        html = HTML_TEMPLATE
        html = html.replace("{% if not result %}", "<div style='display:none;'>").replace("{% endif %}", "</div>")
        html = html.replace("{% if result %}", "").replace("{% endif %}", "")
        
        # 결과 데이터 주입
        html = html.replace("{{ result.type }}", fortune_type)
        html = html.replace("{{ result.saju_text }}", f"사주팔자: {saju_text}")
        html = html.replace("{{ result.ai_comment }}", ai_comment)
        
        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"<h2>오류가 발생했습니다.</h2><p>{str(e)}</p><a href='/saju'>돌아가기</a>")
