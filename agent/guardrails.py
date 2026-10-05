"""
AirGuard Deterministic Clinical Safety Guardrails.
Enforces hard medical boundaries, GINA acute distress protocols, and output sanitization.
Zero dependency on LLM honesty or non-deterministic reasoning.
"""

import re
from typing import Dict, Any, Tuple, List

# ==================== INPUT RED FLAGS (SEVERE RESPIRATORY DISTRESS) ====================

# Intrinsic distress phrases (where negation or inability IS the symptom)
INTRINSIC_DISTRESS_PHRASES = [
    "can't speak in full sentences",
    "cannot speak in full sentences",
    "cant speak in full sentences",
    "cannot speak more than two words",
    "unable to complete sentences",
    "unable to talk",
    "can't speak",
    "cannot speak",
    "cant speak",
    "too breathless to speak",
    "inhaler not working",
    "rescue inhaler not working",
    "reliever not helping",
    "inhaler isn't working",
    "inhaler is not working",
    "inhaler did not help",
    "inhaler not helping",
    "no relief from inhaler",
    "can't breathe",
    "cannot breathe",
    "cant breathe",
    "unable to breathe",
    # Hindi / Hinglish intrinsic
    "saans nahi aa rahi",
    "saans nahi aa rahi hai",
    "saans nahi le pa raha",
    "saans nahi le pa rahi",
    "sans nahi aa rahi",
    "inhaler kaam nahi kar raha",
    "inhaler kam nahi kar raha",
    "inhaler se aaram nahi mila",
    "inhaler se aaram nahi",
    "baat nahi kar pa rahe",
    "bol nahi pa rahe",
    "bol nahi pa raha hu",
    "bol nahi pa raha",
    "saans ukhad rahi",
    "saans ukhad rahi hai",
    "सांस नहीं आ रही",
    "सांस नहीं ले पा रहा",
    "सांस नहीं ले पा रही",
    "बात नहीं कर पा रहे",
    "बोल नहीं पा रहे",
    "बोल नहीं पा रहा",
    "इनहेलर काम नहीं कर रहा",
    "इन्हेलर काम नहीं कर रहा",
    "सांस उखड़ रही",
    "सांस उखड़ रही है"
]

# Physical clinical signs that can be affirmed or negated ("I have blue lips" vs "I do NOT have blue lips")
PHYSICAL_CLINICAL_SIGNS = [
    "blue lips",
    "blue nails",
    "blue fingers",
    "fingers are blue",
    "fingernails are blue",
    "nails are blue",
    "cyanosis",
    "bluish skin",
    "silent chest",
    "stridor",
    "gasping for air",
    "gasping",
    "gasping for breath",
    "severe breathlessness",
    "feeling faint",
    "faint from breathlessness",
    "suffocating",
    "drowning in mucus",
    "chest tightness and sweating",
    "chest tightness with cold sweating",
    "profuse sweating",
    "severe chest pain",
    "loss of consciousness",
    "drowsy and confused",
    "confusion and drowsiness",
    "ribs pulling in",
    "sucking in ribs",
    "sucking in",
    "retractions",
    "intercostal retractions",
    "subcostal retractions",
    "neck muscles straining",
    "struggling to breathe",
    # Hinglish physical signs
    "hoth neele",
    "hoth neele pad rahe",
    "honth neele",
    "honth neele pad rahe",
    "hoth neele pad gaye",
    "lips neele",
    "saans phool rahi",
    "saans phool rahi hai",
    "saans lene me takleef",
    "saans lene me taklif",
    "saans lene me dikkat",
    "sans lene me dikkat",
    "dam ghut raha hai",
    "chhati me tez dard",
    "chhati me jakdan",
    "seene me tez dard",
    "behoshi",
    # Devanagari Hindi physical signs
    "सांस लेने में बहुत तकलीफ",
    "सांस लेने में तकलीफ",
    "सांस फूल रही है",
    "होठ नीले पड़ रहे हैं",
    "होठ नीले",
    "होंठ नीले पड़ रहे हैं",
    "होंठ नीले",
    "नाखून नीले",
    "नाखून नीले हो गए",
    "बेहोश",
    "छाती में तेज दर्द",
    "छाती में बहुत तेज दर्द",
    "जकड़न",
    "दम घुट रहा है"
]

RED_FLAG_KEYWORDS = INTRINSIC_DISTRESS_PHRASES + PHYSICAL_CLINICAL_SIGNS

HINDI_RED_FLAGS = [
    "सांस नहीं आ रही",
    "सांस लेने में बहुत तकलीफ",
    "सांस लेने में तकलीफ",
    "सांस फूल रही है",
    "सांस नहीं ले पा रहा",
    "सांस नहीं ले पा रही",
    "होठ नीले पड़ रहे हैं",
    "होठ नीले",
    "होंठ नीले पड़ रहे हैं",
    "होंठ नीले",
    "बात नहीं कर पा रहे",
    "बोल नहीं पा रहे",
    "इनहेलर काम नहीं कर रहा",
    "बेहोश",
    "छाती में तेज दर्द",
    "दम घुट रहा है"
]

