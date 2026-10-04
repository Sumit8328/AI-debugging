import React from "react";
import { CheckCircle2, AlertCircle, Sparkles } from "lucide-react";

export function RoundTimeline({ currentRound, maxRounds = 3, status }) {
  const rounds = Array.from({ length: maxRounds }, (_, i) => i + 1);
  const isVerified = status === "verified";
  const isFailed = status === "failed";

  return (
    <div className="w-full bg-[#0d0f1a] border border-[#1e2438] rounded-xl px-6 py-4 shadow-xl flex flex-col md:flex-row items-center justify-between gap-5">
      {/* Label & Status */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-extrabold uppercase tracking-wider text-zinc-200 font-mono">
          Adversarial Progression:
        </span>
        <span className={`text-xs uppercase font-mono font-bold px-3 py-1 rounded-md border shadow-sm ${
          isVerified
            ? "bg-emerald-950 border-emerald-700 text-emerald-300"
            : status === "debating"
            ? "bg-rose-950 border-rose-700 text-rose-300 animate-pulse"
            : status === "executing"
            ? "bg-sky-950 border-sky-700 text-sky-300 animate-pulse"
            : "bg-zinc-800 border-zinc-700 text-zinc-300"
        }`}>
          {status.toUpperCase()}
        </span>
      </div>

      {/* Progress Track: R1 ●────────● R2────────● R3────────◎ VERIFIED */}
      <div className="flex items-center gap-3 md:gap-5 flex-1 max-w-xl mx-auto">
        {rounds.map((r) => {
          const isCurrent = currentRound === r && !isVerified && !isFailed;
          const isPassed = currentRound > r || isVerified;

          return (
            <React.Fragment key={r}>
              {/* Round Node */}
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-mono font-bold border transition-all ${
                    isCurrent
                      ? "bg-rose-900 border-rose-400 text-white shadow-[0_0_16px_rgba(244,63,94,0.7)] animate-pulse"
                      : isPassed
                      ? "bg-zinc-800 border-zinc-600 text-zinc-200"
                      : "bg-[#090b12] border-zinc-800 text-zinc-500"
                  }`}
                >
                  R{r}
                </div>
                <span className={`text-[12px] font-mono uppercase font-semibold ${isCurrent ? "text-rose-400" : isPassed ? "text-zinc-400" : "text-zinc-600"}`}>
                  {isCurrent ? "Active" : isPassed ? "Done" : "Queue"}
                </span>
              </div>

              {/* Connecting Line */}
              <div className="flex-1 h-[2px] bg-zinc-800 relative">
                <div
                  className={`h-full transition-all duration-500 ${
                    isPassed ? "bg-zinc-500 w-full" : isCurrent ? "bg-rose-500 w-1/2" : "w-0"
                  }`}
                />
              </div>
            </React.Fragment>
          );
        })}

        {/* VERIFIED TERMINATION NODE */}
        <div className="flex flex-col items-center gap-1.5">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center border transition-all ${
              isVerified
                ? "bg-emerald-600 border-emerald-300 text-white shadow-[0_0_20px_rgba(16,185,129,0.85)]"
                : isFailed
                ? "bg-rose-950 border-rose-700 text-rose-400"
                : "bg-[#090b12] border-zinc-800 text-zinc-600"
            }`}
          >
            {isVerified ? (
              <CheckCircle2 className="w-6 h-6 text-white" />
            ) : isFailed ? (
              <AlertCircle className="w-6 h-6 text-rose-400" />
            ) : (
              <Sparkles className="w-5 h-5 text-zinc-600" />
            )}
          </div>
          <span className={`text-[12px] font-mono uppercase font-bold tracking-wider ${isVerified ? "text-emerald-400" : "text-zinc-500"}`}>
            {isVerified ? "VERIFIED" : "VERIFY"}
          </span>
        </div>
      </div>
    </div>
  );
}
export default RoundTimeline;
