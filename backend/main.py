# ========================================
# 여행 플래너 AI 백엔드 서버
# ========================================
# 이 파일은 여행 계획을 AI로 생성하고 호텔 정보를 제공하는 웹 서버입니다.
# FastAPI 프레임워크를 사용하여 만들어졌습니다.

# 필요한 라이브러리들을 가져옵니다 (import)
from fastapi import FastAPI, HTTPException  # FastAPI: 웹 서버 프레임워크, HTTPException: 에러 처리용
from fastapi.middleware.cors import CORSMiddleware  # CORS: 웹 브라우저의 보안 정책 관련
from fastapi.responses import StreamingResponse  # SSE를 위한 StreamingResponse
from pydantic import BaseModel  # 데이터 검증을 위한 라이브러리
from typing import List, Optional  # 타입 힌트를 위한 라이브러리
import openai  # OpenAI API 사용을 위한 라이브러리
import os  # 운영체제 관련 기능 (환경변수 등)
from dotenv import load_dotenv  # .env 파일에서 환경변수를 로드하는 라이브러리
import json  # JSON 데이터 처리용
import logging  # 로그 기록용
from datetime import datetime, timedelta  # 날짜와 시간 처리용
import urllib.parse  # URL 인코딩용
import requests  # HTTP 요청을 위한 라이브러리
import re  # 정규표현식을 위한 라이브러리
import asyncio  # 비동기 처리를 위한 라이브러리
from kakao_location_validator import KakaoLocationValidator, PlaceValidationResult
from kakao_geocoding import KakaoGeocodingService
from kakao_place_service import KakaoPlaceService

load_dotenv()

