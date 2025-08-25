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
`.env` 파일에 OpenAI API 키를 설정하세요:
```
OPENAI_API_KEY=your_api_key_here
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