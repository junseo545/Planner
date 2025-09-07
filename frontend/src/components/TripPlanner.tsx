import React, { useState, useRef, useEffect } from 'react';
import { Search, Calendar, Bed, ArrowRight, ArrowLeft, Car } from 'lucide-react';
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
    travelPace: '',
    budget: '보통',
    interests: [],
    rooms: 1,
    transportation: '자동차',
    start_date: '',
    end_date: ''
  });

  // 진행 상황 관련 상태
  const [progressStep, setProgressStep] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [progressPercent, setProgressPercent] = useState(0);

  // 컴포넌트 마운트 시 저장된 폼 데이터와 단계 복원
  useEffect(() => {
    try {
      const savedFormData = sessionStorage.getItem('tripPlannerFormData');
      const savedCurrentStep = sessionStorage.getItem('tripPlannerCurrentStep');
      
      if (savedFormData) {
        const parsedFormData = JSON.parse(savedFormData);
        setFormData(parsedFormData);
        setInputValue(parsedFormData.customRegion || '');
        console.log('Restored form data from session storage');
      }
      
      if (savedCurrentStep) {
        const step = parseInt(savedCurrentStep, 10);
        if (step >= 1 && step <= 6) {
          setCurrentStep(step);
          console.log(`Restored current step: ${step}`);
        }
      }
    } catch (error) {
      console.error('Error restoring trip planner state:', error);
      // 오류 발생 시 저장된 데이터 삭제
      sessionStorage.removeItem('tripPlannerFormData');
      sessionStorage.removeItem('tripPlannerCurrentStep');
    }
  }, []);

  // 폼 데이터가 변경될 때마다 저장
  useEffect(() => {
    try {
      sessionStorage.setItem('tripPlannerFormData', JSON.stringify(formData));
    } catch (error) {
      console.error('Error saving form data:', error);
    }
  }, [formData]);

  // 현재 단계가 변경될 때마다 저장
  useEffect(() => {
    try {
      sessionStorage.setItem('tripPlannerCurrentStep', currentStep.toString());
    } catch (error) {
      console.error('Error saving current step:', error);
    }
  }, [currentStep]);

  // 자동완성을 위한 상태
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // 한국의 주요 도시/지역명 목록 (섬 지역 포함)
  const regionSuggestions = [
    '강릉', '강원도', '거제', '거창', '경산', '경주', '고성', '공주', '과천', '광명', '광주', '구미', '군산', '김제', '김천', '김포', '나주', '남양주', '남원', '논산', '단양', '담양', '대구', '대전', '동두천', '동해', '마산', '목포', '문경', '밀양', '보령', '보성', '보은', '봉화', '부산', '부안', '부여', '부천', '사천', '삼척', '상주', '서산', '서울', '서천', '성남', '세종', '속초', '수원', '순천', '시흥', '아산', '안동', '안산', '안성', '안양', '양구', '양산', '양양', '양주', '양평', '여수', '여주', '연천', '영광', '영덕', '영동', '영암', '영양', '영월', '영주', '영천', '예산', '예천', '오산', '옥천', '완도', '완주', '용인', '울산', '울진', '원주', '음성', '의령', '의성', '의정부', '이천', '익산', '인천', '인제', '임실', '장성', '장수', '전주', '정선', '정읍', '제주', '제천', '조성', '주천', '증평', '진도', '진안', '진주', '진천', '창녕', '창원', '창원시', '천안', '철원', '청도', '청양', '청주', '춘천', '충주', '태백', '태안', '통영', '파주', '평창', '평택', '포천', '포항', '하남', '하동', '한산', '함양', '함평', '해남', '해주', '홍성', '홍천', '화성', '화순', '횡성',
    // 섬 지역 추가
    '대부도', '제부도', '영종도', '강화도', '교동도', '백령도', '연평도', '옹진', '덕적도', '자월도', '선재도', '승봉도', '신시모도', '팔미도', '월미도', '용유도', '삼목도'
  ];

  const companionTypeOptions = ['연인', '친구', '가족', '동료', '기타'];

  const travelStyleOptions = [
    '자연 관광', '문화 체험', '쇼핑', '액티비티', '휴양', '역사 탐방'
  ];

  const travelPaceOptions = [
    { value: '타이트하게', label: '타이트하게', description: '알차게 많은 곳을 둘러보고 싶어요' },
    { value: '널널하게', label: '널널하게', description: '여유롭게 천천히 즐기고 싶어요' }
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

  // 날짜 유효성 검사 함수
  const getMaxEndDate = (startDate: string): string => {
    if (!startDate) return '';
    const start = new Date(startDate);
    const maxEnd = new Date(start);
    maxEnd.setDate(start.getDate() + 4); // 최대 4박 5일
    return maxEnd.toISOString().split('T')[0];
  };

  const getMinEndDate = (startDate: string): string => {
    if (!startDate) return '';
    const start = new Date(startDate);
    const minEnd = new Date(start);
    minEnd.setDate(start.getDate() + 1); // 최소 1박 2일
    return minEnd.toISOString().split('T')[0];
  };

  // 입력값 변경 처리
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = e.target;
    
    if (name === 'customRegion') {
      setInputValue(value);
      const filtered = filterSuggestions(value);
      setFilteredSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else if (name === 'start_date') {
      setFormData((prev: TripFormData) => ({
        ...prev,
        start_date: value,
        end_date: '' // 시작일이 변경되면 종료일 초기화
      }));
    } else {
      setFormData((prev: TripFormData) => ({
        ...prev,
        [name]: name === 'guests' || name === 'rooms' ? parseInt(value) : value
      }));
    }
  };

  // 자동완성 선택 처리
  const handleSuggestionClick = (suggestion: string) => {
    setFormData((prev: TripFormData) => ({ ...prev, customRegion: suggestion, region: suggestion }));
    setInputValue(suggestion);
    setShowSuggestions(false);
    // 지역 선택 후 자동으로 다음 단계로 이동
    setCurrentStep(2);
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





  const handleGuestsSelect = (): void => {
    if (formData.guests >= 2) {
      setCurrentStep(3); // 동반자 유형 선택 단계로
    } else {
      // 혼자 여행하는 경우 companionType을 '혼자'로 자동 설정하고 4단계로 이동
      setFormData((prev: TripFormData) => ({ ...prev, companionType: '혼자' }));
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

  const handleTravelPaceOptionClick = (pace: string): void => {
    setFormData(prev => ({ ...prev, travelPace: pace }));
    setCurrentStep(6);
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
    
    // 기본 필드 검증
    if ((!formData.region && !formData.customRegion) || !formData.guests || !formData.travelStyle) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    // 날짜 검증
    if (!formData.start_date) {
      alert('여행 시작일을 선택해주세요.');
      return;
    }

    if (!formData.end_date) {
      alert('여행 종료일을 선택해주세요.');
      return;
    }

    // 날짜 논리 검증
    const startDate = new Date(formData.start_date);
    const endDate = new Date(formData.end_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (startDate < today) {
      alert('여행 시작일은 오늘 이후 날짜여야 합니다.');
      return;
    }

    if (startDate >= endDate) {
      alert('여행 시작일은 종료일보다 이전이어야 합니다.');
      return;
    }

    const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    if (daysDiff > 4) {
      alert('여행 기간은 최대 4박 5일까지 가능합니다.');
      return;
    }

    setLoading(true);
    setProgressStep(0);
    setProgressMessage('여행 계획 생성을 시작합니다...');
    setProgressPercent(0);
    
    try {
      // 백엔드로 전송할 데이터 준비
      const submitData = {
        destination: formData.region || formData.customRegion,
        guests: formData.guests,
        companionType: formData.companionType,
        travelStyle: formData.travelStyle,
        travelPace: formData.travelPace,
        budget: formData.budget,
        interests: formData.interests,
        rooms: formData.rooms,
        transportation: formData.transportation,
        start_date: formData.start_date,
        end_date: formData.end_date
      };

      // 환경에 따른 API URL 설정
      const baseUrl = import.meta.env.PROD 
        ? 'https://planner-backend-3bcz.onrender.com'
        : 'http://localhost:8000';
      
      const progressUrl = `${baseUrl}/plan-trip-progress?destination=${encodeURIComponent(submitData.destination)}&start_date=${submitData.start_date}&end_date=${submitData.end_date}&budget=${encodeURIComponent(submitData.budget)}&guests=${submitData.guests}&rooms=${submitData.rooms}`;
      const planUrl = `${baseUrl}/plan-trip`;
      
      console.log('전송할 데이터:', submitData);
      console.log('Progress URL:', progressUrl);
      console.log('Plan URL:', planUrl);
      
      // SSE로 진행 상황 받기
      const eventSource = new EventSource(progressUrl);
      
      // 8초 후에 자동으로 실제 API 호출 시작 (SSE가 끊어져도 진행)
      const progressTimeout = setTimeout(() => {
        eventSource.close();
        setProgressMessage('여행 계획을 최종 완성하고 있습니다...');
        setProgressPercent(85);
        generateTripPlan(submitData, planUrl);
      }, 8000);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.step) {
            setProgressStep(data.step);
            setProgressMessage(data.message);
            setProgressPercent(data.progress);
          }
          
          if (data.completed) {
            clearTimeout(progressTimeout);
            eventSource.close();
            // 진행 상황이 완료되면 실제 여행 계획 요청
            setProgressMessage('여행 계획을 최종 완성하고 있습니다...');
            generateTripPlan(submitData, planUrl);
          }
          
          if (data.error) {
            clearTimeout(progressTimeout);
            eventSource.close();
            console.error('Progress error:', data.error);
            setLoading(false);
            alert('여행 계획 생성 중 오류가 발생했습니다.');
          }
        } catch (error) {
          console.error('Progress parsing error:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        clearTimeout(progressTimeout);
        eventSource.close();
        // 진행 상황 실패 시에도 여행 계획은 생성 시도
        setProgressMessage('진행 상황 연결이 끊어졌습니다. 여행 계획을 계속 생성합니다...');
        setProgressPercent(85);
        generateTripPlan(submitData, planUrl);
      };
      
    } catch (error: any) {
      console.error('여행 계획 생성 오류:', error);
      setLoading(false);
      alert('여행 계획 생성 중 오류가 발생했습니다.');
    }
  };

  const generateTripPlan = async (submitData: any, planUrl: string) => {
    let progressInterval: NodeJS.Timeout | null = null;
    
    try {
      // 실제 API 호출 시작
      setProgressMessage('AI가 최종 여행 계획을 완성하고 있습니다...');
      setProgressPercent(88);
      
      // 점진적 진행률 시뮬레이션
      progressInterval = setInterval(() => {
        setProgressPercent(prev => {
          if (prev < 98) {
            return prev + 1;
          }
          return prev;
        });
      }, 800); // 0.8초마다 1%씩 증가
      
      const response = await axios.post<TripPlan>(planUrl, submitData);
      
      // API 완료 시 인터벌 정리하고 100% 완료
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setProgressMessage('여행 계획이 완성되었습니다!');
      setProgressPercent(100);
      
      // 잠시 100% 상태를 보여준 후 완료
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // 여행 계획 생성 성공 시 플래너 데이터 삭제
      sessionStorage.removeItem('tripPlannerFormData');
      sessionStorage.removeItem('tripPlannerCurrentStep');
      console.log('Cleared trip planner data after successful generation');
      
      onTripGenerated(response.data);
    } catch (error: any) {
      console.error('여행 계획 생성 오류:', error);
      
      // 에러 발생 시에도 인터벌 정리
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      console.error('오류 상세:', error.response?.data);
      console.error('HTTP 상태:', error.response?.status);
      
      let errorMessage = '여행 계획 생성 중 오류가 발생했습니다.';
      
      if (error.response?.status === 500) {
        errorMessage = '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else if (error.response?.data?.detail) {
        errorMessage = `오류: ${error.response.data.detail}`;
      }
      
      alert(errorMessage);
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
        </div>
        <p className="region-input-hint">
          지역명을 입력하면 추천 목록이 나타납니다. 목록에서 선택하세요
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
      <h3 className="step-title">어떤 여행 페이스를 선호하시나요?</h3>
      <div className="pace-options-grid">
        {travelPaceOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => handleTravelPaceOptionClick(option.value)}
            className={`pace-option ${formData.travelPace === option.value ? 'selected' : ''}`}
          >
            <span className="pace-title">{option.label}</span>
            <span className="pace-description">{option.description}</span>
          </button>
        ))}
      </div>
    </div>
  );

  const renderStep6 = (): JSX.Element => (
    <div className="step-container">
      <h3 className="step-title">추가 정보를 입력해주세요</h3>
      
      <div className="additional-info-form">
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
            <Car />
            교통수단
          </label>
          <select
            name="transportation"
            value={formData.transportation}
            onChange={handleInputChange}
            className="form-select"
          >
            <option value="자동차">자동차</option>
            <option value="대중교통">대중교통</option>
            <option value="기차">기차</option>
            <option value="비행기">비행기</option>
            <option value="렌터카">렌터카</option>
            <option value="도보/자전거">도보/자전거</option>
          </select>
        </div>

        <div className="form-section">
          <label className="form-label">
            <Calendar />
            여행 시작일
          </label>
          <input
            type="date"
            name="start_date"
            value={formData.start_date}
            onChange={handleInputChange}
            className="form-input"
            min={new Date().toISOString().split('T')[0]}
            required
          />
        </div>

        <div className="form-section">
          <label className="form-label">
            <Calendar />
            여행 종료일 <span className="date-hint">(최대 4박 5일)</span>
          </label>
          <input
            type="date"
            name="end_date"
            value={formData.end_date}
            onChange={handleInputChange}
            className="form-input"
            min={getMinEndDate(formData.start_date)}
            max={getMaxEndDate(formData.start_date)}
            disabled={!formData.start_date}
            required
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || !formData.start_date || !formData.end_date}
        className={`submit-button ${(loading || !formData.start_date || !formData.end_date) ? 'opacity-50 cursor-not-allowed' : ''}`}
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
      {loading ? (
        <div className="progress-container">
          <div className="planner-header">
            <h2 className="planner-title">
              여행 계획 생성중
            </h2>
            <p className="planner-subtitle">
              AI가 맞춤형 여행 계획을 생성하고 있습니다
            </p>
          </div>
          
          <div className="generation-progress">
            <div className="progress-info">
              <div className="progress-step-indicator">
                <span className="step-number">{progressStep}/7</span>
                <span className="step-message">{progressMessage}</span>
              </div>
              
              <div className="progress-bar-container">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${progressPercent}%` }}
                ></div>
              </div>
              
              <div className="progress-percentage">
                {progressPercent}%
              </div>
            </div>
            
            {/* 단계별 상세 내용은 숨김 - 게이지만 표시 */}
          </div>
        </div>
      ) : (
        <>
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
        {(() => {
          // 혼자 여행하는 경우 동반자 유형 단계를 제외
          const isSoloTravel = formData.guests === 1;
          const steps = isSoloTravel 
            ? [
                { num: 1, label: '지역 선택' },
                { num: 2, label: '인원수' },
                { num: 3, label: '여행 스타일' },
                { num: 4, label: '여행 페이스' },
                { num: 5, label: '추가 정보' }
              ]
            : [
                { num: 1, label: '지역 선택' },
                { num: 2, label: '인원수' },
                { num: 3, label: '동반자 유형' },
                { num: 4, label: '여행 스타일' },
                { num: 5, label: '여행 페이스' },
                { num: 6, label: '추가 정보' }
              ];
          
          return steps.map((step) => {
            // 혼자 여행인 경우 currentStep 조정
            let adjustedCurrentStep = currentStep;
            if (isSoloTravel && currentStep > 2) {
              adjustedCurrentStep = currentStep - 1;
            }
            
            return (
              <div
                key={step.num}
                className={`progress-step ${adjustedCurrentStep >= step.num ? 'active' : ''} ${adjustedCurrentStep === step.num ? 'current' : ''}`}
              >
                <span className="progress-number">{step.num}</span>
                <span className="progress-label">{step.label}</span>
          </div>
            );
          });
        })()}
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
          {currentStep >= 3 && formData.companionType && formData.guests > 1 && (
            <div className="summary-item">
              <strong>동반자:</strong> {formData.companionType}
            </div>
           )}
           {formData.guests === 1 && formData.companionType === '혼자' && (
            <div className="summary-item">
              <strong>여행 유형:</strong> 혼자 여행
            </div>
           )}
                     {currentStep >= 4 && formData.interests.length > 0 && (
             <div className="summary-item">
               <strong>여행 스타일:</strong> {formData.interests.join(', ')}
             </div>
           )}
           {currentStep >= 5 && formData.travelPace && (
             <div className="summary-item">
               <strong>여행 페이스:</strong> {formData.travelPace}
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
          {currentStep === 6 && renderStep6()}
        </form>
      </div>
        </>
      )}
    </div>
  );
};

export default TripPlanner;
