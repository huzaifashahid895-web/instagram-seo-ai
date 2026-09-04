import { useEffect, useState } from "react";
import { getRagDocuments, deleteRagDocument, createRagDocument } from "../services/api";
import type { RAGDocument, RAGChunk } from "../types/api";

type Props = {
  token: string;
};

export function KnowledgeBasePage({ token }: Props) {
  const [documents, setDocuments] = useState<RAGDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentName, setDocumentName] = useState("");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      setLoading(true);
      setError(null);
      const data = await getRagDocuments(token);
      setDocuments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile || !documentName.trim()) return;
    
    try {
      setUploading(true);
      setError(null);
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("document_name", documentName);
      await createRagDocument(token, formData);
      setShowUploadModal(false);
      setDocumentName("");
      setSelectedFile(null);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    
    try {
      setError(null);
      await deleteRagDocument(token, docId);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700",
      processing: "bg-blue-100 text-blue-700",
      completed: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
    };
    return colors[status] || "bg-slate-100 text-slate-700";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Knowledge Base</h1>
          <p className="text-slate-600 mt-1">RAG documents for AI context and content generation</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadDocuments}
            className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Upload Document
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Upload Document</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Document Name
                </label>
                <input
                  type="text"
                  value={documentName}
                  onChange={(e) => setDocumentName(e.target.value)}
                  placeholder="Enter document name..."
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  File
                </label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="text-xs text-slate-500 mt-1">
                  PDF, DOCX, TXT files supported
                </div>
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleUpload}
                disabled={uploading || !selectedFile || !documentName.trim()}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setDocumentName("");
                  setSelectedFile(null);
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

      {/* Documents Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-500">Loading documents...</div>
        </div>
      ) : documents.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-4xl mb-4">📚</div>
          <div className="text-slate-400 text-lg mb-2">No documents yet</div>
          <div className="text-slate-500 text-sm mb-4">
            Upload documents to build your knowledge base for AI content generation
          </div>
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Upload Your First Document
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map((doc) => (
            <div key={doc.id} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white text-xl font-bold">
                    {doc.filename.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800">{doc.document_name}</h3>
                    <p className="text-sm text-slate-500">{doc.filename}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="text-red-500 hover:text-red-700"
                  title="Delete document"
                >
                  🗑️
                </button>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Status</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(doc.status)}`}>
                    {doc.status}
                  </span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-slate-500">File Size</span>
                  <span className="font-medium text-slate-700">{formatFileSize(doc.file_size)}</span>
                </div>
                
                {doc.chunk_count !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Chunks</span>
                    <span className="font-medium text-slate-700">{doc.chunk_count}</span>
                  </div>
                )}
                
                <div className="flex justify-between">
                  <span className="text-slate-500">Uploaded</span>
                  <span className="font-medium text-slate-700">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              
              {doc.processing_error && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                  <div className="text-xs font-medium text-red-700 mb-1">Error:</div>
                  <div className="text-sm text-red-600">{doc.processing_error}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
