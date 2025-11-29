from mcp.server.fastmcp import FastMCP
import uvicorn
import os

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # 1. 클라우드(Smithery/Render)가 주는 포트가 있으면($PORT) 무조건 그걸 씁니다.
    # 2. 로컬 개발이라서 그게 없으면 8000번을 씁니다.
    # 이게 배포의 '국룰'입니다.
    port = int(os.environ.get("PORT", 8000))
    
    # 0.0.0.0으로 열어야 외부에서 접속 가능
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()