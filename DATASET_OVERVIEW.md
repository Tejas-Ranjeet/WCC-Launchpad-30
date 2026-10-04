# 📊 HridyaVayu: Dataset Overview & Data Architecture
### Multimodal Atmospheric Telemetry & GINA Clinical Guidelines Dataset Breakdown
**Department of Computer Science & Engineering, VIT Bhopal University • Group — 147**

---

## 📌 1. Dataset Partitioning Summary

The core dataset contains **2,000 multimodal clinical and atmospheric records** partitioned into strictly stratified **Training (70%)**, **Validation (15%)**, and **Independent Testing (15%)** subsets. This rigorous division ensures zero data leakage while assessing the model's true generalization capacity across low, moderate, and acute asthma exacerbation scenarios.

| Dataset Partition | File Path | Sample Count | Percentage | Class Stratification (Low / Medium / High) | Primary Experimental Role |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Training Set** | [`data/train.csv`](data/train.csv) | **1,400** | **70.0%** | 107 (7.6%) / 694 (49.6%) / 599 (42.8%) | Model parameter estimation, tree splitting, and feature scaler fitting (`StandardScaler`). |
| **Validation Set** | [`data/validation.csv`](data/validation.csv) | **300** | **15.0%** | 23 (7.7%) / 149 (49.7%) / 128 (42.7%) | Soft-voting weight calibration ($w_1=1, w_2=2, w_3=2$), hyperparameter tuning, and early stopping. |
| **Held-Out Test Set** | [`data/test.csv`](data/test.csv) | **300** | **15.0%** | 23 (7.7%) / 148 (49.3%) / 129 (43.0%) | Final unbiased performance benchmarking, confusion matrix generation, and clinical safety verification. |
| **Full Combined Dataset**| [`data/dataset.csv`](data/dataset.csv) | **2,000** | **100.0%** | 153 (7.7%) / 991 (49.5%) / 856 (42.8%) | Master aggregated repository dataset. |

---

## 🛡️ 2. Data Hygiene & Zero-Leakage Protocol

To ensure publication-grade scientific validity, the preprocessing pipeline follows strict medical data hygiene principles:
1. **Isolated Scaler Fitting:** The feature scaling transformation (`StandardScaler`) is fitted **strictly on the 1,400 training samples**. The derived mean ($\mu$) and standard deviation ($\sigma$) parameters are frozen and applied to the validation and test sets without recalculation.
2. **Zero Information Bleed:** No test or validation statistics (e.g. min, max, quantiles) are ever exposed during training or feature engineering.
3. **Exact Class Stratification:** The 3-class distribution is preserved identically across all three subsets to prevent sampling bias:
   * **Low Risk:** ~7.7%
   * **Medium Risk:** ~49.5%
   * **High Risk:** ~42.8%

---

## 📋 3. Comprehensive Data Dictionary

### A. Continuous Environmental & Atmospheric Telemetry (7 Features)
Captured via real-time satellite dispersion telemetry from the **Open-Meteo European CAMS API** (ECMWF):

| Feature Name | Type | Physical Unit | Mean ± Std | Min – Max | Clinical Relevance & Physiological Impact |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **AQI** | Integer | Index [0–500] | 185.50 ± 69.33 | 41 – 345 | Composite ambient air quality severity index. Values >150 trigger acute airway inflammation. |
| **PM2.5** | Continuous | µg/m³ | 78.04 ± 37.97 | 4.73 – 172.12 | Fine respirable particulate matter penetrating deep alveolar lung tissues; major exacerbation driver. |
| **SO2 level** | Continuous | ppb / µg/m³ | 26.26 ± 13.63 | 0.60 – 57.68 | Sulfur dioxide gas emitted from combustion; causes rapid bronchoconstriction in asthmatics. |
| **NO2 level** | Continuous | ppb / µg/m³ | 54.36 ± 25.03 | 4.28 – 114.03 | Nitrogen dioxide from vehicular emissions; increases bronchial hyper-reactivity to allergens. |
| **CO2 level** | Continuous | ppm | 443.81 ± 83.70 | 254.45 – 670.92 | Carbon dioxide concentration; serves as a proxy for enclosed spaces and stagnant air pockets. |
| **Humidity** | Continuous | % | 58.13 ± 16.28 | 24.06 – 101.67 | Atmospheric relative humidity; high humidity swells mold spores while dry air irritates mucous membranes. |
| **Temperature**| Continuous | °C | 21.94 ± 9.72 | 4.06 – 45.76 | Ambient thermal index; sudden drops induce cold-induced bronchospasm. |

### B. Standardized GINA Clinical Guidelines Features (5 Features)
Collected via standardized 5-question intake screening following **Global Initiative for Asthma (GINA 2023)** protocols:

