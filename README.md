🧾 Receipt-AI-Analyzer-MCP (v1.0)

담당자: 이현규

역할: FastAPI 백엔드 API 개발 (Azure AI 연동 및 데이터 추출)

📌 프로젝트 개요

이 프로젝트는 영수증 이미지를 입력받아, Azure AI Vision으로 텍스트를 추출(OCR)하고, **정규 표현식(RegEx)**으로 데이터를 가공하여, 구조화된 JSON 데이터를 반환하는 FastAPI 서버입니다.

[입력]: 영수증 이미지 파일, 사용자 ID

[출력]: { "category": "...", "amount": "...", "date": "..." } 형태의 JSON

✨ 주요 기능

FastAPI 서버: POST /analyze_receipt 엔드포인트 제공

Azure AI 연동: Azure AI Vision API를 호출하여 이미지에서 텍스트 추출 (OCR)

데이터 추출: 추출된 raw_text에서 정규 표현식(RegEx)을 사용해 금액, 날짜, 카테고리, 상호명 추출

자동 문서화: http://127.0.0.1:8000/docs 를 통해 API 명세(Swagger) 자동 제공

코드 분리 (리팩터링):

main.py: FastAPI 서버 로직 담당

parser.py: OCR 텍스트 분석 및 정규식 로직 담당

🚀 로컬에서 실행하는 방법

이 서버를 본인 PC에서 실행하기 위한 단계별 가이드입니다.

1. 프로젝트 다운로드 (Git Clone)

터미널(cmd)을 열고, 원하는 폴더에 이 프로젝트를 다운로드합니다.

# GitHub에서 'Receipt-AI-Analyzer-MCP'라는 이름으로 저장소를 만드세요.
git clone [여기에 본인의 GitHub 저장소 HTTPS 주소 붙여넣기]
cd Receipt-AI-Analyzer-MCP


2. 파이썬 가상 환경 생성 (권장)

프로젝트별로 라이브러리가 섞이지 않게 가상 환경을 만드는 것을 강력히 권장합니다.

# 'venv'라는 이름의 가상 환경 폴더 생성
python -m venv venv

# 가상 환경 활성화 (Windows)
.\venv\Scripts\activate


3. 필요 라이브러리 설치

requirements.txt 파일은 이 프로젝트가 사용하는 모든 라이브러리의 목록입니다. (GitHub에 푸시하기 전에 pip freeze > requirements.txt 명령어로 꼭 생성해주세요.)

pip install -r requirements.txt


4. API 키 설정 (.env 파일) (★필수★)

가장 중요한 단계입니다. 이 서버는 Azure AI Vision의 API 키가 없으면 작동하지 않습니다.

main.py 파일이 있는 최상위 폴더에 .env 라는 이름의 새 파일을 만드세요.

아래 내용을 복사/붙여넣기 한 뒤, 본인의 Azure 키 값으로 채워주세요.

(주의) .env 파일은 보안 파일이므로 절대 GitHub에 올리면 안 됩니다! (.gitignore 파일에 추가 필요)

# Azure AI Vision 리소스의 키와 엔드포인트
AZURE_VISION_KEY="여기에_Azure_키_1_값을_붙여넣으세요"
AZURE_VISION_ENDPOINT="여기에_Azure_엔드포인트_URL을_붙여넣으세요"


5. 서버 실행

모든 준비가 끝났습니다. 아래 명령어로 서버를 실행합니다.

uvicorn main:app --reload


서버가 성공적으로 켜지면, 터미널에 아래와 같은 메시지가 뜹니다.
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

🧪 API 테스트 방법 (Swagger UI)

코드를 수정할 필요 없이, 웹 브라우저에서 API 기능을 바로 테스트할 수 있습니다.

서버가 켜진 상태에서, 웹 브라우저 주소창에 아래 URL을 입력합니다.

http://127.0.0.1:8000/docs

POST /analyze_receipt 항목을 클릭해서 펼칩니다.

오른쪽의 "Try it out" 버튼을 누릅니다.

image_file 아래 "Choose File" 버튼을 눌러 테스트할 영수증 이미지를 선택합니다.

user_id 칸에는 "test_user" 처럼 임의의 ID를 입력합니다.

파란색 "Execute" 버튼을 클릭합니다.

"Server response" 섹션에서 200 코드와 함께 추출된 JSON 결과를 확인할 수 있습니다.

🐞 현재 상태 (v1.0)

[작동] 금액(amount), 날짜(date), 카테고리(category)가 테스트한 영수증 10개(구글에서 찾음)에서 잘 추출됩니다.
