"""
AirGuard Agent Autonomous Decision Loop.
Orchestrates: SENSE -> REASON -> PLAN -> PROPOSE -> ACT -> LOG.
Enforces deterministic safety overrides and human-in-the-loop approval on all external actions.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from models import db, User, AgentAction, AgentLog, Alert
from agent.tools import AirGuardTools
from agent.llm import AirGuardLLM
from agent.guardrails import check_input_red_flags

class AirGuardAgentLoop:
    """
    Main AirGuard Agent decision engine.
    """
    def __init__(self, review1_package=None, llm_provider: Optional[str] = None):
        self.review1_package = review1_package
        self.llm = AirGuardLLM(provider=llm_provider)

    def run_cycle(self, user_id: int, trigger: str = "forecast_update",
                  user_query: Optional[str] = None, lat: Optional[float] = None,
                  lon: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes one full AirGuard cycle for the given user.
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": f"User ID {user_id} not found"}

        user_lat = lat or user.lat or 28.6139
        user_lon = lon or user.lon or 77.2090
        language = user.language_pref or "en"

        # ==================== STEP 1: SENSE ====================
        user_context = AirGuardTools.get_user_context(user_id)
        forecast = AirGuardTools.get_air_quality_forecast(user_lat, user_lon, hours=24)
        risk_data = AirGuardTools.get_risk_assessment(user_id, review1_package=self.review1_package)

        input_state = {
            "user_id": user_id,
            "patient_name": user.name,
            "city": user.city,
            "baseline_severity": user.baseline_severity,
            "prescribed_inhaler": user.inhaler_prescribed,
            "risk_score": risk_data.get("risk_score", 0.45),
            "risk_tier": risk_data.get("risk_tier", "Low"),
            "current_aqi": risk_data.get("sensor_snapshot", {}).get("aqi", 85),
            "current_pm25": risk_data.get("sensor_snapshot", {}).get("pm25", 35.0),
            "safest_window": forecast.get("safest_window", "06:30 - 08:30"),
            "user_query": user_query
        }

        # ==================== SAFETY CHECK (INPUT RED FLAGS) ====================
        guardrail_tripped = False
        guardrail_details = None

        if user_query:
            red_flag = check_input_red_flags(user_query)
            if red_flag["tripped"]:
                guardrail_tripped = True
                guardrail_details = red_flag["reason"]
                emergency_alert = Alert(
                    user_id=user_id,
                    message=f"CRITICAL RED-FLAG TRIGGERED: {red_flag['reason']}. Emergency SOS protocol activated.",
                    timestamp=datetime.utcnow()
                )
                db.session.add(emergency_alert)
                db.session.commit()

                # Log emergency run
                self._write_audit_log(
                    user_id=user_id,
                    trigger=trigger,
                    input_state=input_state,
                    reasoning=f"EMERGENCY OVERRIDE: {red_flag['reason']}",
                    actions_proposed=[{"type": "emergency_sos", "status": "IMMEDIATE_ACTION"}],
                    guardrail_tripped=True,
                    guardrail_details=guardrail_details
                )

                return {
                    "success": True,
                    "cycle_status": "EMERGENCY_OVERRIDE",
                    "emergency": True,
                    "risk_tier": "Emergency",
                    "response": red_flag["instructions"],
                    "actions_proposed": [],
                    "guardrail_tripped": True,
                    "reasoning": red_flag["reason"]
                }

        # ==================== STEP 2: REASON ====================
        risk_tier = risk_data.get("risk_tier", "Low")
        peak_aqi = max([h["aqi"] for h in forecast.get("hourly", [])[:24]] or [100])
        safest_window = forecast.get("safest_window", "06:30 - 08:30")

        reasoning_points = [
            f"Evaluated multimodal ML ensemble score: {risk_data.get('risk_score', 0):.2f} (Tier: {risk_tier}).",
            f"24-hour environmental forecast predicts peak AQI of {peak_aqi} with lowest particulate window between {safest_window}."
        ]

        if risk_data.get("heuristic_override"):
            reasoning_points.append("GINA heuristic safety rule overrode baseline risk due to documented symptom severity.")

        if risk_tier in ["High", "Medium"] or peak_aqi >= 150:
            reasoning_points.append("High ambient exposure risk detected: Caregiver safety notification and calendar schedule adjustment recommended.")

        full_reasoning = " ".join(reasoning_points)

        # ==================== STEP 3: PLAN ====================
        plan_result = AirGuardTools.draft_plan(user_id, lat=user_lat, lon=user_lon, review1_package=self.review1_package)

        # Generate LLM advice or response if query is present
        query_to_run = user_query or "Please review my asthma plan and give me personalized advice for today."
        llm_result = self.llm.generate_response(
            user_query=query_to_run,
            context={
                "patient_name": user.name,
                "risk_tier": risk_tier,
                "aqi": input_state["current_aqi"],
                "safest_window": safest_window,
                "inhaler_prescribed": user.inhaler_prescribed
            },
            language=language
        )

        if llm_result.get("guardrail_tripped"):
            guardrail_tripped = True
            guardrail_details = "; ".join(llm_result.get("violations", []))

        # ==================== STEP 4: PROPOSE (APPROVAL QUEUE) ====================
        # Propose actions that require patient consent (never auto-execute)
        proposed_actions = []

        if risk_tier == "High" or peak_aqi >= 160:
            # Check if there is already a pending caregiver alert to avoid duplicates
            existing_pending = AgentAction.query.filter_by(
                user_id=user_id,
                action_type="caregiver_notification",
                status="PENDING"
            ).first()

            if not existing_pending:
                cg_msg = (
                    f"AirGuard Health Notice: Air pollution in {user.city} is reaching AQI {peak_aqi} today. "
                    f"{user.name}'s asthma risk is currently HIGH. Please ensure they remain indoors and have rescue medication nearby."
                )
                action_prop = AirGuardTools.propose_notification(
                    user_id=user_id,
                    recipient=f"{user.emergency_contact_name} ({user.emergency_contact_phone})",
                    message=cg_msg,
                    channel="sms",
                    reasoning=f"High risk forecast (Peak AQI {peak_aqi}). Caregiver awareness minimizes delay in acute events."
                )
                proposed_actions.append(action_prop.get("action"))

        # ==================== STEP 5: ACT (SAFE NON-CRITICAL EXECUTION) ====================
        # Non-critical actions (updating the daily plan, logging telemetry) are completed automatically.
        # Critical actions remain PENDING in the approval queue.

        # ==================== STEP 6: LOG (AUDIT TRAIL) ====================
        log_entry = self._write_audit_log(
            user_id=user_id,
            trigger=trigger,
            input_state=input_state,
            reasoning=full_reasoning,
            actions_proposed=proposed_actions,
            guardrail_tripped=guardrail_tripped,
            guardrail_details=guardrail_details
        )

        return {
            "success": True,
            "cycle_status": "COMPLETED",
            "emergency": False,
            "risk_tier": risk_tier,
            "risk_score": risk_data.get("risk_score"),
            "current_aqi": input_state["current_aqi"],
            "safest_window": safest_window,
            "plan": plan_result,
            "agent_response": llm_result["response"],
            "llm_provider": llm_result.get("provider"),
            "proposed_actions": proposed_actions,
            "guardrail_tripped": guardrail_tripped,
            "guardrail_details": guardrail_details,
            "log_id": log_entry.id if log_entry else None
        }

    def _write_audit_log(self, user_id: int, trigger: str, input_state: Dict[str, Any],
                         reasoning: str, actions_proposed: list, guardrail_tripped: bool,
                         guardrail_details: Optional[str]) -> Optional[AgentLog]:
        try:
            log_record = AgentLog(
                user_id=user_id,
                timestamp=datetime.utcnow(),
                trigger=trigger,
                input_state=json.dumps(input_state),
                reasoning=reasoning,
                actions_proposed=json.dumps(actions_proposed) if actions_proposed else "[]",
                guardrail_tripped=guardrail_tripped,
                guardrail_details=guardrail_details
            )
            db.session.add(log_record)
            db.session.commit()
            return log_record
        except Exception as e:
            db.session.rollback()
            return None
