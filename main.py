from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import sys
import re
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

# --- 데이터베이스 모듈 임포트 ---
from db_connection import db
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
    expose_headers=["*"],  # 모든 헤더 노출
)

# 모바일 브라우저 호환성을 위한 추가 설정
@app.middleware("http")
async def log_requests(request, call_next):
    """요청 로깅 및 디버깅용 미들웨어"""
    print(f"[요청] {request.method} {request.url}")
    print(f"[헤더] {dict(request.headers)}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print(f"[오류] {e}")
        raise

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

# 데이터베이스 테이블 초기화 (서버 시작 시)
print("\n" + "="*50)
print("데이터베이스 초기화 중...")
if db.connection_string:
    db.create_tables()
    print("✅ 데이터베이스 준비 완료")
else:
    print("⚠️ 데이터베이스 연결 정보가 없습니다. 저장 기능이 비활성화됩니다.")
    print("   (선택사항: .env에 Azure SQL Database 연결 정보 추가)")
print("="*50 + "\n")


@app.get("/")
def read_root():
    return {"Hello": "World", "message": "서버가 잘 작동중입니다!"}

@app.get("/test")
def test_connection():
    """연결 테스트용 엔드포인트"""
    return {
        "status": "success",
        "message": "서버 연결 성공!",
        "server": "Receipt AI Analyzer"
    }


@app.get("/receipts/{user_id}")
def get_user_receipts(user_id: str, limit: int = 100):
    """
    사용자 ID로 영수증 목록을 조회하는 엔드포인트
    
    Args:
        user_id: 사용자 ID
        limit: 최대 조회 개수 (기본값: 100)
    
    Returns:
        영수증 목록 JSON
    """
    if not db.connection_string:
        raise HTTPException(
            status_code=503,
            detail="데이터베이스 연결이 설정되지 않았습니다."
        )
    
    receipts = db.get_receipts_by_user(user_id, limit)
    return {
        "user_id": user_id,
        "count": len(receipts),
        "receipts": receipts
    }


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
    print(f"\n{'='*50}")
    print(f"[영수증 분석 요청 시작]")
    print(f"파일명: {image_file.filename}")
    print(f"Content-Type: {image_file.content_type}")
    print(f"User ID: {user_id or 'anonymous'}")
    print(f"{'='*50}\n")
    
    # 사용자 ID 검증 (옵셔널이지만 명세서 요구사항)
    if not user_id:
        user_id = "anonymous"  # 기본값
    
    status_code = 200  # 성공 상태 코드
    
    try:
        # 업로드 디렉토리 확인
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
        
        # 파일 저장
        print(f"[1/5] 파일 저장 시작...")
        file_path = os.path.join(UPLOAD_DIR, image_file.filename or "receipt.jpg")
        
        # 파일 크기 확인 (최대 10MB)
        file_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await image_file.read(8192)  # 8KB씩 읽기
                if not chunk:
                    break
                buffer.write(chunk)
                file_size += len(chunk)
                if file_size > 10 * 1024 * 1024:  # 10MB 제한
                    os.remove(file_path)
                    raise HTTPException(status_code=413, detail="파일 크기가 10MB를 초과합니다.")
        
        print(f"[1/5] 파일 저장 완료 (크기: {file_size / 1024:.2f} KB)")
        
        # 파일 포인터를 처음으로 되돌림
        await image_file.seek(0)

        # 이미지 바이트 읽기
        print(f"[2/5] 이미지 파일 읽기...")
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        print(f"[2/5] 이미지 파일 읽기 완료 ({len(image_bytes)} bytes)")
        
        # Azure OCR 분석
        extracted_text = ""
        print(f"[3/5] Azure OCR 분석 시작...")
        result = client.analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.READ]
        )

        if result.read is not None:
            print(f"[3/5] Azure OCR 분석 성공!")
            for line in result.read.blocks[0].lines:
                extracted_text += line.text + "\n"
            print(f"[3/5] 추출된 텍스트 길이: {len(extracted_text)} 문자")
        else:
            status_code = 400
            raise Exception("OCR 결과가 없습니다.")
        
        # --- 3. 정규식(RegEx)으로 정보 추출 ---
        print(f"[4/5] 정규식으로 정보 추출 시작...")
        parsed_data = parse_receipt(extracted_text)
        print(f"[4/5] 정보 추출 완료")
        
        # --- 4. 카테고리 분류 ---
        category = categorize_receipt(extracted_text, parsed_data.get("store_name"))
        print(f"[4/5] 카테고리: {category}")
        
        # --- 5. NLP 분석 (Azure Text Analytics) ---
        print(f"[5/5] NLP 분석 시작...")
        nlp_result = analyze_text_with_nlp(extracted_text, text_analytics_client)
        insights = extract_receipt_insights(nlp_result, parsed_data)
        print(f"[5/5] NLP 분석 완료")
        
        # 추출 결과 요약 출력
        print(f"\n[추출 결과] 상호명: {parsed_data.get('store_name')}, 금액: {parsed_data.get('total_price')}원, 카테고리: {category}")

        # ------------------------------------
        # 명세서에 맞는 응답 형식: 카테고리, 금액, 날짜, 상태 코드
        # 품목 데이터 정리 (가격이 0이거나 None인 경우 제외)
        items_cleaned = []
        for item in parsed_data.get("items", []):
            item_name = item.get("name", "").strip()
            item_price = item.get("price")
            
            # 품목명 끝에 붙은 숫자 제거 (가격이 0인 경우)
            if item_name and re.search(r'[가-힣A-Za-z]', item_name):
                # 끝에 붙은 숫자 패턴 제거 (예: "WOW새우진짬뽕0" -> "WOW새우진짬뽕")
                item_name = re.sub(r'(\d+)$', '', item_name).strip()
            
            # 가격이 유효한 경우만 포함 (0이 아니고 None이 아닌 경우)
            if item_price and item_price != "0" and item_price != "0원" and str(item_price).strip() != "":
                try:
                    # 가격이 숫자인지 확인
                    price_num = float(str(item_price).replace(",", ""))
                    if price_num > 0:
                        items_cleaned.append({
                            "name": item_name,
                            "price": str(item_price),  # 문자열로 명시적 변환
                            "quantity": item.get("quantity") or None
                        })
                    else:
                        print(f"[경고] 가격이 0인 품목 제외: {item_name} - 가격: {item_price}")
                except:
                    print(f"[경고] 가격 파싱 실패, 품목 제외: {item_name} - 가격: {item_price}")
            else:
                # 가격이 0이거나 없는 경우 제외 (디버깅 정보만 출력)
                print(f"[경고] 가격이 0이거나 없는 품목 제외: {item_name} - 가격: {item_price}")
        
        response_data = {
            "category": category,
            "amount": parsed_data.get("total_price") or "0",
            "date": parsed_data.get("normalized_date"),
            "status_code": status_code,
            "user_id": user_id,  # 디버깅용
            "store_name": parsed_data.get("store_name"),  # 추가 정보
            "items": items_cleaned,  # 정리된 품목 리스트
            "items_count": len(items_cleaned),  # 품목 개수 추가
            "nlp_analysis": {  # NLP 분석 결과
                "sentiment": nlp_result.get("sentiment"),
                "key_phrases": nlp_result.get("key_phrases", [])[:10],  # 상위 10개만
                "entities": nlp_result.get("entities", [])[:10],  # 상위 10개만
                "insights": insights
            } if text_analytics_client else None
        }
        
        print(f"[분석 완료] 총 {response_data.get('items_count')}개 품목, 금액: {response_data.get('amount')}원\n")
        
        # 데이터베이스에 저장
        if db.connection_string:
            try:
                receipt_db_data = {
                    "user_id": user_id,
                    "store_name": parsed_data.get("store_name"),
                    "category": category,
                    "amount": parsed_data.get("total_price") or "0",
                    "date": parsed_data.get("normalized_date"),
                    "status_code": status_code,
                    "items": items_cleaned,
                    "items_count": len(items_cleaned),
                    "image_filename": image_file.filename or "receipt.jpg",
                    "extracted_text": extracted_text[:4000],  # 텍스트 길이 제한
                    "nlp_analysis": response_data.get("nlp_analysis")
                }
                receipt_id = db.save_receipt(receipt_db_data)
                if receipt_id:
                    response_data["receipt_id"] = receipt_id
                    print(f"✅ 데이터베이스 저장 완료 (Receipt ID: {receipt_id})")
                else:
                    print("⚠️ 데이터베이스 저장 실패 (응답은 정상 반환)")
            except Exception as e:
                print(f"⚠️ 데이터베이스 저장 중 오류 발생: {e}")
                print("   (응답은 정상 반환)")
        else:
            print("ℹ️ 데이터베이스 연결 정보가 없어 저장하지 않습니다.")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[치명적 오류] {e}")
        import traceback
        traceback.print_exc()
        # 파일 정리
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")