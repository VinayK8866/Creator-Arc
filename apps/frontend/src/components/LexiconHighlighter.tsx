"use client";

import React, { useMemo } from "react";

interface LexiconHighlighterProps {
  rewrittenText: string;
}

// Indian English lexicon terms that the backend injects
// Indian, Singapore, Australian, and British English lexicon terms that the backend injects
const LEXICON_TERMS: { term: string; tooltip: string }[] = [
  { term: "kindly revert at the earliest", tooltip: "Replaced: 'reply ASAP' (Indian/Singapore)" },
  { term: "prepone", tooltip: "Replaced: 'reschedule earlier' (Indian/Singapore)" },
  { term: "PFA the document", tooltip: "Replaced: 'please find attached'" },
  { term: "PFA", tooltip: "Replaced: 'please find attached'" },
  { term: "do one thing", tooltip: "Indian English idiom injected" },
  { term: "discuss about", tooltip: "Replaced: 'discuss' (Indian)" },
  { term: "updation", tooltip: "Replaced: 'update/updating' (Indian)" },
  { term: "needful", tooltip: "Replaced: 'necessary action' (Indian)" },
  { term: "revert back", tooltip: "Replaced: 'reply' (Indian/Singapore)" },
  { term: "passed out", tooltip: "Replaced: 'graduated' (Indian)" },
  { term: "out of station", tooltip: "Replaced: 'out of town' (Indian)" },
  { term: "years back", tooltip: "Replaced: 'years ago' (Indian)" },
  
  // Singapore English (Singlish / Professional SG)
  { term: "take MC", tooltip: "Singapore: Replaced 'take sick leave'" },
  { term: "submit MC", tooltip: "Singapore: Replaced 'submit sick note'" },
  { term: "chop", tooltip: "Singapore: Replaced 'stamp/approve'" },
  { term: "kiasu", tooltip: "Singapore: Replaced 'afraid of missing out'" },
  
  // Australian English (Aussie)
  { term: "this arvo", tooltip: "Australia: Replaced 'this afternoon'" },
  { term: "arvo", tooltip: "Australia: Replaced 'afternoon'" },
  { term: "a fortnight", tooltip: "Australia: Replaced 'two weeks'" },
  { term: "no worries", tooltip: "Australia: Replaced 'no problem'" },
  { term: "how ya going", tooltip: "Australia: Replaced 'how are you'" },
  { term: "uni", tooltip: "Australia: Replaced 'university'" },
  { term: "barbie", tooltip: "Australia: Replaced 'barbecue'" },
  
  // British English (UK)
  { term: "colour", tooltip: "UK: Spelling adjustment for 'color'" },
  { term: "colours", tooltip: "UK: Spelling adjustment for 'colors'" },
  { term: "flavour", tooltip: "UK: Spelling adjustment for 'flavor'" },
  { term: "flavours", tooltip: "UK: Spelling adjustment for 'flavors'" },
  { term: "analyse", tooltip: "UK: Spelling adjustment for 'analyze'" },
  { term: "analysed", tooltip: "UK: Spelling adjustment for 'analyzed'" },
  { term: "analyses", tooltip: "UK: Spelling adjustment for 'analyzes'" },
  { term: "analysing", tooltip: "UK: Spelling adjustment for 'analyzing'" },
  { term: "organisation", tooltip: "UK: Spelling adjustment for 'organization'" },
  { term: "organisations", tooltip: "UK: Spelling adjustment for 'organizations'" },
  { term: "realise", tooltip: "UK: Spelling adjustment for 'realize'" },
  { term: "realised", tooltip: "UK: Spelling adjustment for 'realized'" },
  { term: "realises", tooltip: "UK: Spelling adjustment for 'realizes'" },
  { term: "realising", tooltip: "UK: Spelling adjustment for 'realizing'" },
  { term: "defence", tooltip: "UK: Spelling adjustment for 'defense'" },
  { term: "offence", tooltip: "UK: Spelling adjustment for 'offense'" },
  { term: "flat", tooltip: "UK: Replaced 'apartment'" },
  { term: "flats", tooltip: "UK: Replaced 'apartments'" },
  { term: "lift", tooltip: "UK: Replaced 'elevator'" },
  { term: "lifts", tooltip: "UK: Replaced 'elevators'" },
  { term: "holiday", tooltip: "UK: Replaced 'vacation'" },
  { term: "holidays", tooltip: "UK: Replaced 'vacations'" },
];

interface HighlightedSegment {
  text: string;
  isHighlighted: boolean;
  tooltip?: string;
}

export default function LexiconHighlighter({
  rewrittenText,
}: LexiconHighlighterProps) {
  const segments: HighlightedSegment[] = useMemo(() => {
    if (!rewrittenText) return [];

    const lowerText = rewrittenText.toLowerCase();
    const matches: { start: number; end: number; tooltip: string }[] = [];

    for (const item of LEXICON_TERMS) {
      const termLower = item.term.toLowerCase();
      let searchFrom = 0;
      while (true) {
        const idx = lowerText.indexOf(termLower, searchFrom);
        if (idx === -1) break;
        // Avoid overlapping matches
        const overlaps = matches.some(
          (m) =>
            (idx >= m.start && idx < m.end) ||
            (idx + item.term.length > m.start && idx + item.term.length <= m.end)
        );
        if (!overlaps) {
          matches.push({
            start: idx,
            end: idx + item.term.length,
            tooltip: item.tooltip,
          });
        }
        searchFrom = idx + 1;
      }
    }

    // Sort by position
    matches.sort((a, b) => a.start - b.start);

    if (matches.length === 0) {
      return [{ text: rewrittenText, isHighlighted: false }];
    }

    const result: HighlightedSegment[] = [];
    let cursor = 0;

    for (const match of matches) {
      if (match.start > cursor) {
        result.push({
          text: rewrittenText.slice(cursor, match.start),
          isHighlighted: false,
        });
      }
      result.push({
        text: rewrittenText.slice(match.start, match.end),
        isHighlighted: true,
        tooltip: match.tooltip,
      });
      cursor = match.end;
    }

    if (cursor < rewrittenText.length) {
      result.push({
        text: rewrittenText.slice(cursor),
        isHighlighted: false,
      });
    }

    return result;
  }, [rewrittenText]);

  const highlightCount = segments.filter((s) => s.isHighlighted).length;

  if (!rewrittenText) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Humanized Output
        </h4>
        {highlightCount > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[10px] text-emerald-400 font-semibold">
              {highlightCount} lexicon swap{highlightCount > 1 ? "s" : ""} detected
            </span>
          </div>
        )}
      </div>

      <div className="bg-slate-900/50 rounded-xl border border-slate-800/60 p-4 max-h-[300px] overflow-y-auto">
        <p className="text-sm leading-relaxed text-slate-200">
          {segments.map((seg, i) =>
            seg.isHighlighted ? (
              <span
                key={i}
                className="relative inline-block group"
              >
                <span className="bg-emerald-500/15 text-emerald-300 px-1 py-0.5 rounded border-b-2 border-emerald-500/40 font-medium cursor-help transition-colors hover:bg-emerald-500/25">
                  {seg.text}
                </span>
                {/* Tooltip */}
                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-[10px] text-slate-300 font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity shadow-xl z-50">
                  {seg.tooltip}
                  <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
                </span>
              </span>
            ) : (
              <span key={i}>{seg.text}</span>
            )
          )}
        </p>
      </div>
    </div>
  );
}
