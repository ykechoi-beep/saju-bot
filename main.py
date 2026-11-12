import os
import time
import traceback
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sajupy import calculate_saju
from google import genai

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_ai_response(prompt: str) -> str:
    model_candidates = ['gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-1.5-flash']
    for model_name in model_candidates:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                if response.text: return response.text
            except Exception as e:
                if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(1)
                    continue
                else: break
    return "현재 우주의 기운이 혼잡하여 분석이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."

def get_no_cache_response(html_content: str):
    response = HTMLResponse(content=html_content)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def hanja_to_kr(text):
    hanja_to_hangul = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계", "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사", "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해"}
    return "".join([hanja_to_hangul.get(char, char) for char in text])

# ==========================================
# 공통 로딩 스크립트 및 프리미엄 CSS
# ==========================================
BASE_SCRIPT = """
    <script>
        window.onpageshow = function(e) { 
            if (e.persisted || (window.performance && window.performance.navigation.type === 2)) location.reload(); 
        };
        function showLoading() { document.getElementById('loading-overlay').style.display = 'flex'; }
    </script>
"""

BASE_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@300;400;700&display=swap');
    * { box-sizing: border-box; }
    body { 
        background: linear-gradient(135deg, #090909, #1a1612, #090909); /* 딥 블랙 & 다크 브라운 */
        color: #f0e6d2; 
        font-family: 'Noto Serif KR', 'Malgun Gothic', sans-serif; 
        margin: 0; 
        padding: 40px 20px; 
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .container { width: 100%; max-width: 480px; animation: fadeIn 1s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    
    .hero-section { text-align: center; margin-bottom: 40px; }
    .hero-title { color: #d4af37; font-size: 32px; font-weight: 700; margin: 0 0 15px 0; text-shadow: 0 0 20px rgba(212, 175, 55, 0.4); letter-spacing: 1px;}
    .hero-subtitle { color: #a0a0a0; font-size: 15px; line-height: 1.6; font-weight: 300; word-break: keep-all;}
    
    /* 💡 고급스러운 유리 질감 카드 (Glassmorphism) */
    .glass-panel { 
        background: rgba(255, 255, 255, 0.03); 
        backdrop-filter: blur(15px); 
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(212, 175, 55, 0.2); 
        border-radius: 24px; 
        padding: 40px 25px; 
        box-shadow: 0 15px 35px rgba(0,0,0,0.5);
        position: relative;
        overflow: hidden;
    }
    .glass-panel::before {
        content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(212, 175, 55, 0.05) 0%, transparent 60%);
        pointer-events: none;
    }

    .input-row { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 25px; position: relative; z-index: 2;}
    input[type="number"] { 
        padding: 15px 5px; 
        border: 1px solid rgba(212, 175, 55, 0.4); 
        border-radius: 12px; 
        background: rgba(0,0,0,0.4); 
        color: #fff; 
        width: 24%; 
        height: 60px; 
        text-align: center; 
        font-size: 18px; 
        font-family: 'Noto Serif KR', sans-serif;
        transition: all 0.3s;
    }
    input[type="number"]:focus { outline: none; border-color: #d4af37; box-shadow: 0 0 15px rgba(212,175,55,0.3); background: rgba(0,0,0,0.6);}
    input::placeholder { color: #666; }
    
    .radio-group { display: flex; justify-content: center; gap: 20px; margin-bottom: 25px; font-size: 14px; color: #ccc; position: relative; z-index: 2;}
    .radio-group label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
    input[type="radio"] { appearance: none; width: 16px; height: 16px; border: 1px solid #d4af37; border-radius: 50%; background: transparent; cursor: pointer; position: relative;}
    input[type="radio"]:checked::after { content: ''; position: absolute; top: 3px; left: 3px; width: 8px; height: 8px; background: #d4af37; border-radius: 50%; }
    
    .divider { border-top: 1px solid rgba(212, 175, 55, 0.2); margin: 30px 0 25px 0; text-align: center; position: relative; z-index: 2;}
    .divider span { background: #1a1612; color: #d4af37; padding: 0 15px; font-size: 13px; position: relative; top: -10px; letter-spacing: 2px;}
    
    .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; position: relative; z-index: 2; }
    button { 
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(212, 175, 55, 0.05)); 
        border: 1px solid rgba(212, 175, 55, 0.5); 
        color: #d4af37; 
        padding: 18px 10px; 
        border-radius: 12px; 
        font-family: 'Noto Serif KR', sans-serif;
        font-weight: 700; 
        font-size: 15px; 
        cursor: pointer; 
        transition: all 0.3s;
    }
    button:hover, button:active { 
        background: #d4af37; 
        color: #000; 
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);
        transform: translateY(-2px);
    }

    #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(9, 9, 9, 0.9); z-index: 9999; flex-direction: column; justify-content: center; align-items: center; backdrop-filter: blur(10px);}
    .spinner { border: 4px solid rgba(212, 175, 55, 0.2); border-top: 4px solid #d4af37; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 25px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loading-text { color: #d4af37; font-size: 18px; font-weight: bold; padding: 0 30px; line-height: 1.6; word-break: keep-all; text-align: center;}
    .loading-subtext { color: #888; font-size: 14px; margin-top: 15px; }
"""

# ==========================================
# 1. 사주 (Saju) 코드
# ==========================================
HTML_SAJU_FORM = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>소윤의 사주타로</title>
<style>{BASE_CSS}</style></head><body>
    {BASE_SCRIPT}
    <div id="loading-overlay"><div class="spinner"></div><div class="loading-text">당신의 고민과 타고난 운명의 흐름을<br>살펴보고 있습니다...</div><div class="loading-subtext">사주 명식을 분석 중입니다 (약 5~10초 소요)</div></div>
    
    <div class="container">
        <div class="hero-section">
            <h1 class="hero-title">🔮 사주 명리학</h1>
            <div class="hero-subtitle">당신의 삶의 좌표를 찾아드립니다.<br>생년월일시를 입력하고 운세를 확인하세요.</div>
        </div>
        
        <form action="/saju/result" method="GET" onsubmit="showLoading()">
            <div class="glass-panel">
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
                <div class="radio-group" style="margin-bottom: 0;">
                    <label><input type="radio" name="gender" value="남성" checked> 남성</label>
                    <label><input type="radio" name="gender" value="여성"> 여성</label>
                </div>
                
                <div class="divider"><span>운세 선택</span></div>
                
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
    </div>
</body></html>
"""

HTML_SAJU_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>분석 결과</title>
<style>
    {BASE_CSS}
    .result-box {{ background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 20px; padding: 30px 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: left; }}
    .result-title {{ color: #d4af37; font-size: 22px; font-weight: bold; border-bottom: 1px solid rgba(212, 175, 55, 0.3); padding-bottom: 15px; text-align: center; margin-bottom: 20px;}}
    .saju-text {{ font-size: 18px; font-weight: bold; color: #fff; margin: 20px 0; text-align: center; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border: 1px solid rgba(212,175,55,0.2);}}
    .ai-comment {{ line-height: 1.8; font-size: 15px; color: #ccc; font-weight: 300;}}
    .back-btn {{ display: block; margin-top: 30px; color: #d4af37; text-decoration: none; font-weight: bold; border: 1px solid #d4af37; padding: 15px; border-radius: 12px; text-align: center; background: transparent; transition: 0.3s;}}
    .back-btn:hover {{ background: rgba(212,175,55,0.1); }}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">🔮 분석 결과</h1></div>
        {{result_content}}
    </div>
</body></html>
"""

@app.get("/saju")
async def saju_page(): return get_no_cache_response(HTML_SAJU_FORM)

@app.get("/saju/result")
async def saju_result(year: int, month: int, day: int, hour: int, calendar: str, gender: str, fortune_type: str):
    try:
        fortune_map = {"today": "오늘의 운세", "month": "이달의 운세", "year1": "1년 운세", "year5": "5년 운세", "year10": "10년 운세", "life": "평생 운세"}
        fortune_type_kr = fortune_map.get(fortune_type, "오늘의 운세")
        saju_result = calculate_saju(year, month, day, hour, 0)
        saju_text = f"{hanja_to_kr(saju_result['year_pillar'])} {hanja_to_kr(saju_result['month_pillar'])} {hanja_to_kr(saju_result['day_pillar'])} {hanja_to_kr(saju_result['hour_pillar'])}"
        prompt = f"너는 친절하고 신비로운 분위기의 동양 명리학 사주 상담가야. {gender}의 사주팔자({saju_text})를 바탕으로 '{fortune_type_kr}'에 대한 조언을 4문장 이내로 따뜻하고 긍정적으로 해줘. 참고로 입력된 생년월일시는 '{calendar}' 기준이야."
        ai_comment = get_ai_response(prompt)
        
        result_html = f"""
        <div class="result-box">
            <div class="result-title">🔮 {fortune_type_kr}</div>
            <div class="saju-text">사주팔자: {saju_text}</div>
            <div class="ai-comment">{ai_comment}</div>
            <a href="/saju?v=1" class="back-btn">← 다시 입력하기</a>
        </div>
        """
        return get_no_cache_response(HTML_SAJU_RESULT.replace("{result_content}", result_html))
    except Exception as e:
        return get_no_cache_response(HTML_SAJU_RESULT.replace("{result_content}", f"<div class='result-box'>오류: {str(e)}</div>"))

# ==========================================
# 2. 타로 (Tarot) 코드 - 3단계 프로세스 (테마 변경)
# ==========================================
HTML_TAROT_CATEGORY = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 고민 선택</title>
<style>
    {BASE_CSS}
    body {{ background: linear-gradient(135deg, #0a0510, #1e0b36, #0a0510); }} /* 타로는 보라색 테마 */
    .category-btn {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(138, 43, 226, 0.4); border-radius: 16px; padding: 22px; font-size: 18px; color: #d8b4e2; font-weight: bold; cursor: pointer; transition: 0.3s; display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);}}
    .category-btn:active, .category-btn:hover {{ transform: scale(0.98); background: rgba(138, 43, 226, 0.2); border-color: #d8b4e2; }}
    .hero-title {{ color: #d8b4e2; text-shadow: 0 0 20px rgba(138,43,226,0.5); }}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">🃏 신비의 타로</h1><div class="hero-subtitle">마음을 가라앉히고<br>지금 가장 궁금한 고민을 선택하세요.</div></div>
        <form action="/tarot/cards" method="GET" onsubmit="showLoading()">
            <button type="submit" name="category" value="love" class="category-btn">💕 연애 / 관계</button>
            <button type="submit" name="category" value="career" class="category-btn">💼 직업 / 진로</button>
            <button type="submit" name="category" value="wealth" class="category-btn">💰 재물 / 금전</button>
            <button type="submit" name="category" value="health" class="category-btn">🌿 건강 / 마음</button>
        </form>
    </div>
</body></html>
"""

HTML_TAROT_CARDS = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 카드 뽑기</title>
<style>
    {BASE_CSS}
    body {{ background: linear-gradient(135deg, #0a0510, #1e0b36, #0a0510); }}
    .card-grid {{ display: flex; justify-content: space-between; gap: 10px; margin-bottom: 30px; }}
    .tarot-card {{ background: linear-gradient(135deg, #2b154a, #150726); border: 1px solid rgba(216, 180, 226, 0.5); border-radius: 16px; width: 30%; height: 220px; display: flex; flex-direction: column; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 4px 15px rgba(138,43,226,0.3); transition: transform 0.2s; }}
    .tarot-card:active {{ transform: scale(0.95); }}
    .card-icon {{ font-size: 45px; margin-bottom: 15px; color: #d8b4e2; filter: drop-shadow(0 0 10px rgba(138,43,226,0.8));}}
    .card-text {{ font-size: 15px; font-weight: bold; color: #d8b4e2;}}
    .hero-title {{ color: #d8b4e2; text-shadow: 0 0 20px rgba(138,43,226,0.5); }}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">🃏 카드 뽑기</h1><div class="hero-subtitle">직관적으로 끌리는 카드를<br>하나 선택하세요.</div></div>
        <form action="/tarot/result" method="GET" onsubmit="showLoading()">
            <input type="hidden" name="category" value="{{category}}">
            <div class="card-grid">
                <button type="submit" name="card" value="1" class="tarot-card"><div class="card-icon">🌙</div><div class="card-text">1번</div></button>
                <button type="submit" name="card" value="2" class="tarot-card"><div class="card-icon">⭐</div><div class="card-text">2번</div></button>
                <button type="submit" name="card" value="3" class="tarot-card"><div class="card-icon">☀️</div><div class="card-text">3번</div></button>
            </div>
        </form>
    </div>
</body></html>
"""

HTML_TAROT_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 결과</title>
<style>
    {BASE_CSS}
    body {{ background: linear-gradient(135deg, #0a0510, #1e0b36, #0a0510); }}
    .result-box {{ background: rgba(43, 21, 74, 0.6); backdrop-filter: blur(15px); border: 1px solid rgba(216, 180, 226, 0.3); border-radius: 20px; padding: 30px 25px; text-align: left; box-shadow: 0 10px 30px rgba(0,0,0,0.5);}}
    .result-title {{ color: #d8b4e2; font-size: 20px; font-weight: bold; border-bottom: 1px solid rgba(216,180,226,0.3); padding-bottom: 15px; text-align: center; margin-bottom: 20px;}}
    .card-name {{ font-size: 24px; font-weight: bold; color: #fff; margin: 20px 0; text-align: center; text-shadow: 0 0 15px rgba(138,43,226,0.8);}}
    .ai-comment {{ line-height: 1.8; font-size: 15px; color: #ccc; font-weight: 300;}}
    .back-btn {{ display: block; margin-top: 30px; color: #d8b4e2; text-decoration: none; font-weight: bold; border: 1px solid #d8b4e2; padding: 15px; border-radius: 12px; text-align: center; background: transparent; transition: 0.3s;}}
    .hero-title {{ color: #d8b4e2; text-shadow: 0 0 20px rgba(138,43,226,0.5); }}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">🃏 타로 리딩</h1></div>
        {{result_content}}
    </div>
</body></html>
"""

@app.get("/tarot")
async def tarot_page(): return get_no_cache_response(HTML_TAROT_CATEGORY)

@app.get("/tarot/cards")
async def tarot_cards(category: str):
    html = HTML_TAROT_CARDS.replace("{category}", category)
    return get_no_cache_response(html)

@app.get("/tarot/result")
async def tarot_result(category: str, card: int):
    try:
        category_map = {"love": "연애/관계", "career": "직업/진로", "wealth": "재물/금전", "health": "건강/마음"}
        category_kr = category_map.get(category, "종합 운세")
        card_map = {1: "달 (The Moon)", 2: "별 (The Star)", 3: "태양 (The Sun)"}
        selected_card = card_map.get(card, "운명의 수레바퀴")
        
        prompt = f"너는 신비로운 타로 마스터야. 사용자가 '{category_kr}' 고민을 가지고 '{selected_card}' 카드를 뽑았어. 이 카드가 의미하는 메시지와 '{category_kr}'에 대한 조언을 4문장 이내로 신비롭게 해석해줘."
        ai_comment = get_ai_response(prompt)
        
        result_html = f"""<div class="result-box"><div class="result-title">🔮 {category_kr} 리딩</div><div class="card-name">✨ {selected_card} ✨</div><div class="ai-comment">{ai_comment}</div><a href="/tarot?v=1" class="back-btn">← 다시 뽑기</a></div>"""
        return get_no_cache_response(HTML_TAROT_RESULT.replace("{result_content}", result_html))
    except Exception as e:
         return get_no_cache_response(HTML_TAROT_RESULT.replace("{result_content}", f"<div class='result-box'>오류: {str(e)}</div>"))

# ==========================================
# 3. 궁합 (Compatibility) 코드 (프리미엄 디자인)
# ==========================================
HTML_COMPAT_FORM = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>궁합 보기</title>
<style>
    {BASE_CSS}
    body {{ background: linear-gradient(135deg, #1a0b12, #2e0f1d, #1a0b12); }} /* 궁합은 로맨틱한 다크 레드 테마 */
    .hero-title {{ color: #ff69b4; text-shadow: 0 0 20px rgba(255,105,180,0.4); }}
    .person-title {{ font-weight: bold; color: #ff69b4; text-align: left; margin-bottom: 15px; font-size: 16px;}}
    input[type="number"] {{ border: 1px solid rgba(255, 105, 180, 0.4); }}
    input[type="number"]:focus {{ border-color: #ff69b4; box-shadow: 0 0 15px rgba(255,105,180,0.3); }}
    input[type="radio"] {{ border: 1px solid #ff69b4; }}
    input[type="radio"]:checked::after {{ background: #ff69b4; }}
    button {{ background: linear-gradient(135deg, rgba(255, 105, 180, 0.1), rgba(255, 105, 180, 0.05)); border: 1px solid rgba(255, 105, 180, 0.5); color: #ff69b4; width: 100%; margin-top: 10px; padding: 20px;}}
    button:hover, button:active {{ background: #ff69b4; color: #fff; box-shadow: 0 0 20px rgba(255,105,180,0.4); }}
    .divider span {{ color: #ff69b4; background: #1a0b12;}}
    .glass-panel {{ border-color: rgba(255, 105, 180, 0.2); }}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">💞 궁합 분석</h1><div class="hero-subtitle">두 사람의 케미스트리를 확인해보세요.</div></div>
        <form action="/compat/result" method="GET" onsubmit="showLoading()">
            <div class="glass-panel" style="margin-bottom: 20px;">
                <div class="person-title">👨 남성</div>
                <div class="input-row"><input type="number" name="m_year" placeholder="년" required><input type="number" name="m_month" placeholder="월" required><input type="number" name="m_day" placeholder="일" required><input type="number" name="m_hour" placeholder="시" required></div>
                <div class="radio-group"><label><input type="radio" name="m_calendar" value="양력" checked> 양력</label><label><input type="radio" name="m_calendar" value="음력"> 음력</label></div>
            </div>
            <div class="glass-panel">
                <div class="person-title">👩 여성</div>
                <div class="input-row"><input type="number" name="f_year" placeholder="년" required><input type="number" name="f_month" placeholder="월" required><input type="number" name="f_day" placeholder="일" required><input type="number" name="f_hour" placeholder="시" required></div>
                <div class="radio-group"><label><input type="radio" name="f_calendar" value="양력" checked> 양력</label><label><input type="radio" name="f_calendar" value="음력"> 음력</label></div>
            </div>
            <button type="submit">궁합 보기</button>
        </form>
    </div>
</body></html>
"""

HTML_COMPAT_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>궁합 결과</title>
<style>
    {BASE_CSS}
    body {{ background: linear-gradient(135deg, #1a0b12, #2e0f1d, #1a0b12); }}
    .hero-title {{ color: #ff69b4; text-shadow: 0 0 20px rgba(255,105,180,0.4); }}
    .result-box {{ background: rgba(255, 105, 180, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(255, 105, 180, 0.3); border-radius: 20px; padding: 30px 25px; text-align: left; box-shadow: 0 10px 30px rgba(0,0,0,0.5);}}
    .result-title {{ color: #ff69b4; font-size: 20px; font-weight: bold; border-bottom: 1px solid rgba(255,105,180,0.3); padding-bottom: 15px; text-align: center; margin-bottom: 20px;}}
    .saju-compare {{ display: flex; justify-content: space-around; margin: 20px 0; text-align: center; font-weight: bold; color: #fff; background: rgba(0,0,0,0.4); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,105,180,0.2);}}
    .ai-comment {{ line-height: 1.8; font-size: 15px; color: #ccc; font-weight: 300;}}
    .back-btn {{ display: block; margin-top: 30px; color: #ff69b4; text-decoration: none; font-weight: bold; border: 1px solid #ff69b4; padding: 15px; border-radius: 12px; text-align: center; background: transparent; transition: 0.3s;}}
</style></head><body>
    {BASE_SCRIPT}
    <div class="container">
        <div class="hero-section"><h1 class="hero-title">💞 궁합 결과</h1></div>
        {{result_content}}
    </div>
</body></html>
"""

@app.get("/compat")
async def compat_page(): return get_no_cache_response(HTML_COMPAT_FORM)

@app.get("/compat/result")
async def compat_result(m_year: int, m_month: int, m_day: int, m_hour: int, m_calendar: str, f_year: int, f_month: int, f_day: int, f_hour: int, f_calendar: str):
    try:
        m_saju_res = calculate_saju(m_year, m_month, m_day, m_hour, 0)
        m_saju = f"{hanja_to_kr(m_saju_res['year_pillar'])} {hanja_to_kr(m_saju_res['month_pillar'])} {hanja_to_kr(m_saju_res['day_pillar'])} {hanja_to_kr(m_saju_res['hour_pillar'])}"
        
        f_saju_res = calculate_saju(f_year, f_month, f_day, f_hour, 0)
        f_saju = f"{hanja_to_kr(f_saju_res['year_pillar'])} {hanja_to_kr(f_saju_res['month_pillar'])} {hanja_to_kr(f_saju_res['day_pillar'])} {hanja_to_kr(f_saju_res['hour_pillar'])}"
        
        prompt = f"너는 신비로운 궁합 상담가야. 남자 사주({m_saju}, {m_calendar} 기준)와 여자 사주({f_saju}, {f_calendar} 기준)를 바탕으로 두 사람의 케미스트리와 연애/결혼 운을 5문장 이내로 따뜻하고 긍정적으로 분석해줘."
        ai_comment = get_ai_response(prompt)
        
        result_html = f"""<div class="result-box"><div class="result-title">케미스트리 분석</div><div class="saju-compare"><div>👨 남성<br>{m_saju}</div><div>💕</div><div>👩 여성<br>{f_saju}</div></div><div class="ai-comment">{ai_comment}</div><a href="/compat?v=1" class="back-btn">← 다시 입력하기</a></div>"""
        return get_no_cache_response(HTML_COMPAT_RESULT.replace("{result_content}", result_html))
    except Exception as e:
         return get_no_cache_response(HTML_COMPAT_RESULT.replace("{result_content}", f"<div class='result-box'>오류: {str(e)}</div>"))

# ==========================================
# 루트 접속 시 사주로 리다이렉트 (선택사항)
# ==========================================
@app.get("/")
async def root_page():
    return get_no_cache_response(HTML_SAJU_FORM)
