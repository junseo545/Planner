import React, { useState } from 'react';
import { Star, ThumbsUp, ThumbsDown, Send, X } from 'lucide-react';
import { FeedbackFormProps, FeedbackData } from '../types';

const FeedbackForm: React.FC<FeedbackFormProps> = ({ onSubmit, onCancel }) => {
  const [rating, setRating] = useState(0);
  const [positivePoints, setPositivePoints] = useState('');
  const [negativePoints, setNegativePoints] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (rating === 0) {
      alert('별점을 선택해주세요.');
      return;
    }

    setIsSubmitting(true);
    
    try {
      const feedbackData: FeedbackData = {
        rating,
        positivePoints: positivePoints.trim(),
        negativePoints: negativePoints.trim(),
        timestamp: new Date().toISOString()
      };

      await onSubmit(feedbackData);
      
      // 폼 초기화
      setRating(0);
      setPositivePoints('');
      setNegativePoints('');
    } catch (error) {
      console.error('피드백 제출 오류:', error);
      alert('피드백 제출 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  return (
    <div className="feedback-form-container">
      <div className="feedback-form-header">
        <h2 className="feedback-form-title">정성데이터 수집</h2>
        {onCancel && (
          <button 
            onClick={handleCancel}
            className="feedback-close-button"
            type="button"
          >
            <X size={20} />
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="feedback-form">
        {/* 만족도 평가 */}
        <div className="feedback-section">
          <h3 className="feedback-question">
            이번 여행 일정 추천이 얼마나 만족스러우셨나요?
          </h3>
          <div className="rating-container">
            <span className="rating-label">별점 0-5</span>
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  className={`star-button ${star <= rating ? 'active' : ''}`}
                  onClick={() => setRating(star)}
                  disabled={isSubmitting}
                >
                  <Star 
                    size={32} 
                    fill={star <= rating ? '#fbbf24' : 'none'}
                    stroke={star <= rating ? '#f59e0b' : '#d1d5db'}
                  />
                </button>
              ))}
            </div>
            {rating > 0 && (
              <span className="rating-text">
                {rating}점을 선택하셨습니다 ⭐
              </span>
            )}
          </div>
        </div>

        {/* 긍정 포인트 */}
        <div className="feedback-section">
          <h3 className="feedback-question">
            <ThumbsUp className="feedback-icon positive" />
            "무엇이 가장 도움이 되었나요?"
          </h3>
          <p className="feedback-example">
            (예: 일정 자동 생성, 교통·숙소 추천, 시간 절약 등)
          </p>
          <textarea
            value={positivePoints}
            onChange={(e) => setPositivePoints(e.target.value)}
            placeholder="만족했던 점을 자유롭게 작성해주세요..."
            className="feedback-textarea"
            rows={3}
            disabled={isSubmitting}
          />
        </div>

        {/* 부정 포인트 */}
        <div className="feedback-section">
          <h3 className="feedback-question">
            <ThumbsDown className="feedback-icon negative" />
            "개선되면 좋을 점이 있나요?"
          </h3>
          <p className="feedback-example">
            (예: 더 다양한 장소 추천, 예산 옵션 추가, UI 개선 등)
          </p>
          <textarea
            value={negativePoints}
            onChange={(e) => setNegativePoints(e.target.value)}
            placeholder="개선사항을 자유롭게 작성해주세요..."
            className="feedback-textarea"
            rows={3}
            disabled={isSubmitting}
          />
        </div>

        {/* 제출 버튼 */}
        <div className="feedback-actions">
          <button
            type="submit"
            className="feedback-submit-button"
            disabled={isSubmitting || rating === 0}
          >
            {isSubmitting ? (
              <>
                <div className="spinner" />
                제출 중...
              </>
            ) : (
              <>
                <Send size={18} />
                평가 완료하기
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default FeedbackForm;
