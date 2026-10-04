# ⚠️ Clinical & Technical Limitations

**Project:** AirGuard Agent (built on HridyaVayu base)  
**Hackathon:** WCC Launchpad 30 • Track: Agentic AI (Healthcare)  
**Notice:** Transparent disclosure of system boundaries, dataset provenance, and clinical scope.

---

## 1. Regulatory Status & Non-Diagnostic Scope

> ### 🚨 Critical Clinical Disclaimer
> **AirGuard / HridyaVayu is an assistive health-tech decision-support prototype and is NOT a certified medical device.**  
> It is not approved by the US FDA, European EMA, Indian CDSCO, or any statutory health regulatory body. It does not provide medical diagnosis, clinical prognosis, or direct therapeutic prescriptions. It must never be used as a substitute for professional clinical judgment, emergency medical services (such as 112/108 in India or 911 in the US), or an individualized Asthma Action Plan established by a licensed pulmonologist.

* Under no circumstances should patients alter, initiate, or discontinue prescribed corticosteroid or bronchodilator therapies based on agent outputs.
* All suggestions produced by the agent are informational decision-support aids designed to encourage environmental vigilance and medication schedule adherence.

---

## 2. Dataset Provenance: Synthetic Data Disclosure

* **Nature of Data:** All training (`data/train.csv`), validation (`data/validation.csv`), testing (`data/test.csv`), and site files (`data/hospital_network_a.csv`, `data/primary_care_b.csv`) in this repository were **synthetically generated** using parameterized multivariate distributions.
* **Why Synthetic Data?** Publicly accessible datasets that synchronously correlate real-time GPS atmospheric telemetry (CAMS PM2.5, NO2, SO2) with longitudinal patient symptom diaries and clinical exacerbation events do not exist in open science due to patient privacy (HIPAA/GDPR) and cross-institutional sensor fragmentation.
* **Limitation:** While distributions reflect clinical benchmarks from GINA 2023 literature, synthetic data cannot replicate the complex physiological heterogeneity, latent comorbidity interactions (e.g., COPD, allergic rhinitis, cardiovascular disease), or unmodeled environmental confounders present in living patient cohorts.

---

## 3. Machine Learning vs. Deterministic Clinical Safety Rails

To ensure scientific honesty, evaluation metrics are reported separately for the statistical model and the rule-based clinical safety rails:

| Evaluation Dimension | Pure ML Collaborative Ensemble | Hybrid System (Ensemble + GINA Safety Rails) |
| :--- | :---: | :---: |
| **Model Type** | Soft-voting classifier (LR + RF + GB) | Learned ML ensemble + Rule-based Step-5 heuristic |
| **Accuracy on Held-Out Test Set** | **73.00%** | **63.67%** |
| **Weighted F1-Score** | **0.7234** | **0.6243** |
| **High-Risk Sensitivity (Recall)** | **72.09%** | **82.95%** |
| **High-Risk Precision** | **78.81%** | **60.45%** |

### Key Takeaways
1. **The statistical model alone achieves 72.09% High-Risk sensitivity.** It is not infallible and produces misclassifications in borderline cases.
2. **The GINA Step-5 override is NOT machine learning.** It is a deterministic safety heuristic (`if Daily symptoms or Frequent nocturnal dyspnea -> force High Risk`).
3. **The Clinical Safety Trade-Off:** The safety rails boost High-Risk Sensitivity from 72.09% to 82.95% (detecting 107 of 129 acute cases). However, this deliberate bias lowers overall statistical accuracy from 73.00% to 63.67% by intentionally over-warning moderate patients. In respiratory triage, an abundance of caution (higher false alarms) is clinically preferred over silent false negatives.
4. **"Zero False Negatives" is impossible:** No statistical model or simple heuristic rule can guarantee zero false negatives in medicine. Unusual clinical presentations (e.g., sudden exertion-induced bronchospasm in clean air) may not trigger heuristic rules.

---

## 4. Atmospheric Telemetry Constraints

* **Spatial Resolution:** Real-time air quality metrics are ingested via the Open-Meteo European CAMS Atmospheric API. While state-of-the-art for regional forecasting, satellite and numerical dispersion models operate on grid resolutions of ~10 km × 10 km.
* **Micro-Climate Blind Spots:** Regional satellite telemetry cannot measure micro-environmental hazards, such as indoor secondhand tobacco smoke, unventilated biomass cooking, damp mold proliferation, or localized industrial exhausts.
* **Network & API Latency:** Satellite feeds are refreshed at discrete hourly intervals; rapid localized dust storms or sudden construction plumes may not register immediately.

---

## 5. Agentic AI & LLM Limitations

* **Non-Deterministic Natural Language:** Although temperature settings are constrained and clinical guardrails intercept all plan generation, Large Language Models (LLMs) can occasionally hallucinate colloquial phrasing.
* **Strict Human-in-the-Loop Requirement:** The agent is architected so that **no external actuation (SMS, WhatsApp alert to caregiver, notification) can execute without explicit user approval** via the Human Approval Queue.
* **Red-Flag Interception:** Any input signaling acute distress (e.g., inability to complete sentences, persistent nocturnal dyspnea, blue lips) completely bypasses LLM planning and diverts immediately to the deterministic emergency workflow.