# 카카오 API 인증
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# ========================================
# 카카오 로컬 API 서비스 클래스
# ========================================
class KakaoLocalService:
    """카카오 로컬 API를 사용하여 장소 검색 및 검증을 수행하는 서비스"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or KAKAO_API_KEY
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    
    def search_place(self, query: str, region: str = None) -> dict:
        """목적지와 날짜에 맞는 축제/행사 정보를 검색하는 메서드"""
        try:
            # 날짜 정보 파싱
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            current_date = datetime.now().date()
            
            # 여행 시작일이 현재 날짜보다 과거인지 확인
            if start_dt.date() < current_date:
                logger.info(f"과거 여행 제외: {start_date} (현재: {current_date})")
                return []
            
            # 검색 쿼리 구성 - 연도를 명시적으로 포함하고 미래 이벤트 강조
            year = start_dt.year
            month = start_dt.month
            
            # 지역 중심의 검색 쿼리 (지역을 더 강조)
            search_queries = [
                f'"{destination}" {year}년 {month}월 축제',  # 따옴표로 지역명 강조
                f'"{destination}" {year}년 {month}월 행사',
                f'"{destination}" {year}년 {month}월 이벤트',
                f'"{destination}" {year}년 {month}월 문화행사',
                f'"{destination}" {year}년 {month}월 페스티벌',
                f'"{destination}" {year}년 {month}월 축제 일정',
                f'"{destination}" {year}년 {month}월 행사 일정',
                # 구체적인 날짜 범위를 포함한 검색
                f'"{destination}" {start_date} {end_date} 축제',
                f'"{destination}" {start_date} {end_date} 행사',
                f'"{destination}" {start_date} {end_date} 이벤트',
                # 지역명을 앞에 배치하여 우선순위 높임
                f'{destination}지역 {year}년 {month}월 축제',
                f'{destination}지역 {year}년 {month}월 행사',
                f'{destination}지역 {year}년 {month}월 이벤트'
            ]
            
            all_results = []
            
            for query in search_queries:
                try:
                    # 뉴스 검색 - 최신순으로 정렬
                    news_results = self._search_naver("news", query, 5)
                    all_results.extend(self._process_news_results(news_results, destination, start_date, end_date))
                    
                    # 블로그 검색 - 관련성순으로 정렬
                    blog_results = self._search_naver("blog", query, 5)
                    all_results.extend(self._process_blog_results(blog_results, destination, start_date, end_date))
                    
                    # 웹문서 검색 - 관련성순으로 정렬
                    web_results = self._search_naver("webkr", query, 5)
                    all_results.extend(self._process_web_results(web_results, destination, start_date, end_date))
                    
                except Exception as e:
                    logger.warning(f"쿼리 '{query}' 검색 중 오류: {e}")
                    continue
            
            # 중복 제거 및 관련성 점수로 정렬
            unique_results = self._remove_duplicates(all_results)
            scored_results = self._calculate_relevance_scores(unique_results, destination, start_date, end_date)
            
            # 상위 결과만 반환 (최대 8개)
            return scored_results[:5]
            
        except Exception as e:
            logger.error(f"네이버 검색 중 오류: {e}")
            return []
    
    def _search_naver(self, search_type: str, query: str, display: int = 10) -> dict:
        """네이버 API 검색 실행"""
        url = f"https://openapi.naver.com/v1/search/{search_type}.json"
        
        # 검색 타입별 최적 파라미터 설정
        if search_type == "news":
            # 뉴스는 최신순으로 정렬하고 연도 필터링 강화
            params = {
                "query": query,
                "display": display,
                "sort": "date",  # 최신순
                "start": 1
            }
        elif search_type == "blog":
            # 블로그는 관련성순으로 정렬
            params = {
                "query": query,
                "display": display,
                "sort": "sim",  # 관련성순
                "start": 1
            }
        else:  # webkr
            # 웹문서는 관련성순으로 정렬
            params = {
                "query": query,
                "display": display,
                "sort": "sim",  # 관련성순
                "start": 1
            }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"네이버 API 검색 타임아웃: {search_type}")
            return {"items": []}
        except Exception as e:
            logger.error(f"네이버 API 검색 오류: {search_type}, {e}")
            return {"items": []}
    
    def _process_news_results(self, results: dict, destination: str, start_date: str, end_date: str) -> List[dict]:
        """뉴스 검색 결과를 처리하여 이벤트 정보로 변환"""
        events = []
        
        if 'items' not in results:
            return events
        
        # 여행 기간 파싱
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        target_year = start_dt.year
        
        for item in results['items']:
            try:
                # 제목과 설명에서 목적지가 명확하게 포함되어 있는지 확인
                title = item.get('title', '').lower()
                description = item.get('description', '').lower()
                
                # 목적지가 제목이나 설명에 포함되어 있는지 확인 (지역명, 약칭, 별칭 포함)
                destination_variants = self._get_destination_variants(destination)
                has_destination = any(variant in title or variant in description for variant in destination_variants)
                
                if not has_destination:
                    logger.info(f"목적지 불일치 제외: {item.get('title', '')} - 목적지: {destination}")
                    continue
                
                # 날짜 정보 추출
                pub_date = self._extract_date(item.get('pubDate', ''))
                if not pub_date:
                    continue
                
                # 연도가 여행 연도와 일치하는지 확인
                if pub_date.year != target_year:
                    logger.info(f"연도 불일치 제외: {item.get('title', '')} - {pub_date.year}년 (목표: {target_year}년)")
                    continue
                
                # 여행 기간과 비교 (월/일만)
                if self._is_date_in_range(pub_date, start_date, end_date):
                    event = {
                        'name': self._clean_title(item.get('title', '')),
                        'date': pub_date.strftime("%Y-%m-%d"),
                        'description': self._clean_description(item.get('description', '')),
                        'location': destination,
                        'type': '뉴스',
                        'website': item.get('link', ''),
                        'ticket_info': None,
                        'source': 'naver_news',
                        'relevance_score': 0
                    }
                    events.append(event)
                    logger.info(f"뉴스 이벤트 추가: {event['name']} ({event['date']}) - {destination}")
                else:
                    logger.info(f"날짜 범위 밖 제외: {item.get('title', '')} - {pub_date.strftime('%Y-%m-%d')}")
                    
            except Exception as e:
                logger.warning(f"뉴스 결과 처리 중 오류: {e}")
                continue
        
        return events
    
    def _process_blog_results(self, results: dict, destination: str, start_date: str, end_date: str) -> List[dict]:
        """블로그 검색 결과를 처리하여 이벤트 정보로 변환"""
        events = []
        
        if 'items' not in results:
            return events
        
        # 여행 기간 파싱
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        target_year = start_dt.year
        current_date = datetime.now().date()  # 현재 날짜
        
        for item in results['items']:
            try:
                # 블로그는 날짜 정보가 부정확할 수 있으므로 키워드 기반으로 필터링
                title = item.get('title', '').lower()
                description = item.get('description', '').lower()
                
                # 목적지가 제목이나 설명에 포함되어 있는지 확인 (지역명, 약칭, 별칭 포함)
                destination_variants = self._get_destination_variants(destination)
                has_destination = any(variant in title or variant in description for variant in destination_variants)
                
                if not has_destination:
                    logger.info(f"블로그 목적지 불일치 제외: {item.get('title', '')} - 목적지: {destination}")
                    continue
                
                # 연도가 제목이나 설명에 명시적으로 포함되어 있는지 확인
                year_in_title = str(target_year) in title
                year_in_description = str(target_year) in description
                
                # 축제/행사 관련 키워드 확인
                event_keywords = ['축제', '행사', '이벤트', '페스티벌', '전시회', '공연', '쇼']
                has_event_keywords = any(keyword in title or keyword in description for keyword in event_keywords)
                
                # 연도와 이벤트 키워드가 모두 있는 경우만 포함
                if (year_in_title or year_in_description) and has_event_keywords:
                    # 여행 시작일이 현재 날짜보다 과거인지 확인
                    if start_dt.date() < current_date:
                        logger.info(f"블로그 과거 여행 제외: {start_date} (현재: {current_date})")
                        continue
                    
                    event = {
                        'name': self._clean_title(item.get('title', '')),
                        'date': start_date,  # 블로그는 정확한 날짜를 알기 어려우므로 여행 시작일로 설정
                        'description': self._clean_description(item.get('description', '')),
                        'location': destination,
                        'type': '블로그 정보',
                        'website': item.get('link', ''),
                        'ticket_info': None,
                        'source': 'naver_blog',
                        'relevance_score': 0
                    }
                    events.append(event)
                    logger.info(f"블로그 이벤트 추가: {event['name']} (연도 확인됨) - {destination}")
                else:
                    logger.info(f"블로그 제외: {item.get('title', '')} - 연도 또는 키워드 부족")
                    
            except Exception as e:
                logger.warning(f"블로그 결과 처리 중 오류: {e}")
                continue
        
        return events
    
    def _process_web_results(self, results: dict, destination: str, start_date: str, end_date: str) -> List[dict]:
        """웹문서 검색 결과를 처리하여 이벤트 정보로 변환"""
        events = []
        
        if 'items' not in results:
            return events
        
        # 여행 기간 파싱
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        target_year = start_dt.year
        current_date = datetime.now().date()  # 현재 날짜
        
        for item in results['items']:
            try:
                title = item.get('title', '').lower()
                description = item.get('description', '').lower()
                
                # 목적지가 제목이나 설명에 포함되어 있는지 확인 (지역명, 약칭, 별칭 포함)
                destination_variants = self._get_destination_variants(destination)
                has_destination = any(variant in title or variant in description for variant in destination_variants)
                
                if not has_destination:
                    logger.info(f"웹문서 목적지 불일치 제외: {item.get('title', '')} - 목적지: {destination}")
                    continue
                
                # 연도가 제목이나 설명에 명시적으로 포함되어 있는지 확인
                year_in_title = str(target_year) in title
                year_in_description = str(target_year) in description
                
                # 축제/행사 관련 키워드 확인
                event_keywords = ['축제', '행사', '이벤트', '페스티벌', '전시회', '공연', '쇼']
                has_event_keywords = any(keyword in title or keyword in description for keyword in event_keywords)
                
                # 연도와 이벤트 키워드가 모두 있는 경우만 포함
                if (year_in_title or year_in_description) and has_event_keywords:
                    # 여행 시작일이 현재 날짜보다 과거인지 확인
                    if start_dt.date() < current_date:
                        logger.info(f"웹문서 과거 여행 제외: {start_date} (현재: {current_date})")
                        continue
                    
                    event = {
                        'name': self._clean_title(item.get('title', '')),
                        'date': start_date,  # 웹문서도 정확한 날짜를 알기 어려움
                        'description': self._clean_description(item.get('description', '')),
                        'location': destination,
                        'type': '웹문서',
                        'website': item.get('link', ''),
                        'ticket_info': None,
                        'source': 'naver_web',
                        'relevance_score': 0
                    }
                    events.append(event)
                    logger.info(f"웹문서 이벤트 추가: {event['name']} (연도 확인됨) - {destination}")
                else:
                    logger.info(f"웹문서 제외: {item.get('title', '')} - 연도 또는 키워드 부족")
                    
            except Exception as e:
                logger.warning(f"웹문서 결과 처리 중 오류: {e}")
                continue
        
        return events
    
    def _extract_date(self, date_str: str) -> Optional[datetime]:
        """문자열에서 날짜 정보를 추출"""
        try:
            # 다양한 날짜 형식 처리
            date_patterns = [
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{1,2})월\s*(\d{1,2})일',
                r'(\d{4})년\s*(\d{1,2})월'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    if len(match.groups()) == 3:
                        year, month, day = map(int, match.groups())
                        return datetime(year, month, day)
                    elif len(match.groups()) == 2:
                        month, day = map(int, match.groups())
                        # 현재 연도 사용
                        current_year = datetime.now().year
                        return datetime(current_year, month, day)
            
            return None
            
        except Exception as e:
            logger.warning(f"날짜 추출 실패: {date_str}, {e}")
            return None
    
    def _is_date_in_range(self, event_date: datetime, start_date: str, end_date: str) -> bool:
        """이벤트 날짜가 여행 기간 내에 있는지 확인"""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            current_date = datetime.now().date()  # 현재 날짜
            
            # 이미 지난 이벤트는 제외
            if event_date.date() < current_date:
                logger.info(f"과거 이벤트 제외: {event_date.strftime('%Y-%m-%d')} (현재: {current_date})")
                return False
            
            # 여행 기간 내에 있는지 정확하게 확인 (연도 포함)
            if start_dt <= event_date <= end_dt:
                logger.info(f"여행 기간 내 이벤트: {event_date.strftime('%Y-%m-%d')} (여행: {start_date} ~ {end_date})")
                return True
            
            # 연도가 바뀌는 경우 (예: 12월 31일 ~ 1월 2일) - 월/일만 비교
            if start_dt.month > end_dt.month:
                # 여행이 연도를 걸치는 경우
                event_month_day = (event_date.month, event_date.day)
                start_month_day = (start_dt.month, start_dt.day)
                end_month_day = (end_dt.month, end_dt.day)
                
                # 월/일 기준으로 매칭
                if (event_month_day >= start_month_day) or (event_month_day <= end_month_day):
                    logger.info(f"연도 걸친 여행 기간 내 이벤트: {event_date.strftime('%Y-%m-%d')} (여행: {start_date} ~ {end_date})")
                    return True
            
            # 여행 기간 밖의 이벤트는 제외
            logger.info(f"여행 기간 밖 이벤트 제외: {event_date.strftime('%Y-%m-%d')} (여행: {start_date} ~ {end_date})")
            return False
            
        except Exception as e:
            logger.warning(f"날짜 범위 확인 실패: {e}")
            return False
    
    def _clean_title(self, title: str) -> str:
        """제목에서 HTML 태그와 불필요한 문자 제거"""
        # HTML 태그 제거
        title = re.sub(r'<[^>]+>', '', title)
        # 특수 문자 정리
        title = re.sub(r'[^\w\s가-힣]', '', title)
        return title.strip()
    
    def _clean_description(self, description: str) -> str:
        """설명에서 HTML 태그와 불필요한 문자 제거"""
        # HTML 태그 제거
        description = re.sub(r'<[^>]+>', '', description)
        # 특수 문자 정리
        description = re.sub(r'[^\w\s가-힣]', '', description)
        return description.strip()
    
    def _remove_duplicates(self, events: List[dict]) -> List[dict]:
        """중복 이벤트 제거"""
        seen = set()
        unique_events = []
        
        for event in events:
            # 제목과 설명을 기반으로 중복 확인
            key = (event['name'], event['description'][:50])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
    
    def _calculate_relevance_scores(self, events: List[dict], destination: str, start_date: str, end_date: str) -> List[dict]:
        """이벤트의 관련성 점수를 계산하고 정렬"""
        target_year = datetime.strptime(start_date, "%Y-%m-%d").year
        current_date = datetime.now().date()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        for event in events:
            score = 0
            
            # 제목과 설명에서 관련 키워드 확인
            title = event['name'].lower()
            description = event['description'].lower()
            
            # 목적지 관련성 (가장 중요)
            destination_variants = self._get_destination_variants(destination)
            destination_score = 0
            
            # 정확한 지역명 매칭을 위한 강화된 필터링
            exact_location_match = False
            other_location_penalty = 0
            
            # 제목에서 목적지 확인
            for variant in destination_variants:
                if variant in title:
                    destination_score += 8  # 제목에 목적지가 있으면 매우 높은 점수
                    exact_location_match = True
                    break
            
            # 설명에서 목적지 확인
            if destination_score == 0:  # 제목에 없었다면
                for variant in destination_variants:
                    if variant in description:
                        destination_score += 5  # 설명에 목적지가 있으면 높은 점수
                        exact_location_match = True
                        break
            
            # 다른 강원도 지역명이 있는지 확인하여 점수 차감
            if destination.lower() in ["강릉", "속초", "춘천", "평창", "원주", "동해", "태백", "삼척"]:
                gangwon_cities = ["강릉", "속초", "춘천", "평창", "원주", "동해", "태백", "삼척"]
                for city in gangwon_cities:
                    if city != destination.lower() and city in title.lower():
                        other_location_penalty = -10  # 다른 강원도 도시명이 있으면 큰 점수 차감
                        logger.info(f"다른 강원도 도시 {city} 발견으로 점수 차감: {event['name']}")
                        break
                    elif city != destination.lower() and city in description.lower():
                        other_location_penalty = -5  # 설명에 다른 도시명이 있으면 점수 차감
                        break
            
            score += destination_score + other_location_penalty
            
            # 연도 일치
            if str(target_year) in title:
                score += 10  # 제목에 연도가 있으면 매우 높은 점수
            elif str(target_year) in description:
                score += 8   # 설명에 연도가 있으면 높은 점수
            
            # 여행 기간 내 정확한 날짜 매칭 (가장 중요)
            try:
                event_date = datetime.strptime(event['date'], "%Y-%m-%d")
                if start_dt <= event_date <= end_dt:
                    score += 15  # 여행 기간 내 정확한 날짜는 매우 높은 점수
                    logger.info(f"여행 기간 내 정확한 날짜 매칭: {event['name']} ({event['date']}) - +15점")
                elif start_dt.month > end_dt.month:  # 연도 걸친 여행
                    event_month_day = (event_date.month, event_date.day)
                    start_month_day = (start_dt.month, start_dt.day)
                    end_month_day = (end_dt.month, end_dt.day)
                    if (event_month_day >= start_month_day) or (event_month_day <= end_month_day):
                        score += 12  # 연도 걸친 여행 기간 내 날짜는 높은 점수
                        logger.info(f"연도 걸친 여행 기간 내 날짜 매칭: {event['name']} ({event['date']}) - +12점")
            except:
                pass  # 날짜 파싱 실패 시 점수 추가하지 않음
            
            # 미래 이벤트 키워드 (예정, 일정 등)
            future_keywords = ['예정', '일정', '개최', '진행', '열린다', '개막', '시작']
            for keyword in future_keywords:
                if keyword in title:
                    score += 4
                if keyword in description:
                    score += 3
            
            # 축제/행사 키워드
            event_keywords = ['축제', '행사', '이벤트', '페스티벌', '전시회', '공연', '쇼']
            for keyword in event_keywords:
                if keyword in title:
                    score += 3
                if keyword in description:
                    score += 2
            
            # 날짜 정확성
            if event['source'] == 'naver_news':
                score += 5  # 뉴스는 날짜가 더 정확함
            elif event['source'] == 'naver_blog':
                score += 3  # 블로그는 중간
            elif event['source'] == 'naver_web':
                score += 2  # 웹문서는 낮음
            
            # 정보 품질
            if len(event['description']) > 50:
                score += 2
            
            # 제목 길이 (너무 짧거나 긴 것은 제외)
            if 10 <= len(event['name']) <= 100:
                score += 1
            
            event['relevance_score'] = score
        
        # 점수가 0 이하인 이벤트 필터링 (관련성이 떨어지는 결과 제외)
        filtered_events = [event for event in events if event['relevance_score'] > 0]
        
        # 점수순으로 정렬
        return sorted(filtered_events, key=lambda x: x['relevance_score'], reverse=True)

    def _get_destination_variants(self, destination: str) -> List[str]:
        """목적지의 다양한 변형(약칭, 별칭, 구/군 단위 등)을 반환"""
        variants = [destination.lower()]  # 원본 지역명
        
        # 지역별 약칭 및 별칭 추가
        destination_mapping = {
            "부산": ["부산", "부산시", "부산광역시", "해운대", "서면", "남포동", "광안리", "동래", "부산진"],
            "서울": ["서울", "서울시", "서울특별시", "강남", "홍대", "명동", "이태원", "잠실", "강북"],
            "제주도": ["제주", "제주도", "제주시", "서귀포", "애월", "성산", "한라산", "제주특별자치도"],
            "여수": ["여수", "여수시", "여수항", "돌산공원", "여수엑스포"],
            "도쿄": ["도쿄", "tokyo", "신주쿠", "시부야", "하라주쿠", "우에노", "아사쿠사"],
            "파리": ["파리", "paris", "몽마르트", "샹젤리제", "루브르", "에펠탑"],
            "세종": ["세종", "세종시", "세종특별자치시", "세종특별자치도"],
            "대구": ["대구", "대구시", "대구광역시", "동성로", "서문시장", "수성구"],
            "인천": ["인천", "인천시", "인천광역시", "송도", "월미도", "인천공항"],
            "광주": ["광주", "광주시", "광주광역시", "유스퀘어", "상무지구"],
            "대전": ["대전", "대전시", "대전광역시", "유성구", "중앙로"],
            "울산": ["울산", "울산시", "울산광역시", "울산항", "태화강"],
            "수원": ["수원", "수원시", "경기도수원시", "화성", "수원화성"],
            "고양": ["고양", "고양시", "경기도고양시", "일산", "덕양구"],
            "용인": ["용인", "용인시", "경기도용인시", "에버랜드", "기흥구"],
            "성남": ["성남", "성남시", "경기도성남시", "분당", "판교"],
            "부천": ["부천", "부천시", "경기도부천시", "상동", "중동"],
            # 강원도 지역별 세부 매핑 추가 - 각 도시별로 독립적으로 검색되도록 설정
            "강릉": ["강릉", "강릉시", "강원도강릉시", "강릉해변", "강릉시내", "경포대", "정동진"],
            "속초": ["속초", "속초시", "강원도속초시", "속초해수욕장", "속초항", "설악산입구"],
            "춘천": ["춘천", "춘천시", "강원도춘천시", "남이섬", "춘천호", "명동거리"],
            "평창": ["평창", "평창군", "강원도평창군", "평창올림픽", "대관령", "용평리조트"],
            "원주": ["원주", "원주시", "강원도원주시", "원주시내", "치악산"],
            "동해": ["동해", "동해시", "강원도동해시", "동해항", "망상해수욕장"],
            "태백": ["태백", "태백시", "강원도태백시", "태백산", "태백시내"],
            "삼척": ["삼척", "삼척시", "강원도삼척시", "삼척해변", "환선굴", "용화해수욕장"],
            "안산": ["안산", "안산시", "경기도안산시", "단원구", "상록구"],
            "안양": ["안양", "안양시", "경기도안양시", "만안구", "동안구"],
            "평택": ["평택", "평택시", "경기도평택시", "평택항", "송탄"],
            "시흥": ["시흥", "시흥시", "경기도시흥시", "정왕동", "연성동"],
            "김포": ["김포", "김포시", "경기도김포시", "김포공항", "운양동"],
            "화성": ["화성", "화성시", "경기도화성시", "오산", "병점"],
            "광명": ["광명", "광명시", "경기도광명시", "철산동", "광명동"],
            "군포": ["군포", "군포시", "경기도군포시", "산본동", "금정동"],
            "오산": ["오산", "오산시", "경기도오산시", "오산동", "청호동"],
            "이천": ["이천", "이천시", "경기도이천시", "장호원", "마장"],
            "안성": ["안성", "안성시", "경기도안성시", "공도", "보개"],
            "포천": ["포천", "포천시", "경기도포천시", "운악산", "소흘"],
            "양평": ["양평", "양평군", "경기도양평군", "양수리", "청운"],
            "여주": ["여주", "여주시", "경기도여주시", "가남", "능서"],
            "양주": ["양주", "양주시", "경기도양주시", "회천", "백석"],
            "동두천": ["동두천", "동두천시", "경기도동두천시", "생연동", "보산동"],
            "가평": ["가평", "가평군", "경기도가평군", "청평", "설악"],
            "연천": ["연천", "연천군", "경기도연천군", "전곡", "청산"],
            "과천": ["과천", "과천시", "경기도과천시", "과천동", "문원동"],
            "의왕": ["의왕", "의왕시", "경기도의왕시", "왕곡동", "오전동"],
            "하남": ["하남", "하남시", "경기도하남시", "하남동", "광주동"],
            "구리": ["구리", "구리시", "경기도구리시", "인창동", "교문동"],
            "남양주": ["남양주", "남양주시", "경기도남양주시", "와부", "진건"],
            "파주": ["파주", "파주시", "경기도파주시", "운정", "문산"],
            "고양": ["고양", "고양시", "경기도고양시", "일산", "덕양구"],
            "의정부": ["의정부", "의정부시", "경기도의정부시", "의정부동", "호원동"],
            "양주": ["양주", "양주시", "경기도양주시", "회천", "백석"],
            "동두천": ["동두천", "동두천시", "경기도동두천시", "생연동", "보산동"],
            "가평": ["가평", "가평군", "경기도가평군", "청평", "설악"],
            "연천": ["연천", "연천군", "경기도연천군", "전곡", "청산"],
            "과천": ["과천", "과천시", "경기도과천시", "과천동", "문원동"],
            "의왕": ["의왕", "의왕시", "경기도의왕시", "왕곡동", "오전동"],
            "하남": ["하남", "하남시", "경기도하남시", "하남동", "광주동"],
            "구리": ["구리", "구리시", "경기도구리시", "인창동", "교문동"],
            "남양주": ["남양주", "남양주시", "경기도남양주시", "와부", "진건"],
            "파주": ["파주", "파주시", "경기도파주시", "운정", "문산"],
            "고양": ["고양", "고양시", "경기도고양시", "일산", "덕양구"],
            "의정부": ["의정부", "의정부시", "경기도의정부시", "의정부동", "호원동"]
        }
        
        # 매핑된 지역명이 있으면 해당 변형들 추가
        if destination in destination_mapping:
            variants.extend([v.lower() for v in destination_mapping[destination]])
        
        # 일반적인 지역명 패턴 추가
        if "시" in destination:
            variants.append(destination.replace("시", "").lower())
        if "도" in destination:
            variants.append(destination.replace("도", "").lower())
        if "군" in destination:
            variants.append(destination.replace("군", "").lower())
        
        # 중복 제거 및 반환
        return list(set(variants))

# ========================================
# 카카오 로컬 API 서비스 클래스
# ========================================
class KakaoLocalService:
    """카카오 로컬 API를 사용하여 장소 검색 및 검증을 수행하는 서비스"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or kakao_api_key
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        
    def search_place(self, query: str, region: str = None) -> dict:
        """
        카카오 로컬 API를 사용하여 장소를 검색합니다.
        
        Args:
            query: 검색할 장소명
            region: 지역 필터 (선택사항)
            
        Returns:
            검색 결과 딕셔너리 (장소 정보 포함)
        """
        if not self.api_key:
            logger.warning("카카오 API 키가 없어 장소 검색을 건너뜁니다.")
            return None
            
        headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        }
        
        params = {
            "query": query,
            "size": 5  # 최대 5개 결과만 가져오기
        }
        
        # 지역이 지정된 경우 검색어에 포함
        if region:
            params["query"] = f"{region} {query}"
            
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('documents', [])
            
            if documents:
                # 첫 번째 결과 반환 (가장 관련성 높은 결과)
                place = documents[0]
                return {
                    'found': True,
                    'name': place.get('place_name', ''),
                    'address': place.get('address_name', ''),
                    'road_address': place.get('road_address_name', ''),
                    'category': place.get('category_name', ''),
                    'phone': place.get('phone', ''),
                    'x': place.get('x', ''),  # 경도
                    'y': place.get('y', ''),  # 위도
                    'url': place.get('place_url', '')
                }
            else:
                logger.warning(f"카카오 API에서 '{query}' 장소를 찾을 수 없습니다.")
                return {'found': False, 'query': query}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"카카오 API 요청 실패: {str(e)}")
            return {'found': False, 'error': str(e), 'query': query}
            
    def _clean_place_name(self, place_name: str) -> str:
        """장소명에서 불필요한 단어들을 제거합니다."""
        # 불필요한 단어들 제거
        remove_words = [
            '방문', '관람', '투어', '체험', '구경', '산책', '둘러보기', '탐방', '견학',
            '가기', '보기', '하기', '즐기기', '걷기', '오르기', '내려가기', '올라가기',
            '에서', '까지', '으로', '를', '을', '의', '에', '와', '과', '도', '만',
            '점심', '저녁', '아침', '식사', '먹기', '맛보기', '시식',
            '휴식', '쉬기', '잠시', '잠깐', '구입', '쇼핑', '구매'
        ]
        
        cleaned = place_name
        for word in remove_words:
            cleaned = cleaned.replace(word, '').strip()
        
        return cleaned if cleaned else place_name

    def _is_relevant_result(self, search_keyword: str, search_result: dict, original_title: str) -> bool:
        """검색 결과가 원본 키워드와 관련성이 있는지 확인합니다."""
        result_name = search_result.get('name', '').lower()
        result_category = search_result.get('category', '').lower()
        
        # 원본 제목과 검색 키워드에서 핵심 키워드 추출
        original_keywords = self._extract_core_keywords(original_title.lower())
        search_keywords = self._extract_core_keywords(search_keyword.lower())
        
        # 핵심 키워드가 검색 결과에 포함되어 있는지 확인
        for keyword in original_keywords + search_keywords:
            if len(keyword) > 2 and keyword in result_name:
                return True
        
        # 부적절한 카테고리 필터링 (요양, 병원, 의료 등)
        inappropriate_categories = [
            '요양', '병원', '의료', '클리닉', '한의원', '치과', '약국',
            '부동산', '학원', '학교', '사무실', '회사'
        ]
        
        for inappropriate in inappropriate_categories:
            if inappropriate in result_name or inappropriate in result_category:
                logger.warning(f"부적절한 카테고리 감지: {result_name} ({result_category})")
                return False
        
        return True
    
    def _extract_core_keywords(self, text: str) -> list:
        """텍스트에서 핵심 키워드를 추출합니다."""
        import re
        
        # 한글, 영문, 숫자만 남기고 나머지 제거
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        words = cleaned.split()
        
        # 의미있는 키워드만 추출 (2글자 이상)
        core_keywords = []
        for word in words:
            if len(word) >= 2:
                core_keywords.append(word)
        
        return core_keywords

    def _extract_specific_place_names(self, title: str) -> list:
        """제목에서 구체적인 장소명을 우선적으로 추출합니다."""
        import re
        
        candidates = []
        
        # 1. 복합 장소명 패턴 (예: "경주 양동마을", "부산 해운대 해수욕장")
        # 지역명 + 구체적 장소명 패턴
        region_place_patterns = [
            r'(\w+)\s+(\w+마을)',      # 경주 양동마을
            r'(\w+)\s+(\w+\s*해수욕장)', # 부산 해운대 해수욕장
            r'(\w+)\s+(\w+\s*유적지)',   # 경주 월성 유적지
            r'(\w+)\s+(\w+\s*박물관)',   # 경주 국립박물관
            r'(\w+)\s+(\w+\s*공원)',     # 부산 용두산 공원
            r'(\w+)\s+(\w+\s*사찰)',     # 경주 불국사
            r'(\w+)\s+(\w+\s*궁)',       # 경주 동궁
            r'(\w+)\s+(\w+\s*성)',       # 경주 월성
            r'(\w+)\s+(\w+\s*터)',       # 경주 첨성대터
            r'(\w+)\s+(\w+\s*다리)',     # 부산 광안대교
            r'(\w+)\s+(\w+\s*시장)',     # 부산 자갈치시장
        ]
        
        for pattern in region_place_patterns:
            matches = re.findall(pattern, title)
            for match in matches:
                if len(match) == 2:
                    region, place = match
                    # 전체 장소명을 우선순위로
                    full_place = f"{region} {place}".strip()
                    candidates.append(full_place)
                    # 구체적인 장소명만도 추가 (2순위)
                    if place.strip() not in candidates:
                        candidates.append(place.strip())
        
        # 2. 단독 구체적 장소명 패턴
        specific_patterns = [
            r'(\w+마을)',      # 양동마을, 하회마을
            r'(\w+\s*해수욕장)', # 해운대해수욕장, 광안리 해수욕장
            r'(\w+\s*해변)',     # 정동진 해변, 경포 해변
            r'(\w+\s*유적지)',   # 월성 유적지, 대릉원 유적지
            r'(\w+\s*박물관)',   # 국립경주박물관, 부산시립박물관
            r'(\w+\s*미술관)',   # 부산시립미술관
            r'(\w+\s*공원)',     # 용두산공원, 해운대공원
            r'(\w+사)',         # 불국사, 석굴암
            r'(\w+궁)',         # 동궁, 월궁
            r'(\w+성)',         # 월성, 동성
            r'(\w+대)',         # 첨성대, 석빙고
            r'(\w+\s*다리)',     # 광안대교, 부산대교
            r'(\w+\s*시장)',     # 자갈치시장, 국제시장
            r'(\w+\s*타워)',     # 부산타워, 롯데타워
            r'(\w+\s*센터)',     # 벡스코, 문화센터
            r'(\w+\s*역)',       # 정동진역, 강릉역
        ]
        
        for pattern in specific_patterns:
            matches = re.findall(pattern, title)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 1:
                    # 부적절한 단어 필터링
                    if self._is_real_place_name(match.strip()) and match.strip() not in candidates:
                        candidates.append(match.strip())
        
        return candidates

    def _extract_place_name_from_title(self, title: str) -> list:
        """제목에서 실제 장소명을 추출합니다."""
        import re
        
        # 장소명 후보들
        candidates = []
        
        # 1. 구체적인 장소명 패턴 우선 추출 (가장 중요!)
        specific_place_candidates = self._extract_specific_place_names(title)
        candidates.extend(specific_place_candidates)
        
        # 2. 정제된 제목 (불필요한 단어 제거)
        cleaned_title = self._clean_place_name(title)
        if cleaned_title and cleaned_title != title and len(cleaned_title.strip()) > 1:
            # 이미 구체적인 장소명이 있으면 중복 방지
            if cleaned_title.strip() not in candidates:
                candidates.append(cleaned_title.strip())
        
        # 3. 괄호 안 내용 제거
        no_brackets = re.sub(r'\([^)]*\)', '', title).strip()
        if no_brackets and no_brackets != title and len(no_brackets.strip()) > 1:
            # 불필요한 단어도 함께 제거
            no_brackets_cleaned = self._clean_place_name(no_brackets)
            if no_brackets_cleaned and no_brackets_cleaned not in candidates:
                candidates.append(no_brackets_cleaned)
        
        # 4. 마지막 단어 제거 (보통 동작 단어)
        words = title.split()
        if len(words) > 1:
            without_last = ' '.join(words[:-1]).strip()
            if len(without_last) > 1 and without_last not in candidates:
                candidates.append(without_last)
        
        # 5. 첫 번째 단어만 (지역명, 최후 수단)
        first_word = title.split()[0] if title.split() else ""
        if first_word and len(first_word) > 1 and first_word not in candidates:
            candidates.append(first_word)
        
        # 중복 제거 및 빈 문자열 제거
        unique_candidates = []
        for candidate in candidates:
            candidate = candidate.strip()
            if candidate and candidate not in unique_candidates and len(candidate) > 1:
                unique_candidates.append(candidate)
        
        return unique_candidates

    def _is_detailed_address(self, text: str) -> bool:
        """텍스트가 상세 주소인지 확인합니다."""
        import re
        
        # 상세 주소 패턴 (시/군/구/동/리/면 등이 포함된 경우)
        address_patterns = [
            r'\w+시\s+\w+구',      # 서울시 강남구
            r'\w+시\s+\w+군',      # 경기도 평택시
            r'\w+도\s+\w+시',      # 경기도 수원시
            r'\w+시\s+\w+면',      # 강릉시 강동면
            r'\w+구\s+\w+동',      # 강남구 역삼동
            r'\w+동\s+\w+리',      # 강동면 정동진리
            r'\w+면\s+\w+리',      # 강동면 정동진리
            r'\d+번지',            # 123번지
            r'\d+-\d+',            # 123-45
        ]
        
        for pattern in address_patterns:
            if re.search(pattern, text):
                return True
                
        # 주소 키워드가 많이 포함된 경우
        address_keywords = ['시', '군', '구', '동', '리', '면', '번지', '로', '길']
        keyword_count = sum(1 for keyword in address_keywords if keyword in text)
        
        # 3개 이상의 주소 키워드가 있으면 상세 주소로 판단
        return keyword_count >= 3

    def _is_real_place_name(self, text: str) -> bool:
        """텍스트가 실제 장소명인지 확인합니다."""
        import re
        
        # 명확한 장소명 패턴들
        place_patterns = [
            r'\w+성$',          # 동래읍성, 경복궁성
            r'\w+궁$',          # 경복궁, 창덕궁
            r'\w+사$',          # 불국사, 해인사
            r'\w+암$',          # 석굴암, 보문암
            r'\w+대$',          # 첨성대, 석빙고
            r'\w+관$',          # 박물관, 미술관
            r'\w+원$',          # 공원, 동물원
            r'\w+장$',          # 시장, 광장
            r'\w+교$',          # 다리 (광안대교)
            r'\w+탑$',          # 탑, 타워
            r'\w+마을$',        # 양동마을, 하회마을
            r'\w+해변$',        # 정동진해변
            r'\w+해수욕장$',    # 해운대해수욕장
            r'\w+유적지$',      # 월성유적지
            r'\w+센터$',        # 문화센터
            r'\w+역$',          # 기차역
        ]
        
        for pattern in place_patterns:
            if re.search(pattern, text):
                return True
        
        # 부적절한 단어들 (장소명이 아닌 것들)
        non_place_words = [
            '역사', '문화', '전통', '체험', '관람', '구경', '산책', '탐방',
            '방문', '투어', '여행', '휴식', '감상', '관찰', '학습'
        ]
        
        # 단일 단어이면서 부적절한 단어인 경우
        if text.strip() in non_place_words:
            return False
            
        return True  # 기본적으로는 장소명으로 간주

    def verify_and_enrich_location(self, activity: dict, region: str = None) -> dict:
        """
        활동 정보의 장소를 검증하고 정확한 정보로 보강합니다.
        
        Args:
            activity: 활동 정보 딕셔너리
            region: 지역명 (검색 정확도 향상용)
            
        Returns:
            검증 및 보강된 활동 정보
        """
        title = activity.get('title', '')
        location = activity.get('location', '')
        
        logger.info(f"🔍 장소 검증 시작: '{title}' (location: '{location}')")
        
        # 검색 키워드 우선순위 생성
        search_keywords = []
        
        # 1. location이 구체적인 장소명이면 최우선 (상세주소가 아닌 경우만)
        if location and location.strip() and not self._is_detailed_address(location.strip()):
            # location이 실제 장소명인지 확인
            if self._is_real_place_name(location.strip()):
                search_keywords.append(location.strip())
                # location에서도 불필요한 단어 제거한 버전
                cleaned_location = self._clean_place_name(location.strip())
                if cleaned_location != location.strip() and cleaned_location not in search_keywords:
                    search_keywords.append(cleaned_location)
        
        # 2. title에서 구체적인 장소명 추출
        extracted_places = self._extract_place_name_from_title(title)
        # location과 중복되지 않는 것만 추가
        for place in extracted_places:
            if place not in search_keywords:
                search_keywords.append(place)
        
        # 3. location이 상세 주소인 경우 처리
        if location and location.strip() and self._is_detailed_address(location.strip()):
            # 상세 주소는 후순위로 (보조 수단)
            logger.info(f"상세 주소 감지, 후순위로 이동: {location.strip()}")
        elif location and location.strip() and not self._is_real_place_name(location.strip()):
            # location이 장소명이 아닌 경우도 후순위로
            logger.info(f"일반적이지 않은 location, 후순위로 이동: {location.strip()}")
        
        # 3. 원본 title도 포함 (중간 순위)
        if title not in search_keywords:
            search_keywords.append(title)
            
        # 4. 상세 주소는 최후 수단으로만 사용
        if location and location.strip() and self._is_detailed_address(location.strip()):
            if location.strip() not in search_keywords:
                search_keywords.append(location.strip())
        
        logger.info(f"🔍 검색 키워드 목록: {search_keywords}")
        
        # 키워드별로 순차 검색
        search_result = None
        successful_keyword = None
        
        for keyword in search_keywords:
            if not keyword or len(keyword.strip()) < 2:
                continue
                
            logger.info(f"🔍 키워드로 검색 중: '{keyword}'")
            search_result = self.search_place(keyword, region)
            
            if search_result and search_result.get('found'):
                # 검색 결과의 관련성 검증
                if self._is_relevant_result(keyword, search_result, title):
                    successful_keyword = keyword
                    logger.info(f"✅ 검색 성공: '{keyword}' -> {search_result.get('name')}")
                    break
                else:
                    logger.info(f"❌ 검색 결과 관련성 낮음: '{keyword}' -> {search_result.get('name')}")
                    search_result = None
            else:
                logger.info(f"❌ 검색 실패: '{keyword}'")
        
        # 검증된 정보로 활동 정보 업데이트
        if search_result and search_result.get('found'):
            activity['verified'] = True
            activity['real_address'] = search_result.get('road_address') or search_result.get('address')
            activity['place_category'] = search_result.get('category')
            activity['place_telephone'] = search_result.get('phone')
            activity['coordinates'] = {
                'lat': float(search_result.get('y', 0)) if search_result.get('y') else None,
                'lng': float(search_result.get('x', 0)) if search_result.get('x') else None
            }
            
            # 정확한 장소명으로 업데이트
            if search_result.get('name'):
                activity['verified_name'] = search_result.get('name')
                activity['location'] = search_result.get('road_address') or search_result.get('address') or activity['location']
                
            logger.info(f"🎉 장소 검증 완료: '{title}' -> '{search_result.get('name')}' (키워드: '{successful_keyword}')")
            logger.info(f"   주소: {activity['real_address']}")
            logger.info(f"   카테고리: {activity['place_category']}")
        else:
            activity['verified'] = False
            # 검증 실패한 경우 가짜 주소 표시 방지
            activity['location'] = f"⚠️ {activity.get('location', '')} (검증되지 않은 주소)"
            activity['real_address'] = "검증되지 않은 주소입니다"
            logger.warning(f"⚠️ 장소 검증 실패: '{title}' - 모든 키워드로 검색했지만 찾을 수 없습니다")
            logger.warning(f"   시도한 키워드: {search_keywords}")
            
        return activity

