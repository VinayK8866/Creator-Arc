"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface PasswordLockProps {
  children: React.ReactNode;
}

export default function PasswordLock({ children }: PasswordLockProps) {
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const cachedKey = localStorage.getItem("creatorarc_master_key");
    if (cachedKey) {
      setUnlocked(true);
    }
  }, []);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setError("Please enter password");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const isValid = await api.testAuth(password);
      if (isValid) {
        localStorage.setItem("creatorarc_master_key", password);
        setUnlocked(true);
      } else {
        setError("Invalid master password");
      }
    } catch (err: any) {
      setError(err.message || "Failed to verify password");
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) {
    return <div className="min-h-screen bg-[#05060b]" />;
  }

  if (unlocked) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-[#05060b] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-900/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-900/15 rounded-full blur-3xl" />

      <div className="w-full max-w-md glass-card rounded-2xl p-8 relative z-10 shadow-2xl">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight mb-2">
            <span className="text-gradient-purple">CreatorArc</span>
          </h1>
          <p className="text-slate-400 text-sm">
            Please enter your master password to unlock the creator hub dashboard.
          </p>
        </div>

        <form onSubmit={handleUnlock} className="space-y-4">
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-2">
              Master Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-4 py-3 rounded-lg glass-input text-base text-center tracking-widest font-mono"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-rose-400 text-sm text-center bg-rose-500/10 py-2 rounded-lg border border-rose-500/20">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg btn-gradient font-bold transition-all relative flex items-center justify-center cursor-pointer"
          >
            {loading ? (
              <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Unlock Hub"
            )}
          </button>
        </form>

        <div className="text-center mt-6 text-xs text-slate-500">
          CreatorArc Personal Edition • Secured via Header Verify
        </div>
      </div>
    </div>
  );
}
