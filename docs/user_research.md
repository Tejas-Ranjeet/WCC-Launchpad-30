# AirGuard Agent — User Research & Clinical Personas

## Executive Summary
Asthma affects over **262 million people globally** (WHO 2023) and accounts for over **455,000 deaths annually**, with India bearing disproportionately high mortality despite modern pharmacotherapy. In high-particulate urban centers like Delhi NCR, Mumbai, and Lucknow, respiratory patients face daily swings between baseline stability and severe acute exacerbations triggered by air pollution (PM2.5, NO2, ozone), temperature inversions, and exercise.

Existing solutions fail because they are **passive and disconnected**:
1. **Weather and AQI apps** provide ambient numbers (e.g. "AQI 220") without actionable personal meaning or schedule adaptation.
2. **Generic AI chatbots** hallucinate ungrounded advice, dangerously suggest dosage increases, or fail to recognize medical red flags.
3. **Doctors during 10-minute clinic visits** suffer from patient recall bias ("I felt fine most days, maybe wheezed a little") without objective peak flow or reliever usage data.

**AirGuard Agent** transforms asthma risk from a passive statistic into **proactive daily protection**, grounded in clinical guidelines (GINA 2023) and protected by deterministic safety boundaries.

---

## The 5 Clinical Personas

### Persona 1: Rohan Sharma — The Urban University Student
* **Demographics**: 21 years old, Undergraduate Engineering Student, Delhi NCR.
* **Clinical Profile**: Moderate Persistent Asthma, diagnosed at age 10. Exercise-induced bronchospasm.
* **Prescription**: Formoterol / Budesonide 2 puffs daily morning; Salbutamol inhaler as needed.
* **Environment**: High exposure to rush-hour particulate smog during a 45-minute bus and walking commute.
* **Pain Points**:
  - Forgets his reliever inhaler at home because morning air seems clear.
  - Tries to jog in the evening after classes, triggering severe bronchospasms during winter temperature inversions.
  - Doesn't know when outdoor air is clean enough for physical exercise.
* **How AirGuard Solves It**:
  - **24-Hour Predictive Planning**: Pinpoints the cleanest daylight air window (06:30 - 08:30 AM) and highlights the high-risk evening spike.
  - **Proactive Commute Alert**: Sends a morning prompt reminding him to pack his rescue inhaler based on projected PM2.5 levels > 140 µg/m³.
  - **Schedule Shift Proposal**: Proactively offers to shift his calendar workout to the morning safe window, pending his 1-click approval.

---

### Persona 2: Kavita Mehra — The High School Teacher & Mother
* **Demographics**: 54 years old, High School Biology Teacher, Lucknow, Uttar Pradesh.
* **Clinical Profile**: Moderate-to-Severe Allergic Asthma; seasonal exacerbations during harvest stubble burning (Oct–Dec).
* **Prescription**: Beclomethasone inhaler twice daily; Montelukast tablet at night; Levalbuterol reliever.
* **Environment**: Outdoors daily during school morning assemblies and sports supervision.
* **Pain Points**:
  - Dismisses early tightness until it becomes a full-blown attack requiring hospitalization.
  - Her adult daughter lives in another city and constantly worries without knowing her daily health status.
  - Struggles with complex technology interfaces when experiencing shortness of breath.
* **How AirGuard Solves It**:
  - **Symptom Diary & Early Warning**: Tracks peak flow (PEF) drops below 80% baseline before clinical attacks manifest.
  - **Human-Approved Caregiver Alert**: When a Yellow Zone episode occurs, AirGuard queues an automated SMS to her daughter (`Dr. / Caregiver Alert`), requiring only a single tap to approve and dispatch.
  - **Bilingual Interface**: Seamlessly toggles to Hindi with large high-contrast visual indicators.

---

