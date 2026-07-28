"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import SentencePacingChart from "@/components/SentencePacingChart";
import LexiconHighlighter from "@/components/LexiconHighlighter";
import AIScoreMeter from "@/components/AIScoreMeter";

type TabType = "rewriter" | "twitter" | "linkedin";

interface RewriteResult {
  original: string;
  rewritten: string;
  score: number;
  attempts: number;
  status: string;
}

export default function TextSuite() {
  const [activeSubTab, setActiveSubTab] = useState<TabType>("rewriter");

  // Input fields
  const [inputText, setInputText] = useState("");
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [tone, setTone] = useState("human-like");
  const [dialect, setDialect] = useState("en-IN");
  
  // Rate limiting user tier
  const [userTier, setUserTier] = useState<"Free" | "Premium">("Free");

  // Output fields
  const [rewriteResult, setRewriteResult] = useState<RewriteResult | null>(null);
  const [tweets, setTweets] = useState<string[]>([]);
  const [linkedinPost, setLinkedinPost] = useState("");

  // Loading/Error states
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  // Analytics panel visibility
  const [showAnalytics, setShowAnalytics] = useState(true);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleProcess = async () => {
    setLoading(true);
    setError("");
    setStatusMessage("");

    try {
      if (activeSubTab === "rewriter") {
        if (!inputText) throw new Error("Input text is required");
        
        const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        
        // Initiate POST streaming connection
        const response = await fetch(`${BASE_URL}/text/rewrite-stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CreatorArc-Key": localStorage.getItem("creatorarc_master_key") || "",
            "X-User-Tier": userTier,
          },
          body: JSON.stringify({ text: inputText, tone, dialect }),
        });

        if (!response.ok) {
          const errText = await response.text();
          let parsedErr = "Transformation failed";
          try {
            parsedErr = JSON.parse(errText).detail || parsedErr;
          } catch {
            parsedErr = errText || parsedErr;
          }
          throw new Error(parsedErr);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("Readable stream reader is not available.");

        const decoder = new TextDecoder();
        let buffer = "";
        let currentEventName = "message";

        // Reset output targets
        setRewriteResult(null);
        setRewrittenText("");
        setStatusMessage("Establishing connection...");

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
              currentEventName = trimmed.replace("event:", "").trim();
            } else if (trimmed.startsWith("data:")) {
              const rawData = trimmed.replace("data:", "").trim();
              try {
                const parsed = JSON.parse(rawData);
                if (currentEventName === "status") {
                  setStatusMessage(parsed);
                } else if (currentEventName === "text_chunk") {
                  setRewrittenText((prev) => prev + parsed);
                } else if (currentEventName === "result") {
                  setRewriteResult({
                    original: parsed.original,
                    rewritten: parsed.rewritten,
                    score: parsed.score,
                    attempts: parsed.attempts,
                    status: parsed.status,
                  });
                } else if (currentEventName === "error") {
                  throw new Error(parsed.detail || "Stream error occurred");
                }
              } catch (e) {
                console.error("Failed to parse event data:", e);
              }
            }
          }
        }
        setStatusMessage("");
      } else if (activeSubTab === "twitter") {
        if (!topic) throw new Error("Topic is required");
        const res = await api.generateTwitter(topic, context);
        setTweets(res.posts || []);
      } else if (activeSubTab === "linkedin") {
        if (!topic) throw new Error("Topic is required");
        const res = await api.generateLinkedIn(topic, context);
        setLinkedinPost(res.post);
      }
    } catch (err: any) {
      setError(
        err.message ||
          "Something went wrong. Please check password and backend connection."
      );
    } finally {
      setLoading(false);
    }
  };

  // Helper setter to update state targets
  const setRewrittenText = (val: string | ((prev: string) => string)) => {
    if (typeof val === "function") {
      setRewriteResult((prev) => {
        const prevText = prev ? prev.rewritten : "";
        const nextText = val(prevText);
        return {
          original: inputText,
          rewritten: nextText,
          score: prev ? prev.score : 1.0,
          attempts: prev ? prev.attempts : 1,
          status: prev ? prev.status : "partial_success",
        };
      });
    } else {
      setRewriteResult((prev) => ({
        original: inputText,
        rewritten: val,
        score: prev ? prev.score : 1.0,
        attempts: prev ? prev.attempts : 1,
        status: prev ? prev.status : "partial_success",
      }));
    }
  };

  const wordCount = inputText.split(/\s+/).filter(Boolean).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Text Suite
          </h2>
          <p className="text-slate-400 text-sm">
            Fine-tune your messaging and draft dynamic copy for social media
            platforms.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Rate Limiting Tier Selector */}
          <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-800 rounded-lg p-1">
            <span className="text-[10px] uppercase font-bold text-slate-500 px-2">Tier:</span>
            <button
              onClick={() => setUserTier("Free")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                userTier === "Free"
                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  : "text-slate-500 hover:text-slate-400"
              }`}
            >
              Free (3 RPM)
            </button>
            <button
              onClick={() => setUserTier("Premium")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                userTier === "Premium"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-500 hover:text-slate-400"
              }`}
            >
              Premium (20 RPM)
            </button>
          </div>

          {/* Sub tabs */}
          <div className="flex p-1 rounded-lg glass-panel max-w-sm">
            <button
              onClick={() => {
                setActiveSubTab("rewriter");
                setError("");
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                activeSubTab === "rewriter"
                  ? "bg-indigo-600/40 text-white border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Human Rewriter
            </button>
            <button
              onClick={() => {
                setActiveSubTab("twitter");
                setError("");
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                activeSubTab === "twitter"
                  ? "bg-indigo-600/40 text-white border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Twitter Gen
            </button>
            <button
              onClick={() => {
                setActiveSubTab("linkedin");
                setError("");
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                activeSubTab === "linkedin"
                  ? "bg-indigo-600/40 text-white border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              LinkedIn Gen
            </button>
          </div>
        </div>
      </div>

      {/* ===== REWRITER TAB: Side-by-Side Workspace ===== */}
      {activeSubTab === "rewriter" && (
        <div className="space-y-6">
          {/* Side-by-Side Editing Canvas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 rounded-2xl overflow-hidden border border-slate-800/60">
            {/* LEFT: Input Panel */}
            <div className="bg-slate-900/30 p-6 border-r border-slate-800/40 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
                  <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
                    AI Input
                  </h3>
                </div>
                <span className="text-[10px] text-slate-600 font-mono">
                  {wordCount} words
                </span>
              </div>

              <textarea
                id="humanizer-input"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Paste your AI-generated text, rough notes, or outline here..."
                rows={12}
                className="w-full flex-1 p-4 rounded-lg glass-input text-sm resize-none leading-relaxed font-[family-name:var(--font-geist-mono)] text-slate-300"
              />

              {/* Controls row */}
              <div className="flex items-center gap-3 mt-4">
                <div className="flex-1">
                  <select
                    id="humanizer-tone"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full p-2.5 rounded-lg glass-input text-xs cursor-pointer"
                  >
                    <option value="human-like">
                      Human-like (Casual, relatable)
                    </option>
                    <option value="professional">Professional & Technical</option>
                    <option value="engaging">Engaging Storyteller</option>
                    <option value="witty">Witty & Humorous</option>
                  </select>
                </div>
                <div className="flex-1">
                  <select
                    id="humanizer-dialect"
                    value={dialect}
                    onChange={(e) => setDialect(e.target.value)}
                    className="w-full p-2.5 rounded-lg glass-input text-xs cursor-pointer"
                  >
                    <option value="en-IN">🇮🇳 Indian English</option>
                    <option value="en-SG">🇸🇬 Singapore English</option>
                    <option value="en-AU">🇦🇺 Australian English</option>
                    <option value="en-GB">🇬🇧 British English</option>
                    <option value="en-US">🇺🇸 American English</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20 mt-3">
                  {error}
                </div>
              )}

              <button
                id="humanizer-submit"
                onClick={handleProcess}
                disabled={loading}
                className="w-full py-3 rounded-lg btn-gradient font-bold transition-all flex items-center justify-center cursor-pointer disabled:opacity-50 mt-4"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span className="text-sm">Processing...</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                    Humanize Text
                  </div>
                )}
              </button>
            </div>

            {/* RIGHT: Output Panel */}
            <div className="bg-slate-950/40 p-6 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/60" />
                  <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
                    Humanized Output
                  </h3>
                </div>
                {rewriteResult && rewriteResult.rewritten && (
                  <button
                    id="copy-output"
                    onClick={() =>
                      handleCopy(rewriteResult.rewritten, "rewrite-main")
                    }
                    className="px-3 py-1.5 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 flex items-center gap-1.5 cursor-pointer transition-all"
                  >
                    <svg
                      className="w-3 h-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
                      />
                    </svg>
                    {copied === "rewrite-main" ? "Copied!" : "Copy All"}
                  </button>
                )}
              </div>

              {loading && !rewriteResult?.rewritten ? (
                <div className="flex-1 flex flex-col items-center justify-center py-16 space-y-4">
                  <div className="relative">
                    <div className="w-14 h-14 border-4 border-indigo-500/20 rounded-full" />
                    <div className="absolute inset-0 w-14 h-14 border-4 border-transparent border-t-indigo-500 rounded-full animate-spin" />
                  </div>
                  <div className="text-center space-y-1">
                    <p className="text-slate-300 text-sm font-semibold">
                      Transforming via RAG Pipeline
                    </p>
                    <p className="text-indigo-400 text-[10px] font-semibold animate-pulse">
                      {statusMessage || "Processing stages..."}
                    </p>
                  </div>
                </div>
              ) : rewriteResult && rewriteResult.rewritten ? (
                <div className="flex-1 flex flex-col justify-between">
                  <div className="overflow-y-auto flex-1 mb-4">
                    <LexiconHighlighter
                      rewrittenText={rewriteResult.rewritten}
                    />
                  </div>
                  {statusMessage && (
                    <p className="text-[10px] text-indigo-400 font-semibold animate-pulse border-t border-slate-800/40 pt-2">
                      {statusMessage}
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-16 h-16 rounded-2xl bg-slate-800/50 border border-slate-700/30 flex items-center justify-center mb-4">
                    <svg
                      className="w-7 h-7 text-slate-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                      />
                    </svg>
                  </div>
                  <p className="text-slate-500 text-sm font-medium">
                    Paste your text and click Humanize
                  </p>
                  <p className="text-slate-600 text-[10px] mt-1 max-w-[200px]">
                    The output will appear here with lexicon highlights and
                    analytics below.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* ===== Analytics Dashboard (only shown after results) ===== */}
          {rewriteResult && rewriteResult.rewritten && (
            <div className="space-y-4">
              {/* Analytics toggle */}
              <button
                id="toggle-analytics"
                onClick={() => setShowAnalytics(!showAnalytics)}
                className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              >
                <svg
                  className={`w-4 h-4 transition-transform ${
                    showAnalytics ? "rotate-0" : "-rotate-90"
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
                Humanization Analytics
                <div className="h-px flex-1 bg-slate-800/60" />
              </button>

              {showAnalytics && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-500">
                  {/* Left: Sentence Pacing Chart */}
                  <div className="glass-card rounded-xl p-5">
                    <SentencePacingChart
                      originalText={rewriteResult.original}
                      rewrittenText={rewriteResult.rewritten}
                    />
                  </div>

                  {/* Right: AI Score Meter */}
                  <div className="glass-card rounded-xl p-5">
                    <AIScoreMeter
                      score={rewriteResult.score}
                      attempts={rewriteResult.attempts}
                      status={rewriteResult.status}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===== TWITTER & LINKEDIN TABS (unchanged layout) ===== */}
      {(activeSubTab === "twitter" || activeSubTab === "linkedin") && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Side: Inputs */}
          <div className="glass-card rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-semibold text-slate-200 mb-2">
              Configure Parameters
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase text-slate-400 mb-2">
                  Post Topic / Theme
                </label>
                <input
                  type="text"
                  id="social-topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Scaling background workers using Celery and Redis"
                  className="w-full p-3 rounded-lg glass-input text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium uppercase text-slate-400 mb-2">
                  Context / Key Details (Optional)
                </label>
                <textarea
                  id="social-context"
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="Add bullet points or key details you want the post to mention..."
                  rows={6}
                  className="w-full p-4 rounded-lg glass-input text-sm resize-none"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20">
                {error}
              </div>
            )}

            <button
              id="social-submit"
              onClick={handleProcess}
              disabled={loading}
              className="w-full py-3 rounded-lg btn-gradient font-bold transition-all flex items-center justify-center cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                "Generate Post Assets"
              )}
            </button>
          </div>

          {/* Right Side: Outputs */}
          <div className="glass-card rounded-xl p-6 flex flex-col min-h-[350px]">
            <h3 className="text-lg font-semibold text-slate-200 mb-4">
              Generated Output
            </h3>

            <div className="flex-1 flex flex-col justify-center">
              {loading ? (
                <div className="text-center py-12 space-y-3">
                  <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto" />
                  <p className="text-slate-400 text-xs">
                    Generating content via Gemini...
                  </p>
                </div>
              ) : (
                <div className="space-y-4 h-full flex flex-col justify-between">
                  {activeSubTab === "twitter" && tweets.length > 0 && (
                    <div className="space-y-4 overflow-y-auto flex-1">
                      {tweets.map((tweet, i) => (
                        <div
                          key={i}
                          className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 relative group flex flex-col justify-between"
                        >
                          <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                            {tweet}
                          </p>
                          <div className="flex justify-between items-center mt-3">
                            <span className="text-xs text-slate-500">
                              {tweet.length} / 280 chars
                            </span>
                            <button
                              onClick={() => handleCopy(tweet, `tweet-${i}`)}
                              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-xs cursor-pointer"
                            >
                              {copied === `tweet-${i}` ? "Copied!" : "Copy"}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeSubTab === "linkedin" && linkedinPost && (
                    <div className="relative group bg-slate-900/40 p-4 rounded-lg border border-slate-800 flex-1 flex flex-col justify-between">
                      <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap flex-1 overflow-y-auto">
                        {linkedinPost}
                      </p>
                      <div className="flex justify-end mt-4">
                        <button
                          onClick={() =>
                            handleCopy(linkedinPost, "linkedin")
                          }
                          className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 flex items-center gap-1.5 cursor-pointer"
                        >
                          {copied === "linkedin" ? "Copied!" : "Copy"}
                        </button>
                      </div>
                    </div>
                  )}

                  {tweets.length === 0 && !linkedinPost && (
                    <div className="text-center py-20 text-slate-500 text-sm">
                      Configure your settings and hit generate to view output.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
