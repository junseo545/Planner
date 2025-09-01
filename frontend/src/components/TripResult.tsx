import React, { useState } from 'react';
import { ArrowLeft, ExternalLink, Download, Share2, MapPin, Calendar, DollarSign, ChevronUp, Send } from 'lucide-react';
import { TripResultProps } from '../types';

const TripResult: React.FC<TripResultProps> = ({ tripPlan, onReset, onTripUpdated }): React.JSX.Element => {
  const [isBottomPanelOpen, setIsBottomPanelOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<Array<{type: 'user' | 'assistant', message: string}>>([]);
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
        
        <div className="day-activities">
          {day.activities && day.activities
            .filter((activity: any) => {
              // 호텔/숙박 관련 활동 필터링
              const title = activity.title?.toLowerCase() || '';
              const description = activity.description?.toLowerCase() || '';
              const category = activity.place_category?.toLowerCase() || '';
              
              // 호텔, 숙박, 체크인, 체크아웃 등의 키워드가 포함된 활동 제외
              const hotelKeywords = ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out', '펜션', '게스트하우스', '모텔'];
              
              return !hotelKeywords.some(keyword => 
                title.includes(keyword) || 
                description.includes(keyword) || 
                category.includes(keyword)
              );
            })
            .map((activity: any, index: number) => (
            <div key={index} className="activity-item">
              <div className="activity-number">
                <span className="number-badge">{index + 1}</span>
              </div>
              <div className="activity-content">
                <h4 className="activity-title">{activity.title}</h4>
                <div className="activity-location-info">
                  <p className="activity-location">📍 {activity.real_address || activity.location}</p>
                  {activity.place_category && (
                    <p className="activity-category">{activity.place_category}</p>
                  )}
                  {activity.place_telephone && (
                    <p className="activity-phone">📞 {activity.place_telephone}</p>
                  )}
                </div>
                <p className="activity-description">{activity.description}</p>

              </div>
            </div>
          ))}
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
      ${day.activities?.filter(activity => {
        // 호텔/숙박 관련 활동 필터링
        const title = activity.title?.toLowerCase() || '';
        const description = activity.description?.toLowerCase() || '';
        const hotelKeywords = ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out', '펜션', '게스트하우스', '모텔'];
        return !hotelKeywords.some(keyword => title.includes(keyword) || description.includes(keyword));
      }).map(activity => `
      ${activity.time} - ${activity.title}
      📍 ${activity.location}
      ${activity.description} (${activity.duration})
      `).join('') || '일정 정보 없음'}
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

  const handleChatSubmit = async (): Promise<void> => {
    if (!chatMessage.trim()) return;

    // 사용자 메시지 추가
    const userMessage = chatMessage.trim();
    setChatHistory(prev => [...prev, { type: 'user', message: userMessage }]);
    setChatMessage('');

    // 백엔드에 실제 수정 요청을 보냅니다
    try {
      setChatHistory(prev => [...prev, { type: 'assistant', message: '요청을 처리중입니다...' }]);
      
      const apiUrl = import.meta.env.PROD 
        ? 'https://planner-backend-3bcz.onrender.com/modify-trip-chat'
        : 'http://localhost:8000/modify-trip-chat';
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          current_trip_plan: tripPlan
        })
      });

      const result = await response.json();
      
      if (result.success && result.modified_plan) {
        // 수정된 계획으로 업데이트
        setChatHistory(prev => {
          // 마지막 "처리중" 메시지 제거하고 성공 메시지 추가
          const newHistory = [...prev];
          newHistory[newHistory.length - 1] = { 
            type: 'assistant', 
            message: result.message 
          };
          return newHistory;
        });
        
        // 상위 컴포넌트로 수정된 계획 전달
        if (onTripUpdated) {
          onTripUpdated(result.modified_plan);
        }
        
      } else {
        setChatHistory(prev => {
          const newHistory = [...prev];
          newHistory[newHistory.length - 1] = { 
            type: 'assistant', 
            message: result.message || '요청 처리 중 오류가 발생했습니다.' 
          };
          if (result.suggestion) {
            newHistory.push({ type: 'assistant', message: result.suggestion });
          }
          return newHistory;
        });
      }
    } catch (error) {
      console.error('채팅 요청 오류:', error);
      setChatHistory(prev => {
        const newHistory = [...prev];
        newHistory[newHistory.length - 1] = { 
          type: 'assistant', 
          message: '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' 
        };
        return newHistory;
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit();
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
            <p className="overview-value">
              {tripPlan.total_cost.includes('1인당') ? tripPlan.total_cost : `1인당 ${tripPlan.total_cost}`}
            </p>
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
                    title={`${siteInfo.name}에서 ${tripPlan.trip_hotel_search?.destination || tripPlan.destination} 호텔 검색하기`}
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

      {/* 하단 접힌 패널 */}
      <div className={`bottom-panel ${isBottomPanelOpen ? 'open' : ''}`}>
        {/* 올리기 버튼 */}
        <div className="panel-toggle" onClick={() => setIsBottomPanelOpen(!isBottomPanelOpen)}>
          <ChevronUp className={`chevron-icon ${isBottomPanelOpen ? 'rotated' : ''}`} />
          <span>{isBottomPanelOpen ? '접기' : '일정 수정'}</span>
        </div>

        {/* 패널 내용 */}
        {isBottomPanelOpen && (
          <div className="panel-content">
            <div className="chat-tab">
              <h3>일정 수정 요청</h3>
              <div className="chat-messages">
                {chatHistory.length === 0 ? (
                  <div className="chat-placeholder">
                    <p>예시: "2일차 다시 수정해줘", "부산 맛집 더 추가해줘"</p>
                  </div>
                ) : (
                  chatHistory.map((msg, index) => (
                    <div key={index} className={`chat-message ${msg.type}`}>
                      {msg.message}
                    </div>
                  ))
                )}
              </div>
              <div className="chat-input-container">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="일정 수정 요청을 입력하세요..."
                  className="chat-input"
                />
                <button onClick={handleChatSubmit} className="chat-send-button">
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TripResult;
