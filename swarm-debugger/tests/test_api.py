import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "SWARM DEBUGGER"
    assert "tagline" in data


def test_list_demos():
    response = client.get("/api/demos")
    assert response.status_code == 200
    demos = response.json()
    assert len(demos) == 3
    assert demos[0]["id"] == "bug-01"


def test_create_and_get_session():
    create_payload = {
        "bug_description": "Off by one loop overflow in batch slicing",
        "test_command": "pytest test_processor.py",
        "max_rounds": 3,
        "demo_id": "bug-01"
    }
    create_res = client.post("/api/sessions", json=create_payload)
    assert create_res.status_code == 200
    session_data = create_res.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "idle"

    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

    # Test start endpoint
    start_res = client.post(f"/api/sessions/{session_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "debating"

    # Test stop endpoint
    stop_res = client.post(f"/api/sessions/{session_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # Test codebase endpoint
    codebase_res = client.get(f"/api/sessions/{session_id}/codebase")
    assert codebase_res.status_code == 200
    assert "tree" in codebase_res.json()
    assert "files" in codebase_res.json()

