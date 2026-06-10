"""
3D-PAWS Station Health Report — pipeline entry point

Usage
-----
python3 run_pipeline.py --raw-dir data/raw --out-dir data [--prefix MyString]

  Sampling rates are resolved per instrument from SAMPLING_RATE_OVERRIDES in
  config.py (falling back to SAMPLING_RATE_DEFAULT).  Pass --sampling-rate to
  force a single rate for every file (useful for one-off testing).

  Pass --prefix to namespace all outputs for a particular run (country/month).
  With --prefix MyString:
    data/processed/MyString/MyString_<station>_QC.csv
    data/plots/MyString/MyString_<station>_uptime.png  (and rainfall)
    data/outliers/MyString_outliers.csv
    data/reports/MyString_station_health_report.xlsx

Steps
-----
0. Download raw data from CHORDS (Go 1 day in the future in order to use Day Prior rainfall values), add into raw folder
1. QC  : gap-fill, remove sentinels, deduplicate, sort
2. Stats: compute per-station uptime (and future metrics)
3. Report: write color-coded Excel summary
4. Plots: daily uptime bar charts + rainfall accumulation
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from config import (SAMPLING_RATE_DEFAULT, RAIN_GAUGE_COLS,
                    RAIN_GAUGE_PRIOR_COLS, RAIN_GAUGE_TODAY_COLS,
                    PREFIX as CONFIG_PREFIX, RAW_DIR as CONFIG_RAW_DIR, OUT_DIR as CONFIG_OUT_DIR,
                    DATA_START, DATA_END)
from pipeline.qc     import run_qc, infer_sampling_rate
from pipeline.stats  import summarize_station, compute_daily_rainfall
from pipeline.report import generate_report
from pipeline.plots  import (plot_monthly_uptime, plot_monthly_rainfall_totals,
                             plot_daily_rainfall_bars, plot_rainfall_accumulation)


def _resolve_col(df_columns: set, candidates) -> str:
    """Return the first candidate column name present in df; fall back to the first candidate."""
    if isinstance(candidates, str):
        return candidates
    return next((c for c in candidates if c in df_columns), candidates[0])


def _resolve_sampling_rate(csv_path: Path, override: int | None) -> int:
    """Return the sampling rate (minutes) for this file.

    Priority: CLI --sampling-rate > inferred from CSV head > SAMPLING_RATE_DEFAULT
    """
    if override is not None:
        return override
    rate = infer_sampling_rate(csv_path)
    if rate is not None:
        return rate
    print(f"[WARNING] Could not infer sampling rate from '{csv_path.name}', using default ({SAMPLING_RATE_DEFAULT} min)")
    return SAMPLING_RATE_DEFAULT


def parse_args():
    parser = argparse.ArgumentParser(description="Generate monthly station health report.")
    parser.add_argument("--raw-dir",       default=None,        help="Directory containing raw CSVs from chords-download. Defaults to RAW_DIR in config.py.")
    parser.add_argument("--out-dir",       default=None,        help="Root output directory (sub-folders created automatically). Defaults to OUT_DIR in config.py.")
    parser.add_argument("--sampling-rate", type=int, default=None,
                        help="Force a single sampling rate (minutes) for all files. "
                             "Overrides per-instrument config. Omit to use config.py rules.")
    parser.add_argument("--prefix", default="",
                        help="String prefix for all output files and sub-folders. "
                             "E.g. --prefix Ethiopia_Apr2026")
    return parser.parse_args()


def main():
    args = parse_args()

    raw_dir  = Path(args.raw_dir or CONFIG_RAW_DIR)
    out_dir  = Path(args.out_dir or CONFIG_OUT_DIR)
    prefix   = args.prefix or CONFIG_PREFIX

    period_start = pd.Timestamp(DATA_START).date() if DATA_START else None
    period_end   = pd.Timestamp(DATA_END).date()   if DATA_END   else None

    processed_dir = out_dir / "processed" / prefix if prefix else out_dir / "processed"
    outliers_dir  = out_dir / "outliers"
    reports_dir   = out_dir / "reports"
    plots_dir     = out_dir / "plots" / prefix if prefix else out_dir / "plots"

    for d in (processed_dir, outliers_dir, reports_dir, plots_dir):
        d.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {raw_dir}")
        sys.exit(1)

    # Instruments the downloader flagged as having no data for the period
    warning_files = sorted(f for f in raw_dir.glob("*.txt") if "[WARNING]" in f.name)

    all_outliers   = []
    summary_rows   = []
    rainfall_rows  = []

    for csv_path in csv_files:
        station_name  = csv_path.stem
        sampling_rate = _resolve_sampling_rate(csv_path, args.sampling_rate)
        print(f"\n--- {station_name}  [{sampling_rate}-min] ---")

        # 1. QC
        qc_df, outliers_df = run_qc(csv_path, sampling_rate)
        qc_filename = f"{prefix}_{station_name}_QC.csv" if prefix else f"{station_name}_QC.csv"
        qc_df.to_csv(processed_dir / qc_filename, index=False)
        print(f"[qc] {len(qc_df)} rows after QC  |  {len(outliers_df)} values removed")
        if not outliers_df.empty:
            all_outliers.append(outliers_df)

        # 2. Stats — clip to analysis period so any extra "future" day doesn't skew uptime
        qc_period = qc_df
        if period_start or period_end:
            dates = pd.to_datetime(qc_period["time"]).dt.date
            if period_start:
                qc_period = qc_period[dates >= period_start]
            if period_end:
                qc_period = qc_period[dates <= period_end]
        row = summarize_station(station_name, qc_period, sampling_rate)
        print(f"[stats] uptime={row['overall_uptime']:.1%}  ({row['uptime_status']})")

        # 3. Rainfall — use full qc_df so extra day's Total Prior is available;
        #    period_end clips the returned series to the analysis window
        plot_name = f"{prefix}_{station_name}" if prefix else station_name
        daily_by_gauge = {}
        rainfall_row   = {"station": station_name}
        df_cols = set(qc_df.columns)
        for i, (prior_candidates, today_candidates, display_col) in enumerate(
            zip(RAIN_GAUGE_PRIOR_COLS, RAIN_GAUGE_TODAY_COLS, RAIN_GAUGE_COLS), start=1
        ):
            actual_prior = _resolve_col(df_cols, prior_candidates)
            actual_today = _resolve_col(df_cols, today_candidates)
            daily = compute_daily_rainfall(qc_df, actual_prior, actual_today, period_end=period_end)
            daily_by_gauge[f"Rain Gauge {i}"] = daily
            total = float(daily.sum()) if daily.notna().any() else float("nan")
            row[f"rain_gauge_{i}_total"] = total
            rainfall_row[display_col] = total
        plot_daily_rainfall_bars(plot_name, daily_by_gauge, plots_dir)
        plot_rainfall_accumulation(plot_name, daily_by_gauge, plots_dir)
        rainfall_rows.append(rainfall_row)

        g1 = row.get("rain_gauge_1_total", float("nan"))
        g2 = row.get("rain_gauge_2_total", float("nan"))
        avg = (g1 + g2) / 2
        row["rainfall_pct_diff"] = (
            round(abs(g1 - g2) / avg * 100, 1)
            if avg > 0 and pd.notna(g1) and pd.notna(g2)
            else float("nan")
        )

        # Pearson correlation between the two daily totals
        g1_daily = daily_by_gauge.get("Rain Gauge 1", pd.Series(dtype=float))
        g2_daily = daily_by_gauge.get("Rain Gauge 2", pd.Series(dtype=float))
        paired = pd.concat([g1_daily, g2_daily], axis=1).dropna()
        if (len(paired) >= 2
                and paired.iloc[:, 0].std() > 0
                and paired.iloc[:, 1].std() > 0):
            row["rain_gauge_corr"] = round(float(paired.iloc[:, 0].corr(paired.iloc[:, 1])), 3)
        else:
            row["rain_gauge_corr"] = float("nan")

        # Maximum single-day absolute difference and the date it occurred
        diff_series = (g1_daily - g2_daily).dropna()
        if not diff_series.empty:
            abs_diff = diff_series.abs()
            max_idx = abs_diff.idxmax()
            row["rain_gauge_max_diff"]     = round(float(abs_diff[max_idx]), 1)
            row["rain_gauge_max_diff_day"] = str(max_idx)
        else:
            row["rain_gauge_max_diff"]     = float("nan")
            row["rain_gauge_max_diff_day"] = None

        # Number of days each gauge reported zero rainfall
        for j, gauge_key in enumerate(["Rain Gauge 1", "Rain Gauge 2"], start=1):
            daily = daily_by_gauge.get(gauge_key, pd.Series(dtype=float))
            valid = daily.dropna()
            row[f"rain_gauge_{j}_zero_days"] = int((valid == 0.0).sum()) if not valid.empty else float("nan")

        summary_rows.append(row)

    # Stub rows for instruments with no data
    for txt_path in warning_files:
        station_name = re.sub(r"_?\[WARNING\]$", "", txt_path.stem, flags=re.IGNORECASE)
        print(f"\n--- {station_name}  [NO DATA] ---")
        summary_rows.append({
            "station":        station_name,
            "expected_obs":   "N/A",
            "actual_obs":     "N/A",
            "overall_uptime": 0.0,
            "uptime_status":  "grey",
        })

    # Monthly uptime chart (all instruments in one plot)
    plot_monthly_uptime(summary_rows, plots_dir, prefix)

    # Monthly rainfall totals charts (full scale + 300 mm scaled version)
    plot_monthly_rainfall_totals(rainfall_rows, RAIN_GAUGE_COLS, plots_dir, prefix)
    plot_monthly_rainfall_totals(rainfall_rows, RAIN_GAUGE_COLS, plots_dir, prefix, y_max=300)

    # Save combined outlier table
    if all_outliers:
        combined = pd.concat(all_outliers, ignore_index=True)
        out_path = outliers_dir / (f"{prefix}_outliers.csv" if prefix else "outliers.csv")
        combined.to_csv(out_path, index=False)
        print(f"\n[outliers] {len(combined)} total values removed — saved to {out_path}")

    # 4. Report
    report_path = reports_dir / (f"{prefix}_station_health_report.xlsx" if prefix else "station_health_report.xlsx")
    generate_report(summary_rows, report_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
