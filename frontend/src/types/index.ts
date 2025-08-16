export interface HotelInfo {
  name: string;
  type: string;
  price_range: string;
  booking_links: {
    [key: string]: {
      name: string;
      url: string;
      icon: string;
    };
  };
  description: string;
  rating?: number;
  amenities?: string[];
  location?: string;
}

export interface TripPlan {
  destination: string;
  duration: string;
  itinerary: Array<{
    day: number;
    date: string;
    morning: string;
    afternoon: string;
    evening: string;
    accommodation: string;
  }>;
  events?: Array<{
    name: string;
    date: string;
    description: string;
    location: string;
    type: string;
    website?: string;
    ticket_info?: string;
  }>;
  accommodation: HotelInfo[];
  total_cost: string;
  tips: string[];
}

export interface FormData {
  destination: string;
  start_date: string;
  end_date: string;
  budget: string;
  interests: string[];
  guests: number;
  rooms: number;
}

export interface TripPlannerProps {
  onTripGenerated: (plan: TripPlan) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export interface TripResultProps {
  tripPlan: TripPlan;
  onReset: () => void;
}