# Patterns for output sanitization
DOSAGE_CHANGE_PATTERNS = [
    re.compile(r'\b(take|increase|double|triple|decrease|reduce|halve)\s+(\d+|\w+)?\s*(p[\.\s_-]*u[\.\s_-]*f[\.\s_-]*f[\.\s_-]*s?|d[\.\s_-]*o[\.\s_-]*s[\.\s_-]*e[\.\s_-]*s?|mg|mcg|tablets?)\b', re.IGNORECASE),
    re.compile(r'\b(increase|raise|boost|bump\s+up|decrease|reduce|halve|cut)\s+.*(dose|dosage|puffs?)\b', re.IGNORECASE),
    re.compile(r'\b(stop|discontinue|cease|quit)\s+(taking|using)?\s*.*(inhaler|medication|steroid|steroids|controller|medicine)\b', re.IGNORECASE),
    re.compile(r'\b(you\s+should\s+stop|do\s+not\s+take|dont\s+take)\s+.*(inhaler|medication|puffs?|steroids|dose)\b', re.IGNORECASE),
    re.compile(r'\b(take|use)\s+\d+\s+extra\s+(puffs?|doses?)\b', re.IGNORECASE),
    re.compile(r'\b(double|triple)\s+(your\s+)?(dose|dosage|puffs?|inhaler)\b', re.IGNORECASE),
    re.compile(r'\b(replace|substitute)\s+(your\s+)?(inhaler|medication)\b', re.IGNORECASE),
    # Hindi dosage patterns
    re.compile(r'(खुराक\s+(बढ़ाएं|घटाएं|दोगुनी|कम\s+करें)|दवा\s+(बंद\s+कर|छोड़|मत\s+लो))', re.IGNORECASE),
    re.compile(r'(dose\s+(badhao|ghatao|double\s+karo)|dawa\s+.*(band\s+karo|band\s+karein|chhod\s+do))', re.IGNORECASE),
    re.compile(r'(dawa\s+lena\s+band)', re.IGNORECASE),
    re.compile(r'(inhaler\s+band\s+kar\s+do)', re.IGNORECASE)
]

DIAGNOSTIC_ASSERTION_PATTERNS = [
    re.compile(r'\b(you have|diagnosed with|diagnosis is|you are suffering from|you definitely have|i diagnose you|confirmed)\s+.*(pneumonia|bronchitis|copd|covid|tuberculosis|heart failure|asthma|emphysema|respiratory\s+distress)\b', re.IGNORECASE),
    re.compile(r'\b(you are cured|asthma is cured|no longer have asthma|cured of asthma|permanently cured|100% cured|cure your asthma|cure)\b', re.IGNORECASE),
    re.compile(r'\b(this is not asthma|you do not have asthma)\b', re.IGNORECASE),
    re.compile(r'\b(i diagnose you|my diagnosis is)\b', re.IGNORECASE),
    # Hindi diagnostic claims
    re.compile(r'(आपको\s+(न्यूमोनिया|ब्रोंकाइटिस|अस्थमा|copd)\s+है|अस्थमा\s+ठीक\s+हो\s+गया\s+है)', re.IGNORECASE),
    re.compile(r'(aapko\s+(asthma|pneumonia|copd)\s+(ho\s+gaya|hai)|asthma\s+(theek|poori\s+tarah\s+theek)\s+ho\s+gaya)', re.IGNORECASE)
]

