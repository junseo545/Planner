import React, { useState, useMemo } from 'react';
import { ArrowLeft, ExternalLink, Download, MapPin, Calendar, DollarSign, ChevronUp, Send } from 'lucide-react';
import { TripResultProps, FeedbackData } from '../types';
import TripMap from './TripMap';
import FeedbackForm from './FeedbackForm';
import { analyticsEvents } from '../utils/analytics';
import { saveFeedbackToSupabase } from '../lib/feedbackService';
import '../styles/FeedbackForm.css';

const TripResult: React.FC<TripResultProps> = ({ tripPlan, onReset, onTripUpdated }): React.JSX.Element => {
  const [isBottomPanelOpen, setIsBottomPanelOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState(1);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  // 지도에 표시할 위치 데이터 준비 (선택된 일차만)
  const mapLocations = useMemo(() => {
    const locations: any[] = [];
    
    // 선택된 일차의 데이터만 필터링
    const selectedDayData = tripPlan.itinerary.find(day => day.day === selectedDay);
    
    if (selectedDayData && selectedDayData.activities) {
      selectedDayData.activities
        .filter((activity: any) => {
          // 호텔/숙박 관련 활동 필터링
          const title = activity.title?.toLowerCase() || '';
          const description = activity.description?.toLowerCase() || '';
          const category = activity.place_category?.toLowerCase() || '';
          
          const hotelKeywords = ['호텔', '숙박', '체크인', '체크아웃', 'hotel', 'check-in', 'check-out', '펜션', '게스트하우스', '모텔'];
          
          return !hotelKeywords.some(keyword => 
            title.includes(keyword) || 
            description.includes(keyword) || 
            category.includes(keyword)
          );
        })
        .forEach((activity: any, activityIndex: number) => {
          locations.push({
            title: activity.title,
            location: activity.location,
            real_address: activity.real_address,
            description: activity.description,
            time: activity.time,
            day: selectedDayData.day,
            order: activityIndex + 1 // 일정 순서 번호 추가
          });
        });
    }
    
    return locations;
  }, [tripPlan, selectedDay]);
  // duration에서 "(3일)" 같은 텍스트를 제거하는 함수
  const formatDuration = (duration: string): string => {
    // "(3일)" 같은 패턴을 제거
    return duration.replace(/\s*\(\d+일\)/, '');
  };



  const handleDownload = (): void => {
    // GA4 이벤트 추적
    analyticsEvents.buttonClick('download_trip_plan', 'trip_result');
    
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




  const handleFeedbackSubmit = async (feedback: FeedbackData): Promise<void> => {
    try {
      // GA4 이벤트 추적
      analyticsEvents.buttonClick('feedback_submitted', 'trip_result');

      // Supabase에 피드백 저장
      const feedbackData = {
        ...feedback,
        tripId: `${tripPlan.destination}_${Date.now()}`,
        destination: tripPlan.destination,
        duration: tripPlan.duration,
        timestamp: new Date().toISOString()
      };

      const result = await saveFeedbackToSupabase(feedbackData);

      if (result.success) {
        setFeedbackSubmitted(true);
        setShowFeedbackForm(false);
        alert('피드백이 성공적으로 제출되었습니다! 소중한 의견 감사합니다. 🙏');
      } else {
        throw new Error(result.error || '피드백 제출 실패');
      }
    } catch (error) {
      console.error('피드백 제출 오류:', error);
      
      // Supabase 오류가 있어도 로컬에 백업 저장
      const feedbacks = JSON.parse(localStorage.getItem('trip_feedbacks') || '[]');
      feedbacks.push({
        ...feedback,
        tripId: `${tripPlan.destination}_${Date.now()}`,
        destination: tripPlan.destination,
        duration: tripPlan.duration,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('trip_feedbacks', JSON.stringify(feedbacks));
      
      setFeedbackSubmitted(true);
      setShowFeedbackForm(false);
      alert('피드백이 로컬에 저장되었습니다! 소중한 의견 감사합니다. 🙏');
    }
  };



  return (
    <div className="result-container">
      {/* 헤더 */}
      <div className="result-header">
        <button
          onClick={() => {
            analyticsEvents.buttonClick('new_trip_plan', 'trip_result');
            onReset();
          }}
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
              {tripPlan.total_cost}
            </p>
          </div>
        </div>
      </div>

      {/* 지도 */}
      {mapLocations.length > 0 && (
        <div className="map-card">
          <TripMap locations={mapLocations} destination={tripPlan.destination} />
        </div>
      )}

      {/* 선택된 일차의 상세 일정 */}
      <div className="itinerary-card">
        <h2 className="itinerary-title">📅 상세 일정</h2>
        
        {/* 일차별 탭 */}
        <div className="day-tabs">
          {tripPlan.itinerary.map((day) => (
            <button
              key={day.day}
              onClick={() => setSelectedDay(day.day)}
              className={`day-tab ${selectedDay === day.day ? 'active' : ''}`}
            >
              Day {day.day}
            </button>
          ))}
        </div>
        
        {/* 선택된 일차의 일정만 표시 */}
        <div className="itinerary-list">
          {tripPlan.itinerary
            .filter(day => day.day === selectedDay)
            .map((day) => (
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
                        </div>
                        <p className="activity-description">{activity.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
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

      {/* 평가 폼 */}
      {!feedbackSubmitted && (
        <div className="feedback-section">
          {!showFeedbackForm ? (
            <div className="feedback-prompt">
              <h2 className="feedback-prompt-title">여행 계획이 도움이 되셨나요?</h2>
              <p className="feedback-prompt-description">
                소중한 피드백을 주시면 더 나은 서비스를 제공할 수 있습니다.
              </p>
              <button
                onClick={() => {
                  analyticsEvents.buttonClick('feedback_form_open', 'trip_result');
                  setShowFeedbackForm(true);
                }}
                className="feedback-prompt-button"
              >
                평가하기
              </button>
            </div>
          ) : (
            <FeedbackForm
              onSubmit={handleFeedbackSubmit}
              onCancel={() => setShowFeedbackForm(false)}
            />
          )}
        </div>
      )}

      {/* 평가 완료 메시지 */}
      {feedbackSubmitted && (
        <div className="feedback-thanks">
          <h2 className="feedback-thanks-title">감사합니다! 🙏</h2>
          <p className="feedback-thanks-description">
            소중한 피드백을 주셔서 정말 감사합니다!<br/>
            여러분의 의견을 바탕으로 더욱 나은 여행 계획 서비스를 만들어가겠습니다. ✨
          </p>
        </div>
      )}

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
                <div className="chat-placeholder">
                  <p><strong>일정 수정 예시:</strong></p>
                  <p><strong>📅 일정 추가:</strong> "1일차 일정 늘려줘", "2일차 오후에 뭔가 더 추가해줘"</p>
                  <p><strong>❌ 일정 제거:</strong> "1일차 마사지 빼줘", "2일차 오후 일정 제거해줘"</p>
                  <p><strong>🔄 일정 교체:</strong> "3일차 마사지를 맛집으로 바꿔줘", "1일차 ○○를 다른 곳으로 바꿔줘"</p>
                  <p><strong>↔️ 일정 이동:</strong> "2일차 해수욕장과 3일차 타워 바꿔줘", "1일차 아침 일정을 2일차로 옮겨줘"</p>
                </div>
              </div>
              <div className="chat-input-container" style={{ opacity: 0.5, pointerEvents: 'none' }}>
                <input
                  type="text"
                  value=""
                  placeholder="현재 기능을 구현 중입니다"
                  className="chat-input"
                  disabled
                />
                <button 
                  className="chat-send-button"
                  disabled
                >
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
