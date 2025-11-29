from mcp.server.fastmcp import FastMCP
import uvicorn
import os

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    port = int(os.environ.get("PORT", 8000))
    # 수정: mcp._sse_app -> mcp.sse_app (언더바 제거!)
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()