import { useEffect, useState } from "react";
import { uploadFile, getContentAssets, analyzeContent, deleteContentAsset } from "../services/api";
import type { ContentAsset } from "../types/api";

type Props = {
  token: string;
};

export function ContentLibraryPage({ token }: Props) {
  const [assets, setAssets] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAssets();
  }, []);

  async function loadAssets() {
    try {
      setLoading(true);
      const data = await getContentAssets(token);
      setAssets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assets");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile) return;
    
    try {
      setUploading(true);
      setError(null);
      const newAsset = await uploadFile(token, selectedFile);
      setAssets([newAsset, ...assets]);
      setSelectedFile(null);
      
      // Clear the file input
      const fileInput = document.getElementById("file-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyze(assetId: string) {
    try {
      setAnalyzing(assetId);
      setError(null);
      await analyzeContent(token, assetId);
      await loadAssets(); // Reload to get updated analysis
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(null);
    }
  }

  async function handleDelete(assetId: string) {
    if (!confirm("Delete this asset? This cannot be undone.")) return;
    
    try {
      await deleteContentAsset(token, assetId);
      setAssets(assets.filter(a => a.id !== assetId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function formatDuration(seconds?: number): string {
    if (!seconds) return "—";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading content library...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Content Library</h1>
        <div className="text-sm text-slate-500">{assets.length} assets</div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Upload Content</h2>
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label htmlFor="file-input" className="block text-sm font-medium text-slate-700 mb-2">
              Select File (Image, Video, or Audio)
            </label>
            <input
              id="file-input"
              type="file"
              accept="image/*,video/*,audio/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-500
                file:mr-4 file:py-2 file:px-4
                file:rounded file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
          </div>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>

      {/* Assets Grid */}
      {assets.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-slate-400 text-lg mb-2">No content yet</div>
          <div className="text-slate-500 text-sm">Upload your first video, image, or audio file to get started</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assets.map((asset) => (
            <div key={asset.id} className="bg-white rounded-lg shadow overflow-hidden">
              {/* Thumbnail or Type Badge */}
              <div className="h-48 bg-slate-100 flex items-center justify-center relative">
                {asset.thumbnail_path ? (
                  <img 
                    src={`http://localhost:8000${asset.thumbnail_path}`} 
                    alt={asset.filename}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-center">
                    <div className="text-4xl mb-2">
                      {asset.media_type === "video" && "🎥"}
                      {asset.media_type === "image" && "🖼️"}
                      {asset.media_type === "audio" && "🎵"}
                    </div>
                    <div className="text-sm text-slate-500 uppercase">{asset.media_type}</div>
                  </div>
                )}
                {!asset.processed && (
                  <div className="absolute top-2 right-2 bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">
                    Unprocessed
                  </div>
                )}
              </div>

              {/* Asset Details */}
              <div className="p-4">
                <h3 className="font-medium text-slate-800 truncate mb-2">{asset.filename}</h3>
                
                <div className="space-y-1 text-sm text-slate-600 mb-4">
                  <div className="flex justify-between">
                    <span>Size:</span>
                    <span>{formatFileSize(asset.file_size)}</span>
                  </div>
                  {asset.duration_seconds && (
                    <div className="flex justify-between">
                      <span>Duration:</span>
                      <span>{formatDuration(asset.duration_seconds)}</span>
                    </div>
                  )}
                  {asset.width && asset.height && (
                    <div className="flex justify-between">
                      <span>Dimensions:</span>
                      <span>{asset.width} × {asset.height}</span>
                    </div>
                  )}
                </div>

                {/* Transcript/Description Preview */}
                {asset.transcript && (
                  <div className="mb-4">
                    <div className="text-xs font-medium text-slate-700 mb-1">Transcript:</div>
                    <div className="text-xs text-slate-600 line-clamp-3 bg-slate-50 p-2 rounded">
                      {asset.transcript}
                    </div>
                  </div>
                )}

                {asset.visual_description && (
                  <div className="mb-4">
                    <div className="text-xs font-medium text-slate-700 mb-1">Description:</div>
                    <div className="text-xs text-slate-600 line-clamp-2 bg-slate-50 p-2 rounded">
                      {asset.visual_description}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAnalyze(asset.id)}
                    disabled={analyzing === asset.id}
                    className="flex-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-slate-300"
                  >
                    {analyzing === asset.id ? "Analyzing..." : "Analyze"}
                  </button>
                  <button
                    onClick={() => handleDelete(asset.id)}
                    className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