ANTI_MEDICAL_CARE_PATTERNS = [
    re.compile(r'\b(no need|don\'t need|do not need|dont need|no longer need)\s+to\s+(see a doctor|go to the hospital|visit an emergency room|call emergency|consult a physician|see a doctor or physician)\b', re.IGNORECASE),
    re.compile(r'\b(skip|avoid)\s+(the doctor|the er|the hospital|medical evaluation|your clinic visit)\b', re.IGNORECASE),
    re.compile(r'\b(do not|dont)\s+(go to the hospital|consult your doctor)\b', re.IGNORECASE),
    re.compile(r'\b(no need to consult your doctor)\b', re.IGNORECASE),
    re.compile(r'\byou(\'ll| will) be fine,?\s*(don\'t worry about hospital|no hospital needed)\b', re.IGNORECASE),
    re.compile(r'(डॉक्टर\s+के\s+पास\s+जाने\s+की\s+जरूरत\s+नहीं|अस्पताल\s+मत\s+जाएं)', re.IGNORECASE),
    re.compile(r'(doctor\s+ke\s+paas\s+jaane\s+ki\s+(zaroorat|jaroorat)\s+nahi|hospital\s+mat\s+jaao)', re.IGNORECASE)
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


def _normalize_text(text: str) -> str:
    """Normalizes whitespace and removes excessive punctuation while preserving letters and numbers."""
    if not text:
        return ""
    text = text.lower()
    # Replace punctuation with single spaces except alphanumeric and unicode Hindi
    text = re.sub(r'[^\w\s\u0900-\u097F]', ' ', text)
    # Collapse multiple whitespaces
    return ' '.join(text.split())


def _is_negated(text: str, phrase: str) -> bool:
    """
    Checks if a physical symptom phrase is explicitly negated in the sentence.
    E.g. "I do not have blue lips", "no cyanosis", "without gasping", "honth neele nahi hain".
    """
    # Check leading negation: e.g. "not/no/don't/never/without/nahi [word]{0,3} phrase"
    escaped_phrase = re.escape(phrase)
    leading_neg_pattern = rf'\b(no|not|don\'t|dont|do not|never|without|zero|neither|nahi|nahin|nhi)\s+(?:\w+\s+){{0,3}}{escaped_phrase}\b'
    if re.search(leading_neg_pattern, text, re.IGNORECASE):
        return True

    # Check trailing negation in Hindi/Hinglish: e.g. "phrase nahi/nahin"
    trailing_neg_pattern = rf'\b{escaped_phrase}\s+(?:bhi\s+)?(nahi|nahin|nhi|mat)\b'
    if re.search(trailing_neg_pattern, text, re.IGNORECASE):
        return True

    return False


def check_input_red_flags(user_text: str) -> Dict[str, Any]:
    """
    Scans input for clinical signs of acute severe or life-threatening asthma exacerbation.
    Returns structured safety payload. When tripped, IMMEDIATELY bypasses LLM and triggers Emergency SOS.
    Handles English, Hindi, and Romanized Hindi (Hinglish), punctuation, and negation.
    """
    if not user_text:
        return {"tripped": False, "matched_keywords": [], "emergency_protocol": False}

    cleaned_raw = user_text.lower().strip()
    norm_text = _normalize_text(cleaned_raw)
    matched = []

    # 1. Check Intrinsic Distress Phrases (where negation is part of the emergency, e.g. "can't speak")
    for phrase in INTRINSIC_DISTRESS_PHRASES:
        norm_phrase = _normalize_text(phrase)
        if norm_phrase in norm_text or phrase in cleaned_raw or phrase in user_text:
            matched.append(phrase)

    # Regex for flexible speech or inhaler failures
    if re.search(r'\b(can\'t|cannot|cant|unable to|too breathless to)\s+(speak|talk)\b', norm_text):
        matched.append("speech difficulty (can't speak)")
    if re.search(r'\binhaler\b.*(not working|did not help|not helping|fail|kaam nahi|aaram nahi)\b', norm_text):
        matched.append("inhaler failure")
    if re.search(r'(इनहेलर|इन्हेलर)\b.*(काम नहीं कर रहा|असर नहीं|मदद नहीं)', norm_text) or "इन्हेलर" in norm_text:
        matched.append("इन्हेलर काम नहीं कर रहा")
    if re.search(r'(सांस|साँस)\s+उखड़\s+रही', norm_text):
        matched.append("सांस उखड़ रही है")
    if re.search(r'\b(bol|baat)\s+nahi\s+pa\s+(raha|rahe|rahi)\b', norm_text):
        matched.append("bol nahi pa raha")

    # 2. Check Physical Clinical Signs (e.g. "blue lips", "gasping"), respecting negation
    for phrase in PHYSICAL_CLINICAL_SIGNS:
        norm_phrase = _normalize_text(phrase)
        if norm_phrase in norm_text or phrase in cleaned_raw or phrase in user_text:
            # Check if this occurrence is negated ("I do NOT have blue lips")
            if _is_negated(norm_text, norm_phrase) or _is_negated(cleaned_raw, phrase):
                continue  # Negated: do not trip false positive
            matched.append(phrase)

    # Flexible cyanosis check: lips/fingers/nails + blue/neele unless negated
    if not _is_negated(norm_text, "blue") and not _is_negated(norm_text, "neele"):
        if re.search(r'\b(lips?|nails?|fingers?|hoth|honth|nakhoon|naakhun)\b.*\b(blue|neele|neela)\b|\b(blue|neele|neela)\b.*\b(lips?|nails?|fingers?|hoth|honth|nakhoon|naakhun)\b', norm_text):
            matched.append("cyanosis (blue lips/nails/fingers)")

    # Flexible silent chest check unless negated
    if not _is_negated(norm_text, "silent"):
        if re.search(r'\bchest\b.*\bsilent\b|\bsilent\b.*\bchest\b', norm_text):
            matched.append("silent chest")

    # 3. Check PEF critical zone (< 150 L/min or explicitly noted very low)
    pef_match = re.search(r'\bpef\s*(?:reading)?\s*(?:is|of|at|=)?\s*(\d{2,3})\b', norm_text)
    if pef_match:
        val = int(pef_match.group(1))
        if val <= 150 or "very low" in norm_text:
            matched.append(f"PEF {val} L/min (< 50% critical zone)")

    if matched:
        is_hindi = any(
            any('\u0900' <= char <= '\u097F' for char in m) or
            m in ["saans nahi aa rahi", "hoth neele", "dam ghut raha hai"]
            for m in matched
        )
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


def sanitize_agent_output(llm_output: str, language: str = "en") -> str:
    """Convenience string-to-string sanitizer wrapper for agent output."""
    sanitized, _, _ = sanitize_output(llm_output, language)
    return sanitized
