import React, { useState } from "react";
import { Copy, Check, X, ShieldCheck, Terminal, Award } from "lucide-react";

export function FinalVerdict({ winningPatch, verifiedPatch, reason, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!winningPatch && !verifiedPatch) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(verifiedPatch || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const normalizedWinner = winningPatch ? winningPatch.replace("Patch ", "") : "B";

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-200">
      <div className="bg-[#0e111d] border border-emerald-500/50 rounded-2xl max-w-2xl w-full overflow-hidden shadow-[0_0_60px_rgba(16,185,129,0.25)]">
        {/* Banner Header */}
        <div className="px-6 py-5 bg-emerald-950/50 border-b border-emerald-800/50 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-md">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-sm font-mono font-black uppercase tracking-wider px-2.5 py-0.5 rounded bg-emerald-400 text-black">
                  VERIFIED
                </span>
                <span className="text-sm text-emerald-400 font-mono font-semibold">
                  ACTUAL TEST EXECUTION TRUTH
                </span>
              </div>
              <h2 className="text-2xl font-black text-white mt-1 font-mono tracking-tight">
                Candidate Fix Validated in Sandbox
              </h2>
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-2 rounded-lg hover:bg-zinc-800/80 transition-colors cursor-pointer"
            >
              <X className="w-6 h-6" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Winner announcement */}
          <div className="flex flex-wrap items-center justify-between p-4 rounded-xl bg-black/50 border border-zinc-800 gap-3">
            <div className="flex items-center gap-2.5">
              <Award className="w-6 h-6 text-amber-400 shrink-0" />
              <span className="text-sm text-zinc-300 font-mono">Winning Candidate:</span>
              <span className={`text-base font-bold font-mono px-3.5 py-1 rounded-md border shadow-md ${
                normalizedWinner === "B"
                  ? "bg-sky-950 border-sky-700 text-sky-200"
                  : "bg-rose-950 border-rose-700 text-rose-200"
              }`}>
                PATCH {normalizedWinner} ({normalizedWinner === "B" ? "Defender" : "Prosecutor"})
              </span>
            </div>
            <div className="text-xs text-zinc-300 font-mono flex items-center gap-1.5 bg-emerald-950/40 px-3 py-1 rounded border border-emerald-900/60">
              <Terminal className="w-4 h-4 text-emerald-400" /> All pytest tests passed (exit code 0)
            </div>
          </div>

          {/* Judicial reason */}
          {reason && (
            <div>
              <div className="text-xs uppercase font-bold text-zinc-400 mb-1.5 font-mono tracking-wider">
                Judicial Confirmation
              </div>
              <div className="p-4 rounded-xl bg-[#141829] border border-[#222944] text-zinc-100 font-mono text-[14px] leading-relaxed shadow-inner">
                {reason}
              </div>
            </div>
          )}

          {/* Verified unified patch */}
          {verifiedPatch && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase font-bold text-emerald-400 font-mono tracking-wider">
                  Verified Unified Patch Diff
                </span>
                <button
                  onClick={handleCopy}
                  className="text-xs text-zinc-200 hover:text-white px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 flex items-center gap-2 transition-colors font-mono cursor-pointer shadow-sm"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  {copied ? "Copied to Clipboard!" : "Copy Patch Diff"}
                </button>
              </div>
              <pre className="p-4 rounded-xl bg-black border border-emerald-950 text-emerald-300 font-mono text-[13px] overflow-x-auto max-h-52 leading-relaxed shadow-inner">
                <code>{verifiedPatch}</code>
              </pre>
            </div>
          )}

          {/* Core premise footer */}
          <div className="pt-2 text-center text-xs text-zinc-400 font-mono italic">
            "AI can argue about the bug. The code decides who is right."
          </div>
        </div>
      </div>
    </div>
  );
}
export default FinalVerdict;
