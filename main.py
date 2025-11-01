from fastapi import FastAPI, File, UploadFile
import shutil
import os
from dotenv import load_dotenv  # 1. 'dotenv'에서 'load_dotenv' 함수를 임포트

# --- Azure SDK 임포트 ---
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
# -------------------------

# 2. .env 파일에서 환경 변수(API 키 등)를 불러옵니다.
load_dotenv()

# --- 3. .env에서 키와 엔드포인트를 읽어옵니다 ---
try:
    AZURE_VISION_KEY = os.environ["AZURE_VISION_KEY"]
    AZURE_VISION_ENDPOINT = os.environ["AZURE_VISION_ENDPOINT"]
except KeyError:
    print("="*50)
    print("오류: .env 파일에 AZURE_VISION_KEY와 AZURE_VISION_ENDPOINT가")
    print("정확히 설정되었는지 확인해 주세요.")
    print("="*50)
    exit()  # 서버 중지
# -----------------------------------------------

app = FastAPI()

UPLOAD_DIR = "uploads"  # 업로드 폴더

# 4. Azure 클라이언트를 준비합니다. (서버 시작 시 1회 실행)
client = ImageAnalysisClient(
    endpoint=AZURE_VISION_ENDPOINT,
    credential=AzureKeyCredential(AZURE_VISION_KEY)
)
print("Azure AI Vision 클라이언트가 성공적으로 준비되었습니다.")


@app.get("/")
def read_root():
    return {"Hello": "World", "message": "서버가 잘 작동중입니다!"}


@app.post("/analyze_receipt")
async def analyze_receipt(image_file: UploadFile = File(...)):

    # 업로드 폴더가 없으면 생성
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    
    # 1. 일단 이미지를 서버에 저장합니다.
    file_path = os.path.join(UPLOAD_DIR, image_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    # --- 2. Azure AI Vision OCR 로직 ---
    extracted_text = ""
    try:
        # 2.1 Azure로 보낼 수 있게 방금 저장한 파일을 '바이너리(rb)' 모드로 다시 읽습니다.
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        
        # 2.2 Azure API에 이미지 바이트를 전송하고 '텍스트 읽기(Read)'를 요청합니다.
        print(f"'{image_file.filename}' 파일 분석을 Azure에 요청합니다...")
        result = client.analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.READ]  # OCR(텍스트 읽기) 기능 명시
        )

        # 2.3 Azure가 분석한 결과를 'extracted_text'에 저장합니다.
        if result.read is not None:
            print("Azure OCR 분석 성공!")
            for line in result.read.blocks[0].lines:
                extracted_text += line.text + "\n"  # 한 줄씩 추가
        
    except Exception as e:
        print(f"Azure API 오류 발생: {e}")
        # 오류가 나면 프론트엔드에 오류 메시지를 보냅니다.
        return {"error": "Azure OCR 처리 중 오류 발생", "detail": str(e)}
    # ------------------------------------

    # 3. 프론트엔드에 성공 응답을 보냅니다.
    return {
        "filename": image_file.filename,
        "message": "파일 업로드 및 Azure OCR 처리 성공!",
        "extracted_text": extracted_text
    }