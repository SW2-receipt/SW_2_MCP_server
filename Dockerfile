# 1. 파이썬 3.10 슬림 버전 (가벼움)
FROM python:3.10-slim

# 2. 설치 최적화 (JDK 대신 가벼운 JRE 설치, 캐시 제거)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jre-headless \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 3. 환경변수 설정
ENV JAVA_HOME="/usr/lib/jvm/default-java"

# 4. 작업 폴더
WORKDIR /app

# 5. 라이브러리 설치 (캐시 없이 가볍게)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 복사
COPY . .

# 7. 포트 8080 (클라우드 표준)
EXPOSE 8080

# 8. 실행 명령어 (8080 포트로 실행)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]