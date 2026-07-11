"use client";

import React, { useMemo } from "react";

interface SentencePacingChartProps {
  originalText: string;
  rewrittenText: string;
}

function getSentenceLengths(text: string): number[] {
  if (!text.trim()) return [];
  const sentences = text
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  return sentences.map((s) => s.split(/\s+/).length);
}

export default function SentencePacingChart({
  originalText,
  rewrittenText,
}: SentencePacingChartProps) {
  const originalLengths = useMemo(
    () => getSentenceLengths(originalText),
    [originalText]
  );
  const rewrittenLengths = useMemo(
    () => getSentenceLengths(rewrittenText),
    [rewrittenText]
  );

  const maxPoints = Math.max(originalLengths.length, rewrittenLengths.length, 2);
  const allValues = [...originalLengths, ...rewrittenLengths];
  const maxVal = Math.max(...allValues, 10);

  const chartW = 520;
  const chartH = 160;
  const padX = 40;
  const padY = 20;
  const innerW = chartW - padX * 2;
  const innerH = chartH - padY * 2;

  function toPath(lengths: number[]): string {
    if (lengths.length === 0) return "";
    return lengths
      .map((val, i) => {
        const x = padX + (i / (maxPoints - 1)) * innerW;
        const y = padY + innerH - (val / maxVal) * innerH;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  function toSmoothPath(lengths: number[]): string {
    if (lengths.length < 2) return toPath(lengths);
    const points = lengths.map((val, i) => ({
      x: padX + (i / (maxPoints - 1)) * innerW,
      y: padY + innerH - (val / maxVal) * innerH,
    }));

    let d = `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const cpx1 = prev.x + (curr.x - prev.x) * 0.4;
      const cpx2 = curr.x - (curr.x - prev.x) * 0.4;
      d += ` C${cpx1.toFixed(1)},${prev.y.toFixed(1)} ${cpx2.toFixed(1)},${curr.y.toFixed(1)} ${curr.x.toFixed(1)},${curr.y.toFixed(1)}`;
    }
    return d;
  }

  // Y-axis grid lines
  const gridLines = [0, 0.25, 0.5, 0.75, 1.0];

  if (originalLengths.length === 0 && rewrittenLengths.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Sentence Pacing Analysis
        </h4>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-[2px] bg-rose-500/80 rounded-full" />
            <span className="text-[10px] text-slate-500">Original (Uniform)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-[2px] bg-emerald-400 rounded-full" />
            <span className="text-[10px] text-slate-500">Humanized (Bursty)</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-900/50 rounded-xl border border-slate-800/60 p-4 overflow-hidden">
        <svg
          viewBox={`0 0 ${chartW} ${chartH}`}
          className="w-full"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="origGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#fb7185" stopOpacity="0.6" />
            </linearGradient>
            <linearGradient id="rewriteGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#34d399" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#6ee7b7" stopOpacity="0.7" />
            </linearGradient>
            <linearGradient id="origFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.02" />
            </linearGradient>
            <linearGradient id="rewriteFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#34d399" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {gridLines.map((frac) => {
            const y = padY + innerH - frac * innerH;
            const label = Math.round(frac * maxVal);
            return (
              <g key={frac}>
                <line
                  x1={padX}
                  y1={y}
                  x2={padX + innerW}
                  y2={y}
                  stroke="rgba(148,163,184,0.08)"
                  strokeDasharray="4,4"
                />
                <text
                  x={padX - 6}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-slate-600"
                  fontSize="9"
                >
                  {label}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {Array.from({ length: maxPoints }).map((_, i) => {
            const x = padX + (i / (maxPoints - 1)) * innerW;
            return (
              <text
                key={`x-${i}`}
                x={x}
                y={chartH - 4}
                textAnchor="middle"
                className="fill-slate-600"
                fontSize="9"
              >
                S{i + 1}
              </text>
            );
          })}

          {/* Original fill area */}
          {originalLengths.length > 1 && (
            <path
              d={`${toSmoothPath(originalLengths)} L${(
                padX +
                ((originalLengths.length - 1) / (maxPoints - 1)) * innerW
              ).toFixed(1)},${(padY + innerH).toFixed(1)} L${padX},${(
                padY + innerH
              ).toFixed(1)} Z`}
              fill="url(#origFill)"
            />
          )}

          {/* Rewritten fill area */}
          {rewrittenLengths.length > 1 && (
            <path
              d={`${toSmoothPath(rewrittenLengths)} L${(
                padX +
                ((rewrittenLengths.length - 1) / (maxPoints - 1)) * innerW
              ).toFixed(1)},${(padY + innerH).toFixed(1)} L${padX},${(
                padY + innerH
              ).toFixed(1)} Z`}
              fill="url(#rewriteFill)"
            />
          )}

          {/* Original line */}
          {originalLengths.length > 0 && (
            <path
              d={toSmoothPath(originalLengths)}
              fill="none"
              stroke="url(#origGrad)"
              strokeWidth="2"
              strokeLinecap="round"
            />
          )}

          {/* Rewritten line */}
          {rewrittenLengths.length > 0 && (
            <path
              d={toSmoothPath(rewrittenLengths)}
              fill="none"
              stroke="url(#rewriteGrad)"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          )}

          {/* Original data points */}
          {originalLengths.map((val, i) => {
            const x = padX + (i / (maxPoints - 1)) * innerW;
            const y = padY + innerH - (val / maxVal) * innerH;
            return (
              <circle
                key={`o-${i}`}
                cx={x}
                cy={y}
                r="3"
                fill="#0f172a"
                stroke="#f43f5e"
                strokeWidth="1.5"
              >
                <title>Original S{i + 1}: {val} words</title>
              </circle>
            );
          })}

          {/* Rewritten data points */}
          {rewrittenLengths.map((val, i) => {
            const x = padX + (i / (maxPoints - 1)) * innerW;
            const y = padY + innerH - (val / maxVal) * innerH;
            return (
              <circle
                key={`r-${i}`}
                cx={x}
                cy={y}
                r="3.5"
                fill="#0f172a"
                stroke="#34d399"
                strokeWidth="2"
              >
                <title>Humanized S{i + 1}: {val} words</title>
              </circle>
            );
          })}

          {/* Y-axis label */}
          <text
            x={4}
            y={padY + innerH / 2}
            textAnchor="middle"
            className="fill-slate-500"
            fontSize="8"
            transform={`rotate(-90, 8, ${padY + innerH / 2})`}
          >
            Words/Sentence
          </text>
        </svg>
      </div>
    </div>
  );
}
