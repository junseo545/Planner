import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import { TripPlan, FeedbackData } from './types';
import { trackPageView } from './utils/analytics';
import { saveFeedbackToSupabase } from './lib/feedbackService';

const App: React.FC = () => {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState(false);

  // 컴포넌트 마운트 시 저장된 여행 계획 복원 및 페이지 뷰 추적
  useEffect(() => {
    // 페이지 뷰 추적
    trackPageView(window.location.pathname, 'Plan & Go - AI 여행 플래너');
    
    try {
      const savedTripPlan = sessionStorage.getItem('currentTripPlan');
      if (savedTripPlan) {
        const parsedTripPlan = JSON.parse(savedTripPlan);
        setTripPlan(parsedTripPlan);
        console.log('Restored trip plan from session storage');
      }
    } catch (error) {
      console.error('Error restoring trip plan:', error);
      // 오류 발생 시 저장된 데이터 삭제
      sessionStorage.removeItem('currentTripPlan');
    }
  }, []);

  const handleTripGenerated = (plan: TripPlan) => {
    setTripPlan(plan);
    // 여행 계획을 세션 스토리지에 저장
    try {
      sessionStorage.setItem('currentTripPlan', JSON.stringify(plan));
      console.log('Saved trip plan to session storage');
    } catch (error) {
      console.error('Error saving trip plan:', error);
    }
  };

  const handleNewTrip = () => {
    setTripPlan(null);
    // 새 여행 시작 시 저장된 데이터 삭제
    sessionStorage.removeItem('currentTripPlan');
    sessionStorage.removeItem('tripPlannerFormData');
    sessionStorage.removeItem('tripPlannerCurrentStep');
    console.log('Cleared all trip data from session storage');
  };

  const handleTripUpdated = (updatedPlan: TripPlan) => {
    setTripPlan(updatedPlan);
    // 업데이트된 여행 계획을 세션 스토리지에 저장
    try {
      sessionStorage.setItem('currentTripPlan', JSON.stringify(updatedPlan));
      console.log('Updated trip plan in session storage');
    } catch (error) {
      console.error('Error updating trip plan in session storage:', error);
    }
  };

  const handleFeedbackSubmit = async (feedbackData: FeedbackData) => {
    try {
      // 여행 계획 정보 추가
      const enhancedFeedback: FeedbackData = {
        ...feedbackData,
        tripId: tripPlan?.id || `trip_${Date.now()}`,
        destination: tripPlan?.destination || 'unknown',
        duration: tripPlan?.duration || 'unknown',
        timestamp: new Date().toISOString()
      };

      const result = await saveFeedbackToSupabase(enhancedFeedback);
      
      if (result.success) {
        console.log('피드백이 성공적으로 저장되었습니다.');
      } else {
        console.error('피드백 저장 실패:', result.error);
        throw new Error(result.error || '피드백 저장에 실패했습니다.');
      }
    } catch (error) {
      console.error('피드백 제출 오류:', error);
      throw error;
    }
  };

  return (
    <div className="app">
      <Header />
      <main className="main-content">
        {!tripPlan ? (
          <TripPlanner 
            onTripGenerated={handleTripGenerated}
            loading={loading}
            setLoading={setLoading}
          />
        ) : (
          <TripResult 
            tripPlan={tripPlan}
            onReset={handleNewTrip}
            onTripUpdated={handleTripUpdated}
          />
        )}
      </main>
    </div>
  );
};

export default App;
