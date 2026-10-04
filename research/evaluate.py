"""
AirGuard / HridyaVayu - Reproducible Evaluation Pipeline
Generates unbiased held-out test evaluation metrics, separating:
1. Pure ML Ensemble (Learned statistical model)
2. Hybrid System (Ensemble + Deterministic GINA Clinical Safety Override)

Outputs:
- results/evaluation_metrics.json
- results/evaluation_report.txt
- figures/confusion_matrix_ensemble_only.png
- figures/confusion_matrix_hybrid.png
- figures/calibration_curve.png
"""

import sys
import os
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, brier_score_loss
)
from sklearn.calibration import calibration_curve

warnings.filterwarnings('ignore')

# ==================== NUMPY BITGENERATOR COMPATIBILITY ====================
try:
    import numpy.random._pickle as _np_pickle
    from numpy.random._mt19937 import MT19937 as _OrigMT19937
    from numpy.random.mtrand import RandomState

    class _CompatibleMT19937(_OrigMT19937):
        def __setstate__(self, state):
            if isinstance(state, tuple):
                state = state[0]
            super().__setstate__(state)

    _CompatibleMT19937.__name__ = 'MT19937'
    _CompatibleMT19937.__qualname__ = 'MT19937'

    def _compat_bit_generator_ctor(name="MT19937"):
        if isinstance(name, _OrigMT19937):
            return name
        return _CompatibleMT19937()

    def _compat_randomstate_ctor(bit_generator_name="MT19937", bit_generator_ctor=None):
        if isinstance(bit_generator_name, _OrigMT19937):
            bg = bit_generator_name
        elif isinstance(bit_generator_name, type) and issubclass(bit_generator_name, _OrigMT19937):
            bg = _CompatibleMT19937()
        else:
            bg = _compat_bit_generator_ctor(bit_generator_name)
        return RandomState(bg)

    _np_pickle.__bit_generator_ctor = _compat_bit_generator_ctor
    _np_pickle.__randomstate_ctor = _compat_randomstate_ctor
    _np_pickle.BitGenerators['MT19937'] = _CompatibleMT19937
    _np_pickle.BitGenerators[_OrigMT19937] = _CompatibleMT19937
    _np_pickle.BitGenerators[_CompatibleMT19937] = _CompatibleMT19937
except Exception as _e:
    print(f"NumPy compat notice: {_e}")


