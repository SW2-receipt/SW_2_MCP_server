@echo off
echo ========================================
echo Receipt AI Analyzer 서버 시작 (로컬 전용)
echo ========================================
echo.
echo 서버를 로컬 전용 모드로 시작합니다.
echo 127.0.0.1에서만 접근 가능합니다.
echo.
echo 중지하려면 Ctrl+C를 누르세요.
echo ========================================
echo.

call venv\Scripts\activate.bat
set DISABLE_KONLPY=1
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause

