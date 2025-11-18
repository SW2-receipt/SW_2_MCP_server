#!/bin/bash

echo "========================================"
echo "Receipt AI Analyzer 서버 시작"
echo "========================================"
echo ""
echo "서버를 네트워크 접근 가능 모드로 시작합니다."
echo "다른 와이파이/모바일 데이터에서도 접근 가능합니다."
echo ""
echo "중지하려면 Ctrl+C를 누르세요."
echo "========================================"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

