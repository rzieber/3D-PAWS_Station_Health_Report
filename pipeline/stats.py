import pandas as pd
import numpy as np
from pathlib import Path

from config import UPTIME_PASS_THRESHOLD, RAIN_GAUGE_COLS, RAIN_GAUGE_PRIOR_COLS, RAIN_GAUGE_TODAY_COLS


def compute_daily_rainfall(
    df: pd.DataFrame,
    prior_col: str,
    today_col: str,
    period_end=None,
) -> pd.Series:
    """
    Reconstruct reliable daily rainfall totals (mm) from Total Prior and Total Today columns.

    Total Prior on day D holds day (D-1)'s complete daily total — a scalar set at
    midnight that is unaffected by mid-day network gaps.

    Strategy:
      - For every day that has a following day in the data: use Total Prior from that
        next day (reliable, complete).
      - For the last day in the dataset only: fall back to max(Total Today) because no
        following day's Prior is available.
      - The first day's own Total Prior value (= the previous month's final day) is
        discarded.

    period_end : datetime.date or None
        When set, the returned series is clipped to dates <= period_end.  Pass the
        last day of the desired analysis period so that any extra "future" day
        downloaded solely to supply a Total Prior value is excluded from totals.

    Returns a pd.Series indexed by datetime.date.  NaN where data is absent.
    """
    if prior_col not in df.columns:
        return pd.Series(dtype=float)

    tmp = df.copy()
    tmp["_date"] = pd.to_datetime(tmp["time"]).dt.date

    grouped = tmp.groupby("_date")[prior_col].median()
    dates   = grouped.index.tolist()

    if not dates:
        return pd.Series(dtype=float)

    # Total Prior on date D+1 = date D's complete daily total.
    # Drop element 0 (= previous month's spill) from values; align with dates 0..N-2.
    daily = pd.Series(grouped.values[1:], index=grouped.index[:-1], dtype=float)

    # Last day in the dataset has no following day — fall back to max(Total Today).
    last_date = dates[-1]
    if today_col in df.columns:
        today_vals = tmp[tmp["_date"] == last_date][today_col].dropna()
        daily[last_date] = today_vals.max() if not today_vals.empty else float("nan")
    else:
        daily[last_date] = float("nan")

    if period_end is not None:
        daily = daily[daily.index <= period_end]

    return daily.sort_index()


def calculate_uptime(df: pd.DataFrame, sampling_rate: int) -> dict:
    """
    Compute overall and daily uptime for a gap-filled station dataframe.

    After gap filling, every expected timestamp is present. A timestamp is
    considered "live" when at least one non-time sensor column has a real
    (non-NaN) value.

    Returns a dict with:
      overall_uptime  : float  (0.0–1.0)
      daily_uptime    : pd.Series indexed by date, values 0.0–1.0
      expected_obs    : int
      actual_obs      : int
    """
    non_time = [c for c in df.columns if c != "time"]
    live_mask = df[non_time].notna().any(axis=1)

    expected = len(df)
    actual   = int(live_mask.sum())

    df_tmp = df.copy()
    df_tmp["_live"] = live_mask
    df_tmp["_date"] = pd.to_datetime(df_tmp["time"]).dt.date

    daily = df_tmp.groupby("_date")["_live"].agg(
        lambda s: s.sum() / len(s) if len(s) > 0 else np.nan
    )

    return {
        "overall_uptime": actual / expected if expected > 0 else 0.0,
        "daily_uptime":   daily,
        "expected_obs":   expected,
        "actual_obs":     actual,
    }


def uptime_status(uptime: float) -> str:
    """Map an uptime fraction to 'green' (pass) | 'red' (fail)."""
    return "green" if uptime >= UPTIME_PASS_THRESHOLD else "red"


# ---------------------------------------------------------------------------
# Stubs — to be filled in after the first meeting
# ---------------------------------------------------------------------------

def flag_excessive_rainfall(df: pd.DataFrame, threshold_mm: float) -> pd.DataFrame:
    """
    TODO: Return rows where any rain gauge column exceeds threshold_mm in a
    single observation period.
    """
    raise NotImplementedError


def flag_stuck_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """
    TODO: Identify periods where one rain gauge reports non-zero while the
    other reports zero (potential stuck tipping bucket).
    Requires RAIN_GAUGE_COLS = [col_a, col_b] in config.py.
    """
    raise NotImplementedError


def flag_bucket_deviation(df: pd.DataFrame, threshold_mm: float) -> pd.DataFrame:
    """
    TODO: Return rows where the absolute difference between the two rain gauge
    columns exceeds threshold_mm.
    """
    raise NotImplementedError


def summarize_station(station_name: str, df: pd.DataFrame, sampling_rate: int) -> dict:
    """
    Aggregate all metrics for one station into a single flat dict suitable
    for a row in the summary report.
    """
    uptime_info = calculate_uptime(df, sampling_rate)

    return {
        "station":        station_name,
        "expected_obs":   uptime_info["expected_obs"],
        "actual_obs":     uptime_info["actual_obs"],
        "overall_uptime": round(uptime_info["overall_uptime"], 4),
        "uptime_status":  uptime_status(uptime_info["overall_uptime"]),
        # Additional metric columns will be added here after the first meeting
    }
