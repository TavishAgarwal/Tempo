"""Wilcoxon signed-rank, Holm correction, Vargha-Delaney A12. No t-tests."""

from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon


def a12(x: np.ndarray, y: np.ndarray) -> float:
    """P(x < y) + 0.5 P(x == y): probability that x is better (smaller) than y."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    gt = (x[:, None] < y[None, :]).sum() + 0.5 * (x[:, None] == y[None, :]).sum()
    return float(gt / (len(x) * len(y)))


def wilcoxon_p(x: np.ndarray, y: np.ndarray) -> float:
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    if np.allclose(d, 0):
        return 1.0
    return float(wilcoxon(d, zero_method="wilcox").pvalue)


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, idx in enumerate(order):
        run = max(run, (m - rank) * pvals[idx])
        adj[idx] = min(1.0, run)
    return [float(a) for a in adj]
