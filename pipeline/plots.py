import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path


def plot_daily_uptime(station_name: str, daily_uptime: pd.Series, output_dir: Path) -> None:
    """
    Bar chart of daily uptime fraction (0–1) for each day of the month.

    daily_uptime : pd.Series indexed by datetime.date, values 0.0–1.0
    """
    fig, ax = plt.subplots(figsize=(12, 4))

    dates  = [str(d) for d in daily_uptime.index]
    values = daily_uptime.values

    colors = []
    for v in values:
        if v >= 0.95:
            colors.append("#70AD47")   # green
        elif v >= 0.80:
            colors.append("#FFD966")   # yellow
        else:
            colors.append("#FF7F7F")   # red

    ax.bar(dates, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(0.95, color="#70AD47", linewidth=1, linestyle="--", label="95% threshold")
    ax.axhline(0.80, color="#FFD966", linewidth=1, linestyle="--", label="80% threshold")

    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel("Date")
    ax.set_ylabel("Uptime")
    ax.set_title(f"{station_name} — Daily Uptime")
    ax.legend(loc="lower right", fontsize=8)
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()

    out = output_dir / f"{station_name}_uptime.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[plots] Saved: {out}")


def plot_rainfall_accumulation(
    station_name: str,
    df: pd.DataFrame,
    rain_cols: list[str],
    output_dir: Path,
) -> None:
    """
    Cumulative rainfall time series for each rain gauge column in rain_cols.
    Skips columns not present in df.
    """
    available = [c for c in rain_cols if c in df.columns]
    if not available:
        print(f"[plots] {station_name}: no rain gauge columns found, skipping rainfall plot")
        return

    df_plot = df.set_index("time")[available].copy()
    cumulative = df_plot.cumsum()

    fig, ax = plt.subplots(figsize=(12, 4))
    for col in available:
        ax.plot(cumulative.index, cumulative[col], label=col)

    ax.set_xlabel("Time")
    ax.set_ylabel("Accumulated rainfall (mm)")
    ax.set_title(f"{station_name} — Rainfall Accumulation")
    ax.legend()
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()

    out = output_dir / f"{station_name}_rainfall.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[plots] Saved: {out}")
