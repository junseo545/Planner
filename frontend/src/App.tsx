import React, { useState } from 'react';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import Header from './components/Header';
import { TripPlan } from './types';

function App(): JSX.Element {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleTripGenerated = (plan: TripPlan): void => {
    setTripPlan(plan);
  };

  const handleReset = (): void => {
    setTripPlan(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Header />
      <main className="container mx-auto px-4 py-8">
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
}

export default App;
