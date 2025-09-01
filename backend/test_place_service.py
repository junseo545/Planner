#!/usr/bin/env python3
"""
네이버 장소 검색 API 테스트 스크립트
사용법: python test_place_service.py
"""

import os
from dotenv import load_dotenv
from naver_place_service import NaverPlaceService

# 환경 변수 로드
load_dotenv()

def test_place_search():
    """장소 검색 기능 테스트"""
    print("=== 네이버 장소 검색 API 테스트 ===\n")
    
    # 서비스 초기화
    place_service = NaverPlaceService()
    
    # API 키 확인
    if not place_service.search_client_id or not place_service.search_client_secret:
        print("❌ 네이버 검색 API 키가 설정되지 않았습니다.")
        print("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경 변수를 설정해주세요.")
        return
    
    print("✅ 네이버 검색 API 키가 설정되었습니다.\n")
    
    # 테스트 케이스들
    test_queries = [
        ("강릉", "가볼만한 곳"),
        ("부산", "해운대"),
        ("속초", "맛집"),
        ("서울", "경복궁"),
        ("제주", "성산일출봉"),
    ]
    
    print("🔍 장소 검색 테스트 시작...\n")
    
    for region, query in test_queries:
        print(f"검색: '{region} {query}'")
        
        places = place_service.search_places(query, region, display=3)
        
        if places:
            for i, place in enumerate(places, 1):
                print(f"  {i}. {place['name']}")
                print(f"     📍 주소: {place['address']}")
                if place['category']:
                    print(f"     🏷️ 카테고리: {place['category']}")
                if place['telephone']:
                    print(f"     📞 전화: {place['telephone']}")
                print()
        else:
            print("  ❌ 검색 결과가 없습니다.")
        
        print("-" * 60)
    
    # 활동 정보 향상 테스트
    print("\n🎯 활동 정보 향상 테스트...\n")
    
    test_activities = [
        {
            "title": "해운대 해수욕장 방문",
            "location": "해운대해수욕장",
            "description": "해변 산책 및 휴식",
            "time": "10:00",
            "duration": "2시간"
        },
        {
            "title": "경복궁 관람",
            "location": "경복궁",
            "description": "궁궐 투어",
            "time": "14:00",
            "duration": "1.5시간"
        },
        {
            "title": "속초 중앙시장 맛집",
            "location": "속초중앙시장",
            "description": "현지 음식 체험",
            "time": "12:00",
            "duration": "1시간"
        }
    ]
    
    regions = ["부산", "서울", "속초"]
    
    for i, activity in enumerate(test_activities):
        region = regions[i]
        print(f"활동 향상 테스트: {activity['title']} (지역: {region})")
        
        enhanced_activity = place_service.enhance_activity_with_real_place(activity, region)
        
        print(f"  원본 위치: {activity['location']}")
        print(f"  향상된 위치: {enhanced_activity['location']}")
        
        if enhanced_activity.get('real_place_name'):
            print(f"  실제 장소명: {enhanced_activity['real_place_name']}")
        if enhanced_activity.get('real_address'):
            print(f"  실제 주소: {enhanced_activity['real_address']}")
        if enhanced_activity.get('place_category'):
            print(f"  카테고리: {enhanced_activity['place_category']}")
        if enhanced_activity.get('place_telephone'):
            print(f"  전화번호: {enhanced_activity['place_telephone']}")
        
        print("-" * 50)
    
    # 전체 일정 향상 테스트
    print("\n📅 전체 일정 향상 테스트...\n")
    
    test_itinerary = [
        {
            "day": 1,
            "date": "2024-01-01",
            "activities": [
                {
                    "title": "해운대 해수욕장",
                    "location": "해운대",
                    "description": "해변 산책",
                    "time": "09:00"
                },
                {
                    "title": "광안리 해변",
                    "location": "광안리",
                    "description": "야경 감상",
                    "time": "19:00"
                }
            ]
        }
    ]
    
    enhanced_itinerary = place_service.enhance_itinerary_with_real_places(test_itinerary, "부산")
    
    for day in enhanced_itinerary:
        print(f"{day['day']}일차 ({day['date']}):")
        for activity in day['activities']:
            print(f"  - {activity['title']}")
            print(f"    위치: {activity['location']}")
            if activity.get('real_address'):
                print(f"    실제 주소: {activity['real_address']}")
        print()

if __name__ == "__main__":
    test_place_search()
