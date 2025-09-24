# -*- coding: utf-8 -*-
"""
Runs the research workflow sequentially and aggregates outputs.
"""
import os, sys, subprocess
BASE = os.path.dirname(__file__)

def run(pyfile):
    print(">>", pyfile)
    subprocess.run([sys.executable, os.path.join(BASE, pyfile)], check=True)

if __name__ == "__main__":
    # Ensure data exists
    run("data_simulation.py")
    # Models
    run("baseline_attention_classifier.py")
    run("scq_risk_screener.py")
    run("next_skill_recommender.py")
    print("\nAll research prototypes finished. See research/artifacts/")
