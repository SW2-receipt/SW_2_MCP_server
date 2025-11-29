from mcp.server.fastmcp import FastMCP
import uvicorn

# 1. 서버 정의
mcp = FastMCP("Receipt Analyzer")

# 2. 기능 정의 (초록불용)
@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청을 받았습니다. (MCP 연결 성공)"

# 3. ★핵심 수정★: 채팅 모드(stdio)를 버리고, 웹 서버(uvicorn)를 강제로 띄웁니다.
def main():
    # 스미더리 스캐너가 좋아하는 8000번 포트를 엽니다.
    # mcp._sse_app은 내부적으로 숨겨진 웹 서버 기능입니다.
    uvicorn.run(mcp._sse_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()