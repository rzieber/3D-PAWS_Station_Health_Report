import re

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

from config import UPTIME_PASS_THRESHOLD


def plot_monthly_uptime(summary_rows: list, output_dir: Path, prefix: str = "") -> None:
    """
    Single bar chart of each instrument's total monthly uptime fraction.

    summary_rows : list of dicts with 'station' and 'overall_uptime' keys
    """
    if not summary_rows:
        return

    def _sort_key(row):
        m = re.search(r"Instrument-(\d+)", row["station"], re.IGNORECASE)
        return int(m.group(1)) if m else float("inf")

    summary_rows = sorted(summary_rows, key=_sort_key)

    labels = []
    values = []
    for row in summary_rows:
        m = re.search(r"Instrument-\d+", row["station"], re.IGNORECASE)
        labels.append(m.group(0) if m else row["station"])
        v = row["overall_uptime"]
        values.append(v if isinstance(v, float) else 0.0)

    colors = ["#70AD47" if v >= UPTIME_PASS_THRESHOLD else "#FF7F7F" for v in values]

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.6), 5))
    ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(UPTIME_PASS_THRESHOLD, color="#70AD47", linewidth=1, linestyle="--",
               label=f"{UPTIME_PASS_THRESHOLD:.0%} pass threshold")

    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel("Instrument")
    ax.set_ylabel("Monthly Uptime")
    ax.set_title("Monthly Uptime by Instrument")
    ax.legend(loc="lower right", fontsize=8)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.tight_layout()

    filename = f"{prefix}_monthly_uptime.png" if prefix else "monthly_uptime.png"
    out = output_dir / filename
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[plots] Saved: {out}")


def plot_daily_rainfall_bars(
    station_name: str,
    daily_by_gauge: dict,
    output_dir: Path,
) -> None:
    """
    Grouped daily bar chart of rainfall totals per gauge.

    daily_by_gauge : {label: pd.Series indexed by datetime.date}
                     Each Series holds one day's total (mm) derived from
                     Total Prior / Total Today columns.
    """
    import numpy as np

    available = {label: s for label, s in daily_by_gauge.items() if s.notna().any()}
    if not available:
        print(f"[plots] {station_name}: no rainfall data, skipping daily rainfall plot")
        return

    all_dates = sorted(set().union(*[set(s.index) for s in available.values()]))
    if not all_dates:
        return

    n_gauges  = len(available)
    x         = np.arange(len(all_dates))
    bar_width = 0.8 / n_gauges
    offsets   = np.linspace(-(n_gauges - 1) / 2, (n_gauges - 1) / 2, n_gauges) * bar_width
    colors    = ["#4472C4", "#ED7D31", "#A9D18E", "#FF7F7F"]

    fig, ax = plt.subplots(figsize=(max(10, len(all_dates) * 0.5), 4))

    for i, (label, series) in enumerate(available.items()):
        values = [series.get(d, float("nan")) for d in all_dates]
        ax.bar(x + offsets[i], values, bar_width, label=label,
               color=colors[i % len(colors)], edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Date")
    ax.set_ylabel("Rainfall (mm)")
    ax.set_title(f"{station_name} — Daily Rainfall")
    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in all_dates], rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=8)
    plt.tight_layout()

    out = output_dir / f"{station_name}_rainfall.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[plots] Saved: {out}")


def plot_monthly_rainfall_totals(
    rainfall_rows: list,
    rain_cols: list[str],
    output_dir: Path,
    prefix: str = "",
    y_max: float | None = None,
) -> None:
    """
    Grouped bar chart of total monthly rainfall per instrument, one bar per
    rain gauge, so gauge-to-gauge differences are immediately visible.

    rainfall_rows : list of dicts with 'station' key and one key per rain col
                    containing the summed mm total (NaN if gauge absent).
    y_max         : if set, caps the y-axis at this value (mm); bars that exceed
                    it are clipped visually but their true values remain in the data.
    """
    import numpy as np

    if not rainfall_rows:
        return

    def _sort_key(row):
        m = re.search(r"Instrument-(\d+)", row["station"], re.IGNORECASE)
        return int(m.group(1)) if m else float("inf")

    rainfall_rows = sorted(rainfall_rows, key=_sort_key)

    labels = []
    for row in rainfall_rows:
        m = re.search(r"Instrument-\d+", row["station"], re.IGNORECASE)
        labels.append(m.group(0) if m else row["station"])

    n_instruments = len(labels)
    n_gauges      = len(rain_cols)
    x             = np.arange(n_instruments)
    bar_width     = 0.35
    offsets       = np.linspace(-(n_gauges - 1) / 2, (n_gauges - 1) / 2, n_gauges) * bar_width

    colors = ["#4472C4", "#ED7D31", "#A9D18E", "#FF7F7F"]

    fig, ax = plt.subplots(figsize=(max(8, n_instruments * 0.7), 5))

    for i, col in enumerate(rain_cols):
        totals = [row.get(col, float("nan")) for row in rainfall_rows]
        ax.bar(x + offsets[i], totals, bar_width, label=col, color=colors[i % len(colors)],
               edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Instrument")
    ax.set_ylabel("Total Rainfall (mm)")
    ax.set_title("Monthly Rainfall Totals by Instrument")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    if y_max is not None:
        ax.set_ylim(top=y_max)
    ax.legend(fontsize=8)
    plt.tight_layout()

    stem     = "monthly_rainfall_totals" + ("_scaled" if y_max is not None else "")
    filename = f"{prefix}_{stem}.png" if prefix else f"{stem}.png"
    out = output_dir / filename
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[plots] Saved: {out}")