### Persona 3: David Chen — The Tech Lead & Distance Runner
* **Demographics**: 34 years old, Software Architect & Marathoner, Urban Tech Hub.
* **Clinical Profile**: Mild Intermittent Asthma, cold-air and exertion triggered.
* **Prescription**: Albuterol 2 puffs 15 minutes before vigorous aerobic exercise.
* **Environment**: Highly active outdoors; monitors weather widgets obsessively.
* **Pain Points**:
  - Standard weather apps report average citywide AQI, not hourly hyper-local forecasts.
  - Wants transparent AI: demands to know *why* a particular hour is safe or dangerous rather than black-box recommendations.
  - Concerned about data privacy and health data ownership.
* **How AirGuard Solves It**:
  - **Transparent Feature Driver Attribution**: Clearly displays model confidence and attribution gauges (PM2.5, Humidity, NO2, Temperature).
  - **48-Hour Open-Meteo Integration**: Hourly curve mapping particulate concentration throughout the weekend.
  - **GDPR / India DPDP Act Compliance**: 1-click full JSON data archive download and permanent account erasure guarantee.

---

### Persona 4: Sunita Devi — Elderly Patient with Asthma-COPD Overlap (ACOS)
* **Demographics**: 68 years old, Homemaker, Patna, Bihar.
* **Clinical Profile**: Asthma-COPD Overlap Syndrome, chronic cough, limited mobility.
* **Prescription**: Tiotropium + Formoterol inhaler; Budesonide nebulization as needed.
* **Environment**: High exposure to indoor biomass smoke (chulha/agarbatti) and outdoor winter dust.
* **Pain Points**:
  - Illiterate in English; unable to navigate text-heavy apps or typing-based interfaces.
  - Difficulty recognizing life-threatening distress versus routine daily phlegm.
  - Vulnerable to dangerous non-medical home remedies and misleading online advice.
* **How AirGuard Solves It**:
  - **Multilingual Voice Querying**: Speaks directly in Hindi ("सांस लेने में तकलीफ़ हो रही है").
  - **GINA Emergency Red-Flag Interceptor**: Instant, LLM-bypassing detection of critical phrases ("नीले होंठ", "सांस नहीं आ रही", "बोल नहीं पा रहे").
  - **Emergency Protocol SOS**: Immediately triggers flashing red alert with direct one-tap calling for national ambulance services (112 / 108) and emergency contact.

---

### Persona 5: Dr. Vikram Sethi, MD, DNB — Senior Pulmonologist
* **Demographics**: 46 years old, Consultant Pulmonologist, Fortis Hospital & Private Clinic.
* **Clinical Profile**: Clinician reviewing 30+ asthma and allergy patients daily in 10-minute slots.
* **Pain Points**:
  - Patients cannot accurately recall how many times they used their reliever inhaler over the past month.
  - Cannot tell if exacerbations were caused by medication non-adherence or unavoidable environmental pollution spikes.
  - Fears generative AI giving patients dangerous dosage alterations or claiming asthma is "cured".
* **How AirGuard Solves It**:
  - **30-Day Objective Doctor Summary**: Generates a standardized clinical report with symptom counts, reliever frequency, and PEF variance.
  - **Deterministic Safety Rails**: Output guardrails strictly prohibit dosage modification, diagnosis, or anti-medical claims, always deferring to physician authority.
  - **Non-Diagnostic Clarity**: Prominent visual banners confirm AirGuard is an assistive adherence agent, never replacing clinical judgment.

---

## Key Clinical & Behavioral Takeaways
1. **Action Beats Information**: Showing an AQI number does not change health outcomes; proposing a concrete schedule shift with 1-click approval creates real-world preventive behavior.
2. **Safety Must Be Deterministic**: Red flags cannot depend on LLM prompt obedience. Keyword/regex pattern interceptors must execute before any generative model is called.
3. **Doctors Need Summaries, Not Raw Data**: Aggregating 30 days of telemetry into GINA symptom steps empowers physicians to make informed prescription adjustments.
