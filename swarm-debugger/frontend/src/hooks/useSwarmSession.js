import { useState, useEffect, useRef, useCallback } from "react";
import * as api from "../services/api";

export function useSwarmSession(initialSessionId = null) {
  const [session, setSession] = useState({
    session_id: initialSessionId || "sess_demo_live",
    status: "idle",
    bug_description: "Off-by-one boundary failure in loop termination condition during batch slicing.",
    test_command: "pytest test_processor.py",
    current_round: 1,
    max_rounds: 3,
    demo_id: "bug-01",
    rounds: [],
    verified_patch: null,
    winning_patch: null,
  });

  const [activeStage, setActiveStage] = useState("IDLE");
  const [activeAgent, setActiveAgent] = useState(null);
  const [currentProsecutor, setCurrentProsecutor] = useState(null);
  const [currentDefender, setCurrentDefender] = useState(null);
  const [currentJudge, setCurrentJudge] = useState(null);
  const [executionA, setExecutionA] = useState(null);
  const [executionB, setExecutionB] = useState(null);
  const [liveLogs, setLiveLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  const addLog = useCallback((sender, message, type = "info") => {
    const timestamp = new Date().toISOString().substring(11, 19);
    setLiveLogs((prev) => [...prev.slice(-150), { timestamp, sender, message, type }]);
  }, []);

  // Handle incoming typed DebugEvent
  const handleEvent = useCallback((data) => {
    const { event, round, agent, payload } = data;

    if (round) {
      setSession((prev) => ({ ...prev, current_round: round }));
    }

    switch (event) {
      case "session_created":
      case "connected":
        setIsConnected(true);
        addLog("SYSTEM", `Session initialized: ${data.session_id}`, "system");
        if (payload?.rounds?.length) {
          const lastRound = payload.rounds[payload.rounds.length - 1];
          if (lastRound.prosecutor_result) setCurrentProsecutor(lastRound.prosecutor_result);
          if (lastRound.defender_result) setCurrentDefender(lastRound.defender_result);
          if (lastRound.patch_a_execution) setExecutionA(lastRound.patch_a_execution);
          if (lastRound.patch_b_execution) setExecutionB(lastRound.patch_b_execution);
          if (lastRound.judge_result) setCurrentJudge(lastRound.judge_result);
        }
        break;

      case "session_started":
        setSession((prev) => ({ ...prev, status: "debating" }));
        setActiveStage("SESSION STARTED");
        addLog("ORCHESTRATOR", `Adversarial session started. Bug: ${payload.bug_description}`, "system");
        break;

      case "round_started":
        setActiveStage(`ROUND ${payload.round || round} STARTED`);
        addLog("ORCHESTRATOR", `Round ${payload.round || round} initiated [DEMO / MOCK MODE]`, "system");
        break;

      case "agent_started":
        setActiveAgent(agent);
        setActiveStage(`${agent?.toUpperCase()} ANALYZING`);
        addLog(agent?.toUpperCase() || "AGENT", payload.message || `${agent} started`, agent);
        break;

      case "agent_completed":
        if (agent === "prosecutor") {
          const result = payload.result || payload;
          setCurrentProsecutor(result);
          addLog("PROSECUTOR", `Indictment ready. Root cause: ${result.root_cause}`, "prosecutor");
        } else if (agent === "defender") {
          const result = payload.result || payload;
          setCurrentDefender(result);
          addLog("DEFENDER", `Challenge issued: ${result.challenge}`, "defender");
        }
        break;

      case "judge_started":
        setActiveAgent("judge");
        setActiveStage("SANDBOX VALIDATION");
        addLog("JUDGE", payload.message || "Judge evaluating candidate patches in sandbox", "judge");
        break;

      case "execution_started":
        if (payload?.patch === "A") {
          setExecutionA({ status: "running", patch: "A" });
        } else if (payload?.patch === "B") {
          setExecutionB({ status: "running", patch: "B" });
        }
        addLog("SANDBOX", `Executing candidate Patch ${payload.patch} in isolated container...`, "info");
        break;

      case "execution_completed":
        {
          const patchKey = payload.patch;
          const res = payload.result || payload.payload;
          if (patchKey === "A") {
            setExecutionA(res);
            addLog("SANDBOX", `Patch A: ${res.status.toUpperCase()} (${res.tests_passed} passed, ${res.tests_failed} failed, ${res.duration_ms}ms)`, res.status === "passed" ? "success" : "warning");
          } else {
            setExecutionB(res);
            addLog("SANDBOX", `Patch B: ${res.status.toUpperCase()} (${res.tests_passed} passed, ${res.tests_failed} failed, ${res.duration_ms}ms)`, res.status === "passed" ? "success" : "warning");
          }
        }
        break;

      case "judge_completed":
        {
          const result = payload.result || payload;
          setCurrentJudge(result);
          setActiveAgent("judge");
          const outcome = result.winning_patch ? `Winner: Patch ${result.winning_patch}` : result.decision;
          addLog("JUDGE", `Judicial decision: ${result.decision} (${outcome}). ${result.reason}`, "judge");
        }
        break;

      case "round_completed":
        addLog("SYSTEM", `Round ${payload.round || round} complete.`, "info");
        break;

      case "evidence_created":
        addLog("SYSTEM", `Carried failure traces to Round ${payload.next_round}.`, "warning");
        break;

      case "verification_completed":
        setSession((prev) => ({
          ...prev,
          status: "verified",
          verified_patch: payload.verified_patch,
          winning_patch: payload.winning_patch
        }));
        setActiveStage("VERIFIED");
        addLog("VERDICT", `Fix VERIFIED by actual sandbox test execution! Winner: Patch ${payload.winning_patch}`, "success");
        break;

      case "session_completed":
        if (payload.status === "verified") {
          setSession((prev) => ({
            ...prev,
            status: "verified",
            verified_patch: payload.verified_patch || prev.verified_patch,
            winning_patch: payload.winning_patch || prev.winning_patch
          }));
          setActiveStage("VERIFIED");
        } else {
          setSession((prev) => ({ ...prev, status: "failed" }));
          setActiveStage("FAILED");
          addLog("VERDICT", `Debate concluded without verified patch: ${payload.message}`, "error");
        }
        break;

      case "session_stopped":
        setSession((prev) => ({ ...prev, status: "stopped" }));
        setActiveStage("STOPPED");
        addLog("SYSTEM", "Session stopped by user request.", "warning");
        break;

      default:
        break;
    }
  }, [addLog]);

  // Connect WebSocket to backend
  useEffect(() => {
    if (!session.session_id) return;

    let socket;
    try {
      socket = new WebSocket(`ws://localhost:8000/api/sessions/${session.session_id}/events`);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          handleEvent(data);
        } catch (e) {
          console.error("Invalid WS message:", e);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
      };

      socket.onerror = () => {
        setIsConnected(false);
      };
    } catch (e) {
      setIsConnected(false);
    }

    return () => {
      if (socket) socket.close();
    };
  }, [session.session_id, handleEvent]);

  // Actions
  const startDebate = async () => {
    try {
      setSession((prev) => ({ ...prev, status: "debating" }));
      addLog("SYSTEM", "Triggering adversarial multi-agent debate loop...", "system");
      await api.startSession(session.session_id);
    } catch (err) {
      addLog("ERROR", `Failed to start session: ${err.message}`, "error");
    }
  };

  const stopDebate = async () => {
    try {
      await api.stopSession(session.session_id);
      setSession((prev) => ({ ...prev, status: "stopped" }));
      addLog("SYSTEM", "Stop command dispatched.", "warning");
    } catch (err) {
      addLog("ERROR", `Failed to stop: ${err.message}`, "error");
    }
  };

  const loadDemo = async (demo) => {
    const newSession = await api.createSession({
      bug_description: demo.description,
      test_command: demo.test_command,
      max_rounds: 3,
      demo_id: demo.id
    });
    setSession({
      ...newSession,
      rounds: []
    });
    setCurrentProsecutor(null);
    setCurrentDefender(null);
    setCurrentJudge(null);
    setExecutionA(null);
    setExecutionB(null);
    setLiveLogs([]);
    addLog("SYSTEM", `Loaded preset demo: ${demo.title}`, "system");
  };

  // Deterministic local simulation walkthrough
  const runOfflineSimulation = useCallback(() => {
    setSession((prev) => ({ ...prev, status: "debating", current_round: 1 }));
    setCurrentProsecutor(null);
    setCurrentDefender(null);
    setCurrentJudge(null);
    setExecutionA(null);
    setExecutionB(null);
    addLog("SYSTEM", "Starting deterministic adversarial simulation [DEMO / MOCK]...", "system");

    setTimeout(() => {
      handleEvent({
        event: "session_started",
        session_id: session.session_id,
        round: 1,
        agent: "system",
        payload: {
          bug_description: session.bug_description,
          test_command: session.test_command,
          max_rounds: 3
        }
      });
    }, 500);

    setTimeout(() => {
      handleEvent({
        event: "round_started",
        session_id: session.session_id,
        round: 1,
        agent: "system",
        payload: { round: 1 }
      });
      handleEvent({
        event: "agent_started",
        session_id: session.session_id,
        round: 1,
        agent: "prosecutor",
        payload: { message: "Round 1: Prosecutor analyzing failure traces [DEMO / MOCK]" }
      });
    }, 1200);

    setTimeout(() => {
      handleEvent({
        event: "agent_completed",
        session_id: session.session_id,
        round: 1,
        agent: "prosecutor",
        payload: {
          result: {
            root_cause: "The loop iterates one position beyond the valid range due to an off-by-one boundary failure.",
            evidence: [
              "range() uses len(items) + 1 in loop termination condition",
              "The failing test reports an IndexError: list index out of range during boundary condition"
            ],
            affected_files: ["processor.py"],
            proposed_patch: `--- a/processor.py\n+++ b/processor.py\n@@ -39,5 +39,5 @@\n-    for i in range(0, len(items) + 1, batch_size):\n+    for i in range(0, len(items), batch_size):\n         batches.append(items[i:i + batch_size])`,
            reasoning_summary: "The extra iteration causes an out-of-range access when collection size is an exact multiple of batch_size."
          }
        }
      });
      handleEvent({
        event: "agent_started",
        session_id: session.session_id,
        round: 1,
        agent: "defender",
        payload: { message: "Round 1: Defender challenging hypothesis & checking regressions [DEMO / MOCK]" }
      });
    }, 2500);

    setTimeout(() => {
      handleEvent({
        event: "agent_completed",
        session_id: session.session_id,
        round: 1,
        agent: "defender",
        payload: {
          result: {
            challenge: "Prosecutor's Fix A is naive: the loop boundary is not the only issue and Fix A causes regressions on non-positive batch sizes and generator inputs.",
            alternative_hypothesis: "The caller contract must validate batch_size and normalize iterable inputs, not merely adjust the range stop index.",
            evidence: [
              "batch_size is not validated before iteration begins",
              "Non-positive batch_size (<= 0) causes ValueError/infinite loop",
              "Streaming generator inputs lacking __len__ raise TypeError under Fix A"
            ],
            affected_files: ["processor.py"],
            proposed_patch: `--- a/processor.py\n+++ b/processor.py\n@@ -35,7 +35,11 @@\n+    if batch_size <= 0:\n+        raise ValueError("batch_size must be positive integer")\n     batches = []\n-    for i in range(0, len(items) + 1, batch_size):\n+    item_list = list(items)\n+    for i in range(0, len(item_list), batch_size):\n         batches.append(item_list[i:i + batch_size])`,
            reasoning_summary: "Fix B converts input safely, validates positive batch_size, and eliminates boundary overflow while supporting any iterable."
          }
        }
      });
      handleEvent({
        event: "judge_started",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: { message: "Round 1: Judge evaluating candidate patches in isolated sandbox [DEMO / MOCK]" }
      });
    }, 4000);

    setTimeout(() => {
      handleEvent({
        event: "execution_started",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: { patch: "A" }
      });
      handleEvent({
        event: "execution_completed",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: {
          patch: "A",
          result: {
            patch: "A",
            status: "failed",
            stdout: "[DEMO / MOCK SANDBOX RUNNER]\ntest_processor.py::test_standard_batch PASSED\ntest_processor.py::test_zero_or_negative_batch_size FAILED\n==== 1 failed, 4 passed in 0.38s ====",
            stderr: "FAILED test_processor.py::test_zero_or_negative_batch_size - Failed: DID NOT RAISE <class 'ValueError'>",
            exit_code: 1,
            tests_passed: 4,
            tests_failed: 1,
            duration_ms: 382
          }
        }
      });
    }, 5200);

    setTimeout(() => {
      handleEvent({
        event: "execution_started",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: { patch: "B" }
      });
      handleEvent({
        event: "execution_completed",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: {
          patch: "B",
          result: {
            patch: "B",
            status: "passed",
            stdout: "[DEMO / MOCK SANDBOX RUNNER]\ntest_processor.py::test_standard_batch PASSED\ntest_processor.py::test_boundary_exact_match PASSED\ntest_processor.py::test_empty_input PASSED\ntest_processor.py::test_single_item PASSED\ntest_processor.py::test_zero_or_negative_batch_size PASSED\n==== 5 passed in 0.42s ====",
            stderr: "",
            exit_code: 0,
            tests_passed: 5,
            tests_failed: 0,
            duration_ms: 418
          }
        }
      });
    }, 6500);

    setTimeout(() => {
      handleEvent({
        event: "judge_completed",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: {
          decision: "VERIFIED",
          winning_patch: "B",
          reason: "Fix B VERIFIED by actual pytest execution in sandbox. All 5 tests passed with exit code 0. Fix A failed with 1 test failure.",
          result: {
            decision: "VERIFIED",
            winning_patch: "B",
            reason: "Fix B VERIFIED by actual pytest execution in sandbox. All 5 tests passed with exit code 0. Fix A failed with 1 test failure."
          }
        }
      });
      handleEvent({
        event: "round_completed",
        session_id: session.session_id,
        round: 1,
        agent: "system",
        payload: { round: 1, status: "completed" }
      });
    }, 7800);

    setTimeout(() => {
      handleEvent({
        event: "verification_completed",
        session_id: session.session_id,
        round: 1,
        agent: "judge",
        payload: {
          winning_patch: "B",
          verified_patch: `--- a/processor.py\n+++ b/processor.py\n@@ -35,7 +35,11 @@\n+    if batch_size <= 0:\n+        raise ValueError("batch_size must be positive integer")\n     batches = []\n-    for i in range(0, len(items) + 1, batch_size):\n+    item_list = list(items)\n+    for i in range(0, len(item_list), batch_size):\n         batches.append(item_list[i:i + batch_size])`,
          reason: "Fix B VERIFIED by actual pytest execution in sandbox. All 5 tests passed with exit code 0."
        }
      });
      handleEvent({
        event: "session_completed",
        session_id: session.session_id,
        round: 1,
        agent: "system",
        payload: { status: "verified", winning_patch: "B" }
      });
    }, 8800);
  }, [handleEvent, addLog, session.bug_description, session.test_command, session.session_id]);

  return {
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
  };
}
