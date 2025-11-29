from mcp.server.fastmcp import FastMCP
import uvicorn
import os  # <--- 1. 이 줄 추가

mcp = FastMCP("Receipt Analyzer")

@mcp.tool()
def analyze_receipt(image_url: str) -> str:
    return f"이미지({image_url}) 분석 요청 받음 (성공)"

def main():
    # <--- 2. 포트 설정 부분을 이렇게 바꾸세요!
    # 렌더가 PORT 환경변수를 주면 그걸 쓰고, 없으면(스미더리/로컬) 8000을 씁니다.
    port = int(os.environ.get("PORT", 8000))
    
    # host는 0.0.0.0 유지, port는 변수로 변경
    uvicorn.run(mcp._sse_app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()