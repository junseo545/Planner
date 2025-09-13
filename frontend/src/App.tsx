import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import { TripPlan } from './types';

const App: React.FC = () => {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState(false);

  // 컴포넌트 마운트 시 저장된 여행 계획 복원
  useEffect(() => {
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
