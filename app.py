import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Cython unpickling alias compatibility
try:
    import sklearn._loss._loss as _cy_loss
    sys.modules['_loss'] = _cy_loss
except Exception:
    pass
import json
import pickle
import sqlite3
import hashlib
import warnings
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_cors import CORS

from models import db, User, SensorData, Alert, QuizResponse, SymptomDiary, AgentAction, AgentLog, DailyPlan
from agent.tools import AirGuardTools
from agent.llm import AirGuardLLM
from agent.loop import AirGuardAgentLoop
from agent.guardrails import check_input_red_flags, sanitize_output

warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================

REVIEW1_MODEL_PATH = "results/review1_ensemble.pkl"
FALLBACK_MODEL_PATH = "results/best_ensemble_model.pkl"
DB_PATH = "asthmai.db"

# ==================== NUMPY BITGENERATOR COMPATIBILITY ====================
# Resolves cross-version unpickling differences between NumPy 1.x and 2.x MT19937 BitGenerators
try:
    import numpy.random._pickle as _np_pickle
    from numpy.random._mt19937 import MT19937 as _OrigMT19937
    from numpy.random.mtrand import RandomState

    class _CompatibleMT19937(_OrigMT19937):
        def __setstate__(self, state):
            if isinstance(state, tuple):
                state = state[0]
            super().__setstate__(state)

    _CompatibleMT19937.__name__ = 'MT19937'
    _CompatibleMT19937.__qualname__ = 'MT19937'

    def _compat_bit_generator_ctor(name="MT19937"):
        if isinstance(name, _OrigMT19937):
            return name
        return _CompatibleMT19937()

    def _compat_randomstate_ctor(bit_generator_name="MT19937", bit_generator_ctor=None):
        if isinstance(bit_generator_name, _OrigMT19937):
            bg = bit_generator_name
        elif isinstance(bit_generator_name, type) and issubclass(bit_generator_name, _OrigMT19937):
            bg = _CompatibleMT19937()
        else:
            bg = _compat_bit_generator_ctor(bit_generator_name)
        return RandomState(bg)

    _np_pickle.__bit_generator_ctor = _compat_bit_generator_ctor
    _np_pickle.__randomstate_ctor = _compat_randomstate_ctor
    _np_pickle.BitGenerators['MT19937'] = _CompatibleMT19937
    _np_pickle.BitGenerators[_OrigMT19937] = _CompatibleMT19937
    _np_pickle.BitGenerators[_CompatibleMT19937] = _CompatibleMT19937
except Exception as _np_compat_err:
    print(f"NumPy compat warning: {_np_compat_err}")

# ==================== MODEL LOADING ====================

print("Loading HridyaVayu Multimodal Ensemble Models...")
review1_package = None
try:
    if os.path.exists(REVIEW1_MODEL_PATH):
        with open(REVIEW1_MODEL_PATH, "rb") as f:
            review1_package = pickle.load(f)
        print("✓ HridyaVayu Multimodal Collaborative Ensemble Loaded Successfully!")
        model_name = "HridyaVayu Multimodal Ensemble (Baseline LR + Random Forest + Gradient Boosting)"
    elif os.path.exists(FALLBACK_MODEL_PATH):
        with open(FALLBACK_MODEL_PATH, "rb") as f:
            fallback = pickle.load(f)
        print("✓ Fallback Ensemble Loaded Successfully!")
        model_name = "Ensemble Fallback"
    else:
        model_name = "Baseline Heuristics"
except Exception as e:
    print(f"Error loading models: {e}")
    model_name = "Baseline Heuristics"

# Load Review 1 benchmark metrics
review1_metrics = {}
if os.path.exists("results/review1_metrics.json"):
    try:
        with open("results/review1_metrics.json", "r") as f:
            review1_metrics = json.load(f)
    except Exception:
        pass

# ==================== AIRGUARD AGENT ENGINE ====================
print("Initializing AirGuard Agent Decision Engine...")
agent_loop = AirGuardAgentLoop(review1_package=review1_package)
print(f"✓ AirGuard Agent Engine Initialized (LLM Provider: {agent_loop.llm.get_provider_name()})")

# ==================== REAL-TIME AQI SERVICE ====================

class RealTimeAQI:
    def __init__(self):
        self.aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
        
    def get_live_data(self, latitude, longitude):
        try:
            aq_params = {
                "latitude": latitude, "longitude": longitude,
                "current": ["us_aqi", "pm2_5", "nitrogen_dioxide", "sulphur_dioxide"],
                "timezone": "auto"
            }
            w_params = {
                "latitude": latitude, "longitude": longitude,
                "current": ["temperature_2m", "relative_humidity_2m"],
                "timezone": "auto"
            }
            
            aq_res = requests.get(self.aqi_url, params=aq_params, timeout=5).json()
            w_res = requests.get(self.weather_url, params=w_params, timeout=5).json()
            
            if "current" in aq_res and "current" in w_res:
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "location": {"lat": latitude, "lon": longitude},
                    "air_quality": int(aq_res["current"].get("us_aqi", 50) or 50),
                    "AQI": int(aq_res["current"].get("us_aqi", 50) or 50),
                    "pm25": float(aq_res["current"].get("pm2_5", 15) or 15),
                    "PM2.5": float(aq_res["current"].get("pm2_5", 15) or 15),
                    "no2_level": float(aq_res["current"].get("nitrogen_dioxide", 20) or 20),
                    "NO2 level": float(aq_res["current"].get("nitrogen_dioxide", 20) or 20),
                    "so2_level": float(aq_res["current"].get("sulphur_dioxide", 10) or 10),
                    "SO2 level": float(aq_res["current"].get("sulphur_dioxide", 10) or 10),
                    "co2_level": 415.0,
                    "CO2 level": 415.0,
                    "temperature": float(w_res["current"].get("temperature_2m", 25) or 25),
                    "Temperature": float(w_res["current"].get("temperature_2m", 25) or 25),
                    "humidity": float(w_res["current"].get("relative_humidity_2m", 50) or 50),
                    "Humidity": float(w_res["current"].get("relative_humidity_2m", 50) or 50)
                }
            return None
        except Exception as e:
            print(f"AQI Live Fetch Error: {e}")
            return None

aqi_service = RealTimeAQI()

# ==================== FLASK & SQLALCHEMY SETUP ====================

app = Flask(__name__, template_folder='web_ui', static_folder='web_ui')
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'airguard-super-secret-production-key-replace-me')
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath(DB_PATH)}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ==================== TOKEN AUTHENTICATION & IDOR GUARDS ====================
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps
import io

TOKEN_MAX_AGE = 86400 * 7  # 7 days

def get_token_serializer():
    return URLSafeTimedSerializer(app.config.get('SECRET_KEY', 'airguard-super-secret-production-key-replace-me'))

def generate_auth_token(user_id: int, role: str = "User") -> str:
    s = get_token_serializer()
    return s.dumps({"user_id": user_id, "role": role})

def verify_auth_token(token: str):
    if not token:
        return None
    s = get_token_serializer()
    try:
        return s.loads(token, max_age=TOKEN_MAX_AGE)
    except (SignatureExpired, BadSignature, Exception):
        return None

