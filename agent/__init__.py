"""
AirGuard Agent - Proactive Clinical Safety & Action Planning Package.
Turns asthma risk assessments into proactive, human-approved daily actions.
"""

from agent.guardrails import (
    check_input_red_flags,
    sanitize_output,
    RED_FLAG_KEYWORDS,
    HINDI_RED_FLAGS,
    ClinicalSafetyViolation
)
from agent.llm import AirGuardLLM
from agent.tools import AirGuardTools
from agent.loop import AirGuardAgentLoop

__all__ = [
    "check_input_red_flags",
    "sanitize_output",
    "RED_FLAG_KEYWORDS",
    "HINDI_RED_FLAGS",
    "ClinicalSafetyViolation",
    "AirGuardLLM",
    "AirGuardTools",
    "AirGuardAgentLoop"
]
