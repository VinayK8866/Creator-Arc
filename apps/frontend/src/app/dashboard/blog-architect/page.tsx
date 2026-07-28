"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface ChunkResult {
  chunk_index: number;
  heading: string;
  humanized_text: string;
  score: number;
  nli_score: number;
}

interface Platform {
  platform: string;
  display_name: string;
  storytelling_cadence: string;
  heading_style: string;
  layout_constraints: any;
}

interface PerformanceSnapshotItem {
  id: string;
  week: number;
  screenshot_url: string;
  metrics: any;
  confidence: number;
  created_at: string;
}

interface LearnedInsightItem {
  id: string;
  insight_type: string;
  rule_id?: string;
  insight_text: string;
  confidence_score: number;
  sample_size: number;
  avg_read_ratio?: number;
  avg_views?: number;
  is_active: boolean;
}

export default function BlogArchitect() {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("medium");
  const [tone, setTone] = useState("human-like");
  const [platforms, setPlatforms] = useState<Platform[]>([
    { platform: "medium", display_name: "Medium", storytelling_cadence: "Deep storytelling cadence", heading_style: "H2/H3 balancing", layout_constraints: {} },
    { platform: "substack", display_name: "Substack", storytelling_cadence: "Editorial prose", heading_style: "H2 subheadings", layout_constraints: {} },
    { platform: "reddit", display_name: "Reddit", storytelling_cadence: "First-person narrative", heading_style: "Dividers & Linebreaks", layout_constraints: {} },
    { platform: "quora", display_name: "Quora", storytelling_cadence: "Authoritative QA", heading_style: "Step lists", layout_constraints: {} },
    { platform: "wordpress", display_name: "WordPress", storytelling_cadence: "Formal corporate layout", heading_style: "SEO Headings", layout_constraints: {} },
    { platform: "squarespace", display_name: "Squarespace", storytelling_cadence: "Modern concise paragraphs", heading_style: "SEO Headings", layout_constraints: {} },
    { platform: "wix", display_name: "Wix", storytelling_cadence: "Lifestyle-blog layout", heading_style: "SEO Headings", layout_constraints: {} }
  ]);

  // Loading/Progress States
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  
  // Real-time Chunks & Result
  const [suggestedTitle, setSuggestedTitle] = useState("");
  const [seoKeywords, setSeoKeywords] = useState<string[]>([]);
  const [chunks, setChunks] = useState<ChunkResult[]>([]);
  const [finalPost, setFinalPost] = useState("");
  const [copied, setCopied] = useState(false);

  // History / Recent posts
  const [history, setHistory] = useState<any[]>([]);
  const [activePostId, setActivePostId] = useState<string | null>(null);

  // Performance & Self-Learning States
  const [perfSummary, setPerfSummary] = useState<any>(null);
  const [learnedInsights, setLearnedInsights] = useState<LearnedInsightItem[]>([]);
  const [showInsights, setShowInsights] = useState(false);

  // Modals
  const [publishingPost, setPublishingPost] = useState<any | null>(null);
  const [publishedUrlInput, setPublishedUrlInput] = useState("");
  const [publicationNameInput, setPublicationNameInput] = useState("");
  const [isSubmittingPublish, setIsSubmittingPublish] = useState(false);

  const [snapshotPost, setSnapshotPost] = useState<any | null>(null);
  const [snapshotFile, setSnapshotFile] = useState<File | null>(null);
  const [isUploadingSnapshot, setIsUploadingSnapshot] = useState(false);
  const [extractedOcrResult, setExtractedOcrResult] = useState<any | null>(null);

  useEffect(() => {
    fetchPlatformsAndHistory();
    fetchPerformanceDetails();
  }, []);

  const fetchPlatformsAndHistory = async () => {
    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const headers = {
        "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
      };

      const platRes = await fetch(`${BASE_URL}/blog/platforms`, { headers });
      if (platRes.ok) {
        const data = await platRes.json();
        if (data && data.length > 0) setPlatforms(data);
      }

      const histRes = await fetch(`${BASE_URL}/blog/posts`, { headers });
      if (histRes.ok) {
        const data = await histRes.json();
        setHistory(data || []);
      }
    } catch (err) {
      console.error("Failed to load static details", err);
    }
  };

  const fetchPerformanceDetails = async () => {
    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const headers = {
        "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
      };

      const sumRes = await fetch(`${BASE_URL}/blog/performance-summary`, { headers });
      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setPerfSummary(sumData);
      }

      const insRes = await fetch(`${BASE_URL}/blog/insights`, { headers });
      if (insRes.ok) {
        const insData = await insRes.json();
        setLearnedInsights(insData || []);
      }
    } catch (err) {
      console.error("Failed to fetch performance details", err);
    }
  };

  const handleMarkPublishedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publishingPost) return;

    setIsSubmittingPublish(true);
    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const headers = {
        "Content-Type": "application/json",
        "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
      };

      const res = await fetch(`${BASE_URL}/blog/posts/${publishingPost.id}/publish`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({
          published_url: publishedUrlInput,
          publication_name: publicationNameInput
        })
      });

      if (res.ok) {
        setPublishingPost(null);
        setPublishedUrlInput("");
        setPublicationNameInput("");
        fetchPlatformsAndHistory();
        fetchPerformanceDetails();
      } else {
        alert("Failed to mark post as published");
      }
    } catch (err: any) {
      alert(err.message || "Failed to publish");
    } finally {
      setIsSubmittingPublish(false);
    }
  };

  const handleUploadSnapshotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!snapshotPost || !snapshotFile) return;

    setIsUploadingSnapshot(true);
    setExtractedOcrResult(null);

    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const formData = new FormData();
      formData.append("file", snapshotFile);

      const res = await fetch(`${BASE_URL}/blog/posts/${snapshotPost.id}/snapshot`, {
        method: "POST",
        headers: {
          "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
        },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setExtractedOcrResult(data.extracted_metrics);
        fetchPerformanceDetails();
        fetchPlatformsAndHistory();
      } else {
        alert("Failed to extract snapshot data");
      }
    } catch (err: any) {
      alert(err.message || "Upload failed");
    } finally {
      setIsUploadingSnapshot(false);
    }
  };

  const handleDelete = async (postId: string) => {
    if (!window.confirm("Are you sure you want to delete this blog post from history?")) {
      return;
    }

    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const headers = {
        "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
      };

      const res = await fetch(`${BASE_URL}/blog/posts/${postId}`, {
        method: "DELETE",
        headers,
      });

      if (res.ok) {
        fetchPlatformsAndHistory();
        if (activePostId === postId) {
          setActivePostId(null);
          setSuggestedTitle("");
          setSeoKeywords([]);
          setFinalPost("");
          setChunks([]);
        }
      } else {
        const errText = await res.text();
        alert(`Failed to delete post: ${errText}`);
      }
    } catch (err: any) {
      alert(`Error deleting post: ${err.message || "Unknown error"}`);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError("Please specify a core idea or topic.");
      return;
    }

    setLoading(true);
    setError("");
    setStatusMessage("Connecting to Blog Architect service...");
    setProgress(5);
    setChunks([]);
    setSuggestedTitle("");
    setSeoKeywords([]);
    setFinalPost("");

    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${BASE_URL}/blog/generate-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
        },
        body: JSON.stringify({ topic, platform, tone }),
      });

      if (!response.ok) {
        const errText = await response.text();
        let errMsg = "Generation failed";
        try {
          errMsg = JSON.parse(errText).detail || errMsg;
        } catch {
          errMsg = errText || errMsg;
        }
        throw new Error(errMsg);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("Stream reader not available.");

      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "message";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event:")) {
            currentEvent = trimmed.replace("event:", "").trim();
          } else if (trimmed.startsWith("data:")) {
            const rawData = trimmed.replace("data:", "").trim();
            try {
              const data = JSON.parse(rawData);

              if (currentEvent === "status") {
                setStatusMessage(data.message);
                if (data.progress) setProgress(data.progress);
              } else if (currentEvent === "factual_base") {
                setSuggestedTitle(data.suggested_title);
                setSeoKeywords(data.seo_keywords);
              } else if (currentEvent === "chunk_completed") {
                setChunks((prev) => {
                  if (prev.some((c) => c.chunk_index === data.chunk_index)) return prev;
                  return [...prev, data];
                });
              } else if (currentEvent === "completed") {
                setFinalPost(data.full_content);
                setActivePostId(data.post_id);
                setProgress(100);
                setStatusMessage("Blog post completed successfully!");
              } else if (currentEvent === "error") {
                throw new Error(data.detail || "Error occurred during generation");
              }
            } catch (e: any) {
              console.error("Failed to parse event data", e);
            }
          }
        }
      }

      fetchPlatformsAndHistory();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during execution.");
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(finalPost);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([finalPost], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${topic.replace(/\s+/g, "_").toLowerCase()}_blog.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const selectPlatformDetails = platforms.find((p) => p.platform === platform);

  return (
    <div className="min-h-screen bg-[#05060b] text-slate-100 p-6 md:p-10 relative">
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-900/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-purple-900/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-6xl mx-auto space-y-8 relative z-10">
        {/* Header Breadcrumb */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold uppercase tracking-wider">
              <Link href="/" className="hover:text-indigo-300 transition-colors">Workspace Hub</Link>
              <span>/</span>
              <span className="text-slate-400">Blog Architect</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <span className="bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">Blog Architect</span>
              <span className="text-xs font-semibold px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded-full">v1.3 Feedback Loop</span>
            </h1>
            <p className="text-slate-400 text-sm">
              Topic-to-blog content feeder matching regional dialect exemplars, medium strategy rules, and self-learning performance feedback.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowInsights(!showInsights)}
              className="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-lg"
            >
              <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Self-Learning Insights ({learnedInsights.length})
            </button>

            <Link
              href="/"
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800/80 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-lg"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Dashboard
            </Link>
          </div>
        </div>

        {/* Weekly Screenshot Prompt Banner */}
        {perfSummary && perfSummary.due_for_snapshot && perfSummary.due_for_snapshot.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center shrink-0 font-bold">
                📸
              </div>
              <div>
                <h4 className="text-sm font-bold text-amber-200">Weekly Performance Update Due</h4>
                <p className="text-xs text-amber-300/80">
                  {perfSummary.due_for_snapshot.length} published blog post(s) require a stats screenshot update from Medium to evolve the self-learning model.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {perfSummary.due_for_snapshot.map((p: any) => (
                <button
                  key={p.post_id}
                  onClick={() => setSnapshotPost(p)}
                  className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-bold rounded-lg border border-amber-500/40 transition-all flex items-center gap-1.5"
                >
                  Upload Stats for &quot;{p.title.substring(0, 18)}...&quot;
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Self-Learning Insights Drawer */}
        {showInsights && (
          <div className="glass-card rounded-2xl p-6 border border-indigo-500/20 shadow-2xl space-y-4 animate-in fade-in duration-300">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse" />
                  Self-Learning System Prompt Learnings
                </h3>
                <p className="text-xs text-slate-400">
                  These insights are automatically derived by correlating your Medium stats screenshots with the 228 Medium Strategy rules, and are injected into all future blog generations.
                </p>
              </div>
              <button
                onClick={() => setShowInsights(false)}
                className="text-slate-500 hover:text-slate-300 text-xs font-bold px-2 py-1 bg-slate-900 rounded-lg"
              >
                Close
              </button>
            </div>

            {learnedInsights.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-4">
                No performance insights recorded yet. Mark generated blog posts as &quot;Published&quot; and upload weekly stats screenshots to begin self-learning!
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {learnedInsights.map((ins) => (
                  <div key={ins.id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded">
                        {ins.insight_type} {ins.rule_id ? `(${ins.rule_id})` : ""}
                      </span>
                      <span className="text-xs font-mono text-emerald-400 font-bold">
                        Confidence: {(ins.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">
                      {ins.insight_text}
                    </p>
                    {ins.avg_read_ratio && (
                      <p className="text-[11px] text-slate-400 font-mono">
                        Avg Read Ratio: {(ins.avg_read_ratio * 100).toFixed(1)}% ({ins.sample_size} posts analyzed)
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Workspace Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left panel: Input config & History (4 cols) */}
          <div className="lg:col-span-4 space-y-6">
            <div className="glass-card rounded-2xl p-6 border border-slate-800/60 shadow-xl space-y-6">
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 status-glow" />
                Configure Generator
              </h3>

              <form onSubmit={handleGenerate} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-400 mb-2">
                    Topic / Core Idea
                  </label>
                  <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. UPI digital infrastructure development in rural India or Celery workers handling task backlogs."
                    rows={4}
                    disabled={loading}
                    className="w-full p-3.5 rounded-xl glass-input text-sm resize-none focus:border-indigo-500/40 text-slate-300 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-slate-400 mb-2">
                    Target Platform
                  </label>
                  <select
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value)}
                    disabled={loading}
                    className="w-full p-3 rounded-xl glass-input text-xs font-medium cursor-pointer"
                  >
                    {platforms.map((p) => (
                      <option key={p.platform} value={p.platform}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-slate-400 mb-2">
                    Tone Setting
                  </label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    disabled={loading}
                    className="w-full p-3 rounded-xl glass-input text-xs font-medium cursor-pointer"
                  >
                    <option value="human-like">Human-like (Casual, relatable)</option>
                    <option value="professional">Professional & Technical</option>
                    <option value="engaging">Engaging Storyteller</option>
                    <option value="witty">Witty & Humorous</option>
                  </select>
                </div>

                {selectPlatformDetails && (
                  <div className="p-3 bg-indigo-950/10 border border-indigo-500/5 rounded-xl space-y-1">
                    <p className="text-[10px] text-slate-400 uppercase font-semibold">Platform Style Map</p>
                    <p className="text-xs text-indigo-300 font-semibold">{selectPlatformDetails.display_name}</p>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {selectPlatformDetails.storytelling_cadence}. Layout: {selectPlatformDetails.heading_style}
                    </p>
                  </div>
                )}

                {error && (
                  <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-xl border border-rose-500/25">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 rounded-xl btn-gradient font-extrabold text-sm transition-all flex items-center justify-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Generating Blog...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Construct & Feed Chunks
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* History List with Publication Status & Screenshot Upload Trigger */}
            <div className="glass-card rounded-2xl p-5 border border-slate-800/60 shadow-xl space-y-4 max-h-[420px] overflow-y-auto">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex justify-between items-center">
                <span>Article Storage & History</span>
                <span className="text-[10px] text-indigo-400 font-normal">{history.length} posts</span>
              </h4>

              {history.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No posts generated yet.</p>
              ) : (
                <div className="space-y-3">
                  {history.map((post) => {
                    const isPublished = post.publication_status === "published";

                    return (
                      <div
                        key={post.id}
                        className={`group w-full flex flex-col p-3 rounded-xl border text-xs transition-all space-y-2 ${
                          activePostId === post.id
                            ? "bg-slate-900 border-indigo-500/40"
                            : "bg-slate-950/40 border-slate-800/80 hover:bg-slate-900/60"
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <button
                            onClick={() => {
                              setActivePostId(post.id);
                              setSuggestedTitle(post.suggested_title);
                              setSeoKeywords(post.seo_keywords || []);
                              setFinalPost(post.humanized_content || "");
                              setChunks(post.content_chunks || []);
                            }}
                            className="text-left space-y-0.5 flex-1 pr-2"
                          >
                            <p className="font-semibold text-slate-200 line-clamp-1">{post.suggested_title || post.topic}</p>
                            <p className="text-[10px] text-slate-500 capitalize">{post.platform} • {new Date(post.created_at).toLocaleDateString()}</p>
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(post.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 rounded transition-all"
                            title="Delete Post"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>

                        {/* Publication Status Actions */}
                        <div className="flex items-center justify-between pt-1 border-t border-slate-900 text-[10px]">
                          {isPublished ? (
                            <span className="text-emerald-400 font-bold flex items-center gap-1">
                              ✓ Published
                            </span>
                          ) : (
                            <button
                              onClick={() => setPublishingPost(post)}
                              className="text-indigo-400 hover:text-indigo-300 font-bold underline"
                            >
                              Mark as Published?
                            </button>
                          )}

                          {isPublished && (
                            <button
                              onClick={() => setSnapshotPost(post)}
                              className="px-2 py-0.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded font-semibold transition-all"
                            >
                              Upload Weekly Stats
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right panel: Active Feed & Output (8 cols) */}
          <div className="lg:col-span-8 space-y-6 flex flex-col">
            
            {/* Live Progress Indicator / Pipeline Stepper */}
            {loading && (
              <div className="glass-card rounded-2xl p-6 border border-indigo-500/10 shadow-xl space-y-4 animate-in fade-in duration-300">
                <div className="flex justify-between items-center">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-slate-400">Current Phase Operations</p>
                    <p className="text-sm font-bold text-indigo-400 animate-pulse">{statusMessage || "Running..."}</p>
                  </div>
                  <span className="text-xs font-bold text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">{progress}%</span>
                </div>
                
                {/* Visual Progress Bar */}
                <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                    style={{ width: `${progress}%` }}
                  />
                </div>

                {/* Progress Logs */}
                <div className="grid grid-cols-3 gap-2 text-center text-[10px] text-slate-500 font-bold uppercase pt-1">
                  <div className={`transition-colors ${progress >= 10 ? "text-indigo-400" : ""}`}>1. Factual Base</div>
                  <div className={`transition-colors ${progress >= 30 ? "text-indigo-400" : ""}`}>2. Feeder Engine</div>
                  <div className={`transition-colors ${progress >= 95 ? "text-indigo-400" : ""}`}>3. Compiler</div>
                </div>
              </div>
            )}

            {/* Factual Structure Overview */}
            {(suggestedTitle || seoKeywords.length > 0) && (
              <div className="glass-card rounded-2xl p-6 border border-slate-800/60 shadow-xl space-y-4">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-slate-800/60 pb-3">
                  <div>
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Suggested Title</span>
                    <h2 className="text-xl font-bold text-slate-100">{suggestedTitle || "Draft Title"}</h2>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {seoKeywords.map((kw, i) => (
                      <span key={i} className="text-[10px] bg-slate-900 border border-slate-800/80 px-2 py-0.5 rounded text-slate-400">
                        #{kw}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Processed Chunks Metrics List */}
                <div className="space-y-3">
                  <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Feeder Pipeline Outputs</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {chunks.map((c, i) => {
                      const isHighAi = c.score > 0.35;
                      const isWeakFactual = c.nli_score < 0.85;

                      return (
                        <div key={i} className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 flex flex-col justify-between space-y-3 shadow-inner">
                          <div>
                            <p className="text-xs text-slate-400 font-bold uppercase truncate">Chunk {i+1}</p>
                            <h5 className="text-sm font-semibold text-slate-200 truncate mt-0.5">{c.heading}</h5>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-2 text-center text-[10px] border-t border-slate-900 pt-2.5">
                            <div>
                              <p className="text-slate-500 font-semibold uppercase">AI likelihood</p>
                              <p className={`font-mono font-bold text-xs mt-0.5 ${isHighAi ? "text-rose-400" : "text-emerald-400"}`}>
                                {c.score.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-500 font-semibold uppercase">Fact Alignment</p>
                              <p className={`font-mono font-bold text-xs mt-0.5 ${isWeakFactual ? "text-rose-400" : "text-emerald-400"}`}>
                                {c.nli_score.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {loading && chunks.length === 0 && (
                      <div className="col-span-full py-6 text-center text-slate-500 text-xs italic">
                        Structuring factual base... Waiting for sequential feeder checks to start.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Generated output canvas */}
            <div className="glass-card rounded-2xl border border-slate-800/60 shadow-xl overflow-hidden flex-1 flex flex-col min-h-[400px]">
              
              {/* Output Toolbar */}
              <div className="bg-slate-900/30 p-4 border-b border-slate-800/60 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/60" />
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Compiled Article (Markdown)</h3>
                </div>
                {finalPost && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopy}
                      className="px-3 py-1.5 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700/80 flex items-center gap-1.5 cursor-pointer transition-all"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      {copied ? "Copied!" : "Copy"}
                    </button>

                    <button
                      onClick={handleDownload}
                      className="px-3 py-1.5 text-[10px] bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 rounded-lg border border-indigo-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download .md
                    </button>
                  </div>
                )}
              </div>

              {/* Editor Workspace */}
              <div className="flex-1 p-6 bg-slate-950/20 overflow-y-auto max-h-[500px]">
                {finalPost ? (
                  <textarea
                    value={finalPost}
                    onChange={(e) => setFinalPost(e.target.value)}
                    rows={20}
                    className="w-full h-full bg-transparent border-0 outline-none text-slate-300 font-mono text-sm leading-relaxed resize-none"
                  />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-16 h-16 rounded-2xl bg-slate-800/40 border border-slate-700/20 flex items-center justify-center mb-4">
                      <svg className="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <p className="text-slate-500 text-sm font-medium">Outliner & Content Generator Ready</p>
                    <p className="text-slate-600 text-[10px] mt-1 max-w-[240px]">
                      Enter your topic and platform options to generate a fully factual, humanized blog post chunk-by-chunk.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal 1: Mark as Published */}
      {publishingPost && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 rounded-2xl border border-slate-800 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Mark Post as Published</h3>
            <p className="text-xs text-slate-400">
              Confirm that &quot;{publishingPost.suggested_title || publishingPost.topic}&quot; has been published on {publishingPost.platform}.
            </p>

            <form onSubmit={handleMarkPublishedSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">Published Live URL</label>
                <input
                  type="url"
                  placeholder="https://medium.com/@username/your-article-slug"
                  value={publishedUrlInput}
                  onChange={(e) => setPublishedUrlInput(e.target.value)}
                  className="w-full p-3 rounded-xl glass-input text-xs text-slate-200"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">Publication Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. The Startup, Towards Data Science"
                  value={publicationNameInput}
                  onChange={(e) => setPublicationNameInput(e.target.value)}
                  className="w-full p-3 rounded-xl glass-input text-xs text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPublishingPost(null)}
                  className="px-4 py-2 bg-slate-900 text-slate-400 hover:text-slate-200 text-xs font-bold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingPublish}
                  className="px-4 py-2 btn-gradient text-xs font-bold rounded-xl"
                >
                  {isSubmittingPublish ? "Saving..." : "Confirm Published"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Upload Weekly Stats Screenshot */}
      {snapshotPost && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-lg w-full p-6 rounded-2xl border border-slate-800 shadow-2xl space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-bold text-white">Upload Weekly Performance Screenshot</h3>
              <button onClick={() => setSnapshotPost(null)} className="text-slate-500 hover:text-white text-xs">✕</button>
            </div>
            
            <p className="text-xs text-slate-400">
              Upload a screenshot of your Medium stats page for &quot;{snapshotPost.suggested_title || snapshotPost.topic}&quot;. Gemini Vision will OCR-extract your views, reads, and read ratio to evolve the generator.
            </p>

            <form onSubmit={handleUploadSnapshotSubmit} className="space-y-4">
              <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl p-6 text-center cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setSnapshotFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-indigo-600/20 file:text-indigo-300 hover:file:bg-indigo-600/30"
                />
              </div>

              {extractedOcrResult && (
                <div className="p-4 bg-slate-950 rounded-xl border border-indigo-500/30 space-y-2 text-xs">
                  <p className="font-bold text-indigo-300 uppercase tracking-wider text-[10px]">Gemini Vision Extracted Metrics</p>
                  <div className="grid grid-cols-3 gap-2 text-center font-mono">
                    <div className="bg-slate-900 p-2 rounded">
                      <span className="text-slate-500 block text-[9px]">VIEWS</span>
                      <span className="text-white font-bold">{extractedOcrResult.views}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded">
                      <span className="text-slate-500 block text-[9px]">READS</span>
                      <span className="text-white font-bold">{extractedOcrResult.reads}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded">
                      <span className="text-slate-500 block text-[9px]">READ RATIO</span>
                      <span className="text-emerald-400 font-bold">{((extractedOcrResult.read_ratio || 0) * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-400 italic mt-1">Self-learning feedback loop updated!</p>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSnapshotPost(null)}
                  className="px-4 py-2 bg-slate-900 text-slate-400 text-xs font-bold rounded-xl"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={!snapshotFile || isUploadingSnapshot}
                  className="px-4 py-2 btn-gradient text-xs font-bold rounded-xl disabled:opacity-50"
                >
                  {isUploadingSnapshot ? "Extracting OCR with Gemini Vision..." : "Upload & Analyze"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
