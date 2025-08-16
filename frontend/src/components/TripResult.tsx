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
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onReset}
          className="btn-secondary flex items-center space-x-2"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>새로운 여행 계획 만들기</span>
        </button>
        
        <div className="flex space-x-3">
          <button onClick={handleDownload} className="btn-secondary flex items-center space-x-2">
            <Download className="h-4 w-4" />
            <span>다운로드</span>
          </button>
          <button onClick={handleShare} className="btn-secondary flex items-center space-x-2">
            <Share2 className="h-4 w-4" />
            <span>공유</span>
          </button>
        </div>
      </div>

      {/* 여행 개요 */}
      <div className="card mb-8">
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🎉 {tripPlan.destination} 여행 계획 완성!
          </h1>
          <p className="text-xl text-gray-600">AI가 당신을 위해 맞춤형 여행 계획을 만들었습니다</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <MapPin className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h3 className="font-semibold text-gray-900">목적지</h3>
            <p className="text-gray-600">{tripPlan.destination}</p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <Calendar className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <h3 className="font-semibold text-gray-900">여행 기간</h3>
            <p className="text-gray-600">{tripPlan.duration}</p>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <DollarSign className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <span className="font-semibold text-gray-900">예상 비용</span>
            <p className="text-gray-600">{tripPlan.total_cost}</p>
          </div>
        </div>
      </div>

      {/* 상세 일정 */}
      <div className="card mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">📅 상세 일정</h2>
        <div className="space-y-6">
          {tripPlan.itinerary.map((day, index) => (
            <div key={index} className="border-l-4 border-primary-500 pl-6 py-4">
              <div className="flex items-center mb-3">
                <span className="bg-primary-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                  {day.day}일차
                </span>
                <span className="ml-3 text-gray-500">{day.date}</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-1">🌅 오전</h4>
                  <p className="text-blue-800">{day.morning}</p>
                </div>
                <div className="bg-yellow-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-yellow-900 mb-1">☀️ 오후</h4>
                  <p className="text-yellow-800">{day.afternoon}</p>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-purple-900 mb-1">🌙 저녁</h4>
                  <p className="text-purple-800">{day.evening}</p>
                </div>
              </div>
              
              <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-1">🏨 숙박</h4>
                <p className="text-gray-700">{day.accommodation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 축제/행사 정보 */}
      <div className="card mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">🎊 축제/행사 정보</h2>

        {tripPlan.events && tripPlan.events.length > 0 ? (
          <div className="grid grid-cols-1 gap-6">
            {tripPlan.events.map((event, index) => (
              <div key={index} className="border border-purple-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-gradient-to-r from-purple-50 to-pink-50">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <h3 className="text-xl font-semibold text-gray-900">{event.name}</h3>
                      <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
                        {event.type}
                      </span>
                    </div>
                    
                    {/* 날짜와 위치 정보 */}
                    <div className="flex items-center space-x-4 mb-3">
                      <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        <Calendar className="h-3 w-3 mr-1" />
                        {event.date}
                      </span>
                      <span className="inline-flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                        <MapPin className="h-3 w-3 mr-1" />
                        {event.location}
                      </span>
                    </div>
                    
                    <p className="text-gray-600 mb-4">{event.description}</p>
                    
                    {/* 티켓 정보 */}
                    {event.ticket_info && (
                      <div className="mb-4">
                        <span className="inline-flex items-center px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                          💳 {event.ticket_info}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* 웹사이트 링크 */}
                {event.website && (
                  <div className="border-t pt-4">
                    <a
                      href={event.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      공식 웹사이트 방문
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>이 기간에 해당하는 특별한 축제나 행사가 없습니다.</p>
            <p className="text-sm mt-2">일반적인 관광지와 문화체험을 즐겨보세요!</p>
          </div>
        )}
      </div>

      {/* 숙박 정보 */}
      <div className="card mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">🏨 추천 숙박</h2>
        <div className="grid grid-cols-1 gap-6">
          {tripPlan.accommodation.map((acc, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{acc.name}</h3>
                  <div className="flex items-center space-x-4 mb-3">
                    <span className="text-sm text-gray-500">{acc.type}</span>
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                      {acc.price_range}
                    </span>
                    {acc.rating && (
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4 text-yellow-500 fill-current" />
                        <span className="text-sm text-gray-700">{acc.rating}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* 위치 정보 */}
                  {acc.location && (
                    <div className="mb-3">
                      <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        <MapPin className="h-3 w-3 mr-1" />
                        {acc.location}
                      </span>
                    </div>
                  )}
                  
                  <p className="text-gray-600 mb-4">{acc.description}</p>
                  
                  {/* 편의시설 */}
                  {acc.amenities && acc.amenities.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">편의시설</h4>
                      <div className="flex flex-wrap gap-2">
                        {acc.amenities.map((amenity, idx) => (
                          <span key={idx} className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                            {amenity === '무료 WiFi' && <Wifi className="h-3 w-3 mr-1" />}
                            {amenity === '주차' && <Car className="h-3 w-3 mr-1" />}
                            {amenity === '조식' && <Coffee className="h-3 w-3 mr-1" />}
                            {amenity === '수영장' && <span className="mr-1">🏊</span>}
                            {amenity === '스파' && <span className="mr-1">💆</span>}
                            {amenity === '피트니스' && <span className="mr-1">💪</span>}
                            {amenity === '골프장' && <span className="mr-1">⛳</span>}
                            {amenity === '레스토랑' && <span className="mr-1">🍽️</span>}
                            {amenity === '주방' && <span className="mr-1">🍳</span>}
                            {amenity === '바베큐' && <span className="mr-1">🔥</span>}
                            {amenity === '세탁기' && <span className="mr-1">🧺</span>}
                            {amenity === '미슐랭 레스토랑' && <span className="mr-1">⭐</span>}
                            {amenity}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* 예약 링크 */}
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">예약 사이트</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(acc.booking_links).map(([key, link]) => (
                    <a
                      key={key}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200 hover:border-gray-300"
                      title={`${link.name}에서 ${acc.name} 예약하기`}
                    >
                      <span className="text-2xl mb-1">{link.icon}</span>
                      <span className="text-xs font-medium text-gray-700 text-center">{link.name}</span>
                      <ExternalLink className="h-3 w-3 text-gray-500 mt-1" />
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 여행 팁 */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">💡 여행 팁</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tripPlan.tips.map((tip, index) => (
            <div key={index} className="flex items-start space-x-3 p-4 bg-yellow-50 rounded-lg">
              <span className="text-yellow-600 text-lg">💡</span>
              <p className="text-gray-800">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TripResult;
