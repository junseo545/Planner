import os
import requests
import json
from typing import Optional, Dict, Any, List
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class KakaoPlaceService:
    """카카오 로컬 API를 사용한 실제 장소 정보 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv('KAKAO_API_KEY')
        self.search_url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
        self.category_url = 'https://dapi.kakao.com/v2/local/search/category.json'
        
        if not self.api_key:
            logger.warning("카카오 로컬 API 키가 설정되지 않았습니다.")
    
    def search_places(self, query: str, region: str = "", display: int = 3) -> List[Dict[str, Any]]:
        """특정 지역에서 장소를 검색"""
        if not self.api_key:
            logger.warning("카카오 API 키가 없어 장소 검색을 수행할 수 없습니다.")
            return []
        
        try:
            # 지역과 쿼리를 조합
            search_query = f"{region} {query}" if region else query
            
            headers = {
                'Authorization': f'KakaoAK {self.api_key}'
            }
            
            params = {
                'query': search_query,
                'size': display,
                'page': 1,
                'sort': 'accuracy'  # 정확도순 정렬
            }
            
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            places = []
            
            for item in data.get('documents', []):
                place_info = {
                    'name': item.get('place_name', ''),
                    'address': item.get('address_name', ''),
                    'road_address': item.get('road_address_name', ''),
                    'category': item.get('category_name', ''),
                    'telephone': item.get('phone', ''),
                    'place_url': item.get('place_url', ''),
                    'x': item.get('x', ''),  # 경도
                    'y': item.get('y', ''),  # 위도
                    'id': item.get('id', '')
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
            return places[0].get('road_address', '') or places[0].get('address', '')
        
        return None
    
    def enhance_activity_with_real_place(self, activity: Dict[str, Any], region: str = "") -> Dict[str, Any]:
        """활동 정보에 실제 장소 데이터 추가"""
        location = activity.get('location', '')
        title = activity.get('title', '')
        
        # 현재 지역 정보를 클래스 변수로 저장 (주소 검증에서 사용)
        self._current_region = region
        
        # 모호한 장소명 감지
        if self._is_vague_location(location) or self._is_vague_location(title):
            logger.warning(f"모호한 장소명 감지: title='{title}', location='{location}' - 구체적인 장소명이 필요합니다")
            # 모호한 장소명인 경우 검색하지 않고 원본 그대로 반환 (부정확한 정보 방지)
            return activity
        
        # 장소명에서 키워드 추출
        search_keywords = [
            location,
            title,
            # 제목에서 장소명 추출 시도
            self._extract_place_name_from_title(title)
        ]
        
        logger.info(f"장소 검색 시작: title='{title}', location='{location}', region='{region}'")
        
        for i, keyword in enumerate(search_keywords):
            if keyword and len(keyword.strip()) > 1:
                logger.info(f"검색 키워드 {i+1}: '{keyword}'")
                places = self.search_places(keyword, region, display=5)  # 더 많은 결과 가져오기
                
                if places:
                    logger.info(f"'{keyword}' 검색 결과 {len(places)}개:")
                    for j, place in enumerate(places):
                        logger.info(f"  {j+1}. {place['name']} - {place['category']} - {place['address']}")
                    
                    # 관련성이 높은 장소 찾기
                    best_place = self._find_most_relevant_place(keyword, places)
                    
                    if best_place:
                        # 원본 activity 복사
                        enhanced_activity = activity.copy()
                        
                        # 실제 장소 정보 추가
                        enhanced_activity.update({
                            'real_place_name': best_place['name'],
                            'real_address': best_place['road_address'] or best_place['address'],
                            'place_category': best_place['category'],
                            'place_telephone': best_place['telephone'],
                            'place_url': best_place['place_url'],
                            'latitude': best_place['y'],
                            'longitude': best_place['x']
                        })
                        
                        # 기존 location을 더 구체적으로 업데이트
                        if best_place['road_address'] or best_place['address']:
                            enhanced_activity['location'] = best_place['road_address'] or best_place['address']
                        
                        logger.info(f"실제 장소 정보 추가: {keyword} -> {best_place['name']} ({best_place['address']})")
                        return enhanced_activity
                else:
                    logger.warning(f"'{keyword}' 검색 결과 없음")
        
        # 실제 장소를 찾지 못한 경우 원본 그대로 반환 (잘못된 정보 추가 방지)
        logger.warning(f"신뢰할 만한 장소 정보를 찾지 못함: '{location}' - 부정확한 정보 추가를 방지하기 위해 원본 정보 유지")
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
    
    def _find_most_relevant_place(self, keyword: str, places: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """검색 결과에서 가장 관련성이 높은 장소 찾기 (매우 엄격한 기준)"""
        keyword_lower = keyword.lower().replace(' ', '')
        
        # 관련 없는 카테고리 필터링 (확장)
        irrelevant_categories = [
            '자동차정비', '수리', '썬팅', '광택', '주유소', '카센터', '타이어', 
            '세차', '정비', '부품', '렌터카', '중고차', '자동차용품',
            '부동산', '공인중개사', '아파트', '빌라', '원룸', '오피스텔',
            '의료', '병원', '의원', '치과', '한의원', '약국', '한방',
            '음식', '카페', '레스토랑', '식당', '술집', '호프', '치킨', '피자',
            '쇼핑', '마트', '편의점', '슈퍼', '패션', '의류', '화장품',
            '숙박', '모텔', '펜션', '게스트하우스', '호텔'
        ]
        
        logger.info(f"장소 필터링 시작: 키워드='{keyword}', 총 {len(places)}개 결과")
        
        relevant_places = []
        
        for i, place in enumerate(places):
            place_name = place['name'].lower().replace(' ', '')
            place_category = place['category'].lower()
            
            logger.info(f"  {i+1}. 검토: {place['name']} | 카테고리: {place['category']}")
            
            # 1. 관련 없는 카테고리 제외
            excluded = False
            for irrelevant in irrelevant_categories:
                if irrelevant in place_category:
                    logger.warning(f"     → 카테고리 제외: '{irrelevant}' 포함")
                    excluded = True
                    break
            
            if excluded:
                continue
            
            # 2. 정확한 장소명 검증 (매우 엄격)
            exact_match_score = self._calculate_exact_match_score(keyword_lower, place_name)
            
            if exact_match_score < 0.7:  # 70% 이상 일치해야 함
                logger.warning(f"     → 이름 일치도 미달: {exact_match_score:.2f} (최소 0.7 필요)")
                continue
            
            # 3. 관련성 점수 계산
            relevance_score = self._calculate_relevance_score(keyword_lower, place_name, place_category)
            
            if relevance_score > 0.7:  # 매우 엄격한 기준
                # 4. 주소 행정구역 정확성 검증 (지역 정보 사용)
                place_address = place.get('address', '')
                # enhance_activity_with_real_place 함수의 region 파라미터 사용
                target_region = getattr(self, '_current_region', '') or keyword
                if not self._validate_address_accuracy(place_address, target_region):
                    logger.warning(f"     → 주소 행정구역 오류: {place_address} (지역: {target_region})")
                    continue
                
                place['relevance_score'] = relevance_score
                place['exact_match_score'] = exact_match_score
                relevant_places.append(place)
                logger.info(f"     ✅ 통과: 관련성={relevance_score:.2f}, 정확도={exact_match_score:.2f}")
            else:
                logger.warning(f"     → 관련성 미달: {relevance_score:.2f} (최소 0.7 필요)")
        
        if relevant_places:
            # 정확도와 관련성 모두 고려하여 정렬
            relevant_places.sort(key=lambda x: (x['exact_match_score'], x['relevance_score']), reverse=True)
            best_place = relevant_places[0]
            logger.info(f"✅ 최종 선택: {best_place['name']} (정확도: {best_place['exact_match_score']:.2f}, 관련성: {best_place['relevance_score']:.2f})")
            return best_place
        
        logger.error(f"❌ 조건을 만족하는 장소를 찾지 못함: '{keyword}' - 검색 결과가 부정확합니다")
        return None
    
    def _calculate_relevance_score(self, keyword: str, place_name: str, place_category: str) -> float:
        """키워드와 장소의 관련성 점수 계산"""
        score = 0.0
        keyword_normalized = keyword.replace(' ', '').lower()
        place_normalized = place_name.replace(' ', '').lower()
        
        logger.debug(f"관련성 계산: '{keyword_normalized}' vs '{place_normalized}'")
        
        # 1. 정확한 이름 일치도 (가장 중요)
        if keyword_normalized in place_normalized:
            if keyword_normalized == place_normalized:
                score += 1.0  # 완전 일치
                logger.debug(f"완전 일치: +1.0")
            elif place_normalized.startswith(keyword_normalized):
                score += 0.9  # 시작 부분 일치
                logger.debug(f"시작 일치: +0.9")
            else:
                # 키워드가 장소명에 포함되는 비율 계산
                ratio = len(keyword_normalized) / len(place_normalized)
                if ratio > 0.5:  # 키워드가 장소명의 50% 이상을 차지
                    score += 0.7
                    logger.debug(f"주요 부분 일치 ({ratio:.2f}): +0.7")
                else:
                    score += 0.4  # 일반 부분 일치
                    logger.debug(f"부분 일치 ({ratio:.2f}): +0.4")
        
        # 2. 개별 단어 매칭 (더 엄격하게)
        keyword_words = [w for w in keyword.split() if len(w) >= 2]
        place_words = [w for w in place_name.split() if len(w) >= 2]
        
        matched_words = 0
        for kw in keyword_words:
            kw_norm = kw.lower()
            for pw in place_words:
                pw_norm = pw.lower()
                if kw_norm == pw_norm:  # 정확한 단어 일치만
                    matched_words += 1
                    score += 0.3
                    logger.debug(f"단어 일치 '{kw}': +0.3")
                    break
        
        # 3. 카테고리 관련성
        tourism_keywords = ['관광', '명소', '문화', '체험', '공원', '박물관', '미술관', '케이블카', '전망대', '해상']
        if any(word in place_category for word in tourism_keywords):
            score += 0.2
            logger.debug(f"관광 카테고리: +0.2")
        
        # 4. 페널티: 관련 없는 키워드가 있으면 점수 감점
        irrelevant_in_name = ['정비', '수리', '부동산', '병원', '의원']
        for irrelevant in irrelevant_in_name:
            if irrelevant in place_normalized:
                score -= 0.5
                logger.debug(f"관련없는 키워드 '{irrelevant}': -0.5")
        
        final_score = max(0.0, min(score, 1.0))  # 0.0 ~ 1.0 범위 제한
        logger.debug(f"최종 점수: {final_score:.2f}")
        return final_score
    
    def _calculate_exact_match_score(self, keyword: str, place_name: str) -> float:
        """정확한 이름 매칭 점수 계산 (오타, 누락 문자 등 검증)"""
        keyword_clean = keyword.replace(' ', '').lower()
        place_clean = place_name.replace(' ', '').lower()
        
        # 1. 완전 일치
        if keyword_clean == place_clean:
            return 1.0
        
        # 2. 키워드가 장소명에 완전히 포함
        if keyword_clean in place_clean:
            # 포함 비율 계산
            ratio = len(keyword_clean) / len(place_clean)
            if ratio >= 0.8:  # 80% 이상 일치
                return 0.95
            elif ratio >= 0.6:  # 60% 이상 일치  
                return 0.8
            else:
                return 0.6
        
        # 3. 개별 문자 레벤슈타인 거리 계산 (오타 검증)
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]
        
        distance = levenshtein_distance(keyword_clean, place_clean)
        max_len = max(len(keyword_clean), len(place_clean))
        
        if max_len == 0:
            return 0.0
        
        similarity = 1 - (distance / max_len)
        
        # 4. 핵심 단어 확인 (국립, 해양, 박물관 등)
        important_words = ['국립', '해양', '박물관', '미술관', '과학관', '문화관', '전시관']
        keyword_words = [w for w in keyword.split() if w in important_words]
        place_words = [w for w in place_name.split() if w in important_words]
        
        if keyword_words:
            # 중요한 단어가 모두 포함되어야 함
            missing_important = [w for w in keyword_words if w not in place_name]
            if missing_important:
                logger.warning(f"중요 단어 누락: {missing_important}")
                return 0.0  # 중요한 단어가 빠지면 0점
        
        return max(0.0, similarity)
    
    def _validate_address_accuracy(self, address: str, target_region: str) -> bool:
        """주소의 행정구역 정확성 검증"""
        if not address or not target_region:
            return True
        
        # 주요 도시별 행정구역 정보
        city_districts = {
            '여수': ['여수시'],  # 여수는 일반시로 구가 없음
            '순천': ['순천시'],  # 순천도 일반시
            '목포': ['목포시'],  # 목포도 일반시
            '부산': ['중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군'],
            '서울': ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구'],
            '대구': ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군'],
            '인천': ['중구', '동구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서구', '강화군', '옹진군'],
            '광주': ['동구', '서구', '남구', '북구', '광산구'],
            '대전': ['동구', '중구', '서구', '유성구', '대덕구'],
            '울산': ['중구', '남구', '동구', '북구', '울주군']
        }
        
        # 목표 지역의 유효한 구/군 목록 가져오기
        target_city = target_region.replace('시', '').replace('도', '')
        valid_districts = city_districts.get(target_city, [])
        
        if not valid_districts:
            return True  # 목록에 없는 지역은 검증 통과
        
        # 주소에서 구/군 추출
        address_parts = address.split()
        found_invalid = False
        
        for part in address_parts:
            if '구' in part or '군' in part:
                district = part.replace(' ', '')
                # 유효한 구/군 목록에 있는지 확인
                if district not in valid_districts:
                    logger.error(f"❌ 잘못된 행정구역: '{target_city}'에는 '{district}'가 존재하지 않음")
                    found_invalid = True
                    break
                else:
                    logger.info(f"✅ 올바른 행정구역: '{district}' ('{target_city}'에 존재)")
        
        return not found_invalid
    
    def _is_vague_location(self, location_text: str) -> bool:
        """모호한 장소명인지 판단"""
        if not location_text:
            return True
        
        location_lower = location_text.lower().strip()
        
        # 모호한 표현들
        vague_patterns = [
            # 일반적인 모호한 표현
            '해변', '해수욕장', '폭포', '공원', '시장', '식당', '카페', '박물관', '미술관',
            '산', '강', '호수', '다리', '항구', '항', '역', '터미널', '광장', '거리',
            
            # 지역 + 일반명사 (구체적인 고유명사가 아닌 경우)
            '시내', '중심가', '번화가', '구시가지', '신시가지', '해변가', '강변', '산기슭',
            '동쪽', '서쪽', '남쪽', '북쪽', '근처', '주변', '일대', '지역',
            
            # 수식어가 포함된 모호한 표현
            '유명한', '현지', '전통', '인기', '대표적인', '최고의', '추천', '맛있는',
            '아름다운', '멋진', '좋은', '특별한', '독특한',
            
            # 범용적인 장소 표현
            '관광지', '명소', '볼거리', '체험장', '전시관', '문화센터', '휴게소'
        ]
        
        # 모호한 패턴이 포함되어 있으면서 구체적인 고유명사가 없는 경우
        has_vague_pattern = any(pattern in location_lower for pattern in vague_patterns)
        
        if has_vague_pattern:
            # 구체적인 고유명사가 포함되어 있는지 확인
            # 한글 고유명사 패턴 (3글자 이상의 한글 + 특정 접미사)
            specific_patterns = [
                r'[가-힣]{2,}해수욕장',  # 경포해수욕장, 해운대해수욕장
                r'[가-힣]{2,}해변',     # 경포해변, 광안리해변  
                r'[가-힣]{2,}폭포',     # 천지연폭포, 정방폭포
                r'[가-힣]{2,}공원',     # 남산공원, 올림픽공원
                r'[가-힣]{2,}시장',     # 동대문시장, 남대문시장
                r'[가-힣]{2,}박물관',   # 국립중앙박물관
                r'[가-힣]{2,}미술관',   # 국립현대미술관
                r'[가-힣]{2,}사',       # 불국사, 해인사
                r'[가-힣]{2,}궁',       # 경복궁, 창덕궁
                r'[가-힣]{2,}성',       # 수원화성, 남한산성
                r'[가-힣]{2,}탑',       # 남산타워, 부산타워
                r'[가-힣]{2,}다리',     # 광안대교, 한강대교
                r'[가-힣]{2,}역',       # 서울역, 부산역
                r'[가-힣]{2,}항',       # 부산항, 인천항
            ]
            
            import re
            has_specific_pattern = any(re.search(pattern, location_text) for pattern in specific_patterns)
            
            if not has_specific_pattern:
                logger.warning(f"모호한 장소명 감지: '{location_text}' - 구체적인 고유명사가 필요합니다")
                return True
        
        return False
    
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
