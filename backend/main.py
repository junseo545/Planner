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

load_dotenv()

# 네이버 API 인증키
client_id = "W9FDHYIV6V8_B7jxUJoj"
client_secret = "bZ9RDTBZ0h"

# 네이버 API 인증
CLIENT_ID = "ebhz7ru3kl"
CLIENT_SECRET = "rcpmbXqa9QTGJ7Zp8TY9S1JfiAVJPIIUE2WsGy5g"

# 1. 장소 검색 (예: 부산 자갈치시장)
def search_place(query):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {"query": query, "display": 1}
    res = requests.get(url, headers=headers, params=params)
    return res.json()

# 2. 길찾기 (예: 부산역 -> 자갈치시장)
def get_directions(start, goal):
    url = f"https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
        "X-NCP-APIGW-API-KEY": CLIENT_SECRET
    }
    params = {
        "start": start,   # "127.1054328,37.3595963"
        "goal": goal,     # "129.075986,35.179470"
        "option": "trafast"  # 최적경로
    }
    res = requests.get(url, headers=headers, params=params)
    return res.json()


# ========================================
# 네이버 API 검색 서비스 클래스
# ========================================
class NaverSearchService:
    """네이버 API를 활용한 검색 서비스"""
    
    def __init__(self):
        self.client_id = client_id
        self.client_secret = client_secret
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
            
            # 제목에서 목적지 확인
            for variant in destination_variants:
                if variant in title:
                    destination_score += 8  # 제목에 목적지가 있으면 매우 높은 점수
                    break
            
            # 설명에서 목적지 확인
            if destination_score == 0:  # 제목에 없었다면
                for variant in destination_variants:
                    if variant in description:
                        destination_score += 5  # 설명에 목적지가 있으면 높은 점수
                        break
            
            score += destination_score
            
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
        
        # 점수순으로 정렬
        return sorted(events, key=lambda x: x['relevance_score'], reverse=True)

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
# query = "부산 축제"
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
    companionType: Optional[str] = ""  # 동반자 유형 (연인, 친구, 가족 등)
    rooms: Optional[int] = 1   # 객실 수 (선택사항, 기본값: 1개)
    travelStyle: Optional[str] = ""  # 여행 스타일

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
                "url": f"https://kr.trip.com/hotels/list?searchWord={encoded_destination}&checkin={check_in_formatted}&checkout={check_out_formatted}&adult={guests}&children=0&locale=ko-KR&curr=KRW",
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
            links["trip_dot_com"]["url"] = f"https://kr.trip.com/hotels/list?searchWord={encoded_destination}&hotelName={encoded_hotel_name}&checkin={check_in_formatted}&checkout={check_out_formatted}&adult={guests}&children=0&locale=ko-KR&curr=KRW"
            links["agoda"]["url"] = f"https://www.agoda.com/ko-kr/search?textToSearch={encoded_destination}&hotelName={encoded_hotel_name}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&children=0&locale=ko-kr&currency=KRW&travellerType=1"
            links["booking"]["url"] = f"https://www.booking.com/searchresults.html?ss={encoded_destination}&hotelName={encoded_hotel_name}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}"
        
        return links
    
    @staticmethod
    def create_trip_hotel_search_links(destination: str, check_in: str, check_out: str, guests: int, rooms: int) -> dict:
        """전체 여행에 대한 호텔 검색 링크를 생성하는 메서드"""
        # 주요 호텔 예약 사이트들의 검색 링크 생성
        search_links = {
            "trip_dot_com": {
                "name": "트립닷컴",
                "url": f"https://kr.trip.com/hotels/list?searchWord={urllib.parse.quote(destination)}&checkin={check_in}&checkout={check_out}&adult={guests}&children=0&crn={rooms}&locale=ko-KR&curr=KRW",
                "icon": "🏨",
                "description": "트립닷컴에서 호텔 검색하기"
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
        
        다음 형식으로 JSON 응답을 제공해주세요:
        {{
            "destination": "목적지명",
            "duration": "여행 기간",
            "itinerary": [
                {{
                    "day": 1,
                    "date": "{request.start_date}",
                    "morning": "오전 활동 (구체적인 관광지명 포함, 예: 해운대해수욕장, 자갈치시장, 여수해양공원 등)",
                    "afternoon": "오후 활동 (구체적인 관광지명 포함, 예: 광안리해수욕장, 돌산공원, 만장굴 등)",
                    "evening": "저녁 활동 (구체적인 장소명 포함, 예: 남포동, 센텀시티, 여수엑스포역 등)",
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
        3. 각 일차마다 오전, 오후, 저녁 활동을 구체적으로 작성해주세요. 특히 관광지명은 구체적으로 작성해주세요 (예: "해운대해수욕장", "자갈치시장", "여수해양공원", "돌산공원" 등).
        4. accommodation는 여행 기간에 맞게 적절한 수량을 추천해주세요.
        5. 각 활동은 구체적인 장소명을 포함하여 작성해주세요. 이는 호텔 검색과 대중교통 정보 제공을 위해 중요합니다.
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
                
                # 전체 여행에 대한 호텔 검색 링크를 생성합니다
                trip_hotel_search = hotel_service.create_trip_hotel_search_links(
                    request.destination,
                    request.start_date,
                    request.end_date,
                    request.guests,
                    request.rooms
                )
                trip_data["trip_hotel_search"] = trip_hotel_search
                
                # 대중교통 정보를 추가합니다
                transport_service = PublicTransportService()
                transport_info = transport_service.get_itinerary_transport_info(
                    request.destination, 
                    trip_data.get("itinerary", [])
                )
                if "error" not in transport_info:
                    trip_data["transport_info"] = transport_info
                
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
            
            # 전체 여행에 대한 호텔 검색 링크를 생성합니다
            trip_hotel_search = hotel_service.create_trip_hotel_search_links(
                request.destination,
                request.start_date,
                request.end_date,
                request.guests,
                request.rooms
            )
            
            # 대중교통 정보를 추가합니다
            transport_service = PublicTransportService()
            transport_info = transport_service.get_itinerary_transport_info(
                request.destination, 
                itinerary_list
            )
            
            # 여행 기간 계산
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            travel_days = (end_date - start_date).days
            
            # 1인당 예상 비용 계산 (간단한 추정)
            base_cost_per_day = 150000  # 1일 15만원 기준
            estimated_cost_per_person = base_cost_per_day * travel_days
            
            return TripPlan(
                destination=request.destination,
                duration=f"{request.start_date} ~ {request.end_date}",
                itinerary=itinerary_list,
                accommodation=accommodation_list,
                total_cost=f"1인당 약 {estimated_cost_per_person:,}원",
                tips=["여행 전 날씨 확인", "필수품 준비", "현지 교통 정보 파악"],
                transport_info=transport_info if "error" not in transport_info else None,
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