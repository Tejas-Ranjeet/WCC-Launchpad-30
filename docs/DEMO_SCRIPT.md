# AirGuard Agent — 3-Minute Live Hackathon Demo Script

**Total Duration**: 3 Minutes (180 Seconds)  
**Presenter**: Lead Engineer / Pitcher  
**Screen Setup**: Browser open to `http://localhost:7860`, logged in as **Alex Rivera** (`alex@example.com` / `demo123`).

---

## ⏱️ 0:00 – 0:30 | The Hook: The Passive Healthcare Trap
**Screen Action**: Show traditional weather app widget or dashboard with "AQI 210".  
**Spoken Script**:
> "Judges, over 260 million people live with asthma. In cities like Delhi, millions wake up to notifications saying 'AQI is 210 — Very Unhealthy'.
> But here's the dirty secret of digital health: **passive numbers don't prevent asthma attacks.**
> A 29-year-old asthmatic doesn't need another scary number. They need to know: *Can I go for my evening run? What time is safe to step outside? Did I remember my inhaler?*
> Today, we present **AirGuard Agent** — an autonomous AI agent that turns asthma risk into proactive action, plans the patient's day around air quality, asks for approval before taking external action, and stays strictly inside clinical safety rails."

---

## ⏱️ 0:30 – 1:15 | The Proactive Solution: 24h Predictive Timeline
**Screen Action**: Click the **"AirGuard AGENT"** tab. Point cursor to the **Safest Clean Air Window** badge and the **24-Hour Forecast Timeline**.  
**Spoken Script**:
> "Here is our demo user, Alex Rivera, living in Delhi with moderate persistent asthma.
> The moment Alex opens AirGuard, the agent has already executed its autonomous cycle: SENSE, REASON, and PLAN.
> AirGuard pulled a 48-hour atmospheric forecast from Open-Meteo and computed the exact diurnal inversion curve.
> Notice this bright green badge: **'Safest Daylight Window: 06:30 – 08:30 AM'** with an AQI of 62.
> Scrolling down, our 24-hour timeline visually flags the dangerous evening rush-hour spike between 5 PM and 9 PM when PM2.5 surges past 140 µg/m³.
> Instead of leaving Alex to guess, AirGuard generates a concrete hourly schedule to protect his airway."

---

## ⏱️ 1:15 – 1:55 | The Agentic Superpower: Human-in-the-Loop Approval Queue
**Screen Action**: Scroll to the **"Pending Approvals (Human-in-the-Loop)"** card. Point to Action #5.  
**Spoken Script**:
> "Now, here is what separates a true healthcare agent from an ungrounded chatbot: **Deterministic Human-in-the-Loop Control**.
> Based on tonight's forecasted pollution spike, AirGuard autonomously drafted an advisory to reschedule Alex's planned evening cardio workout to tomorrow morning's clean air window.
> But in healthcare, an AI agent should **never execute actions behind a patient's back**.
> Notice the action is currently in status **PENDING**.
> Alex sees the exact proposal, the communication channel (SMS & In-App), and the clinical rationale.
> Watch as I click **'Approve & Dispatch'**."
*(Click button)*  
> "Immediately, the status transitions to **EXECUTED**. Behind the scenes, AirGuard verified the approval token and dispatched the alert via our n8n automation webhook to SMS.
> If this action was not approved, our zero-trust backend guard would strictly reject any dispatch attempt."

---

## ⏱️ 1:55 – 2:30 | Deterministic Safety Rails & Multilingual Voice Query
**Screen Action**: 
1. Toggle the **"हिंदी / English"** switch to show full Hindi localization, then back or keep Hindi.
2. In the Agent Chat box, type: *"Can you double my Budesonide dose to 4 puffs?"* and press Enter.
3. Next, type or speak: *"I can't breathe and my lips are turning blue"* or in Hindi *"सांस नहीं आ रही है"*.  
**Spoken Script**:
> "Real patients also talk to their agents. We built native bilingual English and Hindi voice support for elderly patients.
> But what happens when someone asks a dangerous question?
> Let's test our output safety rails: *'Can you double my Budesonide dose?'*
> Notice the agent **strictly refuses** to adjust medication doses or diagnose, reminding Alex to consult his physician.
> Now, what if Alex experiences an acute, life-threatening asthma attack?
> Let's enter a GINA clinical red-flag phrase: *'I can't breathe and my lips are turning blue'*.
*(Submit message)*  
> **Look at what happened!** The LLM was **completely bypassed**.
> AirGuard's deterministic safety interceptor caught the red flag instantly, launched the Emergency SOS screen, and provided one-tap buttons to dial **112 / 108 Ambulance** and notify his emergency contact.
> No hallucinations. No delays. Pure clinical safety."

---

## ⏱️ 2:30 – 3:00 | The Clinical Bridge & Data Privacy
**Screen Action**: 
1. Click **"Doctor Consultation Summary"** button.
2. Show the rendered 30-day clinical report.
3. Click **"Data Privacy & Export"** modal and show 1-click JSON download.  
**Spoken Script**:
> "Finally, AirGuard solves the doctor's biggest headache.
> During a 10-minute clinic visit, doctors can't get reliable patient recall.
> With one click on **'Doctor Summary'**, AirGuard compiles 30 days of symptom diaries, rescue inhaler puff counts, and peak flow dynamics into a GINA-standardized clinical report ready for Alex's pulmonologist.
> And under our **Data Privacy** section, full GDPR and India DPDP Act compliance gives Alex complete ownership to export his archive or wipe his data with a single click.
> AirGuard turns asthma risk into action — safely, ethically, and reliably.
> Thank you, and we welcome your questions!"

---

## Quick Reference: Demo Checklist for Presenters
- [ ] Ensure `python app.py` is running on port 7860.
- [ ] If resetting the demo state, run: `python scripts/seed_demo.py`.
- [ ] Check microphone permission in Chrome for voice chat demonstration.
- [ ] Verify test suite is passing: `python -m pytest tests/ -v` (29 passed).
