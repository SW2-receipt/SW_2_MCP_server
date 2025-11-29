from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청을 받았습니다. (MCP 연결 성공)"

# [중요] 함수로 감싸야 pyproject.toml에서 실행할 수 있습니다.
def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()