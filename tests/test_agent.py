"""
AirGuard Agent Core Integration & Tool Tests.
Tests environmental forecast parsing, safest window algorithm, approval queue guards,
doctor consultation report generation, and the end-to-end agent cycle.
"""

import pytest
from flask import Flask
from datetime import datetime

from models import db, User, SensorData, SymptomDiary, AgentAction, AgentLog, DailyPlan, Alert
from agent.tools import AirGuardTools
from agent.llm import AirGuardLLM
from agent.loop import AirGuardAgentLoop

@pytest.fixture
def app_ctx():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Seed test user
        user = User(
            name="Alex Rivera",
            age=28,
            gender="Male",
            phone_no="+1-555-0143",
            baseline_severity="Moderate Persistent",
            inhaler_prescribed="Albuterol 2 puffs PRN, Budesonide 1 puff BID",
            triggers="Dust, Cold air, Pollen",
            language_pref="en",
            city="Delhi",
            lat=28.6139,
            lon=77.2090,
            emergency_contact_name="Maria Rivera",
            emergency_contact_phone="+1-555-0188"
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        yield app

def test_password_hashing(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        assert user.check_password("SecurePass123!") is True
        assert user.check_password("WrongPassword") is False
        assert user.password_hash != "SecurePass123!"

def test_air_quality_forecast_structure():
    forecast = AirGuardTools.get_air_quality_forecast(lat=28.6139, lon=77.2090, hours=24)
    assert forecast["success"] is True
    assert "safest_window" in forecast
    assert len(forecast["hourly"]) >= 24
    sample = forecast["hourly"][0]
    assert "aqi" in sample
    assert "pm25" in sample
    assert "temperature" in sample
    assert "humidity" in sample

def test_safest_window_computation():
    hourly = [
        {"hour": f"{h:02d}:00", "aqi": 180 if h not in [7, 8] else 45}
        for h in range(24)
    ]
    window = AirGuardTools._compute_safest_window(hourly)
    assert "07:00" in window or "08:00" in window

def test_propose_notification_stores_pending(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        res = AirGuardTools.propose_notification(
            user_id=user.id,
            recipient="Maria Rivera (+1-555-0188)",
            message="Delhi air quality is poor today. Alex's asthma risk is High.",
            channel="sms",
            reasoning="High AQI forecast (AQI 190)"
        )
        assert res["success"] is True
        assert res["status"] == "PENDING"
        action = AgentAction.query.get(res["action_id"])
        assert action.status == "PENDING"

def test_send_notification_guard_blocks_unapproved(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        res = AirGuardTools.propose_notification(
            user_id=user.id,
            recipient="Maria Rivera",
            message="Alert",
            channel="sms"
        )
        action_id = res["action_id"]

        # Attempt to dispatch while status is PENDING
        dispatch = AirGuardTools.send_notification(action_id)
        assert dispatch["success"] is False
        assert "Security Guard" in dispatch["error"]
        assert AgentAction.query.get(action_id).status == "PENDING"

def test_send_notification_dispatches_when_approved(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        res = AirGuardTools.propose_notification(
            user_id=user.id,
            recipient="Maria Rivera",
            message="Alert",
            channel="sms"
        )
        action_id = res["action_id"]

        # User explicitly approves action
        action = AgentAction.query.get(action_id)
        action.status = "APPROVED"
        db.session.commit()

        dispatch = AirGuardTools.send_notification(action_id)
        assert dispatch["success"] is True
        assert dispatch["status"] == "EXECUTED"
        assert AgentAction.query.get(action_id).status == "EXECUTED"

def test_doctor_summary_generation(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        # Log several symptoms and puffs
        AirGuardTools.log_symptom(user.id, "Mild wheezing in morning", severity="Mild", inhaler_puffs_used=2, pef_reading=380)
        AirGuardTools.log_symptom(user.id, "Cough after cold exposure", severity="Moderate", inhaler_puffs_used=4, pef_reading=320)

        summary = AirGuardTools.generate_doctor_summary(user.id)
        assert summary["success"] is True
        assert summary["total_episodes"] == 2
        assert summary["total_puffs"] == 6
        assert summary["pef_stats"]["min"] == 320
        assert summary["pef_stats"]["max"] == 380
        assert "AIRGUARD CLINICAL ASTHMA CONSULTATION SUMMARY" in summary["formatted_report"]
        assert "Alex Rivera" in summary["formatted_report"]

def test_agent_loop_cycle(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        loop = AirGuardAgentLoop()
        result = loop.run_cycle(user_id=user.id, trigger="manual_run", user_query="Can I go for an evening run?")

        assert result["success"] is True
        assert result["cycle_status"] == "COMPLETED"
        assert "safest_window" in result
        assert "agent_response" in result
        assert result["emergency"] is False

        # Verify audit log was created
        log_records = AgentLog.query.filter_by(user_id=user.id).all()
        assert len(log_records) >= 1
        assert "Evaluated multimodal ML ensemble" in log_records[0].reasoning

def test_agent_loop_emergency_red_flag_bypass(app_ctx):
    with app_ctx.app_context():
        user = User.query.first()
        loop = AirGuardAgentLoop()
        result = loop.run_cycle(
            user_id=user.id,
            trigger="user_chat",
            user_query="Help me, I am struggling to breathe and my blue lips are showing"
        )
        assert result["emergency"] is True
        assert result["risk_tier"] == "Emergency"
        assert result["guardrail_tripped"] is True
        assert "CRITICAL AIRWAY DISTRESS DETECTED" in result["response"]
