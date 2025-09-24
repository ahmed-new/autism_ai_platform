# -*- coding: utf-8 -*-
"""
Toy Contextual Bandit (LinUCB) to recommend the next skill.
- Simulates contexts (child/session features)
- Reward ~ correctness * attention (sigmoid of latent linear score)
- Tracks average reward and (approx) regret over time
- Saves plots to artifacts/
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from .evaluation import save_fig, save_text

BASE = os.path.dirname(__file__)
ART  = os.path.join(BASE, "artifacts")
os.makedirs(ART, exist_ok=True)

class LinUCB:
    def __init__(self, n_arms, d, alpha=0.8, seed=42):
        self.n_arms = n_arms
        self.d = d
        self.alpha = alpha
        self.rng = np.random.default_rng(seed)
        self.A = [np.eye(d) for _ in range(n_arms)]
        self.b = [np.zeros((d,1)) for _ in range(n_arms)]

    def select(self, x):
        p = []
        for a in range(self.n_arms):
            Ainv = np.linalg.inv(self.A[a])
            theta = Ainv @ self.b[a]
            mean = float(theta.T @ x)
            var  = float(np.sqrt(x.T @ Ainv @ x))
            p.append(mean + self.alpha * var)
        return int(np.argmax(p))

    def update(self, arm, x, r):
        self.A[arm] += x @ x.T
        self.b[arm] += r * x

def simulate(T=1500, n_arms=8, d=6, seed=42, noise=0.2):
    rng = np.random.default_rng(seed)
    bandit = LinUCB(n_arms=n_arms, d=d, alpha=0.8, seed=seed)

    # latent “true” vectors per arm
    thetas = [rng.normal(0,1,(d,1)) for _ in range(n_arms)]
    rewards, best_rewards, chosen = [], [], []

    for t in range(T):
        # context: [age_norm, dur_norm, q_norm, diff_hint, fatigue, bias]
        x = rng.normal(0,1,(d,1))
        arm = bandit.select(x)
        chosen.append(arm)

        # reward for chosen arm
        score = float((thetas[arm].T @ x) + rng.normal(0, noise))
        r = 1.0 / (1.0 + np.exp(-score))   # 0..1
        rewards.append(r)

        # best possible at this step (oracle)
        scores = [float((th.T @ x)) for th in thetas]
        r_star = 1.0 / (1.0 + np.exp(-max(scores)))
        best_rewards.append(r_star)

        bandit.update(arm, x, r)

    rewards = np.array(rewards)
    best_rewards = np.array(best_rewards)
    regret = np.cumsum(best_rewards - rewards)
    avg = np.cumsum(rewards) / (np.arange(len(rewards))+1)

    # plots
    plt.figure()
    plt.plot(avg)
    plt.xlabel("Step"); plt.ylabel("Average reward")
    save_fig("bandit_avg_reward.png")

    plt.figure()
    plt.plot(regret)
    plt.xlabel("Step"); plt.ylabel("Cumulative regret")
    save_fig("bandit_regret.png")

    save_text("bandit_summary.txt",
              f"Final avg reward: {avg[-1]:.3f}\nFinal cumulative regret: {regret[-1]:.3f}\n")

if __name__ == "__main__":
    simulate()
