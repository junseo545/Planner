import React, { useState, useRef, useEffect } from 'react';
import { Search, Calendar, DollarSign, Bed, ArrowRight, ArrowLeft } from 'lucide-react';
import axios from 'axios';
import { TripPlan, TripPlannerProps, TripFormData } from '../types';

const TripPlanner: React.FC<TripPlannerProps> = ({ onTripGenerated, loading, setLoading }): React.JSX.Element => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<TripFormData>({
    region: '',
    customRegion: '',
    guests: 2,
    companionType: '',
    travelStyle: '',
    budget: '보통',
    interests: [],
    rooms: 1,
    start_date: '',
    end_date: ''
  });

  // 자동완성을 위한 상태
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // 한국의 주요 도시/지역명 목록
  const regionSuggestions = [
    '강릉', '강원도', '거제', '거창', '경산', '경주', '고성', '공주', '과천', '광명', '광주', '구미', '군산', '김제', '김천', '김포', '나주', '남양주', '남원', '논산', '단양', '담양', '대구', '대전', '동두천', '동해', '마산', '목포', '문경', '밀양', '보령', '보성', '보은', '봉화', '부산', '부안', '부여', '부천', '사천', '삼척', '상주', '서산', '서울', '서천', '성남', '세종', '속초', '수원', '순천', '시흥', '아산', '안동', '안산', '안성', '안양', '양구', '양산', '양양', '양주', '양평', '여수', '여주', '연천', '영광', '영덕', '영동', '영암', '영양', '영월', '영주', '영천', '예산', '예천', '오산', '옥천', '완도', '완주', '용인', '울산', '울진', '원주', '음성', '의령', '의성', '의정부', '이천', '익산', '인천', '인제', '임실', '장성', '장수', '전주', '정선', '정읍', '제주', '제천', '조성', '주천', '증평', '진도', '진안', '진주', '진천', '창녕', '창원', '창원시', '천안', '철원', '청도', '청양', '청주', '춘천', '충주', '태백', '태안', '통영', '파주', '평창', '평택', '포천', '포항', '하남', '하동', '한산', '함양', '함평', '해남', '해주', '홍성', '홍천', '화성', '화순', '횡성'
  ];

  const companionTypeOptions = ['연인', '친구', '가족', '혼자', '동료', '기타'];

  const travelStyleOptions = [
    '자연 관광', '문화 체험', '맛집 탐방', '쇼핑', '액티비티', '휴양', '역사 탐방'
  ];

  // 자동완성 필터링 함수
  const filterSuggestions = (input: string) => {
    if (input.trim() === '') {
      return [];
    }
    return regionSuggestions.filter(region => 
      region.toLowerCase().includes(input.toLowerCase())
    ).slice(0, 10); // 최대 10개만 표시
  };

  // 입력값 변경 처리
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    
    if (name === 'customRegion') {
      setInputValue(value);
      const filtered = filterSuggestions(value);
      setFilteredSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
    setFormData((prev: TripFormData) => ({
      ...prev,
      [name]: name === 'guests' || name === 'rooms' ? parseInt(value) : value
    }));
    }
  };

  // 자동완성 선택 처리
  const handleSuggestionClick = (suggestion: string) => {
    setFormData((prev: TripFormData) => ({ ...prev, customRegion: suggestion }));
    setInputValue(suggestion);
    setShowSuggestions(false);
  };

  // 외부 클릭 시 자동완성 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleCustomRegionInput = (): void => {
    if (formData.customRegion.trim()) {
      setFormData((prev: TripFormData) => ({
        ...prev,
        region: formData.customRegion
      }));
      setCurrentStep(2);
    }
  };

  const handleGuestsSelect = (): void => {
    if (formData.guests >= 2) {
      setCurrentStep(3); // 동반자 유형 선택 단계로
    } else {
      setCurrentStep(4); // 여행 스타일 선택 단계로
    }
  };

  const handleCompanionTypeSelect = (): void => {
    setCurrentStep(4);
  };

  const handleTravelStyleSelect = (): void => {
    // 여행 스타일이 선택되었는지 확인
    if (formData.interests.length > 0) {
      setFormData((prev: TripFormData) => ({
        ...prev,
        travelStyle: formData.interests.join(', ')
      }));
      setCurrentStep(5);
    } else {
      alert('하나 이상의 여행 스타일을 선택해주세요.');
    }
  };

  const handleInterestToggle = (interest: string): void => {
    setFormData((prev: TripFormData) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((i: string) => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    
    if ((!formData.region && !formData.customRegion) || !formData.guests || !formData.travelStyle) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    setLoading(true);
    
    try {
      // 백엔드로 전송할 데이터 준비
      const submitData = {
        destination: formData.region || formData.customRegion,
        guests: formData.guests,
        companionType: formData.companionType,
        travelStyle: formData.travelStyle,
        budget: formData.budget,
        interests: formData.interests,
        rooms: formData.rooms,
        start_date: formData.start_date,
        end_date: formData.end_date
      };

      // 환경에 따른 API URL 설정
      const apiUrl = process.env.NODE_ENV === 'production' 
        ? 'https://trip-planner-backend.onrender.com/plan-trip'
        : 'http://localhost:8000/plan-trip';
      
      const response = await axios.post<TripPlan>(apiUrl, submitData);
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
      <h3 className="step-title">어떤 지역으로 여행하시나요?</h3>
      
      <div className="region-input-section">
        <p className="region-input-label">여행하고 싶은 지역을 입력해주세요</p>
        <div className="region-input-container">
          <input
            type="text"
            name="customRegion"
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => setShowSuggestions(true)}
            placeholder="예: 강원도 속초, 서울, 부산 등"
            className="region-input"
          />
          {showSuggestions && (
            <div ref={suggestionsRef} className="region-suggestions">
              {filteredSuggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="suggestion-item"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </div>
              ))}
            </div>
          )}
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

  const renderStep2 = (): JSX.Element => (
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

  const renderStep3 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">누구와 함께 여행하시나요?</h3>
      <div className="companion-options-grid">
        {companionTypeOptions.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => {
              setFormData((prev: TripFormData) => ({ ...prev, companionType: option }));
            }}
            className={`companion-option ${formData.companionType === option ? 'selected' : ''}`}
          >
            <span className="companion-text">{option}</span>
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={handleCompanionTypeSelect}
        disabled={!formData.companionType}
        className="next-button"
      >
        다음 <ArrowRight />
      </button>
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
              {step === 1 && '지역 선택'}
              {step === 2 && '인원수'}
              {step === 3 && '동반자 유형'}
              {step === 4 && '여행 스타일'}
              {step === 5 && '추가 정보'}
            </span>
          </div>
        ))}
      </div>

      {/* 현재 선택된 정보 요약 */}
      {currentStep > 1 && (
        <div className="selection-summary">
          {getDestination() && (
            <div className="summary-item">
              <strong>선택 지역:</strong> {getDestination()}
            </div>
          )}
          {currentStep >= 2 && formData.guests > 0 && (
             <div className="summary-item">
               <strong>인원수:</strong> {formData.guests}명
             </div>
          )}
          {currentStep >= 3 && formData.companionType && (
            <div className="summary-item">
              <strong>동반자:</strong> {formData.companionType}
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
