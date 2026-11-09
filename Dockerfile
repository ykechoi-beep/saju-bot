# Hugging Face Spaces는 7860번 포트를 사용합니다.
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 보안을 위해 일반 사용자(user)로 실행합니다. (Hugging Face 권장 사항)
RUN useradd -m -u 1000 user
USER user

# FastAPI 서버를 7860번 포트로 실행합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
