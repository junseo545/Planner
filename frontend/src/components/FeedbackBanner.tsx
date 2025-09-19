import React, { useState, useEffect } from 'react';
import { MessageSquare, X, Star } from 'lucide-react';
import FeedbackForm from './FeedbackForm';
import { FeedbackData } from '../types';
import { analyticsEvents } from '../utils/analytics';
import '../styles/FeedbackBanner.css';

interface FeedbackBannerProps {
  onSubmit: (data: FeedbackData) => Promise<void>;
  onCancel?: () => void;
}

const FeedbackBanner: React.FC<FeedbackBannerProps> = ({ onSubmit, onCancel }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // 배너가 표시될 때 analytics 이벤트 발생
  useEffect(() => {
    analyticsEvents.feedbackBannerShown();
  }, []);

  const handleBannerClick = () => {
    if (!isSubmitted) {
      setIsExpanded(true);
      analyticsEvents.feedbackBannerClicked();
      analyticsEvents.feedbackFormOpened();
    }
  };

  const handleFeedbackSubmit = async (data: FeedbackData) => {
    try {
      await onSubmit(data);
      setIsSubmitted(true);
      analyticsEvents.feedbackSubmitted(
        data.rating,
        data.positivePoints.trim().length > 0,
        data.negativePoints.trim().length > 0
      );
    } catch (error) {
      console.error('피드백 제출 오류:', error);
      throw error;
    }
  };

  const handleClose = () => {
    setIsExpanded(false);
    if (onCancel) {
      onCancel();
    }
    analyticsEvents.feedbackFormClosed();
  };

  const handleDismiss = () => {
    setIsSubmitted(true);
    analyticsEvents.feedbackBannerDismissed();
  };

  if (isSubmitted) {
    return null; // 제출 완료 후 배너 숨김
  }

  return (
    <>
      {/* 하단 고정 배너 */}
      <div className="feedback-banner" onClick={handleBannerClick}>
        <div className="feedback-banner-content">
          <div className="feedback-banner-icon">
            <MessageSquare size={20} />
          </div>
          <div className="feedback-banner-text">
            <div className="feedback-banner-title">여행 계획이 도움이 되셨나요?</div>
            <div className="feedback-banner-subtitle">
              소중한 피드백을 주시면 더 나은 서비스를 제공할 수 있습니다.
            </div>
          </div>
          <div className="feedback-banner-actions">
            <button 
              className="feedback-banner-button"
              onClick={(e) => {
                e.stopPropagation();
                handleBannerClick();
              }}
            >
              <Star size={16} />
              평가하기
            </button>
            <button 
              className="feedback-banner-dismiss"
              onClick={(e) => {
                e.stopPropagation();
                handleDismiss();
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* 확장된 피드백 폼 */}
      {isExpanded && (
        <div className="feedback-overlay">
          <div className="feedback-modal">
            <FeedbackForm 
              onSubmit={handleFeedbackSubmit}
              onCancel={handleClose}
            />
          </div>
        </div>
      )}
    </>
  );
};

export default FeedbackBanner;
