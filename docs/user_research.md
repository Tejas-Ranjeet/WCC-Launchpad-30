# AirGuard Agent — User Research & Persona Framework

## Executive Summary
Asthma affects over **262 million people globally** (WHO 2023) and causes over **455,000 deaths annually**, with severe mortality in high-particulate urban centers. AirGuard is designed as a preventive asthma management agent that shifts patients from reactive symptom response to proactive schedule planning.

To maintain strict research integrity, this document separates empirical field evidence collection from hypothetical design frameworks.

---

## Real Evidence (Field Data Collection Framework)

> [!IMPORTANT]
> **Status: Awaiting Empirical Field Deployment**  
> In accordance with scientific and clinical integrity standards, **no survey numbers, percentages, or interview quotes have been fabricated or pre-populated**. The fields below are structured data collection slots awaiting verified deployment data.

### 1. Quantitative Survey Data
* **Target Cohort**: Diagnosed asthma patients and primary caregivers in high-AQI urban corridors (e.g., Delhi NCR, Indo-Gangetic Plain).
* **Survey Sample Size ($n$)**: `[Pending formal deployment — n = ______]`
* **Data Collection Dates**: `[DD/MM/YYYY to DD/MM/YYYY]`

#### Key Survey Statistics:
* **Metric 1: AQI Checking Behavior**
  * *Question*: Do you check AQI proactively before leaving home or only reactively after noticing respiratory symptoms?
  * *Result*: `[______% reactive (n = ___ / ___)]`
* **Metric 2: Inhaler Forgetting Frequency**
  * *Question*: How often do you leave rescue/reliever medication at home during winter or high-smog periods?
  * *Result*: `[______% at least once per week (n = ___ / ___)]`
* **Metric 3: Actionability of Current Weather / AQI Apps**
  * *Question*: Do general weather apps provide concrete action plans or scheduling guidance for asthma?
  * *Result*: `[______% find static AQI numbers non-actionable (n = ___ / ___)]`
* **Metric 4: Human-in-the-Loop Agent Trust**
  * *Question*: Would you trust an AI agent that automatically executes actions without asking your permission first?
  * *Result*: `[______% insist on mandatory user confirmation before action dispatch (n = ___ / ___)]`
* **Metric 5: Physician Consultation Recall**
  * *Question*: Can you accurately recall reliever inhaler puff frequency and symptom dates during doctor appointments?
  * *Result*: `[______% struggle with accurate monthly recall (n = ___ / ___)]`

### 2. Qualitative In-Depth Interview Evidence

#### Interview 1: Patient Experience
* **Participant Profile**: `[Patient ID, Age, City, Asthma Classification — Pending recruitment]`
* **Key Context**: `[Daily commute duration, transit type, occupational exposure]`
* **Interview Quote**:
  > *"[Awaiting verified participant transcript quote — uncollected field]"`
* **Design Takeaway**:
  - `[To be derived from verified interview transcript]`

#### Interview 2: Caregiver Experience
* **Participant Profile**: `[Caregiver ID, Relationship to Patient, Setting — Pending recruitment]`
* **Interview Quote**:
  > *"[Awaiting verified participant transcript quote — uncollected field]"`
* **Design Takeaway**:
  - `[To be derived from verified interview transcript]`

