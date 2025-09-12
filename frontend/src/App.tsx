import React, { useState } from 'react';
import Header from './components/Header';
import TripPlanner from './components/TripPlanner';
import TripResult from './components/TripResult';
import { TripPlan } from './types';

const App: React.FC = () => {
  const [tripPlan, setTripPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTripGenerated = (plan: TripPlan) => {
    setTripPlan(plan);
  };

  const handleNewTrip = () => {
    setTripPlan(null);
  };

  const handleTripUpdated = (updatedPlan: TripPlan) => {
    setTripPlan(updatedPlan);
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
