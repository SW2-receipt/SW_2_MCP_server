@echo off
echo ========================================
echo Receipt AI Analyzer 서버 재시작
echo ========================================
echo.

echo 기존 서버를 종료합니다...
call stop_server.bat

echo.
echo 2초 대기 중...
timeout /t 2 /nobreak >nul

echo.
echo 서버를 시작합니다...
call start_server.bat


