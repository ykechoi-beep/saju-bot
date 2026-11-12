import os
import time
import traceback
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sajupy import calculate_saju
from google import genai

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 💡 전화번호를 여기서 한 번만 설정하면 모든 페이지에 적용됩니다.
CONTACT_PHONE = "010-8759-0362" 

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

LOADING_SCRIPT = """
    <script>
        window.onpageshow = function(e) { 
            if (e.persisted || (window.performance && window.performance.navigation.type === 2)) location.reload(); 
        };
        function showLoading() { document.getElementById('loading-overlay').style.display = 'flex'; }
    </script>
"""

# ==========================================
# 1. 사주 (Saju) 코드 (디자인 선명도 개선)
# ==========================================
HTML_SAJU_FORM = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>소윤의 사주타로</title>
<style>
    /* 💡 배경과 글씨 색상 대비를 높여 선명도 개선 */
    body {{ background-color: #f4e8d3; color: #222; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }}
    h1 {{ color: #b8860b; font-size: 30px; margin-bottom: 10px; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
    .welcome {{ color: #5c2e0b; font-size: 16px; margin-bottom: 30px; font-weight: 900; }}
    .form-group {{ background: #fff; border: 2px solid #d4af37; border-radius: 12px; padding: 40px 20px 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
    .input-row {{ display: flex; justify-content: center; gap: 6px; margin-bottom: 20px; }}
    /* 💡 입력창 테두리를 두껍고 진하게, 배경을 흰색으로 변경 */
    input[type="number"] {{ padding: 15px 5px; border: 3px solid #b8860b; border-radius: 10px; background: #ffffff; width: 23%; max-width: 85px; height: 55px; text-align: center; font-size: 20px; font-weight: bold; color: #000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
    input::placeholder {{ color: #888; font-weight: normal;}}
    .radio-group {{ margin-bottom: 15px; font-size: 16px; display: flex; justify-content: center; gap: 15px; font-weight: bold; color: #333; }}
    .menu-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
    button {{ background: #b8860b; color: #fff; border: none; padding: 16px; border-radius: 8px; font-weight: 700; font-size: 16px; cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.15); }}
    button:active {{ background: #5c4000; }}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.6); border-radius: 8px; font-size: 15px; color: #5c2e0b; font-weight: bold; }}
    #loading-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(244, 232, 211, 0.95); z-index: 9999; flex-direction: column; justify-content: center; align-items: center; }}
    .spinner {{ border: 6px solid #e0cda9; border-top: 6px solid #b8860b; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    .loading-text {{ color: #5c2e0b; font-size: 18px; font-weight: 900; padding: 0 20px; line-height: 1.5; word-break: keep-all; }}
    .loading-subtext {{ color: #8b4513; font-size: 15px; margin-top: 15px; font-weight: bold; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div id="loading-overlay"><div class="spinner"></div><div class="loading-text">당신의 고민과 타고난 운명의 흐름을 살펴보고 있습니다...</div><div class="loading-subtext">사주 명식을 분석 중입니다 (약 5~10초 소요)</div></div>
    <div class="container">
        <h1>🔮 소윤의 사주타로</h1><div class="welcome">환영합니다.<br>당신의 삶의 좌표를 찾아드립니다.</div>
        <form action="/saju/result" method="GET" class="form-group" onsubmit="showLoading()">
            <div class="input-row"><input type="number" name="year" placeholder="년" required><input type="number" name="month" placeholder="월" required><input type="number" name="day" placeholder="일" required><input type="number" name="hour" placeholder="시" required></div>
            <div class="radio-group"><label><input type="radio" name="calendar" value="양력" checked> 양력</label><label><input type="radio" name="calendar" value="음력"> 음력</label></div>
            <div class="radio-group"><label><input type="radio" name="gender" value="남성" checked> 남성</label><label><input type="radio" name="gender" value="여성"> 여성</label></div>
            <p style="color:#5c2e0b; font-size:15px; font-weight:bold; margin-bottom:15px;">▼ 원하시는 운세를 선택해주세요 ▼</p>
            <div class="menu-grid"><button type="submit" name="fortune_type" value="today">오늘의 운세</button><button type="submit" name="fortune_type" value="month">이달의 운세</button><button type="submit" name="fortune_type" value="year1">1년 운세</button><button type="submit" name="fortune_type" value="year5">5년 운세</button><button type="submit" name="fortune_type" value="year10">10년 운세</button><button type="submit" name="fortune_type" value="life">평생 운세</button></div>
        </form>
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#b8860b;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

HTML_SAJU_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>분석 결과</title>
<style>
    body {{ background-color: #f4e8d3; color: #222; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #b8860b; font-size: 28px; margin-bottom: 30px; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
    .result-box {{ background: #fff; padding: 25px 20px; border-radius: 12px; border: 2px solid #b8860b; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: left; }}
    .result-title {{ color: #b8860b; font-size: 20px; font-weight: 900; border-bottom: 2px dashed #d4af37; padding-bottom: 15px; text-align: center; }}
    .saju-text {{ font-size: 18px; font-weight: 900; color: #5c2e0b; margin: 20px 0; text-align: center; background: #fdf5e6; padding: 15px; border-radius: 8px; }}
    .ai-comment {{ line-height: 1.8; font-size: 16px; color: #333; font-weight: 500; }}
    .back-btn {{ display: block; margin-top: 25px; color: #5c2e0b; text-decoration: none; font-weight: 900; border: 2px solid #5c2e0b; padding: 12px; border-radius: 8px; text-align: center; background: #fff;}}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.6); border-radius: 8px; font-size: 15px; color: #5c2e0b; font-weight: bold; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div class="container">
        <h1>🔮 분석 결과</h1>
        {{result_content}}
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#b8860b;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
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
        result_html = f"""<div class="result-box"><div class="result-title">🔮 {fortune_type_kr} 분석 결과</div><div class="saju-text">사주팔자: {saju_text}</div><div class="ai-comment">{ai_comment}</div><a href="/saju?v=1" class="back-btn">← 다시 입력하기</a></div>"""
        return get_no_cache_response(HTML_SAJU_RESULT.replace("{{result_content}}", result_html))
    except Exception as e:
        return get_no_cache_response(HTML_SAJU_RESULT.replace("{{result_content}}", f"<div class='result-box'>오류: {str(e)}</div>"))

# ==========================================
# 2. 타로 (Tarot) 코드 (디자인 선명도 개선)
# ==========================================
HTML_TAROT_CATEGORY = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 고민 선택</title>
<style>
    body {{ background-color: #1a1a2e; color: #ffffff; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #e6c200; font-size: 30px; margin-bottom: 10px; font-weight: 900; text-shadow: 0 0 10px rgba(230,194,0,0.5); }}
    .welcome {{ color: #f0f0ff; font-size: 16px; margin-bottom: 30px; font-weight: bold; }}
    .category-grid {{ display: flex; flex-direction: column; gap: 15px; }}
    .category-btn {{ background: #2b2b4a; border: 2px solid #e6c200; border-radius: 12px; padding: 20px; font-size: 18px; color: #ffffff; font-weight: 900; cursor: pointer; transition: transform 0.2s; display: flex; align-items: center; justify-content: center; gap: 10px; box-shadow: 0 0 15px rgba(230,194,0,0.2); }}
    .category-btn:active {{ transform: scale(0.95); background: #3b3b5a; }}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; font-size: 15px; color: #e6c200; font-weight: bold; }}
    #loading-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(26, 26, 46, 0.95); z-index: 9999; flex-direction: column; justify-content: center; align-items: center; }}
    .spinner {{ border: 6px solid #2b2b4a; border-top: 6px solid #e6c200; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    .loading-text {{ color: #e6c200; font-size: 18px; font-weight: 900; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div id="loading-overlay"><div class="spinner"></div><div class="loading-text">카드를 준비하고 있습니다...</div></div>
    <div class="container">
        <h1>🃏 신비의 타로</h1>
        <div class="welcome">마음을 가라앉히고<br>지금 가장 궁금한 고민을 선택하세요.</div>
        <form action="/tarot/cards" method="GET" class="category-grid" onsubmit="showLoading()">
            <button type="submit" name="category" value="love" class="category-btn">💕 연애 / 관계</button>
            <button type="submit" name="category" value="career" class="category-btn">💼 직업 / 진로</button>
            <button type="submit" name="category" value="wealth" class="category-btn">💰 재물 / 금전</button>
            <button type="submit" name="category" value="health" class="category-btn">🌿 건강 / 마음</button>
        </form>
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#ffffff;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

HTML_TAROT_CARDS = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 카드 뽑기</title>
<style>
    body {{ background-color: #1a1a2e; color: #ffffff; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #e6c200; font-size: 30px; margin-bottom: 10px; font-weight: 900; text-shadow: 0 0 10px rgba(230,194,0,0.5); }}
    .welcome {{ color: #f0f0ff; font-size: 16px; margin-bottom: 40px; font-weight: bold; }}
    .card-grid {{ display: flex; justify-content: space-between; gap: 10px; margin-bottom: 30px; }}
    .tarot-card {{ background: linear-gradient(135deg, #2b2b4a, #1a1a2e); border: 2px solid #e6c200; border-radius: 12px; width: 30%; height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 4px 15px rgba(230,194,0,0.2); transition: transform 0.2s; }}
    .tarot-card:active {{ transform: scale(0.95); }}
    .card-icon {{ font-size: 40px; margin-bottom: 10px; color: #e6c200; }}
    .card-text {{ font-size: 15px; font-weight: 900; color: #ffffff;}}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; font-size: 15px; color: #e6c200; font-weight: bold; }}
    #loading-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(26, 26, 46, 0.95); z-index: 9999; flex-direction: column; justify-content: center; align-items: center; }}
    .spinner {{ border: 6px solid #2b2b4a; border-top: 6px solid #e6c200; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    .loading-text {{ color: #e6c200; font-size: 18px; font-weight: 900; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div id="loading-overlay"><div class="spinner"></div><div class="loading-text">카드의 신비로운 기운을 읽어내고 있습니다...</div></div>
    <div class="container">
        <h1>🃏 신비의 타로</h1>
        <div class="welcome">직관적으로 끌리는 카드를<br>하나 선택하세요.</div>
        <form action="/tarot/result" method="GET" onsubmit="showLoading()">
            <input type="hidden" name="category" value="{{category}}">
            <div class="card-grid">
                <button type="submit" name="card" value="1" class="tarot-card"><div class="card-icon">🌙</div><div class="card-text">1번</div></button>
                <button type="submit" name="card" value="2" class="tarot-card"><div class="card-icon">⭐</div><div class="card-text">2번</div></button>
                <button type="submit" name="card" value="3" class="tarot-card"><div class="card-icon">☀️</div><div class="card-text">3번</div></button>
            </div>
        </form>
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#ffffff;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

HTML_TAROT_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>타로 결과</title>
<style>
    body {{ background-color: #1a1a2e; color: #ffffff; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #e6c200; font-size: 28px; margin-bottom: 30px; font-weight: 900; text-shadow: 0 0 10px rgba(230,194,0,0.5); }}
    .result-box {{ background: #2b2b4a; padding: 25px 20px; border-radius: 12px; border: 2px solid #e6c200; box-shadow: 0 4px 15px rgba(230,194,0,0.2); text-align: left; }}
    .result-title {{ color: #e6c200; font-size: 20px; font-weight: 900; border-bottom: 2px dashed #e6c200; padding-bottom: 15px; text-align: center; }}
    .card-name {{ font-size: 24px; font-weight: 900; color: #ffffff; margin: 20px 0; text-align: center; text-shadow: 0 0 15px rgba(230,194,0,0.8);}}
    .ai-comment {{ line-height: 1.8; font-size: 16px; color: #f0f0ff; font-weight: 500; }}
    .back-btn {{ display: block; margin-top: 25px; color: #e6c200; text-decoration: none; font-weight: 900; border: 2px solid #e6c200; padding: 12px; border-radius: 8px; text-align: center; background: transparent;}}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; font-size: 15px; color: #e6c200; font-weight: bold; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div class="container">
        <h1>🃏 타로 리딩 결과</h1>
        {{result_content}}
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#ffffff;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

@app.get("/tarot")
async def tarot_page(): return get_no_cache_response(HTML_TAROT_CATEGORY)

@app.get("/tarot/cards")
async def tarot_cards(category: str):
    html = HTML_TAROT_CARDS.replace("{{category}}", category)
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
        result_html = f"""<div class="result-box"><div class="result-title">🔮 {category_kr} 타로 리딩</div><div class="card-name">✨ {selected_card} ✨</div><div class="ai-comment">{ai_comment}</div><a href="/tarot?v=1" class="back-btn">← 다시 뽑기</a></div>"""
        return get_no_cache_response(HTML_TAROT_RESULT.replace("{{result_content}}", result_html))
    except Exception as e:
         return get_no_cache_response(HTML_TAROT_RESULT.replace("{{result_content}}", f"<div class='result-box'>오류: {str(e)}</div>"))

# ==========================================
# 3. 궁합 (Compatibility) 코드 (디자인 선명도 개선)
# ==========================================
HTML_COMPAT_FORM = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>궁합 보기</title>
<style>
    body {{ background-color: #f4e8d3; color: #222; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #b8860b; font-size: 30px; margin-bottom: 10px; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
    .welcome {{ color: #5c2e0b; font-size: 16px; margin-bottom: 30px; font-weight: 900; }}
    .form-group {{ background: #fff; border: 2px solid #d4af37; border-radius: 12px; padding: 30px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }}
    .person-title {{ font-weight: 900; color: #5c2e0b; text-align: left; margin-bottom: 15px; font-size: 17px;}}
    .input-row {{ display: flex; justify-content: center; gap: 6px; margin-bottom: 10px; }}
    /* 💡 입력창 테두리를 두껍고 진하게, 배경을 흰색으로 변경 */
    input[type="number"] {{ padding: 15px 5px; border: 3px solid #b8860b; border-radius: 10px; background: #ffffff; width: 23%; max-width: 85px; height: 55px; text-align: center; font-size: 20px; font-weight: bold; color: #000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
    input::placeholder {{ color: #888; font-weight: normal;}}
    button {{ background: #b8860b; color: #fff; border: none; padding: 18px; border-radius: 8px; font-weight: 900; font-size: 18px; cursor: pointer; width: 100%; box-shadow: 0 3px 6px rgba(0,0,0,0.15); }}
    button:active {{ background: #5c4000; }}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.6); border-radius: 8px; font-size: 15px; color: #5c2e0b; font-weight: bold; }}
    #loading-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(244, 232, 211, 0.95); z-index: 9999; flex-direction: column; justify-content: center; align-items: center; }}
    .spinner {{ border: 6px solid #e0cda9; border-top: 6px solid #b8860b; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    .loading-text {{ color: #5c2e0b; font-size: 18px; font-weight: 900; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div id="loading-overlay"><div class="spinner"></div><div class="loading-text">두 사람의 인연과 기운을 분석하고 있습니다...</div></div>
    <div class="container">
        <h1>💑 궁합 분석</h1>
        <div class="welcome">두 사람의 케미스트리를 확인해보세요.</div>
        <form action="/compat/result" method="GET" onsubmit="showLoading()">
            <div class="form-group">
                <div class="person-title">👨 남성 (양력 기준)</div>
                <div class="input-row"><input type="number" name="m_year" placeholder="년" required><input type="number" name="m_month" placeholder="월" required><input type="number" name="m_day" placeholder="일" required><input type="number" name="m_hour" placeholder="시" required></div>
            </div>
            <div class="form-group">
                <div class="person-title">👩 여성 (양력 기준)</div>
                <div class="input-row"><input type="number" name="f_year" placeholder="년" required><input type="number" name="f_month" placeholder="월" required><input type="number" name="f_day" placeholder="일" required><input type="number" name="f_hour" placeholder="시" required></div>
            </div>
            <button type="submit">궁합 보기</button>
        </form>
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#b8860b;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

HTML_COMPAT_RESULT = f"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><title>궁합 결과</title>
<style>
    body {{ background-color: #f4e8d3; color: #222; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }}
    .container {{ max-width: 500px; margin: 0 auto; }} 
    h1 {{ color: #b8860b; font-size: 28px; margin-bottom: 30px; font-weight: 900; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
    .result-box {{ background: #fff; padding: 25px 20px; border-radius: 12px; border: 2px solid #b8860b; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: left; }}
    .result-title {{ color: #b8860b; font-size: 20px; font-weight: 900; border-bottom: 2px dashed #d4af37; padding-bottom: 15px; text-align: center; }}
    .saju-compare {{ display: flex; justify-content: space-around; margin: 20px 0; text-align: center; font-weight: 900; color: #5c2e0b; background: #fdf5e6; padding: 15px; border-radius: 8px; font-size: 16px; }}
    .ai-comment {{ line-height: 1.8; font-size: 16px; color: #333; font-weight: 500; }}
    .back-btn {{ display: block; margin-top: 25px; color: #5c2e0b; text-decoration: none; font-weight: 900; border: 2px solid #5c2e0b; padding: 12px; border-radius: 8px; text-align: center; background: #fff;}}
    .contact-info {{ margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.6); border-radius: 8px; font-size: 15px; color: #5c2e0b; font-weight: bold; }}
</style></head><body>
    {LOADING_SCRIPT}
    <div class="container">
        <h1>💑 궁합 분석 결과</h1>
        {{result_content}}
        <!-- 💡 상담 안내 문구 -->
        <div class="contact-info">📞 더 자세한 상담은 전화 <span style="color:#b8860b;">{CONTACT_PHONE}</span>으로 문의해 주세요.</div>
    </div>
</body></html>
"""

@app.get("/compat")
async def compat_page(): return get_no_cache_response(HTML_COMPAT_FORM)

@app.get("/compat/result")
async def compat_result(m_year: int, m_month: int, m_day: int, m_hour: int, f_year: int, f_month: int, f_day: int, f_hour: int):
    try:
        m_saju_res = calculate_saju(m_year, m_month, m_day, m_hour, 0)
        m_saju = f"{hanja_to_kr(m_saju_res['year_pillar'])} {hanja_to_kr(m_saju_res['month_pillar'])} {hanja_to_kr(m_saju_res['day_pillar'])} {hanja_to_kr(m_saju_res['hour_pillar'])}"
        f_saju_res = calculate_saju(f_year, f_month, f_day, f_hour, 0)
        f_saju = f"{hanja_to_kr(f_saju_res['year_pillar'])} {hanja_to_kr(f_saju_res['month_pillar'])} {hanja_to_kr(f_saju_res['day_pillar'])} {hanja_to_kr(f_saju_res['hour_pillar'])}"
        prompt = f"너는 신비로운 궁합 상담가야. 남자 사주({m_saju})와 여자 사주({f_saju})를 바탕으로 두 사람의 케미스트리와 연애/결혼 운을 5문장 이내로 따뜻하고 긍정적으로 분석해줘."
        ai_comment = get_ai_response(prompt)
        result_html = f"""<div class="result-box"><div class="result-title">케미스트리 분석</div><div class="saju-compare"><div>👨 남성<br>{m_saju}</div><div>💕</div><div>👩 여성<br>{f_saju}</div></div><div class="ai-comment">{ai_comment}</div><a href="/compat?v=1" class="back-btn">← 다시 입력하기</a></div>"""
        return get_no_cache_response(HTML_COMPAT_RESULT.replace("{{result_content}}", result_html))
    except Exception as e:
         return get_no_cache_response(HTML_COMPAT_RESULT.replace("{{result_content}}", f"<div class='result-box'>오류: {str(e)}</div>"))
