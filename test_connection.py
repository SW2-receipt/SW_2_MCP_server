"""
간단한 연결 테스트 서버
모바일에서 이 엔드포인트를 호출해서 연결이 되는지 확인
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test")
def test_connection():
    """연결 테스트용 엔드포인트"""
    return {
        "status": "success",
        "message": "서버 연결 성공!",
        "server": "Receipt AI Analyzer"
    }

@app.post("/test")
def test_post():
    """POST 요청 테스트용"""
    return {
        "status": "success",
        "message": "POST 요청 성공!",
        "method": "POST"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