# ========================================
# 여행 데이터 검증 및 보강 함수
# ========================================
async def verify_and_enrich_trip_data(trip_data: dict, kakao_service: KakaoLocalService, destination: str) -> dict:
    """
    여행 계획 데이터의 모든 장소를 카카오 API로 검증하고 보강합니다.
    검증에 실패한 장소가 있으면 해당 활동만 다시 생성합니다.
    """
    if not trip_data.get("itinerary"):
        return trip_data
    
    failed_activities = []
    region = destination.split()[0]  # 지역명 추출 (예: "부산 해운대" -> "부산")
    
    # 각 일차별로 활동 검증
    for day_idx, day in enumerate(trip_data["itinerary"]):
        if not day.get("activities"):
            continue
            
        for activity_idx, activity in enumerate(day["activities"]):
            # 호텔/숙박 관련 활동은 검증하지 않음
            title = activity.get('title', '').lower()
            if any(keyword in title for keyword in ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out']):
                continue
            
            # 카카오 API로 장소 검증 및 보강
            verified_activity = kakao_service.verify_and_enrich_location(activity, region)
            
            # 검증 실패한 활동 기록
            if not verified_activity.get('verified', False):
                failed_activities.append({
                    'day_idx': day_idx,
                    'activity_idx': activity_idx,
                    'day': day.get('day'),
                    'original_activity': activity.copy()
                })
            
            # 검증된 정보로 업데이트
            day["activities"][activity_idx] = verified_activity
    
    # 검증 실패한 활동이 있으면 재생성
    if failed_activities:
        logger.info(f"검증 실패한 활동 {len(failed_activities)}개를 재생성합니다...")
        trip_data = await regenerate_failed_activities(trip_data, failed_activities, destination)
        
        # 재생성 후 중복 체크 및 제거
        logger.info("재생성 후 중복 장소 재검사를 시작합니다...")
        trip_data = await remove_duplicate_locations(trip_data, destination)
    
    return trip_data

async def regenerate_failed_activities(trip_data: dict, failed_activities: list, destination: str) -> dict:
    """
    검증에 실패한 활동들을 OpenAI로 다시 생성합니다.
    """
    for failed in failed_activities:
        day_idx = failed['day_idx']
        activity_idx = failed['activity_idx']
        day_num = failed['day']
        original = failed['original_activity']
        
        try:
            # 해당 일차의 다른 활동들 정보 수집
            day_activities = trip_data["itinerary"][day_idx]["activities"]
            other_activities = [act for i, act in enumerate(day_activities) if i != activity_idx]
            
            # 전체 여행 일정에서 이미 사용된 모든 장소들 수집 (중복 방지)
            all_used_locations = []
            for day_data in trip_data.get("itinerary", []):
                for activity in day_data.get("activities", []):
                    if activity.get('title') and activity.get('location'):
                        all_used_locations.append({
                            "title": activity.get('title'),
                            "location": activity.get('location'),
                            "day": day_data.get('day')
                        })
            
            # 재생성 프롬프트
            regeneration_prompt = f"""
검증에 실패한 "{original.get('title', '')}" 활동을 {destination} 지역의 **실제 존재하는 유명한 관광지**로 대체해주세요.

🚨 **중복 절대 금지**: 아래 이미 사용된 장소들과 절대 겹치면 안 됩니다:
{json.dumps(all_used_locations, ensure_ascii=False, indent=2)}

현재 {day_num}일차 다른 활동들:
{json.dumps(other_activities, ensure_ascii=False, indent=2)}

🚨 **절대 지켜야 할 규칙**:
1. **위에 나열된 이미 사용된 장소들과 절대 겹치면 안 됩니다** - 최우선 규칙!
2. **실제 존재하는 유명한 관광지만 사용** - 가짜 장소 절대 금지
3. {destination} 지역의 대표적인 랜드마크나 유명 관광지만 선택
4. 확실하지 않은 주소나 장소는 절대 사용하지 마세요
5. 기존 시간대({original.get('time', '')})와 비슷한 시간으로 설정
6. **반드시 구체적인 고유명사를 사용하세요**:
   ❌ 잘못된 예: "해변 산책", "시장 구경", "공원 방문", "○○동 762번지"
   ✅ 올바른 예: "해운대해수욕장", "자갈치시장", "남산공원"
7. location 필드는 유명한 관광지명이나 정확한 도로명주소만 사용
8. JSON 형식으로 단일 activity 객체만 반환

**{destination} 지역 유명 관광지 예시 참고**:
- 부산: 해운대해수욕장, 광안리해변, 자갈치시장, 감천문화마을, 태종대
- 서울: 경복궁, 남산타워, 명동, 인사동, 한강공원
- 제주: 성산일출봉, 한라산, 천지연폭포, 협재해수욕장

🔑 **중요: location과 title 필드 구분**
- **location**: 실제 장소명만 (예: "해운대해수욕장", "자갈치시장")  
- **title**: 화면에 표시될 활동명 (예: "해운대 산책", "자갈치 시장 투어")

JSON 형식:
{{
    "time": "시간",
    "title": "활동명 (예: 해운대 산책)",
    "location": "실제 장소명만 (예: 해운대해수욕장)",
    "description": "활동 설명",
    "duration": "소요시간"
}}
"""
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 한국 관광 전문가입니다. 검증에 실패한 가짜 장소를 실제 존재하는 유명한 관광지로 교체해주세요. 🚨 최우선 규칙: 이미 사용된 장소들과 절대 중복되면 안 됩니다! 절대 가짜 주소나 존재하지 않는 장소를 만들어내지 마세요. 확실하지 않은 장소는 사용하지 말고 대표적인 유명 관광지만 선택하세요."},
                    {"role": "user", "content": regeneration_prompt}
                ],
                max_tokens=500,
                temperature=0.3  # 더 일관된 결과를 위해 온도 감소
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                new_activity = json.loads(json_str)
                
                # 새로운 활동으로 교체
                trip_data["itinerary"][day_idx]["activities"][activity_idx] = new_activity
                logger.info(f"{day_num}일차 활동 재생성 완료: {original.get('title')} -> {new_activity.get('title')}")
                
                # 재생성된 활동이 다른 날짜와 중복되는지 즉시 체크
                new_title = new_activity.get('title', '').lower()
                new_location = new_activity.get('location', '').lower()
                
                for check_day_idx, check_day in enumerate(trip_data.get("itinerary", [])):
                    if check_day_idx == day_idx:  # 같은 날은 건너뛰기
                        continue
                    for check_activity in check_day.get("activities", []):
                        check_title = check_activity.get('title', '').lower()
                        check_location = check_activity.get('location', '').lower()
                        
                        if (new_title and check_title and new_title in check_title) or \
                           (new_location and check_location and new_location in check_location):
                            logger.warning(f"🚨 재생성된 활동이 중복 의심: {day_num}일차 '{new_activity.get('title')}' vs {check_day.get('day')}일차 '{check_activity.get('title')}'")
                            
            else:
                logger.error(f"{day_num}일차 활동 재생성 실패: JSON 파싱 오류")
                
        except Exception as e:
            logger.error(f"{day_num}일차 활동 재생성 중 오류 발생: {str(e)}")
    
    return trip_data

