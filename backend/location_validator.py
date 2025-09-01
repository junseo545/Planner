"""
위치 검증 서비스
네이버 지도 API와 검색 API를 사용하여 추천된 장소의 실제 존재 여부를 확인합니다.
구글보다 국내 장소에 대해 훨씬 더 정확한 정보를 제공합니다.
"""

import logging
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass
from dotenv import load_dotenv  # .env 파일에서 환경변수를 로드하는 라이브러리
import requests
import re

logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class PlaceValidationResult:
    """장소 검증 결과를 담는 데이터 클래스"""
    is_valid: bool
    place_name: str
    formatted_address: Optional[str] = None
    place_id: Optional[str] = None
    rating: Optional[float] = None
    confidence_score: float = 0.0
    suggestion: Optional[str] = None

class LocationValidator:
    """네이버 API 기반 위치 검증 서비스 클래스"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        LocationValidator 초기화
        
        Args:
            client_id: 네이버 API 클라이언트 ID
            client_secret: 네이버 API 클라이언트 Secret
        """
        self.client_id = client_id or os.getenv('NAVER_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            logger.warning("네이버 API 키가 설정되지 않았습니다. 위치 검증이 비활성화됩니다.")
            self.headers = None
        else:
            self.headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret
            }
            logger.info("네이버 API 클라이언트 초기화 완료")
    
    def validate_place(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """
        네이버 API를 사용하여 단일 장소의 존재 여부를 검증합니다.
        
        Args:
            place_name: 검증할 장소명
            region: 지역 정보 (검색 정확도 향상을 위해)
            
        Returns:
            PlaceValidationResult: 검증 결과
        """
        if not self.headers:
            return PlaceValidationResult(
                is_valid=True,  # API가 없으면 기본적으로 유효하다고 가정
                place_name=place_name,
                confidence_score=0.5,
                suggestion="네이버 API 키가 설정되지 않아 위치 검증을 수행할 수 없습니다."
            )
        
        try:
            # 1차: 네이버 지역 검색 API로 검증
            local_result = self._search_naver_local(place_name, region)
            if local_result.confidence_score > 0.7:
                return local_result
            
            # 2차: 네이버 통합 검색으로 보조 검증
            web_result = self._search_naver_web(place_name, region)
            
            # 두 결과 중 더 높은 신뢰도 사용
            if web_result.confidence_score > local_result.confidence_score:
                return web_result
            else:
                return local_result
            
        except Exception as e:
            logger.error(f"네이버 API 장소 검증 중 오류 발생: {e}")
            return PlaceValidationResult(
                is_valid=True,  # 오류 시 기본적으로 유효하다고 가정
                place_name=place_name,
                confidence_score=0.5,
                suggestion="검증 중 오류가 발생했습니다."
            )
    
    def _search_naver_local(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """네이버 지역 검색 API로 장소 검증"""
        try:
            # 검색 쿼리 구성
            query = f"{place_name}"
            if region:
                query = f"{region} {place_name}"
            
            url = "https://openapi.naver.com/v1/search/local.json"
            params = {
                "query": query,
                "display": 5,
                "start": 1,
                "sort": "random"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            if not items:
                return PlaceValidationResult(
                    is_valid=False,
                    place_name=place_name,
                    confidence_score=0.0,
                    suggestion=f"'{place_name}'을(를) 네이버 지도에서 찾을 수 없습니다."
                )
            
            # 가장 관련성 높은 결과 선택
            best_match = items[0]
            confidence_score = self._calculate_naver_local_confidence(place_name, best_match, region)
            
            return PlaceValidationResult(
                is_valid=confidence_score > 0.6,
                place_name=place_name,
                formatted_address=best_match.get('roadAddress') or best_match.get('address'),
                place_id=best_match.get('link'),
                confidence_score=confidence_score,
                suggestion=self._clean_html_tags(best_match.get('title', '')) if confidence_score < 0.8 else None
            )
            
        except Exception as e:
            logger.error(f"네이버 지역 검색 오류: {e}")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                suggestion="네이버 지역 검색 중 오류가 발생했습니다."
            )
    
    def _search_naver_web(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """네이버 통합 검색으로 장소 존재 여부 확인"""
        try:
            # 검색 쿼리 구성
            query = f"{place_name}"
            if region:
                query = f"{region} {place_name}"
            query += " 관광지 맛집 명소"  # 여행 관련 키워드 추가
            
            url = "https://openapi.naver.com/v1/search/webkr.json"
            params = {
                "query": query,
                "display": 10,
                "start": 1
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            if not items:
                return PlaceValidationResult(
                    is_valid=False,
                    place_name=place_name,
                    confidence_score=0.0,
                    suggestion=f"'{place_name}'에 대한 웹 정보를 찾을 수 없습니다."
                )
            
            # 여러 검색 결과에서 신뢰도 계산
            confidence_score = self._calculate_naver_web_confidence(place_name, items, region)
            
            return PlaceValidationResult(
                is_valid=confidence_score > 0.5,
                place_name=place_name,
                confidence_score=confidence_score,
                suggestion=None if confidence_score > 0.6 else f"'{place_name}'의 정확한 정보를 확인하기 어렵습니다."
            )
            
        except Exception as e:
            logger.error(f"네이버 웹 검색 오류: {e}")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                suggestion="네이버 웹 검색 중 오류가 발생했습니다."
            )
    
    def validate_itinerary(self, itinerary: List[Dict], destination: str) -> Dict:
        """
        전체 여행 일정의 장소들을 검증합니다.
        
        Args:
            itinerary: 여행 일정 리스트
            destination: 목적지
            
        Returns:
            Dict: 검증 결과 및 개선 제안
        """
        validation_results = []
        invalid_places = []
        suggestions = []
        
        for day_info in itinerary:
            day_num = day_info.get('day', 0)
            activities = day_info.get('activities', [])
            
            for activity in activities:
                place_name = activity.get('location', '')
                if not place_name:
                    continue
                
                # 장소 검증
                result = self.validate_place(place_name, destination)
                validation_results.append({
                    'day': day_num,
                    'activity': activity.get('title', ''),
                    'location': place_name,
                    'validation_result': result
                })
                
                if not result.is_valid:
                    invalid_places.append({
                        'day': day_num,
                        'location': place_name,
                        'activity': activity.get('title', ''),
                        'suggestion': result.suggestion
                    })
                
                if result.suggestion and result.confidence_score < 0.8:
                    suggestions.append({
                        'original': place_name,
                        'suggested': result.suggestion,
                        'day': day_num
                    })
        
        return {
            'total_places_checked': len(validation_results),
            'invalid_places_count': len(invalid_places),
            'invalid_places': invalid_places,
            'suggestions': suggestions,
            'validation_results': validation_results,
            'overall_accuracy': (len(validation_results) - len(invalid_places)) / len(validation_results) if validation_results else 1.0
        }
    
    def _calculate_naver_local_confidence(self, search_term: str, local_result: Dict, region: str = "") -> float:
        """
        네이버 지역 검색 결과의 신뢰도 점수를 계산합니다.
        
        Args:
            search_term: 원래 검색어
            local_result: 네이버 지역 검색 API 결과
            region: 지역 정보
            
        Returns:
            float: 0.0~1.0 사이의 신뢰도 점수
        """
        score = 0.0
        title = self._clean_html_tags(local_result.get('title', '')).lower()
        search_lower = search_term.lower()
        
        # 이름 일치도 (50% - 가장 중요)
        if search_lower in title or title in search_lower:
            score += 0.5
        elif self._is_similar_name(search_lower, title):
            score += 0.3
        
        # 주소에 지역명 포함 여부 (20%)
        address = (local_result.get('roadAddress', '') + ' ' + local_result.get('address', '')).lower()
        if region.lower() in address:
            score += 0.2
        
        # 카테고리 정보 여부 (15%)
        category = local_result.get('category', '').lower()
        if any(keyword in category for keyword in ['관광', '음식점', '카페', '숙박', '문화', '쇼핑']):
            score += 0.15
        
        # 전화번호 여부 (10% - 실제 사업체일 가능성)
        if local_result.get('telephone'):
            score += 0.1
        
        # 링크 정보 여부 (5%)
        if local_result.get('link'):
            score += 0.05
        
        return min(score, 1.0)
    
    def _calculate_naver_web_confidence(self, search_term: str, web_results: List[Dict], region: str = "") -> float:
        """
        네이버 웹 검색 결과의 신뢰도 점수를 계산합니다.
        
        Args:
            search_term: 원래 검색어
            web_results: 네이버 웹 검색 API 결과들
            region: 지역 정보
            
        Returns:
            float: 0.0~1.0 사이의 신뢰도 점수
        """
        if not web_results:
            return 0.0
        
        total_score = 0.0
        search_lower = search_term.lower()
        region_lower = region.lower()
        
        # 상위 5개 결과만 분석
        for result in web_results[:5]:
            result_score = 0.0
            
            title = self._clean_html_tags(result.get('title', '')).lower()
            description = self._clean_html_tags(result.get('description', '')).lower()
            
            # 제목에 검색어 포함 (30%)
            if search_lower in title:
                result_score += 0.3
            elif self._is_similar_name(search_lower, title):
                result_score += 0.15
            
            # 설명에 검색어 포함 (20%)
            if search_lower in description:
                result_score += 0.2
            
            # 지역명 포함 (20%)
            if region_lower in title or region_lower in description:
                result_score += 0.2
            
            # 여행 관련 키워드 포함 (15%)
            travel_keywords = ['관광', '여행', '맛집', '명소', '볼거리', '추천', '체험', '축제']
            if any(keyword in title or keyword in description for keyword in travel_keywords):
                result_score += 0.15
            
            # 신뢰할 만한 도메인 (15%)
            link = result.get('link', '').lower()
            trusted_domains = ['naver.com', 'daum.net', 'visitkorea.or.kr', 'seoul.go.kr', 'busan.go.kr']
            if any(domain in link for domain in trusted_domains):
                result_score += 0.15
            
            total_score += result_score
        
        # 평균 점수 계산하고 결과 개수로 가중치 적용
        avg_score = total_score / len(web_results[:5])
        result_count_bonus = min(len(web_results) / 10.0, 0.2)  # 최대 20% 보너스
        
        return min(avg_score + result_count_bonus, 1.0)
    
    def _clean_html_tags(self, text: str) -> str:
        """HTML 태그 제거"""
        if not text:
            return ""
        # <b>, </b> 등의 HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', text)
        return clean_text.strip()
    
    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """두 이름이 유사한지 확인합니다."""
        # 간단한 유사도 검사 (실제로는 더 정교한 알고리즘 사용 가능)
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1 & words2
        union = words1 | words2
        
        # Jaccard 유사도 계산
        jaccard_similarity = len(intersection) / len(union)
        return jaccard_similarity > 0.3

# 전역 인스턴스
location_validator = LocationValidator()

def validate_trip_locations(itinerary: List[Dict], destination: str) -> Dict:
    """
    여행 일정의 모든 장소를 검증하는 헬퍼 함수
    
    Args:
        itinerary: 여행 일정
        destination: 목적지
        
    Returns:
        Dict: 검증 결과
    """
    return location_validator.validate_itinerary(itinerary, destination)

def validate_single_location(place_name: str, region: str = "") -> PlaceValidationResult:
    """
    단일 장소를 검증하는 헬퍼 함수
    
    Args:
        place_name: 장소명
        region: 지역
        
    Returns:
        PlaceValidationResult: 검증 결과
    """
    return location_validator.validate_place(place_name, region)
