FROM python:3.10-slim

# 1. 필수 프로그램 설치 (Java + ★ODBC 드라이버 추가★)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jre-headless \
    g++ \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME="/usr/lib/jvm/default-java"
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 스미더리용 포트 설정 (8000)
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]