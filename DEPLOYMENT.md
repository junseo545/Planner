# 🚀 Render 배포 가이드

## 📋 사전 준비사항

### 1. GitHub 저장소 준비
- 모든 코드가 GitHub에 푸시되어 있어야 함
- `.env` 파일은 `.gitignore`에 포함되어 있어야 함

### 2. 환경변수 준비
- OpenAI API 키
- 네이버 API 키 (선택사항)

## 🔧 백엔드 배포 (Render)

### 1단계: Render 계정 생성 및 서비스 생성
1. [Render.com](https://render.com)에 가입
2. "New +" → "Web Service" 선택
3. GitHub 저장소 연결

### 2단계: 백엔드 서비스 설정
```
Name: trip-planner-backend
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 3단계: 환경변수 설정
Render 대시보드에서 다음 환경변수 추가:
```
OPENAI_API_KEY = your_openai_api_key_here
```

### 4단계: 배포
- "Create Web Service" 클릭
- 자동으로 빌드 및 배포 시작
- 배포 완료 후 제공되는 URL 복사 (예: `https://trip-planner-backend.onrender.com`)

## 🎨 프론트엔드 배포 (Render)

### 1단계: 정적 사이트 서비스 생성
1. "New +" → "Static Site" 선택
2. GitHub 저장소 연결

### 2단계: 프론트엔드 서비스 설정
```
Name: trip-planner-frontend
Build Command: npm install && npm run build
Publish Directory: build
```

### 3단계: 환경변수 설정
```
NODE_ENV = production
```

### 4단계: 배포
- "Create Static Site" 클릭
- 자동으로 빌드 및 배포 시작
- 배포 완료 후 제공되는 URL 복사

## 🔗 CORS 설정 확인

백엔드의 `main.py`에서 CORS 설정이 올바른지 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 로컬 개발용
        "https://trip-planner-frontend.onrender.com",  # Render 프론트엔드
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🚨 문제 해결

### 백엔드 배포 실패 시
1. `requirements.txt` 확인
2. Python 버전 호환성 확인
3. 환경변수 설정 확인

### 프론트엔드 배포 실패 시
1. `package.json`의 build 스크립트 확인
2. Node.js 버전 호환성 확인
3. 빌드 로그 확인

### CORS 오류 시
1. 백엔드 CORS 설정 확인
2. 프론트엔드 URL이 백엔드 CORS 허용 목록에 포함되어 있는지 확인

## 📱 배포 후 테스트

1. 프론트엔드에서 여행 계획 생성 시도
2. 백엔드 API 응답 확인
3. 호텔 검색 링크 작동 확인
4. 모바일 반응형 테스트

## 🔄 업데이트 배포

코드 수정 후:
1. GitHub에 푸시
2. Render에서 자동 재배포 (또는 수동 재배포)
3. 배포 완료 확인

## 💡 추가 최적화

### 성능 향상
- 백엔드: Redis 캐싱 추가
- 프론트엔드: 이미지 최적화, 코드 스플리팅

### 보안 강화
- API 키 환경변수 관리
- Rate limiting 추가
- HTTPS 강제 적용

### 모니터링
- Render 대시보드에서 로그 확인
- 에러 알림 설정
- 성능 메트릭 모니터링