# ========================================
# 중복 장소 제거 함수
# ========================================
def _extract_location_keywords(place_name: str, location_name: str) -> list:
    """장소명에서 중복 감지를 위한 키워드들을 추출합니다."""
    keywords = set()
    
    # 두 필드 모두에서 키워드 추출
    for text in [place_name, location_name]:
        if not text:
            continue
            
        # 기본 정규화 (공백, 특수문자 제거)
        normalized = ''.join(text.lower().split())
        keywords.add(normalized)
        
        # 주요 장소 키워드 추출
        location_keywords = _extract_major_location_keywords(text)
        keywords.update(location_keywords)
        
        # 핵심 장소명 추출 (더 정교한 추출)
        core_keywords = _extract_core_location_name(text)
        keywords.update(core_keywords)
    
    return list(filter(None, keywords))

def _extract_core_location_name(text: str) -> set:
    """텍스트에서 핵심 장소명을 추출합니다."""
    import re
    keywords = set()
    
    # 텍스트 정리
    text = text.lower().strip()
    
    # 1. 핵심 지명 패턴 추출
    core_patterns = [
        r'([가-힣]{2,}해수욕장|[가-힣]{2,}해변)',  # 해변/해수욕장
        r'([가-힣]{2,}시장)',                      # 시장
        r'([가-힣]{2,}궁|[가-힣]{2,}궁궐)',        # 궁궐
        r'([가-힣]{2,}사|[가-힣]{2,}절)',          # 사찰
        r'([가-힣]{2,}타워|[가-힣]{2,}탑)',        # 타워/탑
        r'([가-힣]{2,}공원)',                      # 공원
        r'([가-힣]{2,}박물관)',                    # 박물관
        r'([가-힣]{2,}미술관)',                    # 미술관
        r'([가-힣]{2,}폭포)',                      # 폭포
        r'([가-힣]{2,}산)',                        # 산
        r'([가-힣]{2,}봉)',                        # 봉우리
        r'([가-힣]{2,}다리)',                      # 다리
        r'([가-힣]{2,}항|[가-힣]{2,}포구)',        # 항구/포구
        r'([가-힣]{2,}마을)',                      # 마을
        r'([가-힣]{2,}거리|[가-힣]{2,}길)',        # 거리/길
        r'([가-힣]{2,}동)',                        # 동네
        r'([가-힣]{2,}구)',                        # 구
        r'([가-힣]{2,}섬|[가-힣]{2,}도)',          # 섬/도
    ]
    
    for pattern in core_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            keywords.add(match)
    
    # 2. 복합 지명에서 핵심 부분 추출
    # 예: "해운대해수욕장 산책" → "해운대", "해운대해수욕장"
    compound_patterns = [
        r'([가-힣]{2,})(해수욕장|해변|시장|궁|사|탑|타워|공원|박물관|미술관)',
        r'([가-힣]{2,})(문화마을|관광지|전망대|케이블카)',
    ]
    
    for pattern in compound_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 2:  # (지명, 시설명) 튜플
                keywords.add(match[0])  # 지명 부분
                keywords.add(match[0] + match[1])  # 전체 이름
    
    # 3. 유명 관광지의 별칭/축약형 처리
    aliases = {
        '해운대': '해운대해수욕장',
        '광안리': '광안리해수욕장',
        '경포대': '경포해변',
        '남산': '남산타워',
        '자갈치': '자갈치시장',
        '동대문': '동대문디자인플라자',
        '명동': '명동거리',
        '홍대': '홍대거리',
        '강남': '강남역',
        '이태원': '이태원거리',
    }
    
    for alias, full_name in aliases.items():
        if alias in text:
            keywords.add(alias)
            keywords.add(full_name)
    
    return keywords

