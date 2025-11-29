from mcp.server.fastmcp import FastMCP
import uvicorn

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # 서버는 문을 활짝 열어둡니다 (0.0.0.0)
    uvicorn.run(mcp._sse_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()