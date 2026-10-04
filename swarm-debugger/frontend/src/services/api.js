const API_BASE = "http://localhost:8000/api";

export async function getDemos() {
  try {
    const res = await fetch(`${API_BASE}/demos`);
    if (!res.ok) throw new Error("Failed to fetch demos");
    return await res.json();
  } catch (err) {
    console.warn("Using offline demo list fallback:", err);
    return [
      {
        id: "bug-01",
        title: "Batch Slicing Off-by-One Overflow",
        description: "IndexError and boundary leak when batch slicing collection whose length matches multiple of batch size.",
        test_command: "pytest test_processor.py",
        files: ["processor.py", "test_processor.py"]
      },
      {
        id: "bug-02",
        title: "Default Mutable Argument State Bleed",
        description: "Shared list accumulator retains data across consecutive function calls in multi-threaded query builder.",
        test_command: "pytest test_accumulator.py",
        files: ["accumulator.py", "test_accumulator.py"]
      },
      {
        id: "bug-03",
        title: "RegEx Tokenizer ReDoS & Escape Failure",
        description: "Regex fails on unescaped brackets and catastrophic backtracking on malformed input strings.",
        test_command: "pytest test_tokenizer.py",
        files: ["tokenizer.py", "test_tokenizer.py"]
      }
    ];
  }
}

export async function createSession(payload) {
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Failed to create session");
    return await res.json();
  } catch (err) {
    console.warn("Backend offline, generating client session:", err);
    return {
      session_id: `sess_${Math.random().toString(36).substring(2, 9)}`,
      status: "idle",
      bug_description: payload.bug_description,
      test_command: payload.test_command || "pytest",
      current_round: 1,
      max_rounds: payload.max_rounds || 3,
      demo_id: payload.demo_id,
      rounds: []
    };
  }
}

export async function startSession(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    if (!res.ok) throw new Error("Failed to start session");
    return await res.json();
  } catch (err) {
    console.warn("Start session fallback:", err);
    return { status: "debating" };
  }
}

export async function stopSession(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/stop`, {
      method: "POST"
    });
    return await res.json();
  } catch (err) {
    return { status: "stopped" };
  }
}

export async function getSession(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch session");
    return await res.json();
  } catch (err) {
    return null;
  }
}

export async function getSessionCodebase(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/codebase`);
    if (!res.ok) throw new Error("Failed to fetch codebase");
    return await res.json();
  } catch (err) {
    return null;
  }
}
