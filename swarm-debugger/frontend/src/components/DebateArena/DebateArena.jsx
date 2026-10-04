import React, { useState } from "react";
import { Shield, Flame, Swords, FileCode2, Copy, Check, ChevronRight } from "lucide-react";

export function DebateArena({ prosecutor, defender, activeAgent, currentRound }) {
  const [copiedPatch, setCopiedPatch] = useState(null);

  const handleCopy = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopiedPatch(type);
    setTimeout(() => setCopiedPatch(null), 2000);
  };

  const renderEvidenceList = (evidence, theme) => {
    if (!evidence) return <div className="text-[13px] text-zinc-500">No evidence items specified</div>;
    const items = Array.isArray(evidence) ? evidence : [evidence];
    return (
      <ul className="space-y-1.5">
        {items.map((item, idx) => (
          <li key={idx} className="flex items-start gap-2 text-[14px] leading-relaxed">
            <ChevronRight className={`w-4 h-4 shrink-0 mt-0.5 ${theme === "rose" ? "text-rose-400" : "text-sky-400"}`} />
            <span className={theme === "rose" ? "text-rose-200" : "text-sky-200"}>{item}</span>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="flex flex-col h-full bg-[#0d0f18] border border-[#1d2235] rounded-xl overflow-hidden shadow-2xl">
      {/* Debate Arena Header */}
      <div className="px-5 py-3.5 bg-[#121626] border-b border-[#1d2235] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Swords className="w-5 h-5 text-zinc-300" />
          <span className="text-[15px] font-extrabold tracking-wider uppercase text-zinc-100 font-mono">
            Debate Arena
          </span>
          <span className="text-sm px-2.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-mono font-bold">
            ROUND {currentRound}
          </span>
        </div>

        <div className="flex items-center gap-4 text-sm font-mono">
          <span className="flex items-center gap-2 text-rose-400 font-semibold">
            <span className={`w-2.5 h-2.5 rounded-full ${activeAgent === "prosecutor" ? "bg-rose-500 animate-ping" : "bg-rose-500/60"}`} />
            Prosecutor (Fix A)
          </span>
          <span className="text-zinc-600 font-bold">VS</span>
          <span className="flex items-center gap-2 text-sky-400 font-semibold">
            <span className={`w-2.5 h-2.5 rounded-full ${activeAgent === "defender" ? "bg-sky-500 animate-ping" : "bg-sky-500/60"}`} />
            Defender (Fix B)
          </span>
        </div>
      </div>

      {/* Side-by-side Adversarial Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[#1d2235] flex-1 overflow-y-auto">
        {/* PROSECUTOR CARD (RED) */}
        <div className={`p-5 flex flex-col transition-all duration-300 ${activeAgent === "prosecutor" ? "bg-rose-950/15" : "bg-transparent"}`}>
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-rose-900/40">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-rose-950/70 border border-rose-800/60 text-rose-400 shadow-md">
                <Flame className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold uppercase tracking-wider text-rose-400 font-mono">
                  Prosecutor Agent
                </h3>
                <p className="text-[13px] text-zinc-400">Root Cause Indictment & Fix A</p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-rose-950 border border-rose-800 text-rose-300">
              CANDIDATE FIX A
            </span>
          </div>

          {prosecutor ? (
            <div className="space-y-4 flex-1">
              {/* Root Cause Hypothesis */}
              <div>
                <div className="text-[13px] uppercase font-bold text-rose-300 mb-1.5 font-mono tracking-wider">
                  Alleged Root Cause
                </div>
                <div className="p-3.5 rounded-lg bg-[#141724] border border-rose-900/50 text-zinc-100 font-mono text-[14px] leading-relaxed shadow-inner">
                  {prosecutor.root_cause}
                </div>
              </div>

              {/* Forensic Evidence */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-400 mb-1.5 font-mono tracking-wider">
                  Forensic Evidence
                </div>
                <div className="p-3 rounded-lg bg-black/50 border border-[#23293c]">
                  {renderEvidenceList(prosecutor.evidence, "rose")}
                </div>
              </div>

              {/* Affected Files */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-400 mb-1.5 font-mono tracking-wider">
                  Affected Files
                </div>
                <div className="flex flex-wrap gap-2">
                  {prosecutor.affected_files?.map((f, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-zinc-900 border border-zinc-700 text-zinc-200 font-mono text-[13px]">
                      <FileCode2 className="w-3.5 h-3.5 text-rose-400" />
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              {/* Proposed Patch A */}
              <div className="pt-1">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm uppercase font-bold text-rose-400 font-mono tracking-wider">
                    Candidate Patch (Fix A)
                  </span>
                  <button
                    onClick={() => handleCopy(prosecutor.proposed_patch, "A")}
                    className="text-xs text-zinc-300 hover:text-white px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 flex items-center gap-1.5 transition-colors font-mono cursor-pointer"
                  >
                    {copiedPatch === "A" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedPatch === "A" ? "Copied" : "Copy Diff"}
                  </button>
                </div>
                <pre className="p-3 rounded-lg bg-black/80 border border-rose-900/50 text-zinc-200 font-mono text-[13px] overflow-x-auto leading-relaxed">
                  <code>{prosecutor.proposed_patch}</code>
                </pre>
              </div>

              {/* Reasoning Summary */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-500 mb-1 font-mono tracking-wider">
                  Reasoning Artifact
                </div>
                <p className="text-[14px] text-zinc-300 italic leading-relaxed">
                  "{prosecutor.reasoning_summary}"
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-zinc-500">
              <Flame className="w-10 h-10 mb-2 text-rose-950 stroke-1" />
              <p className="text-sm font-medium">Prosecutor analyzing failure traces...</p>
              <p className="text-[13px] text-zinc-600 mt-1 font-mono">Waiting for round turn</p>
            </div>
          )}
        </div>

        {/* DEFENDER CARD (BLUE) */}
        <div className={`p-5 flex flex-col transition-all duration-300 ${activeAgent === "defender" ? "bg-sky-950/15" : "bg-transparent"}`}>
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-sky-900/40">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-sky-950/70 border border-sky-800/60 text-sky-400 shadow-md">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold uppercase tracking-wider text-sky-400 font-mono">
                  Defender Agent
                </h3>
                <p className="text-[13px] text-zinc-400">Challenge & Defensive Fix B</p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-sky-950 border border-sky-800 text-sky-300">
              CANDIDATE FIX B
            </span>
          </div>

          {defender ? (
            <div className="space-y-4 flex-1">
              {/* Challenge against Fix A */}
              <div>
                <div className="text-[13px] uppercase font-bold text-sky-300 mb-1.5 font-mono tracking-wider">
                  Challenge Against Fix A
                </div>
                <div className="p-3.5 rounded-lg bg-[#141724] border border-sky-900/50 text-zinc-100 font-mono text-[14px] leading-relaxed shadow-inner">
                  {defender.challenge}
                </div>
              </div>

              {/* Alternative Hypothesis */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-400 mb-1.5 font-mono tracking-wider">
                  Alternative Hypothesis
                </div>
                <div className="p-3 rounded-lg bg-black/50 border border-[#23293c] text-sky-200 font-mono text-[14px] leading-relaxed">
                  {defender.alternative_hypothesis}
                </div>
              </div>

              {/* Counter Evidence */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-400 mb-1.5 font-mono tracking-wider">
                  Regression Risk Proof
                </div>
                <div className="p-3 rounded-lg bg-black/50 border border-[#23293c]">
                  {renderEvidenceList(defender.evidence, "sky")}
                </div>
              </div>

              {/* Proposed Patch B */}
              <div className="pt-1">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm uppercase font-bold text-sky-400 font-mono tracking-wider">
                    Candidate Patch (Fix B)
                  </span>
                  <button
                    onClick={() => handleCopy(defender.proposed_patch, "B")}
                    className="text-xs text-zinc-300 hover:text-white px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 flex items-center gap-1.5 transition-colors font-mono cursor-pointer"
                  >
                    {copiedPatch === "B" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedPatch === "B" ? "Copied" : "Copy Diff"}
                  </button>
                </div>
                <pre className="p-3 rounded-lg bg-black/80 border border-sky-900/50 text-zinc-200 font-mono text-[13px] overflow-x-auto leading-relaxed">
                  <code>{defender.proposed_patch}</code>
                </pre>
              </div>

              {/* Reasoning Summary */}
              <div>
                <div className="text-[13px] uppercase font-bold text-zinc-500 mb-1 font-mono tracking-wider">
                  Reasoning Artifact
                </div>
                <p className="text-[14px] text-zinc-300 italic leading-relaxed">
                  "{defender.reasoning_summary}"
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-zinc-500">
              <Shield className="w-10 h-10 mb-2 text-sky-950 stroke-1" />
              <p className="text-sm font-medium">Defender preparing challenge and regression analysis...</p>
              <p className="text-[13px] text-zinc-600 mt-1 font-mono">Waiting for Prosecutor artifact</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
export default DebateArena;
