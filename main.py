from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import shutil
import os
from dotenv import load_dotenv
from typing import Optional

# --- Azure SDK 임포트 ---
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
# -------------------------

# --- Parser 모듈 임포트 ---
from parser import parse_receipt, categorize_receipt
# -------------------------

load_dotenv()

try:
    AZURE_VISION_KEY = os.environ["AZURE_VISION_KEY"]
    AZURE_VISION_ENDPOINT = os.environ["AZURE_VISION_ENDPOINT"]
except KeyError:
    print("="*50)
    print("오류: .env 파일에 AZURE_VISION_KEY와 AZURE_VISION_ENDPOINT가")
    print("정확히 설정되었는지 확인해 주세요.")
    print("="*50)
    exit()

app = FastAPI()

UPLOAD_DIR = "uploads"

client = ImageAnalysisClient(
    endpoint=AZURE_VISION_ENDPOINT,
    credential=AzureKeyCredential(AZURE_VISION_KEY)
)

print("Azure AI Vision 클라이언트가 성공적으로 준비되었습니다.")


@app.get("/")
def read_root():
    return {"Hello": "World", "message": "서버가 잘 작동중입니다!"}


@app.post("/analyze_receipt")
async def analyze_receipt(
    image_file: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    """
    영수증 이미지를 분석하여 구조화된 정보를 추출합니다.
    
    Args:
        image_file: 영수증 이미지 파일
        user_id: 사용자 ID 또는 User Token (데이터베이스 저장용)
    
    Returns:
        JSON 응답: 카테고리, 금액, 날짜, 상태 코드
    """
    
    # 사용자 ID 검증 (옵셔널이지만 명세서 요구사항)
    if not user_id:
        user_id = "anonymous"  # 기본값
    
    status_code = 200  # 성공 상태 코드
    
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    
    file_path = os.path.join(UPLOAD_DIR, image_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    extracted_text = ""
    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        
        print(f"'{image_file.filename}' 파일 분석을 Azure에 요청합니다... (User ID: {user_id})")
        result = client.analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.READ]
        )

        if result.read is not None:
            print("Azure OCR 분석 성공!")
            for line in result.read.blocks[0].lines:
                extracted_text += line.text + "\n"
        else:
            status_code = 400
            raise Exception("OCR 결과가 없습니다.")
        
    except Exception as e:
        print(f"Azure API 오류 발생: {e}")
        status_code = 500
        raise HTTPException(status_code=status_code, detail=f"Azure OCR 처리 중 오류 발생: {str(e)}")

    # --- 3. 정규식(RegEx)으로 정보 추출 ---
    # parser.py에 있는 함수 하나만 호출!
    parsed_data = parse_receipt(extracted_text)
    
    # --- 4. 카테고리 분류 ---
    category = categorize_receipt(extracted_text, parsed_data.get("store_name"))
    
    # (디버깅) 터미널에 추출 결과를 출력
    print("--- 정규식 추출 결과 ---")
    print(f"사용자 ID: {user_id}")
    print(f"상호명: {parsed_data.get('store_name')}")
    print(f"날짜: {parsed_data.get('normalized_date')}")
    print(f"금액: {parsed_data.get('total_price')}")
    print(f"카테고리: {category}")
    print(f"상태 코드: {status_code}")
    print("------------------------")
    
    # 금액이 추출되지 않았을 경우 디버깅 정보 출력
    if not parsed_data.get('total_price'):
        print("⚠️ 금액 추출 실패 - 추출된 텍스트 일부:")
        print(extracted_text[:1000] if len(extracted_text) > 1000 else extracted_text)
        print("...")
        lines_debug = extracted_text.split('\n')
        print("'합계' 키워드가 포함된 줄들:")
        for i_debug, line_debug in enumerate(lines_debug):
            if '합계' in line_debug or '총구매액' in line_debug or '총금액' in line_debug:
                print(f"   Line {i_debug}: {line_debug.strip()}")

    # ------------------------------------
    # 명세서에 맞는 응답 형식: 카테고리, 금액, 날짜, 상태 코드
    return {
        "category": category,
        "amount": parsed_data.get("total_price"),
        "date": parsed_data.get("normalized_date"),
        "status_code": status_code,
        "user_id": user_id,  # 디버깅용
        "store_name": parsed_data.get("store_name")  # 추가 정보
    }