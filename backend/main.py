# ========================================
# 여행 플래너 AI 백엔드 서버
# ========================================
# 이 파일은 여행 계획을 AI로 생성하고 호텔 정보를 제공하는 웹 서버입니다.
# FastAPI 프레임워크를 사용하여 만들어졌습니다.

# 필요한 라이브러리들을 가져옵니다 (import)
from fastapi import FastAPI, HTTPException  # FastAPI: 웹 서버 프레임워크, HTTPException: 에러 처리용
from fastapi.middleware.cors import CORSMiddleware  # CORS: 웹 브라우저의 보안 정책 관련
from pydantic import BaseModel  # 데이터 검증을 위한 라이브러리
from typing import List, Optional  # 타입 힌트를 위한 라이브러리
import openai  # OpenAI API 사용을 위한 라이브러리
import os  # 운영체제 관련 기능 (환경변수 등)
from dotenv import load_dotenv  # .env 파일에서 환경변수를 로드하는 라이브러리
import json  # JSON 데이터 처리용
import logging  # 로그 기록용
from datetime import datetime, timedelta  # 날짜와 시간 처리용
import urllib.parse  # URL 인코딩용


import requests
import json

load_dotenv()

# 네이버 API 인증키
client_id = "W9FDHYIV6V8_B7jxUJoj"
client_secret = "bZ9RDTBZ0h"


query = "부산 축제"

headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret
}

# 1. 뉴스 검색
news_url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=3&sort=date"
news_res = requests.get(news_url, headers=headers).json()

print("=== 뉴스 검색 결과 ===")
for item in news_res['items']:
    print(item['title'])
    print(item['link'])
    print(item['pubDate'])
    print("-" * 40)

# 2. 블로그 검색
blog_url = f"https://openapi.naver.com/v1/search/blog.json?query={query}&display=3&sort=date"
blog_res = requests.get(blog_url, headers=headers).json()

print("\n=== 블로그 검색 결과 ===")
for item in blog_res['items']:
    print(item['title'])
    print(item['link'])
    print("-" * 40)

# 3. 웹문서 검색
web_url = f"https://openapi.naver.com/v1/search/webkr.json?query={query}&display=3&sort=date"
web_res = requests.get(web_url, headers=headers).json()

print("\n=== 웹문서 검색 결과 ===")
for item in web_res['items']:
    print(item['title'])
    print(item['link'])
    print("-" * 40)


# ========================================
# 로깅 설정 (로그: 프로그램 실행 과정을 기록하는 것)
# ========================================
logging.basicConfig(level=logging.INFO)  # INFO 레벨 이상의 로그를 모두 기록
logger = logging.getLogger(__name__)  # 현재 파일의 로거를 생성

# ========================================
# 환경 변수 설정
# ========================================
# .env 파일에서 환경변수를 읽어옵니다

# OpenAI API 키를 환경변수에서 가져옵니다
# API 키는 AI 서비스를 사용하기 위한 비밀번호 같은 것입니다
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY가 설정되지 않았습니다!")
    raise ValueError("OPENAI_API_KEY 환경 변수를 설정해주세요.")

# # 검색 쿼리 설정
# query = "부산 축제 2025년 8월 -자동차 -모터쇼 -현대 -BMW -지프 -혼다"
# headers = {
#     "X-Naver-Client-Id": client_id,
#     "X-Naver-Client-Secret": client_secret
# }

# # 관련성 점수 계산 함수
# def calculate_relevance(item):
#     score = 0
#     title = item.get('title', '').lower()
#     description = item.get('description', '').lower()
    
#     # 관련 키워드 점수화
#     keywords = ['축제', '부산', '2025', '8월', '해수욕장', '불꽃', '바다']
#     for keyword in keywords:
#         if keyword in title:
#             score += 2
#         if keyword in description:
#             score += 1
    
#     # 관련 없는 키워드 감점
#     irrelevant_keywords = ['자동차', '모터쇼', '현대', 'bmw', '지프', '혼다']
#     for keyword in irrelevant_keywords:
#         if keyword in title or keyword in description:
#             score -= 3
    
#     return score

# # 검색 결과 수집 및 정렬
# def search_naver(query, search_type, display=3, sort="sim"):
#     url = f"https://openapi.naver.com/v1/search/{search_type}.json?query={query}&display={display}&sort={sort}"
#     try:
#         res = requests.get(url, headers=headers).json()
#         if 'items' not in res:
#             logger.warning(f"{search_type} 검색 결과가 비어 있습니다.")
#             return []
#         return res['items']
#     except Exception as e:
#         logger.error(f"{search_type} 검색 중 오류 발생: {str(e)}")
#         return []

# # 모든 검색 결과 통합 및 순위 매기기
# def get_top_relevant_results():
#     # 뉴스, 블로그, 웹문서 검색
#     news_results = search_naver(query, "news")
#     blog_results = search_naver(query, "blog")
#     web_results = search_naver(query, "webkr")
    
