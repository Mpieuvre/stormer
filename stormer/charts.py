"""Mini graphiques discrets."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def render_sparkline(values: list[float], color: str, width: int = 140, height: int = 28, dpi: int = 80) -> bytes:
    if len(values) < 2:
        return b""

    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    fig.patch.set_facecolor("#1c2433")
    ax.set_facecolor("#1c2433")

    y = np.array(values[-30:], dtype=float)
    x = np.arange(len(y))
    ax.fill_between(x, y.min() - 0.3, y, color=color, alpha=0.2)
    ax.plot(x, y, color=color, linewidth=1.8, solid_capstyle="round")

    ax.set_xlim(0, max(len(y) - 1, 1))
    pad = max((y.max() - y.min()) * 0.2, 0.4)
    ax.set_ylim(y.min() - pad, y.max() + pad)
    ax.axis("off")

    buf = io.BytesIO()
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(buf, format="png", facecolor="#1c2433", edgecolor="none", pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_hourly_strip(
    hourly_values: list[float],
    hour_labels: list[str],
    color: str = "#f59e0b",
    width: float = 4.8,
    height: float = 1.1,
    dpi: int = 100,
) -> bytes:
    """Bandeau meteo minimal : heures + valeurs."""
    if not hourly_values:
        return b""

    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    fig.patch.set_facecolor("#151b26")
    ax.set_facecolor("#151b26")

    x = np.arange(len(hourly_values))
    ax.bar(x, hourly_values, color=color, alpha=0.35, width=0.55, zorder=1)
    ax.plot(x, hourly_values, color=color, linewidth=2, marker="o", markersize=4, zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(hour_labels, color="#94a3b8", fontsize=8)
    ax.tick_params(axis="y", colors="#64748b", labelsize=7, length=0)
    ax.grid(axis="y", color="#334155", alpha=0.4, linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    buf = io.BytesIO()
    fig.tight_layout(pad=0.6)
    fig.savefig(buf, format="png", facecolor="#151b26", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
