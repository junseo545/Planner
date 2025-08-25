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
  transport_info?: {
    city: string;
    itinerary_transport: {
      [key: string]: Array<{
        from: string;
        to: string;
        time: string;
        transport_info: {
          from: string;
          to: string;
          city: string;
          recommended_routes: Array<{
            route_type: string;
            route?: string;
            description: string;
            estimated_time: string;
            fare: string;
          }>;
          all_transport_options: any;
        };
      }>;
    };
    total_days: number;
  };
}

export interface FormData {
  // 단계별 선택을 위한 필드들
  tripType: string; // '도시' 또는 '촌캉스'
  region: string; // 지역 선택
  customRegion: string; // 직접 입력한 지역
  guests: number; // 인원수
  travelStyle: string; // 여행 스타일
  budget: string; // 예산
  interests: string[]; // 관심사
  rooms: number; // 객실 수
  
  // 기존 필드들 (날짜는 나중에 추가될 수 있음)
  start_date: string;
  end_date: string;
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
