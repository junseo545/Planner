import { supabase } from './supabase.js'

export interface FeedbackData {
  rating: number
  positivePoints: string
  negativePoints: string
  tripId?: string
  destination?: string
  duration?: string
  timestamp?: string
}

export const saveFeedbackToSupabase = async (feedback: FeedbackData): Promise<{ success: boolean; error?: string }> => {
  try {
    const { data, error } = await supabase
      .from('Feedback')
      .insert([
        {
          rating: feedback.rating,
          positive_feedback: feedback.positivePoints,
          negative_feedback: feedback.negativePoints,
          created_at: feedback.timestamp || new Date().toISOString()
        }
      ])

    if (error) {
      console.error('Supabase error:', error)
      return { success: false, error: error.message }
    }

    return { success: true }
  } catch (error) {
    console.error('Feedback save error:', error)
    return { success: false, error: 'Failed to save feedback' }
  }
}
