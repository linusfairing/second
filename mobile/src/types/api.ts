// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  is_active: boolean;
}

// User / Profile
export interface PhotoResponse {
  id: string;
  file_path: string;
  is_primary: boolean;
  order_index: number;
  created_at: string;
}

export interface ProfileDataResponse {
  bio: string | null;
  interests: string[] | null;
  values: string[] | null;
  personality_traits: string[] | null;
  relationship_goals: string | null;
  communication_style: string | null;
  profile_completeness: number;
}

export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  gender_preference: string[] | null;
  location: string | null;
  age_range_min: number;
  age_range_max: number;
  is_active: boolean;
  photos: PhotoResponse[];
  profile: ProfileDataResponse | null;
  created_at: string;
  updated_at: string;
}

export interface UserUpdate {
  display_name?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  gender_preference?: string[] | null;
  location?: string | null;
  age_range_min?: number | null;
  age_range_max?: number | null;
}

export interface ProfileUpdate {
  bio?: string | null;
  interests?: string[] | null;
  values?: string[] | null;
  personality_traits?: string[] | null;
  relationship_goals?: string | null;
  communication_style?: string | null;
}

// Chat
export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  reply: string;
  current_topic: string;
  onboarding_status: string;
}

export interface ChatMessageResponse {
  id: string;
  role: string;
  content: string;
  topic: string | null;
  created_at: string;
}

export interface ChatStatusResponse {
  current_topic: string;
  topics_completed: string[];
  onboarding_status: string;
  profile_completeness: number;
}

// Discover
export interface DiscoverUserResponse {
  id: string;
  display_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  location: string | null;
  photos: PhotoResponse[];
  profile: ProfileDataResponse | null;
  compatibility_score: number;
  created_at: string;
}

export interface DiscoverResponse {
  users: DiscoverUserResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Matches
export interface LikeRequest {
  liked_user_id: string;
}

export interface LikeResponse {
  liked_user_id: string;
  is_match: boolean;
  match_id: string | null;
}

export interface PassRequest {
  passed_user_id: string;
}

export interface PassResponse {
  passed_user_id: string;
}

export interface MatchResponse {
  id: string;
  other_user: DiscoverUserResponse;
  compatibility_score: number | null;
  created_at: string;
}

export interface MatchListResponse {
  matches: MatchResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Messages
export interface SendMessageRequest {
  content: string;
}

export interface MessageResponse {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  read_at: string | null;
  created_at: string;
}

// Block
export interface BlockRequest {
  blocked_user_id: string;
}

export interface BlockResponse {
  blocked_user_id: string;
  auto_unmatched: boolean;
}

export interface BlockedUserResponse {
  id: string;
  blocked_user_id: string;
  created_at: string;
}

// Account
export interface AccountStatusResponse {
  is_active: boolean;
  email: string;
  created_at: string;
}
