# 여행 플래너 AI 에이전트

사용자가 지역과 날짜를 입력하면 AI가 추천 코스와 숙박 링크를 제공하는 웹사이트입니다.

## 기능
- 지역 및 날짜 기반 여행 계획 생성
- AI 기반 맞춤형 여행 코스 추천
- 숙박 시설 링크 제공
- 반응형 웹 디자인

## 기술 스택
- **Frontend**: React.js + TypeScript + Vite
- **Backend**: FastAPI (Python)
- **AI**: OpenAI GPT API
- **Styling**: Tailwind CSS

## 설치 및 실행

### 백엔드 (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 프론트엔드 (React + TypeScript + Vite)
```bash
cd frontend
npm install
npm run dev
```

## 환경 변수 설정
`.env` 파일에 다음 API 키들을 설정하세요:

### 필수 설정
```
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here
```

### 선택적 설정 (위치 검증 기능)
```
# 네이버 클라우드 플랫폼 Maps API 키 (위치 검증용)
# https://www.ncloud.com/product/applicationService/maps 에서 발급
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here

# 기존 위치 검증 활성화 여부 (true/false)
ENABLE_LOCATION_VALIDATION=false

# 네이버 지오코딩 검증 활성화 여부 (true/false)
# false로 설정하면 지오코딩 검증을 완전히 비활성화
ENABLE_GEOCODING_VALIDATION=true

# 실제 장소 정보 추가 활성화 여부 (true/false)
# 네이버 검색 API를 사용해 실제 주소, 전화번호 등을 가져옴
ENABLE_PLACE_ENHANCEMENT=true
```

### 위치 검증 및 실제 장소 정보 기능 안내

#### 🔍 위치 검증 기능
- 네이버 지오코딩 API를 사용하여 여행 일정의 장소들이 실제로 요청한 지역에 있는지 검증
- 부산 여행을 요청했는데 강릉 장소가 나오는 것을 방지
- API 키가 없어도 기본 기능은 정상 작동하지만, 위치 검증은 제한됨

#### 📍 실제 장소 정보 기능
- 네이버 검색 API를 사용하여 각 활동에 실제 장소 정보 추가
- **실제 주소**: 정확한 도로명 주소 표시
- **카테고리**: 관광지, 맛집, 카페 등 장소 분류
- **전화번호**: 해당 장소의 연락처 (있는 경우)
- **녹색 텍스트**: 장소명 아래에 실제 주소가 초록색으로 표시

### 빠른 해결 방법 (API 키 없이 사용)
지오코딩 검증으로 인해 일정이 비어있다면 다음 환경 변수를 설정하세요:
```bash
# 윈도우 (PowerShell)
$env:ENABLE_GEOCODING_VALIDATION="false"

# 맥/리눅스 (Bash)
export ENABLE_GEOCODING_VALIDATION=false
```

또는 `.env` 파일에 추가:
```
ENABLE_GEOCODING_VALIDATION=false
```

## TypeScript 지원
이 프로젝트는 TypeScript를 사용하여 타입 안정성을 제공합니다:
- 모든 React 컴포넌트는 `.tsx` 확장자 사용
- 공통 타입 정의는 `src/types/index.ts`에 집중
- 엄격한 타입 검사로 런타임 오류 방지

## Vite 마이그레이션
- React Scripts에서 Vite로 마이그레이션 완료
- 더 빠른 개발 서버 및 빌드 성능
- Hot Module Replacement (HMR) 지원
- 최신 ES 모듈 기반 빌드 시스템 