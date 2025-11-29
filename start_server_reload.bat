@echo off
echo ========================================
echo Receipt AI Analyzer 서버 시작 (자동 리로드)
echo ========================================
echo.
echo 서버를 자동 리로드 모드로 시작합니다.
echo Python 3.14에서 오류가 발생할 수 있습니다.
echo 오류 발생 시 start_server.bat을 사용하세요.
echo.
echo 중지하려면 Ctrl+C를 누르세요.
echo ========================================
echo.

call venv\Scripts\activate.bat
set DISABLE_KONLPY=1
REM --reload-dir 옵션을 사용하여 특정 디렉토리만 감시
venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir .

pause

