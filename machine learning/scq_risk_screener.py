# -*- coding: utf-8 -*-
"""
SCQ risk screener (illustrative, non-diagnostic).
- Bernoulli Naive Bayes on 40 binary items.
- Stratified split + CV predictions
- Calibration plot + classification report

Outputs under artifacts/.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.naive_bayes import BernoulliNB
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, RocCurveDisplay, PrecisionRecallDisplay, roc_auc_score, average_precision_score
from .evaluation import save_fig, save_text

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data")
ART  = os.path.join(BASE, "artifacts")
os.makedirs(ART, exist_ok=True)

def load_scq():
    df = pd.read_csv(os.path.join(DATA, "synthetic_scq.csv"))
    feature_cols = [c for c in df.columns if c.startswith("q")]
    # heuristic risk flag (illustrative)
    df["risk_flag"] = (df["yes_sum"] >= 22).astype(int)
    X = df[feature_cols].values
    y = df["risk_flag"].values
    return df, X, y

def run():
    df, X, y = load_scq()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    clf = BernoulliNB(alpha=1.0, fit_prior=True)
    clf.fit(X_tr, y_tr)
    y_prob = clf.predict_proba(X_te)[:,1]
    y_hat  = (y_prob >= 0.5).astype(int)

    report = classification_report(y_te, y_hat, digits=3)
    auc = roc_auc_score(y_te, y_prob)
    ap  = average_precision_score(y_te, y_prob)
    save_text("scq_screener_report.txt", f"ROC AUC={auc:.3f}\nAP={ap:.3f}\n\n{report}")

    RocCurveDisplay.from_predictions(y_te, y_prob)
    save_fig("scq_screener_roc.png")

    PrecisionRecallDisplay.from_predictions(y_te, y_prob)
    save_fig("scq_screener_pr.png")

if __name__ == "__main__":
    run()
