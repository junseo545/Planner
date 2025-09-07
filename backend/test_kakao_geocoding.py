"""
카카오 지오코딩 API 테스트 스크립트

이 스크립트는 카카오 지오코딩 API가 올바르게 작동하는지 테스트합니다.
"""

import os
import sys
from dotenv import load_dotenv
from kakao_geocoding import KakaoGeocodingService

def main():
    """카카오 지오코딩 API 테스트 실행"""
    print("=== 카카오 지오코딩 API 테스트 ===\n")
    
    # 환경변수 로드
    load_dotenv()
    
    # 카카오 지오코딩 서비스 초기화
    geocoding_service = KakaoGeocodingService()
    
    # API 키 확인
    if not geocoding_service.api_key:
        print("❌ 카카오 API 키가 설정되지 않았습니다.")
        print("KAKAO_API_KEY 환경 변수를 설정해주세요.")
        return
    
    print("✅ 카카오 API 키가 설정되었습니다.\n")
    
    # 테스트 주소 목록
    test_addresses = [
        "부산광역시 해운대구 해운대해변로 264",
        "서울특별시 종로구 세종대로 175",
        "제주특별자치도 제주시 첨단로 242",
        "경상북도 경주시 불국로 385",
        "강원도 강릉시 창해로 17"
    ]
    
    print("📍 주소 → 좌표 변환 테스트")
    print("-" * 50)
    
    for i, address in enumerate(test_addresses, 1):
        print(f"{i}. 테스트 주소: {address}")
        
        try:
            result = geocoding_service.get_location_info(address)
            
            if result:
                print(f"   ✅ 성공!")
                print(f"   📍 좌표: ({result['latitude']:.6f}, {result['longitude']:.6f})")
                print(f"   🏠 주소: {result.get('address', 'N/A')}")
                print(f"   🌏 시도: {result.get('sido', 'N/A')}")
                print(f"   🏘️  시군구: {result.get('sigungu', 'N/A')}")
            else:
                print(f"   ❌ 실패: 좌표를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
        
        print()
    
    # 지역 검증 테스트
    print("🔍 지역 검증 테스트")
    print("-" * 50)
    
    test_cases = [
        ("해운대해수욕장", "부산"),
        ("경복궁", "서울"),
        ("성산일출봉", "제주"),
        ("불국사", "경주"),
        ("경포해변", "강릉")
    ]
    
    for i, (location, region) in enumerate(test_cases, 1):
        print(f"{i}. 장소: {location}, 목표 지역: {region}")
        
        try:
            is_valid, message = geocoding_service.is_location_in_region(location, region)
            
            if is_valid:
                print(f"   ✅ {message}")
            else:
                print(f"   ❌ {message}")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
        
        print()
    
    print("🎯 테스트 완료!")
    print("모든 기능이 정상적으로 작동하면 여행 플래너에서 카카오 지오코딩을 사용할 수 있습니다.")

if __name__ == "__main__":
    main()
