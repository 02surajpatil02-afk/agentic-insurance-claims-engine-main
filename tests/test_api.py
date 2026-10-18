"""
Integration tests for FastAPI REST API endpoints.
"""

from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Autonomous Enterprise Workflow Agent" in data["system"]


def test_api_get_samples():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) >= 4
    filenames = [s["filename"] for s in samples]
    assert "clean_approve.txt" in filenames
    assert "clean_reject.txt" in filenames
    assert "over_threshold.txt" in filenames
    assert "conflicting_data.txt" in filenames


def test_api_process_clean_approve():
    with open("sample_claims/clean_approve.txt", "r", encoding="utf-8") as f:
        text = f.read()

    response = client.post("/api/workflow/process", json={"raw_text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved_approved"
    assert data["decision"] == "approved"
    assert data["extracted_entities"]["claimant_name"] == "Sarah Jenkins"
    assert data["extracted_entities"]["policy_number"] == "POL-8829104"


def test_api_process_over_threshold_and_resume():
    with open("sample_claims/over_threshold.txt", "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Process claim -> MUST HALT for HITL review
    response = client.post("/api/workflow/process", json={"raw_text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_human_review"
    claim_id = data["claim_id"]

    # 2. Fetch claim by ID via API
    get_resp = client.get(f"/api/claims/{claim_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["claim_id"] == claim_id

    # 3. Resume claim via API
    resume_payload = {
        "claim_id": claim_id,
        "action": "approve",
        "notes": "Verified surgery authorization with CMO.",
        "caseworker_signature": "Dr. Vance"
    }
    resume_resp = client.post("/api/workflow/resume", json=resume_payload)
    assert resume_resp.status_code == 200
    resumed_data = resume_resp.json()
    assert resumed_data["status"] == "resolved_approved"
    assert resumed_data["decision"] == "approved"
    assert resumed_data["caseworker_decision"]["caseworker_signature"] == "Dr. Vance"


def test_api_process_clean_reject():
    with open("sample_claims/clean_reject.txt", "r", encoding="utf-8") as f:
        text = f.read()

    response = client.post("/api/workflow/process", json={"raw_text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved_rejected"
    assert data["decision"] == "rejected"
    assert data["extracted_entities"]["policy_number"] == "INVALID_9999"


def test_api_claim_not_found_404():
    response = client.get("/api/claims/NON_EXISTENT_ID_999")
    assert response.status_code == 404
