import pandas as pd
import numpy as np
from pathlib import Path

from config import UPTIME_GREEN, UPTIME_YELLOW, RAIN_GAUGE_COLS


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
    """Map an uptime fraction to 'green' | 'yellow' | 'red'."""
    if uptime >= UPTIME_GREEN:
        return "green"
    if uptime >= UPTIME_YELLOW:
        return "yellow"
    return "red"


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
