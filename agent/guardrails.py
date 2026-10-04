"""
AirGuard Deterministic Clinical Safety Guardrails.
Enforces hard medical boundaries, GINA acute distress protocols, and output sanitization.
Zero dependency on LLM honesty or non-deterministic reasoning.
"""

import re
from typing import Dict, Any, Tuple, List

# ==================== INPUT RED FLAGS (SEVERE RESPIRATORY DISTRESS) ====================

RED_FLAG_KEYWORDS = [
    # GINA Red-Flag Clinical Signs of Life-Threatening Asthma
    "can't speak in full sentences",
    "cannot speak in full sentences",
    "unable to complete sentences",
    "unable to talk",
    "blue lips",
    "blue nails",
    "cyanosis",
    "bluish skin",
    "silent chest",
    "stridor",
    "gasping for air",
    "gasping",
    "pef < 50",
    "pef below 50",
    "peak flow < 50",
    "peak flow below 50",
    "inhaler not working",
    "rescue inhaler not working",
    "reliever not helping",
    "inhaler isn't working",
    "no relief from inhaler",
    "struggling to breathe",
    "can't breathe",
    "cannot breathe",
    "severe breathlessness",
    "suffocating",
    "drowning in mucus",
    "chest tightness and sweating",
    "severe chest pain",
    "loss of consciousness",
    "drowsy and confused",
    "confusion and drowsiness",
    "ribs pulling in",
    "subcostal retractions",
    "neck muscles straining"
]

HINDI_RED_FLAGS = [
    "सांस नहीं आ रही",
    "सांस लेने में बहुत तकलीफ",
    "सांस लेने में तकलीफ",
    "सांस फूल रही है",
    "सांस नहीं ले पा रहा",
    "सांस नहीं ले पा रही",
    "होठ नीले पड़ रहे हैं",
    "होठ नीले",
    "बात नहीं कर पा रहे",
    "बोल नहीं पा रहे",
    "इनहेलर काम नहीं कर रहा",
    "बेहोश",
    "छाती में तेज दर्द",
    "दम घुट रहा है"
]

# Patterns for output sanitization
DOSAGE_CHANGE_PATTERNS = [
    re.compile(r'\b(take|increase|double|triple|decrease|reduce)\s+(\d+|\w+)?\s*(puffs?|doses?|mg|tablets?)\s+instead\b', re.IGNORECASE),
    re.compile(r'\b(increase|raise|boost|bump\s+up)\s+(your\s+)?(dose|dosage|puffs?)\s+to\b', re.IGNORECASE),
    re.compile(r'\b(stop|discontinue|cease|quit)\s+(taking|using)?\s*(your\s+)?(inhaler|medication|steroid|controller|medicine)\b', re.IGNORECASE),
    re.compile(r'\b(take|inhale|administer)\s+([3-9]|\d{2,})\s+puffs\b', re.IGNORECASE),
    re.compile(r'\b(take|use)\s+\d+\s+extra\s+puffs\b', re.IGNORECASE),
    # Hindi dosage patterns
    re.compile(r'(खुराक\s+(बढ़ाएं|घटाएं|दोगुनी|कम\s+करें)|दवा\s+(बंद\s+कर|छोड़|मत\s+लो))', re.IGNORECASE),
]

DIAGNOSTIC_ASSERTION_PATTERNS = [
    re.compile(r'\b(you have|diagnosed with|diagnosis is|you are suffering from|you definitely have)\s+(pneumonia|bronchitis|copd|covid|tuberculosis|heart failure)\b', re.IGNORECASE),
    re.compile(r'\b(you are cured|asthma is cured|no longer have asthma|cured of asthma)\b', re.IGNORECASE),
    re.compile(r'\b(this is not asthma|you do not have asthma)\b', re.IGNORECASE),
    re.compile(r'\b(i diagnose you|my diagnosis is)\b', re.IGNORECASE),
    # Hindi diagnostic claims
    re.compile(r'(आपको\s+(न्यूमोनिया|ब्रोंकाइटिस)\s+है|अस्थमा\s+ठीक\s+हो\s+गया\s+है)', re.IGNORECASE)
]

ANTI_MEDICAL_CARE_PATTERNS = [
    re.compile(r'\b(no need|don\'t need|do not need)\s+to\s+(see a doctor|go to the hospital|visit an emergency room|call emergency|consult a physician)\b', re.IGNORECASE),
    re.compile(r'\b(skip|avoid)\s+(the doctor|the er|the hospital|medical evaluation)\b', re.IGNORECASE),
    re.compile(r'\byou(\'ll| will) be fine,?\s*(don\'t worry about hospital|no hospital needed)\b', re.IGNORECASE),
    re.compile(r'(डॉक्टर\s+के\s+पास\s+जाने\s+की\s+जरूरत\s+नहीं|अस्पताल\s+मत\s+जाएं)', re.IGNORECASE)
]

