import React, { useRef, useEffect } from "react";
import { Terminal, Activity, AlertOctagon, CheckCircle2, XCircle } from "lucide-react";

export function EvidencePanel({ logs = [], carriedEvidence }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="flex flex-col h-full bg-[#0b0d16] border border-[#1d2235] rounded-xl overflow-hidden shadow-2xl">
      {/* Panel Header */}
      <div className="px-4 py-3 bg-[#111524] border-b border-[#1d2235] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Terminal className="w-5 h-5 text-emerald-400" />
          <span className="text-[14px] font-bold tracking-wider uppercase text-zinc-100 font-mono">
            Evidence & Execution Logs
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-mono">
          <Activity className="w-3.5 h-3.5 text-emerald-500 animate-pulse" />
          LIVE STREAM
        </div>
      </div>

      {/* Carried Failure Traces Notice */}
      {carriedEvidence && (
        <div className="p-3 bg-amber-950/40 border-b border-amber-800/50 text-[13px] font-mono text-amber-200 flex items-start gap-2.5 shadow-sm">
          <AlertOctagon className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold uppercase tracking-wider block text-xs text-amber-400">
              Evidence Carried to Next Round:
            </span>
            <div className="text-zinc-200 mt-1 leading-relaxed text-[13px] line-clamp-3">
              {carriedEvidence}
            </div>
          </div>
        </div>
      )}

      {/* Terminal Log Output */}
      <div className="flex-1 p-4 font-mono text-[13px] overflow-y-auto space-y-3 bg-[#08090f] leading-relaxed">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-500 text-sm py-12">
            <Terminal className="w-8 h-8 mb-2 opacity-30 text-zinc-400" />
            <p>Awaiting live debate events and sandbox execution...</p>
            <span className="text-xs text-zinc-600 mt-1">Events will stream here automatically</span>
          </div>
        ) : (
          logs.map((log, index) => {
            let badgeStyle = "text-zinc-300 bg-zinc-800/80 border-zinc-700";
            let textStyle = "text-zinc-200";
            const isPass = log.message.includes("PASSED") || log.message.includes("VERIFIED");
            const isFail = log.message.includes("FAILED");

            if (log.sender === "PROSECUTOR") {
              badgeStyle = "text-rose-300 bg-rose-950/70 border-rose-800/70";
              textStyle = "text-rose-100";
            } else if (log.sender === "DEFENDER") {
              badgeStyle = "text-sky-300 bg-sky-950/70 border-sky-800/70";
              textStyle = "text-sky-100";
            } else if (log.sender === "JUDGE" || log.sender === "VERDICT") {
              badgeStyle = "text-zinc-100 bg-zinc-800 border-zinc-600 font-bold";
              textStyle = "text-zinc-100 font-semibold";
            } else if (log.sender === "SANDBOX") {
              badgeStyle = isPass
                ? "text-emerald-300 bg-emerald-950/80 border-emerald-700"
                : "text-rose-300 bg-rose-950/80 border-rose-700";
              textStyle = isPass ? "text-emerald-200" : "text-rose-200";
            }

            return (
              <div key={index} className="flex items-start gap-2.5 leading-relaxed text-[13px] border-b border-zinc-900/60 pb-1.5 last:border-0">
                <span className="text-zinc-500 text-xs select-none shrink-0 pt-0.5">
                  [{log.timestamp}]
                </span>
                <span className={`px-2 py-0.5 rounded border text-[11px] uppercase font-bold shrink-0 shadow-sm ${badgeStyle}`}>
                  {log.sender}
                </span>
                <div className={`break-words flex-1 ${textStyle} flex items-center gap-1.5`}>
                  {isPass && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 inline" />}
                  {isFail && <XCircle className="w-4 h-4 text-rose-400 shrink-0 inline" />}
                  <span>{log.message}</span>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
export default EvidencePanel;
