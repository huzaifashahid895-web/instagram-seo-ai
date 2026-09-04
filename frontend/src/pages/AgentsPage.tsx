import { useEffect, useState } from "react";
import { getAgentTasks, getAgentRuns, createAgentTask, updateAgentTask, deleteAgentTask } from "../services/api";
import type { AgentTask, AgentRun } from "../types/api";

type Props = {
  token: string;
};

export function AgentsPage({ token }: Props) {
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showModal, setShowModal] = useState(false);
  const [editingTask, setEditingTask] = useState<AgentTask | null>(null);
  const [taskName, setTaskName] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskType, setTaskType] = useState("content_generator");
  const [taskActive, setTaskActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [tasksData, runsData] = await Promise.all([
        getAgentTasks(token),
        getAgentRuns(token)
      ]);
      setTasks(tasksData);
      setRuns(runsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!taskName.trim()) {
      setError("Task name is required");
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      
      const taskData = {
        name: taskName,
        description: taskDescription,
        type: taskType,
        is_active: taskActive,
        config: { type: taskType }
      };
      
      if (editingTask) {
        await updateAgentTask(token, editingTask.id, taskData);
      } else {
        await createAgentTask(token, taskData);
      }
      
      setShowModal(false);
      setEditingTask(null);
      setTaskName("");
      setTaskDescription("");
      setTaskType("content_generator");
      setTaskActive(true);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save task");
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(task: AgentTask) {
    setEditingTask(task);
    setTaskName(task.name);
    setTaskDescription(task.description || "");
    setTaskType(task.type || "content_generator");
    setTaskActive(task.is_active ?? true);
    setShowModal(true);
  }

  function handleDelete(id: string) {
    if (confirm("Are you sure you want to delete this agent task?")) {
      deleteAgentTask(token, id).then(loadData).catch(setError);
    }
  }

  function handleCreateNew() {
    setEditingTask(null);
    setTaskName("");
    setTaskDescription("");
    setTaskType("content_generator");
    setTaskActive(true);
    setShowModal(true);
  }

  function getTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      content_generator: "Content Generator",
      caption_writer: "Caption Writer",
      hashtag_optimizer: "Hashtag Optimizer",
      post_scheduler: "Post Scheduler",
      comment_classifier: "Comment Classifier",
      response_writer: "Response Writer",
      analytics_analyzer: "Analytics Analyzer",
    };
    return labels[type] || type;
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700",
      running: "bg-blue-100 text-blue-700",
      completed: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
      cancelled: "bg-slate-100 text-slate-700",
    };
    return colors[status] || "bg-slate-100 text-slate-700";
  }

  function getTaskTypeColor(type: string): string {
    const colors: Record<string, string> = {
      content_generator: "bg-blue-100 text-blue-700",
      caption_writer: "bg-purple-100 text-purple-700",
      hashtag_optimizer: "bg-green-100 text-green-700",
      post_scheduler: "bg-orange-100 text-orange-700",
      comment_classifier: "bg-red-100 text-red-700",
      response_writer: "bg-teal-100 text-teal-700",
      analytics_analyzer: "bg-indigo-100 text-indigo-700",
    };
    return colors[type] || "bg-slate-100 text-slate-700";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">AI Agents</h1>
          <p className="text-slate-600 mt-1">Automated agents for content creation, analysis, and engagement</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          >
            Refresh
          </button>
          <button
            onClick={handleCreateNew}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            New Agent
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Agent List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading agents...</div>
        </div>
      ) : tasks.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">🤖</div>
          <div className="text-slate-400 text-lg mb-2">No agents yet</div>
          <div className="text-slate-500 text-sm mb-4">
            Create AI agents to automate your social media tasks
          </div>
          <button
            onClick={handleCreateNew}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Create Your First Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {tasks.map((task) => (
            <div key={task.id} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getTaskTypeColor(task.type || "content_generator")}`}>
                      {getTypeLabel(task.type || "content_generator")}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${task.is_active ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>
                      {task.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-800 text-lg">{task.name}</h3>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(task)}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(task.id)}
                    className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    Delete
                  </button>
                </div>
              </div>
              
              {task.description && (
                <p className="text-sm text-slate-600 mb-4">{task.description}</p>
              )}
              
              <div className="space-y-2 text-sm text-slate-500">
                <div className="flex justify-between">
                  <span>Type</span>
                  <span className="font-medium">{task.type || "content_generator"}</span>
                </div>
                {task.last_run_at && (
                  <div className="flex justify-between">
                    <span>Last Run</span>
                    <span>{new Date(task.last_run_at).toLocaleDateString()}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Total Runs</span>
                  <span className="font-medium">{task.run_count || 0}</span>
                </div>
              </div>
              
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => {
                    // Trigger agent run
                    alert("Agent run triggered!");
                    loadData();
                  }}
                  className="flex-1 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                >
                  Run Now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Runs */}
      {runs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Recent Agent Runs</h2>
          <div className="space-y-3">
            {runs.slice(0, 5).map((run) => (
              <div key={run.id} className="flex items-center justify-between p-3 border border-slate-200 rounded">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    run.status === "completed" ? "bg-green-500" :
                    run.status === "failed" ? "bg-red-500" :
                    run.status === "running" ? "bg-blue-500" : "bg-yellow-500"
                  }`} />
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      {run.task_name || run.task_type}
                    </div>
                    <div className="text-xs text-slate-500">
                      {new Date(run.started_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(run.status)}`}>
                  {run.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">
              {editingTask ? "Edit Agent" : "Create New Agent"}
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={taskName}
                  onChange={(e) => setTaskName(e.target.value)}
                  placeholder="Enter agent name..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Agent Type
                </label>
                <select
                  value={taskType}
                  onChange={(e) => setTaskType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="content_generator">Content Generator</option>
                  <option value="caption_writer">Caption Writer</option>
                  <option value="hashtag_optimizer">Hashtag Optimizer</option>
                  <option value="post_scheduler">Post Scheduler</option>
                  <option value="comment_classifier">Comment Classifier</option>
                  <option value="response_writer">Response Writer</option>
                  <option value="analytics_analyzer">Analytics Analyzer</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Description
                </label>
                <textarea
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  placeholder="Describe what this agent does..."
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="taskActive"
                  checked={taskActive}
                  onChange={(e) => setTaskActive(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label htmlFor="taskActive" className="text-sm text-slate-700">
                  Active (agent will run automatically)
                </label>
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {saving ? "Saving..." : (editingTask ? "Update" : "Create")}
              </button>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingTask(null);
                  setTaskName("");
                  setTaskDescription("");
                  setTaskType("content_generator");
                  setTaskActive(true);
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
