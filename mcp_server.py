from mcp.server.fastmcp import FastMCP

# 서버 이름 정의
mcp = FastMCP("Receipt Analyzer")

# 기능 정의 (초록불용 가짜 응답)
@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청을 받았습니다. (MCP 연결 성공)"

# ★ 핵심: 실행 진입점 함수 (이게 있어야 함)
def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()