"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";

type JobType = "summary" | "tags" | "description";

export default function YouTubeSuite() {
  const [videoUrl, setVideoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Job tracking
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("");
  const [jobType, setJobType] = useState<JobType | null>(null);
  const [method, setMethod] = useState<string>("");

  // Results
  const [summary, setSummary] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [description, setDescription] = useState("");
  
  const [copied, setCopied] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Stop polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const startPolling = (id: string, type: JobType) => {
    setJobId(id);
    setJobStatus("pending");
    setJobType(type);
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
          
          if (type === "summary") {
            setSummary(job.result.summary);
            setMethod(job.result.processing_method || "transcript");
          } else if (type === "tags") {
            setTags(job.result.tags || []);
          } else if (type === "description") {
            setDescription(job.result.description);
          }
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
        setError(err.message || "Failed to fetch status updates");
      }
    }, 3000); // Poll every 3 seconds
  };

  const triggerJob = async (type: JobType) => {
    if (!videoUrl) {
      setError("Please paste a valid YouTube video link");
      return;
    }
    
    setError("");
    setLoading(true);
    setSummary("");
    setTags([]);
    setDescription("");

    try {
      let res;
      if (type === "summary") {
        res = await api.submitYouTubeSummary(videoUrl);
      } else if (type === "tags") {
        res = await api.submitYouTubeTags(videoUrl);
      } else {
        res = await api.submitYouTubeDescription(videoUrl);
      }

      if (res && res.job_id) {
        startPolling(res.job_id, type);
      } else {
        throw new Error("Job dispatch failed");
      }
    } catch (err: any) {
      setError(err.message || "Failed to trigger YouTube processing");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">YouTube Suite</h2>
        <p className="text-slate-400 text-sm">Paste a video link to scrape captions or download the audio to transcribe and summarize.</p>
      </div>

      {/* Input bar */}
      <div className="glass-card rounded-xl p-6 space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">YouTube Video URL</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ"
              className="flex-1 p-3 rounded-lg glass-input text-sm"
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => triggerJob("summary")}
            disabled={loading}
            className="px-6 py-3 rounded-lg btn-gradient font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            Generate Summary
          </button>
          <button
            onClick={() => triggerJob("tags")}
            disabled={loading}
            className="px-6 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            Extract SEO Tags
          </button>
          <button
            onClick={() => triggerJob("description")}
            disabled={loading}
            className="px-6 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            Draft Video Description
          </button>
        </div>

        {error && (
          <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20">
            {error}
          </div>
        )}
      </div>

      {/* Job status and loading overlay */}
      {loading && (
        <div className="glass-card rounded-xl p-8 text-center space-y-4 glow-indigo animate-pulse">
          <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto" />
          <div className="space-y-1">
            <h3 className="text-slate-200 font-semibold uppercase text-xs tracking-wider">
              Background Job Running
            </h3>
            <p className="text-slate-400 text-sm">
              Status: <span className="text-indigo-400 font-bold uppercase">{jobStatus || "queued"}</span>
            </p>
          </div>
          <p className="text-slate-500 text-xs max-w-md mx-auto">
            {jobStatus === "pending" && "Waiting for an idle Celery background worker..."}
            {jobStatus === "processing" && "Worker active. Scraping captions or downloading YouTube audio stream..."}
          </p>
        </div>
      )}

      {/* Output Panel */}
      {(!loading) && (summary || tags.length > 0 || description) && (
        <div className="glass-card rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 className="text-lg font-semibold text-slate-200">
              {summary && "Video Summary Report"}
              {tags.length > 0 && "SEO Tags Report"}
              {description && "SEO Video Description Draft"}
            </h3>

            {summary && method && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-indigo-400 border border-slate-700">
                Method: {method === "multimodal_audio" ? "Multimodal Audio" : "Text Captions"}
              </span>
            )}
          </div>

          <div className="bg-slate-900/40 p-5 rounded-lg border border-slate-800 min-h-[150px]">
            {summary && (
              <div className="space-y-4">
                <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{summary}</p>
                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => handleCopy(summary, "copy-summary")}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    {copied === "copy-summary" ? "Copied!" : "Copy Summary"}
                  </button>
                </div>
              </div>
            )}

            {tags.length > 0 && (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag, idx) => (
                    <span key={idx} className="px-3 py-1 bg-indigo-500/10 text-indigo-300 rounded-full border border-indigo-500/20 text-xs">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex justify-end pt-4">
                  <button
                    onClick={() => handleCopy(tags.join(", "), "copy-tags")}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    {copied === "copy-tags" ? "Copied!" : "Copy Tags String"}
                  </button>
                </div>
              </div>
            )}

            {description && (
              <div className="space-y-4">
                <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-mono">{description}</p>
                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => handleCopy(description, "copy-desc")}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    {copied === "copy-desc" ? "Copied!" : "Copy Description"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