def _extract_major_location_keywords(text: str) -> set:
    """텍스트에서 주요 장소 키워드를 추출합니다."""
    import re
    keywords = set()
    
    # 주요 관광지 패턴들
    patterns = [
        r'([가-힣]{2,}케이블카)',     # 해상케이블카, 남산케이블카
        r'([가-힣]{2,}도)',          # 오동도, 제주도
        r'([가-힣]{2,}해수욕장)',    # 해운대해수욕장
        r'([가-힣]{2,}해변)',        # 경포해변
        r'([가-힣]{2,}폭포)',        # 천지연폭포
        r'([가-힣]{2,}공원)',        # 남산공원
        r'([가-힣]{2,}시장)',        # 자갈치시장
        r'([가-힣]{2,}박물관)',      # 국립중앙박물관
        r'([가-힣]{2,}미술관)',      # 국립현대미술관
        r'([가-힣]{2,}사)',          # 불국사
        r'([가-힣]{2,}궁)',          # 경복궁
        r'([가-힣]{2,}성)',          # 수원화성
        r'([가-힣]{2,}탑)',          # 남산타워
        r'([가-힣]{2,}다리)',        # 광안대교
        r'([가-힣]{2,}항)',          # 부산항
        r'([가-힣]{2,}역)',          # 서울역
        r'([가-힣]{2,}터미널)',      # 고속터미널
        r'([가-힣]{2,}전망대)',      # 부산타워전망대
        r'([가-힣]{2,}아쿠아리움)',  # 코엑스아쿠아리움
        r'([가-힣]{2,}테마파크)',    # 에버랜드테마파크
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            keywords.add(match.lower())
    
    # 특별한 관광지 조합 처리 (연결된 관광지들)
    special_combinations = {
        # 여수 관련
        '해상케이블카': ['오동도', '해상케이블카', '여수해상케이블카'],
        '오동도': ['오동도', '해상케이블카', '여수해상케이블카'],
        
        # 서울 타워 관련
        '남산타워': ['남산타워', 'n서울타워', '서울타워'],
        'n서울타워': ['남산타워', 'n서울타워', '서울타워'],
        '서울타워': ['남산타워', 'n서울타워', '서울타워'],
        
        # 부산 해변 관련
        '해운대': ['해운대', '해운대해수욕장', '해운대해변'],
        '해운대해수욕장': ['해운대', '해운대해수욕장', '해운대해변'],
        '해운대해변': ['해운대', '해운대해수욕장', '해운대해변'],
        '광안리': ['광안리', '광안리해수욕장', '광안리해변'],
        '광안리해수욕장': ['광안리', '광안리해수욕장', '광안리해변'],
        
        # 부산 관광지 관련
        '자갈치시장': ['자갈치시장', '자갈치'],
        '감천문화마을': ['감천문화마을', '감천마을'],
        '태종대': ['태종대', '태종대유원지'],
        
        # 제주 관련
        '성산일출봉': ['성산일출봉', '성산봉'],
        '한라산': ['한라산', '백록담'],
        '천지연폭포': ['천지연폭포', '천지연'],
        
        # 경주 관련
        '불국사': ['불국사', '석굴암'],
        '석굴암': ['불국사', '석굴암'],
        
        # 강릉 관련
        '경포해변': ['경포해변', '경포해수욕장', '경포대'],
        '경포해수욕장': ['경포해변', '경포해수욕장', '경포대'],
        '경포대': ['경포해변', '경포해수욕장', '경포대'],
        
        # 서울 궁궐 관련
        '경복궁': ['경복궁', '광화문'],
        '창덕궁': ['창덕궁', '비원'],
        
        # 인사동/명동 관련
        '인사동': ['인사동', '인사동거리'],
        '명동': ['명동', '명동거리', '명동성당'],
        
        # 기타 유명 관광지
        '롯데타워': ['롯데타워', '롯데월드타워', '서울스카이'],
        '63빌딩': ['63빌딩', '63스카이아트'],
        '동대문': ['동대문', '동대문디자인플라자', 'ddp'],
    }
    
    text_lower = text.lower()
    for key, related_places in special_combinations.items():
        if key in text_lower:
            keywords.update(related_places)
    
    return keywords

def _is_similar_location(keyword1: str, keyword2: str) -> bool:
    """두 장소 키워드가 유사한지 판단합니다 (더 엄격한 중복 검사)."""
    if not keyword1 or not keyword2:
        return False
    
    # 완전 일치
    if keyword1 == keyword2:
        return True
    
    # 한쪽이 다른 쪽을 포함하는 경우 (더 엄격하게 - 2글자 이상부터)
    if len(keyword1) >= 2 and len(keyword2) >= 2:
        if keyword1 in keyword2 or keyword2 in keyword1:
            return True
    
    # 핵심 지명이 같은지 확인 (예: "해운대해수욕장"과 "해운대카페" - 둘 다 해운대 지역)
    core_locations = _extract_core_location_parts(keyword1, keyword2)
    if core_locations and len(core_locations) > 0:
        return True
    
    # 공통 부분이 60% 이상인 경우 (더 엄격하게)
    if len(keyword1) >= 3 and len(keyword2) >= 3:
        common_chars = set(keyword1) & set(keyword2)
        similarity = len(common_chars) / max(len(set(keyword1)), len(set(keyword2)))
        if similarity >= 0.6:
            return True
    
    # 유명 관광지의 다양한 표현 방식 체크
    if _is_same_tourist_spot(keyword1, keyword2):
        return True
    
    return False

def _extract_core_location_parts(keyword1: str, keyword2: str) -> set:
    """두 키워드에서 공통된 핵심 지역명을 추출합니다."""
    import re
    
    # 핵심 지역명 패턴
    location_patterns = [
        r'([가-힣]{2,})(해수욕장|해변|시장|궁|사|탑|타워|공원|박물관|미술관|폭포|산|봉|다리|항|마을|거리|동|구|섬|도)',
        r'([가-힣]{2,})(문화마을|관광지|전망대|케이블카|아쿠아리움|테마파크)',
    ]
    
    cores1 = set()
    cores2 = set()
    
    for pattern in location_patterns:
        # keyword1에서 핵심 지역명 추출
        matches1 = re.findall(pattern, keyword1)
        for match in matches1:
            if len(match) == 2:
                cores1.add(match[0])  # 지역명 부분만
        
        # keyword2에서 핵심 지역명 추출
        matches2 = re.findall(pattern, keyword2)
        for match in matches2:
            if len(match) == 2:
                cores2.add(match[0])  # 지역명 부분만
    
    # 공통 핵심 지역명 반환
    return cores1 & cores2

def _is_same_tourist_spot(keyword1: str, keyword2: str) -> bool:
    """같은 관광지의 다른 표현인지 확인합니다."""
    # 같은 관광지의 다양한 표현들
    same_spots = [
        # 서울
        {'남산타워', 'n서울타워', '서울타워', '남산'},
        {'경복궁', '경복궁궁궐', '경복궁앞'},
        {'창덕궁', '창덕궁궁궐', '비원'},
        {'명동', '명동거리', '명동쇼핑'},
        {'홍대', '홍대거리', '홍익대학교앞'},
        {'이태원', '이태원거리', '이태원역'},
        {'강남', '강남역', '강남구'},
        {'동대문', '동대문디자인플라자', 'ddp'},
        {'인사동', '인사동거리', '인사동문화거리'},
        
        # 부산
        {'해운대', '해운대해수욕장', '해운대해변', '해운대비치'},
        {'광안리', '광안리해수욕장', '광안리해변', '광안리비치'},
        {'자갈치시장', '자갈치', '자갈치수산시장'},
        {'감천문화마을', '감천마을', '감천색깔마을'},
        {'태종대', '태종대유원지', '태종대공원'},
        {'부산타워', '부산타워전망대', '용두산공원타워'},
        {'국제시장', '부산국제시장', '국제시장거리'},
        
        # 제주
        {'성산일출봉', '성산봉', '일출봉'},
        {'한라산', '백록담', '한라산백록담'},
        {'천지연폭포', '천지연', '천지연계곡'},
        {'협재해수욕장', '협재해변', '협재비치'},
        {'우도', '우도섬', '소가섬'},
        
        # 강릉
        {'경포해변', '경포해수욕장', '경포대', '경포대해변'},
        {'정동진', '정동진해변', '정동진역'},
        {'오죽헌', '율곡이이생가', '신사임당생가'},
        
        # 여수
        {'오동도', '동백섬', '오동도공원'},
        {'여수해상케이블카', '해상케이블카', '돌산케이블카'},
        {'여수밤바다', '여수항', '여수신항'},
        
        # 경주
        {'불국사', '불국사절', '불국사사찰'},
        {'석굴암', '석굴암석굴', '석굴암불상'},
        {'첨성대', '경주첨성대', '신라첨성대'},
        {'안압지', '동궁과월지', '경주안압지'},
    ]
    
    for spot_group in same_spots:
        if keyword1 in spot_group and keyword2 in spot_group:
            return True
    
    return False

async def remove_duplicate_locations(trip_data: dict, destination: str) -> dict:
    """
    여행 계획에서 중복되는 장소를 순차적으로 감지하고 즉시 교체합니다.
    더 효율적인 처리를 위해 중복 발견 시 바로 교체합니다.
    """
    if not trip_data.get("itinerary"):
        return trip_data
    
    visited_locations = set()
    fixed_count = 0
    
    # 1일차부터 순차적으로 처리
    for day_idx, day in enumerate(trip_data["itinerary"]):
        if not day.get("activities"):
            continue
        
        day_num = day.get('day', day_idx + 1)
        logger.info(f"{day_num}일차 중복 검사 시작...")
            
        for activity_idx, activity in enumerate(day["activities"]):
            # 호텔/숙박 관련 활동은 체크하지 않음
            title = activity.get('title', '').lower()
            if any(keyword in title for keyword in ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out']):
                continue
            
            # 장소명으로 중복 체크
            place_name = activity.get('title', '').strip()
            location_name = activity.get('location', '').strip()
            
            # 더 정교한 중복 감지를 위한 키워드 추출
            location_keys = _extract_location_keywords(place_name, location_name)
            
            # 중복 체크
            is_duplicate = False
            duplicate_key = None
            
            for key in location_keys:
                if key and key in visited_locations:
                    is_duplicate = True
                    duplicate_key = key
                    break
                    
                # 기존 방문 장소들과 유사성 검사
                for visited_key in visited_locations:
                    if _is_similar_location(key, visited_key):
                        is_duplicate = True
                        duplicate_key = key
                        break
                        
                if is_duplicate:
                    break
            
            if is_duplicate:
                # 중복 발견 시 즉시 교체
                logger.info(f"🔄 중복 장소 즉시 교체: {day_num}일차 '{place_name}' (키워드: {duplicate_key})")
                
                # 단일 활동 교체
                new_activity = await replace_single_duplicate_activity(
                    trip_data, day_idx, activity_idx, destination, visited_locations
                )
                
                if new_activity:
                    # 교체 전후 정보 로깅
                    original_location = activity.get('location', 'N/A')
                    new_title = new_activity.get('title', 'N/A')
                    new_location = new_activity.get('location', 'N/A')
                    new_real_address = new_activity.get('real_address', 'N/A')
                    
                    logger.info(f"🔄 장소 교체 상세:")
                    logger.info(f"   이전: '{place_name}' -> {original_location}")
                    logger.info(f"   이후: '{new_title}' -> {new_location}")
                    if new_activity.get('verified'):
                        logger.info(f"   검증된 주소: {new_real_address}")
                    
                    trip_data["itinerary"][day_idx]["activities"][activity_idx] = new_activity
                    fixed_count += 1
                    
                    # 새로운 활동의 키워드를 방문 목록에 추가
                    new_location_keys = _extract_location_keywords(
                        new_activity.get('title', ''), 
                        new_activity.get('location', '')
                    )
                    for key in new_location_keys:
                        if key:
                            visited_locations.add(key)
                    
                    logger.info(f"✅ 교체 완료: {place_name} → {new_activity.get('title')}")
                else:
                    # 교체 실패 시 원래 활동의 키워드를 추가 (무한 루프 방지)
                    for key in location_keys:
                        if key:
                            visited_locations.add(key)
            else:
                # 중복이 아닌 경우 모든 키워드를 방문 목록에 추가
                for key in location_keys:
                    if key:
                        visited_locations.add(key)
    
    if fixed_count > 0:
        logger.info(f"✅ 총 {fixed_count}개의 중복 장소를 교체했습니다.")
    else:
        logger.info("✅ 중복 장소가 발견되지 않았습니다.")
    
    return trip_data

async def replace_single_duplicate_activity(trip_data: dict, day_idx: int, activity_idx: int, destination: str, visited_locations: set) -> dict:
    """
    단일 중복 활동을 빠르게 교체합니다.
    """
    try:
        day = trip_data["itinerary"][day_idx]
        original = day["activities"][activity_idx]
        day_num = day.get('day', day_idx + 1)
        
        # 이미 사용된 모든 장소 목록 생성 (간소화)
        used_titles = set()
        used_locations = set()
        
        for d in trip_data.get("itinerary", []):
            for act in d.get("activities", []):
                if act.get('title'):
                    used_titles.add(act.get('title').lower())
                if act.get('location'):
                    used_locations.add(act.get('location').lower())
        
        # 빠른 교체용 프롬프트 (간소화)
        replacement_prompt = f"""
중복된 "{original.get('title', '')}" 활동을 {destination}의 다른 유명 관광지로 즉시 교체해주세요.

🚨 **사용하면 안 되는 장소들** (이미 사용됨):
{', '.join(list(used_titles)[:10])}...

**요구사항**:
1. {destination} 지역의 실제 존재하는 유명 관광지만 사용
2. 위에 나열된 장소들과 절대 겹치지 않는 새로운 장소
3. JSON 형식으로 단일 activity만 반환

🔑 **중요: location과 title 필드 구분**
- **location**: 실제 장소명만 (예: "광안리해변", "국제시장")
- **title**: 화면에 표시될 활동명 (예: "광안리 산책", "국제시장 투어")

{{
    "time": "{original.get('time', '09:00')}",
    "title": "새로운 활동명 (예: 광안리 산책)",
    "location": "실제 장소명만 (예: 광안리해변)",
    "description": "활동 설명",
}}
"""
        
        # OpenAI API 호출 (더 빠른 설정)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"당신은 {destination} 관광 전문가입니다. 중복된 장소를 빠르게 다른 유명 관광지로 교체해주세요. 간단하고 빠르게 응답해주세요."},
                {"role": "user", "content": replacement_prompt}
            ],
            max_tokens=300,  # 토큰 수 줄임
            temperature=0.2   # 더 일관된 결과
        )
        
        content = response.choices[0].message.content.strip()
        
        # JSON 파싱
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx]
            new_activity = json.loads(json_str)
            
            # 🔥 중요: 새로운 활동의 주소를 카카오 API로 즉시 검증 및 업데이트
            region = destination.split()[0] if destination else ""
            verified_activity = kakao_service.verify_and_enrich_location(new_activity, region)
            
            # 검증된 정보로 업데이트
            if verified_activity.get('verified', False):
                logger.info(f"🔄 교체된 장소 주소 업데이트: '{new_activity.get('title')}' -> {verified_activity.get('real_address', 'N/A')}")
                return verified_activity
            else:
                logger.warning(f"⚠️ 교체된 장소 '{new_activity.get('title')}'의 주소 검증 실패")
                return new_activity
        
    except Exception as e:
        logger.error(f"단일 활동 교체 중 오류: {str(e)}")
    
    return None