SAFE_FALLBACK_RESPONSE = (
    "AirGuard Clinical Safety Notice: I am an AI assistive tool and cannot adjust prescription "
    "medication dosages, declare medical diagnoses, or advise against professional medical evaluation. "
    "Please follow your prescribed Asthma Action Plan. If you are experiencing severe breathing difficulty, "
    "stridor, inability to speak, or if your reliever inhaler is not providing relief, please call emergency "
    "services immediately (112 or 108 in India / local emergency dispatch) or proceed to the nearest emergency department."
)

SAFE_FALLBACK_HINDI = (
    "एयरगार्ड क्लिनिकल सुरक्षा सूचना: मैं एक सहायक एआई टूल हूँ और डॉक्टर द्वारा लिखी गई दवाओं की खुराक "
    "बदलने या कोई चिकित्सकीय निदान करने के लिए अधिकृत नहीं हूँ। कृपया अपने डॉक्टर द्वारा दी गई कार्ययोजना का पालन करें। "
    "यदि आपको सांस लेने में अत्यधिक कठिनाई हो रही है या इनहेलर काम नहीं कर रहा है, तो तुरंत आपातकालीन सेवा "
    "(112 या 108) पर कॉल करें या निकटतम अस्पताल जाएं।"
)

class ClinicalSafetyViolation(Exception):
    """Raised when deterministic clinical safety rail is triggered."""
    def __init__(self, message: str, rail_type: str, matched_text: str):
        super().__init__(message)
        self.rail_type = rail_type
        self.matched_text = matched_text


def check_input_red_flags(user_text: str) -> Dict[str, Any]:
    """
    Scans input for clinical signs of acute severe or life-threatening asthma exacerbation.
    Returns structured safety payload. When tripped, IMMEDIATELY bypasses LLM and triggers Emergency SOS.
    """
    if not user_text:
        return {"tripped": False, "matched_keywords": [], "emergency_protocol": False}

    cleaned_text = user_text.lower().strip()
    matched = []

    # Check English red flags
    for phrase in RED_FLAG_KEYWORDS:
        if phrase in cleaned_text:
            matched.append(phrase)

    # Check Hindi red flags
    for phrase in HINDI_RED_FLAGS:
        if phrase in user_text:
            matched.append(phrase)

    # Check PEF < 50 pattern with regex
    pef_match = re.search(r'\bpef\s*(?:reading)?\s*(?:is|of|at|=)?\s*(\d{2,3})\b', cleaned_text)
    if pef_match:
        val = int(pef_match.group(1))
        if val < 50:
            matched.append(f"PEF {val} L/min (< 50% critical zone)")

    if matched:
        is_hindi = any(m in HINDI_RED_FLAGS for m in matched)
        instruction = (
            "🚨 CRITICAL AIRWAY DISTRESS DETECTED: Sit upright. Use fast-acting reliever inhaler "
            "(2 to 4 puffs immediately with spacer). Call emergency services (112 / 108) or notify your emergency contact right now."
            if not is_hindi else
            "🚨 गंभीर श्वसन आपातकाल: सीधे बैठें। तुरंत रिलीवर इनहेलर (2 से 4 पफ) लें। आपातकालीन नंबर (112 / 108) पर कॉल करें।"
        )

        return {
            "tripped": True,
            "matched_keywords": matched,
            "emergency_protocol": True,
            "action": "EMERGENCY_OVERRIDE",
            "risk_tier": "Emergency",
            "reason": f"Deterministic safety rail triggered by acute distress indicator: {', '.join(matched)}",
            "instructions": instruction,
            "emergency_numbers": ["112", "108"],
            "requires_human_ack": True
        }

    return {
        "tripped": False,
        "matched_keywords": [],
        "emergency_protocol": False,
        "action": "PROCEED",
        "risk_tier": None,
        "reason": "No critical acute red flags detected in input."
    }


def sanitize_output(llm_output: str, language: str = "en") -> Tuple[str, bool, List[str]]:
    """
    Sanitizes LLM-generated text against medication adjustment, diagnostic claims,
    and anti-medical advice.
    Returns: (sanitized_text, was_altered, reasons_list)
    """
    if not llm_output:
        return "", False, []

    violations = []

    for pat in DOSAGE_CHANGE_PATTERNS:
        match = pat.search(llm_output)
        if match:
            violations.append(f"Medication dosage change detected: '{match.group(0)}'")

    for pat in DIAGNOSTIC_ASSERTION_PATTERNS:
        match = pat.search(llm_output)
        if match:
            violations.append(f"Diagnostic claim detected: '{match.group(0)}'")

    for pat in ANTI_MEDICAL_CARE_PATTERNS:
        match = pat.search(llm_output)
        if match:
            violations.append(f"Advising against medical attention detected: '{match.group(0)}'")

    if violations:
        fallback = SAFE_FALLBACK_HINDI if language == "hi" else SAFE_FALLBACK_RESPONSE
        sanitized = f"{fallback}\n\n[Safety Rail Triggered: {'; '.join(violations)}]"
        return sanitized, True, violations

    return llm_output, False, []
