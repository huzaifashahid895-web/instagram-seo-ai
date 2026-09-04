import type {
  AuthUser,
  DashboardSummary,
  TokenResponse,
  ContentAsset,
  AnalysisSummary,
  GeneratedScript,
  GeneratedCaption,
  SEOScore,
  Keyword,
  Hashtag,
  HashtagsResponse,
  KeywordsResponse,
  ScheduledJob,
  Comment,
  CommentStats,
  AnalyticsSummary,
  ContentTypePerformance,
  PostingTimeAnalysis,
  HashtagPerformance,
  GrowthMetrics,
  ModelConfig,
  SocialAccount,
  RAGDocument,
  UploadRAGDocument,
  ContentStrategy,
  AgentTask,
  AgentRun,
  ApprovalQueue
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type RequestOptions = {
  token?: string | null;
  body?: unknown;
  method?: string;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || (options.body ? "POST" : "GET"),
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function uploadFile(token: string, file: File): Promise<ContentAsset> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/content/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed with ${response.status}`);
  }

  return response.json();
}

// Auth endpoints
export function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", { body: { email, password } });
}

export function register(email: string, password: string, fullName: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", { body: { email, password, full_name: fullName || null } });
}

export function getMe(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", { token });
}

// Dashboard
export function getDashboardSummary(token: string): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/dashboard/summary", { token });
}

// Content endpoints
export function getContentAssets(token: string): Promise<ContentAsset[]> {
  return apiRequest<ContentAsset[]>("/content/assets", { token });
}

export function getContentAsset(token: string, assetId: string): Promise<ContentAsset> {
  return apiRequest<ContentAsset>(`/content/assets/${assetId}`, { token });
}

export function analyzeContent(token: string, assetId: string): Promise<AnalysisSummary> {
  return apiRequest<AnalysisSummary>("/content/analyze", { 
    token, 
    body: { asset_id: assetId } 
  });
}

export function deleteContentAsset(token: string, assetId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/content/assets/${assetId}`, { 
    token, 
    method: "DELETE" 
  });
}

// AI Studio endpoints
export function generateScript(token: string, prompt: string, duration?: number): Promise<GeneratedScript> {
  return apiRequest<GeneratedScript>("/ai-studio/generate-script", {
    token,
    body: { prompt, target_duration_seconds: duration }
  });
}

export function generateCaption(token: string, contentId: string, platform: string = "instagram"): Promise<GeneratedCaption> {
  return apiRequest<GeneratedCaption>("/ai-studio/generate-caption", {
    token,
    body: { content_id: contentId, platform }
  });
}

export function produceVideo(
  token: string, 
  scriptId: string, 
  voiceId?: string
): Promise<{ job_id: string; status: string }> {
  return apiRequest("/ai-studio/produce-video", {
    token,
    body: { script_id: scriptId, voice_id: voiceId }
  });
}

// SEO endpoints
export function extractKeywords(token: string, text: string): Promise<KeywordsResponse> {
  return apiRequest<KeywordsResponse>("/seo/keywords/extract", {
    token,
    body: { text }
  });
}

export function getKeywords(token: string): Promise<Keyword[]> {
  return apiRequest<Keyword[]>("/seo/keywords", { token });
}

export function generateHashtags(token: string, text: string, count: number = 30): Promise<HashtagsResponse> {
  return apiRequest<HashtagsResponse>("/seo/hashtags/generate", {
    token,
    body: { text, count }
  });
}

export function getHashtags(token: string): Promise<Hashtag[]> {
  return apiRequest<Hashtag[]>("/seo/hashtags", { token });
}

export function calculateSEOScore(token: string, caption: string, hashtags: string[]): Promise<SEOScore> {
  return apiRequest<SEOScore>("/seo/score", {
    token,
    body: { caption, hashtags }
  });
}

export function analyzeContentSEO(token: string, contentId: string): Promise<SEOScore> {
  return apiRequest<SEOScore>("/seo/analyze", {
    token,
    body: { content_id: contentId }
  });
}

// Scheduling endpoints
export function createScheduledJob(
  token: string,
  postId: string,
  scheduledTime: string
): Promise<ScheduledJob> {
  return apiRequest<ScheduledJob>("/scheduler/jobs", {
    token,
    body: { post_id: postId, scheduled_time: scheduledTime }
  });
}

export function getScheduledJobs(token: string): Promise<ScheduledJob[]> {
  return apiRequest<ScheduledJob[]>("/scheduler/jobs", { token });
}

