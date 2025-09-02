import React, { useEffect, useRef } from 'react';

interface Location {
  title: string;
  location: string;
  real_address?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
  time?: string;
}

interface TripMapProps {
  locations: Location[];
  destination: string;
}

declare global {
  interface Window {
    kakao: any;
  }
}

const TripMap: React.FC<TripMapProps> = ({ locations, destination }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  useEffect(() => {
    // 카카오맵 API 로딩 대기
    let attempts = 0;
    const maxAttempts = 100; // 10초 대기
    
    const checkKakaoMaps = () => {
      attempts++;
      console.log(`Checking Kakao Maps API... (${attempts}/${maxAttempts})`);
      console.log('window.kakao:', window.kakao);
      console.log('window.kakao?.maps:', window.kakao?.maps);
      
      if (window.kakao && window.kakao.maps) {
        try {
          // kakao.maps.load 없이 직접 초기화 시도
          if (typeof window.kakao.maps.Map === 'function') {
            console.log('Kakao Maps API is ready');
            setError(null);
            initializeMap();
          } else {
            // 아직 완전히 로드되지 않았다면 load 함수 사용
            window.kakao.maps.load(() => {
              console.log('Kakao Maps API loaded successfully');
              setError(null);
              initializeMap();
            });
          }
        } catch (loadError) {
          console.error('Error during kakao maps initialization:', loadError);
          setError('지도 초기화 중 오류가 발생했습니다.');
          setIsLoading(false);
        }
      } else if (attempts < maxAttempts) {
        setTimeout(checkKakaoMaps, 100);
      } else {
        console.error('Failed to load Kakao Maps API after maximum attempts');
        console.error('This is usually caused by:');
        console.error('1. Invalid API key');
        console.error('2. Domain not registered in Kakao Developers Console');
        console.error('3. Network connectivity issues');
        console.error('4. Script loading blocked by browser/firewall');
        
        setError('지도 API를 로드할 수 없습니다. 다음을 확인해주세요:\n1. 인터넷 연결 상태\n2. 브라우저 설정 (스크립트 차단 여부)\n3. 방화벽 설정');
        setIsLoading(false);
      }
    };

    // 스크립트가 이미 로드되었는지 확인
    const existingScript = document.querySelector('script[src*="dapi.kakao.com"]');
    if (existingScript) {
      console.log('Kakao Maps script found in document');
      // 이미 로드된 스크립트의 경우 바로 체크 시작
      checkKakaoMaps();
    } else {
      console.log('Kakao Maps script not found, loading dynamically...');
      
      // 동적으로 스크립트 로드
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=f6e207213c7c7754caa4f7931c760036&libraries=services';
      script.async = false; // 동기적으로 로드
      
      script.onload = () => {
        console.log('Kakao Maps script loaded dynamically');
        // 스크립트 로드 후 약간의 지연을 두고 체크 시작
        setTimeout(checkKakaoMaps, 300);
      };
      
      script.onerror = (error) => {
        console.error('Failed to load Kakao Maps script:', error);
        console.error('Possible causes:');
        console.error('- Network connectivity issues');
        console.error('- Firewall or ad blocker blocking the request');
        console.error('- Invalid API key or domain not registered');
        console.error('- CORS policy restrictions');
        
        setError('카카오맵 스크립트를 로드할 수 없습니다.\n\n가능한 원인:\n• 네트워크 연결 문제\n• 광고 차단기나 방화벽 설정\n• API 키 또는 도메인 등록 문제');
        setIsLoading(false);
      };
      
      document.head.appendChild(script);
    }
  }, [locations]);

  const initializeMap = async () => {
    console.log('Initializing map...');
    console.log('Current domain:', window.location.hostname);
    console.log('Current protocol:', window.location.protocol);
    console.log('Full URL:', window.location.href);
    
    if (!mapContainer.current) {
      console.error('Map container not found');
      return;
    }

    if (!window.kakao || !window.kakao.maps || !window.kakao.maps.services) {
      console.error('Kakao Maps API or services not available');
      console.error('Available kakao object:', window.kakao);
      return;
    }

    console.log('Locations to display:', locations);

    // 기본 중심점 설정 (서울)
    let centerLat = 37.5665;
    let centerLng = 126.9780;

    // 목적지에 따른 기본 좌표 설정
    const cityCoordinates: { [key: string]: [number, number] } = {
      '서울': [37.5665, 126.9780],
      '부산': [35.1796, 129.0756],
      '제주': [33.4996, 126.5312],
      '제주도': [33.4996, 126.5312],
      '대구': [35.8714, 128.6014],
      '인천': [37.4563, 126.7052],
      '광주': [35.1595, 126.8526],
      '대전': [36.3504, 127.3845],
      '울산': [35.5384, 129.3114],
      '경주': [35.8562, 129.2247],
      '전주': [35.8242, 127.1480],
      '여수': [34.7604, 127.6622],
      '강릉': [37.7519, 128.8761],
      '춘천': [37.8813, 127.7298],
      '포항': [36.0190, 129.3435],
      '안동': [36.5684, 128.7294],
    };

    // 목적지에서 도시명 추출
    const cityName = Object.keys(cityCoordinates).find(city => 
      destination.includes(city)
    );

    if (cityName) {
      [centerLat, centerLng] = cityCoordinates[cityName];
      console.log(`Found city: ${cityName}, coordinates: [${centerLat}, ${centerLng}]`);
    } else {
      console.log(`City not found in predefined list, using default coordinates for: ${destination}`);
    }

    try {
      const mapOption = {
        center: new window.kakao.maps.LatLng(centerLat, centerLng),
        level: 10  // 더 넓은 범위를 보여주기 위해 레벨 증가
      };

      const map = new window.kakao.maps.Map(mapContainer.current, mapOption);
      mapRef.current = map;
      console.log('Map created successfully');
      setIsLoading(false);

      // 지오코딩이 가능한지 확인
      if (window.kakao.maps.services && locations.length > 0) {
        // 지오코딩을 위한 geocoder 객체 생성
        const geocoder = new window.kakao.maps.services.Geocoder();
        const bounds = new window.kakao.maps.LatLngBounds();

        let validLocations = 0;
        let processedCount = 0;

        // 각 위치에 대해 지오코딩 수행
        locations.forEach((location, index) => {
          const address = location.real_address || location.location;
          console.log(`Processing location ${index + 1}: ${address}`);
          
          geocoder.addressSearch(address, (result: any[], status: string) => {
            processedCount++;
            console.log(`Geocoding result for "${address}":`, status, result);
            
            if (status === window.kakao.maps.services.Status.OK && result.length > 0) {
              const coords = new window.kakao.maps.LatLng(result[0].y, result[0].x);
              console.log(`Success! Coordinates: [${result[0].y}, ${result[0].x}]`);
              
              // 마커 생성
              const marker = new window.kakao.maps.Marker({
                map: map,
                position: coords
              });

              // 커스텀 오버레이 내용
              const content = `
                <div style="
                  background: white;
                  border: 2px solid #4F46E5;
                  border-radius: 8px;
                  padding: 8px 12px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                  min-width: 150px;
                  position: relative;
                ">
                  <div style="
                    background: #4F46E5;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 4px;
                    margin-bottom: 4px;
                    display: inline-block;
                  ">
                    ${index + 1}번째
                  </div>
                  <div style="
                    font-weight: bold;
                    color: #1F2937;
                    font-size: 14px;
                  ">
                    ${location.title}
                  </div>
                  <div style="
                    position: absolute;
                    bottom: -8px;
                    left: 20px;
                    width: 0;
                    height: 0;
                    border-left: 8px solid transparent;
                    border-right: 8px solid transparent;
                    border-top: 8px solid #4F46E5;
                  "></div>
                </div>
              `;

              // 커스텀 오버레이 생성
              const overlay = new window.kakao.maps.CustomOverlay({
                content: content,
                map: map,
                position: coords,
                yAnchor: 1.2
              });

              bounds.extend(coords);
              validLocations++;
            } else {
              console.warn(`Geocoding failed for: ${address}, status: ${status}`);
            }

            // 모든 위치 처리가 완료되면 지도 범위 조정
            if (processedCount === locations.length) {
              console.log(`Processing complete. Valid locations: ${validLocations}/${locations.length}`);
              
              if (validLocations > 1) {
                // 패딩을 추가하여 마커들이 화면 가장자리에 붙지 않도록 함
                // 상하좌우 80px 패딩으로 여유 공간 확보
                map.setBounds(bounds, 80, 80, 80, 80);
                
                // 적절한 줌 레벨로 조정
                setTimeout(() => {
                  const currentLevel = map.getLevel();
                  // 너무 가까우면 적당히 줌아웃
                  if (currentLevel < 3) {
                    map.setLevel(3);
                  }
                  // 너무 멀면 적당히 줌인
                  else if (currentLevel > 12) {
                    map.setLevel(12);
                  }
                }, 200);
              } else if (validLocations === 1) {
                // 단일 마커인 경우 적절한 줌 레벨 설정
                map.setLevel(6);
              } else {
                // 마커가 없는 경우 기본 줌 레벨
                map.setLevel(8);
              }
              
              // 지도 크기 재조정
              setTimeout(() => {
                map.relayout();
              }, 300);
            }
          });
        });
      } else {
        console.warn('Geocoding service not available or no locations to display');
        // 지오코딩 서비스가 없어도 기본 지도는 표시
        setTimeout(() => {
          map.relayout();
        }, 200);
      }

    } catch (error) {
      console.error('Error initializing map:', error);
      setError('지도를 초기화하는 중 오류가 발생했습니다.');
      setIsLoading(false);
    }
  };

  if (error) {
    return (
      <div className="map-container">
        <div className="map-header">
          <h3 className="map-title">📍 여행지 지도</h3>
          <p className="map-description">일정에 포함된 장소들을 지도에서 확인하세요</p>
        </div>
        <div 
          className="map-error"
          style={{
            width: '100%',
            height: '400px',
            borderRadius: '12px',
            border: '1px solid #E5E7EB',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#F9FAFB',
            color: '#6B7280',
            padding: '20px',
            textAlign: 'center'
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🗺️</div>
          <h4 style={{ margin: '0 0 12px 0', fontWeight: '600', color: '#374151' }}>지도를 불러올 수 없습니다</h4>
          <div style={{ margin: '0 0 16px 0', lineHeight: '1.5', fontSize: '14px', whiteSpace: 'pre-line' }}>
            {error}
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button 
              onClick={() => window.location.reload()} 
              style={{
                padding: '10px 20px',
                backgroundColor: '#4F46E5',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              🔄 페이지 새로고침
            </button>
            <button 
              onClick={() => {
                setError(null);
                setIsLoading(true);
                // 컴포넌트 다시 마운트하기 위해 key 변경
                setTimeout(() => {
                  window.location.hash = Math.random().toString();
                }, 100);
              }}
              style={{
                padding: '10px 20px',
                backgroundColor: '#10B981',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              🔄 다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="map-container">
      <div className="map-header">
        <h3 className="map-title">📍 여행지 지도</h3>
        <p className="map-description">일정에 포함된 장소들을 지도에서 확인하세요</p>
      </div>
      <div 
        ref={mapContainer}
        className="kakao-map"
        style={{
          width: '100%',
          height: '400px',
          borderRadius: '12px',
          border: '1px solid #E5E7EB',
          position: 'relative'
        }}
      >
        {isLoading && (
          <div 
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(249, 250, 251, 0.9)',
              zIndex: 1000,
              borderRadius: '12px'
            }}
          >
            <div 
              style={{
                width: '40px',
                height: '40px',
                border: '4px solid #E5E7EB',
                borderTop: '4px solid #4F46E5',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                marginBottom: '16px'
              }}
            />
            <p style={{ margin: 0, color: '#6B7280', fontSize: '14px' }}>지도를 로딩중입니다...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TripMap;