#     # 모든 결과를 하나로 합치기
#     all_results = []
#     for item in news_results:
#         all_results.append({
#             'type': 'news',
#             'title': item['title'],
#             'link': item['link'],
#             'pubDate': item.get('pubDate', ''),
#             'description': item.get('description', '')
#         })
#     for item in blog_results:
#         all_results.append({
#             'type': 'blog',
#             'title': item['title'],
#             'link': item['link'],
#             'pubDate': item.get('postdate', ''),
#             'description': item.get('description', '')
#         })
#     for item in web_results:
#         all_results.append({
#             'type': 'web',
#             'title': item['title'],
#             'link': item['link'],
#             'pubDate': '',
#             'description': item.get('description', '')
#         })
    
#     # 관련성 점수로 정렬
#     ranked_results = sorted(all_results, key=calculate_relevance, reverse=True)
#     return ranked_results[:3]  # 상위 3개만 반환

# # 메인 실행
# if __name__ == "__main__":
#     logger.info("부산 축제 2025년 8월 검색 시작")
#     top_results = get_top_relevant_results()
    
#     print("\n=== 부산 축제 2025년 8월 관련 상위 3개 결과 ===")
#     for i, result in enumerate(top_results, 1):
#         print(f"{i}. [{result['type'].upper()}] {result['title']}")
#         print(f"링크: {result['link']}")
#         print(f"게시일: {result['pubDate']}")
#         print(f"설명: {result['description']}")
#         print("-" * 40)

# OpenAI 클라이언트를 초기화합니다 (최신 버전 호환)
client = openai.OpenAI(api_key=openai_api_key)

# ========================================
# FastAPI 애플리케이션 생성
# ========================================
# FastAPI는 현대적인 Python 웹 프레임워크입니다
app = FastAPI(title="여행 플래너 AI", version="1.0.0")

# ========================================
# CORS 설정 (Cross-Origin Resource Sharing)
# ========================================
# CORS는 웹 브라우저에서 다른 도메인의 서버에 접근할 수 있게 해주는 설정입니다
# 프론트엔드(localhost:3000)에서 백엔드(localhost:8000)에 접근할 수 있게 합니다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 프론트엔드 주소
    allow_credentials=True,  # 쿠키 등 인증 정보 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],  # 모든 헤더 허용
)

# ========================================
# 데이터 모델 정의 (Pydantic 사용)
# ========================================
# Pydantic은 데이터 검증을 자동으로 해주는 라이브러리입니다

class TripRequest(BaseModel):
    """여행 계획 요청을 받는 데이터 모델"""
    destination: str  # 목적지 (예: "제주도", "도쿄")
    start_date: str  # 시작 날짜 (예: "2024-01-01")
    end_date: str    # 종료 날짜 (예: "2024-01-03")
    budget: Optional[str] = "보통"  # 예산 (선택사항, 기본값: "보통")
    interests: Optional[List[str]] = []  # 관심사 리스트 (선택사항, 기본값: 빈 리스트)
    guests: Optional[int] = 2  # 투숙객 수 (선택사항, 기본값: 2명)
    rooms: Optional[int] = 1   # 객실 수 (선택사항, 기본값: 1개)

class HotelInfo(BaseModel):
    """호텔 정보를 담는 데이터 모델"""
    name: str  # 호텔 이름
    type: str  # 호텔 타입 (호텔, 펜션, 게스트하우스 등)
    price_range: str  # 가격대 (저예산, 보통, 고급, 럭셔리)
    booking_links: dict  # 각 사이트별 예약 링크
    description: str  # 호텔 설명
    rating: Optional[float] = None  # 평점 (선택사항)
    amenities: Optional[List[str]] = []  # 편의시설 리스트 (선택사항)

class TripPlan(BaseModel):
    """완성된 여행 계획을 담는 데이터 모델"""
    destination: str  # 목적지
    duration: str  # 여행 기간
    itinerary: List[dict]  # 일정표 (각 날짜별 활동)
    events: List[dict]  # 축제/행사 정보 (새로 추가)
    accommodation: List[HotelInfo]  # 숙박 정보
    total_cost: str  # 총 예상 비용
    tips: List[str]  # 여행 팁 리스트

class EventInfo(BaseModel):
    """축제/행사 정보를 담는 데이터 모델"""
    name: str  # 축제/행사 이름
    date: str  # 날짜
    description: str  # 설명
    location: str  # 장소
    type: str  # 유형 (축제, 행사, 전시회 등)
    website: Optional[str] = None  # 공식 웹사이트 (선택사항)
    ticket_info: Optional[str] = None  # 티켓 정보 (선택사항)

# ========================================
# 축제/행사 정보 서비스 클래스
# ========================================
# 이 클래스는 여행 기간에 해당하는 축제나 행사 정보를 제공합니다