async def check_final_duplicates(trip_data: dict) -> list:
    """
    최종 중복 검사를 수행합니다.
    """
    if not trip_data.get("itinerary"):
        return []
    
    all_locations = []
    duplicates = []
    
    # 모든 장소를 수집
    for day_idx, day in enumerate(trip_data["itinerary"]):
        if not day.get("activities"):
            continue
            
        for activity_idx, activity in enumerate(day["activities"]):
            title = activity.get('title', '').strip()
            location = activity.get('location', '').strip()
            
            # 호텔/숙박 관련 활동은 체크하지 않음
            if any(keyword in title.lower() for keyword in ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out']):
                continue
            
            location_info = {
                'day_idx': day_idx,
                'activity_idx': activity_idx,
                'day': day.get('day'),
                'title': title,
                'location': location,
                'keywords': _extract_location_keywords(title, location)
            }
            
            # 기존 장소들과 중복 체크
            for existing in all_locations:
                # 제목이나 위치가 완전히 같은 경우
                if title.lower() == existing['title'].lower() or location.lower() == existing['location'].lower():
                    duplicates.append(f"Day {day.get('day')}: '{title}' 중복 (Day {existing['day']}와 동일)")
                    continue
                
                # 키워드 기반 유사성 체크
                for keyword in location_info['keywords']:
                    if keyword and keyword in existing['keywords']:
                        duplicates.append(f"Day {day.get('day')}: '{title}' 중복 키워드 '{keyword}' (Day {existing['day']}와 중복)")
                        break
            
            all_locations.append(location_info)
    
    return duplicates

async def replace_duplicate_activities(trip_data: dict, duplicates: list, destination: str, visited_locations: set) -> dict:
    """
    중복된 활동들을 새로운 장소로 교체합니다.
    """
    for duplicate in duplicates:
        day_idx = duplicate['day_idx']
        activity_idx = duplicate['activity_idx']
        day_num = duplicate['day']
        original = duplicate['original_activity']
        
        try:
            # 해당 일차의 다른 활동들 정보 수집
            day_activities = trip_data["itinerary"][day_idx]["activities"]
            other_activities = [act for i, act in enumerate(day_activities) if i != activity_idx]
            
            # 이미 방문한 장소들 목록 생성
            visited_list = list(visited_locations)
            
            # 전체 일정에서 이미 사용된 모든 장소들 수집
            all_used_locations = set()
            for day in trip_data.get("itinerary", []):
                for activity in day.get("activities", []):
                    if activity.get('title') and activity.get('location'):
                        # 더 정교한 키워드 추출로 중복 방지
                        used_keywords = _extract_location_keywords(
                            activity.get('title', ''), 
                            activity.get('location', '')
                        )
                        all_used_locations.update(used_keywords)
            
            # 교체용 프롬프트 (더 강화된 버전)
            replacement_prompt = f"""
🚨 **중복 장소 교체 요청** 🚨

"{original.get('title', '')}" 활동이 다른 날짜와 중복되어 교체가 필요합니다.
{destination} 지역의 **완전히 다른 새로운 장소**로 교체해주세요.

**현재 {day_num}일차 다른 활동들:**
{json.dumps(other_activities, ensure_ascii=False, indent=2)}

**🚫 절대 사용하면 안 되는 장소들 (이미 일정에 포함됨):**
{', '.join(sorted(list(all_used_locations))[:20])}
... (총 {len(all_used_locations)}개 장소가 이미 사용됨)

**⚠️ 중복 방지 규칙 (매우 중요!):**
1. **위에 나열된 모든 장소와 완전히 다른 곳만 선택**
2. **유사한 장소도 절대 금지**: 
   - 예: "해운대해수욕장" 사용 시 → "해운대카페", "해운대근처" 등 해운대 관련 모든 장소 금지
   - 예: "자갈치시장" 사용 시 → "자갈치회센터", "자갈치근처" 등 자갈치 관련 모든 장소 금지
3. **같은 지역/건물 내 다른 시설도 금지**
4. **완전히 다른 지역의 다른 유형 장소만 선택**

**✅ 교체 요구사항:**
1. {destination} 지역의 실제 존재하는 유명 관광지만 사용
2. 시간대: {original.get('time', '')} 유지
3. 지리적으로 {day_num}일차 다른 활동들과 접근 가능한 곳
4. **반드시 구체적인 고유명사 사용**:
   ❌ "다른 해변", "새로운 시장", "또 다른 공원"
   ✅ "송도해수욕장", "국제시장", "용두산공원"

🔑 **중요: location과 title 필드 구분**
- **location**: 실제 장소명만 (예: "태종대", "감천문화마을")
- **title**: 화면에 표시될 활동명 (예: "태종대 산책", "감천문화마을 투어")

**JSON 응답 형식:**
{{
    "time": "{original.get('time', '')}",
    "title": "새로운 활동명 (예: 태종대 산책)",
    "location": "실제 장소명만 (예: 태종대)",
    "description": "새로운 활동에 대한 설명",
}}

**⚠️ 주의**: 위에 나열된 사용 금지 장소들과 조금이라도 유사하면 절대 사용하지 마세요!
"""
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """당신은 한국 관광 전문가입니다. 중복 장소 교체를 담당합니다.

🚨 **절대 규칙**:
1. **중복 절대 금지**: 사용자가 제공한 "사용하면 안 되는 장소" 목록과 조금이라도 유사한 곳은 절대 선택하지 마세요
2. **유사 장소도 금지**: 같은 지역/건물/시설군의 다른 장소도 금지 (예: 해운대해수욕장 → 해운대 관련 모든 장소 금지)
3. **구체적 고유명사만**: "다른 해변", "새로운 시장" 같은 모호한 표현 절대 금지
4. **실제 존재 확인**: 확실히 존재하는 유명 관광지만 선택
5. **완전히 다른 지역**: 기존 장소들과 완전히 다른 지역의 다른 유형 장소만 선택

⚠️ 의심스러우면 선택하지 마세요. 확실한 곳만 추천하세요."""},
                    {"role": "user", "content": replacement_prompt}
                ],
                max_tokens=500,
                temperature=0.8  # 더 다양한 결과를 위해 온도 증가
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                new_activity = json.loads(json_str)
                
                # 교체된 장소가 또 다른 중복이 아닌지 검증
                new_keywords = _extract_location_keywords(
                    new_activity.get('title', ''), 
                    new_activity.get('location', '')
                )
                
                # 기존 장소들과 중복 확인
                is_still_duplicate = False
                for new_keyword in new_keywords:
                    if new_keyword in all_used_locations:
                        is_still_duplicate = True
                        logger.warning(f"교체된 장소도 중복됨: {new_keyword}")
                        break
                    
                    # 더 정교한 유사성 검사
                    for used_keyword in all_used_locations:
                        if _is_similar_location(new_keyword, used_keyword):
                            is_still_duplicate = True
                            logger.warning(f"교체된 장소가 유사함: {new_keyword} ≈ {used_keyword}")
                            break
                    
                    if is_still_duplicate:
                        break
                
                if not is_still_duplicate:
                    # 새로운 활동으로 교체
                    trip_data["itinerary"][day_idx]["activities"][activity_idx] = new_activity
                    
                    # 새로운 장소를 방문 목록에 추가
                    visited_locations.update(new_keywords)
                    
                    logger.info(f"✅ {day_num}일차 중복 장소 교체 완료: {original.get('title')} -> {new_activity.get('title')}")
                else:
                    # 여전히 중복이면 원본 유지하고 경고
                    logger.error(f"❌ {day_num}일차 교체 실패 - 새 장소도 중복됨: {new_activity.get('title')}")
                    logger.info(f"원본 활동 유지: {original.get('title')}")
            else:
                logger.error(f"{day_num}일차 중복 장소 교체 실패: JSON 파싱 오류")
                
        except Exception as e:
            logger.error(f"{day_num}일차 중복 장소 교체 중 오류 발생: {str(e)}")
    
    return trip_data

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

# 카카오 로컬 API 키를 환경변수에서 가져옵니다
kakao_api_key = os.getenv("KAKAO_API_KEY")
if not kakao_api_key:
    logger.warning("KAKAO_API_KEY가 설정되지 않았습니다. 장소 검증 기능이 제한됩니다.")

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
    allow_origins=[
        "http://localhost:3000",  # 로컬 개발용
        "https://planner-kq3e.onrender.com",  # Render 프론트엔드
        "https://trip-planner-frontend.vercel.app",   # Vercel 프론트엔드 (대안)
    ],
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
    companionType: Optional[str] = ""  # 동반자 유형 (연인, 친구, 가족 등)
    rooms: Optional[int] = 1   # 객실 수 (선택사항, 기본값: 1개)
    travelStyle: Optional[str] = ""  # 여행 스타일
    travelPace: Optional[str] = ""  # 여행 페이스 (타이트하게, 널널하게)

class ChatModifyRequest(BaseModel):
    """채팅을 통한 일정 수정 요청 데이터 모델"""
    message: str  # 사용자가 입력한 수정 요청 메시지
    current_trip_plan: dict  # 현재 여행 계획 전체 데이터

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
    total_cost: str  # 총 예상 비용
    tips: List[str]  # 여행 팁 리스트
    transport_info: Optional[dict] = None  # 대중교통 정보
    trip_hotel_search: Optional[dict] = None  # 전체 여행에 대한 호텔 검색 링크
    accommodation: Optional[List[HotelInfo]] = []  # 숙박 정보 (선택사항, 기본값: 빈 리스트)


# ========================================
# 여행 비용 계산 함수
# ========================================

def calculate_trip_cost(budget: str, travel_days: int, destination: str) -> int:
    """예산 등급과 여행 일수에 따른 1인당 예상 비용을 계산합니다"""
    
    # 디버깅을 위한 로그
    print(f"비용 계산 - 예산: {budget}, 여행일수: {travel_days}, 목적지: {destination}")
    
    # 기본 일일 비용 (숙박 + 식사 + 교통 + 관광)
    budget_multipliers = {
        "저예산": 0.7,    # 70% 수준
        "보통": 1.0,      # 100% 기준
        "고급": 1.8,      # 180% 수준
        "럭셔리": 3.0     # 300% 수준
    }
    
    # 지역별 기본 비용 조정 (서울 기준 1.0)
    region_multipliers = {
        # 수도권
        "서울": 1.2, "인천": 1.0, "경기": 1.0,
        # 제주도 (관광지 프리미엄)
        "제주": 1.4,
        # 부산/대구 등 광역시
        "부산": 1.1, "대구": 0.9, "광주": 0.9, "대전": 0.9, "울산": 0.9,
        # 강원도 (관광지)
        "강원": 1.1, "춘천": 1.1, "강릉": 1.2, "속초": 1.2, "평창": 1.1,
        # 경상도
        "경주": 1.0, "안동": 0.8, "포항": 0.9, "창원": 0.9, "진주": 0.8,
        # 전라도
        "전주": 0.9, "여수": 1.1, "순천": 0.8, "목포": 0.8,
        # 충청도
        "충주": 0.8, "천안": 0.9, "청주": 0.8, "공주": 0.8,
        # 기타
        "통영": 1.0, "거제": 1.0
    }
    
    # 기본 일일 비용 (1인 기준) - 국내 여행 현실적 비용
    base_daily_cost = {
        "숙박": 50000,    # 평균 숙박비 (모텔/펜션 기준)
        "식사": 30000,    # 3끼 식사비 (아침 5천, 점심 12천, 저녁 13천)
        "교통": 15000,    # 지역 내 교통비 (버스/지하철/택시)
        "관광": 20000,    # 입장료, 체험비 등
        "기타": 10000     # 쇼핑, 간식 등
    }
    
    # 총 기본 일일 비용
    total_daily_cost = sum(base_daily_cost.values())  # 125,000원
    
    # 예산 등급별 비용 조정
    budget_adjusted_cost = total_daily_cost * budget_multipliers.get(budget, 1.0)
    
    # 지역별 비용 조정
    region_multiplier = 1.0
    destination_lower = destination.lower()
    for region, multiplier in region_multipliers.items():
        if region in destination_lower:
            region_multiplier = multiplier
            break
    
    # 최종 일일 비용
    final_daily_cost = budget_adjusted_cost * region_multiplier
    
    # 여행 일수에 따른 할인 (장기 여행 시 일부 비용 절약)
    if travel_days >= 7:
        day_discount = 0.9  # 10% 할인
    elif travel_days >= 4:
        day_discount = 0.95  # 5% 할인
    else:
        day_discount = 1.0  # 할인 없음
    
    # 최종 1인당 총 비용 계산
    total_cost = final_daily_cost * travel_days * day_discount
    
    # 디버깅을 위한 로그
    print(f"일일 기본비용: {total_daily_cost:,}원")
    print(f"예산 조정후: {budget_adjusted_cost:,}원")
    print(f"지역 조정후: {final_daily_cost:,}원")
    print(f"최종 총비용: {total_cost:,}원")
    
    return int(total_cost)





# ========================================
# 호텔 검색 서비스 클래스
# ========================================
# 이 클래스는 호텔 정보를 제공하고 예약 링크를 생성합니다

