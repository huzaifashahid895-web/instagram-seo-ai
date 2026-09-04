import { useEffect, useState } from "react";
import { getKeywords, getHashtags, analyzeContentSEO } from "../services/api";
import type { Keyword, Hashtag, SEOScore } from "../types/api";

type Props = {
  token: string;
};

export function SEOPage({ token }: Props) {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [hashtags, setHashtags] = useState<Hashtag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [contentId, setContentId] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [seoScore, setSeoScore] = useState<SEOScore | null>(null);
  
  const [activeTab, setActiveTab] = useState<"keywords" | "hashtags" | "analyzer">("keywords");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [keywordsData, hashtagsData] = await Promise.all([
        getKeywords(token),
        getHashtags(token)
      ]);
      setKeywords(keywordsData);
      setHashtags(hashtagsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load SEO data");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyze() {
    if (!contentId.trim()) return;
    
    try {
      setAnalyzing(true);
      setError(null);
      const score = await analyzeContentSEO(token, contentId);
      setSeoScore(score);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze content");
    } finally {
      setAnalyzing(false);
    }
  }

  function getScoreColor(score: number): string {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    if (score >= 40) return "text-orange-600";
    return "text-red-600";
  }

  function getScoreBgColor(score: number): string {
    if (score >= 80) return "bg-green-100";
    if (score >= 60) return "bg-yellow-100";
    if (score >= 40) return "bg-orange-100";
    return "bg-red-100";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">SEO & Optimization</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab("keywords")}
            className={`px-4 py-2 rounded ${
              activeTab === "keywords"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Keywords ({keywords.length})
          </button>
          <button
            onClick={() => setActiveTab("hashtags")}
            className={`px-4 py-2 rounded ${
              activeTab === "hashtags"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Hashtags ({hashtags.length})
          </button>
          <button
            onClick={() => setActiveTab("analyzer")}
            className={`px-4 py-2 rounded ${
              activeTab === "analyzer"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Content Analyzer
          </button>
        </div>
      </div>

      {/* Keywords Tab */}
      {activeTab === "keywords" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Tracked Keywords</h2>
          
          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading keywords...</div>
          ) : keywords.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">🔍</div>
              <div className="text-slate-400 text-lg mb-2">No keywords tracked yet</div>
              <div className="text-slate-500 text-sm">Keywords will appear here once you analyze content</div>
            </div>
          ) : (
            <div className="space-y-3">
              {keywords.map((keyword) => (
                <div key={keyword.id} className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-slate-800">{keyword.text}</span>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded font-medium">
                        {keyword.category}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-600">{keyword.search_volume?.toLocaleString() || "N/A"}</div>
                      <div className="text-xs text-slate-500">monthly searches</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-slate-100">
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Competition</div>
                      <div className="font-semibold text-slate-700 capitalize">{keyword.competition || "N/A"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Relevance</div>
                      <div className="font-semibold text-slate-700">{keyword.relevance_score ? `${keyword.relevance_score}%` : "N/A"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">CPC</div>
                      <div className="font-semibold text-slate-700">${keyword.cpc?.toFixed(2) || "N/A"}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Hashtags Tab */}
      {activeTab === "hashtags" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Trending Hashtags</h2>
          
          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading hashtags...</div>
          ) : hashtags.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">#️⃣</div>
              <div className="text-slate-400 text-lg mb-2">No hashtags tracked yet</div>
              <div className="text-slate-500 text-sm">Hashtags will appear here once you analyze content</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {hashtags.map((hashtag) => (
                <div key={hashtag.id} className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-semibold text-blue-600">#{hashtag.tag}</span>
                    <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                      hashtag.trending ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-600"
                    }`}>
                      {hashtag.trending ? "🔥 Trending" : "Regular"}
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Usage Count</span>
                      <span className="font-semibold text-slate-700">{hashtag.usage_count?.toLocaleString() || "N/A"}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Engagement</span>
                      <span className="font-semibold text-slate-700">{hashtag.avg_engagement?.toFixed(1) || "N/A"}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Relevance</span>
                      <span className="font-semibold text-slate-700">{hashtag.relevance_score || "N/A"}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Content Analyzer Tab */}
      {activeTab === "analyzer" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Analyze Content SEO</h2>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Content Asset ID
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={contentId}
                onChange={(e) => setContentId(e.target.value)}
                placeholder="Enter content asset ID..."
                className="flex-1 px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleAnalyze}
                disabled={analyzing || !contentId.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {analyzing ? "Analyzing..." : "Analyze"}
              </button>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Enter the ID of a content asset to analyze its SEO performance
            </div>
          </div>

          {seoScore && (
            <div className="space-y-4">
              <div className={`rounded-lg p-6 ${getScoreBgColor(seoScore.overall_score)}`}>
                <div className="text-center">
                  <div className="text-sm text-slate-600 mb-2">Overall SEO Score</div>
                  <div className={`text-5xl font-bold ${getScoreColor(seoScore.overall_score)}`}>
                    {seoScore.overall_score}
                  </div>
                  <div className="text-sm text-slate-600 mt-2">out of 100</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border border-slate-200 rounded-lg p-4">
                  <div className="text-sm text-slate-600 mb-2">Keyword Density</div>
                  <div className={`text-3xl font-bold ${getScoreColor(seoScore.keyword_density_score)}`}>
                    {seoScore.keyword_density_score}
                  </div>
                </div>
                
                <div className="border border-slate-200 rounded-lg p-4">
                  <div className="text-sm text-slate-600 mb-2">Hashtag Relevance</div>
                  <div className={`text-3xl font-bold ${getScoreColor(seoScore.hashtag_relevance_score)}`}>
                    {seoScore.hashtag_relevance_score}
                  </div>
                </div>
                
                <div className="border border-slate-200 rounded-lg p-4">
                  <div className="text-sm text-slate-600 mb-2">Readability</div>
                  <div className={`text-3xl font-bold ${getScoreColor(seoScore.readability_score)}`}>
                    {seoScore.readability_score}
                  </div>
                </div>
              </div>

              {seoScore.suggestions && seoScore.suggestions.length > 0 && (
                <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
                  <div className="font-semibold text-blue-800 mb-3">💡 Suggestions for Improvement</div>
                  <ul className="space-y-2">
                    {seoScore.suggestions.map((suggestion, index) => (
                      <li key={index} className="text-sm text-blue-700 flex items-start">
                        <span className="mr-2">•</span>
                        <span>{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!seoScore && !analyzing && (
            <div className="text-center py-12 text-slate-400">
              Enter a content ID above and click Analyze to see SEO insights
            </div>
          )}
        </div>
      )}
    </div>
  );
}
