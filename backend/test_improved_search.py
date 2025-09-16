#!/usr/bin/env python3
"""
개선된 카카오 API 검색 테스트
"""

import os
import sys
import requests
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_kakao_search():
    """카카오 API 검색 테스트"""
    
    # API 키 확인
    api_key = os.getenv('KAKAO_API_KEY')
    if not api_key:
        logger.error("KAKAO_API_KEY가 설정되지 않았습니다.")
        return False
    
    logger.info("✅ 카카오 API 키 확인됨")
    
    headers = {
        "Authorization": f"KakaoAK {api_key}"
    }
    
    base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "에버랜드 검색",
            "queries": ["에버랜드", "용인 에버랜드", "에버랜드 관광지"],
            "region": "용인"
        },
        {
            "name": "용인 자연휴양림 검색", 
            "queries": ["용인 자연휴양림", "자연휴양림", "용인 자연휴양림 관광지"],
            "region": "용인"
        },
        {
            "name": "경주 불국사 검색",
            "queries": ["경주 불국사", "불국사", "경주 불국사 관광지"],
            "region": "경주"
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"\n🔍 {test_case['name']} 테스트")
        
        for query in test_case['queries']:
            try:
                params = {
                    "query": query,
                    "size": 5,
                    "sort": "accuracy"
                }
                
                response = requests.get(base_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                documents = data.get('documents', [])
                
                if documents:
                    logger.info(f"  ✅ '{query}' 검색 성공: {len(documents)}개 결과")
                    for i, doc in enumerate(documents[:3]):  # 상위 3개만 표시
                        place_name = doc.get('place_name', '')
                        address = doc.get('road_address_name') or doc.get('address_name', '')
                        category = doc.get('category_name', '')
                        logger.info(f"    {i+1}. {place_name} - {address} ({category})")
                else:
                    logger.warning(f"  ❌ '{query}' 검색 결과 없음")
                    
            except Exception as e:
                logger.error(f"  ❌ '{query}' 검색 오류: {e}")
    
    return True

if __name__ == "__main__":
    test_kakao_search()
