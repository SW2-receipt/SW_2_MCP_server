@echo off
echo ========================================
echo 빠른 연결 테스트
echo ========================================
echo.

echo [1] PC의 IP 주소:
ipconfig | findstr /i "IPv4"
echo.

echo [2] 서버 실행 확인:
echo - 서버가 실행 중인지 확인하세요
echo - 명령어: uvicorn main:app --host 0.0.0.0 --port 8000
echo.

echo [3] PC에서 테스트:
echo 브라우저에서 http://127.0.0.1:8000/test 접속
echo.

echo [4] 모바일에서 테스트:
echo 브라우저에서 http://[위의IPv4주소]:8000/test 접속
echo.

pause

