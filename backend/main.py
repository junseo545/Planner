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
import requests  # HTTP 요청을 위한 라이브러리
import re  # 정규표현식을 위한 라이브러리
from location_validator import validate_trip_locations, PlaceValidationResult
from naver_geocoding import NaverGeocodingService
from naver_place_service import NaverPlaceService

load_dotenv()

# 네이버 API 인증
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ========================================
# 네이버 API 검색 서비스 클래스
# ========================================
class NaverSearchService:
    """네이버 API를 활용한 검색 서비스"""
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
    
    def search_events(self, destination: str, start_date: str, end_date: str) -> List[dict]:
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
        
        # 장소명으로 검색 시도
        search_result = self.search_place(title, region)
        
        if not search_result or not search_result.get('found'):
            # 제목으로 찾지 못하면 location으로 재시도
            if location and location != title:
                search_result = self.search_place(location, region)
        
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
                
            logger.info(f"장소 검증 성공: {title} -> {search_result.get('name')}")
        else:
            activity['verified'] = False
            logger.warning(f"장소 검증 실패: {title}")
            
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
            
            # 재생성 프롬프트
            regeneration_prompt = f"""
다음 여행 일정에서 "{original.get('title', '')}" 활동을 {destination} 지역의 실제 존재하는 장소로 대체해주세요.

현재 {day_num}일차 다른 활동들:
{json.dumps(other_activities, ensure_ascii=False, indent=2)}

요구사항:
1. {destination} 지역에 실제로 존재하는 관광지/맛집/체험활동으로 대체
2. 기존 시간대({original.get('time', '')})와 비슷한 시간으로 설정
3. 다른 활동들과 겹치지 않는 장소 선택
4. JSON 형식으로 단일 activity 객체만 반환

JSON 형식:
{{
    "time": "시간",
    "title": "실제 장소명",
    "location": "구체적인 주소",
    "description": "활동 설명",
    "duration": "소요시간"
}}
"""
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 여행 전문가입니다. 실제 존재하는 장소만 추천해주세요."},
                    {"role": "user", "content": regeneration_prompt}
                ],
                max_tokens=500,
                temperature=0.7
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
            else:
                logger.error(f"{day_num}일차 활동 재생성 실패: JSON 파싱 오류")
                
        except Exception as e:
            logger.error(f"{day_num}일차 활동 재생성 중 오류 발생: {str(e)}")
    
    return trip_data

