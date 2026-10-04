#!/usr/bin/env python3
"""
AirGuard Agent - Demo Seed Script
Seeds a realistic 30-day patient journey for demo user Alex Rivera.
Includes symptom diaries, peak flow history, sensor records, past agent approvals,
and a fresh PENDING action ready for live judge interaction.
"""

import os
import sys
import json
from datetime import datetime, timedelta
import random

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from models import db, User, SensorData, SymptomDiary, AgentAction, AgentLog, DailyPlan, Alert, QuizResponse

def create_demo_app():
    app = Flask(__name__)
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'asthmai.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def seed_database():
    app = create_demo_app()
    with app.app_context():
        print("[*] Initializing AirGuard database tables...")
        db.create_all()

        # 1. Create or update Demo User (Alex Rivera)
        alex = User.query.filter((User.phone_no == "+1555019900") | (User.name == "Alex Rivera")).first()
        if not alex:
            alex = User(
                name="Alex Rivera",
                age=29,
                gender="Male",
                phone_no="+1555019900",
                medical_history="Childhood asthma diagnosed age 8; seasonal allergic rhinitis; sensitive to high particulate pollution (PM2.5) and sudden cold air drops.",
                baseline_severity="Moderate Persistent",
                inhaler_prescribed="Budesonide/Formoterol (Symbicort 160/4.5mcg) 2 puffs BID daily; Albuterol Sulfate 90mcg 2 puffs PRN as reliever",
                triggers="PM2.5, Cold dry air, Dust mites, Vehicle exhaust",
                language_pref="en",
                city="Delhi",
                lat=28.6139,
                lon=77.2090,
                emergency_contact_name="Dr. Sarah Patel (Pulmonologist) / Elena Rivera",
                emergency_contact_phone="+91 98765 43210"
            )
            alex.set_password("demo123")
            db.session.add(alex)
            db.session.commit()
            print(f"[+] Created demo user: Alex Rivera (ID: {alex.id}, Phone: {alex.phone_no})")
        else:
            alex.name = "Alex Rivera"
            alex.age = 29
            alex.gender = "Male"
            alex.medical_history = "Childhood asthma diagnosed age 8; seasonal allergic rhinitis; sensitive to high particulate pollution (PM2.5) and sudden cold air drops."
            alex.baseline_severity = "Moderate Persistent"
            alex.inhaler_prescribed = "Budesonide/Formoterol (Symbicort 160/4.5mcg) 2 puffs BID daily; Albuterol Sulfate 90mcg 2 puffs PRN as reliever"
            alex.triggers = "PM2.5, Cold dry air, Dust mites, Vehicle exhaust"
            alex.language_pref = "en"
            alex.city = "Delhi"
            alex.lat = 28.6139
            alex.lon = 77.2090
            alex.emergency_contact_name = "Dr. Sarah Patel (Pulmonologist) / Elena Rivera"
            alex.emergency_contact_phone = "+91 98765 43210"
            alex.set_password("demo123")
            db.session.commit()
            print(f"[+] Updated demo user: Alex Rivera (ID: {alex.id})")

        user_id = alex.id

        # Clean existing dependent records for a consistent clean demo state
        SymptomDiary.query.filter_by(user_id=user_id).delete()
        SensorData.query.filter_by(user_id=user_id).delete()
        AgentAction.query.filter_by(user_id=user_id).delete()
        AgentLog.query.filter_by(user_id=user_id).delete()
        DailyPlan.query.filter_by(user_id=user_id).delete()
        Alert.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        print("[*] Generating 30 days of realistic clinical and environmental history...")
        now = datetime.utcnow()

        # High pollution spike days in the past 30 days
        spike_days = {4, 5, 17, 18, 25}
        moderate_days = {2, 8, 9, 10, 19, 20}

        for day_offset in range(30, -1, -1):
            record_date = now - timedelta(days=day_offset)

            # Determine environmental profile for the day
            if day_offset in spike_days:
                aqi = random.randint(185, 240)
                pm25 = round(aqi * 0.48 + random.uniform(-5, 5), 1)
                no2 = round(random.uniform(45.0, 70.0), 1)
                so2 = round(random.uniform(15.0, 28.0), 1)
                temp = round(random.uniform(16.0, 22.0), 1)
                hum = round(random.uniform(40.0, 60.0), 1)

                symptoms = "Moderate wheezing, chest tightness after evening commute, dry persistent cough"
                severity = "Moderate"
                pef = round(random.uniform(380.0, 410.0), 1)  # Drop from baseline 480
                puffs = random.randint(2, 3)
                activity = "Commute"
                notes = "Evening smog felt heavy; had to use albuterol inhaler twice."
            elif day_offset in moderate_days:
                aqi = random.randint(115, 145)
                pm25 = round(aqi * 0.40 + random.uniform(-3, 3), 1)
                no2 = round(random.uniform(28.0, 42.0), 1)
                so2 = round(random.uniform(8.0, 16.0), 1)
                temp = round(random.uniform(20.0, 26.0), 1)
                hum = round(random.uniform(50.0, 70.0), 1)

                symptoms = "Mild morning cough, throat irritation"
                severity = "Mild"
                pef = round(random.uniform(425.0, 455.0), 1)
                puffs = 1
                activity = "Light Walk"
                notes = "Felt mild tightness upon waking; improved after drinking warm water."
            else:
                # Clean air day
                aqi = random.randint(45, 80)
                pm25 = round(aqi * 0.32 + random.uniform(-2, 2), 1)
                no2 = round(random.uniform(12.0, 22.0), 1)
                so2 = round(random.uniform(4.0, 10.0), 1)
                temp = round(random.uniform(23.0, 28.0), 1)
                hum = round(random.uniform(45.0, 65.0), 1)

                symptoms = "None reported"
                severity = "None"
                pef = round(random.uniform(465.0, 495.0), 1)  # Near personal best 500
                puffs = 0
                activity = "Rest"
                notes = "Breathed comfortably throughout the day. Took regular daily controller."

            # Save Sensor Snapshot (simulated daily noon reading)
            sensor = SensorData(
                user_id=user_id,
                timestamp=record_date.replace(hour=12, minute=0, second=0),
                air_quality=aqi,
                pm25=pm25,
                so2_level=so2,
                no2_level=no2,
                co2_level=round(random.uniform(420, 520), 1),
                humidity=hum,
                temperature=temp
            )
            db.session.add(sensor)

            # Save Symptom Diary (evening log)
            diary = SymptomDiary(
                user_id=user_id,
                timestamp=record_date.replace(hour=20, minute=30, second=0),
                symptoms=symptoms,
                severity=severity,
                inhaler_puffs_used=puffs,
                pef_reading=pef,
                activity_level=activity,
                notes=notes
            )
            db.session.add(diary)

        # 3. Add Historical Past Agent Actions (Approved & Executed, and 1 Rejected)
        print("[*] Seeding historical agent approvals and audit logs...")

        actions_data = [
            {
                "offset_days": 24,
                "action_type": "routine_reschedule",
                "recipient": "Alex Rivera (In-App Calendar)",
                "channel": "push",
                "payload": "Severe particulate spike (AQI 210) forecast from 18:00-21:00. Propose rescheduling planned outdoor jog to 07:00 AM clean air window.",
                "reasoning": "Open-Meteo forecast indicated AQI 210 during rush hour. Alex's baseline asthma exhibits acute sensitivity at AQI > 150.",
                "status": "EXECUTED",
                "decided_offset": 24,
                "result": "Calendar event shifted to 07:00 AM. User notified via push."
            },
            {
                "offset_days": 18,
                "action_type": "caregiver_alert",
                "recipient": "Dr. Sarah Patel (Emergency Pulmonologist Contact)",
                "channel": "sms",
                "payload": "AirGuard Health Alert: Alex Rivera reported PEF drop to 385 L/min (79% of personal best) accompanied by 3 rescue inhaler puffs during high smog episode.",
                "reasoning": "Symptom diary triggered GINA Yellow Zone criteria: PEF < 80% baseline and repeated albuterol administration within 24h.",
                "status": "EXECUTED",
                "decided_offset": 18,
                "result": "SMS delivered via simulated gateway to +91 98765 43210."
            },
            {
                "offset_days": 12,
                "action_type": "routine_reschedule",
                "recipient": "Alex Rivera",
                "channel": "in_app",
                "payload": "Propose shifting morning outdoor walk to indoor treadmill due to early morning fog and elevated PM2.5 (115 µg/m³).",
                "reasoning": "Air stagnation detected between 05:00 and 08:00.",
                "status": "REJECTED",
                "decided_offset": 12,
                "result": "User rejected: Walk was already postponed."
            },
            {
                "offset_days": 4,
                "action_type": "routine_reschedule",
                "recipient": "Alex Rivera (In-App Advisory)",
                "channel": "sms",
                "payload": "PM2.5 spike warning (138 µg/m³). Recommended action: Activate indoor HEPA air filtration and avoid unmasked outdoor exposure.",
                "reasoning": "Diurnal inversion spike predicted. Pre-exposure protection suggested.",
                "status": "EXECUTED",
                "decided_offset": 4,
                "result": "Advisory confirmed and logged in daily plan."
            }
        ]

        for act in actions_data:
            c_time = now - timedelta(days=act["offset_days"], hours=4)
            d_time = now - timedelta(days=act["decided_offset"], hours=3, minutes=30)
            action = AgentAction(
                user_id=user_id,
                created_at=c_time,
                action_type=act["action_type"],
                recipient=act["recipient"],
                channel=act["channel"],
                proposed_payload=act["payload"],
                reasoning=act["reasoning"],
                status=act["status"],
                decided_at=d_time,
                execution_result=act["result"]
            )
            db.session.add(action)

        # 4. TODAY'S CRITICAL PENDING ACTION (For live hackathon judging & approval interaction)
        pending_action = AgentAction(
            user_id=user_id,
            created_at=now - timedelta(minutes=25),
            action_type="routine_reschedule",
            recipient="Alex Rivera (In-App & SMS)",
            channel="sms",
            proposed_payload="AirGuard 24h Advisory: PM2.5 is projected to peak at 142 µg/m³ (AQI 195 - Unhealthy) between 17:00 and 21:00 due to evening temperature inversion and traffic. Recommended action: Reschedule evening outdoor cardio to tomorrow morning 06:30-08:30 AM (Safest Air Window, projected AQI 62). Ensure rescue inhaler is in your bag when commuting.",
            reasoning="Open-Meteo 48-hour forecast detects an evening particulate concentration spike. Alex's historical records indicate an 80% probability of requiring reliever medication when exposed to AQI > 150. Proposing schedule shift to protect respiratory capacity.",
            status="PENDING",
            decided_at=None,
            execution_result=None
        )
        db.session.add(pending_action)

        # 5. Agent Audit Logs
        log_entries = [
            {
                "offset_hours": 24,
                "trigger": "forecast_update",
                "reasoning": "Ingested 48-hour atmospheric forecast from Open-Meteo. Peak AQI 195 predicted at 19:00. Generated 24h proactive daily schedule.",
                "guardrail": False
            },
            {
                "offset_hours": 16,
                "trigger": "symptom_diary",
                "reasoning": "Alex logged evening PEF of 475 L/min. Green zone stability confirmed. No emergency thresholds exceeded.",
                "guardrail": False
            },
            {
                "offset_hours": 8,
                "trigger": "chat_query",
                "reasoning": "User asked 'Can I go for an evening run at 6 PM?'. Agent evaluated air quality forecast (AQI 188 at 18:00) and advised rescheduling to morning safest window (06:30-08:30).",
                "guardrail": False
            },
            {
                "offset_hours": 0.5,
                "trigger": "forecast_update",
                "reasoning": "Predictive forecast confirmed high evening exposure risk. Proposed schedule shift action #106 to human-in-the-loop approval queue.",
                "guardrail": False
            }
        ]

        for entry in log_entries:
            db.session.add(AgentLog(
                user_id=user_id,
                timestamp=now - timedelta(hours=entry["offset_hours"]),
                trigger=entry["trigger"],
                input_state=json.dumps({"aqi": 182, "pm25": 87.4, "pef": 475, "risk": "Moderate Risk"}),
                reasoning=entry["reasoning"],
                actions_proposed=json.dumps([{"type": "routine_reschedule", "channel": "sms", "status": "PENDING"}]),
                guardrail_tripped=entry["guardrail"],
                guardrail_details=None
            ))

        # 6. Today's Daily Plan
        today_str = now.strftime("%Y-%m-%d")
        daily_plan = DailyPlan(
            user_id=user_id,
            generated_at=now - timedelta(hours=1),
            valid_date=today_str,
            risk_tier="Medium",
            safest_window="06:30 - 08:30 AM",
            summary="Moderate air quality throughout daytime with sharp evening particulate spike (AQI 195) after 17:00. Cleanest air window is 06:30-08:30 AM.",
            hourly_recommendations=json.dumps([
                {"time": "06:00 - 09:00", "aqi": 62, "level": "Good / Moderate", "advice": "Safest window of the day. Ideal for outdoor exercise and airing living spaces."},
                {"time": "09:00 - 13:00", "aqi": 110, "level": "Moderate", "advice": "Normal indoor routine. Keep windows ajar only on low-traffic sides."},
                {"time": "13:00 - 17:00", "aqi": 128, "level": "Moderate", "advice": "Pre-dusk period. Carry rescue inhaler during routine afternoon transit."},
                {"time": "17:00 - 21:00", "aqi": 195, "level": "Unhealthy", "advice": "HIGH RISK: Particulate inversion spike. Avoid outdoor exertion, close windows, use indoor air filter."},
                {"time": "21:00 - 06:00", "aqi": 160, "level": "Unhealthy for Sensitive Groups", "advice": "Nighttime rest. Ensure bedroom filter is running on low quiet mode."}
            ]),
            preventive_actions=json.dumps([
                "Shift planned evening outdoor run to 06:30-08:30 AM tomorrow.",
                "Ensure prescribed Albuterol reliever is kept in daily bag during commute.",
                "Take prescribed maintenance Budesonide inhaler as scheduled by your doctor.",
                "Keep bedroom air purifier running on sleep mode overnight."
            ])
        )
        db.session.add(daily_plan)

        db.session.commit()
        print("[+] Seed completed successfully!")
        print(f"[+] Demo account ready: alex@example.com (Password: demo123, Phone: +1555019900)")
        print(f"[+] 30 days of symptom diary and sensor records inserted.")
        print(f"[+] 4 historical executed actions + 1 PENDING action ready for live approval.")

if __name__ == "__main__":
    seed_database()
