export interface User {
  id: number;
  email: string;
  plan: 'free' | 'start' | 'pro' | 'unlimited';
  applications_count: number;
  applications_limit: number;
  created_at: string;
  telegram_id?: number;
}

export interface Stats {
  total_applications: number;
  applications_today: number;
  active_campaigns: number;
  interviews: number;
  response_rate: number;
}

export interface Campaign {
  id: number;
  name: string;
  status: 'running' | 'paused' | 'completed';
  source: string;
  keywords: string;
  location: string;
  applications_sent: number;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: number;
  campaign_id: number;
  company: string;
  position: string;
  url: string;
  status: 'sent' | 'viewed' | 'interview' | 'offer' | 'rejected';
  applied_at: string;
  source: string;
}

export interface Plan {
  id: string;
  name: string;
  price: number;
  period: string;
  applications_limit: number;
  features: string[];
  stripe_price_id?: string;
  popular?: boolean;
}

export interface TrackerCard {
  id: number;
  company: string;
  position: string;
  status: 'wishlist' | 'applied' | 'phone' | 'interview' | 'offer' | 'rejected';
  notes: string;
  url?: string;
  updated_at: string;
}

export interface Resume {
  id: number;
  filename: string;
  uploaded_at: string;
  is_active: boolean;
}

export type Toast = {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
};
