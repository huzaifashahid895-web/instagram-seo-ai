import { useEffect, useState } from "react";
import { getApprovalQueue, updateApproval, createApproval } from "../services/api";
import type { ApprovalQueue } from "../types/api";

type Props = {
  token: string;
};

export function ApprovalsPage({ token }: Props) {
  const [approvals, setApprovals] = useState<ApprovalQueue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showModal, setShowModal] = useState(false);
  const [newPostId, setNewPostId] = useState("");
  const [newRequestor, setNewRequestor] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadApprovals();
  }, []);

  async function loadApprovals() {
    try {
      setLoading(true);
      setError(null);
      const data = await getApprovalQueue(token);
      setApprovals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdate(approvalId: string, status: "approved" | "rejected") {
    const reason = prompt("Enter approval reason:", status === "approved" ? "Looks good!" : "Needs changes");
    if (reason === null) return;
    
    try {
      setError(null);
      await updateApproval(token, approvalId, status, reason);
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${status} approval`);
    }
  }

  async function handleCreate() {
    if (!newPostId.trim()) {
      setError("Post ID is required");
      return;
    }
    
    try {
      setCreating(true);
      setError(null);
      await createApproval(token, {
        post_id: newPostId,
        requested_by: newRequestor.trim() || "system"
      });
      setShowModal(false);
      setNewPostId("");
      setNewRequestor("");
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create approval request");
    } finally {
      setCreating(false);
    }
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700",
      approved: "bg-green-100 text-green-700",
      rejected: "bg-red-100 text-red-700",
      cancelled: "bg-slate-100 text-slate-700",
    };
    return colors[status] || "bg-slate-100 text-slate-700";
  }

  function getPriorityColor(priority: string): string {
    const colors: Record<string, string> = {
      high: "bg-red-50 text-red-700 border-red-200",
      medium: "bg-yellow-50 text-yellow-700 border-yellow-200",
      low: "bg-green-50 text-green-700 border-green-200",
    };
    return colors[priority] || "bg-slate-50 text-slate-700 border-slate-200";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Approval Queue</h1>
          <p className="text-slate-600 mt-1">Manage content approvals and review requests</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadApprovals}
            className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            New Request
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-slate-600 mb-1">Pending</div>
          <div className="text-3xl font-bold text-yellow-600">
            {approvals.filter(a => a.status === "pending").length}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-slate-600 mb-1">Approved</div>
          <div className="text-3xl font-bold text-green-600">
            {approvals.filter(a => a.status === "approved").length}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-slate-600 mb-1">Rejected</div>
          <div className="text-3xl font-bold text-red-600">
            {approvals.filter(a => a.status === "rejected").length}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-slate-600 mb-1">Total</div>
          <div className="text-3xl font-bold text-slate-800">{approvals.length}</div>
        </div>
      </div>

      {/* Approval List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading approvals...</div>
        </div>
      ) : approvals.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">📋</div>
          <div className="text-slate-400 text-lg mb-2">No approvals pending</div>
          <div className="text-slate-500 text-sm">
            Create an approval request or wait for pending approvals
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Create Approval Request
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <div key={approval.id} className={`bg-white rounded-lg shadow p-5 border-l-4 ${approval.priority === "high" ? "border-red-500" : approval.priority === "medium" ? "border-yellow-500" : "border-green-500"}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    approval.status === "pending" ? "bg-yellow-100 text-yellow-600" :
                    approval.status === "approved" ? "bg-green-100 text-green-600" :
                    "bg-red-100 text-red-600"
                  }`}>
                    {approval.status === "pending" ? "⏳" : approval.status === "approved" ? "✅" : "❌"}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-800">{approval.status}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(approval.status)}`}>
                        {approval.status}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${approval.priority === "high" ? "bg-red-100 text-red-700" : approval.priority === "medium" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
                        {approval.priority}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">
                      Post ID: {approval.post_id}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-sm text-slate-500">
                    Requested by: {approval.requested_by}
                  </div>
                  <div className="text-xs text-slate-400">
                    {new Date(approval.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
              
              {approval.content_summary && (
                <div className="mt-4 p-3 bg-slate-50 rounded">
                  <div className="text-xs font-medium text-slate-500 mb-1">Content Summary:</div>
                  <div className="text-sm text-slate-700">{approval.content_summary}</div>
                </div>
              )}
              
              {approval.reason && (
                <div className="mt-3 flex gap-2">
                  {approval.status === "pending" && (
                    <>
                      <button
                        onClick={() => handleUpdate(approval.id, "approved")}
                        className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleUpdate(approval.id, "rejected")}
                        className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              )}
              
              {approval.decision_reason && (
                <div className={`mt-3 p-3 rounded border ${
                  approval.status === "approved" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
                }`}>
                  <div className="text-xs font-medium text-slate-500 mb-1">
                    {approval.status === "approved" ? "Approval Reason:" : "Rejection Reason:"}
                  </div>
                  <div className="text-sm text-slate-700">{approval.decision_reason}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    Decision by: {approval.decision_by}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Create Approval Request</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Post ID
                </label>
                <input
                  type="text"
                  value={newPostId}
                  onChange={(e) => setNewPostId(e.target.value)}
                  placeholder="Enter post ID to request approval..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Requested By
                </label>
                <input
                  type="text"
                  value={newRequestor}
                  onChange={(e) => setNewRequestor(e.target.value)}
                  placeholder="Enter your name..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCreate}
                disabled={creating || !newPostId.trim()}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {creating ? "Creating..." : "Create Request"}
              </button>
              <button
                onClick={() => {
                  setShowModal(false);
                  setNewPostId("");
                  setNewRequestor("");
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
    </div>
  );
}
