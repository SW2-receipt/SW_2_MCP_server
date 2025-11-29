from mcp.server.fastmcp import FastMCP
import uvicorn
import os

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # [핵심 로직 변경]
    # 1. Render 환경일 때만: 렌더가 주는 동적 포트 사용
    if os.environ.get("RENDER"):
        port = int(os.environ.get("PORT"))
    # 2. Smithery 및 로컬 환경일 때: 설정파일과 맞춘 8000번 강제 고정
    else:
        port = 8000
    
    # 0.0.0.0으로 열어야 외부 접속이 가능합니다.
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()