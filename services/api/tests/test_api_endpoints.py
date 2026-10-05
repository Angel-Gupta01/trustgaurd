# services/api/tests/test_api_endpoints.py
import pytest
from starlette.testclient import TestClient
from trustguard_api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert "requestId" in data

def test_anonymous_vishing_scan():
    payload = {
        "text": "URGENT ACTION REQUIRED: Verify your password and confirm your pin immediately to prevent legal action and asset freeze!",
        "source_type": "PASTED_TEXT"
    }
    response = client.post("/api/v1/vishing/scan", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    scan_result = json_data["data"]
    assert scan_result["is_critical"] is True
    assert float(scan_result["risk_score"]) >= 70.0
    assert "HANG UP" in scan_result["recommendation"]
    assert "URGENCY_PRESSURE" in scan_result["matched_categories"]

def test_benign_vishing_scan():
    payload = {
        "text": "Hey John, can you please email me the updated slides for tomorrow's standup meeting?",
        "source_type": "PASTED_TEXT"
    }
    response = client.post("/api/v1/vishing/scan", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    scan_result = json_data["data"]
    assert scan_result["is_critical"] is False
    assert float(scan_result["risk_score"]) < 40.0
    assert "LOOKS SAFE" in scan_result["recommendation"]

def test_validation_error_envelope():
    # Sending missing required text field
    response = client.post("/api/v1/vishing/scan", json={"source_type": "PASTED_TEXT"})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "requestId" in data
