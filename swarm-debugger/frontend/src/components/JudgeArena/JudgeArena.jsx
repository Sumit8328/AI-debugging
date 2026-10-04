import React from "react";
import { Scale, CheckCircle2, XCircle, Cpu, Terminal, ShieldAlert } from "lucide-react";

export function JudgeArena({ judge, executionA, executionB, activeAgent, currentRound }) {
  const isEvaluating = activeAgent === "judge";

  const isDockerLive = (executionA?.execution_mode === "docker" || executionB?.execution_mode === "docker");

  const renderStatusBadge = (execution) => {
    if (!execution) {
      return <span className="text-[13px] text-zinc-500 font-mono">AWAITING RUN</span>;
    }
    if (execution.status === "running") {
      return (
        <span className="text-[14px] font-mono font-bold px-3 py-1 rounded-md border border-amber-600/70 bg-amber-950/60 text-amber-300 flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          ● RUNNING
        </span>
      );
    }
    if (execution.status === "passed") {
      return (
        <span className="text-[14px] font-mono font-bold px-3 py-1 rounded-md border bg-emerald-950 border-emerald-700 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)] flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ✓ PASSED
        </span>
      );
    }
    if (execution.status === "timeout") {
      return (
        <span className="text-[14px] font-mono font-bold px-3 py-1 rounded-md border bg-amber-950 border-amber-700 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)] flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          ⏱ TIMEOUT
        </span>
      );
    }
    return (
      <span className="text-[14px] font-mono font-bold px-3 py-1 rounded-md border bg-rose-950 border-rose-700 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.3)] flex items-center gap-1.5">
        <XCircle className="w-4 h-4 text-rose-400" />
        ✕ FAILED
      </span>
    );
  };

  return (
    <div className="bg-[#0c0e18] border border-[#1e2438] rounded-xl overflow-hidden shadow-2xl flex flex-col">
      {/* Judicial Bench Header */}
      <div className="px-5 py-3.5 bg-[#121626] border-b border-[#1e2438] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-md bg-zinc-800 border border-zinc-700 text-zinc-100 shadow-sm">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <span className="text-base font-bold tracking-wider uppercase text-zinc-100 font-mono">
              Judge Arena & Sandbox Execution
            </span>
            <span className="ml-3 text-[13px] text-zinc-400 font-mono">
              "The code decides who is right"
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isDockerLive ? (
            <span className="text-xs px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-600/70 text-emerald-300 font-mono font-bold flex items-center gap-1.5 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              LIVE DOCKER EXECUTION
            </span>
          ) : (
            <span className="text-xs px-2.5 py-1 rounded bg-amber-950/60 border border-amber-600/70 text-amber-300 font-mono font-bold flex items-center gap-1.5 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              DEMO EXECUTION
            </span>
          )}
          <span className="text-xs px-2.5 py-1 rounded bg-zinc-900 border border-zinc-750 text-zinc-300 font-mono flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-zinc-400" />
            Isolated Sandbox
          </span>
          {isEvaluating && (
            <span className="text-xs px-3 py-1 rounded bg-zinc-800 text-zinc-100 border border-zinc-600 font-mono font-bold animate-pulse">
              Adjudicating Truth...
            </span>
          )}
        </div>
      </div>

      {/* Crucible: Patch A vs Patch B Sandbox Results */}
      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* PATCH A EXECUTION PROOF */}
        <div className="p-4 rounded-xl bg-[#0f121d] border border-[#21273d] flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                <span className="text-base font-bold uppercase tracking-wider text-rose-400 font-mono">
                  PATCH A (Prosecutor)
                </span>
              </div>
              {renderStatusBadge(executionA)}
            </div>

            {executionA ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3 py-1 text-center font-mono">
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Exit Code</div>
                    <div className={`text-base font-bold mt-0.5 ${executionA.exit_code === 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {executionA.exit_code !== undefined ? executionA.exit_code : "-"}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Tests</div>
                    <div className="text-sm font-bold mt-0.5 text-zinc-100">
                      <span className="text-emerald-400">{executionA.tests_passed || 0} passed</span> / <span className="text-rose-400">{executionA.tests_failed || 0} failed</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Duration</div>
                    <div className="text-base font-bold mt-0.5 text-zinc-200">
                      {executionA.duration_ms ? `${(executionA.duration_ms / 1000).toFixed(2)}s` : "-"}
                    </div>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="text-[13px] uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5 font-mono font-medium">
                    <Terminal className="w-4 h-4 text-zinc-400" /> Sandbox Pytest Log
                  </div>
                  <pre className="p-3 rounded-lg bg-black border border-zinc-800 text-[13px] font-mono text-zinc-300 overflow-x-auto max-h-32 leading-relaxed">
                    <code>{executionA.stdout || executionA.stderr || (executionA.status === "running" ? "Running tests in isolated container..." : "No log output")}</code>
                  </pre>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-zinc-500 text-sm font-mono">
                Awaiting isolated container dispatch...
              </div>
            )}
          </div>
        </div>

        {/* PATCH B EXECUTION PROOF */}
        <div className="p-4 rounded-xl bg-[#0f121d] border border-[#21273d] flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                <span className="text-base font-bold uppercase tracking-wider text-sky-400 font-mono">
                  PATCH B (Defender)
                </span>
              </div>
              {renderStatusBadge(executionB)}
            </div>

            {executionB ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3 py-1 text-center font-mono">
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Exit Code</div>
                    <div className={`text-base font-bold mt-0.5 ${executionB.exit_code === 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {executionB.exit_code !== undefined ? executionB.exit_code : "-"}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Tests</div>
                    <div className="text-sm font-bold mt-0.5 text-zinc-100">
                      <span className="text-emerald-400">{executionB.tests_passed || 0} passed</span> / <span className="text-rose-400">{executionB.tests_failed || 0} failed</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/60 border border-zinc-800">
                    <div className="text-[12px] text-zinc-400 uppercase font-semibold">Duration</div>
                    <div className="text-base font-bold mt-0.5 text-zinc-200">
                      {executionB.duration_ms ? `${(executionB.duration_ms / 1000).toFixed(2)}s` : "-"}
                    </div>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="text-[13px] uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5 font-mono font-medium">
                    <Terminal className="w-4 h-4 text-zinc-400" /> Sandbox Pytest Log
                  </div>
                  <pre className="p-3 rounded-lg bg-black border border-zinc-800 text-[13px] font-mono text-zinc-300 overflow-x-auto max-h-32 leading-relaxed">
                    <code>{executionB.stdout || executionB.stderr || (executionB.status === "running" ? "Running tests in isolated container..." : "No log output")}</code>
                  </pre>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-zinc-500 text-sm font-mono">
                Awaiting isolated container dispatch...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Judicial Verdict Bar */}
      {judge && (
        <div className="px-5 py-4 bg-[#141828] border-t border-[#1e2438] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold uppercase tracking-wider text-zinc-300 font-mono">
              Judicial Determination:
            </span>
            <span className={`text-[16px] font-mono font-extrabold px-3 py-1 rounded-md border shadow-md ${
              judge.winning_patch === "B" || judge.winning_patch === "Patch B"
                ? "bg-sky-950 border-sky-700 text-sky-200"
                : judge.winning_patch === "A" || judge.winning_patch === "Patch A"
                ? "bg-rose-950 border-rose-700 text-rose-200"
                : "bg-amber-950 border-amber-700 text-amber-200"
            }`}>
              {judge.winning_patch ? `WINNER: PATCH ${judge.winning_patch.replace("Patch ", "")}` : judge.decision}
            </span>
          </div>

          <div className="text-[14px] text-zinc-200 font-mono flex-1 md:text-right leading-relaxed">
            {judge.reason}
          </div>
        </div>
      )}
    </div>
  );
}
export default JudgeArena;
