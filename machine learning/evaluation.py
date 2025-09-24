# -*- coding: utf-8 -*-
"""
Shared evaluation helpers for saving figures/text reports to artifacts directory.
"""
import os, io, contextlib
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
ART = os.path.join(BASE, "artifacts")
os.makedirs(ART, exist_ok=True)

def save_text(name: str, content: str):
    path = os.path.join(ART, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved:", path)

def save_fig(name: str):
    path = os.path.join(ART, name)
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print("Saved:", path)

def capture_print(func, *args, **kwargs) -> str:
    """Capture stdout of a function to a string (for reports)."""
    buff = io.StringIO()
    with contextlib.redirect_stdout(buff):
        func(*args, **kwargs)
    return buff.getvalue()