| Feature Name | Variable Type | Possible Categorical Values & Cohort Frequency | GINA Clinical Rationale |
| :--- | :---: | :--- | :--- |
| **Asthma Symptoms Frequency** | Categorical (Ordinal) | • `Daily` (682 records, 34.1%)<br>• `Less than once a month` (491 records, 24.6%)<br>• `Frequently (Weekly)` (466 records, 23.3%)<br>• `1-2 times a month` (361 records, 18.1%) | Primary measure of daytime asthma control. Daily symptoms denote uncontrolled persistent asthma (GINA Step 4/5). |
| **Night Breathing Difficulty (Nocturnal Dyspnea)** | Categorical (Ordinal) | • `Never` (594 records, 29.7%)<br>• `Rarely` (535 records, 26.8%)<br>• `Frequently` (442 records, 22.1%)<br>• `Occasionally` (429 records, 21.5%) | Critical clinical red flag. Frequent nocturnal awakenings indicate high risk of fatal asthma exacerbation; triggers GINA Safety Override. |
| **Poor Air Quality Exposure** | Categorical | • `Yes, often` (689 records, 34.5%)<br>• `Occasionally` (685 records, 34.3%)<br>• `No` (626 records, 31.3%) | Self-reported environmental risk factor assessing occupational and commuting exposure. |
| **Weather Sensitivity** | Categorical | • `No specific weather-related triggers` (583 records, 29.2%)<br>• `Cold weather` (486 records, 24.3%)<br>• `Windy and dry weather` (478 records, 23.9%)<br>• `Hot and humid weather` (453 records, 22.7%) | Individual respiratory reaction to barometric, thermal, and humidity fluctuations. |
| **Triggers** | Multi-Select Categorical | • `Pollen` (194)<br>• `Humidity` (194)<br>• `Dust` (181)<br>• `Air pollution (smoke, chemicals)` (113)<br>• Combinations (e.g. `Dust + Pollen + Pollution`) | Specific allergen and environmental triggers causing immediate airway hyper-responsiveness. |

### C. Engineered Composite Interaction Terms (10 Features)
To enable the collaborative machine learning ensemble to capture non-linear synergistic triggers, 10 composite interaction features are engineered before inference, constructing the full **22-dimensional input space ($X \in \mathbb{R}^{22}$)**:

1. **Pollution Severity Index:** $	ext{PM2.5} 	imes 	ext{AQI} / 100$
2. **PM2.5 to AQI Ratio:** Captures particulate dominance relative to general gaseous air pollution.
3. **Combined Gaseous Toxicity Index:** $	ext{NO}_2 + 	ext{SO}_2$
4. **Thermal-Humidity Strain Index:** Interaction between ambient temperature and relative humidity.
5. **Cold-Dry Airway Irritation Index:** Quantifies risk under sub-10°C dry atmospheric conditions.
6. **Hot-Humid Stagnation Factor:** Quantifies airborne mold and bio-aerosol proliferation.
7. **Clinical Severity Score:** Ordinal mapping of symptom frequency + nocturnal dyspnea.
8. **Allergen-Weather Synergy Term:** Maps interaction between weather sensitivity and reported triggers.
9. **Exposure Susceptibility Factor:** Combines self-reported pollution history with measured AQI.
10. **Composite Airway Vulnerability Index:** Holistic non-linear fusion term across sensing streams.

---

## 🏥 4. Synthetic Multi-Site Validation Cohorts (Simulation)

> ### ⚠️ Responsible AI Provenance Disclosure
> To evaluate out-of-distribution stability without patient privacy breaches, two additional **synthetic multi-site cohorts** were generated via parameterized simulation (`research/generate_missing_sites.py`):

| Evaluation Split | File Path | Nature | Sample Size | Primary Role |
| :--- | :--- | :--- | :---: | :--- |
| **Multi-Site Cohort A** | [`data/hospital_network_a.csv`](data/hospital_network_a.csv) | Parameterized synthetic cohort with elevated clinical noise | **600** | Simulated tertiary care triage evaluation |
| **Primary Care Cohort B**| [`data/primary_care_b.csv`](data/primary_care_b.csv) | Parameterized synthetic cohort with moderate outdoor exposure | **700** | Simulated outpatient screening evaluation |

*Note on Third-Party Datasets: Previous academic references to third-party cohorts (Zenodo, Kaggle) are non-reproducible within this standalone repository because raw patient records cannot be redistributed under public license without specific institutional agreements. All reproducible numbers in this project stem from the in-repo evaluation script [`research/evaluate.py`](research/evaluate.py).*

---

## 🎯 5. Ground Truth Target Classification

The target risk classification represents clinical asthma exacerbation threat:

* **🟢 Low Risk (Controlled Asthma):** Patient exhibits infrequent daytime symptoms (<1/month), zero nocturnal dyspnea, and ambient air is within safe thresholds.
* **🟡 Medium Risk (Moderate Concern):** Moderate symptoms (1–2 times/month), intermittent triggers, or elevated urban particulate exposure (AQI 100–200). Patient advised to carry rescue inhaler and limit outdoor exertion.
* **🔴 High Risk (Acute Threat / Severe Flare-up):** Frequent attacks, acute nocturnal dyspnea, or hazardous particulate air pollution (AQI >200, PM2.5 >100 µg/m³). Triggers emergency alert modal, inhaler protocol, and SOS broadcasting.
