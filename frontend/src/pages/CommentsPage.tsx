import { useEffect, useState } from "react";
import { getComments, getCommentStats, replyToComment, escalateComment } from "../services/api";
import type { Comment, CommentStats } from "../types/api";

type Props = {
  token: string;
};

export function CommentsPage({ token }: Props) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [stats, setStats] = useState<CommentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedStatus]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [commentsData, statsData] = await Promise.all([
        getComments(token, selectedStatus === "all" ? undefined : selectedStatus),
        getCommentStats(token)
      ]);
      setComments(commentsData);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load comments");
    } finally {
      setLoading(false);
    }
  }

  async function handleReply(commentId: string) {
    if (!replyText.trim()) return;
    
    try {
      setSubmitting(true);
      setError(null);
      await replyToComment(token, commentId, replyText);
      setReplyingTo(null);
      setReplyText("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reply");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleEscalate(commentId: string) {
    const reason = prompt("Why are you escalating this comment?");
    if (!reason) return;
    
    try {
      setError(null);
      await escalateComment(token, commentId, reason);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to escalate");
    }
  }

  function getClassificationBadgeColor(classification: string): string {
    const colors: Record<string, string> = {
      POSITIVE: "bg-green-100 text-green-700",
      NEGATIVE: "bg-red-100 text-red-700",
      QUESTION: "bg-blue-100 text-blue-700",
      SPAM: "bg-orange-100 text-orange-700",
      TROLL: "bg-purple-100 text-purple-700",
      SENSITIVE: "bg-yellow-100 text-yellow-700",
    };
    return colors[classification] || "bg-slate-100 text-slate-700";
  }

  function getSentimentEmoji(sentiment: string): string {
    if (sentiment === "POSITIVE") return "😊";
    if (sentiment === "NEGATIVE") return "😟";
    if (sentiment === "NEUTRAL") return "😐";
    return "❓";
  }

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading comments...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Comments Management</h1>
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

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-slate-600 mb-1">Total Comments</div>
            <div className="text-3xl font-bold text-slate-800">{stats.total_comments}</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-slate-600 mb-1">Pending Replies</div>
            <div className="text-3xl font-bold text-yellow-600">{stats.pending_replies}</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-slate-600 mb-1">Escalated</div>
            <div className="text-3xl font-bold text-red-600">{stats.escalated}</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-slate-600 mb-1">Auto-Replied</div>
            <div className="text-3xl font-bold text-green-600">
              {stats.by_status?.auto_replied || 0}
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setSelectedStatus("all")}
            className={`px-4 py-2 rounded ${
              selectedStatus === "all"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setSelectedStatus("pending")}
            className={`px-4 py-2 rounded ${
              selectedStatus === "pending"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Pending ({stats?.by_status?.pending || 0})
          </button>
          <button
            onClick={() => setSelectedStatus("auto_replied")}
            className={`px-4 py-2 rounded ${
              selectedStatus === "auto_replied"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Auto-Replied ({stats?.by_status?.auto_replied || 0})
          </button>
          <button
            onClick={() => setSelectedStatus("escalated")}
            className={`px-4 py-2 rounded ${
              selectedStatus === "escalated"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Escalated ({stats?.escalated || 0})
          </button>
        </div>
      </div>

      {/* Comments List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading comments...</div>
        </div>
      ) : comments.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">💬</div>
          <div className="text-slate-400 text-lg mb-2">No comments yet</div>
          <div className="text-slate-500 text-sm">Comments will appear here once people interact with your posts</div>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <div key={comment.id} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold">
                  {comment.author_username[0].toUpperCase()}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-slate-800">@{comment.author_username}</span>
                    <span className="text-2xl">{getSentimentEmoji(comment.sentiment)}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getClassificationBadgeColor(comment.classification)}`}>
                      {comment.classification}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(comment.received_at).toLocaleString()}
                    </span>
                  </div>
                  
                  <p className="text-slate-700 mb-3">{comment.text}</p>
                  
                  {comment.auto_reply_text && (
                    <div className="bg-blue-50 border-l-4 border-blue-600 p-3 mb-3">
                      <div className="text-xs text-blue-600 font-medium mb-1">Auto-Reply:</div>
                      <p className="text-sm text-blue-800">{comment.auto_reply_text}</p>
                    </div>
                  )}
                  
                  {replyingTo === comment.id ? (
                    <div className="mt-3">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder="Type your reply..."
                        rows={3}
                        className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleReply(comment.id)}
                          disabled={submitting}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
                        >
                          {submitting ? "Sending..." : "Send Reply"}
                        </button>
                        <button
                          onClick={() => {
                            setReplyingTo(null);
                            setReplyText("");
                          }}
                          className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => setReplyingTo(comment.id)}
                        className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        Reply
                      </button>
                      {comment.status !== "escalated" && (
                        <button
                          onClick={() => handleEscalate(comment.id)}
                          className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                        >
                          Escalate
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
