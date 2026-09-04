import { useEffect, useState } from "react";
import { getScheduledJobs, cancelScheduledJob, createScheduledJob } from "../services/api";
import type { ScheduledJob } from "../types/api";

type Props = {
  token: string;
};

export function CalendarPage({ token }: Props) {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPostId, setNewPostId] = useState("");
  const [newScheduledTime, setNewScheduledTime] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      setLoading(true);
      setError(null);
      const data = await getScheduledJobs(token);
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scheduled jobs");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateJob() {
    if (!newPostId.trim() || !newScheduledTime.trim()) {
      setError("Post ID and scheduled time are required");
      return;
    }
    
    try {
      setCreating(true);
      setError(null);
      await createScheduledJob(token, newPostId, newScheduledTime);
      setShowCreateModal(false);
      setNewPostId("");
      setNewScheduledTime("");
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scheduled job");
    } finally {
      setCreating(false);
    }
  }

  async function handleCancelJob(jobId: string) {
    if (!confirm("Are you sure you want to cancel this scheduled post?")) return;
    
    try {
      setError(null);
      await cancelScheduledJob(token, jobId);
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel job");
    }
  }

  function getStatusBadge(status: string): { bg: string; text: string } {
    const badges: Record<string, { bg: string; text: string }> = {
      pending: { bg: "bg-blue-100", text: "text-blue-700" },
      running: { bg: "bg-yellow-100", text: "text-yellow-700" },
      completed: { bg: "bg-green-100", text: "text-green-700" },
      failed: { bg: "bg-red-100", text: "text-red-700" },
      cancelled: { bg: "bg-slate-100", text: "text-slate-700" },
    };
    return badges[status] || badges.pending;
  }

  function getStatusEmoji(status: string): string {
    const emojis: Record<string, string> = {
      pending: "⏳",
      running: "▶️",
      completed: "✅",
      failed: "❌",
      cancelled: "⛔",
    };
    return emojis[status] || "❓";
  }

  function groupJobsByDate(): Record<string, ScheduledJob[]> {
    const groups: Record<string, ScheduledJob[]> = {};
    
    jobs.forEach((job) => {
      const date = new Date(job.scheduled_time).toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(job);
    });
    
    // Sort jobs within each date by time
    Object.keys(groups).forEach((date) => {
      groups[date].sort((a, b) => 
        new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
      );
    });
    
    return groups;
  }

  const groupedJobs = groupJobsByDate();
  const sortedDates = Object.keys(groupedJobs).sort((a, b) => {
    const dateA = new Date(groupedJobs[a][0].scheduled_time);
    const dateB = new Date(groupedJobs[b][0].scheduled_time);
    return dateA.getTime() - dateB.getTime();
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Content Calendar</h1>
        <div className="flex gap-2">
          <button
            onClick={loadJobs}
            className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Schedule Post
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Schedule a Post</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Post ID
                </label>
                <input
                  type="text"
                  value={newPostId}
                  onChange={(e) => setNewPostId(e.target.value)}
                  placeholder="Enter post ID..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Scheduled Time
                </label>
                <input
                  type="datetime-local"
                  value={newScheduledTime}
                  onChange={(e) => setNewScheduledTime(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCreateJob}
                disabled={creating}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {creating ? "Scheduling..." : "Schedule"}
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewPostId("");
                  setNewScheduledTime("");
                  setError(null);
                }}
                className="flex-1 px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Calendar View */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading schedule...</div>
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">📅</div>
          <div className="text-slate-400 text-lg mb-2">No scheduled posts yet</div>
          <div className="text-slate-500 text-sm mb-4">
            Schedule your first post to see it appear on the calendar
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Schedule Your First Post
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stats Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-slate-600 mb-1">Total Scheduled</div>
              <div className="text-3xl font-bold text-blue-600">{jobs.length}</div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-slate-600 mb-1">Pending</div>
              <div className="text-3xl font-bold text-yellow-600">
                {jobs.filter(j => j.status === "pending").length}
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-slate-600 mb-1">Completed</div>
              <div className="text-3xl font-bold text-green-600">
                {jobs.filter(j => j.status === "completed").length}
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-slate-600 mb-1">Failed</div>
              <div className="text-3xl font-bold text-red-600">
                {jobs.filter(j => j.status === "failed").length}
              </div>
            </div>
          </div>

          {/* Grouped Jobs by Date */}
          {sortedDates.map((dateLabel) => (
            <div key={dateLabel} className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4 border-b border-slate-200 pb-2">
                {dateLabel}
              </h2>
              
              <div className="space-y-3">
                {groupedJobs[dateLabel].map((job) => {
                  const badge = getStatusBadge(job.status);
                  return (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-blue-300 transition"
                    >
                      <div className="flex items-center gap-4">
                        <div className="text-3xl">{getStatusEmoji(job.status)}</div>
                        
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-slate-800">
                              {new Date(job.scheduled_time).toLocaleTimeString("en-US", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${badge.bg} ${badge.text}`}>
                              {job.status}
                            </span>
                          </div>
                          
                          <div className="text-sm text-slate-600">
                            Post ID: <span className="font-mono">{job.post_id}</span>
                          </div>
                          
                          {job.attempts > 0 && (
                            <div className="text-xs text-slate-500 mt-1">
                              Attempts: {job.attempts}
                            </div>
                          )}
                          
                          {job.last_error && (
                            <div className="text-xs text-red-600 mt-1">
                              Error: {job.last_error}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        {(job.status === "pending" || job.status === "failed") && (
                          <button
                            onClick={() => handleCancelJob(job.id)}
                            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