class EventService:
    """축제/행사 정보를 제공하는 서비스"""
    
    @staticmethod
    def get_events_by_destination_and_date(destination: str, start_date: str, end_date: str) -> List[dict]:
        """목적지와 날짜에 맞는 축제/행사 정보를 제공하는 메서드"""
        
        # 실제 축제/행사 데이터베이스 (더 많은 정보를 추가할 수 있습니다)
        events_db = {
            "여수": [
                {
                    "name": "여수 세계 엑스포",
                    "date": "2024-05-01",
                    "description": "해양과 미래를 주제로 한 세계 박람회",
                    "location": "여수 엑스포 공원",
                    "type": "세계 박람회",
                    "website": "https://www.expo2024.kr",
                    "ticket_info": "사전 예약 필요"
                },
                {
                    "name": "여수 밤바다 불꽃축제",
                    "date": "2024-07-15",
                    "description": "여수 바다를 배경으로 한 화려한 불꽃쇼",
                    "location": "여수 해안가",
                    "type": "불꽃축제",
                    "website": None,
                    "ticket_info": "무료"
                },
                {
                    "name": "여수 해산물 축제",
                    "date": "2024-10-01",
                    "description": "신선한 해산물을 맛볼 수 있는 지역 축제",
                    "location": "여수 항구",
                    "type": "음식 축제",
                    "website": None,
                    "ticket_info": "무료 (음식은 유료)"
                }
            ],
            "제주도": [
                {
                    "name": "제주 한라문화제",
                    "date": "2024-04-15",
                    "description": "한라산을 주제로 한 문화 축제",
                    "location": "제주시 일원",
                    "type": "문화 축제",
                    "website": None,
                    "ticket_info": "무료"
                },
                {
                    "name": "제주 해녀 축제",
                    "date": "2024-06-20",
                    "description": "제주 해녀 문화를 체험할 수 있는 축제",
                    "location": "성산일출봉",
                    "type": "문화 체험",
                    "website": None,
                    "ticket_info": "일부 체험 유료"
                },
                {
                    "name": "제주 감귤 축제",
                    "date": "2024-11-01",
                    "description": "제주 특산품 감귤을 주제로 한 축제",
                    "location": "서귀포시",
                    "type": "특산품 축제",
                    "website": None,
                    "ticket_info": "무료"
                }
            ],
            "부산": [
                {
                    "name": "부산 국제영화제",
                    "date": "2024-10-01",
                    "description": "아시아 최대 규모의 영화제",
                    "location": "해운대구",
                    "type": "영화제",
                    "website": "https://www.biff.kr",
                    "ticket_info": "사전 예약 필요"
                },
                {
                    "name": "부산 불꽃축제",
                    "date": "2024-08-15",
                    "description": "해운대 해변에서 열리는 화려한 불꽃쇼",
                    "location": "해운대 해변",
                    "type": "불꽃축제",
                    "website": None,
                    "ticket_info": "무료"
                },
                {
                    "name": "부산 국제수산무역전시회",
                    "date": "2024-05-20",
                    "description": "수산업 관련 국제 전시회",
                    "location": "BEXCO",
                    "type": "전시회",
                    "website": None,
                    "ticket_info": "사전 등록 필요"
                }
            ],
            "도쿄": [
                {
                    "name": "도쿄 체리블라썸 축제",
                    "date": "2024-04-01",
                    "description": "벚꽃 개화를 축하하는 전통 축제",
                    "location": "우에노 공원",
                    "type": "전통 축제",
                    "website": None,
                    "ticket_info": "무료"
                },
                {
                    "name": "도쿄 게임쇼",
                    "date": "2024-09-15",
                    "description": "세계 최대 규모의 게임 전시회",
                    "location": "마쿠하리 멧세",
                    "type": "게임 전시회",
                    "website": "https://tgs.nikkeibp.co.jp",
                    "ticket_info": "사전 예약 필요"
                },
                {
                    "name": "도쿄 디자인 위크",
                    "date": "2024-10-20",
                    "description": "디자인과 창작을 주제로 한 국제 행사",
                    "location": "도쿄 시내",
                    "type": "디자인 행사",
                    "website": "https://tokyodesignweek.jp",
                    "ticket_info": "일부 행사 유료"
                }
            ],
            "파리": [
                {
                    "name": "파리 패션 위크",
                    "date": "2024-03-01",
                    "description": "세계 최고의 패션 디자이너들의 컬렉션",
                    "location": "파리 시내",
                    "type": "패션 행사",
                    "website": "https://www.fhcm.paris",
                    "ticket_info": "초대장 필요"
                },
                {
                    "name": "파리 음악제",
                    "date": "2024-06-21",
                    "description": "전국에서 열리는 음악 축제",
                    "location": "파리 전역",
                    "type": "음악 축제",
                    "website": "https://fetedelamusique.culture.gouv.fr",
                    "ticket_info": "무료"
                },
                {
                    "name": "파리 북 페어",
                    "date": "2024-03-20",
                    "description": "프랑스 최대 규모의 도서 전시회",
                    "location": "파리 엑스포 포르트 드 베르사유",
                    "type": "도서 전시회",
                    "website": "https://www.livreshebdo.fr",
                    "ticket_info": "사전 등록 필요"
                }
            ]
        }
        
        # 기본 축제/행사 정보 (목적지에 해당하는 정보가 없는 경우)
        default_events = [
            {
                "name": "지역 문화 행사",
                "date": "2024-01-01",
                "description": "방문 시기에 열리는 지역 문화 행사가 있을 수 있습니다.",
                "location": "지역 일원",
                "type": "문화 행사",
                "website": None,
                "ticket_info": "현지 정보 확인 필요"
            }
        ]
        
        try:
            # 날짜를 datetime 객체로 변환
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # 목적지에 해당하는 축제/행사 목록 가져오기
            destination_events = events_db.get(destination, default_events)
            
            # 여행 기간에 해당하는 축제/행사만 필터링
            matching_events = []
            for event in destination_events:
                try:
                    event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                    
                    # 연도에 관계없이 월과 일만 매칭 (매년 반복되는 축제/행사)
                    start_month_day = (start_dt.month, start_dt.day)
                    end_month_day = (end_dt.month, end_dt.day)
                    event_month_day = (event_date.month, event_date.day)
                    
                    # 월/일 기준으로 매칭 (더 유연하게)
                    if (start_month_day <= event_month_day <= end_month_day) or \
                       (start_month_day > end_month_day and  # 연도가 바뀌는 경우 (예: 12월 31일 ~ 1월 2일)
                        (event_month_day >= start_month_day or event_month_day <= end_month_day)) or \
                       (start_dt.month == event_date.month and start_dt.day <= event_date.day <= end_dt.day) or \
                       (end_dt.month == event_date.month and start_dt.day <= event_date.day <= end_dt.day):
                        matching_events.append(event)
                        
                except Exception as e:
                    # 날짜 형식이 맞지 않는 경우 건너뛰기
                    logger.warning(f"이벤트 날짜 파싱 실패: {event['name']}, {e}")
                    continue
            
            # 날짜순으로 정렬
            matching_events.sort(key=lambda x: x["date"])
            
            # 디버깅을 위한 로그 추가
            logger.info(f"목적지: {destination}, 여행 기간: {start_date} ~ {end_date}")
            logger.info(f"총 이벤트 수: {len(destination_events)}, 매칭된 이벤트 수: {len(matching_events)}")
            if matching_events:
                for event in matching_events:
                    logger.info(f"매칭된 이벤트: {event['name']} ({event['date']})")
            
            # 테스트를 위해 매칭된 이벤트가 없으면 모든 이벤트를 반환
            if not matching_events:
                logger.info("매칭된 이벤트가 없어 모든 이벤트를 반환합니다.")
                return destination_events
            
            return matching_events
            
        except Exception as e:
            logger.warning(f"축제/행사 정보 조회 중 오류: {e}")
            return default_events

