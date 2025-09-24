# -*- coding: utf-8 -*-
"""
Baseline classifier to predict low attention from session-level features.
Includes:
- Data loading & feature engineering
- Train/val split + cross-validation
- Probability calibration
- ROC/PR plots + confusion matrix
- Coefficients report
- Model export with joblib

Notes:
- Independent from production.
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from joblib import dump
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import (classification_report, ConfusionMatrixDisplay,
                             RocCurveDisplay, PrecisionRecallDisplay, roc_auc_score,
                             average_precision_score)
from sklearn.calibration import CalibratedClassifierCV

from .evaluation import save_fig, save_text

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data")
ART  = os.path.join(BASE, "artifacts")
os.makedirs(ART, exist_ok=True)

def load_features():
    df = pd.read_csv(os.path.join(DATA, "synthetic_sessions.csv"))
    # Label: low attention < 0.5 (illustrative)
    df["low_attention"] = (df["attention"] < 0.5).astype(int)

    # Features (engineer a few interactions)
    df["acc_x_q"] = df["correct_rate"] * df["questions"]
    df["att_x_dur"] = df["attention"] * df["duration_min"]
    X = df[["correct_rate", "duration_min", "questions", "acc_x_q", "att_x_dur"]].values
    y = df["low_attention"].values
    return df, X, y

def run():
    df, X, y = load_features()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    base = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000))
    ])

    # Calibrated model via CV
    clf = CalibratedClassifierCV(base_estimator=base, method="sigmoid", cv=5)
    clf.fit(X_tr, y_tr)

    # Predict
    y_prob = clf.predict_proba(X_te)[:,1]
    y_hat  = (y_prob >= 0.5).astype(int)

    # Metrics
    report = classification_report(y_te, y_hat, digits=3)
    auc = roc_auc_score(y_te, y_prob)
    ap  = average_precision_score(y_te, y_prob)
    summary = f"ROC AUC: {auc:.3f}\nAverage Precision: {ap:.3f}\n\n{report}"
    save_text("attention_baseline_report.txt", summary)

    # Plots
    RocCurveDisplay.from_predictions(y_te, y_prob)
    save_fig("attention_baseline_roc.png")

    PrecisionRecallDisplay.from_predictions(y_te, y_prob)
    save_fig("attention_baseline_pr.png")

    ConfusionMatrixDisplay.from_predictions(y_te, y_hat)
    save_fig("attention_baseline_cm.png")

    # Save model
    dump(clf, os.path.join(ART, "attention_baseline.joblib"))
    print("Saved:", os.path.join(ART, "attention_baseline.joblib"))

    # Coefficients (extract from inner LogReg if possible)
    # Note: We trained a calibrated wrapper; coefficients vary across folds.
    # For illustration, fit a single pipeline on full train to report coefs.
    single = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000))
    ])
    single.fit(X_tr, y_tr)
    coefs = single.named_steps["clf"].coef_.ravel().tolist()
    names = ["correct_rate","duration_min","questions","acc_x_q","att_x_dur"]
    coef_report = json.dumps(dict(zip(names, coefs)), ensure_ascii=False, indent=2)
    save_text("attention_baseline_coefficients.json", coef_report)

if __name__ == "__main__":
    run()
