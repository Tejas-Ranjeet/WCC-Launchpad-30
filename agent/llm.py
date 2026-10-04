"""
AirGuard Provider-Agnostic LLM Client.
Supports Gemini, Anthropic, OpenAI, and a clinical-grade deterministic Mock provider.
Enforces system safety prompts and output sanitization guardrails on all responses.
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from agent.guardrails import sanitize_output, check_input_red_flags

SYSTEM_PROMPT_EN = (
    "You are AirGuard, an assistive AI agent that empowers asthma patients to plan their day safely around air quality. "
    "MANDATORY CLINICAL BOUNDARIES:\n"
    "1. You do NOT make medical diagnoses or claim conditions are cured.\n"
    "2. You NEVER prescribe, increase, decrease, or change medication dosages.\n"
    "3. You remind patients to use their physician-prescribed medications as directed in their personal Asthma Action Plan.\n"
    "4. You suggest practical environmental precautions, timing of outdoor activities, and air filtration.\n"
    "5. If any signs of severe respiratory distress (inability to speak, cyanosis, stridor, PEF < 50%) appear, "
    "instruct the patient immediately to seek emergency medical attention (112 / 108 in India).\n"
    "Always be concise, empathetic, and clinically grounded."
)

SYSTEM_PROMPT_HI = (
    "आप एयरगार्ड हैं, जो अस्थमा रोगियों को वायु गुणवत्ता के अनुसार अपने दिन की सुरक्षित योजना बनाने में मदद करने वाला एक सहायक एआई एजेंट है। "
    "अनिवार्य चिकित्सकीय सीमाएं:\n"
    "1. आप कोई चिकित्सीय निदान नहीं करते हैं और न ही किसी बीमारी के पूरी तरह ठीक होने का दावा करते हैं।\n"
    "2. आप कभी भी दवाओं की खुराक में कोई बदलाव (बढ़ाना या घटाना) नहीं करते हैं।\n"
    "3. आप मरीज को डॉक्टर द्वारा निर्धारित दवाएं समय पर लेने की याद दिलाते हैं।\n"
    "4. आप बाहरी गतिविधियों के सुरक्षित समय और प्रदूषण से बचाव के उपाय सुझाते हैं।\n"
    "5. यदि सांस लेने में गंभीर तकलीफ हो, तो तुरंत आपातकालीन सहायता (112 या 108) लेने का निर्देश दें।"
)

class AirGuardLLM:
    """
    Provider-agnostic LLM interface for AirGuard.
    """
    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER") or "mock").lower()
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

        # Automatically select provider if key is available and provider not forced to mock
        if self.provider == "auto":
            if self.gemini_key:
                self.provider = "gemini"
            elif self.anthropic_key:
                self.provider = "anthropic"
            elif self.openai_key:
                self.provider = "openai"
            else:
                self.provider = "mock"

    def get_provider_name(self) -> str:
        return self.provider.upper()

    def generate_response(self, user_query: str, context: Optional[Dict[str, Any]] = None, language: str = "en") -> Dict[str, Any]:
        """
        Processes a user query with clinical context and returns a sanitized response.
        """
        # Step 1: Input Red-Flag Check (Bypass LLM immediately if emergency)
        red_flag_check = check_input_red_flags(user_query)
        if red_flag_check["tripped"]:
            return {
                "response": red_flag_check["instructions"],
                "provider": "DETERMINISTIC_SAFETY_RAIL",
                "emergency": True,
                "risk_tier": "Emergency",
                "sanitized": False,
                "violations": [],
                "guardrail_tripped": True,
                "details": red_flag_check["reason"]
            }

        context = context or {}
        system_prompt = SYSTEM_PROMPT_HI if language == "hi" else SYSTEM_PROMPT_EN

        raw_output = ""
        used_provider = self.provider

        try:
            if self.provider == "gemini" and self.gemini_key:
                raw_output = self._call_gemini(user_query, context, system_prompt)
            elif self.provider == "anthropic" and self.anthropic_key:
                raw_output = self._call_anthropic(user_query, context, system_prompt)
            elif self.provider == "openai" and self.openai_key:
                raw_output = self._call_openai(user_query, context, system_prompt)
            else:
                raw_output = self._call_mock(user_query, context, language)
                used_provider = "MOCK (Deterministic Clinical Rule Engine)"
        except Exception as e:
            # Fallback to deterministic mock on network or API failure
            raw_output = self._call_mock(user_query, context, language)
            used_provider = f"MOCK_FALLBACK (API Error: {str(e)[:40]})"

        # Step 2: Output Sanitization Guardrail
        sanitized_text, altered, violations = sanitize_output(raw_output, language=language)

        return {
            "response": sanitized_text,
            "provider": used_provider,
            "emergency": False,
            "risk_tier": context.get("risk_tier", "Low"),
            "sanitized": altered,
            "violations": violations,
            "guardrail_tripped": altered,
            "details": "Output sanitized to prevent dosage tampering or non-clinical claim" if altered else "Safe"
        }

    def _call_gemini(self, query: str, context: Dict[str, Any], system_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        prompt_text = f"{system_prompt}\n\nPatient Context:\n{json.dumps(context, indent=2)}\n\nPatient Query: {query}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
        }
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raise RuntimeError(f"Gemini API returned {res.status_code}: {res.text}")

    def _call_anthropic(self, query: str, context: Dict[str, Any], system_prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        prompt_text = f"Patient Context:\n{json.dumps(context, indent=2)}\n\nPatient Query: {query}"
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 400,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data["content"][0]["text"].strip()
        raise RuntimeError(f"Anthropic API returned {res.status_code}: {res.text}")

    def _call_openai(self, query: str, context: Dict[str, Any], system_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{json.dumps(context, indent=2)}\n\nQuery: {query}"}
            ],
            "max_tokens": 400,
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
        raise RuntimeError(f"OpenAI API returned {res.status_code}: {res.text}")

    def _call_mock(self, query: str, context: Dict[str, Any], language: str) -> str:
        """
        High-reliability clinical heuristic generator for mock mode.
        """
        risk_tier = context.get("risk_tier", "Low")
        aqi = context.get("aqi", 85)
        safest_window = context.get("safest_window", "06:30 - 08:30")
        inhaler = context.get("inhaler_prescribed", "prescribed inhaler")
        patient_name = context.get("patient_name", "Patient")

        q_lower = query.lower()

        if language == "hi":
            if "बाहर" in query or "दौड़" in query or "घूम" in query or "walk" in q_lower or "exercise" in q_lower:
                return (
                    f"आज वायु गुणवत्ता सूचकांक (AQI) लगभग {aqi} रहने का अनुमान है। "
                    f"बाहरी गतिविधियों के लिए सबसे सुरक्षित समय **{safest_window}** है। "
                    f"कृपया बाहर जाते समय N95 मास्क पहनें और अपना {inhaler} हमेशा साथ रखें।"
                )
            return (
                f"नमस्ते {patient_name}। आपका अनुमानित जोखिम स्तर **{risk_tier}** है (AQI: {aqi})। "
                f"सर्वोत्तम सुरक्षा के लिए खिड़कियां बंद रखें और अपने डॉक्टर की योजना अनुसार {inhaler} का उपयोग करें। "
                f"यदि सांस फूलने की समस्या हो तो तुरंत अपने रिलीवर इनहेलर का उपयोग करें।"
            )

        # English responses
        if any(w in q_lower for w in ["jog", "run", "walk", "exercise", "outside", "outdoor", "park"]):
            return (
                f"Based on the 48-hour air quality forecast (Current AQI: {aqi}), your safest outdoor window today is **{safest_window}**. "
                f"During midday and evening rush hours, particulate matter peaks significantly. If you exercise outdoors, "
                f"keep your session within the safe window, keep your rescue inhaler ({inhaler}) accessible, and consider an N95 respirator if traffic is heavy."
            )
        elif any(w in q_lower for w in ["inhaler", "puff", "dose", "medicine", "medication"]):
            return (
                f"Please adhere strictly to your personal Asthma Action Plan as prescribed by your doctor ({inhaler}). "
                f"I cannot alter medication dosages or timing. Remember to use a spacer if prescribed to ensure optimal lung deposition, "
                f"and log every reliever puff in your AirGuard diary."
            )
        elif any(w in q_lower for w in ["plan", "today", "schedule", "routine", "advice"]):
            return (
                f"AirGuard Daily Plan Summary for {patient_name}:\n"
                f"- Risk Level: **{risk_tier}** (Ambient AQI: {aqi})\n"
                f"- Safest Outdoor Window: **{safest_window}**\n"
                f"- Environmental Advice: Run HEPA air purifier indoors; seal windows between 12:00 and 19:00 during pollution peak.\n"
                f"- Action: Keep your rescue inhaler within arm's reach."
            )
        else:
            return (
                f"Hello {patient_name}. Your current asthma risk tier is **{risk_tier}** with an ambient AQI of {aqi}. "
                f"Your safest window for outdoor tasks is **{safest_window}**. Please ensure you have your {inhaler} with you. "
                f"If you experience any chest tightness or wheezing, pause activity immediately and follow your medical action plan."
            )