def load_model_package(model_path="results/review1_ensemble.pkl"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model package not found at {model_path}")
    with open(model_path, "rb") as f:
        pkg = pickle.load(f)
    return pkg


def preprocess_test_data(test_csv_path, pkg):
    df = pd.read_csv(test_csv_path)
    df.columns = df.columns.str.strip()

    # Feature Engineering (identical to app.py)
    df_feat = df.copy()
    df_feat['AQI_PM_ratio'] = df_feat['AQI'] / (df_feat['PM2.5'] + 1)
    df_feat['pollution_index'] = (
        df_feat['AQI'] * 0.4 + df_feat['PM2.5'] * 0.3 +
        df_feat['NO2 level'] * 0.15 + df_feat['SO2 level'] * 0.15
    )
    df_feat['gas_pollution'] = df_feat['CO2 level'] * df_feat['NO2 level'] * df_feat['SO2 level'] / 10000
    df_feat['humidity_pollution'] = df_feat['Humidity'] * df_feat['pollution_index'] / 100
    df_feat['temp_pollution'] = df_feat['Temperature'] * df_feat['pollution_index'] / 100
    df_feat['AQI_critical'] = (df_feat['AQI'] > 200).astype(int)
    df_feat['AQI_unhealthy'] = ((df_feat['AQI'] > 100) & (df_feat['AQI'] <= 200)).astype(int)
    df_feat['PM25_high'] = (df_feat['PM2.5'] > 75).astype(int)

    symptom_map = {'Daily': 4, 'Frequently (Weekly)': 3, '1-2 times a month': 2, 'Less than once a month': 1}
    df_feat['symptom_severity'] = df_feat['Asthma Symptoms Frequency'].map(symptom_map).fillna(0)
    exposure_map = {'Yes, often': 3, 'Occasionally': 2, 'No': 1}
    df_feat['exposure_score'] = df_feat['Poor Air Quality Exposure'].map(exposure_map).fillna(0)
    night_map = {'Frequently': 3, 'Occasionally': 2, 'Rarely': 1, 'Never': 0}
    df_feat['night_score'] = df_feat['Night Breathing Difficulty'].map(night_map).fillna(0)
    df_feat['trigger_count'] = df_feat['Triggers'].apply(lambda x: str(x).count(',') + 1)
    df_feat['clinical_risk_score'] = df_feat['symptom_severity'] * 0.4 + df_feat['exposure_score'] * 0.3 + df_feat['night_score'] * 0.3
    df_feat['env_risk_score'] = df_feat['AQI_critical'] * 0.3 + df_feat['AQI_unhealthy'] * 0.2 + df_feat['PM25_high'] * 0.25 + (df_feat['pollution_index'] / 500.0) * 0.25

    df_encoded = pd.get_dummies(df_feat, columns=pkg['categorical_cols'], drop_first=True)
    for col in pkg['feature_columns']:
        if col not in df_encoded.columns:
            df_encoded[col] = 0
    df_aligned = df_encoded[pkg['feature_columns']]
    X_scaled = pkg['scaler'].transform(df_aligned)

    y_true = df['Risk Class'].values
    return df, X_scaled, y_true


def evaluate_predictions(y_true, y_pred, classes=['Low', 'Medium', 'High']):
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=classes, zero_division=0)
    
    macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, average='macro', zero_division=0)
    weighted_prec, weighted_rec, weighted_f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    
    class_metrics = {}
    for i, c in enumerate(classes):
        class_metrics[c] = {
            "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4),
            "f1_score": round(float(f1[i]), 4),
            "support": int(sup[i])
        }

    high_risk_sensitivity = class_metrics['High']['recall']

    return {
        "accuracy": round(float(acc), 4),
        "macro_precision": round(float(macro_prec), 4),
        "macro_recall": round(float(macro_rec), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "high_risk_sensitivity": round(float(high_risk_sensitivity), 4),
        "per_class": class_metrics,
        "confusion_matrix": cm.tolist()
    }


def plot_confusion_matrix(cm, classes, title, output_path):
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    
    ax.set(xticks=np.arange(len(classes)),
           yticks=np.arange(len(classes)),
           xticklabels=classes, yticklabels=classes,
           title=title,
           ylabel='True Class',
           xlabel='Predicted Class')

    thresh = cm.max() / 2.
    for i in range(len(classes)):
        for j in range(len(classes)):
            val = cm[i, j]
            row_sum = cm[i].sum()
            pct = (val / row_sum * 100) if row_sum > 0 else 0
            ax.text(j, i, f"{val}\n({pct:.1f}%)",
                    ha="center", va="center",
                    color="white" if val > thresh else "black",
                    fontsize=9, weight='bold')

    fig.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"Saved figure: {output_path}")


