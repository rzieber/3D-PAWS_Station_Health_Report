import re
import math
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows


def _instrument_sort_key(row: dict) -> int:
    match = re.search(r"Instrument-(\d+)", row.get("station", ""), re.IGNORECASE)
    return int(match.group(1)) if match else float("inf")


# Hex fills for cell status colors
_FILLS = {
    "green":  PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
    "red":    PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    "header": PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid"),
}

# Human-readable header overrides (columns not listed fall back to title-cased snake_case)
_HEADER_NAMES = {
    "station":               "Station",
    "expected_obs":          "Expected Obs",
    "actual_obs":            "Actual Obs",
    "overall_uptime":        "Overall Uptime",
    "rain_gauge_1_total":    "Rain Gauge 1 Total (mm)",
    "rain_gauge_2_total":    "Rain Gauge 2 Total (mm)",
    "rainfall_pct_diff":     "Rainfall % Diff",
    "rain_gauge_corr":       "Rain Gauge Correlation",
    "rain_gauge_max_diff":   "Max Daily Diff (mm)",
    "rain_gauge_max_diff_day": "Max Diff Date",
    "rain_gauge_1_zero_days": "Rain Gauge 1 Zero-Rain Days",
    "rain_gauge_2_zero_days": "Rain Gauge 2 Zero-Rain Days",
}

# Which columns get color-coded and what their status column is named
# Format: { data_column: status_column }
# The status column is expected to hold 'green' | 'yellow' | 'red'
_COLOR_MAP = {
    "overall_uptime": "uptime_status",
}


def generate_report(summary_rows: list[dict], output_path: Path) -> None:
    """
    Write a color-formatted Excel workbook from a list of per-station summary dicts.

    Each dict should be the output of stats.summarize_station().
    Status columns (e.g. 'uptime_status') drive cell color; they are hidden
    from the sheet after coloring.
    """
    summary_rows = sorted(summary_rows, key=_instrument_sort_key)
    df = pd.DataFrame(summary_rows)

    # Columns to hide after they've been used for coloring
    status_cols = set(_COLOR_MAP.values())
    display_cols = [c for c in df.columns if c not in status_cols]

    wb = Workbook()
    ws = wb.active
    ws.title = "Station Health"

    header_font = Font(bold=True, color="FFFFFF")

    # Write header row
    for col_idx, col_name in enumerate(display_cols, start=1):
        cell = ws.cell(row=1, column=col_idx, value=_HEADER_NAMES.get(col_name, col_name.replace("_", " ").title()))
        cell.fill = _FILLS["header"]
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Write data rows (convert NaN → None so cells are blank, not "nan")
    for row_idx, row in enumerate(df[display_cols].itertuples(index=False), start=2):
        for col_idx, value in enumerate(row, start=1):
            if isinstance(value, float) and math.isnan(value):
                value = "N/A"
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Apply color coding
    for data_col, status_col in _COLOR_MAP.items():
        if data_col not in display_cols or status_col not in df.columns:
            continue
        col_idx = display_cols.index(data_col) + 1
        for row_idx, status in enumerate(df[status_col], start=2):
            fill = _FILLS.get(status)
            if fill:
                ws.cell(row=row_idx, column=col_idx).fill = fill

    # Auto-size columns
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = max_len + 4

    wb.save(output_path)
    print(f"[report] Saved: {output_path}")
