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

데이터 추출: 추출된 raw_text에서 정규 표현식(RegEx)을 사용해 금액, 날짜, 카테고리, 상호명, 품목 추출

NLP 분석 (선택사항): Azure Text Analytics를 사용한 감정 분석, 키워드 추출, 엔티티 추출

Azure SQL Database 연동 (선택사항): 영수증 분석 결과를 데이터베이스에 자동 저장 및 조회 기능

자동 문서화: http://127.0.0.1:8000/docs 또는 http://[PC의IP주소]:8000/docs 를 통해 API 명세(Swagger) 자동 제공

코드 분리 (리팩터링):

main.py: FastAPI 서버 로직 담당

parser.py: OCR 텍스트 분석 및 정규식 로직 담당

nlp_analyzer.py: Azure Text Analytics를 사용한 NLP 분석 로직 담당

db_connection.py: Azure SQL Database 연결 및 데이터 저장/조회 로직 담당

🚀 로컬에서 실행하는 방법

이 서버를 본인 PC에서 실행하기 위한 단계별 가이드입니다.

1. 프로젝트 다운로드 (Git Clone)

터미널(cmd)을 열고, 원하는 폴더에 이 프로젝트를 다운로드합니다.

# GitHub에서 'Receipt-AI-Analyzer-MCP'라는 이름으로 저장소를 만드세요.
git clone [여기에 본인의 GitHub 저장소 HTTPS 주소 붙여넣기]
cd Receipt-AI-Analyzer-MCP


2. 파이썬 가상 환경 생성 (권장)

프로젝트별로 라이브러리가 섞이지 않게 가상 환경을 만드는 것을 강력히 권장합니다.

> ✅ **KoNLPy 사용 시 Python 3.11 권장**
> - KoNLPy/JPype 조합은 Python 3.13에서 안정적으로 동작하지 않습니다.
> - 기존에 Python 3.13이 설치되어 있어도, 이 프로젝트 전용으로 Python 3.11 가상환경을 추가로 만드는 것이 가장 좋습니다.

```bash
# Windows (py 런처 사용) - 3.11이 설치되어 있어야 합니다.
py -3.11 -m venv venv

# macOS/Linux - python3.11이 설치되어 있어야 합니다.
python3.11 -m venv venv

# 가상 환경 활성화 (Windows)
.\venv\Scripts\activate

# 가상 환경 활성화 (macOS/Linux)
source venv/bin/activate
```


3. 필요 라이브러리 설치

requirements.txt 파일은 이 프로젝트가 사용하는 모든 라이브러리의 목록입니다.

```bash
pip install -r requirements.txt
```