class HotelSearchService:
    """호텔 검색 및 예약 링크 생성 서비스"""
    
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
            "hotels": {
                "name": "호텔스닷컴",
                "url": f"https://kr.hotels.com/Hotel-Search?destination={encoded_destination}&flexibility=0_DAY&d1={check_in}&startDate={check_in}&d2={check_out}&endDate={check_out}&adults={guests}&rooms={rooms}",
                "icon": "🏨"
            },
            "airbnb": {
                "name": "에어비앤비",
                "url": f"https://www.airbnb.co.kr/s/{encoded_destination}/homes?checkin={check_in}&checkout={check_out}&adults={guests}&children=0&infants=0&pets=0",
                "icon": "🏠"
            },
            "agoda": {
                "name": "아고다",
                "url": f"https://www.agoda.com/ko-kr/search?textToSearch={encoded_destination}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&children=0&locale=ko-kr&currency=KRW&travellerType=1",
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
            links["hotels"]["url"] = f"https://kr.hotels.com/Hotel-Search?destination={encoded_destination}&flexibility=0_DAY&d1={check_in}&startDate={check_in}&d2={check_out}&endDate={check_out}&adults={guests}&rooms={rooms}&q={encoded_hotel_name}"
            links["agoda"]["url"] = f"https://www.agoda.com/ko-kr/search?textToSearch={encoded_destination}&hotelName={encoded_hotel_name}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&children=0&locale=ko-kr&currency=KRW&travellerType=1"
            links["booking"]["url"] = f"https://www.booking.com/searchresults.html?ss={encoded_destination}&hotelName={encoded_hotel_name}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}"
        
        return links
    
    @staticmethod
    def create_trip_hotel_search_links(destination: str, check_in: str, check_out: str, guests: int, rooms: int) -> dict:
        """전체 여행에 대한 호텔 검색 링크를 생성하는 메서드"""
        # 주요 호텔 예약 사이트들의 검색 링크 생성
        search_links = {
            "hotels": {
                "name": "호텔스닷컴",
                "url": f"https://kr.hotels.com/Hotel-Search?destination={urllib.parse.quote(destination)}&flexibility=0_DAY&d1={check_in}&startDate={check_in}&d2={check_out}&endDate={check_out}&adults={guests}&rooms={rooms}",
                "icon": "🏨",
                "description": "호텔스닷컴에서 호텔 검색하기"
            },
            "yeogi": {
                "name": "여기어때",
                "url": f"https://www.yeogi.com/domestic-accommodations?keyword={urllib.parse.quote(destination)}&checkIn={check_in}&checkOut={check_out}&personal={guests}&freeForm=false",
                "icon": "🏨",
                "description": "여기어때에서 호텔 검색하기"
            },
            "booking": {
                "name": "부킹닷컴",
                "url": f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote(destination)}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}",
                "icon": "📅",
                "description": "부킹닷컴에서 호텔 검색하기"
            },
            "airbnb": {
                "name": "에어비앤비",
                "url": f"https://www.airbnb.co.kr/s/{urllib.parse.quote(destination)}/homes?checkin={check_in}&checkout={check_out}&adults={guests}&children=0&infants=0&pets=0",
                "icon": "🏠",
                "description": "에어비앤비에서 숙소 검색하기"
            }
        }
        
        return {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms,
            "search_links": search_links
        }
    
    @staticmethod
    def _extract_location_from_activity(activity_text: str, destination: str) -> str:
        """활동 텍스트에서 주요 장소명을 추출하는 메서드"""
        if not activity_text:
            return destination
        
        # 구체적인 관광지 키워드 패턴 (2글자 이상 고유명사 + 접미사)
        location_patterns = [
            # 자연 관광지
            r'([가-힣]{2,}해수욕장)',  # 해운대해수욕장, 경포해수욕장
            r'([가-힣]{2,}해변)',      # 광안리해변, 경포해변
            r'([가-힣]{2,}폭포)',      # 천지연폭포, 정방폭포
            r'([가-힣]{2,}산)',        # 한라산, 지리산
            r'([가-힣]{2,}봉)',        # 성산일출봉, 우도봉
            r'([가-힣]{2,}강)',        # 한강, 낙동강
            r'([가-힣]{2,}호수)',      # 천지호수, 밤섬호수
            r'([가-힣]{2,}굴)',        # 만장굴, 협재굴
            
            # 문화/역사 관광지
            r'([가-힣]{2,}사)',        # 불국사, 해인사, 조계사
            r'([가-힣]{2,}궁)',        # 경복궁, 창덕궁, 덕수궁
            r'([가-힣]{2,}성)',        # 수원화성, 남한산성
            r'([가-힣]{2,}탑)',        # 남산타워, 부산타워
            r'([가-힣]{2,}박물관)',    # 국립중앙박물관, 전쟁기념관
            r'([가-힣]{2,}미술관)',    # 국립현대미술관, 리움미술관
            r'([가-힣]{2,}문화재)',    # 석굴암문화재
            
            # 도시 인프라
            r'([가-힣]{2,}시장)',      # 동대문시장, 남대문시장, 자갈치시장
            r'([가-힣]{2,}공원)',      # 남산공원, 올림픽공원, 한강공원
            r'([가-힣]{2,}역)',        # 서울역, 부산역, 제주공항
            r'([가-힣]{2,}항)',        # 부산항, 인천항, 제주항
            r'([가-힣]{2,}다리)',      # 광안대교, 한강대교, 반포대교
            r'([가-힣]{2,}거리)',      # 명동거리, 홍대거리, 가로수길
            r'([가-힣]{2,}로)',        # 청계천로, 강남대로
            
            # 행정구역 (구체적인 지명)
            r'([가-힣]{2,}동)',        # 명동, 홍대동, 강남동
            r'([가-힣]{2,}구)',        # 강남구, 종로구, 해운대구
            r'([가-힣]{2,}시)',        # 부산시, 제주시, 강릉시
            r'([가-힣]{2,}군)',        # 제주서귀포시, 강화군
            r'([가-힣]{2,}읍)',        # 성산읍, 한림읍
            r'([가-힣]{2,}면)',        # 애월면, 구좌면
            
            # 복합 명칭
            r'([가-힣]{2,}테마파크)',  # 에버랜드테마파크, 롯데월드테마파크
            r'([가-힣]{2,}리조트)',    # 제주신화월드리조트
            r'([가-힣]{2,}아쿠아리움)', # 코엑스아쿠아리움
            r'([가-힣]{2,}전망대)',    # 서울스카이전망대, 부산타워전망대
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, activity_text)
            if match:
                return match.group(1)
        
        # 특정 키워드가 없으면 전체 활동 텍스트에서 첫 번째 명사 추출
        words = activity_text.split()
        for word in words:
            if len(word) >= 2 and re.match(r'^[가-힣]+$', word):
                return word
        
        # 추출 실패 시 기본 목적지 반환
        return destination

# ========================================
# API 엔드포인트 정의
# ========================================
# 엔드포인트는 웹 서버에서 특정 기능을 제공하는 주소입니다

@app.get("/")
async def root():
    """루트 경로 (메인 페이지) - 서버가 정상 작동하는지 확인하는 용도"""
    return {"message": "여행 플래너 AI API"}

# ========================================
# 진행 상황 SSE 엔드포인트
# ========================================

async def generate_progress_events(request_data: dict):
    """여행 계획 생성 과정의 진행 상황을 실시간으로 전달하는 제너레이터"""
    try:
        # 1단계: 요청 검증
        yield f"data: {json.dumps({'step': 1, 'message': '여행 정보를 검증하고 있습니다...', 'progress': 8, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.8)
        
        # 2단계: 데이터 전처리
        yield f"data: {json.dumps({'step': 2, 'message': '여행 데이터를 분석하고 있습니다...', 'progress': 15, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.0)
        
        # 3단계: AI 시스템 준비
        yield f"data: {json.dumps({'step': 3, 'message': 'AI 시스템을 준비하고 있습니다...', 'progress': 25, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.2)
        
        # 4단계: 기본 정보 수집
        yield f"data: {json.dumps({'step': 4, 'message': '목적지 기본 정보를 수집하고 있습니다...', 'progress': 35, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.4)
        
        # 5단계: 관광지 데이터베이스 조회
        yield f"data: {json.dumps({'step': 5, 'message': '관광지 데이터베이스를 조회하고 있습니다...', 'progress': 45, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.6)
        
        # 6단계: 맞춤형 추천 준비
        yield f"data: {json.dumps({'step': 6, 'message': '맞춤형 추천을 준비하고 있습니다...', 'progress': 55, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.2)
        
        # 7단계: 여행 패턴 분석
        yield f"data: {json.dumps({'step': 7, 'message': '여행 패턴을 분석하고 있습니다...', 'progress': 65, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.4)
        
        # 8단계: 일정 최적화 준비
        yield f"data: {json.dumps({'step': 8, 'message': '일정 최적화를 준비하고 있습니다...', 'progress': 75, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(1.0)
        
        # 9단계: AI 모델 로딩
        yield f"data: {json.dumps({'step': 9, 'message': 'AI 모델을 로딩하고 있습니다...', 'progress': 82, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.8)
        
        # 10단계: 최종 준비 단계
        yield f"data: {json.dumps({'step': 10, 'message': '여행 계획 생성을 준비하고 있습니다...', 'progress': 88, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.8)
        
        # 11단계: API 호출 직전
        yield f"data: {json.dumps({'step': 11, 'message': 'AI가 여행 계획을 생성하고 있습니다...', 'progress': 90, 'total_steps': 11}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.8)
        
        # 실제 OpenAI API 호출은 plan-trip API에서 처리됨 - 여기서는 90%까지만
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

