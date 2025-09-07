import os
import requests
import json
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class KakaoGeocodingService:
    """카카오 지오코딩 API를 사용한 위치 검증 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv('KAKAO_API_KEY')
        self.base_url = 'https://dapi.kakao.com/v2/local/search/address.json'
        self.coord2address_url = 'https://dapi.kakao.com/v2/local/geo/coord2address.json'
        
        if not self.api_key:
            logger.warning("카카오 지오코딩 API 키가 설정되지 않았습니다. 위치 검증 기능이 제한됩니다.")
    
    def get_location_info(self, address: str) -> Optional[Dict[str, Any]]:
        """주소를 입력받아 위도, 경도 및 행정구역 정보를 반환"""
        if not self.api_key:
            logger.warning("카카오 API 키가 없어 지오코딩을 수행할 수 없습니다.")
            return None
            
        try:
            headers = {
                'Authorization': f'KakaoAK {self.api_key}'
            }
            
            params = {
                'query': address
            }
            
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('documents'):
                address_info = data['documents'][0]
                
                return {
                    'latitude': float(address_info['y']),
                    'longitude': float(address_info['x']),
                    'address': address_info.get('address_name', ''),
                    'road_address': address_info.get('road_address_name', ''),
                    'sido': address_info.get('address', {}).get('region_1depth_name', ''),
                    'sigungu': address_info.get('address', {}).get('region_2depth_name', ''),
                    'raw_response': address_info
                }
            else:
                logger.warning(f"지오코딩 실패: {address}")
                return None
                
        except Exception as e:
            logger.error(f"지오코딩 API 오류: {e}")
            return None
    
    def is_location_in_region(self, location: str, target_region: str) -> Tuple[bool, Optional[str]]:
        """특정 장소가 목표 지역에 있는지 검증"""
        # API 키가 없으면 기본적인 텍스트 매칭으로 검증
        if not self.api_key:
            return self._fallback_text_matching(location, target_region)
        
        location_info = self.get_location_info(location)
        
        if not location_info:
            # 지오코딩 실패 시 텍스트 매칭으로 폴백
            return self._fallback_text_matching(location, target_region)
        
        # 지역명 정규화 (띄어쓰기 제거, 소문자 변환)
        def normalize_region(region: str) -> str:
            return region.replace(' ', '').lower()
        
        target_normalized = normalize_region(target_region)
        sido = normalize_region(location_info.get('sido', ''))
        sigungu = normalize_region(location_info.get('sigungu', ''))
        
        # 다양한 방식으로 지역 매칭 시도
        match_cases = [
            # 시도 매칭 (예: 부산 -> 부산광역시)
            target_normalized in sido or sido in target_normalized,
            # 시군구 매칭 (예: 해운대 -> 해운대구)
            target_normalized in sigungu or sigungu in target_normalized,
            # 전체 주소에서 매칭
            target_normalized in normalize_region(location_info.get('address', ''))
        ]
        
        is_match = any(match_cases)
        
        region_info = f"{location_info.get('sido', '')} {location_info.get('sigungu', '')}".strip()
        
        if is_match:
            return True, f"✅ {location}은(는) {region_info}에 위치합니다."
        else:
            return False, f"❌ {location}은(는) {region_info}에 위치하여 {target_region}과 다릅니다."
    
    def validate_activity_locations(self, activities: list, target_region: str) -> Dict[str, Any]:
        """여행 활동 목록의 장소들이 목표 지역에 있는지 검증"""
        validation_results = {
            'valid_activities': [],
            'invalid_activities': [],
            'validation_details': []
        }
        
        for activity in activities:
            location = activity.get('location', '')
            
            if not location:
                continue
                
            is_valid, message = self.is_location_in_region(location, target_region)
            
            validation_detail = {
                'activity': activity,
                'location': location,
                'is_valid': is_valid,
                'message': message
            }
            
            validation_results['validation_details'].append(validation_detail)
            
            if is_valid:
                validation_results['valid_activities'].append(activity)
            else:
                validation_results['invalid_activities'].append(activity)
                logger.warning(f"지역 불일치: {message}")
        
        return validation_results
    
    def suggest_alternative_location(self, invalid_location: str, target_region: str) -> Optional[str]:
        """유효하지 않은 장소에 대한 대안 제안"""
        # 목표 지역의 대표적인 관광지들을 제안
        region_attractions = {
            '부산': ['해운대해수욕장', '광안리해수욕장', '태종대', '감천문화마을', '범어사', '자갈치시장', '국제시장', '부산타워'],
            '서울': ['경복궁', '명동', '강남', '홍대', '이태원', '남산타워', '동대문', '광화문'],
            '제주': ['성산일출봉', '한라산', '제주올레길', '우도', '천지연폭포', '용머리해안', '만장굴'],
            '경주': ['불국사', '석굴암', '천마총', '첨성대', '안압지', '양동마을'],
            '강릉': ['경포해변', '안목해변', '오죽헌', '선교장', '정동진'],
        }
        
        # 목표 지역에서 키워드 추출
        for region, attractions in region_attractions.items():
            if region in target_region or target_region in region:
                return f"{region} 지역의 추천 관광지: {', '.join(attractions[:3])}"
        
        return f"{target_region} 지역의 대표 관광지를 추천합니다."
    
    def _fallback_text_matching(self, location: str, target_region: str) -> Tuple[bool, str]:
        """API 키가 없거나 지오코딩 실패 시 텍스트 기반 매칭"""
        # 지역명 정규화
        def normalize_text(text: str) -> str:
            return text.replace(' ', '').replace('광역시', '').replace('특별시', '').replace('도', '').lower()
        
        location_normalized = normalize_text(location)
        target_normalized = normalize_text(target_region)
        
        # 기본적인 텍스트 매칭
        if target_normalized in location_normalized:
            return True, f"✅ {location}에서 '{target_region}' 키워드를 발견했습니다."
        
        # 주요 지역별 키워드 매칭
        region_keywords = {
            '부산': ['해운대', '광안리', '태종대', '감천', '범어사', '자갈치', '국제시장', '송정', '기장'],
            '서울': ['강남', '명동', '홍대', '이태원', '종로', '마포', '용산', '송파', '강서'],
            '제주': ['성산', '한라산', '우도', '천지연', '용머리', '만장굴', '협재', '서귀포'],
            '경주': ['불국사', '석굴암', '천마총', '첨성대', '안압지', '양동'],
            '강릉': ['경포', '안목', '정동진', '오죽헌', '선교장'],
            '속초': ['설악산', '속초해변', '청초호', '외옹치'],
            '전주': ['한옥마을', '전동성당', '경기전', '오목대'],
            '여수': ['오동도', '진남관', '돌산대교', '향일암'],
            '대구': ['팔공산', '서문시장', '김광석길', '동성로'],
            '인천': ['차이나타운', '월미도', '송도', '강화도'],
        }
        
        # 지역 키워드로 매칭
        for region, keywords in region_keywords.items():
            if normalize_text(region) == target_normalized:
                for keyword in keywords:
                    if normalize_text(keyword) in location_normalized:
                        return True, f"✅ {location}은(는) {region} 지역의 대표 관광지입니다."
        
        # 매칭되지 않으면 보수적으로 유효하다고 판단 (빈 일정 방지)
        return True, f"⚠️ {location}의 지역을 정확히 확인할 수 없어 포함합니다. (API 키 필요)"