> ℹ️ **KoNLPy 사용 시 주의**
> - `konlpy`는 Java(JDK)와 `JPype1`이 필요합니다. requirements 설치 후에도 JDK가 없다면 별도로 설치하세요.
> - Windows에서는 [Azul Zulu](https://www.azul.com/downloads/?package=jdk) 또는 Oracle JDK 설치 후 환경 변수 `JAVA_HOME`을 설정하세요.
> - macOS/Linux도 동일하게 JDK 설치가 필요합니다.


4. API 키 설정 (.env 파일) (★필수★)

가장 중요한 단계입니다. 이 서버는 Azure AI Vision의 API 키가 없으면 작동하지 않습니다.

main.py 파일이 있는 최상위 폴더에 .env 라는 이름의 새 파일을 만드세요.

아래 내용을 복사/붙여넣기 한 뒤, 본인의 Azure 키 값으로 채워주세요.

(주의) .env 파일은 보안 파일이므로 절대 GitHub에 올리면 안 됩니다! (.gitignore 파일에 추가 필요)

# Azure AI Vision 리소스의 키와 엔드포인트 (필수)
AZURE_VISION_KEY="여기에_Azure_키_1_값을_붙여넣으세요"
AZURE_VISION_ENDPOINT="여기에_Azure_엔드포인트_URL을_붙여넣으세요"

# Azure Text Analytics 리소스의 키와 엔드포인트 (선택사항 - NLP 분석용)
# NLP 분석 기능을 사용하려면 아래 값도 설정하세요
AZURE_TEXT_ANALYTICS_KEY="여기에_Text_Analytics_키_값을_붙여넣으세요"
AZURE_TEXT_ANALYTICS_ENDPOINT="여기에_Text_Analytics_엔드포인트_URL을_붙여넣으세요"

# Azure SQL Database 연결 정보 (선택사항 - 데이터 저장용)
# 영수증 분석 결과를 데이터베이스에 저장하려면 아래 값들을 설정하세요
AZURE_SQL_SERVER="여기에_서버_이름.database.windows.net"
AZURE_SQL_DATABASE="여기에_데이터베이스_이름"
AZURE_SQL_USERNAME="여기에_사용자_이름"
AZURE_SQL_PASSWORD="여기에_비밀번호"
AZURE_SQL_DRIVER="{ODBC Driver 18 for SQL Server}"


5. 서버 실행

모든 준비가 끝났습니다. 아래 명령어로 서버를 실행합니다.

**기본 실행 (로컬 네트워크 접근 가능)**:
다른 와이파이나 모바일 데이터에서도 접근 가능하게 하려면 `--host 0.0.0.0` 옵션을 추가하세요.

**방법 1: 실행 스크립트 사용 (가장 간단)**:
- **Windows**: `start_server.bat` 더블클릭 또는 명령 프롬프트에서 실행
- **Mac/Linux**: `chmod +x start_server.sh && ./start_server.sh`

**방법 2: 직접 명령어 실행**:

**Windows 사용자**:
```bash
# 네트워크 접근 허용 (권장)
uvicorn main:app --host 0.0.0.0 --port 8000

# Python 3.13에서 오류 발생 시 --reload 없이 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Linux/Mac 사용자**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**로컬에서만 접근 (127.0.0.1)**:
```bash
# Windows: start_server_local.bat 사용
# 또는 직접 실행:
uvicorn main:app --reload
```

서버가 성공적으로 켜지면, 터미널에 아래와 같은 메시지가 뜹니다.
```
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**🌐 네트워크 접근 설정**

서버를 `--host 0.0.0.0`으로 실행한 후, 다른 기기에서 접근하려면:

1. **PC의 IP 주소 확인**:
   - **Windows**: `ipconfig` 명령어 실행 후 "IPv4 주소" 확인
   - **Mac/Linux**: `ifconfig` 또는 `ip addr` 명령어 실행

2. **접근 URL**:
   - 같은 와이파이: `http://[PC의IP주소]:8000`
   - 예시: `http://192.168.0.100:8000`
   - API 문서: `http://192.168.0.100:8000/docs`

3. **방화벽 설정** (Windows):
   - Windows 방화벽에서 포트 8000을 허용해야 할 수 있습니다.
   - 제어판 > Windows Defender 방화벽 > 고급 설정 > 인바운드 규칙 > 새 규칙
   - 포트 > TCP > 8000 > 연결 허용

4. **모바일 데이터 접근**:
   - 모바일 데이터로 접근하려면 PC가 공인 IP를 가져야 하며, 라우터 포트 포워딩 설정이 필요합니다.
   - 또는 ngrok 같은 터널링 서비스를 사용할 수 있습니다.

**📱 모바일 접근 자세한 가이드**: `MOBILE_ACCESS_GUIDE.md` 파일을 참고하세요!

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

📊 데이터베이스 기능

Azure SQL Database를 연동하면 영수증 분석 결과가 자동으로 저장됩니다.

**저장되는 데이터:**
- 사용자 ID, 상호명, 카테고리, 총 금액, 구매 날짜
- 품목 목록 (품목명, 가격, 수량)
- NLP 분석 결과 (감정, 키워드, 엔티티)
- 원본 OCR 텍스트

**API 엔드포인트:**
- `GET /receipts/{user_id}`: 특정 사용자의 영수증 목록 조회
  - 예: `http://127.0.0.1:8000/receipts/test_user`
  - 쿼리 파라미터: `limit` (기본값: 100)

**ODBC 드라이버 설치:**
- Windows: [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) 다운로드 및 설치 필요
- macOS/Linux: `brew install msodbcsql18` 또는 해당 OS의 설치 방법 참고

**데이터베이스 테이블:**
서버 시작 시 자동으로 다음 테이블들이 생성됩니다:
- `receipts`: 영수증 메인 정보
- `receipt_items`: 영수증 품목 정보
- `receipt_nlp_analysis`: NLP 분석 결과

🐞 현재 상태 (v1.0)

[작동] 금액(amount), 날짜(date), 카테고리(category)가 테스트한 영수증 10개(구글에서 찾음)에서 잘 추출됩니다.

[추가됨] Azure SQL Database 연동 기능 (v1.1)
