# AirGuard Agent — Hackathon Pitch Deck & Technical Dossier
**Event**: WCC Launchpad 30 Hackathon  
**Track**: AGENTIC AI (Healthcare Domain)  
**One-Liner**: *"An autonomous AI agent that turns asthma risk into action — planning the patient's day around air quality, asking for approval before acting, and staying strictly inside deterministic clinical safety rails."*

---

## 1. User Insight (15 Points)

### The Real Problem: Chronic Respiratory Vulnerability & Clinical Triage Realities
Over **262 million people live with asthma** (WHO), yet 80% of deaths occur in low-and-middle-income countries where seasonal smog spikes and particulate volatility are acute. AirGuard addresses critical behavioral and clinical gaps identified across chronic respiratory literature:

1. **The Passive Trap**: Patients typically only check AQI *after* coughing, wheezing, or chest tightness begins. Passive weather widgets fail because they report conditions without changing proactive behavior.
2. **Deceptive Clear Mornings**: Patients frequently leave rescue inhalers at home on mornings when the air looks deceptively clear, only to suffer an acute attack during evening rush-hour smog inversions.
3. **The Autonomy Boundary**: Patients and caregivers consistently insist on retaining final control over their care. Autonomous agents that send alerts or reschedule commitments without explicit permission erode user trust.
4. **The Doctor Recall Void**: Under Global Initiative for Asthma (GINA) guidelines, using a reliever inhaler >2 times per week indicates uncontrolled asthma requiring therapy escalation. Yet patients routinely struggle to recall exact 30-day symptom and puff counts during brief consultations.

*(Note: Real evidence collection framework and hypothetical design personas are documented in [`docs/user_research.md`](docs/user_research.md)).*

---

## 2. Core Solution (24 Points)

AirGuard is not a passive dashboard and not a chat wrapper. It is an **autonomous agent cycle** operating across six continuous phases:

```
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  SENSE   ├────►│  REASON  ├────►│   PLAN   │
    └──────────┘     └──────────┘     └────┬─────┘
                                           │
    ┌──────────┐     ┌──────────┐          ▼
    │   LOG    │◄────┤   ACT    │◄──── PROPOSE ◄─── [Zero-Trust Human Gate]
    └──────────┘     └──────────┘
```

1. **SENSE**: Ingests 48-hour live hourly air quality (PM2.5, PM10, NO2, SO2, O3) and weather from Open-Meteo (with an automatic offline diurnal fallback), cross-referenced with the patient's symptom diary and peak flow readings.
2. **REASON**: Evaluates exposure risk using our multimodal ensemble model and clinical heuristic rules.
3. **PLAN**: Synthesizes a proactive 24-hour daily timeline, pinpointing the **Safest Clean Air Window** (e.g. 06:30–08:30 AM) and highlighting dangerous evening smog inversions.
4. **PROPOSE**: Queues actionable recommendations (e.g. reschedule outdoor cardio, carry rescue inhaler, alert caregiver) into a **Human-in-the-Loop Approval Queue**.
5. **ACT**: Executes actions **only after explicit human consent** (SMS/WhatsApp dispatch via n8n, calendar schedule adjustment).
6. **LOG**: Records every decision, LLM prompt, and safety verification into a tamper-evident clinical audit trail.

---

## 3. Technical Depth & Reliability (24 Points)

### Honest ML Science & The Clinical Safety Trade-off
We evaluated our pre-existing multimodal stacking ensemble on held-out test data ($N=300$ samples, evaluated via `research/evaluate.py`):
- **Pure ML Ensemble**: **73.0% Accuracy**, **0.7234 Macro F1**, **0.8496 Multiclass AUC**, with **68.18% High-Risk Sensitivity**.
- **Hybrid Clinical Rule Override**: **63.67% Accuracy**, with High-Risk Sensitivity surging to **82.95%**.
- **The Deliberate Trade-Off**: It trades accuracy (73.0% -> 63.67%) for higher high-risk sensitivity (~83%) by design. In healthcare triage:
  > *"A false alarm causes minor schedule inconvenience. A false negative lands the patient in the ICU. We accept more false alarms to miss fewer emergencies."*

### Resilient Architecture
- **Live Atmospheric API with Offline Fallback**: Live Open-Meteo connection with 10-minute TTL caching and an automatic diurnal simulation fallback. (The UI visibly badges whether data is live or simulated fallback).
- **Provider-Agnostic LLM Engine**: Supports Google Gemini, Anthropic Claude, OpenAI, and an offline deterministic `MOCK` clinical engine that runs anywhere without API keys.
- **Deterministic Safety Rails (The Zero-Trust Barrier)**:
  - **Input Interceptor**: Bypasses the LLM completely upon detecting life-threatening GINA distress phrases in English and Hindi (*"can't speak in full sentences"*, *"blue lips"*, *"silent chest"*, *"सांस नहीं आ रही"*, *"होंठ नीले"*).
  - **Output Sanitizer**: Enforces regex-based post-generation filters that block dosage tampering, diagnostic assertions, and anti-medical claims.
- **Automated Test Suite**: 29 automated unit tests verifying every guardrail, multilingual phrase, and approval constraint, plus end-to-end integration tests.

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
* **Privacy by Design (India DPDP & GDPR Principles)**:
  - Supports full patient data portability (`/api/user/export-data/<id>`) allowing patients to download their complete clinical and telemetry history in JSON format.
  - Supports Right to Erasure (`/api/user/delete-account/<id>`) enabling complete and permanent data deletion.
* **Transparent Attribution & Data Provenance**: Clear badges in the UI indicating whether environmental data is from live Open-Meteo stations or simulated fallback, and clearly labeling synthetic demo patient profiles.

---

## Hackathon Verification Checklist
- **Demo Patient**: Alex Rivera (Age 29, Moderate Persistent Asthma, Delhi — clearly badged as a seeded demo profile).
- **Test Suite**: 29/29 Passing Unit Tests (`python -m pytest tests/ -v`).
- **Live Local Run**: `python app.py` running on port 7860.
