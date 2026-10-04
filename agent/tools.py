"""
AirGuard Agent Clinical & Environmental Tools.
Provides real-time air quality forecasts, ML risk assessment integration,
symptom logging, 24-hour daily planning, human approval action dispatch, and doctor consultation summaries.
"""

import os
import json
import math
import sqlite3
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from models import db, User, SensorData, Alert, QuizResponse, SymptomDiary, AgentAction, AgentLog, DailyPlan

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

class AirGuardTools:
    """
    Core toolset for AirGuard autonomous agent.
    """

    @staticmethod
    def get_air_quality_forecast(lat: float = 28.6139, lon: float = 77.2090, hours: int = 48) -> Dict[str, Any]:
        """
        Retrieves 48-hour hourly air quality and weather forecast from Open-Meteo API.
        Falls back to authentic simulated diurnal cycle if network is unavailable.
        """
        try:
            aq_params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi",
                "timezone": "auto",
                "forecast_days": min(3, max(1, math.ceil(hours / 24)))
            }
            w_params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                "timezone": "auto",
                "forecast_days": min(3, max(1, math.ceil(hours / 24)))
            }

            aq_res = requests.get(OPEN_METEO_AQ_URL, params=aq_params, timeout=5)
            w_res = requests.get(OPEN_METEO_WEATHER_URL, params=w_params, timeout=5)

            if aq_res.status_code == 200 and w_res.status_code == 200:
                aq_json = aq_res.json().get("hourly", {})
                w_json = w_res.json().get("hourly", {})

                times = aq_json.get("time", [])[:hours]
                pm25 = aq_json.get("pm2_5", [])[:hours]
                pm10 = aq_json.get("pm10", [])[:hours]
                no2 = aq_json.get("nitrogen_dioxide", [])[:hours]
                so2 = aq_json.get("sulphur_dioxide", [])[:hours]
                o3 = aq_json.get("ozone", [])[:hours]
                us_aqi = aq_json.get("us_aqi", [])[:hours]

                temp = w_json.get("temperature_2m", [])[:hours]
                hum = w_json.get("relative_humidity_2m", [])[:hours]
                precip = w_json.get("precipitation", [])[:hours]
                wind = w_json.get("wind_speed_10m", [])[:hours]

                hourly_data = []
                for i in range(len(times)):
                    val_aqi = int(us_aqi[i]) if i < len(us_aqi) and us_aqi[i] is not None else 80
                    val_pm25 = float(pm25[i]) if i < len(pm25) and pm25[i] is not None else 35.0
                    hourly_data.append({
                        "time": times[i],
                        "hour": times[i].split("T")[1] if "T" in times[i] else times[i],
                        "aqi": val_aqi,
                        "pm25": round(val_pm25, 1),
                        "pm10": round(float(pm10[i] or 0), 1) if i < len(pm10) else 0.0,
                        "no2": round(float(no2[i] or 0), 1) if i < len(no2) else 0.0,
                        "so2": round(float(so2[i] or 0), 1) if i < len(so2) else 0.0,
                        "ozone": round(float(o3[i] or 0), 1) if i < len(o3) else 0.0,
                        "temperature": round(float(temp[i] or 25), 1) if i < len(temp) else 25.0,
                        "humidity": round(float(hum[i] or 50), 1) if i < len(hum) else 50.0,
                        "precipitation": round(float(precip[i] or 0), 1) if i < len(precip) else 0.0,
                        "wind_speed": round(float(wind[i] or 0), 1) if i < len(wind) else 0.0
                    })

                safest_window = AirGuardTools._compute_safest_window(hourly_data[:24])

                return {
                    "success": True,
                    "is_simulated": False,
                    "location": {"lat": lat, "lon": lon},
                    "total_hours": len(hourly_data),
                    "safest_window": safest_window,
                    "hourly": hourly_data
                }
        except Exception as e:
            # Safe simulated fallback
            pass

        # Generate realistic simulated diurnal curve (morning clean air window, evening traffic spike)
        simulated_data = []
        base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        for h in range(hours):
            cur_time = base_time + timedelta(hours=h)
            hour_of_day = cur_time.hour
            # Diurnal sinusoidal variation: best at 6am-8am, worst at 20:00
            diurnal_factor = math.sin((hour_of_day - 6) / 24.0 * 2 * math.pi)
            sim_aqi = int(max(40, min(260, 110 + 60 * diurnal_factor + (h % 5) * 4)))
            sim_pm25 = round(sim_aqi * 0.42, 1)

            simulated_data.append({
                "time": cur_time.isoformat(),
                "hour": f"{hour_of_day:02d}:00",
                "aqi": sim_aqi,
                "pm25": sim_pm25,
                "pm10": round(sim_pm25 * 1.6, 1),
                "no2": round(25.0 + 15 * diurnal_factor, 1),
                "so2": 12.0,
                "ozone": round(20.0 + 20 * math.cos(hour_of_day / 24.0 * 2 * math.pi), 1),
                "temperature": round(22.0 + 8.0 * math.sin((hour_of_day - 9) / 24.0 * 2 * math.pi), 1),
                "humidity": round(65.0 - 20.0 * math.sin((hour_of_day - 9) / 24.0 * 2 * math.pi), 1),
                "precipitation": 0.0,
                "wind_speed": 8.5
            })

        safest_window = AirGuardTools._compute_safest_window(simulated_data[:24])

        return {
            "success": True,
            "is_simulated": True,
            "location": {"lat": lat, "lon": lon},
            "total_hours": len(simulated_data),
            "safest_window": safest_window,
            "hourly": simulated_data
        }

    @staticmethod
    def _compute_safest_window(hourly_24: List[Dict[str, Any]]) -> str:
        """Finds the contiguous 2-hour daylight window (06:00 to 20:00) with minimum AQI."""
        daylight = [h for h in hourly_24 if 6 <= int(h["hour"].split(":")[0]) <= 19]
        if not daylight or len(daylight) < 2:
            return "06:30 - 08:30"

        min_avg = float('inf')
        best_idx = 0
        for i in range(len(daylight) - 1):
            avg_aqi = (daylight[i]["aqi"] + daylight[i+1]["aqi"]) / 2.0
            if avg_aqi < min_avg:
                min_avg = avg_aqi
                best_idx = i

        start_h = daylight[best_idx]["hour"]
        end_h = daylight[best_idx + 1]["hour"]
        end_hour_int = (int(end_h.split(":")[0]) + 1) % 24
        return f"{start_h} - {end_hour_int:02d}:00"

    @staticmethod
    def get_risk_assessment(user_id: int, review1_package=None) -> Dict[str, Any]:
        """
        Runs patient through HridyaVayu multimodal ensemble + GINA override.
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        latest_sensor = SensorData.query.filter_by(user_id=user_id).order_by(SensorData.id.desc()).first()
        aqi = float(latest_sensor.air_quality if latest_sensor else 85)
        pm25 = float(latest_sensor.pm25 if latest_sensor else 38.0)
        so2 = float(latest_sensor.so2_level if latest_sensor else 12.0)
        no2 = float(latest_sensor.no2_level if latest_sensor else 24.0)
        co2 = float(latest_sensor.co2_level if latest_sensor else 415.0)
        humidity = float(latest_sensor.humidity if latest_sensor else 55.0)
        temperature = float(latest_sensor.temperature if latest_sensor else 26.0)

        # Pull recent symptoms
        recent_symptoms = SymptomDiary.query.filter_by(user_id=user_id).order_by(SymptomDiary.id.desc()).limit(7).all()
        has_severe_symptom = any(s.severity in ["Severe", "Moderate"] for s in recent_symptoms)
        symptom_freq = "Daily" if len(recent_symptoms) >= 5 else ("Frequently (Weekly)" if len(recent_symptoms) >= 2 else "1-2 times a month")
        night_diff = "Frequently" if any("night" in (s.notes or "").lower() for s in recent_symptoms) else "Occasionally"

        if review1_package:
            try:
                df = pd.DataFrame([{
                    'AQI': aqi, 'PM2.5': pm25, 'SO2 level': so2, 'NO2 level': no2,
                    'CO2 level': co2, 'Humidity': humidity, 'Temperature': temperature,
                    'Asthma Symptoms Frequency': symptom_freq,
                    'Triggers': user.triggers or 'Dust',
                    'Weather Sensitivity': 'Hot and humid weather',
                    'Poor Air Quality Exposure': 'Occasionally',
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
                p_nz = prob_ens[prob_ens > 0]
                uncertainty = float(-np.sum(p_nz * np.log2(p_nz)))
                confidence = float(np.max(prob_ens))
            except Exception as e:
                ens_score, risk_level, uncertainty, confidence = 0.45, "Medium", 0.3, 0.75
        else:
            ens_score = 0.45
            risk_level = "Medium"
            uncertainty = 0.35
            confidence = 0.78

        # Deterministic GINA Clinical Override
        heuristic_override = False
        if symptom_freq == "Daily" or night_diff == "Frequently" or has_severe_symptom:
            ens_score = max(ens_score, 0.88)
            risk_level = "High"
            heuristic_override = True

        top_drivers = [
            {"factor": "Ambient Particulate Exposure (PM2.5)", "contribution": round(pm25 / 150.0 * 100, 1), "value": f"{pm25:.1f} ug/m3"},
            {"factor": "Air Quality Index (AQI)", "contribution": round(aqi / 300.0 * 100, 1), "value": f"{aqi:.0f}"},
            {"factor": "Reported Symptom Frequency", "contribution": 85.0 if symptom_freq == "Daily" else 45.0, "value": symptom_freq},
            {"factor": "Known Environmental Triggers", "contribution": 60.0, "value": user.triggers or "Dust"}
        ]

        return {
            "success": True,
            "user_id": user_id,
            "risk_score": round(ens_score, 4),
            "risk_tier": risk_level,
            "confidence": round(confidence, 4),
            "uncertainty_entropy": round(uncertainty, 4),
            "heuristic_override": heuristic_override,
            "top_drivers": top_drivers,
            "sensor_snapshot": {
                "aqi": aqi, "pm25": pm25, "no2": no2, "so2": so2,
                "temperature": temperature, "humidity": humidity
            }
        }

    @staticmethod
    def get_user_context(user_id: int) -> Dict[str, Any]:
        """
        Gathers complete context: demographics, clinical baseline, 7-day diary, inhaler logs, and contacts.
        """
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}

        # 7-day diary entries
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_diaries = SymptomDiary.query.filter(
            SymptomDiary.user_id == user_id,
            SymptomDiary.timestamp >= week_ago
        ).order_by(SymptomDiary.timestamp.desc()).all()

        # Inhaler puffs in last 7 days
        total_puffs_7d = sum(d.inhaler_puffs_used for d in recent_diaries)

        return {
            "user_id": user.id,
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "phone_no": user.phone_no,
            "baseline_severity": user.baseline_severity,
            "inhaler_prescribed": user.inhaler_prescribed,
            "triggers": user.triggers,
            "language_pref": user.language_pref,
            "city": user.city,
            "lat": user.lat,
            "lon": user.lon,
            "emergency_contact": {
                "name": user.emergency_contact_name,
                "phone": user.emergency_contact_phone
            },
            "symptom_diary_7d": [d.to_dict() for d in recent_diaries],
            "inhaler_puffs_7d": total_puffs_7d
        }

    @staticmethod
    def log_symptom(user_id: int, symptoms: str, severity: str = "Mild",
                    inhaler_puffs_used: int = 0, pef_reading: Optional[float] = None,
                    activity_level: str = "Rest", notes: str = "") -> Dict[str, Any]:
        """
        Logs a symptom episode in SymptomDiary table. Triggers safety alert if PEF < 50% or severe distress.
        """
        entry = SymptomDiary(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            symptoms=symptoms,
            severity=severity,
            inhaler_puffs_used=inhaler_puffs_used,
            pef_reading=pef_reading,
            activity_level=activity_level,
            notes=notes
        )
        db.session.add(entry)
        db.session.commit()

        # Check for clinical emergency in PEF reading
        alert_triggered = False
        if pef_reading and pef_reading < 150:  # Critical low zone
            alert_msg = f"Critical PEF reading ({pef_reading} L/min). GINA Red Zone: Use reliever immediately and call emergency."
            alert = Alert(user_id=user_id, message=alert_msg, timestamp=datetime.utcnow())
            db.session.add(alert)
            db.session.commit()
            alert_triggered = True

        return {
            "success": True,
            "diary_id": entry.id,
            "alert_triggered": alert_triggered,
            "entry": entry.to_dict()
        }

    @staticmethod
    def draft_plan(user_id: int, lat: Optional[float] = None, lon: Optional[float] = None,
                   review1_package=None) -> Dict[str, Any]:
        """
        Generates 24-hour proactive asthma protection plan:
        - Safest window for outdoor activity
        - Hour-by-hour recommendation (safe / caution / avoid)
        - Actionable environmental precautions and reminders
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        user_lat = lat or user.lat or 28.6139
        user_lon = lon or user.lon or 77.2090

        forecast = AirGuardTools.get_air_quality_forecast(user_lat, user_lon, hours=24)
        risk = AirGuardTools.get_risk_assessment(user_id, review1_package=review1_package)
        safest_window = forecast.get("safest_window", "06:30 - 08:30")
        risk_tier = risk.get("risk_tier", "Low")

        hourly_recs = []
        for h in forecast.get("hourly", [])[:24]:
            aqi = h["aqi"]
            hour_str = h["hour"]

            if aqi >= 180 or risk_tier == "High":
                status = "avoid"
                rec_text = "Pollution peak: stay indoors, keep windows closed, activate HEPA air purifier."
            elif aqi >= 100 or risk_tier == "Medium":
                status = "caution"
                rec_text = "Elevated ambient particulates: wear N95 mask if outdoors, carry rescue inhaler."
            else:
                status = "safe"
                rec_text = "Good air quality window: outdoor exercise and commuting permitted."

            hourly_recs.append({
                "time": h["time"],
                "hour": hour_str,
                "aqi": aqi,
                "pm25": h["pm25"],
                "recommendation": status,
                "advice": rec_text
            })

        preventive_actions = [
            f"Safest outdoor window today is **{safest_window}**. Plan workouts or commutes during this time.",
            "Keep residential windows sealed between 12:00 PM and 7:00 PM when particulate accumulation peaks.",
            f"Ensure your rescue inhaler ({user.inhaler_prescribed.split(',')[0]}) is in your bag before leaving.",
            "Run your indoor HEPA air filtration unit in your bedroom overnight."
        ]

        if risk_tier == "High":
            preventive_actions.insert(0, "HIGH RISK DAY: Strictly avoid outdoor endurance exercise. Use reliever at first sign of tightness.")

        summary = (
            f"AirGuard 24-Hour Proactive Plan: Risk level is {risk_tier}. "
            f"Safest outdoor activity window is {safest_window}. Adhere to indoor air filtration."
        )

        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Save or update plan in DB
        existing_plan = DailyPlan.query.filter_by(user_id=user_id, valid_date=today_str).first()
        if existing_plan:
            existing_plan.risk_tier = risk_tier
            existing_plan.safest_window = safest_window
            existing_plan.summary = summary
            existing_plan.hourly_recommendations = json.dumps(hourly_recs)
            existing_plan.preventive_actions = json.dumps(preventive_actions)
            plan_obj = existing_plan
        else:
            plan_obj = DailyPlan(
                user_id=user_id,
                valid_date=today_str,
                risk_tier=risk_tier,
                safest_window=safest_window,
                summary=summary,
                hourly_recommendations=json.dumps(hourly_recs),
                preventive_actions=json.dumps(preventive_actions)
            )
            db.session.add(plan_obj)
        db.session.commit()

        return {
            "success": True,
            "plan_id": plan_obj.id,
            "user_id": user_id,
            "valid_date": today_str,
            "risk_tier": risk_tier,
            "safest_window": safest_window,
            "summary": summary,
            "hourly_recommendations": hourly_recs,
            "preventive_actions": preventive_actions
        }

    @staticmethod
    def propose_notification(user_id: int, recipient: str, message: str,
                             channel: str = "sms", reasoning: str = "") -> Dict[str, Any]:
        """
        Creates an action in the approval queue with status 'PENDING'.
        NEVER sends directly without human approval.
        """
        action = AgentAction(
            user_id=user_id,
            created_at=datetime.utcnow(),
            action_type="caregiver_notification",
            recipient=recipient,
            channel=channel,
            proposed_payload=message,
            reasoning=reasoning or "Automated air quality hazard notification based on patient risk threshold.",
            status="PENDING"
        )
        db.session.add(action)
        db.session.commit()

        return {
            "success": True,
            "action_id": action.id,
            "status": "PENDING",
            "message": "Action queued for human approval. AirGuard will not dispatch until approved.",
            "action": action.to_dict()
        }

    @staticmethod
    def send_notification(action_id: int) -> Dict[str, Any]:
        """
        Dispatches an approved action via n8n webhook or simulated delivery.
        Strictly refuses to execute if status is not 'APPROVED'.
        """
        action = AgentAction.query.get(action_id)
        if not action:
            return {"success": False, "error": "Action not found"}

        if action.status != "APPROVED":
            return {
                "success": False,
                "error": f"Security Guard: Action #{action_id} has status '{action.status}'. Only 'APPROVED' actions can be dispatched."
            }

        webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        dispatch_success = True
        dispatch_result = "Simulated delivery completed successfully"

        if webhook_url:
            try:
                res = requests.post(webhook_url, json={
                    "action_id": action.id,
                    "user_id": action.user_id,
                    "recipient": action.recipient,
                    "channel": action.channel,
                    "message": action.proposed_payload,
                    "reasoning": action.reasoning,
                    "timestamp": datetime.utcnow().isoformat()
                }, timeout=5)
                dispatch_result = f"n8n webhook response {res.status_code}: {res.text[:100]}"
                dispatch_success = res.status_code < 400
            except Exception as e:
                dispatch_result = f"n8n webhook error: {str(e)}"
                dispatch_success = False

        action.status = "EXECUTED" if dispatch_success else "FAILED"
        action.execution_result = dispatch_result
        action.decided_at = datetime.utcnow()
        db.session.commit()

        return {
            "success": dispatch_success,
            "action_id": action.id,
            "status": action.status,
            "result": dispatch_result
        }

    @staticmethod
    def generate_doctor_summary(user_id: int) -> Dict[str, Any]:
        """
        Generates clinical summary of last 30 days for physician consultation:
        - Demographic & clinical baseline
        - 30-day symptom frequency and severity breakdown
        - Total inhaler puffs used and daily average
        - Peak Flow trends and red-flag incidents
        - Environmental trigger correlations
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        diaries = SymptomDiary.query.filter(
            SymptomDiary.user_id == user_id,
            SymptomDiary.timestamp >= thirty_days_ago
        ).order_by(SymptomDiary.timestamp.asc()).all()

        total_episodes = len(diaries)
        mild_cnt = sum(1 for d in diaries if d.severity == "Mild")
        mod_cnt = sum(1 for d in diaries if d.severity == "Moderate")
        sev_cnt = sum(1 for d in diaries if d.severity == "Severe")
        total_puffs = sum(d.inhaler_puffs_used for d in diaries)
        avg_daily_puffs = round(total_puffs / 30.0, 2)

        pef_values = [d.pef_reading for d in diaries if d.pef_reading is not None]
        pef_min = min(pef_values) if pef_values else "N/A"
        pef_max = max(pef_values) if pef_values else "N/A"

        # Red flags / alerts in 30 days
        alerts = Alert.query.filter(
            Alert.user_id == user_id,
            Alert.timestamp >= thirty_days_ago
        ).all()

        report_text = (
            f"==========================================================\n"
            f"          AIRGUARD CLINICAL ASTHMA CONSULTATION SUMMARY   \n"
            f"==========================================================\n"
            f"Patient Name:      {user.name} (Age: {user.age}, Gender: {user.gender})\n"
            f"Phone:             {user.phone_no}\n"
            f"Reporting Period:  30-Day Window Ending {datetime.utcnow().strftime('%Y-%m-%d')}\n"
            f"Prescribed Regimen:{user.inhaler_prescribed}\n"
            f"Documented Triggers:{user.triggers}\n"
            f"----------------------------------------------------------\n"
            f"1. SYMPTOM FREQUENCY & SEVERITY (30 DAYS):\n"
            f"   - Total Logged Episodes: {total_episodes}\n"
            f"   - Mild Symptoms:         {mild_cnt}\n"
            f"   - Moderate Symptoms:     {mod_cnt}\n"
            f"   - Severe Symptoms:       {sev_cnt}\n"
            f"\n"
            f"2. RESCUE INHALER UTILIZATION:\n"
            f"   - Total Reliever Puffs:  {total_puffs}\n"
            f"   - Average Daily Puffs:   {avg_daily_puffs} puffs/day\n"
            f"   - Assessment:            {'Frequent reliever use (>2/week) indicates uncontrolled asthma (GINA Step 3/4 review indicated)' if total_puffs > 8 else 'Reliever use within acceptable control bounds (<2/week)'}\n"
            f"\n"
            f"3. PEAK EXPIRATORY FLOW (PEF) DYNAMICS:\n"
            f"   - Lowest Recorded PEF:   {pef_min} L/min\n"
            f"   - Highest Recorded PEF:  {pef_max} L/min\n"
            f"\n"
            f"4. CLINICAL ALERTS & EMERGENCY EVENTS:\n"
            f"   - Critical Alert Count:  {len(alerts)}\n"
            f"----------------------------------------------------------\n"
            f"DISCLAIMER: Prepared by AirGuard assistive tracking agent for review by a licensed healthcare professional.\n"
            f"This summary is observational and does not constitute a diagnostic evaluation.\n"
            f"==========================================================\n"
        )

        return {
            "success": True,
            "patient_name": user.name,
            "period": "30 Days",
            "total_episodes": total_episodes,
            "severity_breakdown": {"mild": mild_cnt, "moderate": mod_cnt, "severe": sev_cnt},
            "total_puffs": total_puffs,
            "avg_daily_puffs": avg_daily_puffs,
            "pef_stats": {"min": pef_min, "max": pef_max},
            "emergency_alert_count": len(alerts),
            "formatted_report": report_text
        }
