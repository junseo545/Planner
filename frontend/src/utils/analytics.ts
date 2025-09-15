// Google Analytics 4 유틸리티 함수들

declare global {
  interface Window {
    gtag: (...args: any[]) => void;
  }
}

// GA4 ID 가져오기 (환경 변수 또는 기본값)
const GA_ID = import.meta.env.VITE_GA_ID;

// GA4 이벤트 추적 함수
export const trackEvent = (eventName: string, parameters?: Record<string, any>) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', eventName, parameters);
  }
};

// 페이지 뷰 추적
export const trackPageView = (pagePath: string, pageTitle?: string) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('config', GA_ID, {
      page_path: pagePath,
      page_title: pageTitle,
    });
  }
};

// 여행 계획 관련 이벤트들
export const analyticsEvents = {
  // 여행 계획 시작
  tripPlanningStarted: (destination: string, duration: number) => {
    trackEvent('trip_planning_started', {
      destination,
      duration_days: duration,
      event_category: 'trip_planning',
    });
  },

  // 여행 계획 완료
  tripPlanningCompleted: (destination: string, duration: number, totalPlaces: number) => {
    trackEvent('trip_planning_completed', {
      destination,
      duration_days: duration,
      total_places: totalPlaces,
      event_category: 'trip_planning',
    });
  },

  // 장소 검색
  placeSearch: (query: string, resultsCount: number) => {
    trackEvent('place_search', {
      search_query: query,
      results_count: resultsCount,
      event_category: 'search',
    });
  },

  // 장소 선택
  placeSelected: (placeName: string, placeType: string) => {
    trackEvent('place_selected', {
      place_name: placeName,
      place_type: placeType,
      event_category: 'interaction',
    });
  },

  // 숙박 검색
  accommodationSearch: (destination: string, checkIn: string, checkOut: string) => {
    trackEvent('accommodation_search', {
      destination,
      check_in_date: checkIn,
      check_out_date: checkOut,
      event_category: 'accommodation',
    });
  },

  // 숙박 선택
  accommodationSelected: (hotelName: string, price: number) => {
    trackEvent('accommodation_selected', {
      hotel_name: hotelName,
      price,
      event_category: 'accommodation',
    });
  },

  // 에러 발생
  errorOccurred: (errorType: string, errorMessage: string) => {
    trackEvent('error_occurred', {
      error_type: errorType,
      error_message: errorMessage,
      event_category: 'error',
    });
  },

  // 사용자 상호작용
  buttonClick: (buttonName: string, location: string) => {
    trackEvent('button_click', {
      button_name: buttonName,
      location,
      event_category: 'interaction',
    });
  },

  // 지도 상호작용
  mapInteraction: (interactionType: string, details?: string) => {
    trackEvent('map_interaction', {
      interaction_type: interactionType,
      details,
      event_category: 'map',
    });
  },
};

// 커스텀 이벤트 추적을 위한 헬퍼 함수
export const trackCustomEvent = (
  eventName: string,
  category: string,
  action: string,
  label?: string,
  value?: number
) => {
  trackEvent(eventName, {
    event_category: category,
    event_action: action,
    event_label: label,
    value: value,
  });
};
