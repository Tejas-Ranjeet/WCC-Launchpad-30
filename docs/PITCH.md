# AirGuard Agent — Hackathon Pitch Deck & Technical Dossier
**Event**: WCC Launchpad 30 Hackathon  
**Track**: AGENTIC AI (Healthcare Domain)  
**One-Liner**: *"An autonomous AI agent that turns asthma risk into action — planning the patient's day around air quality, asking for approval before acting, and staying strictly inside deterministic clinical safety rails."*

---

## 1. User Insight (15 Points)

### The Problem: The Passive Healthcare Trap
Over **262 million people live with asthma**, yet 80% of asthma deaths occur in low-to-middle income countries where air pollution surges are common.
Existing digital health tools fail because:
- **Weather apps are passive**: Knowing "AQI is 210" does not help a college student or commuter decide when it is safe to exercise, transit, or ventilate their room.
- **Patients react too late**: Reliever inhalers are taken *during* acute attacks, rather than proactively managing exposure.
- **Doctor visits are hurried**: In 10-minute consultations, doctors lack objective data on how many times a patient suffered symptoms or used their inhaler over the past 30 days.

### The Clinical Insight (GINA 2023 Guidelines)
Asthma attacks are not random; they follow predictable atmospheric and physiological precursors. By combining **predictive 48-hour atmospheric forecasts** with **individual patient history**, an autonomous agent can prevent exacerbations before they begin.

---

## 2. Core Solution (24 Points)

AirGuard is not a passive dashboard and not a chat wrapper. It is an **autonomous agent cycle** operating across six continuous phases:

```
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  SENSE   ├────►│  REASON  ├────►│   PLAN   │
    └──────────┘     └──────────┘     └────┬─────┘
                                           │
    ┌──────────┐     ┌──────────┐          ▼
    │   LOG    │◄────┤   ACT    │◄──── PROPOSE ◄─── [Human Approval Gate]
    └──────────┘     └──────────┘
```

1. **SENSE**: Ingests real-time 48-hour hourly air quality (PM2.5, PM10, NO2, SO2, O3) and weather telemetry from Open-Meteo, cross-referenced with user symptom diaries and peak flow readings.
2. **REASON**: Evaluates exposure risk using our multimodal ensemble model and clinical heuristic rules.
3. **PLAN**: Synthesizes a proactive 24-hour daily timeline, pinpointing the **Safest Clean Air Window** (e.g. 06:30–08:30 AM) and flagging high-risk particulate surges.
4. **PROPOSE**: Queues actionable recommendations (e.g. reschedule outdoor cardio, carry rescue inhaler, alert caregiver) into a **Human-in-the-Loop Approval Queue**.
5. **ACT**: Executes actions **only after explicit human consent** (SMS/WhatsApp dispatch via n8n, calendar schedule adjustment).
6. **LOG**: Records every decision, LLM prompt, and safety verification into a tamper-evident clinical audit trail.

---

## 3. Technical Depth & Reliability (24 Points)

### Dual-Layer Intelligence Architecture
* **Pre-existing Multimodal ML Foundation**: Evaluated transparently on held-out test data (Ensemble: 73.0% Accuracy, 0.7234 F1; Hybrid: 63.7% Accuracy with 82.95% High-Risk Sensitivity). Documented honestly in `LIMITATIONS.md` and calibrated via probability isotonic regression.
* **48-Hour Atmospheric API with Diurnal Fallback**: Live Open-Meteo integration with in-memory TTL caching and a sinusoidal atmospheric inversion fallback ensuring 100% offline availability.
* **Provider-Agnostic LLM Engine**: Native support for Google Gemini, Anthropic Claude, OpenAI, and a zero-dependency deterministic `MOCK` clinical engine that runs anywhere without API keys.
* **Deterministic Safety Rails (The Zero-Trust Barrier)**:
  - **Input Interceptor**: Bypasses the LLM completely upon detecting life-threatening GINA distress phrases in English and Hindi ("can't speak in full sentences", "blue lips", "silent chest", "सांस नहीं आ रही").
  - **Output Sanitizer**: Enforces regex-based post-generation filters that block dosage tampering, diagnostic assertions, and anti-medical claims.
* **Tested Reliability**: 29 automated unit tests verifying every guardrail, multilingual phrase, and approval constraint, plus end-to-end integration tests.

---

## 4. Originality (15 Points)

| Feature | Standard Health Chatbots | Weather / AQI Apps | AirGuard Agent |
| :--- | :--- | :--- | :--- |
| **Interaction Model** | Reactive chat only | Passive static widgets | **Proactive Autonomous Loop** |
| **Action Capability** | None (chat text only) | None | **Executable Actions (SMS, n8n, Plans)** |
| **Safety Governance** | Prompt engineering only | N/A | **Deterministic Dual-Layer Guardrails** |
| **Human Consent** | N/A | N/A | **Zero-Trust Approval Queue** |
| **Clinical Bridge** | Generic advice | None | **30-Day GINA Doctor Consultation Summary** |

---

## 5. Real-World Usability (12 Points)

* **Bilingual English & Hindi Interface**: 1-click toggle dynamically switches the entire UI, prompts, and emergency protocols.
* **Voice-First Input**: Native Web Speech API integration allowing patients in respiratory distress or elderly users to speak naturally.
* **Interactive 24-Hour Timeline**: Color-coded hourly risk trajectory with the cleanest daylight window clearly spotlighted.
* **One-Tap Approval**: Actions appear as interactive cards with clear reasoning and one-tap "Approve & Dispatch" or "Decline" buttons.
* **Doctor Consultation Summary**: Instant generation of standardized 30-day clinical reports that patients can take directly to their pulmonologist.

---

## 6. Responsible Design & Ethics (10 Points)

* **Prominent Non-Diagnostic Disclaimers**: Displayed prominently across the header, plans, doctor reports, and chat responses. AirGuard assists adherence; it never diagnoses.
* **GINA Red Zone Emergency Bypass**: Automatically brings up the emergency SOS modal with direct calling buttons for **112 / 108 Ambulance** and emergency contacts.
* **GDPR & India DPDP Act 2023 Compliance**:
  - Full data portability (`/api/user/export-data/<id>`) allowing patients to download their complete clinical and telemetry history in JSON format.
  - Right to Erasure (`/api/user/delete-account/<id>`) enabling complete and irreversible account and data deletion.
* **No Dark Patterns**: Clear transparency on AI model confidence, risk driver attribution, and reasoning rationale for every single action.

---

## The Hackathon Demo Script & Metrics Summary
- **Live Demo User**: Alex Rivera (29, Moderate Persistent Asthma, Delhi)
- **Pre-seeded Dataset**: 30 days of realistic peak flow records, symptom logs, past executed actions, and 1 fresh pending approval ready for live judging interaction.
- **Test Suite**: 29/29 Passing Unit Tests (`python -m pytest tests/ -v`).
- **One-Command Launch**: `python app.py` running on port 7860.