#### Interview 3: Clinician / Pulmonologist Perspective
* **Participant Profile**: `[Clinician ID, Specialty (Pulmonology/Respiratory Medicine), Practice Setting — Pending recruitment]`
* **Interview Quote**:
  > *"[Awaiting verified clinician transcript quote — uncollected field]"`
* **Clinical Takeaways for Agent Boundaries**:
  - `[To be derived from verified clinician interview]`

---

## Hypothetical Design Personas (not collected data)

> [!NOTE]
> The following 5 profiles are **Hypothetical design personas (not collected data)**. They are engineering archetypes created to stress-test UX accessibility, voice interaction, notification boundaries, and deterministic clinical guardrails under edge-case conditions.

### Persona 1: Rohan Sharma — The Urban University Student
* **Classification**: Hypothetical design persona (not collected data)
* **Archetype**: 21, University Student, Delhi NCR. Moderate persistent asthma, exercise-induced bronchospasm.
* **Prescription**: Formoterol + Budesonide maintenance; Salbutamol rescue inhaler.
* **Environment**: Daily metro/auto-rickshaw commute, outdoor collegiate sports.
* **UX Test Case & Boundary Validation**:
  - *Proactive Planning*: Can the agent identify a clean-air window (06:30–08:30 AM) and propose shifting an outdoor workout before morning smog peaks?
  - *Adherence Reminder*: Triggers morning commute inhaler verification before high-traffic exposure.

### Persona 2: Kavita Mehra — The School Teacher & Mother
* **Classification**: Hypothetical design persona (not collected data)
* **Archetype**: 54, High School Teacher, Lucknow. Moderate allergic asthma with seasonal exacerbations.
* **Prescription**: Fluticasone daily inhaler, Levocetirizine for acute allergic flare-ups.
* **Environment**: Daily chalk dust and open-air classroom exposure; autumn stubble-burning smoke.
* **UX Test Case & Boundary Validation**:
  - *Approval Queue Safety*: When a Yellow Zone peak flow drop (<80%) is logged, does the agent queue a caregiver notification in the Human-in-the-Loop queue rather than dispatching it without consent?
  - *Action Consent*: Verifies user explicitly clicks "Approve" before external communication.

### Persona 3: David Chen — The Data-Driven Professional
* **Classification**: Hypothetical design persona (not collected data)
* **Archetype**: 34, Software Architect, Bengaluru. Mild intermittent asthma, adult onset.
* **Prescription**: As-needed Salbutamol reliever.
* **Environment**: Air-conditioned office environment, weekend urban cycling.
* **UX Test Case & Boundary Validation**:
  - *Feature Driver Attribution*: Does the UI clearly communicate risk drivers (PM2.5, Humidity, NO2, Temperature) rather than presenting a black-box score?
  - *Data Ownership*: Does the privacy interface provide 1-click JSON export and complete data erasure controls?

### Persona 4: Sunita Devi — Elderly Patient with Limited English Literacy
* **Classification**: Hypothetical design persona (not collected data)
* **Archetype**: 68, Homemaker, Patna. Asthma-COPD Overlap Syndrome (ACOS).
* **Prescription**: Tiotropium + Formoterol inhaler; Budesonide nebulization as needed.
* **Environment**: High exposure to indoor biomass smoke / agarbatti and outdoor winter dust.
* **UX Test Case & Boundary Validation**:
  - *Multilingual Voice Interface*: Does speech recognition accept vernacular Hindi queries (*"सांस लेने में तकलीफ़ हो रही है"* / *"सीने में जकड़न"* )?
  - *Emergency Guardrail Interceptor*: Does the regex guardrail instantly catch life-threatening phrases (*"नीले होंठ"*, *"सांस नहीं आ रही"*) and trigger the red SOS screen with 112/108 calling, completely bypassing the LLM?

### Persona 5: Dr. Vikram Sethi — Senior Pulmonologist
* **Classification**: Hypothetical design persona (not collected data)
* **Archetype**: 46, Consultant Pulmonologist, Outpatient Clinic.
* **Clinical Setting**: Evaluates 30+ asthma and allergy patients daily in rapid 10-minute consultation slots.
* **UX Test Case & Boundary Validation**:
  - *Consultation Summary*: Does the 30-day physician export summarize objective GINA metrics (reliever puff frequency, nocturnal awakenings, PEF baseline variance) in under 1 page?
  - *Non-Diagnostic Rails*: Are outputs explicitly framed as assistive telemetry, completely barring AI-driven dosage adjustments or diagnostic claims?
