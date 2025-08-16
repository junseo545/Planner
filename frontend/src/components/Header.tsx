import React from 'react';
import { Plane, MapPin, Calendar, Users } from 'lucide-react';

const Header: React.FC = (): JSX.Element => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-primary-600 p-2 rounded-lg">
              <Plane className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI 여행 플래너</h1>
              <p className="text-gray-600 text-sm">맞춤형 여행 계획을 AI가 만들어드립니다</p>
            </div>
          </div>
          
          <div className="hidden md:flex items-center space-x-6 text-sm text-gray-600">
            <div className="flex items-center space-x-2">
              <MapPin className="h-4 w-4" />
              <span>목적지 추천</span>
            </div>
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4" />
              <span>일정 관리</span>
            </div>
            <div className="flex items-center space-x-2">
              <Users className="h-4 w-4" />
              <span>맞춤 코스</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
