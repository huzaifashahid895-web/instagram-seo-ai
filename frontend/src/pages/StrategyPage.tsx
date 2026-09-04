import { useEffect, useState } from "react";
import { getContentStrategies, createContentStrategy, updateContentStrategy, deleteContentStrategy } from "../services/api";
import type { ContentStrategy } from "../types/api";

type Props = {
  token: string;
};

export function StrategyPage({ token }: Props) {
  const [strategies, setStrategies] = useState<ContentStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showModal, setShowModal] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<ContentStrategy | null>(null);
  const [strategyName, setStrategyName] = useState("");
  const [strategyDescription, setStrategyDescription] = useState("");
  const [strategyCategory, setStrategyCategory] = useState("general");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadStrategies();
  }, []);

  async function loadStrategies() {
    try {
      setLoading(true);
      setError(null);
      const data = await getContentStrategies(token);
      setStrategies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load strategies");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!strategyName.trim()) {
      setError("Strategy name is required");
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      
      if (editingStrategy) {
        await updateContentStrategy(token, editingStrategy.id, {
          name: strategyName,
          description: strategyDescription,
          category: strategyCategory,
        });
      } else {
        await createContentStrategy(token, {
          name: strategyName,
          description: strategyDescription,
          category: strategyCategory,
        });
      }
      
      setShowModal(false);
      setEditingStrategy(null);
      setStrategyName("");
      setStrategyDescription("");
      setStrategyCategory("general");
      await loadStrategies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save strategy");
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(strategy: ContentStrategy) {
    setEditingStrategy(strategy);
    setStrategyName(strategy.name);
    setStrategyDescription(strategy.description || "");
    setStrategyCategory(strategy.category || "general");
    setShowModal(true);
  }

  function handleDelete(id: string) {
    if (confirm("Are you sure you want to delete this strategy?")) {
      deleteContentStrategy(token, id).then(loadStrategies).catch(setError);
    }
  }

  function handleCreateNew() {
    setEditingStrategy(null);
    setStrategyName("");
    setStrategyDescription("");
    setStrategyCategory("general");
    setShowModal(true);
  }

  function getCategoryColor(category: string): string {
    const colors: Record<string, string> = {
      general: "bg-slate-100 text-slate-700",
      educational: "bg-blue-100 text-blue-700",
      promotional: "bg-green-100 text-green-700",
      engagement: "bg-purple-100 text-purple-700",
      trending: "bg-yellow-100 text-yellow-700",
      industry: "bg-orange-100 text-orange-700",
    };
    return colors[category] || "bg-slate-100 text-slate-700";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Content Strategy</h1>
          <p className="text-slate-600 mt-1">Create and manage content strategies for your Instagram posts</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadStrategies}
            className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          >
            Refresh
          </button>
          <button
            onClick={handleCreateNew}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            New Strategy
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Strategy List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading strategies...</div>
        </div>
      ) : strategies.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">🎯</div>
          <div className="text-slate-400 text-lg mb-2">No strategies yet</div>
          <div className="text-slate-500 text-sm mb-4">
            Create your first content strategy to guide your Instagram posting
          </div>
          <button
            onClick={handleCreateNew}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Create Your First Strategy
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {strategies.map((strategy) => (
            <div key={strategy.id} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(strategy.category || "general")}`}>
                      {strategy.category || "General"}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-800 text-lg">{strategy.name}</h3>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(strategy)}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(strategy.id)}
                    className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    Delete
                  </button>
                </div>
              </div>
              
              {strategy.description && (
                <p className="text-sm text-slate-600 mb-4">{strategy.description}</p>
              )}
              
              <div className="space-y-2 text-sm text-slate-500">
                <div className="flex justify-between">
                  <span>Created</span>
                  <span>{new Date(strategy.created_at).toLocaleDateString()}</span>
                </div>
                {strategy.updated_at && strategy.updated_at !== strategy.created_at && (
                  <div className="flex justify-between">
                    <span>Updated</span>
                    <span>{new Date(strategy.updated_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">
              {editingStrategy ? "Edit Strategy" : "Create New Strategy"}
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Strategy Name
                </label>
                <input
                  type="text"
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  placeholder="Enter strategy name..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Category
                </label>
                <select
                  value={strategyCategory}
                  onChange={(e) => setStrategyCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="general">General</option>
                  <option value="educational">Educational</option>
                  <option value="promotional">Promotional</option>
                  <option value="engagement">Engagement</option>
                  <option value="trending">Trending</option>
                  <option value="industry">Industry-Specific</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Description
                </label>
                <textarea
                  value={strategyDescription}
                  onChange={(e) => setStrategyDescription(e.target.value)}
                  placeholder="Describe your strategy..."
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {saving ? "Saving..." : (editingStrategy ? "Update" : "Create")}
              </button>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingStrategy(null);
                  setStrategyName("");
                  setStrategyDescription("");
                  setStrategyCategory("general");
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
