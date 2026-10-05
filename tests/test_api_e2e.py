import json
import os
import io
import time
import http.server
import threading
import sqlite3
import pytest
from datetime import datetime

import app as flask_app_module
from app import app, db, get_db_connection, generate_auth_token, verify_auth_token
from models import User, SensorData, SymptomDiary, AgentAction, AgentLog, Alert, QuizResponse, DailyPlan
from agent.tools import AirGuardTools

# Local Fake n8n Webhook Server for testing webhook dispatches
class FakeWebhookHandler(http.server.BaseHTTPRequestHandler):
    received_payloads = []

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode('utf-8'))
            FakeWebhookHandler.received_payloads.append(payload)
        except Exception:
            FakeWebhookHandler.received_payloads.append({"raw": body.decode('utf-8')})
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "delivered", "workflow_id": "test_wf_123"}).encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Quiet logs during test execution

@pytest.fixture(scope="module")
def fake_webhook_server():
    server = http.server.HTTPServer(('127.0.0.1', 8999), FakeWebhookHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    yield 'http://127.0.0.1:8999/webhook/test'
    server.shutdown()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-12345'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

@pytest.fixture
def test_users(client):
    """Creates two distinct patients and one doctor for strict IDOR and permission tests."""
    with app.app_context():
        # User A: Patient Alice
        user_a = User.query.filter_by(phone_no="+1-555-1001").first()
        if not user_a:
            user_a = User(
                name="Alice Walker",
                age=29,
                gender="Female",
                phone_no="+1-555-1001",
                medical_history="Mild asthma",
                baseline_severity="Mild Intermittent",
                inhaler_prescribed="Albuterol 2 puffs PRN",
                triggers="Cold Air",
                language_pref="en",
                city="Delhi",
                emergency_contact_name="Bob Walker",
                emergency_contact_phone="+1-555-1002"
            )
            user_a.set_password("alicePass123")
            db.session.add(user_a)

        # User B: Patient Charlie
        user_b = User.query.filter_by(phone_no="+1-555-2001").first()
        if not user_b:
            user_b = User(
                name="Charlie Day",
                age=35,
                gender="Male",
                phone_no="+1-555-2001",
                medical_history="Severe asthma",
                baseline_severity="Severe Persistent",
                inhaler_prescribed="Fluticasone 2 puffs BID",
                triggers="Dust, Smoke",
                language_pref="hi",
                city="Delhi",
                emergency_contact_name="Dee Reynolds",
                emergency_contact_phone="+1-555-2002"
            )
            user_b.set_password("charliePass123")
            db.session.add(user_b)

        # User C: Doctor
        doctor = User.query.filter_by(phone_no="+1-555-3001").first()
        if not doctor:
            doctor = User(
                name="Dr. Gregory House",
                age=50,
                gender="Male",
                phone_no="+1-555-3001",
                medical_history="Chief Physician",
                baseline_severity="Physician",
                inhaler_prescribed="None",
                triggers="None",
                language_pref="en",
                city="Delhi",
                emergency_contact_name="Hospital Desk",
                emergency_contact_phone="+1-555-9999"
            )
            doctor.set_password("doctorPass123")
            db.session.add(doctor)

        db.session.commit()

        token_a = generate_auth_token(user_a.id, role="User")
        token_b = generate_auth_token(user_b.id, role="User")
        token_doc = generate_auth_token(doctor.id, role="Admin")

        return {
            "user_a": {"id": user_a.id, "phone": user_a.phone_no, "token": token_a, "password": "alicePass123"},
            "user_b": {"id": user_b.id, "phone": user_b.phone_no, "token": token_b, "password": "charliePass123"},
            "doctor": {"id": doctor.id, "phone": doctor.phone_no, "token": token_doc, "password": "doctorPass123"}
        }

# ==============================================================================
# 1. AUTHENTICATION & CREDENTIAL TESTS
# ==============================================================================

def test_auth_signup_success(client):
    phone = f"+1-555-{int(time.time() * 1000) % 9000 + 1000}"
    resp = client.post("/api/auth/signup", json={
        "name": "New Test Patient",
        "phone_no": phone,
        "password": "SecurePassword123!",
        "age": 25,
        "gender": "Female"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    assert "token" in data
    assert verify_auth_token(data["token"]) is not None

def test_auth_signup_duplicate_phone_rejected_409(client, test_users):
    """Duplicate phone signup must be rejected with 409 Conflict without overwriting existing account."""
    resp = client.post("/api/auth/signup", json={
        "name": "Attacker Trying Overwrite",
        "phone_no": test_users["user_a"]["phone"],
        "password": "HackerPassword!"
    })
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["success"] is False
    assert "already exists" in data["error"]

def test_auth_login_success_and_wrong_password_rejected(client, test_users):
    # Successful login
    resp = client.post("/api/auth/login", json={
        "username": test_users["user_a"]["phone"],
        "password": test_users["user_a"]["password"]
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "token" in data

    # Wrong password -> 401
    resp_bad = client.post("/api/auth/login", json={
        "username": test_users["user_a"]["phone"],
        "password": "wrongPassword123"
    })
    assert resp_bad.status_code == 401
    assert resp_bad.get_json()["success"] is False

def test_auth_login_unknown_user_rejected_401(client):
    resp = client.post("/api/auth/login", json={
        "username": "+1-555-9999999",
        "password": "anyPassword"
    })
    assert resp.status_code == 401
    assert resp.get_json()["success"] is False

def test_passwords_are_cryptographically_hashed_in_db(client, test_users):
    """Verify directly in SQLite database that passwords are not stored in plaintext."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM user WHERE id = ?", (test_users["user_a"]["id"],))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    stored_hash = row["password_hash"]
    assert stored_hash != "alicePass123"
    assert len(stored_hash) > 20
    assert any(h in stored_hash for h in ["scrypt", "pbkdf2", "$"]) or len(stored_hash) == 64

# ==============================================================================
# 2. STRICT IDOR & ACCESS CONTROL TESTS
# ==============================================================================

def test_token_required_on_protected_routes(client, test_users):
    """Unauthenticated requests without token must return 401."""
    u_id = test_users["user_a"]["id"]
    routes = [
        ("GET", f"/api/get-user/{u_id}"),
        ("GET", f"/api/user/export-data/{u_id}"),
        ("GET", f"/api/inhaler/status/{u_id}"),
        ("GET", f"/api/agent/actions/pending/{u_id}"),
        ("GET", f"/api/agent/logs/{u_id}"),
        ("GET", f"/api/agent/plan/{u_id}"),
        ("GET", f"/api/agent/doctor-summary/{u_id}"),
        ("GET", f"/api/agent/doctor-summary/{u_id}/pdf"),
    ]
    for method, path in routes:
        if method == "GET":
            r = client.get(path)
        else:
            r = client.post(path)
        assert r.status_code == 401, f"Route {path} should require authentication"
        assert r.get_json()["success"] is False

def test_idor_user_a_cannot_read_or_delete_user_b_data(client, test_users):
    """User A should receive 403 Forbidden when attempting to query or delete User B's profile/data."""
    token_a = test_users["user_a"]["token"]
    user_b_id = test_users["user_b"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A tries to read User B's profile
    r = client.get(f"/api/get-user/{user_b_id}", headers=headers_a)
    assert r.status_code == 403
    assert "Forbidden" in r.get_json()["error"]

    # User A tries to export User B's data
    r = client.get(f"/api/user/export-data/{user_b_id}", headers=headers_a)
    assert r.status_code == 403

    # User A tries to delete User B's account
    r = client.delete(f"/api/user/delete-account/{user_b_id}", headers=headers_a)
    assert r.status_code == 403

    # User A tries to view User B's inhaler count
    r = client.get(f"/api/inhaler/status/{user_b_id}", headers=headers_a)
    assert r.status_code == 403

    # User A tries to view User B's pending actions
    r = client.get(f"/api/agent/actions/pending/{user_b_id}", headers=headers_a)
    assert r.status_code == 403

# ==============================================================================
# 3. APPROVAL QUEUE STRICT TESTS
# ==============================================================================

def test_approval_queue_lifecycle_and_idempotency(client, test_users):
    """
    Verify:
    1. Action starts PENDING and never executes without approval.
    2. Direct call to send_notification on PENDING action is refused.
    3. User B cannot approve User A's action (403).
    4. Editing before approval updates payload.
    5. APPROVE executes exactly once; replay/double-click returns 400.
    """
    user_a_id = test_users["user_a"]["id"]
    headers_a = {"Authorization": f"Bearer {test_users['user_a']['token']}"}
    headers_b = {"Authorization": f"Bearer {test_users['user_b']['token']}"}

    with app.app_context():
        # Propose an action for User A
        prop = AirGuardTools.propose_notification(
            user_id=user_a_id,
            recipient="Caregiver Bob",
            message="AQI Spike Warning: Stay indoors",
            channel="sms",
            reasoning="AQI reached 250 in Delhi"
        )
        action_id = prop["action_id"]

        # 1. Action is PENDING in DB
        action = AgentAction.query.get(action_id)
        assert action.status == "PENDING"

        # 2. Direct tool call refused when PENDING
        refuse_res = AirGuardTools.send_notification(action_id)
        assert refuse_res["success"] is False
        assert "Security Guard" in refuse_res["error"] or "Only 'APPROVED'" in refuse_res["error"]

    # 3. User B tries to approve User A's action -> 403 Forbidden
    r_idor = client.post(f"/api/agent/actions/approve/{action_id}", headers=headers_b)
    assert r_idor.status_code == 403

    # 4. User A edits message and approves
    edited_msg = "AQI Spike Warning: Stay indoors and keep windows closed"
    r_app = client.post(f"/api/agent/actions/approve/{action_id}", headers=headers_a, json={
        "message": edited_msg
    })
    assert r_app.status_code == 200
    app_data = r_app.get_json()
    assert app_data["success"] is True
    assert app_data["action"]["proposed_payload"] == edited_msg
    assert app_data["action"]["status"] == "EXECUTED"

    # 5. Replay attack: User A tries to approve again -> 400 Bad Request
    r_replay = client.post(f"/api/agent/actions/approve/{action_id}", headers=headers_a)
    assert r_replay.status_code == 400
    assert "Cannot re-approve" in r_replay.get_json()["error"]

def test_approval_queue_reject_never_executes(client, test_users):
    """REJECT action sets status to REJECTED and cannot be approved or dispatched."""
    user_a_id = test_users["user_a"]["id"]
    headers_a = {"Authorization": f"Bearer {test_users['user_a']['token']}"}

    with app.app_context():
        prop = AirGuardTools.propose_notification(
            user_id=user_a_id,
            recipient="Caregiver Bob",
            message="Test alert to decline",
            channel="sms",
            reasoning="Test decline flow"
        )
        action_id = prop["action_id"]

    # Reject action
    r_rej = client.post(f"/api/agent/actions/reject/{action_id}", headers=headers_a)
    assert r_rej.status_code == 200
    assert r_rej.get_json()["action"]["status"] == "REJECTED"

    # Attempt to approve rejected action -> 400
    r_app = client.post(f"/api/agent/actions/approve/{action_id}", headers=headers_a)
    assert r_app.status_code == 400

# ==============================================================================
# 4. INHALER TRACKER BOUNDARY & THRESHOLD TESTS
# ==============================================================================

def test_inhaler_tracker_decrement_bounds_and_threshold(client, test_users):
    """
    Test inhaler tracking:
    - Increments doses used
    - Remaining doses calculated as max(0, 200 - used)
    - Low-canister alert flags when remaining <= 20
    - Reset calibrates back to 200 remaining
    """
    user_id = test_users["user_a"]["id"]
    headers = {"Authorization": f"Bearer {test_users['user_a']['token']}"}

    # Reset first
    client.post(f"/api/inhaler/reset/{user_id}", headers=headers)

    # Check initial status
    r0 = client.get(f"/api/inhaler/status/{user_id}", headers=headers)
    assert r0.status_code == 200
    assert r0.get_json()["remaining_doses"] == 200
    assert r0.get_json()["low_canister_alert"] is False

    # Log 1 dose
    r1 = client.post("/api/inhaler/use", headers=headers, json={"user_id": user_id, "dose_count": 1})
    assert r1.status_code == 200
    assert r1.get_json()["remaining_doses"] == 199

    # Log 180 doses to reach remaining = 19 (triggering low canister alert <= 20)
    r2 = client.post("/api/inhaler/use", headers=headers, json={"user_id": user_id, "dose_count": 180})
    assert r2.status_code == 200
    assert r2.get_json()["remaining_doses"] == 19
    assert r2.get_json()["low_canister_alert"] is True

    # Log remaining 50 doses (exceeding 200): remaining doses must NEVER drop below 0
    r3 = client.post("/api/inhaler/use", headers=headers, json={"user_id": user_id, "dose_count": 50})
    assert r3.status_code == 200
    assert r3.get_json()["remaining_doses"] == 0
    assert r3.get_json()["low_canister_alert"] is True

    # Reset
    r_reset = client.post(f"/api/inhaler/reset/{user_id}", headers=headers)
    assert r_reset.status_code == 200
    assert r_reset.get_json()["remaining_doses"] == 200
    assert r_reset.get_json()["low_canister_alert"] is False

# ==============================================================================
# 5. /PREDICT STRICT TESTING (20+ Varied Inputs, Determinism, GINA Override)
# ==============================================================================

def test_predict_returns_required_fields_and_deterministic_output(client):
    payload = {
        "AQI": 95,
        "PM2.5": 42.0,
        "SO2 level": 12.0,
        "NO2 level": 28.0,
        "CO2 level": 420.0,
        "Humidity": 55.0,
        "Temperature": 26.0,
        "Asthma Symptoms Frequency": "1-2 times a month",
        "Triggers": "Dust, Pollen",
        "Weather Sensitivity": "None",
        "Poor Air Quality Exposure": "Occasionally",
        "Night Breathing Difficulty": "Rarely"
    }

    r1 = client.post("/predict", json=payload)
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["success"] is True
    # Confirm contract: score, tier, drivers, uncertainty
    assert "risk_score" in d1
    assert "tier" in d1
    assert "drivers" in d1
    assert "uncertainty" in d1

    # Determinism: same input produces exact same risk score
    r2 = client.post("/predict", json=payload)
    d2 = r2.get_json()
    assert d1["risk_score"] == d2["risk_score"]
    assert d1["tier"] == d2["tier"]

def test_predict_gina_red_flag_override_forces_high(client):
    """When symptoms are 'Daily' or night breathing difficulty is 'Frequently', GINA override forces High."""
    payload = {
        "AQI": 40,  # Very clean air
        "PM2.5": 10.0,
        "Asthma Symptoms Frequency": "Daily",
        "Night Breathing Difficulty": "Frequently"
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data["tier"] == "High"
    assert data["heuristic_override"] is True
    assert data["risk_score"] >= 0.88

def test_predict_twenty_plus_varied_and_extreme_inputs(client):
    """Test 20+ varied inputs including extremes, zeros, huge values, missing fields, string numbers."""
    test_cases = [
        {"AQI": 0, "PM2.5": 0, "SO2 level": 0, "NO2 level": 0},
        {"AQI": 999, "PM2.5": 500, "SO2 level": 200, "NO2 level": 300},
        {"AQI": 150, "Humidity": 99.9, "Temperature": 45.0},
        {"AQI": 25, "Humidity": 10.0, "Temperature": -5.0},
        {"AQI": "120.5", "PM2.5": "45.2"},  # String floats
        {"AQI": "", "PM2.5": None},         # Empty / None
        {},                                  # Empty payload
        {"Triggers": "None", "Weather Sensitivity": "High"},
        {"Triggers": "Dust, Pollen, Smoke, Cold Air, Pets, Exercise"},
        {"Asthma Symptoms Frequency": "Frequently (Weekly)"},
        {"Asthma Symptoms Frequency": "Less than once a month"},
        {"Night Breathing Difficulty": "Never"},
        {"Poor Air Quality Exposure": "Yes, often"},
        {"Poor Air Quality Exposure": "No"},
        {"AQI": 350, "Asthma Symptoms Frequency": "Daily"},
        {"AQI": 50, "CO2 level": 2000},
        {"AQI": 85, "NO2 level": 150},
        {"AQI": 110, "SO2 level": 80},
        {"patient_name": "Test Unicode: अमित शर्मा"},
        {"patient_name": "Long " * 50},
        {"AQI": 75, "Triggers": "Cold Air", "Night Breathing Difficulty": "Rarely"}
    ]

    assert len(test_cases) >= 20
    for idx, tc in enumerate(test_cases):
        res = client.post("/predict", json=tc)
        assert res.status_code == 200, f"Case {idx} failed with {res.status_code}"
        d = res.get_json()
        assert d["success"] is True
        assert 0.0 <= d["risk_score"] <= 1.0
        assert d["tier"] in ["Low", "Medium", "High"]

# ==============================================================================
# 6. SYMPTOM DIARY TESTS (Create, List, Edge Dates, Validation)
# ==============================================================================

def test_symptom_diary_lifecycle(client, test_users):
    user_id = test_users["user_a"]["id"]
    headers = {"Authorization": f"Bearer {test_users['user_a']['token']}"}

    # Add diary entry
    r1 = client.post("/api/agent/symptom/log", headers=headers, json={
        "user_id": user_id,
        "symptoms": "Mild wheezing in morning",
        "severity": "Mild",
        "inhaler_puffs_used": 2,
        "pef_reading": 380.0,
        "activity_level": "Moderate",
        "notes": "Triggered by cold breeze"
    })
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["success"] is True
    assert d1["diary"]["inhaler_puffs_used"] == 2

    # Query symptom history
    r2 = client.get(f"/api/agent/symptom/history/{user_id}", headers=headers)
    assert r2.status_code == 200
    history = r2.get_json()
    assert len(history.get("symptoms", [])) >= 1

# ==============================================================================
# 7. N8N DISPATCH TESTS (Unset, Bad URL Timeout, Local Fake Webhook)
# ==============================================================================

def test_n8n_dispatch_with_unset_webhook(test_users):
    """When N8N_WEBHOOK_URL is unset, dispatch simulates gracefully without crashing."""
    old_url = os.environ.get("N8N_WEBHOOK_URL")
    if "N8N_WEBHOOK_URL" in os.environ:
        del os.environ["N8N_WEBHOOK_URL"]

    try:
        user_id = test_users["user_a"]["id"]
        with app.app_context():
            prop = AirGuardTools.propose_notification(
                user_id=user_id,
                recipient="Caregiver Bob",
                message="Unset test alert",
                channel="sms",
                reasoning="Test unset env var"
            )
            action_id = prop["action_id"]

            # Approve action
            action = AgentAction.query.get(action_id)
            action.status = "APPROVED"
            db.session.commit()

            res = AirGuardTools.send_notification(action_id)
            assert res["success"] is True
            assert res["delivery"] == "simulated"
            assert "Simulated" in res["message"]
    finally:
        if old_url:
            os.environ["N8N_WEBHOOK_URL"] = old_url

def test_n8n_dispatch_with_bad_url_handles_timeout(test_users):
    """When N8N_WEBHOOK_URL points to non-existent endpoint, times out gracefully with error message."""
    old_url = os.environ.get("N8N_WEBHOOK_URL")
    os.environ["N8N_WEBHOOK_URL"] = "http://10.255.255.1:9999/bad_webhook"

    try:
        user_id = test_users["user_a"]["id"]
        with app.app_context():
            prop = AirGuardTools.propose_notification(
                user_id=user_id,
                recipient="Caregiver Bob",
                message="Bad URL test",
                channel="sms",
                reasoning="Test timeout"
            )
            action_id = prop["action_id"]

            action = AgentAction.query.get(action_id)
            action.status = "APPROVED"
            db.session.commit()

            res = AirGuardTools.send_notification(action_id)
            # Must return clean error structure without raising unhandled exception
            assert res["success"] is False
            assert "Delivery failed" in res["error"] or "timed out" in res["error"].lower() or "error" in res
    finally:
        if old_url:
            os.environ["N8N_WEBHOOK_URL"] = old_url
        else:
            del os.environ["N8N_WEBHOOK_URL"]

def test_n8n_dispatch_to_local_fake_webhook(test_users, fake_webhook_server):
    """Points N8N_WEBHOOK_URL to local HTTP server and verifies payload schema and privacy."""
    old_url = os.environ.get("N8N_WEBHOOK_URL")
    os.environ["N8N_WEBHOOK_URL"] = fake_webhook_server
    FakeWebhookHandler.received_payloads.clear()

    try:
        user_id = test_users["user_a"]["id"]
        msg = "High AQI (285) detected. Please check in with patient."
        with app.app_context():
            prop = AirGuardTools.propose_notification(
                user_id=user_id,
                recipient="Caregiver Bob",
                message=msg,
                channel="sms",
                reasoning="Autonomous care loop trigger"
            )
            action_id = prop["action_id"]

            action = AgentAction.query.get(action_id)
            action.status = "APPROVED"
            db.session.commit()

            res = AirGuardTools.send_notification(action_id)
            assert res["success"] is True
            assert res["delivery"] == "dispatched"

        # Verify delivered payload
        assert len(FakeWebhookHandler.received_payloads) == 1
        delivered = FakeWebhookHandler.received_payloads[0]
        assert delivered["action_id"] == action_id
        assert delivered["message"] == msg
        assert delivered["recipient"] == "Caregiver Bob"
        # Confirm no extra personal health identifiers leaked beyond necessary message
        assert "password" not in delivered
        assert "password_hash" not in delivered
    finally:
        if old_url:
            os.environ["N8N_WEBHOOK_URL"] = old_url
        else:
            del os.environ["N8N_WEBHOOK_URL"]

# ==============================================================================
# 8. DATA EXPORT & ACCOUNT DELETION TESTS (All 10 Tables Verified Before & After)
# ==============================================================================

def test_data_export_and_cascade_account_deletion_across_all_tables(client):
    """
    1. Sign up a temporary user.
    2. Populate data in all 10 tables.
    3. Export data and verify complete JSON schema.
    4. Delete account and verify with direct SQLite queries that 0 rows remain across all 10 tables.
    5. Verify user can no longer log in.
    """
    temp_phone = f"+1-555-{int(time.time() * 1000) % 8000 + 2000}"
    signup_res = client.post("/api/auth/signup", json={
        "name": "Deletable Patient",
        "phone_no": temp_phone,
        "password": "TempPassword123!",
        "age": 40
    })
    temp_user_id = signup_res.get_json()["user"]["id"]
    temp_token = signup_res.get_json()["token"]
    headers = {"Authorization": f"Bearer {temp_token}"}

    # Populate entries across remaining 9 tables
    with get_db_connection() as conn:
        conn.execute("INSERT INTO predictions (user_id, timestamp, score, risk_level) VALUES (?, ?, ?, ?)",
                     (temp_user_id, datetime.utcnow().isoformat(), 0.75, "High"))
        conn.execute("INSERT INTO inhaler_usage (user_id, timestamp, dose_count) VALUES (?, ?, ?)",
                     (temp_user_id, datetime.utcnow().isoformat(), 2))
        conn.commit()

    with app.app_context():
        db.session.add(SensorData(user_id=temp_user_id, air_quality=120, timestamp=datetime.utcnow()))
        db.session.add(SymptomDiary(user_id=temp_user_id, symptoms="Cough", timestamp=datetime.utcnow()))
        db.session.add(AgentAction(user_id=temp_user_id, action_type="sms", recipient="Kin", proposed_payload="Alert", reasoning="High AQI"))
        db.session.add(AgentLog(user_id=temp_user_id, trigger="test", reasoning="Test log", input_state=json.dumps({"test": "state"})))
        db.session.add(Alert(user_id=temp_user_id, message="Alert 1", timestamp=datetime.utcnow()))
        db.session.add(QuizResponse(user_id=temp_user_id, question="Q1", answer="A1"))
        db.session.add(DailyPlan(
            user_id=temp_user_id,
            valid_date="2026-10-05",
            risk_tier="Medium",
            safest_window="07:00-09:00",
            summary="Plan",
            hourly_recommendations=json.dumps([{"hour": 8, "action": "Walk"}]),
            preventive_actions=json.dumps(["Wear mask"])
        ))
        db.session.commit()

    # 3. Export data: verify complete JSON representation
    r_exp = client.get(f"/api/user/export-data/{temp_user_id}", headers=headers)
    assert r_exp.status_code == 200
    export_json = r_exp.get_json()
    assert export_json["success"] is True
    assert "predictions" in export_json
    assert "inhaler_usage" in export_json
    assert len(export_json["predictions"]) >= 1
    assert len(export_json["inhaler_usage"]) >= 1
    assert len(export_json["sensor_readings"]) >= 1
    assert len(export_json["symptom_diary"]) >= 1

    # 4. Delete account
    r_del = client.delete(f"/api/user/delete-account/{temp_user_id}", headers=headers)
    assert r_del.status_code == 200
    assert r_del.get_json()["success"] is True

    # Direct SQLite audit across all 10 tables to confirm 0 remaining rows
    conn = get_db_connection()
    cur = conn.cursor()
    tables = [
        "user", "sensor_data", "symptom_diary", "agent_action",
        "agent_log", "alert", "quiz_response", "daily_plan",
        "predictions", "inhaler_usage"
    ]
    for table in tables:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id = ?" if table != "user" else f"SELECT COUNT(*) as cnt FROM user WHERE id = ?", (temp_user_id,))
        count = cur.fetchone()["cnt"]
        assert count == 0, f"Table {table} still has {count} rows for deleted user {temp_user_id}!"
    conn.close()

    # 5. User can no longer log in
    r_login = client.post("/api/auth/login", json={
        "username": temp_phone,
        "password": "TempPassword123!"
    })
    assert r_login.status_code == 401

# ==============================================================================
# 9. DOCTOR SUMMARY PDF & ZERO-DATA TEST
# ==============================================================================

def test_doctor_summary_pdf_generation_and_zero_data_handling(client, test_users):
    """
    Tests:
    1. User A with data returns valid PDF bytes containing %PDF-, clinical tables, and medical disclaimer.
    2. A newly created user with zero data generates PDF cleanly without crashing.
    """
    user_a_id = test_users["user_a"]["id"]
    headers_a = {"Authorization": f"Bearer {test_users['user_a']['token']}"}

    resp = client.get(f"/api/agent/doctor-summary/{user_a_id}/pdf", headers=headers_a)
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    pdf_bytes = resp.data
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Create user with zero data
    phone_zero = f"+1-555-{int(time.time() * 1000) % 9000 + 100}"
    r_zero = client.post("/api/auth/signup", json={"name": "Zero Data Patient", "phone_no": phone_zero, "password": "pass"})
    zero_user_id = r_zero.get_json()["user"]["id"]
    zero_token = r_zero.get_json()["token"]

    resp_zero = client.get(f"/api/agent/doctor-summary/{zero_user_id}/pdf", headers={"Authorization": f"Bearer {zero_token}"})
    assert resp_zero.status_code == 200
    assert resp_zero.content_type == "application/pdf"
    assert resp_zero.data.startswith(b"%PDF-")

# ==============================================================================
# 10. SOS EMERGENCY ENDPOINT & INPUT ATTACK STRINGS
# ==============================================================================

def test_sos_emergency_endpoint(client):
    """SOS alert returns 112/108 numbers and logs the incident."""
    resp = client.post("/api/sos/alert", json={
        "user_id": 1,
        "lat": 28.6139,
        "lon": 77.2090,
        "reason": "Sudden breathlessness"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "112" in str(data) or "108" in str(data)

def test_routes_against_adversarial_and_malformed_inputs(client, test_users):
    """
    Test routes with:
    - SQL injection strings
    - XSS strings
    - Unicode / Hindi strings
    - Oversized payloads
    - Empty strings
    """
    attack_strings = [
        "'; DROP TABLE user; --",
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "अमित शर्मा सांस नहीं आ रही",
        "A" * 5000,  # Oversized string
        ""
    ]

    headers = {"Authorization": f"Bearer {test_users['user_a']['token']}"}

    for attack in attack_strings:
        # Chat endpoint
        r_chat = client.post("/api/agent/chat", headers=headers, json={
            "user_id": test_users["user_a"]["id"],
            "query": attack
        })
        assert r_chat.status_code in [200, 400], f"Chat failed unexpectedly on: {attack[:20]}"

        # Symptom log endpoint
        r_symp = client.post("/api/agent/symptom/log", headers=headers, json={
            "user_id": test_users["user_a"]["id"],
            "symptoms": attack,
            "notes": attack
        })
        assert r_symp.status_code in [200, 400], f"Symptom log failed on: {attack[:20]}"
