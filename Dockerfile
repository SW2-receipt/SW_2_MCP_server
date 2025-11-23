# 1. 파이썬 3.10 버전 사용
FROM python:3.10-slim

# 2. KoNLPy 구동을 위해 Java(JDK) 설치 (필수!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jdk \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 3. JAVA_HOME 환경변수 설정
ENV JAVA_HOME="/usr/lib/jvm/default-java"

# 4. 작업 폴더 설정
WORKDIR /app

# 5. 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 복사
COPY . .

# 7. 포트 열기
EXPOSE 8000

# 8. 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]