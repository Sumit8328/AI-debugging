# SWARM DEBUGGER ⚡

> **"AI can argue about the bug. The code decides who is right."**

An adversarial multi-agent debugging system where specialized AI agents debate candidate fixes, but the code itself—executed in an isolated sandbox—serves as the sole source of truth.

---

## 🏛 The Adversarial Architecture

```
                       +-------------------+
                       |   Reported Bug    |
                       +---------+---------+
                                 |
               +-----------------+-----------------+
               |                                   |
               v                                   v
      +-----------------+                 +-----------------+
      | Prosecutor (A)  |                 |  Defender (B)   |
      | Focus: Causes   |                 | Focus: Edge     |
      | Fix A: Fast     |                 | Fix B: Robust   |
      +--------+--------+                 +--------+--------+
               \                                   /
                \           ROUND N               /
                 +---------------+---------------+
                                 |
                                 v
                     +-----------------------+
                     | Isolated Docker       |
                     | Sandbox Test Runner   |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     |      Judge Agent      |
                     |  Adjudicates solely   |
                     |  on execution truth   |
                     +-----------+-----------+
                                 |
                +----------------+----------------+
                |                                 |
        [All Tests Pass]                   [Tests Fail]
                v                                 v
          ◎ VERIFIED                     Carry failed traces
                                         into Round N+1
```

- **Prosecutor Agent (Crimson Red)**: Investigates the bug, pinpoints root causes, and proposes Fix A.
- **Defender Agent (Cyan Blue)**: Challenges the prosecutor's hypothesis, identifies regression risks and edge cases, and proposes Fix B.
- **Judge Agent (Neutral Silver/White)**: Validates patches by running pytest in an isolated sandbox.
- **Single Source of Truth**: The system **NEVER** declares a patch "VERIFIED" based solely on LLM confidence. Pytest execution in the sandbox determines the victor.
- **Evidence Dossier**: Failed execution traces, pytest failures, and stderr are carried over into subsequent rounds to guide refined proposals.

---

## 📁 Project Structure

```text
swarm-debugger/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DebateArena/        # Side-by-side Prosecutor vs Defender debate
│   │   │   ├── JudgeArena/         # Sandbox comparison of Patch A vs Patch B
│   │   │   ├── EvidencePanel/      # Real-time execution logs and test output
│   │   │   ├── CodebasePanel/      # Source tree and demo project viewer
│   │   │   ├── RoundTimeline/      # R1 -> R2 -> R3 -> VERIFIED timeline
│   │   │   └── FinalVerdict/       # Judicial verification banner
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── backend/
│   ├── agents/
│   │   ├── prosecutor.py           # Prosecutor Agent interface & stubs
│   │   ├── defender.py             # Defender Agent interface & stubs
│   │   ├── judge.py                # Judge Agent adjudication logic
│   │   └── prompts.py              # Structured system prompts
│   ├── orchestrator/
│   │   ├── engine.py               # Async multi-agent debate engine
│   │   ├── round_manager.py        # Round transitions & evidence carryover
│   │   └── state.py                # In-memory session registry & WS broadcast
│   ├── sandbox/
│   │   ├── docker_runner.py        # Isolated sandbox runner stub
│   │   ├── resource_limits.py      # CPU, RAM, and timeout security limits
│   │   └── patch_validator.py      # Static safety checks (Rule 6: Never run on host)
│   ├── evidence/
│   │   ├── collector.py            # Evidence aggregation
│   │   ├── analyzer.py             # Pytest failure & traceback parser
│   │   └── evidence_brief.py       # Round-by-round evidence dossier
│   ├── repository/
│   │   ├── loader.py               # Demo and archive loader
│   │   ├── scanner.py              # File tree and test scanner
│   │   └── git_manager.py          # Patch staging stubs
│   ├── api/
│   │   ├── routes.py               # REST API endpoints
│   │   └── websocket.py            # Real-time WebSocket streaming
│   ├── database/
│   │   ├── models.py               # SQLite session repository
│   │   └── database.py             # SQLite connection and schema init
│   ├── schemas/
│   │   ├── session.py              # Session Pydantic models
│   │   ├── agents.py               # Prosecutor, Defender, Judge models
│   │   ├── execution.py            # ExecutionResult & sandbox configs
│   │   └── events.py               # WebSocket event envelopes
│   ├── config.py                   # Pydantic Settings & env configuration
│   └── main.py                     # FastAPI application entrypoint
│
├── demo-projects/
│   ├── bug-01/                     # Batch Slicing Off-by-One Overflow
│   ├── bug-02/                     # Mutable Default Argument State Bleed
│   └── bug-03/                     # Regex Tokenizer Escape Failure
│
├── tests/
│   ├── test_schemas.py             # Pydantic schema validation tests
│   └── test_api.py                 # FastAPI route integration tests
│
├── docker/
│   └── Dockerfile                  # Isolated sandbox Docker image
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
cd swarm-debugger

# Install backend dependencies
pip install -r requirements.txt

# Start backend server
uvicorn backend.main:app --reload
```
Backend will be live at `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

### 2. Frontend Setup

```bash
cd swarm-debugger/frontend

# Install frontend dependencies
npm install

# Start development UI
npm run dev
```
Frontend will be accessible at `http://localhost:5173`.

---

## 📡 Prepared API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/sessions` | Initialize a new debugging session |
| `POST` | `/api/sessions/{session_id}/start` | Launch adversarial multi-agent debate |
| `GET` | `/api/sessions/{session_id}` | Retrieve session state, history, and verified patch |
| `POST` | `/api/sessions/{session_id}/stop` | Halts active debugging session |
| `WS` | `/api/sessions/{session_id}/events` | Real-time WebSocket event stream |
| `GET` | `/api/demos` | List preset hackathon demo projects |
| `GET` | `/api/sessions/{session_id}/codebase` | Codebase tree and files for session |

---

## 🛡 Security Rules

1. **Host Isolation**: Candidate patches are **never** executed directly on the host machine.
2. **Static Patch Validation**: Patches are screened by `PatchSafetyValidator` before any sandbox execution to prevent escape attempts or destructive shell commands.
3. **Sandbox Resource Limits**: Max 512MB RAM, 1.0 CPU core, 30s timeout, no network egress.
4. **Zero Hardcoded Secrets**: All AI configurations rely on environment variables (`.env.example`).
