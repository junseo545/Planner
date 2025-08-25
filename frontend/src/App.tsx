import React, { useState } from 'react';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import Header from './components/Header';
import { TripPlan } from './types';

const App: React.FC = (): React.JSX.Element => {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleTripGenerated = (plan: TripPlan): void => {
    setTripPlan(plan);
  };

  const handleReset = (): void => {
    setTripPlan(null);
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
          />
        )}
      </main>
    </div>
  );
};

export default App;