def plot_calibration(y_true_binary, prob_high, output_path):
    prob_true, prob_pred = calibration_curve(y_true_binary, prob_high, n_bins=10, strategy='uniform')
    brier = brier_score_loss(y_true_binary, prob_high)
    
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    ax.plot(prob_pred, prob_true, marker='o', linewidth=2, label=f'Ensemble (Brier: {brier:.4f})', color='#0284c7')
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfect Calibration')
    
    ax.set_xlabel('Mean Predicted High-Risk Probability')
    ax.set_ylabel('Fraction of High-Risk Positives')
    ax.set_title('High-Risk Class Probability Calibration Curve')
    ax.legend(loc='lower right')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    fig.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"Saved figure: {output_path}")
    return brier


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    test_csv = os.path.join(base_dir, 'data', 'test.csv')
    model_path = os.path.join(base_dir, 'results', 'review1_ensemble.pkl')
    results_dir = os.path.join(base_dir, 'results')
    figures_dir = os.path.join(base_dir, 'figures')
    
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    print("=" * 70)
    print("AIRGUARD / HRIDYAVAYU — INDEPENDENT TEST SET EVALUATION")
    print("=" * 70)
    print(f"Dataset: {test_csv}")
    print(f"Model:   {model_path}")

    pkg = load_model_package(model_path)
    df_raw, X_scaled, y_true = preprocess_test_data(test_csv, pkg)

    classes = ['Low', 'Medium', 'High']
    total_samples = len(y_true)
    class_counts = pd.Series(y_true).value_counts().to_dict()
    print(f"\nHeld-Out Test Samples: {total_samples}")
    print(f"Class Distribution: Low={class_counts.get('Low', 0)}, Medium={class_counts.get('Medium', 0)}, High={class_counts.get('High', 0)}")

    # 1. Pure ML Ensemble Predictions
    prob_ens = pkg['ensemble_model'].predict_proba(X_scaled)
    y_pred_ens_idx = np.argmax(prob_ens, axis=1)
    y_pred_ens = [pkg['reverse_map'][i] for i in y_pred_ens_idx]

    # Individual Base Models
    prob_lr = pkg['baseline_lr'].predict_proba(X_scaled)
    y_pred_lr = [pkg['reverse_map'][i] for i in np.argmax(prob_lr, axis=1)]

    prob_rf = pkg['rf_model'].predict_proba(X_scaled)
    y_pred_rf = [pkg['reverse_map'][i] for i in np.argmax(prob_rf, axis=1)]

    prob_gb = pkg['gb_model'].predict_proba(X_scaled)
    y_pred_gb = [pkg['reverse_map'][i] for i in np.argmax(prob_gb, axis=1)]

    # 2. Hybrid System Predictions (Ensemble + Deterministic GINA Clinical Safety Override)
    y_pred_hybrid = []
    override_count = 0
    for idx, row in df_raw.iterrows():
        s_freq = str(row['Asthma Symptoms Frequency'])
        n_diff = str(row['Night Breathing Difficulty'])
        ens_choice = y_pred_ens[idx]
        
        # Exact GINA rule from app.py:
        if s_freq == "Daily" or n_diff == "Frequently":
            y_pred_hybrid.append("High")
            if ens_choice != "High":
                override_count += 1
        elif s_freq == "Frequently (Weekly)" and ens_choice == "Low":
            y_pred_hybrid.append("Medium")
            override_count += 1
        else:
            y_pred_hybrid.append(ens_choice)

    # Evaluate Each
    metrics_ens = evaluate_predictions(y_true, y_pred_ens, classes)
    metrics_hybrid = evaluate_predictions(y_true, y_pred_hybrid, classes)
    metrics_lr = evaluate_predictions(y_true, y_pred_lr, classes)
    metrics_rf = evaluate_predictions(y_true, y_pred_rf, classes)
    metrics_gb = evaluate_predictions(y_true, y_pred_gb, classes)

    # Calibration Curve for High Risk
    high_class_idx = list(pkg['class_map'].values()).index('High') if 'High' in pkg['class_map'].values() else 2
    prob_high = prob_ens[:, high_class_idx]
    y_true_high_binary = (y_true == 'High').astype(int)
    brier_score = plot_calibration(y_true_high_binary, prob_high, os.path.join(figures_dir, 'calibration_curve.png'))

    # Plot Confusion Matrices
    cm_ens = np.array(metrics_ens['confusion_matrix'])
    cm_hybrid = np.array(metrics_hybrid['confusion_matrix'])
    plot_confusion_matrix(cm_ens, classes, 'ML Soft-Voting Ensemble (No Overrides)', os.path.join(figures_dir, 'confusion_matrix_ensemble_only.png'))
    plot_confusion_matrix(cm_hybrid, classes, 'Hybrid System (Ensemble + GINA Safety Override)', os.path.join(figures_dir, 'confusion_matrix_hybrid.png'))

    # Build Comprehensive Output
    all_results = {
        "evaluation_dataset": {
            "path": "data/test.csv",
            "nature": "Synthetic multimodal atmospheric & GINA telemetry",
            "total_samples": total_samples,
            "class_distribution": {
                "Low": int(class_counts.get("Low", 0)),
                "Medium": int(class_counts.get("Medium", 0)),
                "High": int(class_counts.get("High", 0))
            }
        },
        "models": {
            "baseline_logistic_regression": {
                "accuracy": metrics_lr["accuracy"],
                "macro_f1": metrics_lr["macro_f1"],
                "weighted_f1": metrics_lr["weighted_f1"],
                "high_risk_sensitivity": metrics_lr["high_risk_sensitivity"]
            },
            "random_forest": {
                "accuracy": metrics_rf["accuracy"],
                "macro_f1": metrics_rf["macro_f1"],
                "weighted_f1": metrics_rf["weighted_f1"],
                "high_risk_sensitivity": metrics_rf["high_risk_sensitivity"]
            },
            "gradient_boosting": {
                "accuracy": metrics_gb["accuracy"],
                "macro_f1": metrics_gb["macro_f1"],
                "weighted_f1": metrics_gb["weighted_f1"],
                "high_risk_sensitivity": metrics_gb["high_risk_sensitivity"]
            },
            "ml_collaborative_ensemble": {
                "description": "Pure learned statistical soft-voting ensemble (1*LR + 2*RF + 2*GB) without heuristic overrides",
                **metrics_ens,
                "high_risk_brier_score": round(float(brier_score), 4)
            },
            "hybrid_neuro_symbolic": {
                "description": "Learned ensemble coupled with deterministic GINA Step-5 safety rails (clinical heuristics)",
                "overrides_triggered": override_count,
                **metrics_hybrid
            }
        }
    }

    # Save JSON
    json_path = os.path.join(results_dir, 'evaluation_metrics.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved JSON metrics: {json_path}")

    # Build Text Report
    report_text = f"""================================================================================
AIRGUARD / HRIDYAVAYU — REPRODUCIBLE TEST SET EVALUATION REPORT
================================================================================
Dataset: data/test.csv (SYNTHETIC multimodal dataset)
Total Test Samples: {total_samples}
Class Distribution: Low={class_counts.get('Low', 0)} ({class_counts.get('Low', 0)/total_samples*100:.1f}%), Medium={class_counts.get('Medium', 0)} ({class_counts.get('Medium', 0)/total_samples*100:.1f}%), High={class_counts.get('High', 0)} ({class_counts.get('High', 0)/total_samples*100:.1f}%)

--------------------------------------------------------------------------------
1. COMPONENT-BY-COMPONENT BENCHMARK SUMMARY
--------------------------------------------------------------------------------
Architecture                             Accuracy   Macro-F1   Weighted-F1   High-Risk Sensitivity
--------------------------------------------------------------------------------
Baseline Logistic Regression             {metrics_lr['accuracy']*100:6.2f}%   {metrics_lr['macro_f1']:8.4f}   {metrics_lr['weighted_f1']:11.4f}   {metrics_lr['high_risk_sensitivity']*100:6.2f}%
Random Forest Classifier                 {metrics_rf['accuracy']*100:6.2f}%   {metrics_rf['macro_f1']:8.4f}   {metrics_rf['weighted_f1']:11.4f}   {metrics_rf['high_risk_sensitivity']*100:6.2f}%
Gradient Boosting Classifier             {metrics_gb['accuracy']*100:6.2f}%   {metrics_gb['macro_f1']:8.4f}   {metrics_gb['weighted_f1']:11.4f}   {metrics_gb['high_risk_sensitivity']*100:6.2f}%
--------------------------------------------------------------------------------
Pure ML Collaborative Ensemble           {metrics_ens['accuracy']*100:6.2f}%   {metrics_ens['macro_f1']:8.4f}   {metrics_ens['weighted_f1']:11.4f}   {metrics_ens['high_risk_sensitivity']*100:6.2f}%
Hybrid (Ensemble + GINA Safety Rails)    {metrics_hybrid['accuracy']*100:6.2f}%   {metrics_hybrid['macro_f1']:8.4f}   {metrics_hybrid['weighted_f1']:11.4f}   {metrics_hybrid['high_risk_sensitivity']*100:6.2f}%
--------------------------------------------------------------------------------

* High-Risk Brier Score (Calibration): {brier_score:.4f}
* Heuristic Overrides Triggered in Test Set: {override_count} / {total_samples}

--------------------------------------------------------------------------------
2. PURE ML ENSEMBLE TEST CONFUSION MATRIX (Learned Model Only)
--------------------------------------------------------------------------------
Predicted:      Low    Medium    High
True Low:      {cm_ens[0,0]:4d}     {cm_ens[0,1]:4d}    {cm_ens[0,2]:4d}
True Medium:   {cm_ens[1,0]:4d}     {cm_ens[1,1]:4d}    {cm_ens[1,2]:4d}
True High:     {cm_ens[2,0]:4d}     {cm_ens[2,1]:4d}    {cm_ens[2,2]:4d}

Per-Class Performance (Ensemble):
  Low Risk:    Precision = {metrics_ens['per_class']['Low']['precision']:.4f} | Recall = {metrics_ens['per_class']['Low']['recall']:.4f} | F1 = {metrics_ens['per_class']['Low']['f1_score']:.4f}
  Medium Risk: Precision = {metrics_ens['per_class']['Medium']['precision']:.4f} | Recall = {metrics_ens['per_class']['Medium']['recall']:.4f} | F1 = {metrics_ens['per_class']['Medium']['f1_score']:.4f}
  High Risk:   Precision = {metrics_ens['per_class']['High']['precision']:.4f} | Recall = {metrics_ens['per_class']['High']['recall']:.4f} | F1 = {metrics_ens['per_class']['High']['f1_score']:.4f}

--------------------------------------------------------------------------------
3. HYBRID SYSTEM TEST CONFUSION MATRIX (Ensemble + Deterministic GINA Override)
--------------------------------------------------------------------------------
Predicted:      Low    Medium    High
True Low:      {cm_hybrid[0,0]:4d}     {cm_hybrid[0,1]:4d}    {cm_hybrid[0,2]:4d}
True Medium:   {cm_hybrid[1,0]:4d}     {cm_hybrid[1,1]:4d}    {cm_hybrid[1,2]:4d}
True High:     {cm_hybrid[2,0]:4d}     {cm_hybrid[2,1]:4d}    {cm_hybrid[2,2]:4d}

Per-Class Performance (Hybrid):
  Low Risk:    Precision = {metrics_hybrid['per_class']['Low']['precision']:.4f} | Recall = {metrics_hybrid['per_class']['Low']['recall']:.4f} | F1 = {metrics_hybrid['per_class']['Low']['f1_score']:.4f}
  Medium Risk: Precision = {metrics_hybrid['per_class']['Medium']['precision']:.4f} | Recall = {metrics_hybrid['per_class']['Medium']['recall']:.4f} | F1 = {metrics_hybrid['per_class']['Medium']['f1_score']:.4f}
  High Risk:   Precision = {metrics_hybrid['per_class']['High']['precision']:.4f} | Recall = {metrics_hybrid['per_class']['High']['recall']:.4f} | F1 = {metrics_hybrid['per_class']['High']['f1_score']:.4f}

================================================================================
IMPORTANT RESPONSIBLE DESIGN NOTICE:
The GINA Step-5 override elevates High-Risk Sensitivity via deterministic rules
(e.g., Daily symptoms or Frequent night dyspnea forced to High Risk).
These rules are clinical safety guardrails, NOT learned machine learning patterns.
Data used is SYNTHETIC and was generated to simulate clinical distributions.
================================================================================
"""

    report_path = os.path.join(results_dir, 'evaluation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"Saved text report:  {report_path}")
    print("\n" + report_text)


if __name__ == '__main__':
    main()
