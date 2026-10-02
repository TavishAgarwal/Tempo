"""Convergence bands, boxplots, scaling plots (PNG + SVG) and CSV exports."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from taqpso.store.results import RunRecord  # noqa: E402

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]


def _save(fig: plt.Figure, out: Path, stem: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out / f"{stem}.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)


def convergence(recs: list[RunRecord], budget: float, out: Path, stem: str, title: str) -> None:
    grid = np.linspace(0.0, budget, 100)
    fig, ax = plt.subplots(figsize=(6, 4))
    solvers = sorted({r.solver for r in recs if r.trace})
    for k, s in enumerate(solvers):
        curves = []
        for r in (r for r in recs if r.solver == s and r.trace):
            t = np.array([p[0] for p in r.trace])
            j = np.array([p[1] for p in r.trace])
            idx = np.searchsorted(t, grid, side="right") - 1
            c = np.where(idx >= 0, j[np.clip(idx, 0, None)], np.nan)
            curves.append(c)
        if not curves:
            continue
        a = np.array(curves)
        med = np.nanmedian(a, axis=0)
        lo, hi = np.nanpercentile(a, 2.5, axis=0), np.nanpercentile(a, 97.5, axis=0)
        ax.plot(grid, med, color=PALETTE[k % 8], label=s)
        ax.fill_between(grid, lo, hi, color=PALETTE[k % 8], alpha=0.15)
    ax.set_xlabel("seconds")
    ax.set_ylabel("best J (normalised)")
    ax.set_title(title)
    ax.legend()
    _save(fig, out, stem)


def boxplot(values: dict[str, list[float]], out: Path, stem: str, title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.boxplot(list(values.values()), tick_labels=list(values.keys()))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    _save(fig, out, stem)


def line(
    x: list[float],
    ys: dict[str, list[float]],
    out: Path,
    stem: str,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    for k, (name, y) in enumerate(ys.items()):
        ax.plot(x, y, marker="o", color=PALETTE[k % 8], label=name)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    _save(fig, out, stem)
