from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import sys
from dotenv import load_dotenv
from typing import Optional

# Windows에서 multiprocessing 호환성 문제 해결
if sys.platform == 'win32':
    import multiprocessing
    multiprocessing.freeze_support()

# --- Azure SDK 임포트 ---
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
# -------------------------

# --- Parser 모듈 임포트 ---
from parser import parse_receipt, categorize_receipt
from nlp_analyzer import analyze_text_with_nlp, extract_receipt_insights
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

# Text Analytics 설정 (선택사항)
AZURE_TEXT_ANALYTICS_KEY = os.environ.get("AZURE_TEXT_ANALYTICS_KEY")
AZURE_TEXT_ANALYTICS_ENDPOINT = os.environ.get("AZURE_TEXT_ANALYTICS_ENDPOINT")

# 엔드포인트 URL 정리 (끝에 슬래시 제거)
AZURE_VISION_ENDPOINT = AZURE_VISION_ENDPOINT.strip().rstrip('/')
AZURE_VISION_KEY = AZURE_VISION_KEY.strip()

if AZURE_TEXT_ANALYTICS_ENDPOINT:
    AZURE_TEXT_ANALYTICS_ENDPOINT = AZURE_TEXT_ANALYTICS_ENDPOINT.strip().rstrip('/')
if AZURE_TEXT_ANALYTICS_KEY:
    AZURE_TEXT_ANALYTICS_KEY = AZURE_TEXT_ANALYTICS_KEY.strip()

# 디버깅용 출력 (키는 일부만 표시)
print("="*50)
print("Azure 설정 확인:")
print(f"Vision 엔드포인트: {AZURE_VISION_ENDPOINT}")
print(f"Vision 키 (처음 10자리): {AZURE_VISION_KEY[:10]}...")
if AZURE_TEXT_ANALYTICS_ENDPOINT:
    print(f"Text Analytics 엔드포인트: {AZURE_TEXT_ANALYTICS_ENDPOINT}")
    print(f"Text Analytics 키 (처음 10자리): {AZURE_TEXT_ANALYTICS_KEY[:10]}...")
else:
    print("Text Analytics: 설정되지 않음 (선택사항)")
print("="*50)

app = FastAPI()

# CORS 설정 - UI에서 백엔드 API를 호출할 수 있도록 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 출처 허용 (프로덕션에서는 특정 도메인 지정 권장)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

UPLOAD_DIR = "uploads"

client = ImageAnalysisClient(
    endpoint=AZURE_VISION_ENDPOINT,
    credential=AzureKeyCredential(AZURE_VISION_KEY)
)

print("Azure AI Vision 클라이언트가 성공적으로 준비되었습니다.")

# Text Analytics 클라이언트 초기화 (선택사항)
text_analytics_client = None
if AZURE_TEXT_ANALYTICS_KEY and AZURE_TEXT_ANALYTICS_ENDPOINT:
    try:
        text_analytics_client = TextAnalyticsClient(
            endpoint=AZURE_TEXT_ANALYTICS_ENDPOINT,
            credential=AzureKeyCredential(AZURE_TEXT_ANALYTICS_KEY)
        )
        print("Azure Text Analytics 클라이언트가 성공적으로 준비되었습니다.")
    except Exception as e:
        print(f"⚠️ Text Analytics 클라이언트 초기화 실패: {e}")
        print("NLP 분석 없이 계속 진행합니다.")
else:
    print("⚠️ Text Analytics 설정이 없습니다. NLP 분석 기능이 비활성화됩니다.")
    print("   (선택사항: .env에 AZURE_TEXT_ANALYTICS_KEY와 AZURE_TEXT_ANALYTICS_ENDPOINT 추가)")


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
    
    # --- 5. NLP 분석 (Azure Text Analytics) ---
    nlp_result = analyze_text_with_nlp(extracted_text, text_analytics_client)
    insights = extract_receipt_insights(nlp_result, parsed_data)
    
    # (디버깅) 터미널에 추출 결과를 출력
    print("--- 정규식 추출 결과 ---")
    print(f"사용자 ID: {user_id}")
    print(f"상호명: {parsed_data.get('store_name')}")
    print(f"날짜: {parsed_data.get('normalized_date')}")
    print(f"금액: {parsed_data.get('total_price')}")
    print(f"카테고리: {category}")
    items = parsed_data.get('items', [])
    if items:
        print(f"품목 수: {len(items)}개")
        for i, item in enumerate(items[:5], 1):  # 최대 5개만 출력
            print(f"  {i}. {item.get('name')}: {item.get('price')}원" + 
                  (f" (수량: {item.get('quantity')})" if item.get('quantity') else ""))
    
    # NLP 분석 결과 출력
    if text_analytics_client and nlp_result.get("sentiment"):
        print(f"NLP 분석 - 감정: {nlp_result.get('sentiment')}")
        if nlp_result.get("key_phrases"):
            print(f"NLP 분석 - 주요 키워드: {', '.join(nlp_result.get('key_phrases', [])[:5])}")
    
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
        "store_name": parsed_data.get("store_name"),  # 추가 정보
        "items": parsed_data.get("items", []),  # 품목 리스트
        "nlp_analysis": {  # NLP 분석 결과
            "sentiment": nlp_result.get("sentiment"),
            "key_phrases": nlp_result.get("key_phrases", [])[:10],  # 상위 10개만
            "entities": nlp_result.get("entities", [])[:10],  # 상위 10개만
            "insights": insights
        } if text_analytics_client else None
    }