from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False, default=30)
    gender = db.Column(db.String(10), nullable=False, default='Other')
    phone_no = db.Column(db.String(25), unique=True, nullable=False)
    medical_history = db.Column(db.Text, nullable=True)

    # Authentication & Security
    password_hash = db.Column(db.String(256), nullable=True, default='')

    # Clinical & Asthmatic Profile
    baseline_severity = db.Column(db.String(50), nullable=False, default='Mild Intermittent')
    inhaler_prescribed = db.Column(db.String(200), nullable=False, default='Albuterol (Reliever) 2 puffs PRN, Budesonide/Formoterol 1 puff BID')
    triggers = db.Column(db.String(255), nullable=False, default='Dust, Pollen, Cold Air, Air Pollution')
    language_pref = db.Column(db.String(10), nullable=False, default='en')  # 'en' or 'hi'

    # Geolocation for Live Weather / Forecast
    city = db.Column(db.String(100), nullable=False, default='Delhi')
    lat = db.Column(db.Float, nullable=False, default=28.6139)
    lon = db.Column(db.Float, nullable=False, default=77.2090)

    # Emergency Contact
    emergency_contact_name = db.Column(db.String(100), nullable=False, default='Emergency Contact')
    emergency_contact_phone = db.Column(db.String(25), nullable=False, default='+1-555-0188')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return True  # Backward compatibility for demo accounts without password
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'full_name': self.name,
            'age': self.age,
            'gender': self.gender,
            'phone_no': self.phone_no,
            'medical_history': self.medical_history,
            'baseline_severity': self.baseline_severity,
            'inhaler_prescribed': self.inhaler_prescribed,
            'triggers': self.triggers,
            'language_pref': self.language_pref,
            'city': self.city,
            'lat': self.lat,
            'lon': self.lon,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone
        }

class SensorData(db.Model):
    __tablename__ = 'sensor_data'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    air_quality = db.Column(db.Integer, nullable=False)  # AQI
    pm25 = db.Column(db.Float, nullable=False)  # PM2.5
    so2_level = db.Column(db.Float, nullable=False)  # SO2 level
    no2_level = db.Column(db.Float, nullable=False)  # NO2 level
    co2_level = db.Column(db.Float, nullable=False)  # CO2 level
    humidity = db.Column(db.Float, nullable=False)  # Humidity
    temperature = db.Column(db.Float, nullable=False)  # Temperature

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            'air_quality': self.air_quality,
            'AQI': self.air_quality,
            'pm25': self.pm25,
            'PM2.5': self.pm25,
            'so2_level': self.so2_level,
            'no2_level': self.no2_level,
            'co2_level': self.co2_level,
            'humidity': self.humidity,
            'temperature': self.temperature
        }

class Alert(db.Model):
    __tablename__ = 'alert'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp)
        }

class QuizResponse(db.Model):
    __tablename__ = 'quiz_response'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question': self.question,
            'answer': self.answer
        }

class SymptomDiary(db.Model):
    __tablename__ = 'symptom_diary'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    symptoms = db.Column(db.Text, nullable=False)  # JSON or comma-separated symptoms (e.g. Wheezing, Cough)
    severity = db.Column(db.String(20), nullable=False, default='Mild')  # None, Mild, Moderate, Severe
    inhaler_puffs_used = db.Column(db.Integer, nullable=False, default=0)
    pef_reading = db.Column(db.Float, nullable=True)  # Peak Expiratory Flow in L/min
    activity_level = db.Column(db.String(50), nullable=False, default='Rest')  # Rest, Light Walk, Exercise
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            'symptoms': self.symptoms,
            'severity': self.severity,
            'inhaler_puffs_used': self.inhaler_puffs_used,
            'pef_reading': self.pef_reading,
            'activity_level': self.activity_level,
            'notes': self.notes
        }

class AgentAction(db.Model):
    """
    Human-in-the-loop approval queue for agent actions.
    No action with external impact (SMS, calendar, purifier, etc.) is taken without user consent.
    """
    __tablename__ = 'agent_action'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    action_type = db.Column(db.String(50), nullable=False)  # 'caregiver_alert', 'routine_reschedule', 'calendar_reminder', 'purifier_toggle'
    recipient = db.Column(db.String(100), nullable=False)  # Contact name / phone / device ID
    channel = db.Column(db.String(50), nullable=False, default='sms')  # 'sms', 'whatsapp', 'push', 'webhook'
    proposed_payload = db.Column(db.Text, nullable=False)  # Exact preview text or JSON
    reasoning = db.Column(db.Text, nullable=False)  # Why the agent recommends this action
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # 'PENDING', 'APPROVED', 'REJECTED', 'EXECUTED', 'FAILED'
    decided_at = db.Column(db.DateTime, nullable=True)
    execution_result = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else str(self.created_at),
            'action_type': self.action_type,
            'recipient': self.recipient,
            'channel': self.channel,
            'proposed_payload': self.proposed_payload,
            'reasoning': self.reasoning,
            'status': self.status,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'execution_result': self.execution_result
        }

class AgentLog(db.Model):
    """
    Complete audit trail of agent reasoning, inputs, outputs, and safety rail status.
    """
    __tablename__ = 'agent_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    trigger = db.Column(db.String(50), nullable=False)  # 'forecast_update', 'symptom_diary', 'chat_query', 'manual_run'
    input_state = db.Column(db.Text, nullable=False)  # JSON snapshot of AQI, risk tier, symptoms
    reasoning = db.Column(db.Text, nullable=False)  # Agent clinical reasoning chain
    actions_proposed = db.Column(db.Text, nullable=True)  # JSON list of action summaries
    guardrail_tripped = db.Column(db.Boolean, nullable=False, default=False)
    guardrail_details = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            'trigger': self.trigger,
            'input_state': json.loads(self.input_state) if self.input_state.startswith('{') else self.input_state,
            'reasoning': self.reasoning,
            'actions_proposed': json.loads(self.actions_proposed) if self.actions_proposed and self.actions_proposed.startswith('[') else self.actions_proposed,
            'guardrail_tripped': self.guardrail_tripped,
            'guardrail_details': self.guardrail_details
        }

class DailyPlan(db.Model):
    """
    AirGuard 24-hour proactive asthma protection plan.
    """
    __tablename__ = 'daily_plan'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    valid_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    risk_tier = db.Column(db.String(20), nullable=False)  # 'Low', 'Medium', 'High', 'Emergency'
    safest_window = db.Column(db.String(100), nullable=False)  # e.g. "06:00 - 08:30"
    summary = db.Column(db.Text, nullable=False)
    hourly_recommendations = db.Column(db.Text, nullable=False)  # JSON array
    preventive_actions = db.Column(db.Text, nullable=False)  # JSON array

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'generated_at': self.generated_at.isoformat() if hasattr(self.generated_at, 'isoformat') else str(self.generated_at),
            'valid_date': self.valid_date,
            'risk_tier': self.risk_tier,
            'safest_window': self.safest_window,
            'summary': self.summary,
            'hourly_recommendations': json.loads(self.hourly_recommendations) if self.hourly_recommendations.startswith('[') else [],
            'preventive_actions': json.loads(self.preventive_actions) if self.preventive_actions.startswith('[') else []
        }
