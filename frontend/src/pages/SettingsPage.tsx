import { useEffect, useState } from "react";
import { 
  getSocialAccounts, 
  getInstagramAuthUrl, 
  disconnectSocialAccount,
  getModelConfigs,
  createModelConfig,
  updateModelConfig,
  deleteModelConfig
} from "../services/api";
import type { SocialAccount, ModelConfig } from "../types/api";

type Props = {
  token: string;
};

export function SettingsPage({ token }: Props) {
  const [activeTab, setActiveTab] = useState<"accounts" | "models">("accounts");
  
  // Social Accounts state
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  
  // Model Configs state
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [showAddConfig, setShowAddConfig] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (activeTab === "models") {
      loadConfigs();
    }
  }, [activeTab]);

  async function loadAccounts() {
    try {
      setLoadingAccounts(true);
      const data = await getSocialAccounts(token);
      setAccounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load accounts");
    } finally {
      setLoadingAccounts(false);
    }
  }

  async function loadConfigs() {
    try {
      setLoadingConfigs(true);
      const data = await getModelConfigs(token);
      setConfigs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load configurations");
    } finally {
      setLoadingConfigs(false);
    }
  }

  async function handleConnectInstagram() {
    try {
      setError(null);
      const { auth_url } = await getInstagramAuthUrl(token);
      window.location.href = auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get auth URL");
    }
  }

  async function handleDisconnect(accountId: string) {
    if (!confirm("Disconnect this Instagram account?")) return;
    
    try {
      setError(null);
      await disconnectSocialAccount(token, accountId);
      await loadAccounts();
      setSuccess("Account disconnected successfully");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
    }
  }

  async function handleDeleteConfig(configId: string) {
    if (!confirm("Delete this model configuration?")) return;
    
    try {
      setError(null);
      await deleteModelConfig(token, configId);
      await loadConfigs();
      setSuccess("Configuration deleted successfully");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete configuration");
    }
  }

  async function handleToggleConfig(config: ModelConfig) {
    try {
      setError(null);
      await updateModelConfig(token, config.id, { is_active: !config.is_active });
      await loadConfigs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update configuration");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
        <p className="text-slate-600 mt-1">Manage your Instagram connections and AI model configurations</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {success}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab("accounts")}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === "accounts"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Instagram Accounts
          </button>
          <button
            onClick={() => setActiveTab("models")}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === "models"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            AI Model Configurations
          </button>
        </div>
      </div>

      {/* Instagram Accounts Tab */}
      {activeTab === "accounts" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-800">Connected Accounts</h2>
              <button
                onClick={handleConnectInstagram}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                + Connect Instagram Account
              </button>
            </div>

            {loadingAccounts ? (
              <div className="text-center py-8 text-slate-500">Loading accounts...</div>
            ) : accounts.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">📱</div>
                <div className="text-slate-600 mb-2">No Instagram accounts connected</div>
                <div className="text-slate-500 text-sm mb-4">
                  Connect your Instagram Business account to start automating your content
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {accounts.map((account) => (
                  <div key={account.id} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center text-white text-xl">
                          📷
                        </div>
                        <div>
                          <div className="font-semibold text-slate-800">@{account.account_name}</div>
                          <div className="text-sm text-slate-600">Platform: {account.platform}</div>
                          <div className="text-xs text-slate-500">
                            Connected {new Date(account.connected_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded-full text-sm ${
                          account.is_active 
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-100 text-slate-600"
                        }`}>
                          {account.is_active ? "Active" : "Inactive"}
                        </span>
                        <button
                          onClick={() => handleDisconnect(account.id)}
                          className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                        >
                          Disconnect
                        </button>
                      </div>
                    </div>

                    {account.last_synced_at && (
                      <div className="mt-3 text-xs text-slate-500">
                        Last synced: {new Date(account.last_synced_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 p-4 rounded">
            <h3 className="font-semibold text-blue-800 mb-2">How to Connect Instagram</h3>
            <ol className="list-decimal list-inside text-blue-700 text-sm space-y-1">
              <li>You need an Instagram Business or Creator account</li>
              <li>Your Instagram must be connected to a Facebook Page</li>
              <li>Click "Connect Instagram Account" above</li>
              <li>Log in to Facebook and authorize the app</li>
              <li>Select the Instagram account you want to connect</li>
            </ol>
          </div>
        </div>
      )}

      {/* AI Model Configurations Tab */}
      {activeTab === "models" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-800">AI Model Configurations</h2>
              <button
                onClick={() => setShowAddConfig(!showAddConfig)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {showAddConfig ? "Cancel" : "+ Add Configuration"}
              </button>
            </div>

            {showAddConfig && (
              <div className="mb-6 p-4 bg-slate-50 rounded border border-slate-200">
                <div className="text-sm text-slate-600 mb-2">
                  Add model configurations through the API or modify existing ones below.
                  Default configurations are created automatically.
                </div>
              </div>
            )}

            {loadingConfigs ? (
              <div className="text-center py-8 text-slate-500">Loading configurations...</div>
            ) : configs.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">⚙️</div>
                <div className="text-slate-600 mb-2">No model configurations</div>
                <div className="text-slate-500 text-sm">
                  Default configurations will be created automatically when needed
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {configs.map((config) => (
                  <div key={config.id} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-semibold text-slate-800 capitalize">
                            {config.capability}
                          </span>
                          {config.is_default && (
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                              Default
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-slate-600">
                          Provider: {config.provider} | Model: {config.model_name}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleConfig(config)}
                          className={`px-3 py-1 rounded text-sm ${
                            config.is_active
                              ? "bg-green-100 text-green-700 hover:bg-green-200"
                              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                          }`}
                        >
                          {config.is_active ? "Active" : "Inactive"}
                        </button>
                        <button
                          onClick={() => handleDeleteConfig(config.id)}
                          className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    {Object.keys(config.config_json).length > 0 && (
                      <details className="mt-3">
                        <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
                          Show configuration details
                        </summary>
                        <pre className="mt-2 text-xs bg-slate-100 p-2 rounded overflow-x-auto">
                          {JSON.stringify(config.config_json, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-50 border border-slate-200 p-4 rounded">
            <h3 className="font-semibold text-slate-800 mb-2">Available AI Capabilities</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              <div className="text-slate-700">• LLM (Text Generation)</div>
              <div className="text-slate-700">• Embeddings (Text → Vectors)</div>
              <div className="text-slate-700">• TTS (Text → Speech)</div>
              <div className="text-slate-700">• STT (Speech → Text)</div>
              <div className="text-slate-700">• Vision (Image Analysis)</div>
              <div className="text-slate-700">• Image Generation</div>
            </div>
            <div className="mt-3 text-xs text-slate-600">
              All capabilities use local, free, open-source models by default (Ollama, faster-whisper, Piper, CLIP, etc.)
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
