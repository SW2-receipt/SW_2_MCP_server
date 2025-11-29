FROM python:3.10-slim

# 1. 필수 프로그램 설치 (기존 유지)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jre-headless \
    g++ \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME="/usr/lib/jvm/default-java"
WORKDIR /app

# 2. 패키지 설치 (혹시 모르니 mcp 관련 패키지 명시적 설치 추가)
COPY requirements.txt .
# 만약 requirements_mcp.txt가 있다면 주석 해제해서 사용하세요
# COPY requirements_mcp.txt . 
# RUN pip install --no-cache-dir -r requirements_mcp.txt

# 필수 라이브러리 확실하게 설치 (fastapi, uvicorn, mcp)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install "mcp[cli]" fastapi uvicorn

COPY . .

# 3. ★여기가 핵심 수정 사항입니다★
# 스미더리는 8000 포트를 보고 있습니다.
EXPOSE 8000

# main:app 대신 mcp_server.py를 파이썬으로 직접 실행합니다.
# (mcp_server.py 안에 uvicorn 실행 코드가 이미 들어있기 때문입니다)
CMD ["python", "mcp_server.py"]