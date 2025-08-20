import React from 'react';
import { ArrowLeft, Calendar, MapPin, DollarSign, ExternalLink, Download, Share2, Star, Wifi, Car, Coffee } from 'lucide-react';
import { TripPlan, TripResultProps } from '../types';

const TripResult: React.FC<TripResultProps> = ({ tripPlan, onReset }): JSX.Element => {
  const handleDownload = (): void => {
    const content = `
      여행 계획서

      목적지: ${tripPlan.destination}
      기간: ${tripPlan.duration}
      총 비용: ${tripPlan.total_cost}

      일정:
      ${tripPlan.itinerary.map(day => `
      ${day.day}일차 (${day.date})
      오전: ${day.morning}
      오후: ${day.afternoon}
      저녁: ${day.evening}
      숙박: ${day.accommodation}
      `).join('')}

      ${tripPlan.events && tripPlan.events.length > 0 ? `
      축제/행사 정보:
      ${tripPlan.events.map(event => `
      ${event.name} (${event.type})
      날짜: ${event.date}
      장소: ${event.location}
      설명: ${event.description}
      ${event.ticket_info ? `티켓: ${event.ticket_info}` : ''}
      ${event.website ? `웹사이트: ${event.website}` : ''}
      `).join('')}
      ` : ''}

      숙박 정보:
      ${tripPlan.accommodation.map(acc => `
      ${acc.name} (${acc.type})
      가격대: ${acc.price_range}
      설명: ${acc.description}
      ${acc.rating ? `평점: ${acc.rating}/5` : ''}
      ${acc.amenities ? `편의시설: ${acc.amenities.join(', ')}` : ''}
      예약 사이트:
      ${Object.values(acc.booking_links).map(link => `- ${link.name}: ${link.url}`).join('\n')}
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
            <p className="overview-value">{tripPlan.duration}</p>
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
          {tripPlan.itinerary.map((day, index) => (
            <div key={index} className="itinerary-day">
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
              
              <div className="schedule-item accommodation">
                <h4 className="schedule-title accommodation">🏨 숙박</h4>
                <p className="schedule-content accommodation">{day.accommodation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 축제/행사 정보 */}
      <div className="events-card">
        <h2 className="events-title">🎊 축제/행사 정보</h2>

        {tripPlan.events && tripPlan.events.length > 0 ? (
          <div className="grid-1">
            {tripPlan.events.map((event, index) => (
              <div key={index} className="event-item">
                <div className="event-header">
                  <div className="flex-1">
                    <div className="flex-start gap-3 mb-3">
                      <h3 className="event-title">{event.name}</h3>
                      <span className="event-type">
                        {event.type}
                      </span>
                    </div>
                    
                    {/* 날짜와 위치 정보 */}
                    <div className="flex-start gap-4 mb-3">
                      <span className="meta-badge blue">
                        <Calendar />
                        {event.date}
                      </span>
                      <span className="meta-badge green">
                        <MapPin />
                        {event.location}
                      </span>
                    </div>
                    
                    <p className="event-description">{event.description}</p>
                    
                    {/* 티켓 정보 */}
                    {event.ticket_info && (
                      <div className="mb-4">
                        <span className="meta-badge orange">
                          💳 {event.ticket_info}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* 웹사이트 링크 */}
                {event.website && (
                  <div className="event-website">
                    <a
                      href={event.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="website-button"
                    >
                      <ExternalLink />
                      공식 웹사이트 방문
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>이 기간에 해당하는 특별한 축제나 행사가 없습니다.</p>
            <p className="empty-subtitle">일반적인 관광지와 문화체험을 즐겨보세요!</p>
          </div>
        )}
      </div>

      {/* 숙박 정보 */}
      <div className="accommodation-card">
        <h2 className="accommodation-title">🏨 추천 숙박</h2>
        <div className="grid-1">
          {tripPlan.accommodation.map((acc, index) => (
            <div key={index} className="accommodation-item">
              <div className="accommodation-header">
                <div className="flex-1">
                  <h3 className="accommodation-name">{acc.name}</h3>
                  <div className="flex-start gap-4 mb-3">
                    <span className="accommodation-type">{acc.type}</span>
                    <span className="price-badge">
                      {acc.price_range}
                    </span>
                    {acc.rating && (
                      <div className="rating">
                        <Star />
                        <span className="rating-text">{acc.rating}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* 위치 정보 */}
                  {acc.location && (
                    <div className="accommodation-location">
                      <span className="location-badge">
                        <MapPin />
                        {acc.location}
                      </span>
                    </div>
                  )}
                  
                  <p className="accommodation-description">{acc.description}</p>
                  
                  {/* 편의시설 */}
                  {acc.amenities && acc.amenities.length > 0 && (
                    <div className="amenities-section">
                      <h4 className="amenities-title">편의시설</h4>
                      <div className="amenities-list">
                        {acc.amenities.map((amenity, idx) => (
                          <span key={idx} className="amenity-badge">
                            {amenity === '무료 WiFi' && <Wifi />}
                            {amenity === '주차' && <Car />}
                            {amenity === '조식' && <Coffee />}
                            {amenity === '수영장' && <span>🏊</span>}
                            {amenity === '스파' && <span>💆</span>}
                            {amenity === '피트니스' && <span>💪</span>}
                            {amenity === '골프장' && <span>⛳</span>}
                            {amenity === '레스토랑' && <span>🍽️</span>}
                            {amenity === '주방' && <span>🍳</span>}
                            {amenity === '바베큐' && <span>🔥</span>}
                            {amenity === '세탁기' && <span>🧺</span>}
                            {amenity === '미슐랭 레스토랑' && <span>⭐</span>}
                            {amenity}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* 예약 링크 */}
              <div className="booking-section">
                <h4 className="booking-title">예약 사이트</h4>
                <div className="booking-grid">
                  {Object.entries(acc.booking_links).map(([key, link]) => (
                    <a
                      key={key}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="booking-link"
                      title={`${link.name}에서 ${acc.name} 예약하기`}
                    >
                      <span className="booking-icon">{link.icon}</span>
                      <span className="booking-name">{link.name}</span>
                      <ExternalLink />
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 여행 팁 */}
      <div className="tips-card">
        <h2 className="tips-title">💡 여행 팁</h2>
        <div className="tips-grid">
          {tripPlan.tips.map((tip, index) => (
            <div key={index} className="tip-item">
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
