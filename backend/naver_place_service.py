import os
import requests
import json
from typing import Optional, Dict, Any, List
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class NaverPlaceService:
    """네이버 검색 API와 지오코딩 API를 사용한 실제 장소 정보 서비스"""
    
    def __init__(self):
        self.search_client_id = os.getenv('NAVER_CLIENT_ID')
        self.search_client_secret = os.getenv('NAVER_CLIENT_SECRET')
        self.geo_client_id = os.getenv('NAVER_CLIENT_ID')  # 같은 키 사용
        self.geo_client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        self.search_url = 'https://openapi.naver.com/v1/search/local.json'
        self.geo_url = 'https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode'
        
        if not self.search_client_id or not self.search_client_secret:
            logger.warning("네이버 검색 API 키가 설정되지 않았습니다.")
    
    def search_places(self, query: str, region: str = "", display: int = 3) -> List[Dict[str, Any]]:
        """특정 지역에서 장소를 검색"""
        if not self.search_client_id or not self.search_client_secret:
            logger.warning("네이버 API 키가 없어 장소 검색을 수행할 수 없습니다.")
            return []
        
        try:
            # 지역과 쿼리를 조합
            search_query = f"{region} {query}" if region else query
            
            headers = {
                'X-Naver-Client-Id': self.search_client_id,
                'X-Naver-Client-Secret': self.search_client_secret
            }
            
            params = {
                'query': search_query,
                'display': display,
                'start': 1,
                'sort': 'random'  # 다양한 결과를 위해 랜덤 정렬
            }
            
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            places = []
            
            for item in data.get('items', []):
                place_info = {
                    'name': self._clean_html_tags(item.get('title', '')),
                    'address': item.get('roadAddress', '') or item.get('address', ''),
                    'category': item.get('category', ''),
                    'telephone': item.get('telephone', ''),
                    'description': item.get('description', ''),
                    'link': item.get('link', ''),
                    'mapx': item.get('mapx', ''),
                    'mapy': item.get('mapy', '')
                }
                places.append(place_info)
            
            logger.info(f"장소 검색 완료: '{search_query}' -> {len(places)}개 결과")
            return places
            
        except Exception as e:
            logger.error(f"장소 검색 오류: {e}")
            return []
    
    def get_detailed_address(self, place_name: str, region: str = "") -> Optional[str]:
        """장소명으로 상세 주소 조회"""
        places = self.search_places(place_name, region, display=1)
        
        if places:
            return places[0].get('address', '')
        
        return None
    
    def enhance_activity_with_real_place(self, activity: Dict[str, Any], region: str = "") -> Dict[str, Any]:
        """활동 정보에 실제 장소 데이터 추가"""
        location = activity.get('location', '')
        title = activity.get('title', '')
        
        # 장소명에서 키워드 추출
        search_keywords = [
            location,
            title,
            # 제목에서 장소명 추출 시도
            self._extract_place_name_from_title(title)
        ]
        
        for keyword in search_keywords:
            if keyword and len(keyword.strip()) > 1:
                places = self.search_places(keyword, region, display=1)
                
                if places:
                    place = places[0]
                    
                    # 원본 activity 복사
                    enhanced_activity = activity.copy()
                    
                    # 실제 장소 정보 추가
                    enhanced_activity.update({
                        'real_place_name': place['name'],
                        'real_address': place['address'],
                        'place_category': place['category'],
                        'place_telephone': place['telephone'],
                        'place_link': place['link']
                    })
                    
                    # 기존 location을 더 구체적으로 업데이트
                    if place['address']:
                        enhanced_activity['location'] = place['address']
                    
                    logger.info(f"실제 장소 정보 추가: {keyword} -> {place['name']} ({place['address']})")
                    return enhanced_activity
        
        # 실제 장소를 찾지 못한 경우 원본 반환
        logger.warning(f"실제 장소 정보를 찾지 못함: {location}")
        return activity
    
    def enhance_itinerary_with_real_places(self, itinerary: List[Dict], destination: str) -> List[Dict]:
        """전체 일정에 실제 장소 정보 추가"""
        enhanced_itinerary = []
        
        for day in itinerary:
            enhanced_day = day.copy()
            
            if day.get('activities'):
                enhanced_activities = []
                
                for activity in day['activities']:
                    enhanced_activity = self.enhance_activity_with_real_place(activity, destination)
                    enhanced_activities.append(enhanced_activity)
                
                enhanced_day['activities'] = enhanced_activities
            
            enhanced_itinerary.append(enhanced_day)
        
        return enhanced_itinerary
    
    def _clean_html_tags(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        return re.sub(r'<[^>]+>', '', text)
    
    def _extract_place_name_from_title(self, title: str) -> str:
        """제목에서 장소명 추출"""
        # 일반적인 패턴들을 제거하여 장소명만 추출
        title = title.replace('방문', '').replace('관람', '').replace('투어', '')
        title = title.replace('체험', '').replace('구경', '').replace('감상', '')
        title = title.strip()
        
        # 첫 번째 단어 추출 (보통 장소명)
        words = title.split()
        if words:
            return words[0]
        
        return title
    
    def search_recommended_places(self, region: str, category: str = "", count: int = 5) -> List[Dict[str, Any]]:
        """지역별 추천 장소 검색"""
        categories = [
            "관광지", "맛집", "카페", "박물관", "공원", "해변", "산", "사찰", "궁궐"
        ]
        
        if category:
            search_query = f"{region} {category}"
        else:
            # 카테고리가 없으면 일반적인 관광지 검색
            search_query = f"{region} 관광지"
        
        return self.search_places(search_query, display=count)
