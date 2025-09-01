import React from 'react';
import { Plane } from 'lucide-react';

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
              <h1 className="header-title">Plan & Go</h1>
              <p className="header-subtitle">맞춤형 여행 계획을 AI가 만들어드립니다</p>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
};

export default Header;
