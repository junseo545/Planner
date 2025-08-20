import React, { useState } from 'react';
import { Search, Calendar, MapPin, DollarSign, Heart, Users, Bed } from 'lucide-react';
import axios from 'axios';
import { TripPlan, TripPlannerProps, FormData } from '../types';

const TripPlanner: React.FC<TripPlannerProps> = ({ onTripGenerated, loading, setLoading }): JSX.Element => {
  const [formData, setFormData] = useState<FormData>({
    destination: '',
    start_date: '',
    end_date: '',
    budget: '보통',
    interests: [],
    guests: 2,
    rooms: 1
  });

  const interestOptions: string[] = [
    '자연 관광', '문화 체험', '맛집 탐방', '쇼핑', '액티비티', '휴양', '역사 탐방'
  ];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'guests' || name === 'rooms' ? parseInt(value) : value
    }));
  };

  const handleInterestToggle = (interest: string): void => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    
    if (!formData.destination || !formData.start_date || !formData.end_date) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    setLoading(true);
    
    try {
      const response = await axios.post<TripPlan>('http://localhost:8000/plan-trip', formData);
      onTripGenerated(response.data);
    } catch (error) {
      console.error('여행 계획 생성 오류:', error);
      alert('여행 계획 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="planner-container">
      <div className="planner-header">
        <h2 className="planner-title">
          당신만의 맞춤 여행 계획을 만들어보세요
        </h2>
        <p className="planner-subtitle">
          AI가 추천하는 최적의 여행 코스와 숙박 정보를 제공합니다
        </p>
      </div>

      <div className="planner-form">
        <form onSubmit={handleSubmit} className="gap-6">
          {/* 목적지 입력 */}
          <div className="form-section">
            <label className="form-label">
              <MapPin />
              여행하고 싶은 지역
            </label>
            <input
              type="text"
              name="destination"
              value={formData.destination}
              onChange={handleInputChange}
              placeholder="예: 제주도, 부산, 도쿄, 파리..."
              className="form-input"
              required
            />
          </div>

          {/* 날짜 선택 */}
          <div className="form-grid">
            <div className="form-section">
              <label className="form-label">
                <Calendar />
                출발일
              </label>
              <input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleInputChange}
                className="form-input"
                required
              />
            </div>
            <div className="form-section">
              <label className="form-label">
                <Calendar />
                도착일
              </label>
              <input
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleInputChange}
                className="form-input"
                required
              />
            </div>
          </div>

          {/* 예산 선택 */}
          <div className="form-section">
            <label className="form-label">
              <DollarSign />
              예산
            </label>
            <select
              name="budget"
              value={formData.budget}
              onChange={handleInputChange}
              className="form-select"
            >
              <option value="저예산">저예산</option>
              <option value="보통">보통</option>
              <option value="고급">고급</option>
              <option value="럭셔리">럭셔리</option>
            </select>
          </div>

          {/* 투숙객 및 객실 수 */}
          <div className="form-grid">
            <div className="form-section">
              <label className="form-label">
                <Users />
                투숙객 수
              </label>
              <select
                name="guests"
                value={formData.guests}
                onChange={handleInputChange}
                className="form-select"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                  <option key={num} value={num}>{num}명</option>
                ))}
              </select>
            </div>
            <div className="form-section">
              <label className="form-label">
                <Bed />
                객실 수
              </label>
              <select
                name="rooms"
                value={formData.rooms}
                onChange={handleInputChange}
                className="form-select"
              >
                {[1, 2, 3, 4, 5].map(num => (
                  <option key={num} value={num}>{num}개</option>
                ))}
              </select>
            </div>
          </div>

          {/* 관심사 선택 */}
          <div className="form-section">
            <label className="form-label">
              <Heart />
              관심사 (선택사항)
            </label>
            <div className="interests-grid">
              {interestOptions.map((interest) => (
                <label key={interest} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.interests.includes(interest)}
                    onChange={() => handleInterestToggle(interest)}
                    className="form-checkbox"
                  />
                  <span className="checkbox-text">{interest}</span>
                </label>
              ))}
            </div>
          </div>

          {/* 제출 버튼 */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className={`submit-button ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {loading ? (
                <>
                  <div className="loading-spinner"></div>
                  <span>AI가 여행 계획을 만들고 있습니다...</span>
                </>
              ) : (
                <>
                  <Search />
                  <span>여행 계획 생성하기</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* 사용 팁 */}
      <div className="tips-section">
        <h3 className="tips-title">💡 사용 팁</h3>
        <ul className="tips-list">
          <li className="tips-item">• 구체적인 지역명을 입력하면 더 정확한 계획을 받을 수 있습니다</li>
          <li className="tips-item">• 관심사를 선택하면 취향에 맞는 여행 코스가 추천됩니다</li>
          <li className="tips-item">• 예산을 설정하면 그에 맞는 숙박과 활동을 추천받을 수 있습니다</li>
        </ul>
      </div>
    </div>
  );
};

export default TripPlanner;
