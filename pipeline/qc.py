import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
from pandas import Index, Timestamp

from config import SENTINEL_VALUE


# ---------------------------------------------------------------------------
# Gap filling
# ---------------------------------------------------------------------------

def _build_empty_row(columns: Index, missing_timestamp: Timestamp, fill_empty=np.nan) -> list | None:
    if pd.isna(missing_timestamp):
        return None
    row = []
    for col in columns:
        row.append(missing_timestamp if col == "time" else fill_empty)
    return row


def _fill_gaps(df: pd.DataFrame, sampling_rate: int) -> pd.DataFrame:
    """Insert NaN rows for missing timestamps so the index is gap-free."""
    if "time" not in df.columns:
        df = df.reset_index()

    df["time"] = pd.to_datetime(df["time"])

    nat_rows = df[df["time"].isna()].copy()
    df = df[df["time"].notna()].copy()

    td = timedelta(minutes=sampling_rate)
    blank_rows = []

    for i in range(len(df) - 1):
        cur  = df["time"].iloc[i].replace(second=0, microsecond=0)
        nxt  = df["time"].iloc[i + 1].replace(second=0, microsecond=0)
        while nxt - cur > td:
            cur += td
            row = _build_empty_row(df.columns, cur)
            if row is not None:
                blank_rows.append(row)

    if blank_rows:
        df = pd.concat(
            [df, pd.DataFrame(blank_rows, columns=df.columns)],
            ignore_index=True,
        ).sort_values("time").reset_index(drop=True)

    if not nat_rows.empty:
        print(f"[WARNING] _fill_gaps: dropped {len(nat_rows)} row(s) with NaT timestamps")

    return df


# ---------------------------------------------------------------------------
# Sentinel-value removal
# ---------------------------------------------------------------------------

def _remove_sentinels(df: pd.DataFrame, station_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Replace SENTINEL_VALUE with NaN throughout the dataframe.
    Returns (cleaned_df, outliers_df).

    outliers_df columns: station, time, variable, original_value, reason
    """
    records = []
    numeric_cols = df.select_dtypes(include="number").columns

    for col in numeric_cols:
        mask = np.isclose(df[col].fillna(0), SENTINEL_VALUE)
        if mask.any():
            for _, row in df.loc[mask, ["time", col]].iterrows():
                records.append({
                    "station":        station_name,
                    "time":           row["time"],
                    "variable":       col,
                    "original_value": row[col],
                    "reason":         f"sentinel value ({SENTINEL_VALUE})",
                })
            df.loc[mask, col] = np.nan

    outliers_df = pd.DataFrame(records, columns=["station", "time", "variable", "original_value", "reason"])
    return df, outliers_df


# ---------------------------------------------------------------------------
# Deduplication and timestamp sorting
# ---------------------------------------------------------------------------

def _sort_and_deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Sort by time, drop exact duplicate rows.
    Returns (cleaned_df, removed_df) where removed_df documents dropped duplicates.
    """
    df = df.sort_values("time").reset_index(drop=True)

    duplicate_mask = df.duplicated(keep="first")
    removed = df[duplicate_mask].copy()
    removed.insert(0, "reason", "duplicate row")

    df = df[~duplicate_mask].reset_index(drop=True)
    return df, removed


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_qc(
    raw_csv: Path,
    sampling_rate: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full QC pipeline for a single station CSV.

    Steps:
      1. Load CSV
      2. Drop unnamed index columns
      3. Sort timestamps and remove duplicate rows
      4. Fill data gaps with NaN rows
      5. Replace sentinel values (-999.99) with NaN

    Returns
    -------
    qc_df : pd.DataFrame
        Gap-filled, sentinel-clean dataframe ready for analysis.
    outliers_df : pd.DataFrame
        Table of every value removed and why (station, time, variable,
        original_value, reason). Append across stations before saving.
    """
    station_name = raw_csv.stem

    df = pd.read_csv(raw_csv, encoding="latin1")
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed|^level_", case=False, na=False)]

    # Normalize the timestamp column name to lowercase regardless of source casing
    time_match = [c for c in df.columns if c.lower() == "time"]
    if not time_match:
        raise ValueError(f"No 'time' column in {raw_csv.name}")
    if time_match[0] != "time":
        df = df.rename(columns={time_match[0]: "time"})

    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    df, dup_removed = _sort_and_deduplicate(df)

    df = _fill_gaps(df, sampling_rate)

    df, sentinel_outliers = _remove_sentinels(df, station_name)

    # Combine all removed values into one outliers table
    if not dup_removed.empty:
        dup_records = []
        non_time = [c for c in dup_removed.columns if c not in ("reason", "time")]
        for _, row in dup_removed.iterrows():
            for col in non_time:
                if pd.notna(row[col]):
                    dup_records.append({
                        "station":        station_name,
                        "time":           row["time"],
                        "variable":       col,
                        "original_value": row[col],
                        "reason":         "duplicate row",
                    })
        dup_outliers = pd.DataFrame(dup_records, columns=["station", "time", "variable", "original_value", "reason"])
        outliers_df = pd.concat([sentinel_outliers, dup_outliers], ignore_index=True)
    else:
        outliers_df = sentinel_outliers

    return df, outliers_df
