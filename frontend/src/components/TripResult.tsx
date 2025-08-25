import React from 'react';
import { ArrowLeft, ExternalLink, Download, Share2, MapPin, Calendar, DollarSign } from 'lucide-react';
import { TripResultProps } from '../types';

const TripResult: React.FC<TripResultProps> = ({ tripPlan, onReset }): React.JSX.Element => {
  // duration에서 "(3일)" 같은 텍스트를 제거하는 함수
  const formatDuration = (duration: string): string => {
    // "(3일)" 같은 패턴을 제거
    return duration.replace(/\s*\(\d+일\)/, '');
  };

  // 일정표를 렌더링하는 함수
  const renderSchedule = (day: any) => {
    return (
      <div key={day.day} className="itinerary-day">
        <div className="day-header">
          <span className="day-badge">
            {day.day}일차
          </span>
          <span className="day-date">{day.date}</span>
        </div>
        
        <div className="day-schedule">
          <div className="schedule-item morning">
            <h4 className="schedule-title morning">🌅 오전</h4>
            <p className="schedule-content morning">{day.morning}</p>
          </div>
          <div className="schedule-item afternoon">
            <h4 className="schedule-title afternoon">☀️ 오후</h4>
            <p className="schedule-content afternoon">{day.afternoon}</p>
          </div>
          <div className="schedule-item evening">
            <h4 className="schedule-title evening">🌙 저녁</h4>
            <p className="schedule-content evening">{day.evening}</p>
          </div>
        </div>
        
        
      </div>
    );
  };

  const handleDownload = (): void => {
    const content = `
      여행 계획서

      목적지: ${tripPlan.destination}
      기간: ${formatDuration(tripPlan.duration)}
      총 비용: ${tripPlan.total_cost}

      일정:
      ${tripPlan.itinerary.map(day => `
      ${day.day}일차 (${day.date})
      오전: ${day.morning}
      오후: ${day.afternoon}
      저녁: ${day.evening}
      `).join('')}

      

      여행 팁:
      ${tripPlan.tips.map(tip => `• ${tip}`).join('\n')}
    `;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tripPlan.destination}_여행계획서.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = async (): Promise<void> => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${tripPlan.destination} 여행 계획`,
          text: `AI가 만든 ${tripPlan.destination} 여행 계획을 확인해보세요!`,
          url: window.location.href
        });
      } catch (error) {
        console.log('공유 취소됨');
      }
    } else {
      // 공유 API가 지원되지 않는 경우 클립보드에 복사
      const text = `${tripPlan.destination} 여행 계획: ${window.location.href}`;
      navigator.clipboard.writeText(text);
      alert('링크가 클립보드에 복사되었습니다!');
    }
  };

  return (
    <div className="result-container">
      {/* 헤더 */}
      <div className="result-header">
        <button
          onClick={onReset}
          className="back-button"
        >
          <ArrowLeft />
          <span>새로운 여행 계획 만들기</span>
        </button>
        
        <div className="action-buttons">
          <button onClick={handleDownload} className="action-button">
            <Download />
            <span>다운로드</span>
          </button>
          <button onClick={handleShare} className="action-button">
            <Share2 />
            <span>공유</span>
          </button>
        </div>
      </div>

      {/* 여행 개요 */}
      <div className="overview-card">
        <div className="overview-header">
          <h1 className="overview-title">
            🎉 {tripPlan.destination} 여행 계획 완성!
          </h1>
          <p className="overview-subtitle">AI가 당신을 위해 맞춤형 여행 계획을 만들었습니다</p>
        </div>
        
        <div className="overview-grid">
          <div className="overview-item blue">
            <MapPin className="overview-icon blue" />
            <h3 className="overview-label">목적지</h3>
            <p className="overview-value">{tripPlan.destination}</p>
          </div>
          <div className="overview-item green">
            <Calendar className="overview-icon green" />
            <h3 className="overview-label">여행 기간</h3>
            <p className="overview-value">{formatDuration(tripPlan.duration)}</p>
          </div>
          <div className="overview-item purple">
            <DollarSign className="overview-icon purple" />
            <span className="overview-label">예상 비용</span>
            <p className="overview-value">{tripPlan.total_cost}</p>
          </div>
        </div>
      </div>

      {/* 상세 일정 */}
      <div className="itinerary-card">
        <h2 className="itinerary-title">📅 상세 일정</h2>
        <div className="itinerary-list">
          {tripPlan.itinerary.map((day) => renderSchedule(day))}
        </div>
      </div>

      {/* 대중교통 정보 */}
      {tripPlan.transport_info && (
        <div className="transport-card">
          <h2 className="transport-title">🚌 대중교통 정보</h2>
          <div className="transport-list">
            {Object.entries(tripPlan.transport_info.itinerary_transport || {}).map(([dayKey, dayTransport]) => {
              const dayNumber = dayKey.replace('day_', '');
              return (
                <div key={dayKey} className="transport-day">
                  <h3 className="transport-day-title">{dayNumber}일차 이동 정보</h3>
                  <div className="transport-routes">
                    {Array.isArray(dayTransport) && dayTransport.map((route, routeIndex) => (
                      <div key={routeIndex} className="transport-route">
                        <div className="route-header">
                          <span className="route-time">{route.time}</span>
                          <span className="route-direction">
                            {route.from} → {route.to}
                          </span>
                        </div>
                        {route.transport_info && route.transport_info.recommended_routes && (
                          <div className="route-options">
                            {route.transport_info.recommended_routes.map((option, optionIndex) => (
                              <div key={optionIndex} className="route-option">
                                <div className="option-header">
                                  <span className="option-type">{option.route_type}</span>
                                  {option.route && <span className="option-route">{option.route}</span>}
                                </div>
                                <p className="option-description">{option.description}</p>
                                <div className="option-meta">
                                  <span className="option-time">⏱️ {option.estimated_time}</span>
                                  <span className="option-fare">💰 {option.fare}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 전체 여행 호텔 검색 링크 */}
      {tripPlan.trip_hotel_search && (
        <div className="trip-hotel-search-card">
          <h2 className="trip-hotel-search-title">🏨 호텔 검색 및 예약</h2>
          <div className="trip-hotel-search-info">
            
            <div className="search-links-section">
              <h3 className="search-links-title">호텔 예약 사이트에서 검색하기</h3>
              <p className="search-links-description">
                아래 링크를 클릭하면 입력하신 여행 정보로 각 사이트에서 호텔을 검색할 수 있습니다.
              </p>
              <div className="search-links-grid">
                {Object.entries(tripPlan.trip_hotel_search.search_links).map(([siteKey, siteInfo]) => (
                  <a
                    key={siteKey}
                    href={siteInfo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    className="search-link-card"
                    title={`${siteInfo.name}에서 ${tripPlan.trip_hotel_search?.destination} 호텔 검색하기`}
                  >
                    <div className="search-link-icon">{siteInfo.icon}</div>
                    <div className="search-link-content">
                      <h4 className="search-link-name">{siteInfo.name}</h4>
                      <p className="search-link-description">{siteInfo.description}</p>
                  </div>
                    <ExternalLink className="search-link-arrow" />
                    </a>
                  ))}
                </div>
              </div>
            </div>
        </div>
      )}

      

      {/* 여행 팁 */}
      <div className="tips-card">
        <h2 className="tips-title">💡 여행 팁</h2>
        <div className="tips-grid">
          {tripPlan.tips.map((tip) => (
            <div key={tip} className="tip-item">
              <span className="tip-icon">💡</span>
              <p className="tip-text">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TripResult;
