from fastapi import FastAPI

# 1. FastAPI 앱(app)을 만듭니다.
app = FastAPI()

# 2. 브라우저가 '/' (기본 주소)로 접속하면
@app.get("/")
def read_root():
    # 3. 이 메시지를 반환합니다.
    return {"Hello": "World"}