# 🔍 AirGuard / HridyaVayu Codebase Audit (Step 0)
**Date:** Hackathon Kickoff • WCC Launchpad 30 • Track: Agentic AI (Healthcare)  
**Status:** Completed  

---

## 1. Executive Summary

This audit assesses the pre-existing **HridyaVayu** codebase prior to building the **AirGuard Agent** during the WCC Launchpad 30 hackathon. Per competition integrity rules, pre-existing code is fully cataloged here, existing bugs and inconsistencies are documented transparently, and only new work committed in this branch will constitute the hackathon project.

---

## 2. Working Components (What Works)

| Component | Files / Endpoints | Status & Details |
| :--- | :--- | :--- |
| **Flask Server & Static Serving** | `app.py`, `web_ui/index.html` | Runs smoothly on port 7860; serves SPA dashboard, static assets (`web_ui/assets/`), and evaluation diagrams (`figures/`). |
| **Relational Database** | `models.py`, `asthmai.db` | SQLite with SQLAlchemy models: `User`, `SensorData`, `Alert`, `QuizResponse`, plus raw tables `predictions`, `inhaler_usage`. Auto-initializes on startup. |
| **Live Environmental Sync** | `app.py` (`RealTimeAQI`, `/api/live`) | Successfully contacts Open-Meteo Air Quality & Weather APIs (PM2.5, US AQI, NO2, SO2, temperature, humidity) using latitude/longitude with offline fallback. |
| **Inhaler Tracking & Reset** | `/use-inhaler`, `/get-inhaler-usage/<id>`, `/api/inhaler/reset` | Correctly counts doses, increments usage in SQLite, and calibrates for fresh canisters. |
| **Emergency SOS Endpoint** | `/api/sos/alert` | Saves emergency broadcast alerts to the `alert` table and retrieves emergency contact numbers. |
| **Admin & History Endpoints** | `/api/admin/overview`, `/api/recent`, `/api/stats`, `/api/eda_data` | Aggregates DB metrics, prediction history, and reads `data/dataset.csv` for EDA metrics. |
| **Multi-Step Assessment Wizard** | `web_ui/index.html` | Step 1 (profile), Step 2 (environmental sensors), Step 3 (symptom survey) connects to the API and visualizes results with Chart.js. |

---

## 3. Broken & Blocking Bugs (Fixed in Step 0)

### 3.1. Silent Model Unpickling Failure (BLOCKING - FIXED)
* **Bug:** `results/review1_ensemble.pkl` was saved under NumPy 2.x with an `MT19937` BitGenerator reducer. When running in a standard Python 3.11 environment with NumPy 1.26.4, `pickle.load()` threw:
  `ValueError: <class 'numpy.random._mt19937.MT19937'> is not a known BitGenerator module.`
* **Silent Failure Impact:** In `app.py`, the exception was caught by a generic `except` block, setting `review1_package = None`. As a result, **every single call to `/predict` silently fell back to hardcoded dummy numbers** (`ens_score=0.5, lr=0.45, rf=0.52, gb=0.51`), completely bypassing the trained machine learning models!
* **Resolution:** Added a clean NumPy BitGenerator cross-version adapter in `app.py` before `pickle.load()`. Now, `review1_ensemble.pkl` loads completely, and `/predict` executes real probability inference across all models (`baseline_lr`, `rf_model`, `gb_model`, `ensemble_model`) and calculates real Shannon entropy uncertainty.

### 3.2. Render Cloud Deployment Syntax Error (BLOCKING - FIXED)
* **Bug:** In `render.yaml` line 6:
  `startCommand: gunicorn --bind 0.0.0.0: --workers 2 --threads 4 app:app`
  The port argument was missing after `0.0.0.0:`. This causes immediate crash upon deployment on Render.
* **Resolution:** Updated to `gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 2 --threads 4 app:app`.

### 3.3. Authentication Security Flaw (NON-BLOCKING - MARKED FOR STEP 4)
* **Issue:** `hash_password(password)` is defined in `app.py` (line 116) but is never used anywhere. The `User` model lacks a `password_hash` column. `/api/auth/signup` and `/api/auth/login` accept any request without authentication verification or password checking.
* **Action:** To be overhauled in Step 4 with proper salted hashing, session management, and credential protection.

---

## 4. File Duplication & Redundant Dead Code

| File Pair / Group | Conflict / Redundancy | Assessment & Remediation |
| :--- | :--- | :--- |
| `models.py` vs `model.py` | `models.py` defines active SQLAlchemy ORM models (`User`, `SensorData`, `Alert`, `QuizResponse`).<br>`model.py` is an orphaned TensorFlow/Keras script compiling a regression neural net (`Dense(1, activation='linear')`, MSE loss) that exports `model.keras` and `preprocessing.pkl`. | `model.py` is dead legacy code from an early prototype; it is not imported by `app.py`. `models.py` is the live schema file. |
| `preprocess.py`, `utils.py`, `main.py` | Stale CLI scripts using deprecated `OneHotEncoder(sparse=False)` and terminal inputs (`input("Enter AQI: ")`). | Not utilized by `app.py` or `web_ui`. |
| `data/dataset.csv` vs `data/dataset_original.csv` | Both files are bit-for-bit identical 284 KB copies of the 2,000-sample master dataset. | Redundant duplication. |
| `results/review1_ensemble.pkl` vs `results/best_ensemble_model.pkl` | `best_ensemble_model.pkl` is an older 60.2 MB checkpoint; `review1_ensemble.pkl` is an 11.3 MB updated package. | `app.py` loads `review1_ensemble.pkl`. The 60 MB file bloats git history. |

