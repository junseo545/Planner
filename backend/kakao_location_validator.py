"""
카카오 API 기반 위치 검증 서비스

카카오 로컬 API를 사용하여 추천된 장소의 실제 존재 여부를 확인합니다.
"""

import os
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class PlaceValidationResult:
    """장소 검증 결과를 담는 데이터 클래스"""
    is_valid: bool
    place_name: str
    confidence_score: float
    found_address: Optional[str] = None
    found_category: Optional[str] = None
    found_phone: Optional[str] = None
    validation_method: Optional[str] = None
    suggestion: Optional[str] = None

class KakaoLocationValidator:
    """카카오 API 기반 위치 검증 서비스 클래스"""
    
    def __init__(self, api_key: str = None):
        """
        카카오 위치 검증 서비스를 초기화합니다.
        
        Args:
            api_key: 카카오 API 키
        """
        self.api_key = api_key or os.getenv('KAKAO_API_KEY')
        
        if not self.api_key:
            logger.warning("카카오 API 키가 설정되지 않았습니다. 위치 검증이 비활성화됩니다.")
        
        self.headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        } if self.api_key else {}
        
        if self.api_key:
            logger.info("카카오 API 클라이언트 초기화 완료")
    
    def validate_place(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """
        카카오 API를 사용하여 단일 장소의 존재 여부를 검증합니다.
        
        Args:
            place_name: 검증할 장소명
            region: 지역명 (선택사항)
            
        Returns:
            PlaceValidationResult: 검증 결과
        """
        logger.info(f"장소 검증 시작: '{place_name}' (지역: {region})")
        
        # API 키가 없으면 기본 검증 결과 반환
        if not self.api_key:
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                validation_method="no_api_key",
                suggestion="카카오 API 키가 설정되지 않아 위치 검증을 수행할 수 없습니다."
            )
        
        try:
            # 1차: 카카오 로컬 검색 API로 검증
            local_result = self._search_kakao_local(place_name, region)
            
            if local_result.is_valid and local_result.confidence_score >= 0.7:
                return local_result
            
            # 2차: 키워드 검색으로 보조 검증
            keyword_result = self._search_kakao_keyword(place_name, region)
            
            # 더 높은 신뢰도 결과 반환
            if keyword_result.confidence_score > local_result.confidence_score:
                return keyword_result
            return local_result
            
        except Exception as e:
            logger.error(f"카카오 API 장소 검증 중 오류 발생: {e}")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                validation_method="api_error",
                suggestion="카카오 API 호출 중 오류가 발생했습니다."
            )
    
    def _search_kakao_local(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """카카오 로컬 검색 API로 장소 검증"""
        search_query = f"{region} {place_name}" if region else place_name
        
        try:
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            params = {
                "query": search_query,
                "size": 5,
                "page": 1,
                "sort": "accuracy"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('documents', [])
            
            if not documents:
                return PlaceValidationResult(
                    is_valid=False,
                    place_name=place_name,
                    confidence_score=0.0,
                    validation_method="kakao_local",
                    suggestion=f"'{place_name}'을(를) 카카오 로컬에서 찾을 수 없습니다."
                )
            
            # 가장 관련성 높은 결과 선택
            best_match = documents[0]
            confidence_score = self._calculate_kakao_local_confidence(place_name, best_match, region)
            
            return PlaceValidationResult(
                is_valid=confidence_score >= 0.6,
                place_name=place_name,
                confidence_score=confidence_score,
                found_address=best_match.get('road_address_name') or best_match.get('address_name'),
                found_category=best_match.get('category_name'),
                found_phone=best_match.get('phone'),
                validation_method="kakao_local",
                suggestion=f"카카오 로컬에서 '{best_match.get('place_name')}'을(를) 찾았습니다."
            )
            
        except requests.exceptions.Timeout:
            logger.error("카카오 로컬 검색 타임아웃")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                validation_method="timeout",
                suggestion="카카오 로컬 검색 중 타임아웃이 발생했습니다."
            )
        except Exception as e:
            logger.error(f"카카오 로컬 검색 오류: {e}")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                validation_method="error",
                suggestion="카카오 로컬 검색 중 오류가 발생했습니다."
            )
    
    def _search_kakao_keyword(self, place_name: str, region: str = "") -> PlaceValidationResult:
        """카카오 키워드 검색으로 장소 존재 여부 확인"""
        search_query = f"{region} {place_name} 관광지" if region else f"{place_name} 관광지"
        
        try:
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            params = {
                "query": search_query,
                "size": 10,
                "page": 1,
                "sort": "accuracy"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('documents', [])
            
            if not documents:
                return PlaceValidationResult(
                    is_valid=False,
                    place_name=place_name,
                    confidence_score=0.0,
                    validation_method="kakao_keyword"
                )
            
            confidence_score = self._calculate_kakao_keyword_confidence(place_name, documents, region)
            
            return PlaceValidationResult(
                is_valid=confidence_score >= 0.5,
                place_name=place_name,
                confidence_score=confidence_score,
                validation_method="kakao_keyword",
                suggestion=f"카카오 키워드 검색에서 관련 장소를 찾았습니다."
            )
            
        except Exception as e:
            logger.error(f"카카오 키워드 검색 오류: {e}")
            return PlaceValidationResult(
                is_valid=False,
                place_name=place_name,
                confidence_score=0.0,
                validation_method="error",
                suggestion="카카오 키워드 검색 중 오류가 발생했습니다."
            )
    
    def validate_multiple_places(self, places: List[str], region: str = "") -> Dict[str, PlaceValidationResult]:
        """
        여러 장소를 일괄 검증합니다.
        
        Args:
            places: 검증할 장소명 리스트
            region: 지역명 (선택사항)
            
        Returns:
            Dict[str, PlaceValidationResult]: 장소별 검증 결과
        """
        results = {}
        
        for place in places:
            if place and place.strip():
                results[place] = self.validate_place(place.strip(), region)
            
        return results
    
    def validate_itinerary(self, itinerary: List[Dict], destination: str = "") -> Dict:
        """
        전체 여행 일정의 장소들을 검증합니다.
        
        Args:
            itinerary: 여행 일정 데이터
            destination: 목적지
            
        Returns:
            Dict: 검증 결과 요약
        """
        all_places = []
        validation_summary = {
            'total_places': 0,
            'valid_places': 0,
            'invalid_places': 0,
            'validation_details': [],
            'suggestions': []
        }
        
        # 일정에서 모든 장소 추출
        for day in itinerary:
            if 'activities' in day:
                for activity in day['activities']:
                    location = activity.get('location', '').strip()
                    if location:
                        all_places.append({
                            'location': location,
                            'activity': activity,
                            'day': day.get('day', 0)
                        })
        
        validation_summary['total_places'] = len(all_places)
        
        # 각 장소 검증
        for place_info in all_places:
            location = place_info['location']
            result = self.validate_place(location, destination)
            
            validation_detail = {
                'location': location,
                'is_valid': result.is_valid,
                'confidence_score': result.confidence_score,
                'found_address': result.found_address,
                'validation_method': result.validation_method,
                'day': place_info['day'],
                'activity_title': place_info['activity'].get('title', ''),
                'suggestion': result.suggestion
            }
            
            validation_summary['validation_details'].append(validation_detail)
            
            if result.is_valid:
                validation_summary['valid_places'] += 1
            else:
                validation_summary['invalid_places'] += 1
                if result.suggestion:
                    validation_summary['suggestions'].append({
                        'location': location,
                        'suggestion': result.suggestion
                    })
        
        logger.info(f"일정 검증 완료: 총 {validation_summary['total_places']}개 장소 중 "
                   f"{validation_summary['valid_places']}개 유효, "
                   f"{validation_summary['invalid_places']}개 무효")
        
        return validation_summary
    
    def _calculate_kakao_local_confidence(self, search_term: str, local_result: Dict, region: str = "") -> float:
        """
        카카오 로컬 검색 결과의 신뢰도 점수를 계산합니다.
        
        Args:
            search_term: 검색어
            local_result: 카카오 로컬 검색 API 결과
            region: 지역명
            
        Returns:
            float: 신뢰도 점수 (0.0 ~ 1.0)
        """
        score = 0.0
        place_name = local_result.get('place_name', '').lower()
        search_lower = search_term.lower()
        
        # 1. 이름 유사도 (가중치 60%)
        if search_lower in place_name:
            if search_lower == place_name:
                score += 0.6  # 완전 일치
            else:
                # 부분 일치 점수
                ratio = len(search_lower) / len(place_name)
                score += 0.6 * ratio
        
        # 2. 카테고리 관련성 (가중치 20%)
        category = local_result.get('category_name', '').lower()
        tourism_categories = ['관광', '명소', '문화', '체험', '공원', '박물관', '미술관', '해변', '산', '사찰']
        if any(cat in category for cat in tourism_categories):
            score += 0.2
        
        # 3. 지역 일치도 (가중치 20%)
        if region:
            address = local_result.get('address_name', '') + ' ' + local_result.get('road_address_name', '')
            if region.lower() in address.lower():
                score += 0.2
        else:
            score += 0.1  # 지역 정보가 없으면 절반 점수
        
        return min(score, 1.0)
    
    def _calculate_kakao_keyword_confidence(self, search_term: str, keyword_results: List[Dict], region: str = "") -> float:
        """
        카카오 키워드 검색 결과의 신뢰도 점수를 계산합니다.
        
        Args:
            search_term: 검색어
            keyword_results: 카카오 키워드 검색 API 결과들
            region: 지역명
            
        Returns:
            float: 신뢰도 점수 (0.0 ~ 1.0)
        """
        if not keyword_results:
            return 0.0
        
        max_score = 0.0
        search_lower = search_term.lower()
        
        for result in keyword_results:
            score = 0.0
            place_name = result.get('place_name', '').lower()
            category = result.get('category_name', '').lower()
            address = result.get('address_name', '') + ' ' + result.get('road_address_name', '')
            
            # 1. 이름 포함 여부
            if search_lower in place_name:
                score += 0.5
            
            # 2. 관광지 카테고리 여부
            tourism_categories = ['관광', '명소', '문화', '체험']
            if any(cat in category for cat in tourism_categories):
                score += 0.3
            
            # 3. 지역 일치도
            if region and region.lower() in address.lower():
                score += 0.2
            
            max_score = max(max_score, score)
        
        return min(max_score, 1.0)
    
    def suggest_alternatives(self, invalid_place: str, region: str = "") -> List[str]:
        """
        무효한 장소에 대한 대안을 제안합니다.
        
        Args:
            invalid_place: 무효한 장소명
            region: 지역명
            
        Returns:
            List[str]: 대안 장소 목록
        """
        if not self.api_key:
            return [f"{region} 지역의 대표 관광지를 검색해보세요."]
        
        try:
            # 지역 + 관광지로 검색
            search_query = f"{region} 관광지" if region else "관광지"
            
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            params = {
                "query": search_query,
                "size": 5,
                "page": 1,
                "sort": "accuracy"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('documents', [])
            
            alternatives = []
            for doc in documents:
                place_name = doc.get('place_name', '')
                category = doc.get('category_name', '')
                if place_name and '관광' in category:
                    alternatives.append(f"{place_name} ({category})")
            
            return alternatives[:3] if alternatives else [f"{region} 지역의 관광지를 직접 검색해보세요."]
            
        except Exception as e:
            logger.error(f"대안 제안 중 오류: {e}")
            return [f"{region} 지역의 대표 관광지를 검색해보세요."]
