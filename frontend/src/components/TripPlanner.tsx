import React, { useState } from 'react';
import { Search, Calendar, MapPin, DollarSign, Heart, Users, Bed, ArrowRight, ArrowLeft } from 'lucide-react';
import axios from 'axios';
import { TripPlan, TripPlannerProps, FormData } from '../types';

const TripPlanner: React.FC<TripPlannerProps> = ({ onTripGenerated, loading, setLoading }): JSX.Element => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    tripType: '',
    region: '',
    customRegion: '',
    guests: 2,
    travelStyle: '',
    budget: '보통',
    interests: [],
    rooms: 1,
    start_date: '',
    end_date: ''
  });

  const tripTypeOptions = ['도시', '촌캉스'];
  
  const regionOptions = {
    '도시': ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '제주도'],
    '촌캉스': ['강원도', '충청북도', '충청남도', '전라북도', '전라남도', '경상북도', '경상남도', '제주도']
  };

  const travelStyleOptions = [
    '자연 관광', '문화 체험', '맛집 탐방', '쇼핑', '액티비티', '휴양', '역사 탐방'
  ];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'guests' || name === 'rooms' ? parseInt(value) : value
    }));
  };

  const handleTripTypeSelect = (tripType: string): void => {
    setFormData(prev => ({
      ...prev,
      tripType,
      region: '',
      customRegion: ''
    }));
    setCurrentStep(2);
  };

  const handleCustomRegionInput = (): void => {
    if (formData.customRegion.trim()) {
      setFormData(prev => ({
        ...prev,
        region: formData.customRegion
      }));
      setCurrentStep(3);
    }
  };

  const handleGuestsSelect = (): void => {
    setCurrentStep(4);
  };

  const handleTravelStyleSelect = (): void => {
    // 여행 스타일이 선택되었는지 확인
    if (formData.interests.length > 0) {
      setFormData(prev => ({
        ...prev,
        travelStyle: formData.interests.join(', ')
      }));
      setCurrentStep(5);
    } else {
      alert('하나 이상의 여행 스타일을 선택해주세요.');
    }
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
    
    if (!formData.tripType || (!formData.region && !formData.customRegion) || !formData.guests || !formData.travelStyle) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    setLoading(true);
    
    try {
      // 백엔드로 전송할 데이터 준비
      const submitData = {
        destination: formData.region || formData.customRegion,
        tripType: formData.tripType,
        guests: formData.guests,
        travelStyle: formData.travelStyle,
        budget: formData.budget,
        interests: formData.interests,
        rooms: formData.rooms,
        start_date: formData.start_date,
        end_date: formData.end_date
      };

      const response = await axios.post<TripPlan>('http://localhost:8000/plan-trip', submitData);
      onTripGenerated(response.data);
    } catch (error) {
      console.error('여행 계획 생성 오류:', error);
      alert('여행 계획 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const goBack = (): void => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const getDestination = (): string => {
    return formData.customRegion || formData.region || '';
  };

  const renderStep1 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">어떤 여행을 계획하시나요?</h3>
      <div className="options-grid">
        {tripTypeOptions.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => handleTripTypeSelect(option)}
            className="option-button"
          >
            <div className="option-icon">
              {option === '도시' ? <MapPin /> : <Heart />}
            </div>
            <span className="option-text">{option}</span>
            <ArrowRight className="option-arrow" />
          </button>
        ))}
      </div>
    </div>
  );

  const renderStep2 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">어떤 지역으로 여행하시나요?</h3>
      
      <div className="region-input-section">
        <p className="region-input-label">여행하고 싶은 지역을 입력해주세요</p>
        <div className="region-input-container">
          <input
            type="text"
            name="customRegion"
            value={formData.customRegion}
            onChange={handleInputChange}
            placeholder="예: 강릉, 청주, 제주도, 속초 등"
            className="region-input"
          />
          <button
            type="button"
            onClick={handleCustomRegionInput}
            disabled={!formData.customRegion.trim()}
            className="region-input-button"
          >
            다음
          </button>
        </div>
        <p className="region-input-hint">
          도시명, 지역명, 또는 "강원도 속초" 같은 형태로 입력하세요
        </p>
      </div>
    </div>
  );

  const renderStep3 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">몇 명이서 여행하시나요?</h3>
      <div className="guests-selection">
        <select
          name="guests"
          value={formData.guests}
          onChange={handleInputChange}
          className="guests-select"
        >
          {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
            <option key={num} value={num}>{num}명</option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleGuestsSelect}
          className="next-button"
        >
          다음 <ArrowRight />
        </button>
      </div>
    </div>
  );

  const renderStep4 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">어떤 여행 스타일을 선호하시나요?</h3>
      <div className="travel-style-grid">
        {travelStyleOptions.map((style) => (
          <label key={style} className="style-checkbox-label">
            <input
              type="checkbox"
              checked={formData.interests.includes(style)}
              onChange={() => handleInterestToggle(style)}
              className="style-checkbox"
            />
            <span className="style-text">{style}</span>
          </label>
        ))}
      </div>
      <button
        type="button"
        onClick={handleTravelStyleSelect}
        className="next-button"
      >
        다음 <ArrowRight />
      </button>
    </div>
  );

  const renderStep5 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">추가 정보를 입력해주세요</h3>
      
      <div className="additional-info-form">
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
          />
        </div>
      </div>

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
  );

  return (
    <div className="planner-container">
      <div className="planner-header">
        <h2 className="planner-title">
          국내여행 플래너
        </h2>
        <p className="planner-subtitle">
          단계별로 선택하여 맞춤 여행 계획을 만들어보세요
        </p>
      </div>

      {/* 진행 단계 표시 */}
      <div className="progress-bar">
        {[1, 2, 3, 4, 5].map((step) => (
          <div
            key={step}
            className={`progress-step ${currentStep >= step ? 'active' : ''} ${currentStep === step ? 'current' : ''}`}
          >
            <span className="progress-number">{step}</span>
            <span className="progress-label">
              {step === 1 && '여행 유형'}
              {step === 2 && '지역 선택'}
              {step === 3 && '인원수'}
              {step === 4 && '여행 스타일'}
              {step === 5 && '추가 정보'}
            </span>
          </div>
        ))}
      </div>

      {/* 현재 선택된 정보 요약 */}
      {currentStep > 1 && (
        <div className="selection-summary">
          <div className="summary-item">
            <strong>여행 유형:</strong> {formData.tripType}
          </div>
          {getDestination() && (
            <div className="summary-item">
              <strong>선택 지역:</strong> {getDestination()}
            </div>
          )}
                     {currentStep >= 3 && formData.guests > 0 && (
             <div className="summary-item">
               <strong>인원수:</strong> {formData.guests}명
             </div>
           )}
                     {currentStep >= 4 && formData.interests.length > 0 && (
             <div className="summary-item">
               <strong>여행 스타일:</strong> {formData.interests.join(', ')}
             </div>
           )}
        </div>
      )}

      {/* 뒤로가기 버튼 */}
      {currentStep > 1 && (
        <button
          type="button"
          onClick={goBack}
          className="back-button"
        >
          <ArrowLeft />
          뒤로가기
        </button>
      )}

      {/* 단계별 폼 */}
      <div className="planner-form">
        <form onSubmit={handleSubmit}>
          {currentStep === 1 && renderStep1()}
          {currentStep === 2 && renderStep2()}
          {currentStep === 3 && renderStep3()}
          {currentStep === 4 && renderStep4()}
          {currentStep === 5 && renderStep5()}
        </form>
      </div>
    </div>
  );
};

export default TripPlanner;