export function cancelScheduledJob(token: string, jobId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/scheduler/jobs/${jobId}`, {
    token,
    method: "DELETE"
  });
}

// Comments endpoints
export function getComments(token: string, status?: string): Promise<Comment[]> {
  const query = status ? `?status=${status}` : "";
  return apiRequest<Comment[]>(`/comments${query}`, { token });
}

export function getCommentStats(token: string): Promise<CommentStats> {
  return apiRequest<CommentStats>("/comments/stats", { token });
}

export function replyToComment(
  token: string,
  commentId: string,
  replyText: string
): Promise<{ success: boolean }> {
  return apiRequest(`/comments/${commentId}/reply`, {
    token,
    body: { reply_text: replyText }
  });
}

export function escalateComment(
  token: string,
  commentId: string,
  reason: string
): Promise<{ success: boolean }> {
  return apiRequest(`/comments/${commentId}/escalate`, {
    token,
    body: { reason }
  });
}

// Analytics endpoints
export function getAnalyticsSummary(token: string, socialAccountId: string): Promise<AnalyticsSummary> {
  return apiRequest<AnalyticsSummary>(`/analytics/summary?social_account_id=${socialAccountId}`, { token });
}

export function getContentTypePerformance(token: string, socialAccountId: string): Promise<ContentTypePerformance[]> {
  return apiRequest<ContentTypePerformance[]>(
    `/analytics/content-types?social_account_id=${socialAccountId}`, 
    { token }
  );
}

export function getPostingTimeAnalysis(token: string, socialAccountId: string): Promise<PostingTimeAnalysis[]> {
  return apiRequest<PostingTimeAnalysis[]>(
    `/analytics/posting-times?social_account_id=${socialAccountId}`, 
    { token }
  );
}

export function getHashtagPerformance(token: string, socialAccountId: string): Promise<HashtagPerformance[]> {
  return apiRequest<HashtagPerformance[]>(
    `/analytics/hashtags?social_account_id=${socialAccountId}`, 
    { token }
  );
}

export function getGrowthMetrics(token: string, socialAccountId: string, days: number = 30): Promise<GrowthMetrics> {
  return apiRequest<GrowthMetrics>(
    `/analytics/growth?social_account_id=${socialAccountId}&days=${days}`, 
    { token }
  );
}

// Settings endpoints
export function getModelConfigs(token: string): Promise<ModelConfig[]> {
  return apiRequest<ModelConfig[]>("/settings/model-configs", { token });
}

export function createModelConfig(token: string, config: Partial<ModelConfig>): Promise<ModelConfig> {
  return apiRequest<ModelConfig>("/settings/model-configs", {
    token,
    body: config
  });
}

export function updateModelConfig(
  token: string,
  configId: string,
  updates: Partial<ModelConfig>
): Promise<ModelConfig> {
  return apiRequest<ModelConfig>(`/settings/model-configs/${configId}`, {
    token,
    method: "PUT",
    body: updates
  });
}

export function deleteModelConfig(token: string, configId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/settings/model-configs/${configId}`, {
    token,
    method: "DELETE"
  });
}

// Social Accounts endpoints
export function getSocialAccounts(token: string): Promise<SocialAccount[]> {
  return apiRequest<SocialAccount[]>("/social-accounts", { token });
}

export function getInstagramAuthUrl(token: string): Promise<{ auth_url: string }> {
  return apiRequest<{ auth_url: string }>("/instagram/auth-url", { token });
}

export function disconnectSocialAccount(token: string, accountId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/social-accounts/${accountId}`, {
    token,
    method: "DELETE"
  });
}

// RAG/Knowledge Base endpoints
export function getRagDocuments(token: string): Promise<RAGDocument[]> {
  return apiRequest<RAGDocument[]>("/rag/documents", { token });
}

export async function createRagDocument(token: string, formData: FormData): Promise<UploadRAGDocument> {
  const response = await fetch(`${API_BASE}/rag/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail ?? "Upload failed");
  }

  return response.json();
}

export function deleteRagDocument(token: string, docId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/rag/documents/${docId}`, {
    token,
    method: "DELETE"
  });
}

// Content Strategy endpoints
export function getContentStrategies(token: string): Promise<ContentStrategy[]> {
  return apiRequest<ContentStrategy[]>("/strategy/strategies", { token });
}

export function createContentStrategy(token: string, strategy: Partial<ContentStrategy>): Promise<ContentStrategy> {
  return apiRequest<ContentStrategy>("/strategy/strategies", {
    token,
    body: strategy
  });
}

export function updateContentStrategy(
  token: string,
  strategyId: string,
  updates: Partial<ContentStrategy>
): Promise<ContentStrategy> {
  return apiRequest<ContentStrategy>(`/strategy/strategies/${strategyId}`, {
    token,
    method: "PUT",
    body: updates
  });
}

export function deleteContentStrategy(token: string, strategyId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/strategy/strategies/${strategyId}`, {
    token,
    method: "DELETE"
  });
}

// Agent endpoints
export function getAgentTasks(token: string): Promise<AgentTask[]> {
  return apiRequest<AgentTask[]>("/agents/tasks", { token });
}

export function getAgentRuns(token: string): Promise<AgentRun[]> {
  return apiRequest<AgentRun[]>("/agents/runs", { token });
}

export function createAgentTask(token: string, task: Partial<AgentTask>): Promise<AgentTask> {
  return apiRequest<AgentTask>("/agents/tasks", {
    token,
    body: task
  });
}

export function updateAgentTask(
  token: string,
  taskId: string,
  updates: Partial<AgentTask>
): Promise<AgentTask> {
  return apiRequest<AgentTask>(`/agents/tasks/${taskId}`, {
    token,
    method: "PUT",
    body: updates
  });
}

export function deleteAgentTask(token: string, taskId: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/agents/tasks/${taskId}`, {
    token,
    method: "DELETE"
  });
}

// Approval Queue endpoints
export function getApprovalQueue(token: string): Promise<ApprovalQueue[]> {
  return apiRequest<ApprovalQueue[]>("/approvals", { token });
}

export function updateApproval(
  token: string,
  approvalId: string,
  status: "approved" | "rejected",
  reason: string
): Promise<ApprovalQueue> {
  return apiRequest<ApprovalQueue>(`/approvals/${approvalId}`, {
    token,
    method: "PUT",
    body: { status, reason }
  });
}

export function createApproval(token: string, data: { post_id: string; requested_by: string }): Promise<ApprovalQueue> {
  return apiRequest<ApprovalQueue>("/approvals", {
    token,
    body: data
  });
}
