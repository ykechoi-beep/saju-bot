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
                else: 
                    break
    return "현재 우주의 기운이 혼잡하여 분석이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."

# 💡 [캐시 방어 1] HTML 메타 태그에 캐시 금지 명령 추가
HTML_FORM = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- 💡 캐시 방지 메타 태그 -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <title>소윤의 사주타로</title>
    <style>
        body { background-color: #f4e8d3; color: #333; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { color: #b8860b; font-size: 28px; margin-bottom: 10px; font-weight: 800; }
        .welcome { color: #8b4513; font-size: 15px; margin-bottom: 30px; font-weight: 700; }
        .form-group { background: #fff; border: 2px solid #d4af37; border-radius: 12px; padding: 40px 20px 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); }
        .input-row { display: flex; justify-content: center; gap: 6px; margin-bottom: 20px; }
        input[type="number"] { padding: 15px 5px; border: 2px solid #d4af37; border-radius: 10px; background: #fafafa; width: 23%; max-width: 85px; height: 55px; text-align: center; font-size: 20px; font-weight: bold; }
        input::placeholder { color: #aaa; font-weight: normal;}
        .radio-group { margin-bottom: 15px; font-size: 15px; display: flex; justify-content: center; gap: 15px; }
        .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
        button { background: #b8860b; color: #fff; border: none; padding: 15px; border-radius: 8px; font-weight: 700; font-size: 15px; cursor: pointer; }
        button:active { background: #5c4000; }

        #loading-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(244, 232, 211, 0.95); z-index: 9999;
            flex-direction: column; justify-content: center; align-items: center;
        }
        .spinner {
            border: 6px solid #e0cda9; border-top: 6px solid #b8860b; border-radius: 50%;
            width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .loading-text { color: #8b4513; font-size: 18px; font-weight: bold; padding: 0 20px; line-height: 1.5; word-break: keep-all; }
        .loading-subtext { color: #b8860b; font-size: 14px; margin-top: 15px; }
    </style>
</head>
<body>
    <!-- 💡 [캐시 방어 2] 페이지 로드 시 강제 새로고침 스크립트 -->
    <script>
        window.onpageshow = function(event) {
            // 만약 뒤로가기나 캐시로 인해 페이지가 로드되었다면, 강제로 새로고침합니다.
            if (event.persisted || (typeof window.performance != "undefined" && window.performance.navigation.type === 2)) {
                location.reload(true); 
            }
        };
    </script>

    <div id="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">당신의 고민과 타고난 운명의 흐름을 살펴보고 있습니다...</div>
        <div class="loading-subtext">사주 명식을 분석 중입니다 (약 5~10초 소요)</div>
    </div>

    <div class="container">
        <h1>🔮 소윤의 사주타로</h1>
        <div class="welcome">환영합니다.<br>당신의 삶의 좌표를 찾아드립니다.</div>
        
        <form action="/saju/result" method="GET" class="form-group" onsubmit="showLoading()">
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
            
            <p style="color:#8b4513; font-size:14px; font-weight:bold; margin-bottom:15px;">▼ 원하시는 운세를 선택해주세요 ▼</p>
            <div class="menu-grid">
                <button type="submit" name="fortune_type" value="today">오늘의 운세</button>
                <button type="submit" name="fortune_type" value="month">이달의 운세</button>
                <button type="submit" name="fortune_type" value="year1">1년 운세</button>
                <button type="submit" name="fortune_type" value="year5">5년 운세</button>
                <button type="submit" name="fortune_type" value="year10">10년 운세</button>
                <button type="submit" name="fortune_type" value="life">평생 운세</button>
            </div>
        </form>
    </div>

    <script>
        function showLoading() {
            document.getElementById('loading-overlay').style.display = 'flex';
        }
    </script>
</body>
</html>
"""

HTML_RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- 💡 캐시 방지 메타 태그 -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <title>분석 결과</title>
    <style>
        body { background-color: #f4e8d3; color: #333; font-family: 'Malgun Gothic', sans-serif; text-align: center; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { color: #b8860b; font-size: 28px; margin-bottom: 30px; font-weight: 800; }
        .result-box { background: #fff; padding: 25px 20px; border-radius: 12px; border: 2px solid #b8860b; box-shadow: 0 4px 10px rgba(0,0,0,0.08); text-align: left; }
        .result-title { color: #b8860b; font-size: 20px; font-weight: bold; border-bottom: 2px dashed #d4af37; padding-bottom: 15px; text-align: center; }
        .saju-text { font-size: 18px; font-weight: bold; color: #8b4513; margin: 20px 0; text-align: center; background: #fdf5e6; padding: 15px; border-radius: 8px; }
        .ai-comment { line-height: 1.7; font-size: 15px; color: #444; }
        .back-btn { display: block; margin-top: 25px; color: #8b4513; text-decoration: none; font-weight: bold; border: 1px solid #8b4513; padding: 12px; border-radius: 8px; text-align: center; background: #fff;}
        .error-box { background: #ffe6e6; color: #cc0000; padding: 20px; border-radius: 8px; text-align: left; border: 1px solid #cc0000; font-size: 14px;}
    </style>
</head>
<body>
    <!-- 💡 [캐시 방어 2] 페이지 로드 시 강제 새로고침 스크립트 -->
    <script>
        window.onpageshow = function(event) {
            if (event.persisted || (typeof window.performance != "undefined" && window.performance.navigation.type === 2)) {
                location.reload(true); 
            }
        };
    </script>
    <div class="container">
        <h1>🔮 분석 결과</h1>
        {result_content}
    </div>
</body>
</html>
"""

# 💡 [캐시 방어 3] 서버 응답 헤더에 강력한 캐시 금지 명령 추가
def get_no_cache_response(html_content: str):
    response = HTMLResponse(content=html_content)
    # no-store: 아예 저장하지 마라, no-cache: 매번 서버에 물어봐라, max-age=0: 유효기간 0초
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/saju")
async def saju_page():
    # URL에 타임스탬프를 붙여서 매번 새로운 요청으로 인식하게 함 (캐시 우회)
    return get_no_cache_response(HTML_FORM)

@app.get("/saju/result")
async def saju_result(year: int, month: int, day: int, hour: int, calendar: str, gender: str, fortune_type: str):
    try:
        fortune_map = {"today": "오늘의 운세", "month": "이달의 운세", "year1": "1년 운세", "year5": "5년 운세", "year10": "10년 운세", "life": "평생 운세"}
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
            <a href="/saju?reset=true" class="back-btn">← 다시 입력하기</a>
        </div>
        """
        return get_no_cache_response(HTML_RESULT_TEMPLATE.replace("{result_content}", result_html))
        
    except Exception as e:
        traceback.print_exc()
        error_html = f"""
        <div class="error-box">
            <h3>분석 중 오류가 발생했습니다.</h3>
            <p>원인: {str(e)}</p>
            <a href="/saju?reset=true" class="back-btn" style="color:red; border-color:red;">← 돌아가기</a>
        </div>
        """
        return get_no_cache_response(HTML_RESULT_TEMPLATE.replace("{result_content}", error_html))
