import React from 'react';
import { Plane, MapPin, Calendar, Users } from 'lucide-react';

const Header: React.FC = (): JSX.Element => {
  return (
    <header className="header">
      <div className="header-container">
        <div className="header-content">
          <div className="header-brand">
            <div className="header-logo">
              <Plane />
            </div>
            <div>
              <h1 className="header-title">AI 여행 플래너</h1>
              <p className="header-subtitle">맞춤형 여행 계획을 AI가 만들어드립니다</p>
            </div>
          </div>
          
          <div className="header-nav">
            <div className="header-nav-item">
              <MapPin />
              <span>목적지 추천</span>
            </div>
            <div className="header-nav-item">
              <Calendar />
              <span>일정 관리</span>
            </div>
            <div className="header-nav-item">
              <Users />
              <span>맞춤 코스</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
