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
    trackEvent('여행계획_시작', {
      destination,
      duration_days: duration,
      event_category: 'trip_planning',
    });
  },

  // 여행 계획 완료
  tripPlanningCompleted: (destination: string, duration: number, totalPlaces: number) => {
    trackEvent('여행계획_완료', {
      destination,
      duration_days: duration,
      total_places: totalPlaces,
      event_category: 'trip_planning',
    });
  },

  // 장소 검색
  placeSearch: (query: string, resultsCount: number) => {
    trackEvent('장소_검색', {
      search_query: query,
      results_count: resultsCount,
      event_category: 'search',
    });
  },

  // 장소 선택
  placeSelected: (placeName: string, placeType: string) => {
    trackEvent('장소_선택', {
      place_name: placeName,
      place_type: placeType,
      event_category: 'interaction',
    });
  },


  // 에러 발생
  errorOccurred: (errorType: string, errorMessage: string) => {
    trackEvent('에러_발생', {
      error_type: errorType,
      error_message: errorMessage,
      event_category: 'error',
    });
  },

  // 사용자 상호작용
  buttonClick: (buttonName: string, location: string) => {
    trackEvent('버튼_클릭', {
      button_name: buttonName,
      location,
      event_category: 'interaction',
    });
  },

  // 지도 상호작용
  mapInteraction: (interactionType: string, details?: string) => {
    trackEvent('지도_상호작용', {
      interaction_type: interactionType,
      details,
      event_category: 'map',
    });
  },

  // 여행 계획 단계별 진행 추적
  stepCompleted: (stepNumber: number, stepName: string, stepData?: Record<string, any>) => {
    trackEvent('단계_완료', {
      step_number: stepNumber,
      step_name: stepName,
      step_data: stepData,
      event_category: 'step_progress',
    });
  },

  // 단계 이탈 (뒤로가기, 취소 등)
  stepAbandoned: (stepNumber: number, stepName: string, reason?: string) => {
    trackEvent('단계_이탈', {
      step_number: stepNumber,
      step_name: stepName,
      abandonment_reason: reason,
      event_category: 'step_progress',
    });
  },

  // 뒤로가기 버튼 클릭
  backButtonClicked: (currentStep: number, currentStepName: string, previousStep?: number) => {
    trackEvent('뒤로가기_클릭', {
      current_step: currentStep,
      current_step_name: currentStepName,
      previous_step: previousStep,
      event_category: 'navigation',
    });
  },

  // 결과 화면 상호작용
  resultItemClicked: (itemType: string, itemName: string, itemId?: string) => {
    trackEvent('결과_항목_클릭', {
      item_type: itemType, // 'hotel', 'attraction', 'restaurant' 등
      item_name: itemName,
      item_id: itemId,
      event_category: 'result_interaction',
    });
  },


  // 결과 화면에서 관광지 상세보기
  attractionDetailsViewed: (attractionName: string, attractionId: string, category?: string) => {
    trackEvent('관광지_상세보기', {
      attraction_name: attractionName,
      attraction_id: attractionId,
      category,
      event_category: 'attraction',
    });
  },

  // 숙박 예약 사이트 링크 클릭
  accommodationLinkClicked: (siteName: string, hotelName: string, destination: string) => {
    trackEvent('숙박사이트_클릭', {
      site_name: siteName, // '여기어때', '부킹닷컴', '아고다' 등
      hotel_name: hotelName,
      destination,
      event_category: 'external_link',
    });
  },


  // 결과 화면에서 일정 저장
  scheduleSaved: (totalDays: number, totalPlaces: number) => {
    trackEvent('일정_저장', {
      total_days: totalDays,
      total_places: totalPlaces,
      event_category: 'schedule_management',
    });
  },

  // 결과 화면에서 지도 보기 토글
  mapViewToggled: (isMapView: boolean) => {
    trackEvent('지도보기_토글', {
      is_map_view: isMapView,
      event_category: 'view_toggle',
    });
  },

  // 결과 화면에서 필터 적용
  resultFilterApplied: (filterType: string, filterValue: string, resultsCount: number) => {
    trackEvent('결과_필터_적용', {
      filter_type: filterType, // 'category', 'price', 'rating', 'distance' 등
      filter_value: filterValue,
      results_count: resultsCount,
      event_category: 'filtering',
    });
  },

  // 결과 화면에서 정렬 변경
  resultSorted: (sortBy: string, sortOrder: string, resultsCount: number) => {
    trackEvent('결과_정렬', {
      sort_by: sortBy, // 'price', 'rating', 'distance', 'name' 등
      sort_order: sortOrder, // 'asc', 'desc'
      results_count: resultsCount,
      event_category: 'sorting',
    });
  },

  // 피드백 배너 관련 이벤트
  feedbackBannerShown: () => {
    trackEvent('피드백배너_표시', {
      event_category: 'feedback',
    });
  },

  feedbackBannerClicked: () => {
    trackEvent('피드백배너_클릭', {
      event_category: 'feedback',
    });
  },

  feedbackBannerDismissed: () => {
    trackEvent('피드백배너_거부', {
      event_category: 'feedback',
    });
  },

  feedbackFormOpened: () => {
    trackEvent('피드백폼_열림', {
      event_category: 'feedback',
    });
  },

  feedbackFormClosed: () => {
    trackEvent('피드백폼_닫힘', {
      event_category: 'feedback',
    });
  },

  feedbackSubmitted: (rating: number, hasPositiveFeedback: boolean, hasNegativeFeedback: boolean) => {
    trackEvent('피드백_제출', {
      rating,
      has_positive_feedback: hasPositiveFeedback,
      has_negative_feedback: hasNegativeFeedback,
      event_category: 'feedback',
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