# ========================================
# 호텔 검색 서비스 클래스
# ========================================
# 이 클래스는 호텔 정보를 제공하고 예약 링크를 생성합니다

class HotelSearchService:
    """호텔 검색 및 예약 링크 생성 서비스"""
    
    @staticmethod #인스턴스를 통해서 호출했습니다 이번에는 인스턴스를 통하지 않고 클래스에서 바로 호출할 수 있는 정적 메서드
    def get_popular_hotels(destination: str) -> List[dict]:
        """목적지별 인기 호텔 정보를 제공하는 메서드"""
        # 실제 인기 호텔 데이터베이스 (더 많은 호텔을 추가할 수 있습니다)
        hotels_db = {
            "여수": [
                {
                    "name": "마린호텔 여수",
                    "type": "호텔",
                    "price_range": "보통",
                    "rating": 4.2,
                    "amenities": ["무료 WiFi", "주차", "조식", "바다 전망"],
                    "location": "여수시",
                    "description": "여수 바다를 바라보는 전망 좋은 호텔로, 여수 해상케이블카와 가깝습니다."
                },
                {
                    "name": "여수 오션뷰 펜션",
                    "type": "펜션",
                    "price_range": "저예산",
                    "rating": 4.0,
                    "amenities": ["무료 WiFi", "주방", "바베큐", "바다 전망"],
                    "location": "여수시",
                    "description": "여수 해안가에 위치한 아늑한 펜션으로 바다 전망을 감상할 수 있습니다."
                },
                {
                    "name": "여수 그랜드 호텔",
                    "type": "비즈니스 호텔",
                    "price_range": "보통",
                    "rating": 4.1,
                    "amenities": ["무료 WiFi", "주차", "조식", "피트니스"],
                    "location": "여수시",
                    "description": "여수 시내 중심가에 위치하여 교통이 편리하고 쇼핑하기 좋습니다."
                }
            ],
            "제주도": [
                {
                    "name": "제주 신라호텔",
                    "type": "리조트",
                    "price_range": "고급",
                    "rating": 4.8,
                    "amenities": ["무료 WiFi", "주차", "조식", "수영장", "골프장"],
                    "location": "서귀포시",
                    "description": "제주 남쪽에 위치한 럭셔리 리조트로 한라산과 바다 전망을 즐길 수 있습니다."
                },
                {
                    "name": "제주 그랜드 호텔",
                    "type": "호텔",
                    "price_range": "보통",
                    "rating": 4.3,
                    "amenities": ["무료 WiFi", "주차", "조식"],
                    "location": "제주시",
                    "description": "제주 시내 중심가에 위치하여 쇼핑과 관광에 편리합니다."
                },
                {
                    "name": "제주 오션뷰 펜션",
                    "type": "펜션",
                    "price_range": "저예산",
                    "rating": 4.1,
                    "amenities": ["무료 WiFi", "주방", "바베큐"],
                    "location": "애월읍",
                    "description": "애월 해안가에 위치하여 아름다운 바다 전망을 감상할 수 있습니다."
                }
            ],
            "부산": [
                {
                    "name": "부산 파크 하얏트 호텔",
                    "type": "럭셔리 호텔",
                    "price_range": "럭셔리",
                    "rating": 4.9,
                    "amenities": ["무료 WiFi", "주차", "조식", "수영장", "스파", "피트니스"],
                    "location": "해운대구",
                    "description": "해운대 해변과 인접한 5성급 럭셔리 호텔입니다."
                },
                {
                    "name": "부산 노보텔 앰배서더",
                    "type": "비즈니스 호텔",
                    "price_range": "보통",
                    "rating": 4.2,
                    "amenities": ["무료 WiFi", "주차", "조식", "피트니스"],
                    "location": "중구",
                    "description": "부산 시내 중심가에 위치하여 교통이 편리합니다."
                },
                {
                    "name": "부산 게스트하우스",
                    "type": "게스트하우스",
                    "price_range": "저예산",
                    "rating": 4.0,
                    "amenities": ["무료 WiFi", "공용 주방"],
                    "location": "서구",
                    "description": "가성비 좋은 게스트하우스로 여행자들에게 인기가 많습니다."
                }
            ],
            "도쿄": [
                {
                    "name": "도쿄 리츠칼튼 호텔",
                    "type": "럭셔리 호텔",
                    "price_range": "럭셔리",
                    "rating": 4.9,
                    "amenities": ["무료 WiFi", "수영장", "스파", "피트니스", "레스토랑"],
                    "location": "미나토구",
                    "description": "도쿄 타워와 가까운 럭셔리 호텔로 도쿄 전경을 감상할 수 있습니다."
                },
                {
                    "name": "도쿄 신주쿠 프린스 호텔",
                    "type": "비즈니스 호텔",
                    "price_range": "보통",
                    "rating": 4.3,
                    "amenities": ["무료 WiFi", "피트니스", "레스토랑"],
                    "location": "신주쿠구",
                    "description": "신주쿠 역과 인접하여 교통이 매우 편리합니다."
                },
                {
                    "name": "도쿄 카피탈 호텔",
                    "type": "경제형 호텔",
                    "price_range": "저예산",
                    "rating": 4.0,
                    "amenities": ["무료 WiFi", "세탁기"],
                    "location": "시부야구",
                    "description": "시부야 중심가에 위치한 깔끔한 경제형 호텔입니다."
                }
            ],
            "파리": [
                {
                    "name": "파리 리츠 호텔",
                    "type": "럭셔리 호텔",
                    "price_range": "럭셔리",
                    "rating": 4.9,
                    "amenities": ["무료 WiFi", "수영장", "스파", "피트니스", "미슐랭 레스토랑"],
                    "location": "1구",
                    "description": "루브르 박물관과 가까운 역사적인 럭셔리 호텔입니다."
                },
                {
                    "name": "파리 노보텔 투어 에펠",
                    "type": "비즈니스 호텔",
                    "price_range": "보통",
                    "rating": 4.2,
                    "amenities": ["무료 WiFi", "피트니스", "레스토랑"],
                    "location": "7구",
                    "description": "에펠탑 근처에 위치하여 파리의 상징적인 랜드마크를 감상할 수 있습니다."
                },
                {
                    "name": "파리 게스트하우스",
                    "type": "게스트하우스",
                    "price_range": "저예산",
                    "rating": 4.1,
                    "amenities": ["무료 WiFi", "공용 주방"],
                    "location": "18구",
                    "description": "몽마르트 언덕 근처의 아늑한 게스트하우스입니다."
                }
            ]
        }
        
        # 기본 호텔 정보 (목적지에 해당하는 호텔이 없는 경우 사용)
        default_hotels = [
            {
                "name": "추천 호텔",
                "type": "호텔",
                "price_range": "보통",
                "rating": 4.0,
                "amenities": ["무료 WiFi", "주차"],
                "location": "시내",
                "description": "편리한 위치의 추천 호텔입니다."
            }
        ]
        
        # 목적지에 맞는 호텔을 반환하고, 없으면 기본 호텔을 반환합니다
        return hotels_db.get(destination, default_hotels)
    
    @staticmethod
    def create_booking_links(destination: str, check_in: str, check_out: str, guests: int, rooms: int, hotel_name: str = "") -> dict:
        """각 호텔 예약 사이트의 검색 링크를 생성하는 메서드"""
        
        # 날짜 형식을 변환합니다 (YYYY-MM-DD -> DD/MM/YYYY)
        # 일부 예약 사이트는 다른 날짜 형식을 사용하기 때문입니다
        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
            check_in_formatted = check_in_date.strftime("%d/%m/%Y")
            check_out_formatted = check_out_date.strftime("%d/%m/%Y")
        except:
            # 날짜 변환에 실패하면 원본 형식을 그대로 사용합니다
            check_in_formatted = check_in
            check_out_formatted = check_out
        
        # URL 인코딩: 한글이나 특수문자를 URL에 안전하게 포함시키기 위한 처리
        encoded_destination = urllib.parse.quote(destination)
        encoded_hotel_name = urllib.parse.quote(hotel_name) if hotel_name else ""
        
        # 각 예약 사이트별 검색 링크를 생성합니다
        links = {
            "trip_dot_com": {
                "name": "트립닷컴",
                "url": f"https://www.trip.com/hotels/list?city={encoded_destination}&checkin={check_in_formatted}&checkout={check_out_formatted}&adult={guests}&room={rooms}",
                "icon": "🏨"
            },
            "airbnb": {
                "name": "에어비앤비",
                "url": f"https://www.airbnb.co.kr/s/{encoded_destination}/homes?checkin={check_in}&checkout={check_out}&adults={guests}&children=0&infants=0&pets=0",
                "icon": "🏠"
            },
            "agoda": {
                "name": "아고다",
                "url": f"https://www.agoda.com/search?city={encoded_destination}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&children=0&travellerType=1",
                "icon": "🛏️"
            },
            "booking": {
                "name": "부킹닷컴",
                "url": f"https://www.booking.com/searchresults.html?ss={encoded_destination}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}",
                "icon": "📅"
            }
        }
        
        # 특정 호텔명이 있는 경우 더 구체적인 검색 링크를 생성합니다
        if hotel_name:
            links["trip_dot_com"]["url"] = f"https://www.trip.com/hotels/list?city={encoded_destination}&hotelName={encoded_hotel_name}&checkin={check_in_formatted}&checkout={check_out_formatted}&adult={guests}&room={rooms}"
            links["agoda"]["url"] = f"https://www.agoda.com/search?city={encoded_destination}&hotelName={encoded_hotel_name}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&children=0&travellerType=1"
            links["booking"]["url"] = f"https://www.booking.com/searchresults.html?ss={encoded_destination}&hotelName={encoded_hotel_name}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}"
        
        return links

