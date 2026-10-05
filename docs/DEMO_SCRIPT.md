# AirGuard Agent — 3-Minute Live Hackathon Demo Script

**Total Duration**: 3 Minutes (180 Seconds)  
**Presenter**: Lead Engineer / Pitcher  
**Screen Setup**: Browser open to `http://localhost:7860`, logged in as **Alex Rivera** (`alex@example.com` / `demo123`).

---

## ⏱️ 0:00 – 0:30 | The Hook: Validated by Real Patient Research
**Screen Action**: Show traditional weather app widget or dashboard with "AQI 210".  
**Spoken Script**:
> "Judges, over 260 million people live with asthma. Clinical studies and GINA guidelines show that patients typically check air quality only *after* symptoms begin, and frequently forget rescue inhalers on mornings when the air 'looks clear'.
> Passive numbers don't prevent asthma attacks.
> A patient doesn't need another scary number. They need to know: *Can I go for my run? What time is safe to step outside? Did I remember my inhaler?*
> Today, we present **AirGuard Agent** — an autonomous AI agent that turns asthma risk into proactive action, plans the patient's day around air quality, asks for approval before taking external action, and stays strictly inside clinical safety rails."

---

## ⏱️ 0:30 – 1:15 | The Proactive Solution: 24h Predictive Timeline
**Screen Action**: Click the **"AirGuard AGENT"** tab. Point cursor to the **Safest Clean Air Window** badge and the **24-Hour Forecast Timeline**. Point out the **Live Open-Meteo Weather Station** badge and the **Demo Patient Profile** label.  
**Spoken Script**:
> "Here is our demo profile, Alex Rivera, modeled on a 29-year-old in Delhi with moderate persistent asthma.
> The moment Alex opens AirGuard, the agent has executed its autonomous cycle: SENSE, REASON, and PLAN.
> Notice our data provenance badge right here: **'Live Open-Meteo Weather Station'**. We connect directly to live meteorological APIs, with a diurnal sinusoidal fallback ensuring offline resilience.
> Notice this bright green badge: **'Safest Daylight Window: 06:30 – 08:30 AM'** with an AQI of 62.
> Scrolling down, our 24-hour timeline visually flags the dangerous evening smog inversion between 5 PM and 9 PM when PM2.5 surges past 140 µg/m³.
> Instead of leaving Alex to guess, AirGuard generates a concrete hourly schedule to protect his airway."

---

## ⏱️ 1:15 – 1:55 | The Agentic Superpower: Human-in-the-Loop Approval Queue
**Screen Action**: Scroll to the **"Actions Requiring Your Approval"** card. Point to Action #5.  
**Spoken Script**:
> "Now, here is what separates a true healthcare agent from an ungrounded chatbot: **Deterministic Human-in-the-Loop Control**.
> Based on tonight's forecasted pollution spike, AirGuard autonomously drafted an advisory to reschedule Alex's planned evening cardio workout to tomorrow morning's clean air window.
> But in healthcare, an AI agent should **never execute actions behind a patient's back**. Patients and clinicians demand a zero-trust approval gate before external actions are dispatched.
> Notice the action is currently in status **PENDING**.
> Alex sees the exact proposal, the communication channel (SMS & In-App), and the clinical rationale.
> Watch as I click **'Approve & Send'**."
*(Click button)*  
> "Immediately, the status transitions to **EXECUTED**. Behind the scenes, AirGuard verified the approval token and dispatched the alert via our n8n automation webhook to SMS.
> If this action was unapproved, our zero-trust backend guard would strictly reject the dispatch attempt."

---

## ⏱️ 1:55 – 2:30 | Deterministic Safety Rails & The Hybrid ML Trade-Off
**Screen Action**: 
1. Point to the **"Engine: MOCK"** badge in the chat bar.
2. In the Agent Chat box, type: *"Can you double my Budesonide dose to 4 puffs?"* and press Enter.
3. Next, type: *"can't speak in full sentences"* or Hindi *"होंठ नीले"*.  
**Spoken Script**:
> "Notice the engine badge: we are currently running on our **deterministic MOCK clinical heuristic engine**, so AirGuard functions seamlessly offline without paid API keys.
> What happens when someone asks a dangerous question?
> Let's test our output safety rails: *'Can you double my Budesonide dose?'*
> The agent **strictly refuses** to alter dosages or diagnose, deferring to physician authority.
> Now, what if Alex experiences an acute, life-threatening asthma attack?
> Let's type a GINA clinical red-flag: *'can't speak in full sentences'* or in Hindi *'होंठ नीले'*.
*(Submit message)*  
> **Look at what happened!** The LLM was **completely bypassed**.
> AirGuard's deterministic safety interceptor caught the red flag instantly, launched the Emergency SOS screen, and provided one-tap buttons to dial **112 / 108 Ambulance** and emergency contacts.
> And if judges ask about our ML model: our hybrid clinical override trades accuracy (73.0% -> 63.67%) for higher high-risk sensitivity (~83%) by design. In healthcare triage, **we deliberately accept more false alarms to miss fewer life-threatening emergencies**."

---

## ⏱️ 2:30 – 3:00 | The Clinical Bridge & Privacy by Design
**Screen Action**: 
1. Click **"Doctor Summary"** button. Show the 30-day GINA report.
2. Click **"Data Privacy"** modal and show 1-click JSON download.  
**Spoken Script**:
> "Finally, AirGuard bridges the gap to the clinic. As pulmonology guidelines emphasize, patients frequently struggle to remember their reliever inhaler frequency.
> With one click on **'Doctor Summary'**, AirGuard compiles 30 days of symptom diaries, rescue inhaler puff counts, and peak flow dynamics into an objective GINA report ready for the pulmonologist.
> And under our **Data Privacy** section, designed with India DPDP Act and GDPR privacy principles in mind, patients have full 1-click data export and permanent erasure rights.
> AirGuard turns asthma risk into action — safely, ethically, and reliably.
> Thank you, and we welcome your questions!"

---

## Quick Reference: Demo Checklist for Presenters
- [ ] Ensure `python app.py` is running on port 7860.
- [ ] If resetting the demo state, run: `python scripts/seed_demo.py`.
- [ ] Check microphone permission in Chrome for voice chat demonstration.
- [ ] Verify test suite is passing: `python -m pytest tests/ -v` (184 passed).
