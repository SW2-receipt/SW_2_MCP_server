@echo off
echo ========================================
echo Receipt AI Analyzer 서버 종료
echo ========================================
echo.

echo 서버를 종료합니다...
echo.

REM 포트 8000을 사용하는 프로세스 찾기 및 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo 프로세스 ID %%a를 종료합니다...
    taskkill /F /PID %%a >nul 2>&1
)

REM 가상환경 Python 프로세스 종료
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *venv*" >nul 2>&1

echo.
echo 서버 종료 완료!
echo.
pause


