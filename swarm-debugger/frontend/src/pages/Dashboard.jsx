import React, { useState, useEffect } from "react";
import { 
  Play, 
  Square, 
  Bug, 
  Sparkles, 
  Scale, 
  Radio,
  FileCheck2
} from "lucide-react";
import { useSwarmSession } from "../hooks/useSwarmSession";
import { DebateArena } from "../components/DebateArena";
import { JudgeArena } from "../components/JudgeArena";
import { EvidencePanel } from "../components/EvidencePanel";
import { CodebasePanel } from "../components/CodebasePanel";
import { RoundTimeline } from "../components/RoundTimeline";
import { FinalVerdict } from "../components/FinalVerdict";
import * as api from "../services/api";

export function Dashboard() {
  const {
    session,
    activeStage,
    activeAgent,
    currentProsecutor,
    currentDefender,
    currentJudge,
    executionA,
    executionB,
    liveLogs,
    isConnected,
    startDebate,
    stopDebate,
    loadDemo,
    runOfflineSimulation
  } = useSwarmSession();

  const [demos, setDemos] = useState([]);
  const [showVerdictModal, setShowVerdictModal] = useState(true);

  // Fetch demos on mount
  useEffect(() => {
    async function init() {
      const data = await api.getDemos();
      setDemos(data);
    }
    init();
  }, []);

  // When session becomes verified, ensure modal is shown
  useEffect(() => {
    if (session.status === "verified") {
      setShowVerdictModal(true);
    }
  }, [session.status]);

  const isDebating = session.status === "debating" || session.status === "executing";

  return (
    <div className="min-h-screen bg-[#08090e] text-zinc-100 flex flex-col forensic-grid selection:bg-rose-900 selection:text-white">
      {/* TOP FORENSIC HUD / HEADER */}
      <header className="sticky top-0 z-40 bg-[#0c0e17]/95 backdrop-blur-md border-b border-[#1c2235] px-5 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3.5">
          <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-700/80 flex items-center justify-center text-white shadow-inner">
            <Scale className="w-6 h-6 text-zinc-100" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-[21px] font-black tracking-wider uppercase text-white font-mono flex items-center gap-2">
                SWARM DEBUGGER
              </h1>
              <span className="text-[13px] px-2.5 py-1 rounded bg-zinc-900 border border-zinc-750 font-mono text-zinc-300 font-medium">
                SESSION #{session.session_id}
              </span>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-[13px] font-mono">
                <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.9)]" : "bg-amber-500"}`} />
                <span className={isConnected ? "text-emerald-400 font-bold" : "text-amber-400 font-medium"}>
                  {isConnected ? "● LIVE" : "STANDALONE"}
                </span>
              </div>
            </div>
            <p className="text-[13px] text-zinc-400 font-mono mt-0.5">
              "AI can argue about the bug. The code decides who is right."
            </p>
          </div>
        </div>

        {/* Live Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={startDebate}
            disabled={isDebating}
            className={`px-4 py-2 rounded-md text-sm font-mono font-bold flex items-center gap-2 transition-all border shadow-lg ${
              isDebating
                ? "bg-zinc-800 text-zinc-500 border-zinc-700 cursor-not-allowed"
                : "bg-rose-950 hover:bg-rose-900 text-rose-200 border-rose-700 hover:border-rose-500 shadow-[0_0_20px_rgba(244,63,94,0.35)] cursor-pointer"
            }`}
          >
            <Play className="w-4 h-4 fill-current" />
            {isDebating ? "DEBATE RUNNING..." : "START DEBATE"}
          </button>

          {isDebating && (
            <button
              onClick={stopDebate}
              className="px-4 py-2 rounded-md text-sm font-mono font-bold bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-zinc-600 flex items-center gap-2 transition-colors cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-current text-rose-400" />
              STOP
            </button>
          )}

          <button
            onClick={runOfflineSimulation}
            disabled={isDebating}
            className="px-4 py-2 rounded-md text-sm font-mono bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 flex items-center gap-2 transition-colors cursor-pointer"
            title="Instant multi-agent simulation walkthrough for testing"
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            DEMO SIMULATION
          </button>
        </div>
      </header>

      {/* FORENSIC TELEMETRY BANNER */}
      <div className="bg-[#0b0e18] border-b border-[#181d2e] px-5 py-2.5 flex flex-wrap items-center justify-between text-[14px] font-mono text-zinc-300">
        <div className="flex items-center gap-2 max-w-2xl">
          <Bug className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="text-zinc-400">Target Bug:</span>
          <span className="text-zinc-100 font-semibold truncate">
            {session.bug_description}
          </span>
        </div>
        <div className="flex items-center gap-5 text-[13px] text-zinc-400">
          <span>Active Agent: <strong className="text-zinc-100 uppercase font-bold">{activeAgent || "IDLE"}</strong></span>
          <span>Pipeline Stage: <strong className="text-sky-400 font-bold uppercase">{activeStage || "READY"}</strong></span>
          <span>Command: <strong className="text-emerald-400 font-bold">{session.test_command}</strong></span>
        </div>
      </div>

      {/* MAIN ADVERSARIAL WORKSPACE */}
      <main className="flex-1 p-4 md:p-5 grid grid-cols-1 xl:grid-cols-12 gap-4 max-w-[1920px] mx-auto w-full">
        {/* LEFT COLUMN: CODEBASE & TESTS */}
        <section className="xl:col-span-3 min-h-[550px] xl:min-h-[720px] flex flex-col">
          <CodebasePanel
            demos={demos}
            selectedDemoId={session.demo_id}
            onSelectDemo={loadDemo}
            testCommand={session.test_command}
          />
        </section>

        {/* CENTER COLUMN: DEBATE ARENA & JUDGE ARENA */}
        <section className="xl:col-span-6 flex flex-col gap-4 min-h-[720px]">
          {/* DEBATE ARENA: Prosecutor (Fix A) vs Defender (Fix B) */}
          <div className="flex-1 min-h-[380px]">
            <DebateArena
              prosecutor={currentProsecutor}
              defender={currentDefender}
              activeAgent={activeAgent}
              currentRound={session.current_round}
            />
          </div>

          {/* JUDGE ARENA: Sandbox Execution Comparison & Judicial Truth */}
          <div className="h-auto">
            <JudgeArena
              judge={currentJudge}
              executionA={executionA}
              executionB={executionB}
              activeAgent={activeAgent}
              currentRound={session.current_round}
            />
          </div>
        </section>

        {/* RIGHT COLUMN: EVIDENCE PANEL & LOGS */}
        <section className="xl:col-span-3 min-h-[550px] xl:min-h-[720px] flex flex-col">
          <EvidencePanel
            logs={liveLogs}
            carriedEvidence={session.rounds[session.rounds.length - 1]?.failed_evidence_carried_over}
          />
        </section>
      </main>

      {/* BOTTOM PROGRESSION TIMELINE */}
      <footer className="sticky bottom-0 z-30 bg-[#0a0c14]/95 backdrop-blur border-t border-[#181d2e] px-5 py-3">
        <RoundTimeline
          currentRound={session.current_round}
          maxRounds={session.max_rounds}
          status={session.status}
        />
      </footer>

      {/* FINAL VERDICT MODAL (when fix is verified by actual test execution) */}
      {showVerdictModal && session.status === "verified" && (
        <FinalVerdict
          winningPatch={session.winning_patch || currentJudge?.winning_patch || "B"}
          verifiedPatch={session.verified_patch}
          reason={currentJudge?.reason}
          onClose={() => setShowVerdictModal(false)}
        />
      )}
    </div>
  );
}
export default Dashboard;
