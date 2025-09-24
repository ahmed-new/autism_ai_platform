

"""
Generates synthetic datasets that resemble the platform's signals:
- synthetic_sessions.csv: per-session per-skill aggregates (accuracy, attention, duration, count)
- synthetic_scq.csv: binary answers (0/1) for 40 items + yes_sum

Notes:
- No dependency on the production codebase.
- Random seed is fixed for reproducibility, with CLI overrides.
"""
import os, argparse, math
import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

def simulate_sessions(n_children=120, n_skills=14, seed=42,
                      sessions_per_child_low=2, sessions_per_child_high=6):
    rng = np.random.default_rng(seed)
    rows = []
    sid = 1

    # latent child-level traits
    child_skill_affinity = rng.normal(0, 0.6, size=(n_children, n_skills))  # child × skill
    child_attention_baseline = rng.normal(0.65, 0.12, size=n_children).clip(0.3, 0.95)
    child_accuracy_baseline  = rng.beta(2.7, 2.3, size=n_children)           # 0..1

    for cid in range(1, n_children+1):
        k = rng.integers(sessions_per_child_low, sessions_per_child_high+1)
        # per-child session scatter
        for _ in range(k):
            duration_min = float(np.clip(rng.normal(18, 6), 5, 60))
            n_q_total = int(np.clip(rng.normal(20, 6), 6, 60))

            # choose a subset of skills used in this session
            n_used = int(np.clip(rng.normal(4.5, 1.4), 2, 8))
            used_skills = rng.choice(np.arange(1, n_skills+1), size=n_used, replace=False)

            att_base = float(np.clip(child_attention_baseline[cid-1] + rng.normal(0, 0.08), 0.1, 0.98))
            acc_base = float(np.clip(child_accuracy_baseline[cid-1]  + rng.normal(0, 0.08), 0.05, 0.99))

            # distribute questions across skills
            weights = rng.random(n_used)
            weights = weights / weights.sum()
            q_per_skill = np.maximum(2, (weights * n_q_total).astype(int))

            for s_idx, skill_id in enumerate(used_skills):
                # skill-specific mod via latent affinity
                aff = child_skill_affinity[cid-1, skill_id-1]
                correct_rate = float(np.clip(acc_base + 0.10*aff + rng.normal(0, 0.07), 0.0, 1.0))
                attention    = float(np.clip(att_base + 0.08*aff + rng.normal(0, 0.07), 0.0, 1.0))

                rows.append({
                    "session_id": sid,
                    "child_id": cid,
                    "skill_id": int(skill_id),
                    "questions": int(q_per_skill[s_idx]),
                    "correct_rate": correct_rate,
                    "attention": attention,
                    "duration_min": duration_min
                })
            sid += 1

    df = pd.DataFrame(rows)
    return df

def simulate_scq(n_children=120, n_items=40, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    # per-child yes-prop baseline
    yes_prop = np.clip(rng.beta(2.0, 2.2, size=n_children) + rng.normal(0, 0.05, n_children), 0.05, 0.95)
    for cid in range(1, n_children+1):
        base = yes_prop[cid-1]
        answers = {}
        yes_count = 0
        for i in range(1, n_items+1):
            p = float(np.clip(base + rng.normal(0, 0.07), 0.05, 0.95))
            a = int(rng.random() < p)
            answers[f"q{i}"] = a
            yes_count += a
        rows.append({"child_id": cid, **answers, "yes_sum": yes_count})
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--children", type=int, default=120)
    ap.add_argument("--skills", type=int, default=14)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    sessions = simulate_sessions(n_children=args.children, n_skills=args.skills, seed=args.seed)
    scq = simulate_scq(n_children=args.children, seed=args.seed)

    sessions.to_csv(os.path.join(DATA, "synthetic_sessions.csv"), index=False)
    scq.to_csv(os.path.join(DATA, "synthetic_scq.csv"), index=False)
    print("Saved:", os.path.join(DATA, "synthetic_sessions.csv"))
    print("Saved:", os.path.join(DATA, "synthetic_scq.csv"))

if __name__ == "__main__":
    main()
