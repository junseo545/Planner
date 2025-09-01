#!/usr/bin/env python3
"""
네이버 지오코딩 API 테스트 스크립트
사용법: python test_geocoding.py
"""

import os
from dotenv import load_dotenv
from naver_geocoding import NaverGeocodingService

# 환경 변수 로드
load_dotenv()

def test_location_validation():
    """위치 검증 기능 테스트"""
    print("=== 네이버 지오코딩 API 테스트 ===\n")
    
    # 서비스 초기화
    geocoding_service = NaverGeocodingService()
    
    # API 키 확인
    if not geocoding_service.client_id or not geocoding_service.client_secret:
        print("❌ 네이버 API 키가 설정되지 않았습니다.")
        print("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경 변수를 설정해주세요.")
        return
    
    print("✅ 네이버 API 키가 설정되었습니다.\n")
    
    # 테스트 케이스들
    test_cases = [
        # (장소명, 목표지역, 예상결과)
        ("해운대해수욕장", "부산", True),
        ("광안리해수욕장", "부산", True),
        ("경복궁", "부산", False),
        ("강릉해변", "부산", False),
        ("태종대", "부산", True),
        ("명동", "서울", True),
        ("제주도 성산일출봉", "제주", True),
        ("부산역", "부산", True),
    ]
    
    print("📍 위치 검증 테스트 시작...\n")
    
    for location, target_region, expected in test_cases:
        print(f"테스트: '{location}' -> '{target_region}' 지역")
        
        # 위치 정보 가져오기
        location_info = geocoding_service.get_location_info(location)
        
        if location_info:
            print(f"  📍 위도: {location_info['latitude']}")
            print(f"  📍 경도: {location_info['longitude']}")
            print(f"  📍 주소: {location_info['address']}")
            print(f"  📍 시도: {location_info['sido']}")
            print(f"  📍 시군구: {location_info['sigungu']}")
            
            # 지역 검증
            is_valid, message = geocoding_service.is_location_in_region(location, target_region)
            print(f"  🔍 검증 결과: {message}")
            
            # 예상 결과와 비교
            if is_valid == expected:
                print("  ✅ 테스트 성공!")
            else:
                print(f"  ❌ 테스트 실패! 예상: {expected}, 실제: {is_valid}")
        else:
            print("  ❌ 위치 정보를 찾을 수 없습니다.")
        
        print("-" * 50)
    
    # 활동 목록 검증 테스트
    print("\n🎯 활동 목록 검증 테스트...\n")
    
    test_activities = [
        {"title": "해운대 해수욕장 방문", "location": "해운대해수욕장", "description": "해변 산책"},
        {"title": "광안리 야경 감상", "location": "광안리해수욕장", "description": "야경 사진 촬영"},
        {"title": "경복궁 관람", "location": "경복궁", "description": "궁궐 투어"},  # 부산이 아님
        {"title": "태종대 관광", "location": "태종대", "description": "절경 감상"},
    ]
    
    validation_result = geocoding_service.validate_activity_locations(test_activities, "부산")
    
    print(f"전체 활동 수: {len(test_activities)}")
    print(f"유효한 활동 수: {len(validation_result['valid_activities'])}")
    print(f"무효한 활동 수: {len(validation_result['invalid_activities'])}")
    
    print("\n✅ 유효한 활동들:")
    for activity in validation_result['valid_activities']:
        print(f"  - {activity['title']} ({activity['location']})")
    
    print("\n❌ 무효한 활동들:")
    for activity in validation_result['invalid_activities']:
        print(f"  - {activity['title']} ({activity['location']})")
    
    print("\n📋 상세 검증 결과:")
    for detail in validation_result['validation_details']:
        status = "✅" if detail['is_valid'] else "❌"
        print(f"  {status} {detail['location']}: {detail['message']}")

if __name__ == "__main__":
    test_location_validation()
