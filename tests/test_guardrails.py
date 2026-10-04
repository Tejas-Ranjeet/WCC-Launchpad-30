"""
AirGuard Clinical Safety Guardrails Test Suite.
Verifies that deterministic rules strictly trap life-threatening inputs and illegal LLM medical outputs,
while avoiding false positives on benign symptom logs.
"""

import pytest
from agent.guardrails import (
    check_input_red_flags,
    sanitize_output,
    RED_FLAG_KEYWORDS,
    HINDI_RED_FLAGS
)

# ==================== INPUT RED FLAGS (CRITICAL ACUTE DISTRESS) ====================

def test_english_red_flag_cant_speak():
    res = check_input_red_flags("The patient can't speak in full sentences and is gasping.")
    assert res["tripped"] is True
    assert res["emergency_protocol"] is True
    assert res["risk_tier"] == "Emergency"
    assert any("can't speak in full sentences" in k for k in res["matched_keywords"])

def test_english_red_flag_blue_lips():
    res = check_input_red_flags("His oxygen seems low and he has blue lips and cold hands.")
    assert res["tripped"] is True
    assert "blue lips" in res["matched_keywords"]

def test_english_red_flag_silent_chest():
    res = check_input_red_flags("Severe wheezing stopped suddenly, doctor noted silent chest.")
    assert res["tripped"] is True
    assert "silent chest" in res["matched_keywords"]

def test_english_red_flag_inhaler_not_working():
    res = check_input_red_flags("Took 4 puffs but inhaler not working, chest still tight.")
    assert res["tripped"] is True
    assert "inhaler not working" in res["matched_keywords"]

def test_english_red_flag_struggling_to_breathe():
    res = check_input_red_flags("I am struggling to breathe after going outside in smoke.")
    assert res["tripped"] is True
    assert "struggling to breathe" in res["matched_keywords"]

def test_english_red_flag_chest_tightness_and_sweating():
    res = check_input_red_flags("Patient has chest tightness and sweating profusely.")
    assert res["tripped"] is True
    assert "chest tightness and sweating" in res["matched_keywords"]

def test_english_red_flag_pef_critical():
    res = check_input_red_flags("My PEF 45 reading today morning.")
    assert res["tripped"] is True
    assert any("PEF 45" in k for k in res["matched_keywords"])

def test_hindi_red_flag_sans_nahi_aa_rahi():
    res = check_input_red_flags("मरीज को सांस नहीं आ रही है, बहुत घबराहट हो रही है।")
    assert res["tripped"] is True
    assert "सांस नहीं आ रही" in res["matched_keywords"]

def test_hindi_red_flag_inhaler_fail():
    res = check_input_red_flags("इनहेलर काम नहीं कर रहा और दम घुट रहा है")
    assert res["tripped"] is True
    assert "इनहेलर काम नहीं कर रहा" in res["matched_keywords"]
    assert "दम घुट रहा है" in res["matched_keywords"]

def test_hindi_red_flag_lips_blue():
    res = check_input_red_flags("बच्चे के होठ नीले पड़ रहे हैं")
    assert res["tripped"] is True
    assert "होठ नीले पड़ रहे हैं" in res["matched_keywords"]

def test_benign_input_no_false_positive():
    # Benign routine symptom updates should NOT trip emergency
    res = check_input_red_flags("I had a mild cough yesterday evening after walking through dust.")
    assert res["tripped"] is False
    assert res["emergency_protocol"] is False
    assert res["action"] == "PROCEED"

def test_benign_inhaler_routine_log():
    res = check_input_red_flags("Logged morning maintenance inhaler dose, feeling stable.")
    assert res["tripped"] is False

# ==================== OUTPUT SANITIZATION FILTER ====================

def test_output_blocks_dosage_increase():
    llm_text = "Your symptoms are worsening, so please increase your dose to 4 puffs twice daily."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert len(violations) > 0
    assert "Medication dosage change detected" in violations[0]
    assert "AirGuard Clinical Safety Notice" in sanitized

def test_output_blocks_dosage_replacement():
    llm_text = "You should take 2 puffs instead of 1 before going out."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert "Medication dosage change detected" in violations[0]

def test_output_blocks_stop_medication():
    llm_text = "Your AQI is good today, so you can stop taking your inhaler."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert "stop" in violations[0]

def test_output_blocks_diagnostic_claim():
    llm_text = "Based on your wheezing and fever, you have pneumonia."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert "Diagnostic claim detected" in violations[0]

def test_output_blocks_cured_claim():
    llm_text = "Great news! Since you had no cough for a week, you are cured of asthma."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert "Diagnostic claim detected" in violations[0]

def test_output_blocks_anti_medical_advice():
    llm_text = "Even if you feel short of breath, there is no need to see a doctor or go to the ER."
    sanitized, altered, violations = sanitize_output(llm_text)
    assert altered is True
    assert "Advising against medical attention detected" in violations[0]

def test_output_blocks_hindi_dosage_tampering():
    llm_text = "अगर खांसी बढ़े तो दवा की खुराक बढ़ाएं।"
    sanitized, altered, violations = sanitize_output(llm_text, language="hi")
    assert altered is True
    assert len(violations) > 0
    assert "एयरगार्ड क्लिनिकल सुरक्षा सूचना" in sanitized

def test_output_allows_valid_assistive_recommendation():
    # Valid advice should pass through untouched
    valid_text = (
        "Air quality in Delhi is forecast to reach AQI 185 by 14:00. "
        "We recommend scheduling your outdoor jog during the safest window (06:30 - 08:30). "
        "Keep windows closed in the afternoon, run your HEPA air purifier, and always carry your prescribed rescue inhaler."
    )
    sanitized, altered, violations = sanitize_output(valid_text)
    assert altered is False
    assert len(violations) == 0
    assert sanitized == valid_text
