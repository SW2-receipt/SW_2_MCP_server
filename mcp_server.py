from mcp.server.fastmcp import FastMCP

# 1. 서버 정의
mcp = FastMCP("Receipt Analyzer")

# 2. 기능 정의 (실제 DB 연결 없이 텍스트만 리턴)
@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    """
    영수증 이미지를 분석합니다.
    """
    # 실제 로직(main.py)은 렌더에서 돌리고, 여기선 연결 성공 메시지만 줍니다.
    return f"✅ [Smithery] 이미지 분석 요청 수신함: {image_url}\n(실제 분석은 Render 서버에서 수행됩니다.)"

# 3. 실행 진입점
def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()