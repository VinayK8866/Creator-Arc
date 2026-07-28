"use client";

import React, { useState } from "react";
import Link from "next/link";
import TextSuite from "@/components/TextSuite";
import YouTubeSuite from "@/components/YouTubeSuite";
import MediaSuite from "@/components/MediaSuite";

type MainTab = "overview" | "text" | "youtube" | "media";

export default function DashboardHome() {
  const [activeTab, setActiveTab] = useState<MainTab>("overview");

  const handleLogout = () => {
    localStorage.removeItem("creatorarc_master_key");
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-[#05060b] flex flex-col md:flex-row text-slate-100 relative">
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-900/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-900/5 rounded-full blur-3xl pointer-events-none" />

      {/* Sidebar navigation */}
      <aside className="w-full md:w-64 glass-panel border-r border-slate-800/80 flex flex-col justify-between z-10">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-9 h-9 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-md">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-xl font-extrabold tracking-tight text-white">CreatorArc</span>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "overview"
                  ? "bg-indigo-600/20 text-indigo-300 border-l-4 border-indigo-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
              </svg>
              Overview
            </button>

            <button
              onClick={() => setActiveTab("text")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "text"
                  ? "bg-indigo-600/20 text-indigo-300 border-l-4 border-indigo-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Text Suite
            </button>

            <button
              onClick={() => setActiveTab("youtube")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "youtube"
                  ? "bg-indigo-600/20 text-indigo-300 border-l-4 border-indigo-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 00-2 2z" />
              </svg>
              YouTube Suite
            </button>

            <button
              onClick={() => setActiveTab("media")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "media"
                  ? "bg-indigo-600/20 text-indigo-300 border-l-4 border-indigo-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Media Suite
            </button>

            <Link
              href="/dashboard/blog-architect"
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 transition-all cursor-pointer"
            >
              <svg className="w-5 h-5 text-indigo-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              Blog Architect
            </Link>
          </nav>
        </div>

        <div className="p-6 border-t border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Dev Edition</span>
            <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full status-glow" />
          </div>
          <button
            onClick={handleLogout}
            className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Lock Dashboard
          </button>
        </div>
      </aside>

      {/* Main panel container */}
      <main className="flex-1 p-6 md:p-10 overflow-y-auto max-h-screen relative z-10">
        {activeTab === "overview" && (
          <div className="space-y-8">
            {/* Header banner card */}
            <div className="p-8 rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 border border-indigo-500/10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 glow-indigo">
              <div className="space-y-2">
                <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
                  Welcome to <span className="text-gradient-purple">CreatorArc</span>
                </h1>
                <p className="text-slate-400 text-sm max-w-xl">
                  Your local creator workstation powered by Google Gemini and local media processing models. 
                  Get started by selecting one of the workspace tools.
                </p>
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-card rounded-xl p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 bg-indigo-500/10 rounded-lg flex items-center justify-center border border-indigo-500/20">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <button onClick={() => setActiveTab("text")} className="text-xs text-indigo-400 font-semibold hover:text-indigo-300 transition-all cursor-pointer">Open Suite →</button>
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-200">Text Workspace</h3>
                  <p className="text-slate-400 text-xs">Humanize tones, write LinkedIn blogs, and script Twitter threads utilizing Gemini.</p>
                </div>
              </div>

              <div className="glass-card rounded-xl p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center border border-purple-500/20">
                    <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <button onClick={() => setActiveTab("youtube")} className="text-xs text-purple-400 font-semibold hover:text-purple-300 transition-all cursor-pointer">Open Suite →</button>
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-200">YouTube Summarizer</h3>
                  <p className="text-slate-400 text-xs">Extract subtitles or scrape raw audio stream parameters to draft video tags, descriptions, and summaries.</p>
                </div>
              </div>

              <div className="glass-card rounded-xl p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 bg-cyan-500/10 rounded-lg flex items-center justify-center border border-cyan-500/20">
                    <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <button onClick={() => setActiveTab("media")} className="text-xs text-cyan-400 font-semibold hover:text-cyan-300 transition-all cursor-pointer">Open Suite →</button>
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-200">Media Enhancer</h3>
                  <p className="text-slate-400 text-xs">Run local deep learning models for upscaling assets or extracting transparent background objects.</p>
                </div>
              </div>

              <div className="glass-card rounded-xl p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 bg-indigo-500/10 rounded-lg flex items-center justify-center border border-indigo-500/20 animate-pulse">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                    </svg>
                  </div>
                  <Link href="/dashboard/blog-architect" className="text-xs text-indigo-400 font-semibold hover:text-indigo-300 transition-all cursor-pointer">Open Suite →</Link>
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-200">Blog Architect</h3>
                  <p className="text-slate-400 text-xs">Generate highly factual blog articles and humanize them chunk-by-chunk for Medium, Reddit, etc.</p>
                </div>
              </div>
            </div>

            {/* Architecture note */}
            <div className="glass-card rounded-xl p-6 space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Current Infrastructure Notes</h3>
              <p className="text-slate-400 text-xs leading-relaxed">
                CreatorArc is structured as a dual-service monorepo. Asynchronous operations (upscaling, video transcription) are offloaded 
                to local **Celery workers** and coordinated via **Redis message queues**. This ensures the FastAPI web thread remains completely 
                unblocked. Processed media assets are temporarily staged in your **free storage bucket** (R2/Supabase) or server disk `/static/` paths.
              </p>
            </div>
          </div>
        )}

        {activeTab === "text" && <TextSuite />}
        {activeTab === "youtube" && <YouTubeSuite />}
        {activeTab === "media" && <MediaSuite />}
      </main>
    </div>
  );
}