# ========================================
# 중복 장소 제거 함수
# ========================================
async def remove_duplicate_locations(trip_data: dict, destination: str) -> dict:
    """
    여행 계획에서 중복되는 장소를 감지하고 제거합니다.
    중복된 장소는 새로운 장소로 교체됩니다.
    """
    if not trip_data.get("itinerary"):
        return trip_data
    
    visited_locations = set()
    duplicates = []
    
    # 중복 장소 감지
    for day_idx, day in enumerate(trip_data["itinerary"]):
        if not day.get("activities"):
            continue
            
        for activity_idx, activity in enumerate(day["activities"]):
            # 호텔/숙박 관련 활동은 체크하지 않음
            title = activity.get('title', '').lower()
            if any(keyword in title for keyword in ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out']):
                continue
            
            # 장소명으로 중복 체크
            place_name = activity.get('title', '').strip()
            location_name = activity.get('location', '').strip()
            
            # 정규화된 장소명 생성 (공백, 특수문자 제거)
            normalized_title = ''.join(place_name.lower().split())
            normalized_location = ''.join(location_name.lower().split())
            
            # 중복 체크 (제목 또는 위치가 같으면 중복으로 간주)
            location_key = normalized_title or normalized_location
            
            if location_key and location_key in visited_locations:
                duplicates.append({
                    'day_idx': day_idx,
                    'activity_idx': activity_idx,
                    'day': day.get('day'),
                    'original_activity': activity.copy(),
                    'duplicate_key': location_key
                })
                logger.info(f"중복 장소 발견: {place_name} ({day.get('day')}일차)")
            elif location_key:
                visited_locations.add(location_key)
    
    # 중복된 장소들을 새로운 장소로 교체
    if duplicates:
        logger.info(f"중복된 장소 {len(duplicates)}개를 새로운 장소로 교체합니다...")
        trip_data = await replace_duplicate_activities(trip_data, duplicates, destination, visited_locations)
    
    return trip_data

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
            
            # 교체용 프롬프트
            replacement_prompt = f"""
다음 여행 일정에서 "{original.get('title', '')}" 활동을 {destination} 지역의 다른 장소로 교체해주세요.
이 장소는 이미 다른 날에 방문 예정이므로 중복을 피해야 합니다.

현재 {day_num}일차 다른 활동들:
{json.dumps(other_activities, ensure_ascii=False, indent=2)}

이미 방문 예정인 장소들 (피해야 할 장소들):
{', '.join(visited_list[:10])}  # 처음 10개만 표시

요구사항:
1. {destination} 지역에 실제로 존재하는 관광지/맛집/체험활동으로 교체
2. 기존 시간대({original.get('time', '')})와 비슷한 시간으로 설정
3. 위에 나열된 장소들과 완전히 다른 새로운 장소 선택
4. 다른 활동들과 지리적으로 접근 가능한 장소 선택
5. JSON 형식으로 단일 activity 객체만 반환

JSON 형식:
{{
    "time": "시간",
    "title": "새로운 실제 장소명",
    "location": "구체적인 주소",
    "description": "활동 설명",
    "duration": "소요시간"
}}
"""
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 여행 전문가입니다. 중복을 피해 실제 존재하는 새로운 장소만 추천해주세요."},
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
                
                # 새로운 활동으로 교체
                trip_data["itinerary"][day_idx]["activities"][activity_idx] = new_activity
                
                # 새로운 장소를 방문 목록에 추가
                new_place_name = new_activity.get('title', '').strip()
                if new_place_name:
                    normalized_new = ''.join(new_place_name.lower().split())
                    visited_locations.add(normalized_new)
                
                logger.info(f"{day_num}일차 중복 장소 교체 완료: {original.get('title')} -> {new_activity.get('title')}")
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
    accommodation: List[HotelInfo]  # 숙박 정보
    total_cost: str  # 총 예상 비용
    tips: List[str]  # 여행 팁 리스트
    transport_info: Optional[dict] = None  # 대중교통 정보
    trip_hotel_search: Optional[dict] = None  # 전체 여행에 대한 호텔 검색 링크


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
# 축제/행사 정보 서비스 클래스
# ========================================
# 이 클래스는 여행 기간에 해당하는 축제나 행사 정보를 제공합니다

class EventService:
    """축제/행사 정보를 제공하는 서비스"""
    
    def __init__(self):
        self.naver_service = NaverSearchService()
    
    def get_events_by_destination_and_date(self, destination: str, start_date: str, end_date: str) -> List[dict]:
        """목적지와 날짜에 맞는 축제/행사 정보를 제공하는 메서드"""
        
        try:
            # 먼저 네이버 API로 실시간 검색 시도
            logger.info(f"네이버 API로 {destination} 지역 축제/행사 검색 시작")
            naver_events = self.naver_service.search_events(destination, start_date, end_date)
            
            # 네이버 API 검색 결과 품질 확인
            if naver_events and len(naver_events) >= 3:
                logger.info(f"네이버 API 검색 결과: {len(naver_events)}개 이벤트 발견 (품질 양호)")
                return naver_events
            elif naver_events and len(naver_events) > 0:
                logger.info(f"네이버 API 검색 결과: {len(naver_events)}개 이벤트 발견 (품질 부족)")
                # 기본 데이터베이스와 병합
                default_events = self._get_default_events(destination, start_date, end_date)
                combined_events = naver_events + default_events
                # 중복 제거
                unique_events = self._remove_duplicates(combined_events)
                return unique_events[:8]  # 최대 8개 반환
            else:
                # 네이버 API 검색 결과가 없는 경우 기본 데이터베이스 사용
                logger.info("네이버 API 검색 결과가 없어 기본 데이터베이스 사용")
                return self._get_default_events(destination, start_date, end_date)
            
        except Exception as e:
            logger.warning(f"네이버 API 검색 실패, 기본 데이터베이스 사용: {e}")
            return self._get_default_events(destination, start_date, end_date)
    
    def _get_default_events(self, destination: str, start_date: str, end_date: str) -> List[dict]:
        """기본 축제/행사 데이터베이스에서 정보를 가져오는 메서드"""
        
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
                    "location": "제주시",
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
            current_date = datetime.now().date()  # 현재 날짜
            
            # 여행 시작일이 현재 날짜보다 과거인지 확인
            if start_dt.date() < current_date:
                logger.info(f"과거 여행 제외: {start_date} (현재: {current_date})")
                return []
            
            # 목적지에 해당하는 축제/행사 목록 가져오기
            destination_events = events_db.get(destination, default_events)
            
            # 여행 기간에 해당하는 축제/행사만 필터링
            matching_events = []
            for event in destination_events:
                try:
                    event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                    
                    # 이미 지난 이벤트는 제외
                    if event_date.date() < current_date:
                        logger.info(f"과거 이벤트 제외: {event['name']} ({event['date']}) (현재: {current_date})")
                        continue
                    
                    # 여행 기간 내에 있는지 정확하게 확인 (연도 포함)
                    if start_dt <= event_date <= end_dt:
                        matching_events.append(event)
                        logger.info(f"여행 기간 내 이벤트: {event['name']} ({event['date']}) (여행: {start_date} ~ {end_date})")
                        continue
                    
                    # 연도가 바뀌는 경우 (예: 12월 31일 ~ 1월 2일) - 월/일만 비교
                    if start_dt.month > end_dt.month:
                        # 여행이 연도를 걸치는 경우
                        event_month_day = (event_date.month, event_date.day)
                        start_month_day = (start_dt.month, start_dt.day)
                        end_month_day = (end_dt.month, end_dt.day)
                        
                        # 월/일 기준으로 매칭
                        if (event_month_day >= start_month_day) or (event_month_day <= end_month_day):
                            matching_events.append(event)
                            logger.info(f"연도 걸친 여행 기간 내 이벤트: {event['name']} ({event['date']}) (여행: {start_date} ~ {end_date})")
                            continue
                    
                    # 여행 기간 밖의 이벤트는 제외
                    logger.info(f"여행 기간 밖 이벤트 제외: {event['name']} ({event['date']}) (여행: {start_date} ~ {end_date})")
                        
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
        
        # 주요 관광지 키워드 패턴
        location_patterns = [
            r'([가-힣]+해수욕장)',  # 해수욕장
            r'([가-힣]+시장)',      # 시장
            r'([가-힣]+공원)',      # 공원
            r'([가-힣]+역)',        # 역
            r'([가-힣]+항)',        # 항
            r'([가-힣]+봉)',        # 봉
            r'([가-힣]+굴)',        # 굴
            r'([가-힣]+사)',        # 사찰
            r'([가-힣]+궁)',        # 궁궐
            r'([가-힣]+성)',        # 성
            r'([가-힣]+탑)',        # 탑
            r'([가-힣]+다리)',      # 다리
            r'([가-힣]+거리)',      # 거리
            r'([가-힣]+로)',        # 도로
            r'([가-힣]+동)',        # 동
            r'([가-힣]+구)',        # 구
            r'([가-힣]+읍)',        # 읍
            r'([가-힣]+면)'         # 면
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

@app.post("/plan-trip", response_model=TripPlan)
async def plan_trip(request: TripRequest):
    """여행 계획을 생성하는 메인 API"""
    try:
        # 로그에 요청 정보를 기록합니다
        logger.info(f"여행 계획 생성 요청: {request.destination}, {request.start_date} ~ {request.end_date}")
        
        # 호텔 검색 서비스를 초기화합니다
        hotel_service = HotelSearchService()
        
        # 카카오 로컬 서비스를 초기화합니다
        kakao_service = KakaoLocalService()
        
        # 여행 일수를 계산합니다
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            travel_days = (end_date - start_date).days + 1
        except:
            travel_days = 3  # 날짜 계산에 실패하면 기본값 3일을 사용합니다
        
        # OpenAI API에 전달할 프롬프트(질문)를 생성합니다
        # 프롬프트는 AI에게 무엇을 해달라고 요청하는 메시지입니다
        prompt = f"""
        다음 조건에 맞는 상세한 여행 계획을 한국어로 작성해주세요:
        
        목적지: {request.destination}
        여행 기간: {request.start_date} ~ {request.end_date} (총 {travel_days}일)
        예산: {request.budget}
        관심사: {', '.join(request.interests) if request.interests else '일반적인 관광'}
        투숙객: {request.guests}명, 객실: {request.rooms}개
        여행 페이스: {request.travelPace if request.travelPace else '보통'}
        
        ⚠️ **중요 지침: 실제 존재하는 장소만 추천해주세요**
        - 모든 관광지, 음식점, 실제로 존재하는 장소여야 합니다
        - 확실하지 않은 장소는 추천하지 마세요
        - 유명하고 검증된 관광명소를 우선적으로 포함해주세요
        - 호텔은 알려주지 마세요
        
        ⚠️ **음식점 및 장소 추천 시 주의사항**
        - 가상의 동네명이나 지역명을 만들지 마세요 (예: "하구마을", "중앙시장" 등)
        - 음식점명은 구체적인 상호명 대신 "현지 유명 빈대떡집", "전통 한식당" 등으로 표현하세요
        - 위치는 실제 도로명이나 동명을 사용하세요 (예: "여수시 중앙동", "여수 돌산대교 근처")
        - 불확실한 정보보다는 일반적인 설명을 선호하세요
        
        다음 형식으로 JSON 응답을 제공해주세요:
        
        여행 페이스별 활동 개수 가이드:
        - 타이트하게: 하루에 4-6개 활동 (빠른 이동, 다양한 체험)
        - 널널하게: 하루에 2-3개 활동 (여유로운 일정, 충분한 휴식)
        {{
            "destination": "목적지명",
            "duration": "여행 기간",
            "itinerary": [
                {{
                    "day": 1,
                    "date": "{request.start_date}",
                    "activities": [
                        {{
                            "time": "09:00",
                            "title": "활동명",
                            "location": "구체적인 장소명",
                            "description": "활동 설명",
                            "duration": "소요시간"
                        }}
                    ],
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
            "total_cost": "1인당 예상 비용",
            "tips": ["여행 팁1", "여행 팁2", "여행 팁3"]
        }}
        
        중요사항:
        1. accommodation의 name 필드에는 실제 존재하는 호텔명을 사용해주세요. 가상의 호텔명(예: "호텔 A", "추천 호텔")은 사용하지 마세요.
        2. itinerary 배열에는 여행 기간에 맞는 모든 일차를 포함해주세요. {travel_days}일 여행이면 {travel_days}개의 일차가 있어야 합니다.
        3. activities 배열에는 여행 페이스에 따라 다른 수의 활동을 포함해주세요:
           - "타이트하게": 하루에 4-6개 활동 (시간별로 세밀하게 계획된 일정)
           - "널널하게": 하루에 2-3개 활동 (각 활동에 충분한 시간 할애)
        4. 각 activity에는 정확한 시간(time), 제목(title), 위치(location), 설명(description), 소요시간(duration)을 포함해주세요.
        5. time은 24시간 형식(예: "09:00", "14:30")으로 작성하고, 여행 페이스에 따라 활동 간격을 조절해주세요.
        6. total_cost는 반드시 "1인당 XXX,XXX원" 형식으로 작성해주세요. 예산별 가이드: 저예산(1일 8-10만원), 보통(1일 12-15만원), 고급(1일 20-25만원), 럭셔리(1일 35-50만원). 예시: "1인당 375,000원"
        7. **중복 장소 금지**: 같은 장소(관광지, 음식점 등)를 여러 날에 중복으로 포함하지 마세요. 각 장소는 한 번만 방문하도록 계획해주세요.
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
                
                # 중복 장소 제거
                logger.info("중복 장소 검사를 시작합니다...")
                trip_data = await remove_duplicate_locations(trip_data, request.destination)
                
                # 카카오 API로 장소 검증 및 보강
                logger.info("카카오 API를 사용하여 장소 검증을 시작합니다...")
                trip_data = await verify_and_enrich_trip_data(trip_data, kakao_service, request.destination)
                
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
                
                # 전체 여행에 대한 호텔 검색 링크를 생성합니다
                trip_hotel_search = hotel_service.create_trip_hotel_search_links(
                    request.destination, 
                    request.start_date, 
                    request.end_date,
                    request.guests,
                    request.rooms
                )
                trip_data["trip_hotel_search"] = trip_hotel_search
                
                # 위치 검증 수행 (선택적)
                validation_enabled = os.getenv('ENABLE_LOCATION_VALIDATION', 'false').lower() == 'true'
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
                
                # 네이버 지오코딩을 사용한 위치 검증 (선택적)
                geocoding_enabled = os.getenv('ENABLE_GEOCODING_VALIDATION', 'true').lower() == 'true'
                
                if geocoding_enabled:
                    try:
                        geocoding_service = NaverGeocodingService()
                        
                        # API 키가 있는지 확인
                        if geocoding_service.client_id and geocoding_service.client_secret:
                            logger.info(f"네이버 지오코딩으로 {request.destination} 지역 검증 시작")
                        else:
                            logger.info(f"네이버 API 키가 없어 텍스트 기반 검증 실행: {request.destination}")
                        
                        if trip_data.get('itinerary'):
                            validated_itinerary = []
                            total_activities = 0
                            invalid_activities = 0
                            
                            for day in trip_data['itinerary']:
                                if day.get('activities'):
                                    activities = day['activities']
                                    validation_result = geocoding_service.validate_activity_locations(
                                        activities, request.destination
                                    )
                                    
                                    total_activities += len(activities)
                                    invalid_activities += len(validation_result['invalid_activities'])
                                    
                                    # 유효한 활동들만 사용하고, 유효하지 않은 활동은 필터링
                                    valid_activities = validation_result['valid_activities']
                                    
                                    if validation_result['invalid_activities']:
                                        logger.info(f"{day['day']}일차에서 {len(validation_result['invalid_activities'])}개의 부적절한 장소 발견")
                                        
                                        for invalid_activity in validation_result['invalid_activities']:
                                            logger.info(f"지역 불일치 제거: {invalid_activity.get('location', 'Unknown')}")
                                    
                                    # 활동이 너무 적어지지 않도록 최소 1개는 유지
                                    if len(valid_activities) == 0 and len(activities) > 0:
                                        logger.warning(f"{day['day']}일차의 모든 활동이 제거되어 원본 유지")
                                        day['activities'] = activities  # 원본 유지
                                    else:
                                        day['activities'] = valid_activities
                                
                                validated_itinerary.append(day)
                            
                            # 검증 통계 로그
                            if invalid_activities > 0:
                                logger.info(f"지오코딩 검증: 총 {total_activities}개 활동 중 {invalid_activities}개 부적절한 장소 처리")
                            else:
                                logger.info(f"지오코딩 검증: 모든 {total_activities}개 활동이 {request.destination} 지역에 적합합니다")
                            
                            # 검증된 일정으로 업데이트
                            trip_data['itinerary'] = validated_itinerary
                            
                    except Exception as e:
                        logger.error(f"네이버 지오코딩 검증 중 오류: {e}")
                        # 검증 실패해도 여행 계획은 반환
                else:
                    logger.info("지오코딩 검증이 비활성화되어 있습니다.")
                
                # 실제 장소 정보 추가 (네이버 검색 API 활용)
                place_enhancement_enabled = os.getenv('ENABLE_PLACE_ENHANCEMENT', 'true').lower() == 'true'
                
                if place_enhancement_enabled:
                    try:
                        place_service = NaverPlaceService()
                        
                        if place_service.search_client_id and place_service.search_client_secret:
                            logger.info(f"네이버 검색 API로 실제 장소 정보 추가 시작: {request.destination}")
                            
                            # 일정에 실제 장소 정보 추가
                            enhanced_itinerary = place_service.enhance_itinerary_with_real_places(
                                trip_data.get('itinerary', []), 
                                request.destination
                            )
                            
                            trip_data['itinerary'] = enhanced_itinerary
                            logger.info("실제 장소 정보 추가 완료")
                            
                        else:
                            logger.info("네이버 검색 API 키가 없어 실제 장소 정보 추가를 건너뜁니다.")
                            
                    except Exception as e:
                        logger.error(f"실제 장소 정보 추가 중 오류: {e}")
                        # 오류가 발생해도 여행 계획은 반환
                else:
                    logger.info("실제 장소 정보 추가가 비활성화되어 있습니다.")
                
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
                    activities = [
                        {"time": "09:00", "title": f"{day}일차 오전 관광", "location": f"{request.destination} 주요 관광지", "description": "주요 관광지 방문", "duration": "2시간"},
                        {"time": "11:30", "title": f"현지 명소 탐방", "location": f"{request.destination} 명소", "description": "현지 문화 체험", "duration": "1.5시간"},
                        {"time": "14:00", "title": f"점심 및 휴식", "location": f"{request.destination} 맛집", "description": "현지 음식 체험", "duration": "1시간"},
                        {"time": "16:00", "title": f"오후 활동", "location": f"{request.destination} 체험장소", "description": "액티비티 참여", "duration": "2시간"},
                        {"time": "19:00", "title": f"저녁 식사", "location": f"{request.destination} 음식점", "description": "저녁 식사 및 휴식", "duration": "1.5시간"}
                    ]
                else:  # 널널하게
                    activities = [
                        {"time": "10:00", "title": f"{day}일차 여유로운 관광", "location": f"{request.destination} 대표 관광지", "description": "천천히 둘러보며 여유있게 관광", "duration": "3시간"},
                        {"time": "14:00", "title": f"점심 및 현지 맛집 탐방", "location": f"{request.destination} 유명 맛집", "description": "현지 특색 음식을 여유롭게 즐기기", "duration": "1.5시간"},
                        {"time": "16:30", "title": f"현지 체험 및 쇼핑", "location": f"{request.destination} 체험장소", "description": "현지 문화를 깊이 있게 체험하고 기념품 쇼핑", "duration": "2시간"},
                        {"time": "19:30", "title": f"저녁 식사 및 산책", "location": f"{request.destination} 저녁 맛집", "description": "현지 음식을 즐기며 여유로운 저녁 산책", "duration": "2시간"}
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
                accommodation=accommodation_list,
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

@app.get("/transport/info/{city}/{destination}")
async def get_transport_info(city: str, destination: str):
    """특정 도시의 목적지로 가는 대중교통 정보를 조회하는 API"""
    try:
        transport_service = PublicTransportService()
        info = transport_service.get_transport_info(city, destination)
        return {
            "city": city,
            "destination": destination,
            "transport_info": info
        }
    except Exception as e:
        logger.error(f"대중교통 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"대중교통 정보 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/transport/destinations/{city}")
async def get_all_destinations(city: str):
    """특정 도시의 모든 목적지 목록을 조회하는 API"""
    try:
        transport_service = PublicTransportService()
        destinations = transport_service.get_all_destinations(city)
        return destinations
    except Exception as e:
        logger.error(f"목적지 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"목적지 목록 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/transport/route")
async def search_transport_route(
    city: str,
    from_location: str,
    to_location: str
):
    """출발지에서 목적지로 가는 대중교통 경로를 검색하는 API"""
    try:
        transport_service = PublicTransportService()
        route_info = transport_service.search_transport_routes(city, from_location, to_location)
        return route_info
    except Exception as e:
        logger.error(f"경로 검색 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"경로 검색 중 오류가 발생했습니다: {str(e)}")

@app.get("/transport/busan/jagalchi")
async def get_jagalchi_transport_info():
    """부산 자갈치시장으로 가는 대중교통 정보를 조회하는 전용 API"""
    try:
        transport_service = PublicTransportService()
        info = transport_service.get_transport_info("부산", "자갈치시장")
        return {
            "destination": "부산 자갈치시장",
            "description": "부산의 대표적인 수산물 시장으로 신선한 해산물과 다양한 먹거리를 즐길 수 있습니다.",
            "transport_info": info
        }
    except Exception as e:
        logger.error(f"자갈치시장 대중교통 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"자갈치시장 대중교통 정보 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/transport/itinerary/{city}")
async def get_itinerary_transport_info(city: str, itinerary: str):
    """특정 도시의 여행 일정에 대한 대중교통 정보를 조회하는 API"""
    try:
        # itinerary는 JSON 문자열로 전달됨
        import json
        itinerary_data = json.loads(itinerary)
        
        transport_service = PublicTransportService()
        transport_info = transport_service.get_itinerary_transport_info(city, itinerary_data)
        
        return {
            "city": city,
            "itinerary": itinerary_data,
            "transport_info": transport_info
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="잘못된 일정 형식입니다. JSON 형식으로 전달해주세요.")
    except Exception as e:
        logger.error(f"일정 대중교통 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"일정 대중교통 정보 조회 중 오류가 발생했습니다: {str(e)}")

# ========================================
# 메인 실행 부분
# ========================================
# 이 파일을 직접 실행할 때만 서버를 시작합니다
if __name__ == "__main__":
    import uvicorn  # ASGI 서버 (FastAPI를 실행하기 위한 서버)
    
    print("=== 서버 시작 ===")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 모든 IP에서 접근 가능, 8000번 포트 사용

# ========================================
# 대중교통 정보 서비스 클래스
# ========================================
class PublicTransportService:
    """대중교통 정보를 제공하는 서비스"""
    
    def __init__(self):
        self.bus_info_db = {
            "부산": {
                "자갈치시장": {
                    "description": "부산의 대표적인 수산물 시장으로 신선한 해산물과 다양한 먹거리를 즐길 수 있습니다.",
                    "address": "부산광역시 중구 자갈치로 52",
                    "transportation": {
                        "버스": [
                            {
                                "route": "1003번",
                                "description": "부산역 → 자갈치시장",
                                "stops": ["부산역", "중앙동", "자갈치시장"],
                                "frequency": "5-10분 간격",
                                "fare": "1,300원",
                                "operating_hours": "05:00 ~ 24:00"
                            },
                            {
                                "route": "1001번",
                                "description": "서면 → 자갈치시장",
                                "stops": ["서면역", "부전동", "자갈치시장"],
                                "frequency": "7-12분 간격",
                                "fare": "1,300원",
                                "operating_hours": "05:30 ~ 23:30"
                            },
                            {
                                "route": "100번",
                                "description": "해운대 → 자갈치시장",
                                "stops": ["해운대해수욕장", "센텀시티", "자갈치시장"],
                                "frequency": "10-15분 간격",
                                "fare": "1,300원",
                                "operating_hours": "06:00 ~ 23:00"
                            },
                            {
                                "route": "200번",
                                "description": "동래 → 자갈치시장",
                                "stops": ["동래역", "온천장", "자갈치시장"],
                                "frequency": "8-12분 간격",
                                "fare": "1,300원",
                                "operating_hours": "05:30 ~ 23:30"
                            }
                        ],
                        "지하철": [
                            {
                                "line": "1호선",
                                "station": "자갈치역",
                                "description": "자갈치시장 바로 앞에 위치",
                                "fare": "1,400원",
                                "operating_hours": "05:30 ~ 24:00"
                            }
                        ],
                        "도보": [
                            {
                                "from": "부산역",
                                "time": "약 15분",
                                "route": "부산역 → 중앙동 → 자갈치시장",
                                "tips": "바다 전망을 보며 걸을 수 있는 해안 산책로 이용 가능"
                            },
                            {
                                "from": "남포동",
                                "time": "약 10분",
                                "route": "남포동 → 광복로 → 자갈치시장",
                                "tips": "쇼핑거리를 지나며 구경할 수 있음"
                            }
                        ]
                    },
                    "tips": [
                        "자갈치시장은 새벽 3시부터 운영되므로 일찍 가면 더 신선한 해산물을 구할 수 있습니다",
                        "시장 내 식당에서는 신선한 회와 해산물 요리를 맛볼 수 있습니다",
                        "주말에는 더 많은 상인들이 나와 다양한 상품을 구경할 수 있습니다",
                        "시장 주변에 주차장이 있지만 혼잡하므로 대중교통 이용을 권장합니다"
                    ]
                },
                "해운대해수욕장": {
                    "description": "부산의 대표적인 해수욕장으로 아름다운 백사장과 맑은 바다를 즐길 수 있습니다.",
                    "address": "부산광역시 해운대구 해운대해변로 264",
                    "transportation": {
                        "버스": [
                            {
                                "route": "100번",
                                "description": "자갈치시장 → 해운대해수욕장",
                                "stops": ["자갈치시장", "센텀시티", "해운대해수욕장"],
                                "frequency": "10-15분 간격",
                                "fare": "1,300원",
                                "operating_hours": "06:00 ~ 23:00"
                            },
                            {
                                "route": "139번",
                                "description": "부산역 → 해운대해수욕장",
                                "stops": ["부산역", "센텀시티", "해운대해수욕장"],
                                "frequency": "8-12분 간격",
                                "fare": "1,300원",
                                "operating_hours": "05:30 ~ 23:30"
                            }
                        ],
                        "지하철": [
                            {
                                "line": "2호선",
                                "station": "해운대역",
                                "description": "해운대해수욕장에서 도보 5분",
                                "fare": "1,400원",
                                "operating_hours": "05:30 ~ 24:00"
                            }
                        ]
                    }
                },
                "광안리해수욕장": {
                    "description": "부산의 또 다른 아름다운 해수욕장으로 광안대교의 야경을 감상할 수 있습니다.",
                    "address": "부산광역시 수영구 광안해변로 264",
                    "transportation": {
                        "버스": [
                            {
                                "route": "1003번",
                                "description": "자갈치시장 → 광안리해수욕장",
                                "stops": ["자갈치시장", "수영구청", "광안리해수욕장"],
                                "frequency": "10-15분 간격",
                                "fare": "1,300원",
                                "operating_hours": "05:00 ~ 24:00"
                            }
                        ],
                        "지하철": [
                            {
                                "line": "2호선",
                                "station": "광안역",
                                "description": "광안리해수욕장에서 도보 3분",
                                "fare": "1,400원",
                                "operating_hours": "05:30 ~ 24:00"
                            }
                        ]
                    }
                }
            },
            "여수": {
                "여수해양공원": {
                    "description": "여수의 아름다운 바다를 한눈에 볼 수 있는 공원입니다.",
                    "address": "전라남도 여수시 돌산공원로 1",
                    "transportation": {
                        "버스": [
                            {
                                "route": "1번",
                                "description": "여수역 → 여수해양공원",
                                "stops": ["여수역", "여수시청", "여수해양공원"],
                                "frequency": "10-15분 간격",
                                "fare": "1,200원",
                                "operating_hours": "06:00 ~ 23:00"
                            }
                        ],
                        "도보": [
                            {
                                "from": "여수역",
                                "time": "약 20분",
                                "route": "여수역 → 여수시청 → 여수해양공원",
                                "tips": "해안가를 따라 걸으며 바다 전망을 즐길 수 있습니다"
                            }
                        ]
                    }
                },
                "돌산공원": {
                    "description": "여수의 상징적인 공원으로 아름다운 전망을 제공합니다.",
                    "address": "전라남도 여수시 돌산공원로 1",
                    "transportation": {
                        "버스": [
                            {
                                "route": "2번",
                                "description": "여수해양공원 → 돌산공원",
                                "stops": ["여수해양공원", "돌산공원"],
                                "frequency": "15-20분 간격",
                                "fare": "1,200원",
                                "operating_hours": "06:00 ~ 23:00"
                            }
                        ],
                        "도보": [
                            {
                                "from": "여수해양공원",
                                "time": "약 15분",
                                "route": "여수해양공원 → 돌산공원",
                                "tips": "돌산을 오르며 여수 시내를 한눈에 볼 수 있습니다"
                            }
                        ]
                    }
                },
                "여수엑스포역": {
                    "description": "2012년 여수세계박람회가 열린 곳으로 다양한 전시관과 공원이 있습니다.",
                    "address": "전라남도 여수시 엑스포대로 1",
                    "transportation": {
                        "버스": [
                            {
                                "route": "3번",
                                "description": "돌산공원 → 여수엑스포역",
                                "stops": ["돌산공원", "여수엑스포역"],
                                "frequency": "20-25분 간격",
                                "fare": "1,200원",
                                "operating_hours": "06:00 ~ 23:00"
                            }
                        ],
                        "지하철": [
                            {
                                "line": "여수엑스포선",
                                "station": "여수엑스포역",
                                "description": "엑스포역 바로 앞에 위치",
                                "fare": "1,300원",
                                "operating_hours": "05:30 ~ 24:00"
                            }
                        ]
                    }
                }
            },
            "제주": {
                "성산일출봉": {
                    "description": "제주도 동쪽 끝에 위치한 아름다운 일출 명소입니다.",
                    "address": "제주특별자치도 서귀포시 성산읍 성산리",
                    "transportation": {
                        "버스": [
                            {
                                "route": "701번",
                                "description": "제주시 → 성산일출봉",
                                "stops": ["제주시", "성산일출봉"],
                                "frequency": "30-40분 간격",
                                "fare": "1,200원",
                                "operating_hours": "06:00 ~ 22:00"
                            }
                        ],
                        "도보": [
                            {
                                "from": "성산항",
                                "time": "약 25분",
                                "route": "성산항 → 성산일출봉",
                                "tips": "해안가를 따라 걸으며 아름다운 바다 전망을 즐길 수 있습니다"
                            }
                        ]
                    }
                },
                "만장굴": {
                    "description": "세계자연유산으로 지정된 용암동굴입니다.",
                    "address": "제주특별자치도 제주시 구좌읍 만장굴길 182",
                    "transportation": {
                        "버스": [
                            {
                                "route": "702번",
                                "description": "성산일출봉 → 만장굴",
                                "stops": ["성산일출봉", "만장굴"],
                                "frequency": "40-50분 간격",
                                "fare": "1,200원",
                                "operating_hours": "06:00 ~ 22:00"
                            }
                        ]
                    }
                }
            }
        }
    
    def get_transport_info(self, city: str, destination: str) -> dict:
        """특정 도시의 목적지로 가는 대중교통 정보를 제공하는 메서드"""
        try:
            if city not in self.bus_info_db:
                return {
                    "error": f"{city}의 대중교통 정보가 준비되지 않았습니다.",
                    "available_cities": list(self.bus_info_db.keys())
                }
            
            if destination not in self.bus_info_db[city]:
                return {
                    "error": f"{city}의 {destination}으로 가는 대중교통 정보가 준비되지 않았습니다.",
                    "available_destinations": list(self.bus_info_db[city].keys())
                }
            
            return self.bus_info_db[city][destination]
            
        except Exception as e:
            logger.error(f"대중교통 정보 조회 중 오류: {e}")
            return {"error": "대중교통 정보 조회 중 오류가 발생했습니다."}
    
    def get_all_destinations(self, city: str) -> dict:
        """특정 도시의 모든 목적지 목록을 제공하는 메서드"""
        try:
            if city not in self.bus_info_db:
                return {
                    "error": f"{city}의 정보가 준비되지 않았습니다.",
                    "available_cities": list(self.bus_info_db.keys())
                }
            
            destinations = self.bus_info_db[city]
            return {
                "city": city,
                "destinations": list(destinations.keys()),
                "total_destinations": len(destinations)
            }
            
        except Exception as e:
            logger.error(f"목적지 목록 조회 중 오류: {e}")
            return {"error": "목적지 목록 조회 중 오류가 발생했습니다."}
    
    def search_transport_routes(self, city: str, from_location: str, to_location: str) -> dict:
        """출발지에서 목적지로 가는 대중교통 경로를 검색하는 메서드"""
        try:
            if city not in self.bus_info_db:
                return {"error": f"{city}의 정보가 준비되지 않았습니다."}
            
            if to_location not in self.bus_info_db[city]:
                return {"error": f"{city}의 {to_location} 정보가 준비되지 않았습니다."}
            
            # 간단한 경로 검색 (실제로는 더 복잡한 알고리즘이 필요)
            transport_info = self.bus_info_db[city][to_location]
            
            # 출발지별 추천 경로 생성
            recommended_routes = []
            
            if from_location == "부산역":
                recommended_routes.append({
                    "route_type": "버스",
                    "route": "1003번",
                    "description": "부산역에서 자갈치시장까지 직행",
                    "estimated_time": "약 20분",
                    "fare": "1,300원"
                })
                recommended_routes.append({
                    "route_type": "지하철",
                    "line": "1호선",
                    "description": "부산역 → 자갈치역",
                    "estimated_time": "약 15분",
                    "fare": "1,400원"
                })
            elif from_location == "서면":
                recommended_routes.append({
                    "route_type": "버스",
                    "route": "1001번",
                    "description": "서면에서 자갈치시장까지 직행",
                    "estimated_time": "약 25분",
                    "fare": "1,300원"
                })
            elif from_location == "해운대":
                recommended_routes.append({
                    "route_type": "버스",
                    "route": "100번",
                    "description": "해운대에서 자갈치시장까지 직행",
                    "estimated_time": "약 35분",
                    "fare": "1,300원"
                })
            else:
                # 일반적인 경로 정보 제공
                for transport_type, routes in transport_info["transportation"].items():
                    if transport_type == "버스" and routes:
                        recommended_routes.append({
                            "route_type": transport_type,
                            "route": routes[0]["route"],
                            "description": routes[0]["description"],
                            "estimated_time": "시간은 출발지에 따라 다름",
                            "fare": routes[0]["fare"]
                        })
                        break
            
            return {
                "from": from_location,
                "to": to_location,
                "city": city,
                "recommended_routes": recommended_routes,
                "all_transport_options": transport_info["transportation"]
            }
            
        except Exception as e:
            logger.error(f"경로 검색 중 오류: {e}")
            return {"error": "경로 검색 중 오류가 발생했습니다."}
    
    def get_itinerary_transport_info(self, city: str, itinerary: List[dict]) -> dict:
        """여행 일정의 장소들 간 이동 정보를 제공하는 메서드"""
        try:
            if city not in self.bus_info_db:
                return {"error": f"{city}의 정보가 준비되지 않았습니다."}
            
            transport_info = {}
            
            # 각 일차별로 장소들을 추출하고 이동 정보 생성
            for day_info in itinerary:
                day = day_info.get("day", 0)
                day_transport = []
                
                # 오전, 오후, 저녁 활동에서 장소명 추출
                activities = [
                    ("오전", day_info.get("morning", "")),
                    ("오후", day_info.get("afternoon", "")),
                    ("저녁", day_info.get("evening", ""))
                ]
                
                # 이전 장소에서 다음 장소로의 이동 정보 생성
                for i in range(len(activities) - 1):
                    current_activity = activities[i]
                    next_activity = activities[i + 1]
                    
                    # 장소명에서 주요 관광지명 추출 (간단한 키워드 매칭)
                    current_location = self._extract_location_name(current_activity[1], city)
                    next_location = self._extract_location_name(next_activity[1], city)
                    
                    if current_location and next_location:
                        route_info = self.search_transport_routes(city, current_location, next_location)
                        if "error" not in route_info:
                            day_transport.append({
                                "from": current_location,
                                "to": next_location,
                                "time": f"{current_activity[0]} → {next_activity[0]}",
                                "transport_info": route_info
                            })
                
                if day_transport:
                    transport_info[f"day_{day}"] = day_transport
            
            return {
                "city": city,
                "itinerary_transport": transport_info,
                "total_days": len(itinerary)
            }
            
        except Exception as e:
            logger.error(f"일정 이동 정보 생성 중 오류: {e}")
            return {"error": "일정 이동 정보 생성 중 오류가 발생했습니다."}
    
    def _extract_location_name(self, activity_text: str, city: str) -> str:
        """활동 텍스트에서 장소명을 추출하는 메서드"""
        try:
            # 도시별 주요 관광지 키워드 매칭
            if city in self.bus_info_db:
                for destination in self.bus_info_db[city].keys():
                    if destination in activity_text:
                        return destination
            
            # 일반적인 관광지 키워드 매칭
            common_keywords = [
                "해수욕장", "공원", "시장", "역", "항", "봉", "굴", "사", "궁", "성", "탑", "다리", "거리", "로"
            ]
            
            for keyword in common_keywords:
                if keyword in activity_text:
                    # 키워드 주변 텍스트에서 장소명 추출 시도
                    start_idx = activity_text.find(keyword)
                    if start_idx > 0:
                        # 키워드 앞의 10글자 정도를 확인하여 장소명 추출
                        potential_name = activity_text[max(0, start_idx-10):start_idx + len(keyword)]
                        # 불필요한 문자 제거
                        clean_name = re.sub(r'[^\w\s가-힣]', '', potential_name).strip()
                        if clean_name and len(clean_name) > 2:
                            return clean_name
            
            return None
            
        except Exception as e:
            logger.error(f"장소명 추출 중 오류: {e}")
            return None

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

**수정 규칙:**
1. 특정 일차의 활동을 바꾸라는 요청이면, 해당 일차(day)의 activities 배열에서 관련 활동을 찾아 새로운 활동으로 교체
2. "3일차 해운대 마사지"를 다른 활동으로 바꾸라는 요청이면, 3일차 activities에서 "마사지"가 포함된 활동을 새로운 부산 관련 활동으로 교체
3. 새 활동은 시간대, 장소, 설명을 현실적으로 설정
4. 나머지 데이터(destination, duration, total_cost, tips 등)는 그대로 유지
5. JSON 형식을 정확히 유지

**중요**: 코드 블록 없이 순수 JSON만 반환하세요.
"""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 여행 계획 수정 전문가입니다. 사용자의 요청에 따라 여행 계획을 수정하고 완전한 JSON 데이터를 반환합니다. 코드 블록이나 설명 없이 순수 JSON만 출력하세요."},
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