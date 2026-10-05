import json
from unittest.mock import patch, MagicMock
import pytest
from app import app, db, User, RealTimeAQI
from agent.llm import AirGuardLLM

@pytest.fixture
def auth_header(client):
    res = client.post("/api/auth/login", json={"email": "demo_user", "password": "demo123"})
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}

def test_llm_auto_provider_selection(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_gemini")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = AirGuardLLM()
    assert llm.provider == "gemini"
    assert llm.get_provider_name() == "GEMINI"

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_claude")
    llm = AirGuardLLM()
    assert llm.provider == "anthropic"

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_openai")
    llm = AirGuardLLM()
    assert llm.provider == "openai"

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = AirGuardLLM()
    assert llm.provider == "mock"

def test_llm_call_gemini_success_and_failure(monkeypatch):
    llm = AirGuardLLM(provider="gemini")
    llm.gemini_key = "test_key"

    # Success case
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {
            "candidates": [{"content": {"parts": [{"text": "Stay indoors during high AQI hours."}]}}]
        })
        res = llm._call_gemini("Is it safe?", {}, "system prompt")
        assert "Stay indoors" in res

    # Failure case
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        with pytest.raises(RuntimeError):
            llm._call_gemini("Is it safe?", {}, "system prompt")

def test_llm_call_anthropic_success_and_failure(monkeypatch):
    llm = AirGuardLLM(provider="anthropic")
    llm.anthropic_key = "test_key"

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {
            "content": [{"text": "Keep your inhaler with you."}]
        })
        res = llm._call_anthropic("Query", {}, "system prompt")
        assert "Keep your inhaler" in res

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")
        with pytest.raises(RuntimeError):
            llm._call_anthropic("Query", {}, "system prompt")

def test_llm_call_openai_success_and_failure(monkeypatch):
    llm = AirGuardLLM(provider="openai")
    llm.openai_key = "test_key"

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {
            "choices": [{"message": {"content": "Air quality is moderate today."}}]
        })
        res = llm._call_openai("Query", {}, "system prompt")
        assert "Air quality" in res

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=429, text="Rate limit")
        with pytest.raises(RuntimeError):
            llm._call_openai("Query", {}, "system prompt")

def test_llm_fallback_on_api_exception(monkeypatch):
    llm = AirGuardLLM(provider="gemini")
    llm.gemini_key = "test_key"

    with patch.object(llm, "_call_gemini", side_effect=Exception("Connection timed out")):
        res = llm.generate_response("Can I go for a jog?", {"aqi": 110, "safest_window": "06:00 - 08:00"})
        assert "MOCK_FALLBACK" in res["provider"]
        assert len(res["response"]) > 0

def test_llm_hindi_mock_responses():
    llm = AirGuardLLM(provider="mock")
    res_outdoor = llm.generate_response("क्या मैं बाहर दौड़ सकता हूँ?", {"aqi": 120, "safest_window": "07:00 - 09:00"}, language="hi")
    assert "वायु गुणवत्ता सूचकांक" in res_outdoor["response"]
    assert "07:00 - 09:00" in res_outdoor["response"]

    res_general = llm.generate_response("मेरी सेहत कैसी है?", {"aqi": 50, "risk_tier": "Low"}, language="hi")
    assert "नमस्ते" in res_general["response"]

def test_real_time_aqi_service():
    service = RealTimeAQI()
    with patch("requests.get") as mock_get:
        # Mock successful AQI and Weather responses
        mock_get.side_effect = [
            MagicMock(json=lambda: {"current": {"us_aqi": 75, "pm2_5": 22.5, "nitrogen_dioxide": 18.0, "sulphur_dioxide": 8.0}}),
            MagicMock(json=lambda: {"current": {"temperature_2m": 28.0, "relative_humidity_2m": 65.0}})
        ]
        data = service.get_live_data(28.6139, 77.2090)
        assert data is not None
        assert data["AQI"] == 75
        assert data["temperature"] == 28.0

    # Test error handling
    with patch("requests.get", side_effect=Exception("Network error")):
        data = service.get_live_data(28.6139, 77.2090)
        assert data is None

def test_additional_app_routes(client, auth_header):
    # Test UI route
    r_index = client.get("/")
    assert r_index.status_code == 200

    # Test admin overview route with doctor/admin token
    res_doc = client.post("/api/auth/login", json={"email": "doctor@example.com", "password": "doctor123"})
    assert res_doc.status_code == 200
    doc_token = res_doc.get_json()["token"]
    r_admin = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {doc_token}"})
    assert r_admin.status_code == 200

    # Test recent, stats, figures, eda
    assert client.get("/api/recent").status_code == 200
    assert client.get("/api/stats").status_code == 200
    assert client.get("/api/figures_list").status_code == 200
    assert client.get("/api/eda_data").status_code == 200

    # User profile GET and POST
    r_prof = client.get("/api/get-user/1", headers=auth_header)
    assert r_prof.status_code == 200
    assert r_prof.get_json()["success"] is True

    r_save = client.post("/api/save-profile", json={"user_id": 1, "name": "Alex Updated", "age": 29}, headers=auth_header)
    assert r_save.status_code == 200
    assert r_save.get_json()["success"] is True

    # Upload sensor data
    r_sensor = client.post("/api/upload-sensor-data", json={"user_id": 1, "AQI": 85, "PM2.5": 25.0, "Temperature": 24.0, "Humidity": 60.0})
    assert r_sensor.status_code == 200

    # Get user data
    r_u_data = client.get("/api/get-user-data/1", headers=auth_header)
    assert r_u_data.status_code == 200

    # Submit quiz and get quiz responses
    r_quiz = client.post("/api/submit-quiz", json={"user_id": 1, "symptoms": "mild coughing", "severity": 2}, headers=auth_header)
    assert r_quiz.status_code == 200
    r_q_resp = client.get("/api/get-quiz-responses/1", headers=auth_header)
    assert r_q_resp.status_code == 200

    # Get alerts
    r_alerts = client.get("/api/get-alerts/1", headers=auth_header)
    assert r_alerts.status_code == 200

    # Send data to AI route
    r_ai = client.post("/api/send-data-to-ai/1", json={"action": "analyze"}, headers=auth_header)
    assert r_ai.status_code == 200