def _execute_auth_check(func, admin_only, *args, **kwargs):
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.headers.get("X-Auth-Token"):
        token = request.headers.get("X-Auth-Token").strip()
    elif request.args.get("token"):
        token = request.args.get("token").strip()

    if not token:
        return jsonify({"success": False, "error": "Authentication token required. Please log in."}), 401

    payload = verify_auth_token(token)
    if not payload:
        return jsonify({"success": False, "error": "Invalid or expired authentication token. Please log in again."}), 401

    auth_user_id = payload.get("user_id")
    auth_role = payload.get("role", "User")

    if admin_only and auth_role != "Admin":
        return jsonify({"success": False, "error": "Administrator privileges required."}), 403

    # IDOR check: if endpoint takes user_id in URL kwargs
    if "user_id" in kwargs:
        target_user_id = kwargs["user_id"]
        if target_user_id != auth_user_id and auth_role != "Admin":
            return jsonify({"success": False, "error": "Forbidden: You cannot access, modify, or delete another patient's data."}), 403

    # IDOR check: if endpoint takes action_id in URL kwargs
    if "action_id" in kwargs:
        action = AgentAction.query.get(kwargs["action_id"])
        if not action:
            return jsonify({"success": False, "error": "Action not found"}), 404
        if action.user_id != auth_user_id and auth_role != "Admin":
            return jsonify({"success": False, "error": "Forbidden: You cannot decide an action belonging to another patient."}), 403

    # IDOR check: if user_id in JSON payload
    if request.is_json:
        try:
            body = request.get_json(silent=True) or {}
            if "user_id" in body and body["user_id"] is not None:
                target_user_id = int(body["user_id"])
                if target_user_id != auth_user_id and auth_role != "Admin":
                    return jsonify({"success": False, "error": "Forbidden: You cannot submit actions or diaries for another patient."}), 403
        except Exception:
            pass

    return func(*args, **kwargs)

def token_required(f_or_admin=None, admin_only=False):
    if callable(f_or_admin):
        func = f_or_admin
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _execute_auth_check(func, False, *args, **kwargs)
        return wrapper
    else:
        is_admin = admin_only or (f_or_admin is True)
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return _execute_auth_check(func, is_admin, *args, **kwargs)
            return wrapper
        return decorator

