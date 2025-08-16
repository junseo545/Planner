@echo off
echo 여행 플래너 AI 백엔드를 시작합니다...
cd backend
echo Python 패키지를 설치합니다...
pip install -r requirements.txt
echo.
echo FastAPI 서버를 시작합니다...
echo 서버는 http://localhost:8000 에서 실행됩니다
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause 