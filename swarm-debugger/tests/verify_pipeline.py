import asyncio
import json
import urllib.request
import websockets


async def test_live_pipeline():
    print("[1/4] Creating new debugging session...")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/sessions",
        data=json.dumps({
            "bug_description": "Off-by-one boundary failure in loop termination during batch slicing",
            "test_command": "pytest test_processor.py",
            "max_rounds": 3,
            "demo_id": "bug-01"
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        sess = json.loads(resp.read())
        session_id = sess["session_id"]
    print(f"Session created: {session_id}")

    print("[2/4] Connecting to WebSocket stream...")
    uri = f"ws://127.0.0.1:8000/api/sessions/{session_id}/events"
    async with websockets.connect(uri) as ws:
        init_msg = await ws.recv()
        data = json.loads(init_msg)
        print(f"WS connected: event='{data['event']}', session_id='{data['session_id']}'")

        print("[3/4] Triggering start session...")
        start_req = urllib.request.Request(
            f"http://127.0.0.1:8000/api/sessions/{session_id}/start",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(start_req)

        print("[4/4] Streaming live adversarial debate events...")
        events_received = []
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=8.0)
                event_data = json.loads(msg)
                evt_name = event_data.get("event")
                round_no = event_data.get("round")
                agent = event_data.get("agent")
                payload = event_data.get("payload", {})
                events_received.append(evt_name)
                print(f"  -> [{evt_name}] Round: {round_no}, Agent: {agent}")

                if evt_name == "agent_completed":
                    print(f"     Artifact from {agent}: {payload.get('message', '')}")
                elif evt_name == "execution_completed":
                    res = payload.get("result", {})
                    print(f"     Execution Proof: Patch {payload.get('patch')}: {res.get('status', '').upper()} (Passed: {res.get('tests_passed')}, Failed: {res.get('tests_failed')})")
                elif evt_name == "judge_completed":
                    print(f"     Judge Decision: {payload.get('decision')} (Winner: Patch {payload.get('winning_patch')})")
                elif evt_name == "verification_completed":
                    print(f"     >>> VERIFICATION COMPLETED: Winner Patch {payload.get('winning_patch')}")
                elif evt_name == "session_completed":
                    print(f"     >>> SESSION COMPLETED: {payload.get('status', '').upper()}")
                    break
                elif evt_name in ("session_stopped", "error"):
                    print(f"     >>> DEBATE TERMINATED: {evt_name}")
                    break
            except asyncio.TimeoutError:
                print("Stream timeout reached.")
                break

        print(f"\nALL CHECKS PASSED: Total events processed: {len(events_received)}")
        assert "session_started" in events_received
        assert "round_started" in events_received
        assert "agent_started" in events_received
        assert "agent_completed" in events_received
        assert "judge_started" in events_received
        assert "execution_started" in events_received
        assert "execution_completed" in events_received
        assert "judge_completed" in events_received
        assert "round_completed" in events_received
        assert "verification_completed" in events_received
        assert "session_completed" in events_received


if __name__ == "__main__":
    asyncio.run(test_live_pipeline())