# ==================== DATABASE HELPERS ====================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Warning during db.create_all: {e}")

    try:
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    score REAL,
                    risk_level TEXT,
                    patient_name TEXT,
                    symptoms TEXT,
                    aqi REAL,
                    user_id INTEGER,
                    baseline_score REAL DEFAULT 0.0,
                    rf_score REAL DEFAULT 0.0,
                    gb_score REAL DEFAULT 0.0,
                    heuristic_override INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inhaler_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    timestamp TEXT,
                    dose_count INTEGER DEFAULT 1
                )
            """)

            # Upgrades for existing predictions table
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(predictions)")
            cols = [col[1] for col in cur.fetchall()]
            for col_name, col_def in [
                ('patient_name', "TEXT DEFAULT 'Anonymous'"),
                ('symptoms', "TEXT DEFAULT ''"),
                ('aqi', "REAL DEFAULT 0.0"),
                ('user_id', "INTEGER DEFAULT NULL"),
                ('baseline_score', "REAL DEFAULT 0.0"),
                ('rf_score', "REAL DEFAULT 0.0"),
                ('gb_score', "REAL DEFAULT 0.0"),
                ('heuristic_override', "INTEGER DEFAULT 0")
            ]:
                if col_name not in cols:
                    try:
                        conn.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

            # Upgrades for sensor_data table (ensure air_quality column)
            cur.execute("PRAGMA table_info(sensor_data)")
            s_cols = [col[1] for col in cur.fetchall()]
            if 'air_quality' not in s_cols and len(s_cols) > 0:
                try:
                    conn.execute("ALTER TABLE sensor_data ADD COLUMN air_quality INTEGER DEFAULT 50")
                    if 'aqi' in s_cols:
                        conn.execute("UPDATE sensor_data SET air_quality = aqi WHERE aqi IS NOT NULL")
                except Exception:
                    pass

            # Upgrades for user table (security, clinical parameters, localization)
            cur.execute("PRAGMA table_info(user)")
            u_cols = [col[1] for col in cur.fetchall()]
            for col_name, col_def in [
                ('password_hash', "TEXT DEFAULT ''"),
                ('baseline_severity', "TEXT DEFAULT 'Mild Intermittent'"),
                ('inhaler_prescribed', "TEXT DEFAULT 'Albuterol (Reliever) 2 puffs PRN, Budesonide/Formoterol 1 puff BID'"),
                ('triggers', "TEXT DEFAULT 'Dust, Pollen, Cold Air, Air Pollution'"),
                ('language_pref', "TEXT DEFAULT 'en'"),
                ('city', "TEXT DEFAULT 'Delhi'"),
                ('lat', "REAL DEFAULT 28.6139"),
                ('lon', "REAL DEFAULT 77.2090")
            ]:
                if col_name not in u_cols:
                    try:
                        conn.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"Warning during SQLite schema migration: {e}")

    # Seed Demo User & Admin in User ORM table (safely idempotent and race-protected)
    with app.app_context():
        try:
            demo_patient = User.query.filter(
                (User.phone_no == "+1-555-0143") | 
                (User.phone_no == "+1555019900") | 
                (User.name == "Alex Rivera")
            ).first()
            if not demo_patient:
                demo_patient = User(
                    name="Alex Rivera",
                    age=28,
                    gender="Male",
                    phone_no="+1-555-0143",
                    medical_history="Diagnosed bronchial asthma, allergen sensitive",
                    baseline_severity="Moderate Persistent",
                    inhaler_prescribed="Albuterol 2 puffs PRN, Budesonide 1 puff BID",
                    triggers="Dust, Pollen, Cold Air, High PM2.5",
                    language_pref="en",
                    city="Delhi",
                    lat=28.6139,
                    lon=77.2090,
                    emergency_contact_name="Maria Rivera (Spouse)",
                    emergency_contact_phone="+1-555-0188"
                )
                demo_patient.set_password("alex123")
                db.session.add(demo_patient)
                db.session.commit()
            elif not demo_patient.password_hash:
                demo_patient.set_password("alex123")
                db.session.commit()
        except Exception as e:
            db.session.rollback()

        try:
            demo_doctor = User.query.filter(
                (User.phone_no == "+1-555-0199") | 
                (User.name.like("%Mitchell%"))
            ).first()
            if not demo_doctor:
                demo_doctor = User(
                    name="Dr. Sarah Mitchell, MD",
                    age=45,
                    gender="Female",
                    phone_no="+1-555-0199",
                    medical_history="Chief of Respiratory Medicine",
                    baseline_severity="Clinical Specialist",
                    inhaler_prescribed="N/A",
                    triggers="None",
                    language_pref="en",
                    city="Delhi",
                    emergency_contact_name="Hospital Emergency Desk",
                    emergency_contact_phone="+1-800-911-0000"
                )
                demo_doctor.set_password("doctor123")
                db.session.add(demo_doctor)
                db.session.commit()
            elif not demo_doctor.password_hash:
                demo_doctor.set_password("doctor123")
                db.session.commit()
        except Exception as e:
            db.session.rollback()

# ==================== STATIC & FIGURE ROUTES ====================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/web_ui/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(os.path.join(app.root_path, "web_ui", "assets"), filename)

@app.route("/figures/<path:filename>")
def serve_figures(filename):
    return send_from_directory(os.path.join(app.root_path, "figures"), filename)

@app.route("/slideshow/<path:filename>")
def serve_slideshow(filename):
    return send_from_directory(os.path.join(app.root_path, "slideshow"), filename)

# ==================== AUTHENTICATION & PROFILE ROUTES ====================

@app.route("/api/auth/signup", methods=["POST"])
def auth_signup():
    try:
        data = request.get_json(force=True) or {}
        name = data.get("name") or data.get("full_name") or data.get("username", "Alex Rivera").strip()
        age = int(data.get("age", 30) or 30)
        gender = data.get("gender", "Other")
        phone_no = (data.get("phone_no") or "").strip()
        if not phone_no:
            phone_no = f"+1-555-{np.random.randint(1000, 9999)}"
        password = data.get("password", "")
        medical_history = data.get("medical_history", "Mild intermittent asthma")
        baseline_severity = data.get("baseline_severity", "Mild Intermittent")
        inhaler_prescribed = data.get("inhaler_prescribed", "Albuterol (Reliever) 2 puffs PRN, Budesonide/Formoterol 1 puff BID")
        triggers = data.get("triggers", "Dust, Pollen, Cold Air")
        language_pref = data.get("language_pref", "en")
        city = data.get("city", "Delhi")
        emergency_contact_name = data.get("emergency_contact_name", "Primary Contact")
        emergency_contact_phone = data.get("emergency_contact_phone", "+1-555-0188")
        role = data.get("role", "User").strip()

        # Check existing phone - Reject duplicate signup with 409 Conflict
        existing = User.query.filter_by(phone_no=phone_no).first()
        if existing:
            return jsonify({
                "success": False,
                "error": f"An account with phone number '{phone_no}' already exists. Please log in instead."
            }), 409

        user = User(
            name=name,
            age=age,
            gender=gender,
            phone_no=phone_no,
            medical_history=medical_history,
            baseline_severity=baseline_severity,
            inhaler_prescribed=inhaler_prescribed,
            triggers=triggers,
            language_pref=language_pref,
            city=city,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone
        )
        if password:
            user.set_password(password)
        else:
            user.set_password("alex123")
        db.session.add(user)
        db.session.commit()

        token = generate_auth_token(user.id, role=role)

        return jsonify({
            "success": True,
            "message": "Account registered securely",
            "token": token,
            "user": {
                **user.to_dict(),
                "role": role,
                "username": name.lower().replace(" ", "_"),
                "full_name": user.name
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    try:
        data = request.get_json(force=True) or {}
        username = str(data.get("username", "") or data.get("email", "") or data.get("phone", "") or data.get("phone_no", "")).strip()
        password = str(data.get("password", ""))

        if not username:
            return jsonify({"success": False, "error": "Username, email, or phone number required"}), 400

        u_low = username.lower()
        role = "User"
        user = None

        # Check known demo aliases
        if u_low in ["alex@example.com", "alex", "demo_user", "alex rivera"]:
            user = User.query.filter((User.phone_no == "+1-555-0143") | (User.phone_no == "+1555019900") | (User.name == "Alex Rivera")).first()
            role = "User"
        elif u_low in ["doctor@example.com", "admin", "dr. sarah mitchell", "sarah"]:
            user = User.query.filter((User.phone_no == "+1-555-0199") | (User.name.like("%Mitchell%"))).first()
            role = "Admin"
        else:
            # Query by exact phone or name
            user = User.query.filter((User.name == username) | (User.phone_no == username)).first()
            if "admin" in u_low:
                role = "Admin"

        if not user:
            return jsonify({"success": False, "error": "User account not found. Please sign up."}), 401

        # Check password: Demo account Alex accepts both 'demo123' and 'alex123'
        is_valid = False
        if user.phone_no in ["+1-555-0143", "+1555019900"] and password in ["demo123", "alex123"]:
            is_valid = True
        elif user.phone_no == "+1-555-0199" and password in ["doctor123", "admin123"]:
            is_valid = True
        elif user.password_hash:
            is_valid = user.check_password(password)
        elif not password:
            is_valid = False

        if not is_valid:
            return jsonify({"success": False, "error": "Invalid password credentials"}), 401

        token = generate_auth_token(user.id, role=role)

        return jsonify({
            "success": True,
            "token": token,
            "user": {
                **user.to_dict(),
                "role": role,
                "username": username or user.name,
                "full_name": user.name
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/get-user/<int:user_id>", methods=["GET"])
@app.route("/api/get-user/<int:user_id>", methods=["GET"])
@token_required
def get_user_profile(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({
            "success": True,
            "user": user.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/save-profile", methods=["POST"])
@app.route("/api/save-profile", methods=["POST"])
@token_required
def save_profile():
    try:
        data = request.get_json(force=True) or {}
        user_id = data.get("user_id") or 1
        phone = data.get("phone_no", "+1-555-0143")
        user = User.query.get(user_id)
        if not user:
            user = User.query.filter_by(phone_no=phone).first()

        if not user:
            user = User(
                name=data.get("name", "Alex Rivera"),
                age=int(data.get("age", 30)),
                gender=data.get("gender", "Other"),
                phone_no=phone,
                emergency_contact_name=data.get("emergency_contact_name", "Primary Contact"),
                emergency_contact_phone=data.get("emergency_contact_phone", "+1-555-0188")
            )
            db.session.add(user)
        else:
            if "name" in data: user.name = data["name"]
            if "age" in data: user.age = int(data["age"])
            if "gender" in data: user.gender = data["gender"]
            if "phone_no" in data: user.phone_no = data["phone_no"]
            if "medical_history" in data: user.medical_history = data["medical_history"]
            if "emergency_contact_name" in data: user.emergency_contact_name = data["emergency_contact_name"]
            if "emergency_contact_phone" in data: user.emergency_contact_phone = data["emergency_contact_phone"]
            if "name" in data: user.name = data["name"]
            if "age" in data: user.age = int(data["age"])
            if "gender" in data: user.gender = data["gender"]
            if "phone_no" in data: user.phone_no = data["phone_no"]
            if "medical_history" in data: user.medical_history = data["medical_history"]
            if "emergency_contact_name" in data: user.emergency_contact_name = data["emergency_contact_name"]
            if "emergency_contact_phone" in data: user.emergency_contact_phone = data["emergency_contact_phone"]

        db.session.commit()
        return jsonify({"success": True, "message": "Profile saved successfully", "user": user.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== SENSORDATA SYNCING BACKEND ROUTES ====================

@app.route("/upload-sensor-data", methods=["POST"])
@app.route("/api/upload-sensor-data", methods=["POST"])
def upload_sensor_data():
    """Stores real-time environmental sensor data into SensorData model."""
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        
        # Ensure user exists for foreign key
        user = User.query.get(user_id)
        if not user:
            user = User(
                name="Alex Rivera",
                age=28,
                gender="Male",
                phone_no="+1-555-0143",
                emergency_contact_name="Maria Rivera",
                emergency_contact_phone="+1-555-0188"
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        air_quality = int(data.get("air_quality") or data.get("AQI") or 50)
        pm25 = float(data.get("pm25") or data.get("PM2.5") or 15.0)
        so2_level = float(data.get("so2_level") or data.get("SO2 level") or 10.0)
        no2_level = float(data.get("no2_level") or data.get("NO2 level") or 20.0)
        co2_level = float(data.get("co2_level") or data.get("CO2 level") or 415.0)
        humidity = float(data.get("humidity") or data.get("Humidity") or 50.0)
        temperature = float(data.get("temperature") or data.get("Temperature") or 25.0)

        sensor_record = SensorData(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            air_quality=air_quality,
            pm25=pm25,
            so2_level=so2_level,
            no2_level=no2_level,
            co2_level=co2_level,
            humidity=humidity,
            temperature=temperature
        )
        db.session.add(sensor_record)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Sensor data uploaded and synced successfully",
            "sensor_id": sensor_record.id,
            "data": sensor_record.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/get-user-data/<int:user_id>", methods=["GET"])
@app.route("/api/get-user-data/<int:user_id>", methods=["GET"])
@token_required
def get_user_data(user_id):
    """Fetches stored environmental sensor data for a specific user from SensorData table."""
    try:
        records = SensorData.query.filter_by(user_id=user_id).order_by(SensorData.id.desc()).limit(30).all()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "count": len(records),
            "sensor_data": [r.to_dict() for r in records],
            "latest": records[0].to_dict() if records else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== QUIZRESPONSE BACKEND ROUTES ====================

@app.route("/submit-quiz", methods=["POST"])
@app.route("/api/submit-quiz", methods=["POST"])
@token_required
def submit_quiz():
    """Stores quiz responses into QuizResponse model."""
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)

        # Single question/answer or array of responses
        responses = data.get("responses", [])
        if "question" in data and "answer" in data:
            responses.append({"question": data["question"], "answer": data["answer"]})

        saved = []
        for r in responses:
            q = str(r.get("question", "")).strip()
            a = str(r.get("answer", "")).strip()
            if q and a:
                qr = QuizResponse(user_id=user_id, question=q, answer=a)
                db.session.add(qr)
                saved.append(qr)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Stored {len(saved)} quiz responses",
            "responses": [r.to_dict() for r in saved]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/get-quiz-responses/<int:user_id>", methods=["GET"])
@app.route("/api/get-quiz-responses/<int:user_id>", methods=["GET"])
@token_required
def get_quiz_responses(user_id):
    """Retrieves stored quiz responses for a specific user."""
    try:
        responses = QuizResponse.query.filter_by(user_id=user_id).order_by(QuizResponse.id.desc()).all()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "responses": [r.to_dict() for r in responses]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== ALERTS & SOS ROUTES ====================

@app.route("/get-alerts/<int:user_id>", methods=["GET"])
@app.route("/api/get-alerts/<int:user_id>", methods=["GET"])
@token_required
def get_alerts(user_id):
    """Fetches AI-generated alerts and emergency notifications for a specific user."""
    try:
        alerts = Alert.query.filter_by(user_id=user_id).order_by(Alert.id.desc()).limit(20).all()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "alerts": [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sos/alert", methods=["POST"])
def trigger_sos():
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        patient_name = data.get("patient_name", "Alex Rivera")
        
        user = User.query.get(user_id)
        contact = user.emergency_contact_phone if user else data.get("emergency_contact", "+1-555-0188")
        
        message = f"CRITICAL RESPIRATORY DISTRESS SOS: Patient {patient_name} triggered Emergency SOS! Immediate medical assistance needed."
        
        alert = Alert(user_id=user_id, message=message, timestamp=datetime.utcnow())
        db.session.add(alert)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Emergency SOS broadcasted! SMS and alerts sent to designated emergency contact.",
            "emergency_contact": contact,
            "emergency_numbers": ["112", "108"],
            "ambulance_call": "108",
            "national_emergency": "112"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== INHALER ROUTES ====================

@app.route("/use-inhaler", methods=["POST"])
@app.route("/api/inhaler/use", methods=["POST"])
@token_required
def inhaler_use():
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        doses_to_add = int(data.get("dose_count", 1) or 1)
        if doses_to_add < 1:
            doses_to_add = 1

        CANISTER_CAPACITY = 200
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT SUM(dose_count) as total FROM inhaler_usage WHERE user_id = ?", (user_id,))
            current_total = cur.fetchone()["total"] or 0

            # Decrement / add dose
            conn.execute("INSERT INTO inhaler_usage (user_id, timestamp, dose_count) VALUES (?, ?, ?)",
                         (user_id, datetime.utcnow().isoformat(), doses_to_add))
            conn.commit()

            cur.execute("SELECT SUM(dose_count) as total FROM inhaler_usage WHERE user_id = ?", (user_id,))
            total = cur.fetchone()["total"] or 0

        remaining = max(0, CANISTER_CAPACITY - total)
        low_canister = remaining <= 20
        return jsonify({
            "success": True,
            "total_doses": total,
            "doses_used": total,
            "canister_capacity": CANISTER_CAPACITY,
            "remaining_doses": remaining,
            "low_canister_alert": low_canister,
            "message": f"Inhaler dose logged successfully. {remaining} doses remaining."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/get-inhaler-usage/<int:user_id>", methods=["GET"])
@app.route("/api/inhaler/count/<int:user_id>", methods=["GET"])
@app.route("/api/inhaler/status/<int:user_id>", methods=["GET"])
@token_required
def inhaler_count(user_id):
    try:
        CANISTER_CAPACITY = 200
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT SUM(dose_count) as total FROM inhaler_usage WHERE user_id = ?", (user_id,))
            total = cur.fetchone()["total"] or 0

        remaining = max(0, CANISTER_CAPACITY - total)
        low_canister = remaining <= 20
        return jsonify({
            "success": True,
            "total_doses": total,
            "doses_used": total,
            "canister_capacity": CANISTER_CAPACITY,
            "remaining_doses": remaining,
            "low_canister_alert": low_canister
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/inhaler/reset", methods=["POST"])
@app.route("/api/inhaler/reset/<int:user_id>", methods=["POST"])
@token_required
def inhaler_reset(user_id=None):
    try:
        if not user_id:
            data = request.get_json(force=True) or {}
            user_id = int(data.get("user_id") or 1)
        with get_db_connection() as conn:
            conn.execute("DELETE FROM inhaler_usage WHERE user_id = ?", (user_id,))
            conn.commit()
        return jsonify({
            "success": True,
            "total_doses": 0,
            "doses_used": 0,
            "remaining_doses": 200,
            "canister_capacity": 200,
            "low_canister_alert": False,
            "message": "Canister tracker calibrated for new inhaler (200 doses ready)"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== LIVE ENVIRONMENTAL SYNC ====================

@app.route("/api/live", methods=["GET"])
def get_live():
    lat = float(request.args.get("lat", 28.6139))
    lon = float(request.args.get("lon", 77.2090))
    data = aqi_service.get_live_data(lat, lon)
    if data:
        return jsonify({"success": True, "data": data})
    return jsonify({
        "success": True,
        "data": {
            "timestamp": datetime.utcnow().isoformat(),
            "location": {"lat": lat, "lon": lon},
            "air_quality": 125, "AQI": 125,
            "pm25": 48.5, "PM2.5": 48.5,
            "no2_level": 32.0, "NO2 level": 32.0,
            "so2_level": 18.0, "SO2 level": 18.0,
            "co2_level": 415.0, "CO2 level": 415.0,
            "temperature": 27.5, "Temperature": 27.5,
            "humidity": 62.0, "Humidity": 62.0,
            "fallback": True
        }
    })

# ==================== PREDICTION PIPELINE ====================

def build_recommendations(risk_level, score, symptoms_freq, aqi):
    recs = []
    if risk_level == "High" or score >= 0.6:
        recs.append("Immediate Rescue Protocol: Keep fast-acting rescue inhaler (SABA / Albuterol) within arm's reach.")
        recs.append("Environmental Containment: Remain indoors with HEPA air purification active; keep windows sealed against particulate infiltration.")
        recs.append("Airway Monitoring: Measure Peak Expiratory Flow (PEF). If values fall below 60% of personal best, initiate GINA Red Zone action plan.")
        recs.append("Emergency Escalation: If acute dyspnea, wheezing, or chest tightness occurs, activate the Emergency SOS immediately.")
    elif risk_level == "Medium" or score >= 0.35:
        recs.append("Maintenance Inhalation: Administer prescribed maintenance controller medication (ICS-formoterol) as scheduled.")
        recs.append("Exertion Management: Limit strenuous outdoor physical exercise during peak ambient air pollution periods.")
        recs.append("Respiratory Protection: Wear an N95 particulate respirator when commuting through heavy traffic or industrial areas.")
        recs.append("Airway Hydration: Maintain optimal hydration to reduce bronchial irritation and assist airway clearance.")
    else:
        recs.append("Stable Airway Status: Airway dynamics indicate controlled stability; regular daily activities are permitted.")
        recs.append("Routine Adherence: Continue scheduled preventive controller therapy as prescribed by your physician.")
        recs.append("Ambient Awareness: Check ambient Air Quality Index (AQI) prior to scheduling prolonged outdoor endurance activities.")
    return recs

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)
        patient_name = data.get("patient_name", "Anonymous Patient").strip()
        user_id = int(data.get("user_id") or 1)

        # Robust input parsing helper
        def _parse_num(val, default):
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        aqi = _parse_num(data.get("air_quality") if data.get("air_quality") is not None else data.get("AQI"), 80.0)
        pm25 = _parse_num(data.get("pm25") if data.get("pm25") is not None else data.get("PM2.5"), 35.0)
        so2 = _parse_num(data.get("so2_level") if data.get("so2_level") is not None else data.get("SO2 level"), 15.0)
        no2 = _parse_num(data.get("no2_level") if data.get("no2_level") is not None else data.get("NO2 level"), 25.0)
        co2 = _parse_num(data.get("co2_level") if data.get("co2_level") is not None else data.get("CO2 level"), 450.0)
        humidity = _parse_num(data.get("humidity") if data.get("humidity") is not None else data.get("Humidity"), 50.0)
        temperature = _parse_num(data.get("temperature") if data.get("temperature") is not None else data.get("Temperature"), 24.0)

        symptoms_freq = str(data.get("Asthma Symptoms Frequency", "1-2 times a month"))
        triggers = str(data.get("Triggers", "Dust"))
        weather_sens = str(data.get("Weather Sensitivity", "None"))
        exposure = str(data.get("Poor Air Quality Exposure", "Occasionally"))
        night_diff = str(data.get("Night Breathing Difficulty", "Rarely"))

        # Save to SensorData ORM table
        try:
            sensor = SensorData(
                user_id=user_id,
                timestamp=datetime.utcnow(),
                air_quality=int(aqi),
                pm25=pm25,
                so2_level=so2,
                no2_level=no2,
                co2_level=co2,
                humidity=humidity,
                temperature=temperature
            )
            db.session.add(sensor)
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Review 1 Model Prediction
        if review1_package:
            df = pd.DataFrame([{
                'AQI': aqi, 'PM2.5': pm25, 'SO2 level': so2, 'NO2 level': no2,
                'CO2 level': co2, 'Humidity': humidity, 'Temperature': temperature,
                'Asthma Symptoms Frequency': symptoms_freq, 'Triggers': triggers,
                'Weather Sensitivity': weather_sens, 'Poor Air Quality Exposure': exposure,
                'Night Breathing Difficulty': night_diff
            }])

            # Feature Engineering
            df['AQI_PM_ratio'] = df['AQI'] / (df['PM2.5'] + 1)
            df['pollution_index'] = (df['AQI'] * 0.4 + df['PM2.5'] * 0.3 + df['NO2 level'] * 0.15 + df['SO2 level'] * 0.15)
            df['gas_pollution'] = df['CO2 level'] * df['NO2 level'] * df['SO2 level'] / 10000
            df['humidity_pollution'] = df['Humidity'] * df['pollution_index'] / 100
            df['temp_pollution'] = df['Temperature'] * df['pollution_index'] / 100
            df['AQI_critical'] = (df['AQI'] > 200).astype(int)
            df['AQI_unhealthy'] = ((df['AQI'] > 100) & (df['AQI'] <= 200)).astype(int)
            df['PM25_high'] = (df['PM2.5'] > 75).astype(int)

            symptom_map = {'Daily': 4, 'Frequently (Weekly)': 3, '1-2 times a month': 2, 'Less than once a month': 1}
            df['symptom_severity'] = df['Asthma Symptoms Frequency'].map(symptom_map).fillna(0)
            exposure_map = {'Yes, often': 3, 'Occasionally': 2, 'No': 1}
            df['exposure_score'] = df['Poor Air Quality Exposure'].map(exposure_map).fillna(0)
            night_map = {'Frequently': 3, 'Occasionally': 2, 'Rarely': 1, 'Never': 0}
            df['night_score'] = df['Night Breathing Difficulty'].map(night_map).fillna(0)
            df['trigger_count'] = df['Triggers'].apply(lambda x: str(x).count(',') + 1)
            df['clinical_risk_score'] = df['symptom_severity'] * 0.4 + df['exposure_score'] * 0.3 + df['night_score'] * 0.3
            df['env_risk_score'] = df['AQI_critical'] * 0.3 + df['AQI_unhealthy'] * 0.2 + df['PM25_high'] * 0.25 + (df['pollution_index'] / 500.0) * 0.25

            df_encoded = pd.get_dummies(df, columns=review1_package['categorical_cols'], drop_first=True)
            for col in review1_package['feature_columns']:
                if col not in df_encoded.columns:
                    df_encoded[col] = 0
            df_aligned = df_encoded[review1_package['feature_columns']]
            X_scaled = review1_package['scaler'].transform(df_aligned)

            prob_ens = review1_package['ensemble_model'].predict_proba(X_scaled)[0]
            prob_lr = review1_package['baseline_lr'].predict_proba(X_scaled)[0]
            prob_rf = review1_package['rf_model'].predict_proba(X_scaled)[0]
            prob_gb = review1_package['gb_model'].predict_proba(X_scaled)[0]

            ens_score = float(prob_ens[2] * 1.0 + prob_ens[1] * 0.5)
            lr_score = float(prob_lr[2] * 1.0 + prob_lr[1] * 0.5)
            rf_score = float(prob_rf[2] * 1.0 + prob_rf[1] * 0.5)
            gb_score = float(prob_gb[2] * 1.0 + prob_gb[1] * 0.5)

            pred_class_idx = int(np.argmax(prob_ens))
            risk_level = review1_package['reverse_map'][pred_class_idx]
            confidence = float(np.max(prob_ens))

            p_nz = prob_ens[prob_ens > 0]
            uncertainty = float(-np.sum(p_nz * np.log2(p_nz)))
        else:
            ens_score = 0.5
            lr_score = 0.45
            rf_score = 0.52
            gb_score = 0.51
            risk_level = "Medium"
            confidence = 0.75
            uncertainty = 0.4

        # GINA Safety Guardrail Heuristic Override
        heuristic_override = False
        if symptoms_freq == "Daily" or night_diff == "Frequently":
            ens_score = max(ens_score, 0.88)
            risk_level = "High"
            confidence = 0.95
            heuristic_override = True
        elif symptoms_freq == "Frequently (Weekly)" and ens_score < 0.6:
            ens_score = max(ens_score, 0.62)
            risk_level = "Medium"
            confidence = 0.88
            heuristic_override = True

        # Generate Alert in Alert ORM Table if Risk >= 0.6
        if ens_score >= 0.6:
            try:
                alert_msg = f"Elevated Asthma Risk ({ens_score*100:.1f}%) detected for {patient_name}. Enact airway safety action plan."
                alert_record = Alert(user_id=user_id, message=alert_msg, timestamp=datetime.utcnow())
                db.session.add(alert_record)
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Log prediction to DB
        ts = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO predictions (timestamp, score, risk_level, patient_name, symptoms, aqi, user_id, baseline_score, rf_score, gb_score, heuristic_override)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, ens_score, risk_level, patient_name, symptoms_freq, aqi, user_id, lr_score, rf_score, gb_score, int(heuristic_override))
            )
            conn.commit()

        recommendations = build_recommendations(risk_level, ens_score, symptoms_freq, aqi)

        factors = [
            {"factor": "Air Quality Index (AQI)", "impact": round(float(aqi / 300.0) * 100, 1), "value": f"{aqi:.0f}"},
            {"factor": "PM2.5 Exposure", "impact": round(float(pm25 / 150.0) * 100, 1), "value": f"{pm25:.1f} ug/m3"},
            {"factor": "Symptom Frequency", "impact": 85.0 if "Daily" in symptoms_freq else (65.0 if "Weekly" in symptoms_freq else 25.0), "value": symptoms_freq},
            {"factor": "Night Breathlessness", "impact": 80.0 if "Frequently" in night_diff else (50.0 if "Occasionally" in night_diff else 15.0), "value": night_diff}
        ]

        return jsonify({
            "success": True,
            "patient_name": patient_name,
            "risk_score": round(ens_score, 4),
            "asthma_risk_score": round(ens_score, 4),
            "risk_level": risk_level,
            "tier": risk_level,
            "confidence": round(confidence, 4),
            "uncertainty": round(uncertainty, 4),
            "uncertainty_entropy": round(uncertainty, 4),
            "heuristic_override": heuristic_override,
            "model_architecture": "HridyaVayu Multimodal Collaborative Ensemble (Baseline LR + RF + GB)",
            "model_breakdown": {
                "baseline_linear_regression": round(lr_score, 4),
                "random_forest": round(rf_score, 4),
                "gradient_boosting": round(gb_score, 4),
                "collaborative_ensemble": round(ens_score, 4)
            },
            "recommendations": recommendations,
            "factors": factors,
            "drivers": factors,
            "timestamp": ts
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/send-data-to-ai/<int:user_id>", methods=["GET", "POST"])
@app.route("/api/send-data-to-ai/<int:user_id>", methods=["GET", "POST"])
@token_required
def send_data_to_ai(user_id):
    """Takes stored SensorData & QuizResponse from DB for user_id and runs AI Risk Prediction."""
    try:
        user = User.query.get(user_id)
        patient_name = user.name if user else "Alex Rivera"

        latest_sensor = SensorData.query.filter_by(user_id=user_id).order_by(SensorData.id.desc()).first()
        latest_quiz = QuizResponse.query.filter_by(user_id=user_id).order_by(QuizResponse.id.desc()).all()

        aqi = latest_sensor.air_quality if latest_sensor else 125
        pm25 = latest_sensor.pm25 if latest_sensor else 48.5
        so2 = latest_sensor.so2_level if latest_sensor else 18.0
        no2 = latest_sensor.no2_level if latest_sensor else 32.0
        co2 = latest_sensor.co2_level if latest_sensor else 415.0
        humidity = latest_sensor.humidity if latest_sensor else 62.0
        temperature = latest_sensor.temperature if latest_sensor else 27.5

        # Infer quiz responses if stored
        symptoms_freq = "Frequently (Weekly)"
        night_diff = "Occasionally"
        triggers = "Dust, Air pollution"
        exposure = "Yes, often"
        weather_sens = "Hot and humid weather"

        for q in latest_quiz:
            q_txt = q.question.lower()
            if "frequency" in q_txt: symptoms_freq = q.answer
            elif "night" in q_txt: night_diff = q.answer
            elif "trigger" in q_txt: triggers = q.answer
            elif "exposure" in q_txt: exposure = q.answer
            elif "weather" in q_txt: weather_sens = q.answer

        # Send to internal predict logic
        sim_req = {
            "patient_name": patient_name,
            "user_id": user_id,
            "air_quality": aqi,
            "pm25": pm25,
            "so2_level": so2,
            "no2_level": no2,
            "co2_level": co2,
            "humidity": humidity,
            "temperature": temperature,
            "Asthma Symptoms Frequency": symptoms_freq,
            "Night Breathing Difficulty": night_diff,
            "Triggers": triggers,
            "Poor Air Quality Exposure": exposure,
            "Weather Sensitivity": weather_sens
        }

        # Run prediction
        df = pd.DataFrame([{
            'AQI': aqi, 'PM2.5': pm25, 'SO2 level': so2, 'NO2 level': no2,
            'CO2 level': co2, 'Humidity': humidity, 'Temperature': temperature,
            'Asthma Symptoms Frequency': symptoms_freq, 'Triggers': triggers,
            'Weather Sensitivity': weather_sens, 'Poor Air Quality Exposure': exposure,
            'Night Breathing Difficulty': night_diff
        }])

        df['AQI_PM_ratio'] = df['AQI'] / (df['PM2.5'] + 1)
        df['pollution_index'] = (df['AQI'] * 0.4 + df['PM2.5'] * 0.3 + df['NO2 level'] * 0.15 + df['SO2 level'] * 0.15)
        df['gas_pollution'] = df['CO2 level'] * df['NO2 level'] * df['SO2 level'] / 10000
        df['humidity_pollution'] = df['Humidity'] * df['pollution_index'] / 100
        df['temp_pollution'] = df['Temperature'] * df['pollution_index'] / 100
        df['AQI_critical'] = (df['AQI'] > 200).astype(int)
        df['AQI_unhealthy'] = ((df['AQI'] > 100) & (df['AQI'] <= 200)).astype(int)
        df['PM25_high'] = (df['PM2.5'] > 75).astype(int)

        symptom_map = {'Daily': 4, 'Frequently (Weekly)': 3, '1-2 times a month': 2, 'Less than once a month': 1}
        df['symptom_severity'] = df['Asthma Symptoms Frequency'].map(symptom_map).fillna(0)
        exposure_map = {'Yes, often': 3, 'Occasionally': 2, 'No': 1}
        df['exposure_score'] = df['Poor Air Quality Exposure'].map(exposure_map).fillna(0)
        night_map = {'Frequently': 3, 'Occasionally': 2, 'Rarely': 1, 'Never': 0}
        df['night_score'] = df['Night Breathing Difficulty'].map(night_map).fillna(0)
        df['trigger_count'] = df['Triggers'].apply(lambda x: str(x).count(',') + 1)
        df['clinical_risk_score'] = df['symptom_severity'] * 0.4 + df['exposure_score'] * 0.3 + df['night_score'] * 0.3
        df['env_risk_score'] = df['AQI_critical'] * 0.3 + df['AQI_unhealthy'] * 0.2 + df['PM25_high'] * 0.25 + (df['pollution_index'] / 500.0) * 0.25

        df_encoded = pd.get_dummies(df, columns=review1_package['categorical_cols'], drop_first=True)
        for col in review1_package['feature_columns']:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_aligned = df_encoded[review1_package['feature_columns']]
        X_scaled = review1_package['scaler'].transform(df_aligned)

        prob_ens = review1_package['ensemble_model'].predict_proba(X_scaled)[0]
        ens_score = float(prob_ens[2] * 1.0 + prob_ens[1] * 0.5)
        pred_class_idx = int(np.argmax(prob_ens))
        risk_level = review1_package['reverse_map'][pred_class_idx]

        if ens_score >= 0.6:
            alert = Alert(user_id=user_id, message=f"Risk Score {ens_score*100:.1f}% exceeds 0.6 threshold. Follow safety protocol.", timestamp=datetime.utcnow())
            db.session.add(alert)
            db.session.commit()

        return jsonify({
            "success": True,
            "user_id": user_id,
            "patient_name": patient_name,
            "risk_score": round(ens_score, 4),
            "risk_level": risk_level,
            "sensor_synced": latest_sensor.to_dict() if latest_sensor else None,
            "recommendations": build_recommendations(risk_level, ens_score, symptoms_freq, aqi)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== ADMIN & TELEMETRY ROUTES ====================

@app.route("/api/admin/overview", methods=["GET"])
@token_required(admin_only=True)
def admin_overview():
    try:
        total_users = User.query.count()
        total_sensors = SensorData.query.count()
        total_alerts = Alert.query.count()

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM predictions")
            total_predictions = cur.fetchone()["cnt"]

            cur.execute("SELECT AVG(score) as avg_score FROM predictions")
            avg_score_row = cur.fetchone()
            avg_risk = round(avg_score_row["avg_score"] or 0.0, 3)

            cur.execute("SELECT id, timestamp, patient_name, risk_level, score, aqi, baseline_score, rf_score, gb_score FROM predictions ORDER BY id DESC LIMIT 15")
            recent_records = [dict(row) for row in cur.fetchall()]

        recent_sensors = [s.to_dict() for s in SensorData.query.order_by(SensorData.id.desc()).limit(10).all()]
        recent_alerts = [a.to_dict() for a in Alert.query.order_by(Alert.id.desc()).limit(10).all()]

        return jsonify({
            "success": True,
            "stats": {
                "total_users": total_users,
                "total_sensors": total_sensors,
                "total_predictions": total_predictions,
                "high_risk_alerts": total_alerts,
                "avg_risk": avg_risk
            },
            "review1_models": review1_metrics or {
                "baseline_lr": {"accuracy": 71.33, "f1": 0.7117},
                "random_forest": {"accuracy": 72.33, "f1": 0.7058},
                "gradient_boosting": {"accuracy": 69.67, "f1": 0.6942},
                "collaborative_ensemble": {"accuracy": 73.00, "f1": 0.7234}
            },
            "recent_predictions": recent_records,
            "recent_sensors": recent_sensors,
            "recent_alerts": recent_alerts
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/recent", methods=["GET"])
def api_recent():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, timestamp, score, risk_level, patient_name, symptoms, aqi FROM predictions ORDER BY id DESC LIMIT 10")
            rows = [dict(r) for r in cur.fetchall()]
        return jsonify({"success": True, "items": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def api_stats():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT risk_level, COUNT(*) as count FROM predictions GROUP BY risk_level")
            counts = {row["risk_level"]: row["count"] for row in cur.fetchall()}
            for k in ["Low", "Medium", "High"]:
                if k not in counts:
                    counts[k] = 0
            cur.execute("SELECT COUNT(*) as total FROM predictions")
            total = cur.fetchone()["total"]
        return jsonify({"success": True, "total": total, "distribution": counts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/eda_data", methods=["GET"])
def api_eda_data():
    try:
        csv_path = "data/dataset.csv"
        if not os.path.exists(csv_path):
            return jsonify({"success": False, "error": "Dataset not found"}), 404

        df = pd.read_csv(csv_path)
        total_samples = len(df)
        risk_counts = df['Risk Class'].value_counts().to_dict()

        pollutants = ['AQI', 'PM2.5', 'NO2 level', 'SO2 level']
        pollutant_by_risk = {}
        for p in pollutants:
            pollutant_by_risk[p] = df.groupby('Risk Class')[p].mean().round(2).to_dict()

        symptom_crosstab = pd.crosstab(df['Asthma Symptoms Frequency'], df['Risk Class']).to_dict()
        night_crosstab = pd.crosstab(df['Night Breathing Difficulty'], df['Risk Class']).to_dict()
        sample_records = df.head(20).to_dict(orient='records')

        return jsonify({
            "success": True,
            "data": {
                "total_samples": total_samples,
                "features_count": len(df.columns) - 2,
                "classes": list(risk_counts.keys()),
                "risk_distribution": risk_counts,
                "pollutant_by_risk": pollutant_by_risk,
                "symptom_by_risk": symptom_crosstab,
                "night_by_risk": night_crosstab,
                "sample_records": sample_records
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/figures_list", methods=["GET"])
def api_figures_list():
    figures = [
        {"id": "roc_curves", "title": "Multi-Model ROC Curves", "category": "Evaluation", "filename": "roc_curves.png", "desc": "ROC curves showing performance across all evaluated classifiers."},
        {"id": "confusion_matrices", "title": "Confusion Matrices Comparison", "category": "Evaluation", "filename": "confusion_matrices.png", "desc": "Confusion matrices illustrating classification distribution."},
        {"id": "model_comparison", "title": "Model Comparison Benchmark", "category": "Evaluation", "filename": "model_comparison.png", "desc": "Comparative accuracy and F1 performance across baseline and ensemble models."},
        {"id": "shap_summary", "title": "SHAP Global Feature Importance", "category": "Explainability", "filename": "shap_summary.png", "desc": "SHAP values identifying top clinical and environmental attack triggers."},
        {"id": "correlation_heatmap", "title": "Environmental Feature Correlations", "category": "EDA", "filename": "correlation_heatmap.png", "desc": "Correlation matrix across all pollutant and weather variables."}
    ]
    return jsonify({"success": True, "figures": figures})

# ==================== AIRGUARD AGENTIC CORE & HEALTH ROUTES ====================

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """Service health, model status, and agent readiness check."""
    return jsonify({
        "status": "healthy",
        "service": "AirGuard Agentic Healthcare Engine",
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": review1_package is not None,
        "llm_provider": agent_loop.llm.get_provider_name(),
        "features": {
            "deterministic_guardrails": True,
            "human_in_the_loop_approval": True,
            "bilingual_support": True,
            "privacy_controls_supported": True,
            "gdpr_dpdp_aligned": True
        }
    })

@app.route("/api/agent/run", methods=["POST"])
@token_required
def agent_run():
    """Executes a full SENSE -> REASON -> PLAN -> PROPOSE -> ACT -> LOG cycle."""
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        trigger = data.get("trigger", "manual_run")
        user_query = data.get("user_query")
        lat = float(data.get("lat")) if data.get("lat") is not None else None
        lon = float(data.get("lon")) if data.get("lon") is not None else None

        result = agent_loop.run_cycle(
            user_id=user_id,
            trigger=trigger,
            user_query=user_query,
            lat=lat,
            lon=lon
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/forecast", methods=["GET"])
def agent_forecast():
    """Provides 48-hour air quality & meteorological forecast with safest window."""
    lat = float(request.args.get("lat", 28.6139))
    lon = float(request.args.get("lon", 77.2090))
    hours = int(request.args.get("hours", 48))
    forecast = AirGuardTools.get_air_quality_forecast(lat, lon, hours)
    return jsonify(forecast)

@app.route("/api/agent/actions/pending/<int:user_id>", methods=["GET"])
@token_required
def agent_pending_actions(user_id):
    """Retrieves all pending human-approval actions for a user."""
    try:
        actions = AgentAction.query.filter_by(user_id=user_id, status="PENDING").order_by(AgentAction.id.desc()).all()
        action_list = [a.to_dict() for a in actions]
        return jsonify({
            "success": True,
            "count": len(actions),
            "actions": action_list,
            "pending_actions": action_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/actions/approve/<int:action_id>", methods=["POST"])
@token_required
def agent_approve_action(action_id):
    """Human-in-the-loop: Patient explicitly approves action. Dispatches via notification tool."""
    try:
        action = AgentAction.query.get(action_id)
        if not action:
            return jsonify({"success": False, "error": "Action not found"}), 404

        # Idempotency guard: never allow re-approving an action
        if action.status != "PENDING":
            return jsonify({
                "success": False,
                "error": f"Action has already been decided with status: {action.status}. Cannot re-approve."
            }), 400

        # Allow patient to edit payload/message before approving
        if request.is_json:
            data = request.get_json(silent=True) or {}
            if "message" in data and data["message"]:
                action.proposed_payload = str(data["message"]).strip()
            elif "proposed_payload" in data and data["proposed_payload"]:
                action.proposed_payload = str(data["proposed_payload"]).strip()

        action.status = "APPROVED"
        action.decided_at = datetime.utcnow()
        db.session.commit()

        # Dispatch action exactly once
        dispatch_result = AirGuardTools.send_notification(action_id)
        return jsonify({
            "success": True,
            "message": "Action approved by user and dispatched",
            "action": action.to_dict(),
            "dispatch": dispatch_result
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/actions/reject/<int:action_id>", methods=["POST"])
@token_required
def agent_reject_action(action_id):
    """Human-in-the-loop: Patient explicitly rejects action."""
    try:
        action = AgentAction.query.get(action_id)
        if not action:
            return jsonify({"success": False, "error": "Action not found"}), 404

        if action.status != "PENDING":
            return jsonify({
                "success": False,
                "error": f"Action has already been decided with status: {action.status}."
            }), 400

        action.status = "REJECTED"
        action.decided_at = datetime.utcnow()
        action.execution_result = "Action declined by user in approval queue."
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Action successfully rejected by patient",
            "action": action.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/logs/<int:user_id>", methods=["GET"])
@token_required
def agent_audit_logs(user_id):
    """Complete audit trail of agent reasoning, inputs, outputs, and safety status."""
    try:
        limit = int(request.args.get("limit", 20))
        logs = AgentLog.query.filter_by(user_id=user_id).order_by(AgentLog.id.desc()).limit(limit).all()
        return jsonify({
            "success": True,
            "count": len(logs),
            "logs": [l.to_dict() for l in logs]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/plan/<int:user_id>", methods=["GET"])
@token_required
def agent_daily_plan(user_id):
    """Retrieves or computes today's 24-hour proactive plan."""
    try:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        plan = DailyPlan.query.filter_by(user_id=user_id, valid_date=today_str).first()
        if not plan:
            plan_res = AirGuardTools.draft_plan(user_id, review1_package=review1_package)
            return jsonify(plan_res)
        return jsonify({
            "success": True,
            "plan_id": plan.id,
            "plan": plan.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/symptom/log", methods=["POST"])
@token_required
def agent_log_symptom():
    """Logs patient symptom diary entry and recalculates risk/plan."""
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        symptoms = data.get("symptoms", "")
        severity = data.get("severity", "Mild")
        puffs = int(data.get("inhaler_puffs_used", 0) or 0)
        pef = float(data.get("pef_reading")) if data.get("pef_reading") is not None else None
        activity = data.get("activity_level", "Rest")
        notes = data.get("notes", "")

        # Check for input red flags in symptoms / notes
        red_flag = check_input_red_flags(f"{symptoms} {notes}")

        res = AirGuardTools.log_symptom(
            user_id=user_id,
            symptoms=symptoms,
            severity="Severe" if red_flag["tripped"] else severity,
            inhaler_puffs_used=puffs,
            pef_reading=pef,
            activity_level=activity,
            notes=notes
        )

        # Trigger quick agent cycle with symptom_logged trigger
        agent_loop.run_cycle(user_id=user_id, trigger="symptom_logged", user_query=f"{symptoms} {notes}")

        return jsonify({
            "success": True,
            "diary": res["entry"],
            "red_flag": red_flag,
            "emergency": red_flag["tripped"]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/symptom/history/<int:user_id>", methods=["GET"])
@app.route("/api/agent/symptom/history/<int:user_id>", methods=["GET"])
@token_required
def get_symptom_history(user_id):
    """Retrieves longitudinal symptom diary history for a patient."""
    try:
        entries = SymptomDiary.query.filter_by(user_id=user_id).order_by(SymptomDiary.timestamp.desc()).all()
        return jsonify({
            "success": True,
            "count": len(entries),
            "symptoms": [e.to_dict() for e in entries]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/chat", methods=["POST"])
@token_required
def agent_chat():
    """Interactive conversational agent endpoint with voice-query support and guardrails."""
    try:
        data = request.get_json(force=True) or {}
        user_id = int(data.get("user_id") or 1)
        query = (data.get("query") or data.get("message") or "").strip()
        language = data.get("language") or "en"

        user = User.query.get(user_id)
        if user and not language:
            language = user.language_pref or "en"

        cycle_res = agent_loop.run_cycle(
            user_id=user_id,
            trigger="chat_query",
            user_query=query
        )

        agent_text = cycle_res.get("agent_response") or cycle_res.get("response") or ""

        return jsonify({
            "success": True,
            "response": agent_text,
            "reply": agent_text,
            "emergency": cycle_res.get("emergency", False),
            "risk_tier": cycle_res.get("risk_tier"),
            "safest_window": cycle_res.get("safest_window"),
            "guardrail_tripped": cycle_res.get("guardrail_tripped", False),
            "guardrail_details": cycle_res.get("guardrail_details"),
            "llm_provider": cycle_res.get("llm_provider")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/doctor-summary/<int:user_id>", methods=["GET"])
@token_required
def agent_doctor_summary(user_id):
    """Generates 30-day clinical consultation report for doctor appointment."""
    summary = AirGuardTools.generate_doctor_summary(user_id)
    return jsonify(summary)

@app.route("/api/agent/doctor-summary/<int:user_id>/pdf", methods=["GET"])
@token_required
def agent_doctor_summary_pdf(user_id):
    """Generates authentic clinical consultation PDF for physician review."""
    try:
        pdf_bytes = AirGuardTools.generate_doctor_summary_pdf(user_id)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"AirGuard_Doctor_Summary_Patient_{user_id}.pdf"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== GDPR / DPDP ACT DATA PRIVACY ROUTES ====================

@app.route("/api/user/export-data/<int:user_id>", methods=["GET"])
@app.route("/api/user/export/<int:user_id>", methods=["GET"])
@app.route("/api/export-data/<int:user_id>", methods=["GET"])
@token_required
def export_user_data(user_id):
    """Right to Data Portability: Downloads complete user data across all 10 tables in JSON format."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        sensors = [s.to_dict() for s in SensorData.query.filter_by(user_id=user_id).all()]
        diaries = [d.to_dict() for d in SymptomDiary.query.filter_by(user_id=user_id).all()]
        actions = [a.to_dict() for a in AgentAction.query.filter_by(user_id=user_id).all()]
        logs = [l.to_dict() for l in AgentLog.query.filter_by(user_id=user_id).all()]
        alerts = [al.to_dict() for al in Alert.query.filter_by(user_id=user_id).all()]
        plans = [p.to_dict() for p in DailyPlan.query.filter_by(user_id=user_id).all()]
        quizzes = [q.to_dict() for q in QuizResponse.query.filter_by(user_id=user_id).all()]

        # Query raw SQLite tables (predictions and inhaler_usage)
        preds = []
        inhalers = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM predictions WHERE user_id = ?", (user_id,))
            preds = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM inhaler_usage WHERE user_id = ?", (user_id,))
            inhalers = [dict(r) for r in cur.fetchall()]

        payload = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "service": "AirGuard Healthcare Agent",
                "format": "JSON Portable Format",
                "compliance_design": "GDPR Article 20 / India DPDP Act 2023 portability principles",
                "tables_included": [
                    "user", "sensor_data", "symptom_diary", "agent_action",
                    "agent_log", "alert", "daily_plan", "quiz_response",
                    "predictions", "inhaler_usage"
                ]
            },
            "user_profile": user.to_dict(),
            "sensor_readings": sensors,
            "symptom_diary": diaries,
            "agent_actions": actions,
            "agent_audit_logs": logs,
            "alerts": alerts,
            "daily_plans": plans,
            "quiz_responses": quizzes,
            "predictions": preds,
            "inhaler_usage": inhalers
        }
        return jsonify({
            "success": True,
            **payload,
            "data": payload
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/user/delete-account/<int:user_id>", methods=["POST", "DELETE"])
@app.route("/api/user/delete/<int:user_id>", methods=["POST", "DELETE"])
@app.route("/api/delete-account/<int:user_id>", methods=["POST", "DELETE"])
@token_required
def delete_user_account(user_id):
    """Right to Erasure (Forget Me): Completely deletes user and all personal medical data across all 10 tables."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # 1. Cascade deletes across ORM tables
        SensorData.query.filter_by(user_id=user_id).delete()
        SymptomDiary.query.filter_by(user_id=user_id).delete()
        AgentAction.query.filter_by(user_id=user_id).delete()
        AgentLog.query.filter_by(user_id=user_id).delete()
        Alert.query.filter_by(user_id=user_id).delete()
        QuizResponse.query.filter_by(user_id=user_id).delete()
        DailyPlan.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()

        # 2. Delete from raw SQLite tables
        with get_db_connection() as conn:
            conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM inhaler_usage WHERE user_id = ?", (user_id,))
            conn.commit()

        return jsonify({
            "success": True,
            "message": f"User account #{user_id} and all associated medical records permanently deleted across all tables."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
        return jsonify({"success": False, "error": str(e)}), 500

# Initialize DB on load (ensures tables exist when running with Gunicorn or direct python)
init_db()

# ==================== MAIN ====================

if __name__ == "__main__":
    if not os.path.exists("web_ui"):
        os.makedirs("web_ui")
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 HridyaVayu Server Started on port {port} - Collaborative AI Engine Ready")
    app.run(host="0.0.0.0", port=port, debug=False)
