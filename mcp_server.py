from mcp.server.fastmcp import FastMCP
import uvicorn
import os

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # 기본값은 8000 (Smithery, 로컬용)
    port = 8000
    
    # 만약 'RENDER'라는 환경변수가 있다면, Render가 주는 포트를 씁니다.
    if os.environ.get("RENDER"):
        port = int(os.environ.get("PORT", 10000))
    
    # 그 외(Smithery)에는 무조건 8000번으로 고정하여 설정 파일과 맞춥니다.
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()