@app.get("/plan-trip-progress")
async def plan_trip_progress(
    destination: str,
    start_date: str,
    end_date: str,
    budget: str = "보통",
    guests: int = 2,
    rooms: int = 1
):
    """여행 계획 생성 진행 상황을 실시간으로 전달하는 SSE 엔드포인트"""
    request_data = {
        'destination': destination,
        'start_date': start_date,
        'end_date': end_date,
        'budget': budget,
        'guests': guests,
        'rooms': rooms
    }
    
    return StreamingResponse(
        generate_progress_events(request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/plan-trip", response_model=TripPlan)
async def plan_trip(request: TripRequest):
    """여행 계획을 생성하는 메인 API"""
    try:
        # 입력 데이터 검증
        if not request.destination or request.destination.strip() == "":
            raise HTTPException(status_code=400, detail="목적지를 입력해주세요.")
        
        if not request.start_date or request.start_date.strip() == "":
            raise HTTPException(status_code=400, detail="여행 시작일을 선택해주세요.")
        
        if not request.end_date or request.end_date.strip() == "":
            raise HTTPException(status_code=400, detail="여행 종료일을 선택해주세요.")
        
        # 날짜 형식 검증 및 파싱
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        
        # 날짜 논리 검증
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="여행 시작일은 종료일보다 이전이어야 합니다.")
        
        # 여행 기간 검증 (최대 4박 5일)
        travel_days = (end_date - start_date).days + 1
        if travel_days > 5:
            raise HTTPException(status_code=400, detail="여행 기간은 최대 4박 5일까지 가능합니다.")
        
        if travel_days < 1:
            raise HTTPException(status_code=400, detail="여행 기간은 최소 1일 이상이어야 합니다.")
        
        # 과거 날짜 검증
        current_date = datetime.now().date()
        if start_date.date() < current_date:
            raise HTTPException(status_code=400, detail="여행 시작일은 오늘 이후 날짜여야 합니다.")
        
        # 로그에 요청 정보를 기록합니다
        logger.info(f"여행 계획 생성 요청: {request.destination}, {request.start_date} ~ {request.end_date} ({travel_days}일)")
        
        # 호텔 검색 서비스를 초기화합니다
        hotel_service = HotelSearchService()
        
        # 카카오 로컬 서비스를 초기화합니다
        kakao_service = KakaoLocalService()
        
        # OpenAI API에 전달할 프롬프트(질문)를 생성합니다
        # 프롬프트는 AI에게 무엇을 해달라고 요청하는 메시지입니다
        prompt = f"""
목적지: {request.destination}
여행 기간: {request.start_date} ~ {request.end_date} (총 {travel_days}일)
인원수: {request.guests}명
객실: {request.rooms}개
예산: {request.budget}
관심사: {', '.join(request.interests) if request.interests else '일반적인 관광'}
여행 페이스: {request.travelPace if request.travelPace else '보통'}

위 조건에 맞는 여행 일정을 짜주세요.

🚨 **최우선 규칙: 장소 중복 절대 금지**

**⚠️ 중요: 작성하기 전에 반드시 다음 단계를 따르세요:**

1️⃣ **1일차 활동 작성** → 사용된 장소들을 기억하세요
2️⃣ **2일차 활동 작성 전** → 1일차에서 사용한 모든 장소와 겹치지 않는지 확인
3️⃣ **3일차 활동 작성 전** → 1일차, 2일차에서 사용한 모든 장소와 겹치지 않는지 확인
4️⃣ **이런 식으로 매일 이전 모든 날짜의 장소들을 피해서 작성**

**중복 금지 예시:**
❌ 1일차: "해운대해수욕장 산책" → 2일차: "해운대해수욕장에서 일출보기" (같은 장소!)
❌ 1일차: "남산타워" → 3일차: "N서울타워" (같은 장소의 다른 이름!)
❌ 1일차: "자갈치시장" → 2일차: "자갈치시장 회센터" (같은 건물 내!)

✅ 1일차: "해운대해수욕장" → 2일차: "광안리해변" (완전히 다른 해변)
✅ 1일차: "경복궁" → 2일차: "창덕궁" (완전히 다른 궁궐)

**여행 페이스별 활동 개수:**
- "널널하게": 하루에 3개 활동 (여유롭게 천천히)
- "타이트하게": 하루에 4개 활동 (알차게 많은 곳 방문)

**다른 규칙들:**
- 애매한 이름 금지: "부산 해변" → "해운대해수욕장"
- 호텔 정보 제외
- 확실히 존재하는 유명한 장소만 추천

**⚠️ 작성 중 체크리스트:**
□ 이 장소가 이전 날짜에 이미 나왔나?
□ 비슷한 이름의 장소가 이미 있나?
□ 같은 건물이나 지역 내 다른 시설인가?
→ 하나라도 해당되면 완전히 다른 장소로 변경!

**🔑 중요: location과 title 필드 구분**
- **location**: 실제 장소명만 (예: "해운대해수욕장", "자갈치시장", "경복궁")
- **title**: 화면에 표시될 활동명 (예: "해운대 산책", "자갈치 시장 투어", "경복궁 관람")

JSON 형식으로 응답:
{{
    "destination": "{request.destination}",
    "duration": "{travel_days}일",
    "itinerary": [
        {{
            "day": 1,
            "date": "{request.start_date}",
            "activities": [
                {{
                    "time": "09:00",
                    "title": "활동명 (예: 해운대 산책)",
                    "location": "실제 장소명만 (예: 해운대해수욕장)",
                    "description": "활동 설명",
                    "duration": "소요시간"
                }}
            ]
        }}
    ],
    "total_cost": "1인당 XXX,XXX원",
    "tips": ["여행 팁들"]
}}
        """
        
        logger.info("=== OpenAI API 호출 시작 ===")
        logger.info(f"목적지: {request.destination}, 여행기간: {travel_days}일")
        logger.info(f"모델: gpt-4o, 최대토큰: 3000, Temperature: 0.3")
        
        # 실제 OpenAI API 호출 시작 시점 기록
        api_start_time = datetime.now()
        logger.info(f"API 호출 시작 시간: {api_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # OpenAI API를 호출하여 AI 여행 계획을 생성합니다
        # 최신 OpenAI API 사용법을 적용했습니다
        response = client.chat.completions.create(
            model="gpt-4o",  # 사용할 AI 모델
            messages=[
                {"role": "system", "content": f"""당신은 전문 여행 플래너입니다. {travel_days}일 여행 계획을 작성해주세요.

🚨 **최우선 규칙: 장소 중복 절대 금지**

**필수 작성 절차:**
1. 1일차 모든 활동 작성 완료
2. 2일차 작성 시: 1일차 장소들을 머릿속에서 확인하고 완전히 다른 장소만 선택
3. 3일차 작성 시: 1일차+2일차 모든 장소들을 확인하고 완전히 다른 장소만 선택
4. 매일 이전 모든 날짜의 장소를 피해서 작성

**중복 체크 방법:**
- 장소명이 같으면 중복 (해운대해수욕장 = 해운대해수욕장)
- 같은 장소의 다른 이름도 중복 (남산타워 = N서울타워)
- 같은 건물/지역 내 시설도 중복 (자갈치시장 = 자갈치시장 회센터)

**절대 하지 말 것:**
❌ "1일차에 해운대해수욕장 → 2일차에 해운대해수욕장" 
❌ 같은 장소를 다른 이름으로 반복

**반드시 할 것:**
✅ 각 장소는 전체 여행에서 단 한 번만 등장
✅ 구체적 고유명사 사용
✅ 여행 페이스에 맞는 활동 개수: 널널하게(3개), 타이트하게(4개)
✅ JSON 형식으로 정확히 응답"""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,  # AI 응답의 최대 길이 (더 긴 응답을 위해 증가)
            temperature=0.3   # AI의 창의성 수준을 낮춰 더 일관되고 규칙을 잘 따르도록 설정
        )
        
        # API 호출 완료 시점 기록
        api_end_time = datetime.now()
        api_duration = (api_end_time - api_start_time).total_seconds()
        logger.info(f"=== OpenAI API 응답 수신 완료 ===")
        logger.info(f"API 호출 완료 시간: {api_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"API 응답 소요 시간: {api_duration:.2f}초")
        
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
                
                # 중복 장소 제거
                logger.info("중복 장소 검사를 시작합니다...")
                trip_data = await remove_duplicate_locations(trip_data, request.destination)
                
                # 중복 제거 후 최종 검증
                logger.info("중복 제거 후 최종 검증을 시작합니다...")
                final_duplicates = await check_final_duplicates(trip_data)
                if final_duplicates:
                    logger.warning(f"최종 검증에서 여전히 중복 발견: {final_duplicates}")
                    # 추가 중복 제거 시도
                    trip_data = await remove_duplicate_locations(trip_data, request.destination)
                
                # 카카오 API로 장소 검증 및 보강
                logger.info("카카오 API를 사용하여 장소 검증을 시작합니다...")
                trip_data = await verify_and_enrich_trip_data(trip_data, kakao_service, request.destination)
                
                # 숙박 정보는 trip_hotel_search 링크로만 제공하므로 accommodation 처리 생략
                
                # 전체 여행에 대한 호텔 검색 링크를 생성합니다
                trip_hotel_search = hotel_service.create_trip_hotel_search_links(
                    request.destination, 
                    request.start_date, 
                    request.end_date,
                    request.guests,
                    request.rooms
                )
                trip_data["trip_hotel_search"] = trip_hotel_search
                
                # 위치 검증 수행 (선택적) - 1일차 일정 누락 문제로 임시 비활성화
                validation_enabled = os.getenv('ENABLE_LOCATION_VALIDATION', 'false').lower() == 'true'
                validation_enabled = False  # 임시로 강제 비활성화
                if validation_enabled:
                    try:
                        validation_result = validate_trip_locations(
                            trip_data.get("itinerary", []), 
                            request.destination
                        )
                        
                        # 검증 결과가 좋지 않은 경우 경고 로그
                        if validation_result['invalid_places_count'] > 0:
                            logger.warning(f"위치 검증 결과: {validation_result['invalid_places_count']}개의 장소를 찾을 수 없습니다")
                            logger.warning(f"문제 장소들: {[p['location'] for p in validation_result['invalid_places']]}")
                        
                        # 검증 결과를 응답에 포함 (개발용)
                        trip_data["location_validation"] = validation_result
                        
                    except Exception as e:
                        logger.error(f"기존 위치 검증 중 오류: {e}")
                
                # 지오코딩 검증 비활성화 (카카오 API만 사용)
                logger.info("지오코딩 검증이 비활성화되어 있습니다. 카카오 API만 사용합니다.")
                
                # 실제 장소 정보 추가 비활성화 (카카오 API만 사용)
                logger.info("실제 장소 정보 추가가 비활성화되어 있습니다. 카카오 API만 사용합니다.")
                
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
            
            # 여행 기간에 맞는 일정을 생성합니다 (새로운 activities 구조)
            itinerary_list = []
            for day in range(1, travel_days + 1):
                current_date = start_date + timedelta(days=day - 1)
                
                # 여행 페이스에 따른 활동 수 결정
                if request.travelPace == "타이트하게":
                    # 하루 4개 활동
                    activities = [
                        {"time": "09:00", "title": f"{day}일차 오전 관광", "location": f"{request.destination} 주요 관광지", "description": "주요 관광지 방문", "duration": "2시간"},
                        {"time": "12:00", "title": f"점심 및 현지 명소", "location": f"{request.destination} 맛집", "description": "현지 음식 체험 후 명소 탐방", "duration": "2시간"},
                        {"time": "15:00", "title": f"오후 체험 활동", "location": f"{request.destination} 체험장소", "description": "액티비티 참여", "duration": "2.5시간"},
                        {"time": "18:30", "title": f"저녁 식사", "location": f"{request.destination} 음식점", "description": "저녁 식사 및 휴식", "duration": "1.5시간"}
                    ]
                elif request.travelPace == "널널하게":
                    # 하루 3개 활동
                    activities = [
                        {"time": "10:00", "title": f"{day}일차 여유로운 관광", "location": f"{request.destination} 대표 관광지", "description": "천천히 둘러보며 여유있게 관광", "duration": "3시간"},
                        {"time": "15:00", "title": f"점심 및 현지 체험", "location": f"{request.destination} 유명 맛집", "description": "현지 특색 음식을 여유롭게 즐기고 문화 체험", "duration": "2.5시간"},
                        {"time": "19:00", "title": f"저녁 식사 및 산책", "location": f"{request.destination} 저녁 맛집", "description": "현지 음식을 즐기며 여유로운 저녁 산책", "duration": "2시간"}
                    ]
                else:  # 보통
                    # 하루 3개 활동
                    activities = [
                        {"time": "09:30", "title": f"{day}일차 오전 관광", "location": f"{request.destination} 주요 관광지", "description": "주요 관광지 방문", "duration": "2.5시간"},
                        {"time": "13:30", "title": f"점심 및 오후 활동", "location": f"{request.destination} 맛집", "description": "현지 음식 체험 후 오후 활동", "duration": "3시간"},
                        {"time": "18:00", "title": f"저녁 식사", "location": f"{request.destination} 음식점", "description": "저녁 식사 및 휴식", "duration": "1.5시간"}
                    ]
                
                itinerary_list.append({
                    "day": day,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "activities": activities,
                    "accommodation": f"{request.destination} 추천 호텔"
                })
            
            # 전체 여행에 대한 호텔 검색 링크를 생성합니다
            trip_hotel_search = hotel_service.create_trip_hotel_search_links(
                request.destination, 
                request.start_date, 
                request.end_date,
                request.guests,
                request.rooms
            )
            
            # 대중교통 정보는 제거됨
            
            # 여행 기간 계산 (실제 여행 일수)
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            travel_days = (end_date - start_date).days + 1  # 실제 여행 일수 (2박3일 = 3일)
            
            # 1인당 예상 비용 계산 (예산 등급별 세부 계산)
            estimated_cost_per_person = calculate_trip_cost(request.budget, travel_days, request.destination)
            
            return TripPlan(
                destination=request.destination,
                duration=f"{request.start_date} ~ {request.end_date}",
                itinerary=itinerary_list,
                total_cost=f"1인당 {estimated_cost_per_person:,}원",
                tips=["여행 전 날짜 확인", "필수품 준비", "현지 교통 정보 파악"],
                trip_hotel_search=trip_hotel_search
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
# 대중교통 정보 API 엔드포인트
# ========================================


# ========================================
# 메인 실행 부분
# ========================================
# 이 파일을 직접 실행할 때만 서버를 시작합니다
if __name__ == "__main__":
    import uvicorn  # ASGI 서버 (FastAPI를 실행하기 위한 서버)
    
    print("=== 서버 시작 ===")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 모든 IP에서 접근 가능, 8000번 포트 사용


# ========================================
# 위치 피드백 수집 API 엔드포인트
# ========================================

from pydantic import BaseModel

class LocationFeedback(BaseModel):
    location: str
    feedback_type: str  # 'not-exist', 'wrong-info', etc.
    destination: str

@app.post("/location-feedback")
async def collect_location_feedback(feedback: LocationFeedback):
    """존재하지 않는 장소에 대한 사용자 피드백을 수집하는 API"""
    try:
        logger.warning(f"장소 오류 신고: {feedback.location} in {feedback.destination} - 타입: {feedback.feedback_type}")
        
        # 실제 구현에서는 데이터베이스에 저장하거나 관리자에게 알림을 보낼 수 있습니다
        # 현재는 로그로만 기록합니다
        
        return {"success": True, "message": "피드백이 접수되었습니다."}
    except Exception as e:
        logger.error(f"피드백 수집 오류: {e}")
        return {"success": False, "message": "피드백 수집 중 오류가 발생했습니다."}



# ========================================
# 채팅을 통한 일정 수정 API 엔드포인트
# ========================================

@app.post("/modify-trip-chat")
async def modify_trip_chat(request: ChatModifyRequest):
    """채팅을 통해 여행 일정을 수정하는 API"""
    try:
        logger.info(f"채팅 수정 요청: {request.message}")
        logger.info(f"현재 여행지: {request.current_trip_plan.get('destination', 'N/A')}")
        
        # OpenAI API를 사용하여 수정 요청 처리
        client = openai.OpenAI(api_key=openai_api_key)
        
        # 현재 일정 데이터를 문자열로 변환
        current_plan_str = json.dumps(request.current_trip_plan, ensure_ascii=False, indent=2)
        
        # GPT에게 수정 요청을 처리하도록 하는 프롬프트
        modify_prompt = f"""
다음은 현재 여행 계획입니다:

{current_plan_str}

사용자의 수정 요청: "{request.message}"

위 수정 요청에 따라 여행 계획을 수정해주세요. 

**수정 기능별 처리 방법:**

1. **일정 추가 요청**:
   - "1일차 일정 늘려줘", "2일차에 활동 하나 더 추가해줘" → 해당 일차에 새로운 활동 1개 추가
   - "○일차 오후에 뭔가 더 추가해줘" → 해당 일차 오후 시간대에 활동 추가
   - 새 활동은 해당 지역의 실제 존재하는 관광지로 설정
   - 기존 활동들과 시간이 겹치지 않도록 적절한 시간 배정
   - 기존 활동들과 중복되지 않는 새로운 장소 선택

2. **일정 제거 요청**:
   - "1일차 ○○ 빼줘", "2일차 마사지 제거해줘" → 해당 활동을 완전히 제거
   - "○일차 오후 일정 빼줘" → 해당 시간대의 활동 제거
   - 제거 후 시간 간격이 너무 크면 다른 활동들의 시간을 자연스럽게 조정

3. **일정 교체 요청**:
   - "1일차 ○○를 다른 곳으로 바꿔줘" → 해당 활동을 같은 시간대의 다른 활동으로 교체
   - "2일차 마사지를 맛집으로 바꿔줘" → 해당 활동을 요청한 종류의 활동으로 교체
   - 시간대와 소요시간은 유지하되 내용만 변경

4. **장소 간 교체/이동 요청**:
   - "2일차 ○○과 3일차 △△ 바꿔줘" → 두 활동의 위치를 서로 교환
   - "1일차 ○○를 2일차로 옮겨줘" → 활동을 다른 일차로 이동
   - 시간대는 각 일차의 기존 패턴에 맞게 조정

5. **활동 내용 변경**:
   - "○일차 ○○를 더 재미있게 바꿔줘" → 같은 장소에서 다른 활동으로 변경
   - "1일차를 더 액티브하게 바꿔줘" → 해당 일차 전체를 더 활동적인 내용으로 변경

**필수 준수 사항:**
- 새로 추가/변경되는 모든 장소는 해당 지역에 실제 존재하는 구체적인 관광지명 사용
- 기존 활동들과 중복되지 않는 장소 선택
- 시간 흐름이 자연스럽게 유지되도록 조정
- destination, duration, total_cost, tips 등 기본 정보는 그대로 유지
- JSON 형식을 정확히 유지

**응답 형식**: 코드 블록 없이 순수 JSON만 반환하세요.

**예시 처리**:
- "1일차 일정 늘려줘" → 1일차에 새로운 관광지 활동 1개 추가
- "2일차 마사지 빼줘" → 2일차에서 마사지 관련 활동 제거
- "3일차 ○○를 맛집으로 바꿔줘" → 3일차의 해당 활동을 현지 맛집 방문으로 교체
- "1일차 ○○와 2일차 △△ 바꿔줘" → 두 활동의 일차를 서로 교환
"""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 여행 계획 수정 전문가입니다. 다음 기능들을 정확히 처리할 수 있습니다: 1) 일정 추가 ('일정 늘려줘') 2) 일정 제거 ('○○ 빼줘') 3) 일정 교체 ('○○를 △△로 바꿔줘') 4) 일정 이동 ('A와 B 바꿔줘') 5) 활동 변경 ('더 재미있게 바꿔줘'). 모든 새 장소는 실제 존재하는 관광지여야 하며, 기존 장소와 중복되면 안 됩니다. 코드 블록이나 설명 없이 순수 JSON만 출력하세요."},
                    {"role": "user", "content": modify_prompt}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            
            response_content = completion.choices[0].message.content.strip()
            logger.info(f"OpenAI 응답 (처음 200자): {response_content[:200]}...")
            
            # JSON 파싱 시도 (더 강력한 정리)
            try:
                # 다양한 형태의 코드 블록 제거
                content = response_content.strip()
                
                # ```json이나 ``` 코드 블록 제거
                if content.startswith('```'):
                    lines = content.split('\n')
                    # 첫 번째 ```가 있는 줄 제거
                    if lines[0].strip() in ['```', '```json']:
                        lines = lines[1:]
                    # 마지막 ```가 있는 줄 제거
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    content = '\n'.join(lines)
                
                # 앞뒤 공백과 개행 제거
                content = content.strip()
                
                # 추가 정리: 맨 앞뒤에 있는 불필요한 텍스트 제거
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                # 첫 번째 {부터 마지막 }까지만 추출
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    content = content[start_idx:end_idx+1]
                
                logger.info(f"정리된 JSON (처음 200자): {content[:200]}...")
                
                # JSON 파싱
                modified_plan = json.loads(content)
                
                return {
                    "success": True,
                    "modified_plan": modified_plan,
                    "message": "일정이 성공적으로 수정되었습니다."
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                logger.error(f"원본 응답: {response_content}")
                logger.error(f"정리된 내용: {content}")
                
                # JSON 파싱 실패시 더 상세한 안내 제공
                return {
                    "success": False,
                    "message": f"'{request.message}' 요청을 처리하는 중에 시스템 오류가 발생했습니다. 다시 시도해주세요.",
                    "suggestion": "다음과 같이 더 구체적으로 요청해주세요: '3일차 마사지를 해운대 해변 산책으로 바꿔줘', '2일차 오후 일정을 맛집 투어로 바꿔줘'"
                }
                
        except Exception as openai_error:
            logger.error(f"OpenAI API 오류: {openai_error}")
            return {
                "success": False,
                "message": "일정 수정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            }
            
    except Exception as e:
        logger.error(f"채팅 수정 처리 중 오류: {e}")
        return {
            "success": False,
            "message": "요청 처리 중 오류가 발생했습니다."
        }