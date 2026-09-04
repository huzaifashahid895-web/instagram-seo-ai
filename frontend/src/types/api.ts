export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
};

export type DashboardSummary = {
  social_accounts: number;
  content_assets: number;
  content_ideas: number;
  generated_content: number;
  posts: number;
  scheduled_posts: number;
  published_posts: number;
  comments: number;
  pending_approvals: number;
  active_model_configs: number;
};

// Content types
export type ContentAsset = {
  id: string;
  user_id: string;
  filename: string;
  media_type: "image" | "video" | "audio";
  file_size: number;
  storage_path: string;
  thumbnail_path?: string;
  duration_seconds?: number;
  width?: number;
  height?: number;
  transcript?: string;
  visual_description?: string;
  detected_objects?: string[];
  detected_text?: string;
  audio_path?: string;
  uploaded_at: string;
  processed: boolean;
};

export type AnalysisSummary = {
  asset_id: string;
  transcript?: string;
  visual_description?: string;
  detected_objects?: string[];
  detected_text?: string;
  duration_seconds?: number;
  processed: boolean;
};

// AI Studio types
export type GeneratedScript = {
  id: string;
  user_id: string;
  prompt: string;
  script_text: string;
  estimated_duration_seconds?: number;
  created_at: string;
};

export type GeneratedCaption = {
  id: string;
  content_id: string;
  caption_text: string;
  platform: string;
  created_at: string;
};

// SEO types
export type Keyword = {
  id: string;
  user_id: string;
  text: string;
  category?: string;
  search_volume?: number;
  competition?: string;
  cpc?: number;
  relevance_score?: number;
  created_at: string;
};

export type KeywordsResponse = {
  keywords: Keyword[];
  total_count: number;
};

export type Hashtag = {
  id: string;
  user_id: string;
  tag: string;
  usage_count?: number;
  avg_engagement?: number;
  relevance_score?: number;
  trending?: boolean;
  created_at: string;
};

export type HashtagsResponse = {
  hashtags: Hashtag[];
  total_count: number;
};

export type SEOScore = {
  overall_score: number;
  keyword_density_score: number;
  hashtag_relevance_score: number;
  readability_score: number;
  engagement_potential?: number;
  suggestions?: string[];
};

// Scheduling types
export type ScheduledJob = {
  id: string;
  user_id: string;
  post_id: string;
  scheduled_time: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  attempts: number;
  last_error?: string;
  created_at: string;
  updated_at: string;
};

// Comments types
export type Comment = {
  id: string;
  post_id: string;
  instagram_comment_id: string;
  author_username: string;
  author_id: string;
  text: string;
  classification: string;
  sentiment: string;
  status: string;
  auto_reply_text?: string;
  created_at: string;
  received_at: string;
};

export type CommentStats = {
  total_comments: number;
  by_classification: Record<string, number>;
  by_sentiment: Record<string, number>;
  by_status: Record<string, number>;
  pending_replies: number;
  escalated: number;
};

// Analytics types
export type AnalyticsSummary = {
  social_account_id: string;
  period_start: string;
  period_end: string;
  total_posts: number;
  total_reach: number;
  total_impressions: number;
  total_engagement: number;
  engagement_rate: number;
  follower_count?: number;
  average_likes_per_post: number;
  average_comments_per_post: number;
  top_post?: {
    post_id: string;
    caption: string;
    engagement: number;
  };
};

export type ContentTypePerformance = {
  content_type: "image" | "video" | "carousel";
  total_posts: number;
  average_engagement: number;
  average_reach: number;
  engagement_rate: number;
};

export type PostingTimeAnalysis = {
  day_of_week: string;
  hour_of_day: number;
  post_count: number;
  average_engagement: number;
  engagement_rate: number;
};

export type HashtagPerformance = {
  hashtag: string;
  usage_count: number;
  total_engagement: number;
  average_engagement: number;
  reach: number;
};

export type GrowthMetrics = {
  period_days: number;
  follower_growth: number;
  follower_growth_rate: number;
  engagement_trend: number;
  posting_frequency: number;
  content_velocity: number;
};

// Settings types
export type ModelConfig = {
  id: string;
  user_id: string;
  capability: string;
  provider: string;
  model_name: string;
  is_default: boolean;
  config_json: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

// Social Account types
export type SocialAccount = {
  id: string;
  user_id: string;
  platform: "instagram";
  account_name: string;
  account_id: string;
  access_token?: string;
  is_active: boolean;
  connected_at: string;
  last_synced_at?: string;
};

// RAG/Knowledge Base types
export type RAGDocument = {
  id: string;
  user_id: string;
  document_name: string;
  filename: string;
  file_size: number;
  file_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  chunk_count?: number;
  processing_error?: string;
  created_at: string;
  updated_at: string;
};

export type RAGChunk = {
  id: string;
  document_id: string;
  content: string;
  embedding?: number[];
  chunk_order: number;
  created_at: string;
};

export type UploadRAGDocument = {
  success: boolean;
  document: RAGDocument;
};

// Content Strategy types
export type ContentStrategy = {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  category: string;
  settings?: Record<string, any>;
  created_at: string;
  updated_at?: string;
};

// Agent types
export type AgentTask = {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  type: string;
  is_active: boolean;
  config: Record<string, any>;
  run_count: number;
  last_run_at?: string;
  created_at: string;
  updated_at?: string;
};

export type AgentRun = {
  id: string;
  task_id: string;
  task_name?: string;
  task_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  created_at: string;
};

// Approval Queue types
export type ApprovalQueue = {
  id: string;
  post_id: string;
  requested_by: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  priority: "low" | "medium" | "high";
  content_summary?: string;
  reason?: string;
  decision_reason?: string;
  decision_by?: string;
  created_at: string;
  updated_at?: string;
};
