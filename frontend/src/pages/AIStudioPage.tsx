import { useState } from "react";
import { generateScript, generateCaption, produceVideo } from "../services/api";
import type { GeneratedScript, GeneratedCaption } from "../types/api";

type Props = {
  token: string;
};

export function AIStudioPage({ token }: Props) {
  const [activeTab, setActiveTab] = useState<"script" | "caption" | "video">("script");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Script generation state
  const [scriptPrompt, setScriptPrompt] = useState("");
  const [targetDuration, setTargetDuration] = useState(60);
  const [generatedScript, setGeneratedScript] = useState<GeneratedScript | null>(null);
  
  // Caption generation state
  const [captionContentId, setCaptionContentId] = useState("");
  const [generatedCaption, setGeneratedCaption] = useState<GeneratedCaption | null>(null);
  
  // Video production state
  const [videoScriptId, setVideoScriptId] = useState("");
  const [videoJobId, setVideoJobId] = useState<string | null>(null);

  async function handleGenerateScript() {
    if (!scriptPrompt.trim()) {
      setError("Please enter a script prompt");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await generateScript(token, scriptPrompt, targetDuration);
      setGeneratedScript(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate script");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateCaption() {
    if (!captionContentId.trim()) {
      setError("Please enter a content ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await generateCaption(token, captionContentId);
      setGeneratedCaption(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate caption");
    } finally {
      setLoading(false);
    }
  }

  async function handleProduceVideo() {
    if (!videoScriptId.trim()) {
      setError("Please enter a script ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await produceVideo(token, videoScriptId);
      setVideoJobId(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start video production");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">AI Studio</h1>
        <p className="text-slate-600 mt-1">Generate scripts, captions, and produce videos with AI</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab("script")}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === "script"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Script Generator
          </button>
          <button
            onClick={() => setActiveTab("caption")}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === "caption"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Caption Generator
          </button>
          <button
            onClick={() => setActiveTab("video")}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === "video"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Video Production
          </button>
        </div>
      </div>

      {/* Script Generator Tab */}
      {activeTab === "script" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Generate Video Script</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Script Prompt
                </label>
                <textarea
                  value={scriptPrompt}
                  onChange={(e) => setScriptPrompt(e.target.value)}
                  placeholder="Describe the video you want to create... (e.g., 'Create a tutorial about Instagram marketing tips')"
                  rows={4}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Target Duration (seconds)
                </label>
                <input
                  type="number"
                  value={targetDuration}
                  onChange={(e) => setTargetDuration(parseInt(e.target.value))}
                  min="15"
                  max="300"
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                onClick={handleGenerateScript}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {loading ? "Generating..." : "Generate Script"}
              </button>
            </div>
          </div>

          {generatedScript && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-800">Generated Script</h3>
                <span className="text-sm text-slate-500">
                  ID: {generatedScript.id}
                </span>
              </div>
              
              <div className="bg-slate-50 p-4 rounded mb-4">
                <div className="text-sm text-slate-600 mb-2">
                  <strong>Prompt:</strong> {generatedScript.prompt}
                </div>
                {generatedScript.estimated_duration_seconds && (
                  <div className="text-sm text-slate-600">
                    <strong>Estimated Duration:</strong> {generatedScript.estimated_duration_seconds}s
                  </div>
                )}
              </div>

              <div className="prose max-w-none">
                <pre className="whitespace-pre-wrap bg-white border border-slate-200 p-4 rounded text-sm">
                  {generatedScript.script_text}
                </pre>
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(generatedScript.script_text);
                    alert("Script copied to clipboard!");
                  }}
                  className="px-4 py-2 bg-slate-600 text-white rounded hover:bg-slate-700"
                >
                  Copy Script
                </button>
                <button
                  onClick={() => setVideoScriptId(generatedScript.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Use for Video Production
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Caption Generator Tab */}
      {activeTab === "caption" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Generate Caption</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Content ID
                </label>
                <input
                  type="text"
                  value={captionContentId}
                  onChange={(e) => setCaptionContentId(e.target.value)}
                  placeholder="Enter content asset ID"
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Get the content ID from the Content Library page
                </p>
              </div>

              <button
                onClick={handleGenerateCaption}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {loading ? "Generating..." : "Generate Caption"}
              </button>
            </div>
          </div>

          {generatedCaption && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Generated Caption</h3>
              
              <div className="bg-slate-50 p-4 rounded mb-4">
                <div className="text-sm text-slate-600 mb-2">
                  <strong>Platform:</strong> {generatedCaption.platform}
                </div>
                <div className="text-sm text-slate-600">
                  <strong>Content ID:</strong> {generatedCaption.content_id}
                </div>
              </div>

              <div className="bg-white border border-slate-200 p-4 rounded">
                <p className="whitespace-pre-wrap">{generatedCaption.caption_text}</p>
              </div>

              <button
                onClick={() => {
                  navigator.clipboard.writeText(generatedCaption.caption_text);
                  alert("Caption copied to clipboard!");
                }}
                className="mt-4 px-4 py-2 bg-slate-600 text-white rounded hover:bg-slate-700"
              >
                Copy Caption
              </button>
            </div>
          )}
        </div>
      )}

      {/* Video Production Tab */}
      {activeTab === "video" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Produce Video</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Script ID
                </label>
                <input
                  type="text"
                  value={videoScriptId}
                  onChange={(e) => setVideoScriptId(e.target.value)}
                  placeholder="Enter generated script ID"
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Generate a script first, then use its ID here
                </p>
              </div>

              <button
                onClick={handleProduceVideo}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-slate-300"
              >
                {loading ? "Starting Production..." : "Produce Video"}
              </button>
            </div>
          </div>

          {videoJobId && (
            <div className="bg-green-50 border border-green-200 p-4 rounded">
              <h3 className="font-semibold text-green-800 mb-2">Video Production Started!</h3>
              <p className="text-green-700 text-sm mb-2">Job ID: {videoJobId}</p>
              <p className="text-green-600 text-sm">
                Your video is being produced in the background. This may take several minutes depending on the length.
                Check the Content Library for the completed video.
              </p>
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 p-4 rounded">
            <h3 className="font-semibold text-blue-800 mb-2">How Video Production Works</h3>
            <ol className="list-decimal list-inside text-blue-700 text-sm space-y-1">
              <li>Generate a script using the Script Generator tab</li>
              <li>Copy the script ID and paste it here</li>
              <li>Click "Produce Video" to start the production</li>
              <li>The system will generate TTS audio, create visuals, and combine them</li>
              <li>Find the completed video in your Content Library</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
