"use client";

import React, { useEffect, useState } from "react";

interface AIScoreMeterProps {
  score: number; // 0.0 to 1.0
  attempts: number;
  status: string;
}

export default function AIScoreMeter({
  score,
  attempts,
  status,
}: AIScoreMeterProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const percentage = Math.round(animatedScore * 100);
  const humanPercentage = 100 - percentage;

  // Color based on score thresholds
  let meterColor = "from-emerald-400 to-emerald-500";
  let glowColor = "rgba(52, 211, 153, 0.4)";
  let badgeText = "Undetectable";
  let badgeBg = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";

  if (score > 0.5) {
    meterColor = "from-rose-400 to-rose-500";
    glowColor = "rgba(244, 63, 94, 0.4)";
    badgeText = "High Risk";
    badgeBg = "bg-rose-500/15 text-rose-400 border-rose-500/30";
  } else if (score > 0.35) {
    meterColor = "from-amber-400 to-orange-500";
    glowColor = "rgba(251, 146, 60, 0.4)";
    badgeText = "Moderate Risk";
    badgeBg = "bg-amber-500/15 text-amber-400 border-amber-500/30";
  } else if (score > 0.15) {
    meterColor = "from-sky-400 to-indigo-400";
    glowColor = "rgba(56, 189, 248, 0.4)";
    badgeText = "Low Risk";
    badgeBg = "bg-sky-500/15 text-sky-400 border-sky-500/30";
  }

  // SVG arc for the gauge
  const radius = 68;
  const strokeWidth = 10;
  const cx = 80;
  const cy = 80;
  const startAngle = 135;
  const endAngle = 405;
  const totalAngle = endAngle - startAngle;

  function polarToCartesian(
    centerX: number,
    centerY: number,
    r: number,
    angleDeg: number
  ) {
    const angleRad = ((angleDeg - 90) * Math.PI) / 180;
    return {
      x: centerX + r * Math.cos(angleRad),
      y: centerY + r * Math.sin(angleRad),
    };
  }

  function describeArc(
    x: number,
    y: number,
    r: number,
    startA: number,
    endA: number
  ) {
    const start = polarToCartesian(x, y, r, endA);
    const end = polarToCartesian(x, y, r, startA);
    const largeArcFlag = endA - startA <= 180 ? "0" : "1";
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
  }

  const filledAngle = startAngle + totalAngle * (1 - animatedScore);
  const bgArc = describeArc(cx, cy, radius, startAngle, endAngle);
  const fillArc = describeArc(cx, cy, radius, startAngle, filledAngle);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          AI Detection Scoreboard
        </h4>
        <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${badgeBg}`}>
          {badgeText}
        </div>
      </div>

      <div className="bg-slate-900/50 rounded-xl border border-slate-800/60 p-5">
        <div className="flex items-center gap-6">
          {/* Gauge */}
          <div className="relative flex-shrink-0">
            <svg width="160" height="120" viewBox="0 0 160 120">
              <defs>
                <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#34d399" />
                  <stop offset="50%" stopColor="#fbbf24" />
                  <stop offset="100%" stopColor="#f43f5e" />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Background arc */}
              <path
                d={bgArc}
                fill="none"
                stroke="rgba(148,163,184,0.08)"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
              />

              {/* Filled arc */}
              <path
                d={fillArc}
                fill="none"
                stroke="url(#gaugeGrad)"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                filter="url(#glow)"
                style={{
                  transition: "all 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
                }}
              />

              {/* Center text */}
              <text
                x={cx}
                y={cy - 6}
                textAnchor="middle"
                className="fill-white"
                fontSize="28"
                fontWeight="800"
              >
                {humanPercentage}%
              </text>
              <text
                x={cx}
                y={cy + 12}
                textAnchor="middle"
                className="fill-slate-400"
                fontSize="9"
                fontWeight="600"
              >
                HUMAN SCORE
              </text>
            </svg>
          </div>

          {/* Stats */}
          <div className="flex-1 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/30">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">
                  AI Probability
                </p>
                <p className="text-lg font-bold text-white">{percentage}%</p>
              </div>
              <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/30">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">
                  Retry Attempts
                </p>
                <p className="text-lg font-bold text-white">{attempts}</p>
              </div>
            </div>

            {/* Confidence bar */}
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-[10px] text-slate-500">Human Confidence</span>
                <span className="text-[10px] font-bold text-slate-300">
                  {humanPercentage}%
                </span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${meterColor}`}
                  style={{
                    width: `${humanPercentage}%`,
                    transition: "width 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
                    boxShadow: `0 0 12px ${glowColor}`,
                  }}
                />
              </div>
            </div>

            <p className="text-[10px] text-slate-600">
              Status:{" "}
              <span
                className={`font-semibold ${
                  status === "success" ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {status === "success" ? "Passed Adversarial Check" : "Best Effort Result"}
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
