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
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          당신만의 맞춤 여행 계획을 만들어보세요
        </h2>
        <p className="text-lg text-gray-600">
          AI가 추천하는 최적의 여행 코스와 숙박 정보를 제공합니다
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 목적지 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <MapPin className="inline h-4 w-4 mr-2" />
              여행하고 싶은 지역
            </label>
            <input
              type="text"
              name="destination"
              value={formData.destination}
              onChange={handleInputChange}
              placeholder="예: 제주도, 부산, 도쿄, 파리..."
              className="input-field"
              required
            />
          </div>

          {/* 날짜 선택 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="inline h-4 w-4 mr-2" />
                출발일
              </label>
              <input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleInputChange}
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="inline h-4 w-4 mr-2" />
                도착일
              </label>
              <input
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleInputChange}
                className="input-field"
                required
              />
            </div>
          </div>

          {/* 예산 선택 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <DollarSign className="inline h-4 w-4 mr-2" />
              예산
            </label>
            <select
              name="budget"
              value={formData.budget}
              onChange={handleInputChange}
              className="input-field"
            >
              <option value="저예산">저예산</option>
              <option value="보통">보통</option>
              <option value="고급">고급</option>
              <option value="럭셔리">럭셔리</option>
            </select>
          </div>

          {/* 투숙객 및 객실 수 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Users className="inline h-4 w-4 mr-2" />
                투숙객 수
              </label>
              <select
                name="guests"
                value={formData.guests}
                onChange={handleInputChange}
                className="input-field"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                  <option key={num} value={num}>{num}명</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Bed className="inline h-4 w-4 mr-2" />
                객실 수
              </label>
              <select
                name="rooms"
                value={formData.rooms}
                onChange={handleInputChange}
                className="input-field"
              >
                {[1, 2, 3, 4, 5].map(num => (
                  <option key={num} value={num}>{num}개</option>
                ))}
              </select>
            </div>
          </div>

          {/* 관심사 선택 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Heart className="inline h-4 w-4 mr-2" />
              관심사 (선택사항)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {interestOptions.map((interest) => (
                <label key={interest} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.interests.includes(interest)}
                    onChange={() => handleInterestToggle(interest)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">{interest}</span>
                </label>
              ))}
            </div>
          </div>

          {/* 제출 버튼 */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className={`w-full btn-primary flex items-center justify-center space-x-2 ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>AI가 여행 계획을 만들고 있습니다...</span>
                </>
              ) : (
                <>
                  <Search className="h-5 w-5" />
                  <span>여행 계획 생성하기</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* 사용 팁 */}
      <div className="mt-8 p-6 bg-blue-50 rounded-xl border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">💡 사용 팁</h3>
        <ul className="text-blue-800 space-y-2 text-sm">
          <li>• 구체적인 지역명을 입력하면 더 정확한 계획을 받을 수 있습니다</li>
          <li>• 관심사를 선택하면 취향에 맞는 여행 코스가 추천됩니다</li>
          <li>• 예산을 설정하면 그에 맞는 숙박과 활동을 추천받을 수 있습니다</li>
        </ul>
      </div>
    </div>
  );
};

export default TripPlanner;
