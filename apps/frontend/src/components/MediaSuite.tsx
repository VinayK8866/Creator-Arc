"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";

type ActionType = "upscale" | "bg-removal";

export default function MediaSuite() {
  const [activeAction, setActiveAction] = useState<ActionType>("upscale");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [scale, setScale] = useState<number>(2);

  // Loading/Tracking state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("");

  // Comparative Previews
  const [originalPreview, setOriginalPreview] = useState<string>("");
  const [processedUrl, setProcessedUrl] = useState<string>("");

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImageUrl(""); // Clear URL input
      setOriginalPreview(URL.createObjectURL(file));
      setError("");
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setImageUrl(url);
    setImageFile(null); // Clear file input
    setOriginalPreview(url);
    setError("");
  };

  const startPolling = (id: string) => {
    setJobId(id);
    setJobStatus("pending");
    setLoading(true);

    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const job = await api.getJobStatus(id);
        setJobStatus(job.status);

        if (job.status === "completed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setLoading(false);
          setJobId(null);
          setProcessedUrl(job.result.output_url);
        } else if (job.status === "failed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setLoading(false);
          setJobId(null);
          setError(job.error || "Processing failed");
        }
      } catch (err: any) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        setLoading(false);
        setJobId(null);
        setError(err.message || "Failed to poll job status");
      }
    }, 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageFile && !imageUrl) {
      setError("Please upload an image file or paste an image link");
      return;
    }

    setError("");
    setLoading(true);
    setProcessedUrl("");

    const formData = new FormData();
    if (imageFile) {
      formData.append("file", imageFile);
    } else {
      formData.append("image_url", imageUrl);
    }

    try {
      let res;
      if (activeAction === "upscale") {
        formData.append("scale", scale.toString());
        res = await api.submitMediaUpscale(formData);
      } else {
        res = await api.submitMediaBgRemoval(formData);
      }

      if (res && res.job_id) {
        startPolling(res.job_id);
      } else {
        throw new Error("Job dispatch failed");
      }
    } catch (err: any) {
      setError(err.message || "Failed to trigger media processing");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Media Suite</h2>
          <p className="text-slate-400 text-sm">Enhance visual materials locally using background removing and upscaling models.</p>
        </div>

        {/* Toggle Controls */}
        <div className="flex p-1 rounded-lg glass-panel max-w-sm">
          <button
            onClick={() => { setActiveAction("upscale"); setError(""); }}
            className={`px-4 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              activeAction === "upscale" ? "bg-indigo-600/40 text-white border border-indigo-500/30" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Image Upscaler
          </button>
          <button
            onClick={() => { setActiveAction("bg-removal"); setError(""); }}
            className={`px-4 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              activeAction === "bg-removal" ? "bg-indigo-600/40 text-white border border-indigo-500/30" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            BG Remover
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side (Span 1): Settings */}
        <div className="glass-card rounded-xl p-6 space-y-4 h-fit">
          <h3 className="text-lg font-semibold text-slate-200 mb-2">Upload Asset</h3>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* File Drag Drop */}
            <div>
              <label className="block text-xs font-medium uppercase text-slate-400 mb-2">Upload Image File</label>
              <div className="border border-dashed border-slate-700 hover:border-indigo-500/50 transition-all rounded-lg p-6 text-center cursor-pointer relative bg-slate-900/10">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept="image/*"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={loading}
                />
                <svg
                  className="mx-auto h-8 w-8 text-slate-400 mb-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <p className="text-slate-300 text-xs font-medium">
                  {imageFile ? imageFile.name : "Click or drag image file here"}
                </p>
                <p className="text-slate-500 text-[10px] mt-1">PNG, JPG up to 10MB</p>
              </div>
            </div>

            <div className="text-center text-xs text-slate-500">OR</div>

            {/* URL input */}
            <div>
              <label className="block text-xs font-medium uppercase text-slate-400 mb-2">Paste Image URL</label>
              <input
                type="text"
                value={imageUrl}
                onChange={handleUrlChange}
                placeholder="https://example.com/image.png"
                className="w-full p-3 rounded-lg glass-input text-xs"
                disabled={loading}
              />
            </div>

            {/* Scale Choice for Upscaler */}
            {activeAction === "upscale" && (
              <div>
                <label className="block text-xs font-medium uppercase text-slate-400 mb-2">Scale Factor Choice</label>
                <div className="grid grid-cols-3 gap-2">
                  {[2, 3, 4].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setScale(val)}
                      className={`py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        scale === val
                          ? "bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 font-extrabold"
                          : "bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200"
                      }`}
                      disabled={loading}
                    >
                      {val}x
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg btn-gradient font-bold transition-all flex items-center justify-center cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : activeAction === "upscale" ? (
                "Run Upscaler"
              ) : (
                "Remove Background"
              )}
            </button>
          </form>
        </div>

        {/* Right Side (Span 2): Comparative Previews */}
        <div className="glass-card rounded-xl p-6 lg:col-span-2 flex flex-col justify-between min-h-[400px]">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3 mb-4">
            <h3 className="text-lg font-semibold text-slate-200">Comparison Output Canvas</h3>
            {loading && (
              <span className="text-xs text-indigo-400 flex items-center gap-1.5 font-semibold">
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                Status: {jobStatus || "queued"}
              </span>
            )}
          </div>

          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-3">
              <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <div className="space-y-1">
                <p className="text-slate-300 font-medium text-sm">Processing asset locally on worker...</p>
                <p className="text-slate-500 text-xs">This can take up to 10 seconds. Please hold on.</p>
              </div>
            </div>
          )}

          {!loading && !originalPreview && !processedUrl && (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm py-20 text-center">
              Upload an asset and run the model to view comparisons.
            </div>
          )}

          {!loading && (originalPreview || processedUrl) && (
            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
              {/* Original Preview */}
              {originalPreview && (
                <div className="space-y-2 text-center">
                  <span className="text-xs font-semibold uppercase text-slate-400">Original Image</span>
                  <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-950 flex items-center justify-center h-64">
                    <img
                      src={originalPreview}
                      alt="Original input"
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                </div>
              )}

              {/* Processed Output */}
              <div className="space-y-2 text-center">
                <span className="text-xs font-semibold uppercase text-slate-400">Processed Output</span>
                <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-950/40 checkerboard-bg flex items-center justify-center h-64">
                  {processedUrl ? (
                    <img
                      src={processedUrl}
                      alt="Processed output"
                      className="max-h-full max-w-full object-contain hover:scale-105 transition-all duration-300"
                    />
                  ) : (
                    <div className="text-slate-600 text-xs italic">
                      Waiting for worker completion...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {processedUrl && !loading && (
            <div className="flex justify-end gap-3 mt-6 border-t border-slate-800 pt-4">
              <a
                href={processedUrl}
                download={`processed_${Date.now()}.png`}
                target="_blank"
                rel="noreferrer"
                className="px-5 py-2.5 bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-xs font-bold rounded-lg transition-all cursor-pointer text-center"
              >
                Open Full Asset
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