# ========================================
# API 엔드포인트 정의
# ========================================
# 엔드포인트는 웹 서버에서 특정 기능을 제공하는 주소입니다

@app.get("/")
async def root():
    """루트 경로 (메인 페이지) - 서버가 정상 작동하는지 확인하는 용도"""
    return {"message": "여행 플래너 AI API"}

@app.post("/plan-trip", response_model=TripPlan)
async def plan_trip(request: TripRequest):
    """여행 계획을 생성하는 메인 API"""
    try:
        # 로그에 요청 정보를 기록합니다
        logger.info(f"여행 계획 생성 요청: {request.destination}, {request.start_date} ~ {request.end_date}")
        
        # 호텔 검색 서비스와 축제/행사 서비스를 초기화합니다
        hotel_service = HotelSearchService()
        event_service = EventService()
        
        # 여행 일수를 계산합니다
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            travel_days = (end_date - start_date).days + 1
        except:
            travel_days = 3  # 날짜 계산에 실패하면 기본값 3일을 사용합니다
        
        # 축제/행사 정보를 미리 가져와서 AI에게 제공합니다
        events = event_service.get_events_by_destination_and_date(
            request.destination, 
            request.start_date, 
            request.end_date
        )
        
        # OpenAI API에 전달할 프롬프트(질문)를 생성합니다
        # 프롬프트는 AI에게 무엇을 해달라고 요청하는 메시지입니다
        events_info = ""
        if events:
            events_info = f"\n\n여행 기간에 열리는 축제/행사 정보:\n"
            for event in events:
                events_info += f"- {event['name']} ({event['date']}): {event['description']} - {event['location']}\n"
        
        prompt = f"""
        다음 조건에 맞는 상세한 여행 계획을 한국어로 작성해주세요:
        
        목적지: {request.destination}
        여행 기간: {request.start_date} ~ {request.end_date} (총 {travel_days}일)
        예산: {request.budget}
        관심사: {', '.join(request.interests) if request.interests else '일반적인 관광'}
        투숙객: {request.guests}명, 객실: {request.rooms}개{events_info}
        
        다음 형식으로 JSON 응답을 제공해주세요:
        {{
            "destination": "목적지명",
            "duration": "여행 기간",
            "itinerary": [
                {{
                    "day": 1,
                    "date": "{request.start_date}",
                    "morning": "오전 활동 (구체적인 관광지명 포함)",
                    "afternoon": "오후 활동 (구체적인 관광지명 포함)",
                    "evening": "저녁 활동 (구체적인 장소명 포함)",
                    "accommodation": "숙박지 (구체적인 지역명 포함)"
                }},
                {{
                    "day": 2,
                    "date": "{start_date + timedelta(days=1) if travel_days > 1 else request.start_date}",
                    "morning": "오전 활동 (구체적인 관광지명 포함)",
                    "afternoon": "오후 활동 (구체적인 관광지명 포함)",
                    "evening": "저녁 활동 (구체적인 장소명 포함)",
                    "accommodation": "숙박지 (구체적인 지역명 포함)"
                }},
                {{
                    "day": 3,
                    "date": "{start_date + timedelta(days=2) if travel_days > 2 else request.start_date}",
                    "morning": "오전 활동 (구체적인 관광지명 포함)",
                    "afternoon": "오후 활동 (구체적인 관광지명 포함)",
                    "evening": "저녁 활동 (구체적인 장소명 포함)",
                    "accommodation": "숙박지 (구체적인 지역명 포함)"
                }}
            ],
            "accommodation": [
                {{
                    "name": "실제 호텔명 (존재하는 호텔명 사용)",
                    "type": "호텔/펜션/게스트하우스 등",
                    "price_range": "가격대",
                    "description": "설명",
                    "rating": 4.5,
                    "amenities": ["무료 WiFi", "주차", "조식"],
                    "location": "구체적인 위치 (구/군 단위)"
                }}
            ],
            "total_cost": "총 예상 비용",
            "tips": ["여행 팁1", "여행 팁2", "여행 팁3"]
        }}
        
        중요사항:
        1. accommodation의 name 필드에는 실제 존재하는 호텔명을 사용해주세요. 가상의 호텔명(예: "호텔 A", "추천 호텔")은 사용하지 마세요.
        2. itinerary 배열에는 여행 기간에 맞는 모든 일차를 포함해주세요. {travel_days}일 여행이면 {travel_days}개의 일차가 있어야 합니다.
        3. 각 일차마다 오전, 오후, 저녁 활동을 구체적으로 작성해주세요.
        4. accommodation는 여행 기간에 맞게 적절한 수량을 추천해주세요.
        5. 여행 기간에 열리는 축제나 행사가 있다면, 해당 날짜의 일정에 포함시켜주세요.
        """
        
        logger.info("OpenAI API 호출 시작...")
        
        # OpenAI API를 호출하여 AI 여행 계획을 생성합니다
        # 최신 OpenAI API 사용법을 적용했습니다
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 사용할 AI 모델
            messages=[
                {"role": "system", "content": f"당신은 전문 여행 플래너입니다. 상세하고 실용적인 여행 계획을 제공해주세요. {travel_days}일 여행 계획을 만들어주세요. 호텔명은 실제 존재하는 구체적인 호텔명을 사용해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,  # AI 응답의 최대 길이 (더 긴 응답을 위해 증가)
            temperature=0.7   # AI의 창의성 수준 (0.0: 매우 일관적, 1.0: 매우 창의적)
        )
        
        logger.info("OpenAI API 응답 수신 완료")
        
        # AI 응답을 파싱(분석)합니다
        content = response.choices[0].message.content
        logger.info(f"AI 응답 내용: {content[:200]}...")
        
        # JSON 응답을 추출하려고 시도합니다
        try:
            # JSON 부분만 추출 (AI가 때로는 설명과 함께 JSON을 반환하기 때문)
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                logger.info(f"추출된 JSON: {json_str}")
                trip_data = json.loads(json_str)
                
                # 호텔 정보에 예약 링크를 추가합니다
                for hotel in trip_data.get("accommodation", []):
                    hotel["booking_links"] = hotel_service.create_booking_links(
                        request.destination,
                        request.start_date,
                        request.end_date,
                        request.guests,
                        request.rooms,
                        hotel.get("name", "")  # 호텔명을 링크 생성에 포함
                    )
                
                # 축제/행사 정보를 가져와서 추가합니다
                events = event_service.get_events_by_destination_and_date(
                    request.destination, 
                    request.start_date, 
                    request.end_date
                )
                trip_data["events"] = events
                
                # TripPlan 모델로 변환하여 반환합니다
                return TripPlan(**trip_data)
            else:
                logger.warning("JSON 응답을 찾을 수 없습니다")
                raise ValueError("JSON 응답을 찾을 수 없습니다")
                
        except json.JSONDecodeError as e:
            # JSON 파싱에 실패한 경우 기본 응답을 생성합니다
            logger.warning(f"JSON 파싱 실패: {e}")
            
            # 실제 호텔 정보를 가져옵니다
            popular_hotels = hotel_service.get_popular_hotels(request.destination)
            
            # 실제 호텔 정보로 기본 응답을 생성합니다
            accommodation_list = []
            for hotel in popular_hotels[:2]:  # 상위 2개 호텔만 사용
                hotel_info = HotelInfo(
                    name=hotel["name"],
                    type=hotel["type"],
                    price_range=hotel["price_range"],
                    booking_links=hotel_service.create_booking_links(
                        request.destination,
                        request.start_date,
                        request.end_date,
                        request.guests,
                        request.rooms,
                        hotel["name"]
                    ),
                    description=hotel["description"],
                    rating=hotel["rating"],
                    amenities=hotel["amenities"]
                )
                accommodation_list.append(hotel_info)
            
            # 여행 기간에 맞는 일정을 생성합니다
            itinerary_list = []
            for day in range(1, travel_days + 1):
                current_date = start_date + timedelta(days=day - 1)
                itinerary_list.append({
                    "day": day,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "morning": f"{day}일차 오전 활동",
                    "afternoon": f"{day}일차 오후 활동",
                    "evening": f"{day}일차 저녁 활동",
                    "accommodation": f"{request.destination} 추천 호텔"
                })
            
            # 축제/행사 정보를 가져옵니다
            events = event_service.get_events_by_destination_and_date(
                request.destination, 
                request.start_date, 
                request.end_date
            )
            
            # 기본 여행 계획을 반환합니다
            return TripPlan(
                destination=request.destination,
                duration=f"{request.start_date} ~ {request.end_date}",
                itinerary=itinerary_list,
                accommodation=accommodation_list,
                events=events,  # 축제/행사 정보 추가
                total_cost="예산에 따라 조정 가능",
                tips=["여행 전 날씨 확인", "필수품 준비", "현지 교통 정보 파악"]
            )
            
    except Exception as e:
        # 에러가 발생한 경우 로그에 기록하고 HTTP 에러를 반환합니다
        logger.error(f"여행 계획 생성 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"여행 계획 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/hotel-links")
async def get_hotel_links(
    destination: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    rooms: int = 1
):
    """특정 조건에 맞는 호텔 검색 링크를 생성하는 API"""
    try:
        hotel_service = HotelSearchService()
        links = hotel_service.create_booking_links(destination, check_in, check_out, guests, rooms)
        return {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms,
            "booking_links": links
        }
    except Exception as e:
        logger.error(f"호텔 링크 생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"호텔 링크 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/popular-hotels/{destination}")
async def get_popular_hotels(destination: str):
    """특정 목적지의 인기 호텔 정보를 조회하는 API"""
    try:
        hotel_service = HotelSearchService()
        hotels = hotel_service.get_popular_hotels(destination)
        return {
            "destination": destination,
            "hotels": hotels
        }
    except Exception as e:
        logger.error(f"인기 호텔 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"인기 호텔 정보 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/events")
async def get_events(
    destination: str,
    start_date: str,
    end_date: str
):
    """특정 목적지와 기간의 축제/행사 정보를 조회하는 API"""
    try:
        event_service = EventService()
        events = event_service.get_events_by_destination_and_date(destination, start_date, end_date)
        return {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "events": events,
            "total_events": len(events)
        }
    except Exception as e:
        logger.error(f"축제/행사 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"축제/행사 정보 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/hotel-search")
async def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    rooms: int = 1,
    hotel_name: str = ""
):
    """호텔 검색 및 예약 링크를 생성하는 통합 API"""
    try:
        hotel_service = HotelSearchService()
        
        # 인기 호텔 정보를 가져옵니다
        popular_hotels = hotel_service.get_popular_hotels(destination)
        
        # 각 호텔에 예약 링크를 추가합니다
        for hotel in popular_hotels:
            hotel["booking_links"] = hotel_service.create_booking_links(
                destination, check_in, check_out, guests, rooms, hotel["name"]
            )
        
        # 일반적인 검색 링크도 제공합니다
        general_links = hotel_service.create_booking_links(
            destination, check_in, check_out, guests, rooms, hotel_name
        )
        
        return {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms,
            "popular_hotels": popular_hotels,
            "general_search_links": general_links
        }
    except Exception as e:
        logger.error(f"호텔 검색 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"호텔 검색 중 오류가 발생했습니다: {str(e)}")

@app.get("/health")
async def health_check():
    """서버 상태를 확인하는 API (헬스 체크)"""
    return {"status": "healthy", "openai_key_set": bool(openai_api_key)}

# ========================================
# 메인 실행 부분
# ========================================
# 이 파일을 직접 실행할 때만 서버를 시작합니다
if __name__ == "__main__":
    import uvicorn  # ASGI 서버 (FastAPI를 실행하기 위한 서버)
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 모든 IP에서 접근 가능, 8000번 포트 사용 