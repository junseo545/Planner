@echo off
echo ========================================
echo 여행 플래너 AI 프로젝트 설정
echo ========================================
echo.

echo 1. Python 가상환경 생성 중...
python -m venv venv
echo.

echo 2. 가상환경 활성화...
call venv\Scripts\activate.bat
echo.

echo 3. Python 패키지 설치 중...
cd backend
pip install -r requirements.txt
cd ..
echo.

echo 4. Node.js 패키지 설치 중...
cd frontend
npm install
cd ..
echo.

echo ========================================
echo 설정 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. backend 폴더에 .env 파일을 생성하고 OpenAI API 키를 설정하세요
echo 2. run_backend.bat을 실행하여 백엔드를 시작하세요
echo 3. run_frontend.bat을 실행하여 프론트엔드를 시작하세요
echo.
echo 백엔드: http://localhost:8000
echo 프론트엔드: http://localhost:3000
echo.
pause 