---

## 5. Inconsistent Numbers & Documentation Mismatches

### 5.1. Test-Set Class Count Contradiction
* **Ground Truth (`data/test.csv` & `DATASET_OVERVIEW.md` Table 1):**
  * Total Test Samples = 300
  * **Low Risk:** 23 (7.7%)
  * **Medium Risk:** 148 (49.3%)
  * **High Risk:** 129 (43.0%)
* **Contradictory Claim in `README.md` (Section 5 Benchmark & Confusion Matrix):**
  * Claims Test Set has:
  * **Low Risk:** 96 (87 + 8 + 1)
  * **Medium Risk:** 124 (19 + 88 + 17)
  * **High Risk:** 80 (1 + 10 + 69)
* **Audit Finding:** The README benchmark table and confusion matrix reported completely fabricated/distorted class distributions (96 / 124 / 80) that do not match the real 300-sample test set in `data/test.csv`.

### 5.2. Multi-Center Cohort Sizes
* `DATASET_OVERVIEW.md` Section 4 claims "Hospital Network A (600 records)" and "Primary Care B (700 records)".
* `research/generate_missing_sites.py` hardcodes N=847 for Hospital Network A and N=990 for Primary Care B, while the generated CSV files were clipped or re-generated to 600 and 700 rows.

---

## 6. Claims Not Backed by Code / Data (Responsible AI Audit)

| Claim in Documentation | Reality in Codebase | Responsible AI Correction |
| :--- | :--- | :--- |
| **"Guaranteed zero false negatives"** | False negatives are not prevented by machine learning. A hardcoded heuristic (`if symptoms_freq == 'Daily' or night_diff == 'Frequently': risk = 'High'`) overrides the model. Any other severe clinical manifestation (acute bronchospasm, inability to speak) would bypass this rule. | Strike all claims of "guaranteed" or "zero false negatives". Report ML ensemble metrics and rule-based override metrics separately, clearly noting the override as deterministic clinical safety rails. |
| **"Independent External Clinical Cohorts" (Hospital Network A & Primary Care B)** | `DATASET_OVERVIEW.md` claimed these were authentic "Tertiary healthcare network telemetry logs" and "Primary care screening center logs". In reality, `research/generate_missing_sites.py` shows they were purely synthetically generated using `data_generator.py` with modified Gaussian distributions. | Re-label all such data as purely synthetic in `DATASET_OVERVIEW.md` and `README.md`. |
| **External Clinical Benchmarks (Zenodo 92.57%, Kaggle 96.45%)** | Zenodo (`real_clinical_data.csv`) and Beijing (`real_asthma_data.csv`) files do NOT exist in the repository. `research/validate_kaggle_asthma.py` references a hardcoded private file path `C:\Users\HP\Downloads\archive (1)\asthma_disease_data.csv`. These benchmarks are non-reproducible. | Remove all non-reproducible external accuracy claims from the README and documentation. Retain only metrics generated from scripts that execute on in-repo data. |
| **Medical Device / Diagnostic Disclaimers** | Neither the UI nor the README had a prominent medical disclaimer. | Add explicit disclaimers: "AirGuard is an assistive decision-support agent and is NOT a medical device. It does not provide medical diagnosis or replace licensed clinical judgment." |

---

## 7. Plan of Action (Steps 1 through 10)

1. **Step 1 — Honesty & Cleanup:**
   - Disclose pre-existing foundation and synthetic nature of data in `README.md`.
   - Create `LIMITATIONS.md`.
   - Build `research/evaluate.py` to transparently regenerate reproducible test-set metrics (ensemble-only vs hybrid override), calibration, and confusion matrices.
   - Embed universal clinical disclaimers across UI and docs.
2. **Step 2 — Agent Core:**
   - Implement `agent/` package: `agent/loop.py`, `agent/tools.py`, `agent/llm.py` with SENSE -> REASON -> PLAN -> PROPOSE -> (human approval) -> ACT -> LOG.
   - Multi-provider support (Gemini, Anthropic) + offline deterministic MOCK mode.
3. **Step 3 — Safety Guardrails:**
   - Implement deterministic `agent/guardrails.py` for input red flags (bypass LLM to emergency card) and output sanitization (block dosing/prescription changes).
   - Write pytest test suite (15+ unit tests).
4. **Step 4 — Human Control & Privacy:**
   - Add approval queue UI (Approve / Edit / Reject).
   - Action log persistence (`pending_actions`, `agent_log`, `symptom_diary`).
   - Consent gate and data minimisation.
5. **Step 5 — Usability & UI:**
   - Modernize `web_ui` with today's plan card, 48h AQI forecast chart with safest outdoor window, agent chat with voice input, bilingual support (English + Hindi), and quick symptom diary.
6. **Step 6 — Explainability:**
   - Plain-language SHAP attribution with top 3 drivers + uncertainty status.
7. **Step 7 — Reliability & Seed Demo:**
   - API caching (30 min for forecast), `/health` route, structured logging, `.env.example`, and `scripts/seed_demo.py`.
8. **Step 8 — n8n Automation:**
   - `n8n/airguard_workflow.json` with human-approval guard condition and communication dispatch nodes.
9. **Step 9 — User Research & Evidence:**
   - `docs/user_research.md` containing patient survey and physician interview templates.
10. **Step 10 — Submission Assets:**
    - Rewrite `README.md`, `docs/PITCH.md`, and `docs/DEMO_SCRIPT.md`.
