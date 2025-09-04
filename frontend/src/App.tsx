import React, { useState, useEffect } from 'react';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import Header from './components/Header';
import { TripPlan } from './types';

const App: React.FC = (): React.JSX.Element => {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // 컴포넌트 마운트 시 저장된 상태 복원
  useEffect(() => {
    try {
      const savedTripPlan = sessionStorage.getItem('currentTripPlan');
      if (savedTripPlan) {
        const parsedPlan = JSON.parse(savedTripPlan);
        setTripPlan(parsedPlan);
        console.log('Restored trip plan from session storage');
      }
    } catch (error) {
      console.error('Error restoring trip plan:', error);
      // 오류 발생 시 저장된 데이터 삭제
      sessionStorage.removeItem('currentTripPlan');
    }
  }, []);

  // tripPlan 상태가 변경될 때마다 저장
  useEffect(() => {
    if (tripPlan) {
      try {
        sessionStorage.setItem('currentTripPlan', JSON.stringify(tripPlan));
        console.log('Trip plan saved to session storage');
      } catch (error) {
        console.error('Error saving trip plan:', error);
      }
    } else {
      // tripPlan이 null이면 저장된 데이터도 삭제
      sessionStorage.removeItem('currentTripPlan');
      console.log('Trip plan removed from session storage');
    }
  }, [tripPlan]);

  const handleTripGenerated = (plan: TripPlan): void => {
    setTripPlan(plan);
  };

  const handleReset = (): void => {
    setTripPlan(null);
    // 리셋 시 플래너 데이터도 삭제
    sessionStorage.removeItem('tripPlannerFormData');
    sessionStorage.removeItem('tripPlannerCurrentStep');
    console.log('Reset: Cleared all session data');
  };

  const handleTripUpdated = (updatedPlan: TripPlan): void => {
    setTripPlan(updatedPlan);
  };

  return (
    <div className="App">
      <Header />
      <main className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
        {!tripPlan ? (
          <TripPlanner 
            onTripGenerated={handleTripGenerated}
            loading={loading}
            setLoading={setLoading}
          />
        ) : (
          <TripResult 
            tripPlan={tripPlan}
            onReset={handleReset}
            onTripUpdated={handleTripUpdated}
          />
        )}
      </main>
    </div>
  );
};

export default App;
