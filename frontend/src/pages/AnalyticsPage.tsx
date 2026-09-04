import { useEffect, useState } from "react";
import { 
  getAnalyticsSummary, 
  getContentTypePerformance, 
  getPostingTimeAnalysis,
  getHashtagPerformance,
  getGrowthMetrics,
  getSocialAccounts
} from "../services/api";
import type { 
  AnalyticsSummary, 
  ContentTypePerformance, 
  PostingTimeAnalysis,
  HashtagPerformance,
  GrowthMetrics,
  SocialAccount 
} from "../types/api";

type Props = {
  token: string;
};

export function AnalyticsPage({ token }: Props) {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [contentTypes, setContentTypes] = useState<ContentTypePerformance[]>([]);
  const [postingTimes, setPostingTimes] = useState<PostingTimeAnalysis[]>([]);
  const [hashtags, setHashtags] = useState<HashtagPerformance[]>([]);
  const [growth, setGrowth] = useState<GrowthMetrics | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccountId) {
      loadAnalytics();
    }
  }, [selectedAccountId]);

  async function loadAccounts() {
    try {
      const data = await getSocialAccounts(token);
      setAccounts(data);
      if (data.length > 0) {
        setSelectedAccountId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load accounts");
    } finally {
      setLoading(false);
    }
  }

  async function loadAnalytics() {
    if (!selectedAccountId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const [summaryData, contentTypesData, postingTimesData, hashtagsData, growthData] = await Promise.all([
        getAnalyticsSummary(token, selectedAccountId),
        getContentTypePerformance(token, selectedAccountId),
        getPostingTimeAnalysis(token, selectedAccountId),
        getHashtagPerformance(token, selectedAccountId),
        getGrowthMetrics(token, selectedAccountId, 30)
      ]);
      
      setSummary(summaryData);
      setContentTypes(contentTypesData);
      setPostingTimes(postingTimesData);
      setHashtags(hashtagsData);
      setGrowth(growthData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }

  function formatNumber(num: number): string {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  }

  function formatPercentage(num: number): string {
    return num.toFixed(2) + "%";
  }

  if (loading && accounts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading analytics...</div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <div className="text-slate-400 text-lg mb-2">No Instagram account connected</div>
        <div className="text-slate-500 text-sm mb-4">
          Connect your Instagram Business account in Settings to view analytics
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Analytics & Insights</h1>
        
        <select
          value={selectedAccountId}
          onChange={(e) => setSelectedAccountId(e.target.value)}
          className="px-4 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              @{account.account_name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading analytics data...</div>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm text-slate-600 mb-1">Total Posts</div>
                <div className="text-3xl font-bold text-slate-800">{summary.total_posts}</div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm text-slate-600 mb-1">Total Reach</div>
                <div className="text-3xl font-bold text-blue-600">{formatNumber(summary.total_reach)}</div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm text-slate-600 mb-1">Total Engagement</div>
                <div className="text-3xl font-bold text-green-600">{formatNumber(summary.total_engagement)}</div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="text-sm text-slate-600 mb-1">Engagement Rate</div>
                <div className="text-3xl font-bold text-purple-600">{formatPercentage(summary.engagement_rate)}</div>
              </div>
            </div>
          )}

          {/* Growth Metrics */}
          {growth && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Growth Metrics (Last 30 Days)</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-slate-600 mb-1">Follower Growth</div>
                  <div className="text-2xl font-bold text-slate-800">
                    {growth.follower_growth > 0 ? "+" : ""}{growth.follower_growth}
                  </div>
                  <div className="text-sm text-slate-500">
                    {formatPercentage(growth.follower_growth_rate)} rate
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-slate-600 mb-1">Engagement Trend</div>
                  <div className="text-2xl font-bold text-slate-800">
                    {growth.engagement_trend > 0 ? "+" : ""}{formatPercentage(growth.engagement_trend)}
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-slate-600 mb-1">Posting Frequency</div>
                  <div className="text-2xl font-bold text-slate-800">
                    {growth.posting_frequency.toFixed(1)} posts/day
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Content Type Performance */}
          {contentTypes.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Performance by Content Type</h2>
              
              <div className="space-y-4">
                {contentTypes.map((type) => (
                  <div key={type.content_type} className="border-b border-slate-200 pb-4 last:border-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {type.content_type === "image" && "🖼️"}
                          {type.content_type === "video" && "🎥"}
                          {type.content_type === "carousel" && "📊"}
                        </span>
                        <div>
                          <div className="font-medium text-slate-800 capitalize">{type.content_type}</div>
                          <div className="text-sm text-slate-500">{type.total_posts} posts</div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="font-semibold text-slate-800">
                          {formatNumber(type.average_engagement)} avg engagement
                        </div>
                        <div className="text-sm text-slate-600">
                          {formatPercentage(type.engagement_rate)} rate
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div 
                        className="bg-blue-600 h-full rounded-full"
                        style={{ width: `${Math.min(type.engagement_rate * 10, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Optimal Posting Times */}
          {postingTimes.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Best Posting Times</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {postingTimes.slice(0, 6).map((time, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-slate-50 rounded">
                    <div>
                      <div className="font-medium text-slate-800">
                        {time.day_of_week} at {time.hour_of_day}:00
                      </div>
                      <div className="text-sm text-slate-600">
                        {time.post_count} posts
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-green-600">
                        {formatPercentage(time.engagement_rate)}
                      </div>
                      <div className="text-sm text-slate-500">engagement</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Hashtags */}
          {hashtags.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Top Performing Hashtags</h2>
              
              <div className="space-y-3">
                {hashtags.slice(0, 10).map((tag, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold text-sm">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="font-medium text-slate-800">#{tag.hashtag}</div>
                        <div className="text-sm text-slate-500">Used {tag.usage_count} times</div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="font-semibold text-slate-800">
                        {formatNumber(tag.average_engagement)}
                      </div>
                      <div className="text-sm text-slate-500">avg engagement</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Post */}
          {summary?.top_post && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-3">🏆 Top Performing Post</h2>
              <div className="bg-white rounded p-4">
                <div className="text-sm text-slate-600 mb-2">Caption:</div>
                <p className="text-slate-800 mb-3 line-clamp-3">{summary.top_post.caption}</p>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-green-600 font-semibold">
                    {formatNumber(summary.top_post.engagement)} engagements
                  </span>
                  <span className="text-slate-500">Post ID: {summary.top_post.post_id}</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
