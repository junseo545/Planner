"""
카카오 장소 검색 API 테스트 스크립트

이 스크립트는 카카오 로컬 API가 올바르게 작동하는지 테스트합니다.
"""

import os
import sys
from dotenv import load_dotenv
from kakao_place_service import KakaoPlaceService

def main():
    """카카오 장소 검색 API 테스트 실행"""
    print("=== 카카오 장소 검색 API 테스트 ===\n")
    
    # 환경변수 로드
    load_dotenv()
    
    # 카카오 장소 서비스 초기화
    place_service = KakaoPlaceService()
    
    # API 키 확인
    if not place_service.api_key:
        print("❌ 카카오 API 키가 설정되지 않았습니다.")
        print("KAKAO_API_KEY 환경 변수를 설정해주세요.")
        return
    
    print("✅ 카카오 API 키가 설정되었습니다.\n")
    
    # 장소 검색 테스트
    print("🔍 장소 검색 테스트")
    print("-" * 50)
    
    test_searches = [
        ("해운대해수욕장", "부산"),
        ("경복궁", "서울"),
        ("성산일출봉", "제주"),
        ("불국사", "경주"),
        ("경포해변", "강릉")
    ]
    
    for i, (query, region) in enumerate(test_searches, 1):
        print(f"{i}. 검색어: {query} (지역: {region})")
        
        try:
            results = place_service.search_places(query, region, display=3)
            
            if results:
                print(f"   ✅ {len(results)}개 결과 발견:")
                for j, place in enumerate(results, 1):
                    print(f"     {j}. {place['name']}")
                    print(f"        📍 주소: {place['address']}")
                    print(f"        📞 전화: {place['telephone'] or 'N/A'}")
                    print(f"        🏷️  카테고리: {place['category']}")
            else:
                print(f"   ❌ 검색 결과가 없습니다.")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
        
        print()
    
    # 상세 주소 조회 테스트
    print("📍 상세 주소 조회 테스트")
    print("-" * 50)
    
    test_places = ["해운대해수욕장", "경복궁", "성산일출봉"]
    
    for i, place_name in enumerate(test_places, 1):
        print(f"{i}. 장소명: {place_name}")
        
        try:
            address = place_service.get_detailed_address(place_name)
            
            if address:
                print(f"   ✅ 주소: {address}")
            else:
                print(f"   ❌ 주소를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
        
        print()
    
    # 활동 정보 보강 테스트
    print("🎯 활동 정보 보강 테스트")
    print("-" * 50)
    
    test_activity = {
        "title": "해운대해수욕장 방문",
        "location": "해운대해수욕장",
        "time": "10:00-12:00",
        "description": "부산의 대표 해수욕장에서 여유로운 시간 보내기"
    }
    
    print(f"원본 활동: {test_activity['title']}")
    print(f"원본 장소: {test_activity['location']}")
    
    try:
        enhanced_activity = place_service.enhance_activity_with_real_place(test_activity, "부산")
        
        if enhanced_activity.get('real_place_name'):
            print(f"✅ 보강 완료!")
            print(f"   🏢 실제 장소명: {enhanced_activity['real_place_name']}")
            print(f"   📍 실제 주소: {enhanced_activity['real_address']}")
            print(f"   🏷️  카테고리: {enhanced_activity['place_category']}")
            print(f"   📞 전화번호: {enhanced_activity['place_telephone'] or 'N/A'}")
        else:
            print(f"⚠️ 보강되지 않음 (원본 정보 유지)")
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
    
    print()
    
    # 추천 장소 검색 테스트
    print("🌟 추천 장소 검색 테스트")
    print("-" * 50)
    
    test_regions = ["부산", "서울", "제주"]
    
    for i, region in enumerate(test_regions, 1):
        print(f"{i}. 지역: {region}")
        
        try:
            recommendations = place_service.search_recommended_places(region, count=3)
            
            if recommendations:
                print(f"   ✅ {len(recommendations)}개 추천 장소:")
                for j, place in enumerate(recommendations, 1):
                    print(f"     {j}. {place['name']} ({place['category']})")
            else:
                print(f"   ❌ 추천 장소가 없습니다.")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")
        
        print()
    
    print("🎯 테스트 완료!")
    print("모든 기능이 정상적으로 작동하면 여행 플래너에서 카카오 장소 검색을 사용할 수 있습니다.")

if __name__ == "__main__":
    main()
