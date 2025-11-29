from mcp.server.fastmcp import FastMCP

# 스미더리에게 보여줄 서버 이름 정의
mcp = FastMCP("Receipt Analyzer")

# 스미더리가 "너 뭐 할 줄 알아?" 물어보면 대답할 기능
@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    """
    영수증 이미지 URL을 받아서 분석합니다.
    """
    # 실제 로직 연결은 나중에 하고, 일단 초록불을 위해 응답만 줍니다.
    return f"이미지({image_url}) 분석 요청을 받았습니다. (MCP 연결 성공)"

if __name__ == "__main__":
    # 스미더리 방식(stdio)으로 실행
    mcp.run(transport="stdio")