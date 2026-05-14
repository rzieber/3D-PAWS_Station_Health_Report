"""
3D-PAWS Station Health Report — pipeline entry point

Usage
-----
python3 run_pipeline.py --raw-dir data/raw --out-dir data

  Sampling rates are resolved per instrument from SAMPLING_RATE_OVERRIDES in
  config.py (falling back to SAMPLING_RATE_DEFAULT).  Pass --sampling-rate to
  force a single rate for every file (useful for one-off testing).

Steps
-----
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

from config import SAMPLING_RATE_DEFAULT, SAMPLING_RATE_OVERRIDES, RAIN_GAUGE_COLS
from pipeline.qc     import run_qc
from pipeline.stats  import summarize_station, calculate_uptime
from pipeline.report import generate_report
from pipeline.plots  import plot_daily_uptime, plot_rainfall_accumulation


def _resolve_sampling_rate(csv_path: Path, override: int | None) -> int:
    """Return the sampling rate (minutes) for this file.

    Priority: CLI --sampling-rate > SAMPLING_RATE_OVERRIDES > SAMPLING_RATE_DEFAULT
    Instrument ID is parsed from filenames like FEWSNET_Instrument-12_...csv
    """
    if override is not None:
        return override
    match = re.search(r"Instrument-(\d+)", csv_path.stem, re.IGNORECASE)
    if match:
        instrument_id = int(match.group(1))
        return SAMPLING_RATE_OVERRIDES.get(instrument_id, SAMPLING_RATE_DEFAULT)
    print(f"[WARNING] Could not parse instrument ID from '{csv_path.name}', using default rate ({SAMPLING_RATE_DEFAULT} min)")
    return SAMPLING_RATE_DEFAULT


def parse_args():
    parser = argparse.ArgumentParser(description="Generate monthly station health report.")
    parser.add_argument("--raw-dir",       required=True,       help="Directory containing raw CSVs from chords-download.")
    parser.add_argument("--out-dir",       required=True,       help="Root output directory (sub-folders created automatically).")
    parser.add_argument("--sampling-rate", type=int, default=None,
                        help="Force a single sampling rate (minutes) for all files. "
                             "Overrides per-instrument config. Omit to use config.py rules.")
    return parser.parse_args()


def main():
    args = parse_args()

    raw_dir  = Path(args.raw_dir)
    out_dir  = Path(args.out_dir)

    processed_dir = out_dir / "processed"
    outliers_dir  = out_dir / "outliers"
    reports_dir   = out_dir / "reports"
    plots_dir     = out_dir / "plots"

    for d in (processed_dir, outliers_dir, reports_dir, plots_dir):
        d.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {raw_dir}")
        sys.exit(1)

    # Instruments the downloader flagged as having no data for the period
    warning_files = sorted(f for f in raw_dir.glob("*.txt") if "[WARNING]" in f.name)

    all_outliers  = []
    summary_rows  = []

    for csv_path in csv_files:
        station_name  = csv_path.stem
        sampling_rate = _resolve_sampling_rate(csv_path, args.sampling_rate)
        print(f"\n--- {station_name}  [{sampling_rate}-min] ---")

        # 1. QC
        qc_df, outliers_df = run_qc(csv_path, sampling_rate)
        qc_df.to_csv(processed_dir / f"{station_name}_QC.csv", index=False)
        print(f"[qc] {len(qc_df)} rows after QC  |  {len(outliers_df)} values removed")
        if not outliers_df.empty:
            all_outliers.append(outliers_df)

        # 2. Stats
        row = summarize_station(station_name, qc_df, sampling_rate)
        summary_rows.append(row)
        print(f"[stats] uptime={row['overall_uptime']:.1%}  ({row['uptime_status']})")

        # 3. Plots
        uptime_info = calculate_uptime(qc_df, sampling_rate)
        plot_daily_uptime(station_name, uptime_info["daily_uptime"], plots_dir)
        plot_rainfall_accumulation(station_name, qc_df, RAIN_GAUGE_COLS, plots_dir)

    # Stub rows for instruments with no data
    for txt_path in warning_files:
        station_name = re.sub(r"_?\[WARNING\]$", "", txt_path.stem, flags=re.IGNORECASE)
        print(f"\n--- {station_name}  [NO DATA] ---")
        summary_rows.append({
            "station":        station_name,
            "expected_obs":   "N/A",
            "actual_obs":     "N/A",
            "overall_uptime": 0.0,
            "uptime_status":  "red",
        })

    # Save combined outlier table
    if all_outliers:
        combined = pd.concat(all_outliers, ignore_index=True)
        out_path = outliers_dir / "outliers.csv"
        combined.to_csv(out_path, index=False)
        print(f"\n[outliers] {len(combined)} total values removed — saved to {out_path}")

    # 4. Report
    report_path = reports_dir / "station_health_report.xlsx"
    generate_report(summary_rows, report_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
