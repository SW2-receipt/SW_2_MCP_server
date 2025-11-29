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
REM Python 3.14에서 --reload 옵션은 multiprocessing 오류를 발생시킬 수 있습니다
REM 오류가 발생하면 아래 줄의 --reload를 제거하세요
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000

pause

