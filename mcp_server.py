from mcp.server.fastmcp import FastMCP
import uvicorn
import os

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # 문제 해결의 핵심:
    # Render든 Smithery든 로컬이든, 환경변수 'PORT'가 있으면 무조건 그걸 씁니다.
    # 없으면(로컬 개발 등) 8000을 씁니다.
    port = int(os.environ.get("PORT", 8000))
    
    # 0.0.0.0으로 열어서 외부 접속을 허용하고, 위에서 정한 포트를 사용합니다.
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()