# AsthmAI - Research Results & Evaluation Report

## Executive Summary

This document presents comprehensive evaluation results for the AsthmAI asthma risk prediction system. We trained and compared **7 machine learning models** using **5-fold stratified cross-validation** with **hyperparameter optimization** on a dataset of **2,000 samples**.

**Evaluated Model Performance (Held-out Test Cohort, N=300)**:
- **Pure ML Stacking Ensemble**:
  - Accuracy: **73.0%**
  - Macro F1-Score: **0.7234**
  - Multiclass ROC-AUC: **0.8496**
  - High-Risk Sensitivity: **68.18%**
- **Hybrid System (Clinical Heuristic Override)**:
  - Accuracy: **63.67%** (Reflects a deliberate 9.3% accuracy trade-off)
  - Macro F1-Score: **0.6385**
  - High-Risk Sensitivity: **82.95%** (Elevated from 68.18% to protect acute patients)
  - *Clinical Safety Trade-off Rationale*: We intentionally accept higher false-alarm rates (false positives) to drastically reduce false negatives on high-risk patients. In respiratory triage, a false caution causes minor schedule adjustments; a false negative risks preventable hospitalization.

---

## Dataset Description

| Attribute | Value |
|-----------|-------|
| Total Samples | 2,000 |
| Training Set | 1,400 (70%) |
| Validation Set | 300 (15%) |
| Test Set | 300 (15%) |
| Features | 12 (7 numerical, 5 categorical) |
| Target Variable | Risk Class (Low, Medium, High) |
| Source | Original 201 samples + Synthetic expansion |

### Class Distribution
| Risk Class | Count | Percentage |
|------------|-------|------------|
| Low | 641 | 32.05% |
| Medium | 829 | 41.45% |
| High | 530 | 26.50% |

---

## Model Comparison Results

### Cross-Validation Performance (5-Fold)

| Model | Accuracy | F1-Score | ROC-AUC |
|-------|----------|----------|---------|
| **Stacking Ensemble** | **0.723 ± 0.012** | **0.719 ± 0.015** | **0.853 ± 0.006** |
| XGBoost | 0.669 ± 0.016 | 0.653 ± 0.017 | 0.797 ± 0.007 |
| Gradient Boosting | 0.668 ± 0.017 | 0.656 ± 0.016 | 0.796 ± 0.007 |
| LightGBM | 0.662 ± 0.005 | 0.649 ± 0.008 | 0.792 ± 0.004 |
| SVM (RBF) | 0.653 ± 0.017 | 0.609 ± 0.024 | 0.781 ± 0.009 |
| Random Forest | 0.662 ± 0.010 | 0.618 ± 0.014 | 0.777 ± 0.009 |
| Logistic Regression | 0.641 ± 0.021 | 0.611 ± 0.022 | 0.754 ± 0.017 |
| KNN | 0.605 ± 0.018 | 0.580 ± 0.014 | 0.695 ± 0.009 |

### Synthetic Data Validation
- **KS-Test**: Passed for all 7 numerical features (p > 0.05), confirming synthetic distribution matches original.
- **PCA Analysis**: Synthetic samples (orange) fully overlap with original samples (blue) in latent space.
- **Conclusion**: Synthetic data expansion introduces negligible bias.

### Clinical Utility
- **High Confidence Mode**: By setting a confidence threshold of 85%, the system achieves **>90% accuracy** (keeping ~60% of samples).
- **Recommendation**: Clinicians should trust "High Confidence" predictions and use manual review for "Uncertain" ones.

---

## Feature Importance Analysis

### Permutation Importance (Top Features)

| Rank | Feature | Mean Decrease in Accuracy | Std |
|------|---------|--------------------------|-----|
| 1 | Asthma Symptoms Frequency | 0.068 | 0.016 |
| 2 | AQI | 0.055 | 0.015 |
| 3 | Poor Air Quality Exposure | 0.027 | 0.012 |
| 4 | PM2.5 | 0.024 | 0.016 |
| 5 | Night Breathing Difficulty | 0.022 | 0.008 |
| 6 | CO2 level | 0.017 | 0.012 |
| 7 | Temperature | 0.011 | 0.010 |

### Key Findings
1. **Clinical factors dominate**: Asthma symptoms frequency is the strongest predictor
2. **Environmental factors matter**: AQI and PM2.5 are significant contributors
3. **Exposure history important**: Poor air quality exposure ranks highly
4. **Night symptoms indicative**: Nighttime breathing difficulty is a reliable indicator

---

## Statistical Significance

### Friedman Test (Non-parametric ANOVA)
All models were compared using the Friedman test to determine if there are statistically significant differences in performance.

### Paired T-Tests
Pairwise comparisons between models using paired t-tests on cross-validation scores.

---

## Generated Figures

All figures are saved in high resolution (300 DPI) in both PNG and PDF formats.

| Figure | Description | Location |
|--------|-------------|----------|
| ROC Curves | Multi-class ROC curves for all models | `figures/roc_curves.png` |
| Confusion Matrices | Heatmaps for all 7 models | `figures/confusion_matrices.png` |
| Model Comparison | Bar chart comparing all metrics | `figures/model_comparison.png` |
| CV Boxplot | Cross-validation score distribution | `figures/cv_boxplot.png` |
| Learning Curve | Training vs validation performance | `figures/learning_curve.png` |
| Correlation Heatmap | Feature correlation matrix | `figures/correlation_heatmap.png` |
| Class Distribution | Dataset class balance | `figures/class_distribution.png` |
| Feature Distributions | Histograms by risk class | `figures/feature_distributions.png` |
| SHAP Summary | Global feature importance | `figures/shap_summary.png` |
| SHAP Importance | Bar plot of SHAP values | `figures/shap_importance.png` |
| Permutation Importance | Feature importance ranking | `figures/permutation_importance.png` |

---

## Reproducibility

### Environment
- Python 3.10+
- TensorFlow 2.x
- scikit-learn 1.3+
- XGBoost 2.0+
- LightGBM 4.0+
- SHAP 0.44+

### Random Seeds
All experiments use `random_state=42` for reproducibility.

### Hyperparameter Tuning
GridSearchCV with 5-fold cross-validation was used for all models.

---

## How to Reproduce

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic dataset
python data_generator.py

# 3. Train all models
python research/train_models.py

# 4. Generate figures
python research/generate_figures.py

# 5. Run explainability analysis
python research/explainability.py
```

---

## Technical Conclusion

This study demonstrates that machine learning models, particularly gradient boosting methods (XGBoost, GradientBoosting, LightGBM), can effectively predict asthma risk from environmental and clinical factors. The feature importance analysis reveals that clinical symptom frequency is the most predictive factor, followed by air quality indicators (AQI, PM2.5).

The pure ML ensemble achieves **73.0% accuracy** and **0.8496 ROC-AUC**. When the **Hybrid Clinical Safety Layer** is applied, accuracy drops to **63.67%**, while High-Risk Sensitivity surges from **68.18% to 82.95%**. The hybrid system trades accuracy (73.0% -> 63.67%) for higher high-risk sensitivity (~83%) by design. 

In healthcare triage, this represents an intentional, patient-centered trade-off: **we accept more false alarms to miss fewer life-threatening emergencies**. All models and overrides are assistive tools and require licensed clinical oversight.
