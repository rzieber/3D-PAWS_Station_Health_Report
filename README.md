# 3D-PAWS Station Health Report

Generates a monthly health report for 3D-PAWS weather station networks. For each instrument in a CHORDS portal the pipeline produces a color-coded Excel summary, a monthly uptime bar chart, per-instrument daily rainfall bar charts, and side-by-side monthly rainfall comparison charts.

---

## Requirements

- Python 3.10+
- `pandas`, `numpy`, `matplotlib`, `openpyxl`

```bash
pip install -r requirements.txt
```

---

## Quick start

1. Edit `config.py` for your run (see [Configuration](#configuration) below).
2. Place raw CSVs in your `RAW_DIR` folder.
3. Run:

```bash
python3 run_pipeline.py
```

All output locations are controlled by `config.py`. No command-line arguments are required unless you want to override a setting for a one-off run.

---

## Workflow

### Step 1 — Download raw data

Use the [CHORDS Data Downloader](https://github.com/3d-paws/CHORDS_Data_Downloader) to download one CSV per instrument for the reporting month.

**Important — download one day beyond your period end for accurate rainfall:**
The pipeline computes daily rainfall totals from the `Rain Gauge X Total Prior (mm/day)` column, which holds the *previous* day's complete total. To get a reliable total for the last day of your analysis period (e.g. April 30), download data through May 1. The May 1 `Total Prior` value gives April 30's complete total without relying on potentially incomplete intraday transmissions.

Set `DATA_START` and `DATA_END` in `config.py` so the pipeline clips statistics and rainfall totals to your intended analysis window and discards the extra day automatically.

**Instruments with no data** produce a `[WARNING].txt` file from the downloader. Leave these in `RAW_DIR` alongside the CSVs — the pipeline includes them in the report with 0% uptime and blank rainfall values.

Place all files for a given run in a dedicated subfolder:

```
data/raw/
└── Kenya-April2026/
    ├── FEWSNET_Instrument-1_2026-04-01_2026-05-01.csv
    ├── FEWSNET_Instrument-2_2026-04-01_2026-05-01.csv
    ├── FEWSNET_Instrument-5_2026-04-01_2026-05-01_[WARNING].txt
    └── ...
```

### Step 2 — Configure `config.py`

Open `config.py` and set the values for your run. See [Configuration](#configuration) for a full description of every setting. At minimum, set:

```python
RAW_DIR    = "data/raw/Kenya-April2026"
PREFIX     = "Kenya-April2026"
DATA_START = "2026-04-01"
DATA_END   = "2026-04-30"
```

### Step 3 — Run the pipeline

```bash
python3 run_pipeline.py
```

Progress is printed to the terminal as each instrument is processed. When complete you will see `Done.`

### Step 4 — Review outputs

With `PREFIX = "Kenya-April2026"` and `OUT_DIR = "data"` the pipeline writes:

```
data/
├── processed/
│   └── Kenya-April2026/
│       └── Kenya-April2026_FEWSNET_Instrument-1_..._QC.csv   (one per instrument)
├── outliers/
│   └── Kenya-April2026_outliers.csv
├── reports/
│   └── Kenya-April2026_station_health_report.xlsx
└── plots/
    └── Kenya-April2026/
        ├── Kenya-April2026_monthly_uptime.png
        ├── Kenya-April2026_monthly_rainfall_totals.png
        ├── Kenya-April2026_monthly_rainfall_totals_scaled.png
        ├── Kenya-April2026_FEWSNET_Instrument-1_..._rainfall.png
        └── ...
```

Running the pipeline again for a different country or month only requires updating `config.py`. Each run's outputs are isolated by their prefix subfolder and filename prefix and will not overwrite previous runs.

---

## Configuration

All settings live in `config.py`. The table below describes every option.

### Run identity

| Setting | Example | Description |
|---|---|---|
| `RAW_DIR` | `"data/raw/Kenya-April2026"` | Folder containing raw CSVs and WARNING files for this run. Overridden by `--raw-dir` on the command line. |
| `OUT_DIR` | `"data"` | Root output folder. Sub-folders are created automatically. Overridden by `--out-dir`. |
| `PREFIX` | `"Kenya-April2026"` | String prepended to all output filenames and used as a subfolder name inside `processed/` and `plots/`. Keeps each country/month run isolated. Overridden by `--prefix`. |

### Analysis period

| Setting | Example | Description |
|---|---|---|
| `DATA_START` | `"2026-04-01"` | First day of the analysis period (inclusive, YYYY-MM-DD). Used to clip QC data before computing uptime so an extra downloaded day does not count toward expected observations. Leave empty to use the full date range in the raw files. |
| `DATA_END` | `"2026-04-30"` | Last day of the analysis period (inclusive, YYYY-MM-DD). Used to clip both uptime statistics and the daily rainfall series. Leave empty to use the full date range. |

> **Tip:** Set `DATA_END` to the last day of the month you are reporting on and download raw data through `DATA_END + 1 day`. The extra day's `Total Prior` column supplies the final day's complete rainfall total, and the extra day is then automatically excluded from all outputs.

### QC settings

| Setting | Default | Description |
|---|---|---|
| `SENTINEL_VALUE` | `-999.9` | Sensor error code. Any value exactly equal to this is replaced with `NaN` and recorded in the outliers file. |
| `SAMPLING_RATE_DEFAULT` | `1` | Fallback sampling rate in minutes, used only when the rate cannot be inferred from the CSV. The pipeline normally detects the sampling rate automatically by reading the first 100 rows of each file. |

### Uptime

| Setting | Default | Description |
|---|---|---|
| `UPTIME_PASS_THRESHOLD` | `0.80` | Fraction of expected observations (0.0–1.0). Instruments at or above this threshold are marked **green (pass)**; below it are marked **red (fail)**. |

### Rain gauge columns

These must exactly match the column shortnames exported by your CHORDS portal.

| Setting | Default | Description |
|---|---|---|
| `RAIN_GAUGE_COLS` | `["Rain Gauge 1 (mm)", "Rain Gauge 2 (mm)"]` | Instantaneous tip columns. Used as display labels in the monthly rainfall summary chart. |
| `RAIN_GAUGE_PRIOR_COLS` | `["Rain Gauge 1 Total Prior (mm/day)", "Rain Gauge 2 Total Prior (mm/day)"]` | Previous day's complete daily total. Primary source for all rainfall calculations. |
| `RAIN_GAUGE_TODAY_COLS` | `["Rain Gauge 1 Total Today (mm/day)", "Rain Gauge 2 Total Today (mm/day)"]` | Intraday accumulation. Used only as a fallback for the last day in the dataset when no following day's `Total Prior` is available. |

---

## Output reference

### Excel report — `*_station_health_report.xlsx`

One row per instrument, sorted numerically by instrument ID. Instruments flagged as having no data (WARNING files) appear at the correct position with 0% uptime and blank rainfall values.

| Column | Description |
|---|---|
| Station | Full station name from the raw filename |
| Expected Obs | Number of expected observations based on the inferred sampling rate |
| Actual Obs | Number of rows containing at least one real (non-NaN) sensor reading |
| Overall Uptime | `Actual Obs / Expected Obs` as a percentage |
| Rain Gauge 1 Total (mm) | Sum of daily rainfall totals for the period (from `Total Prior`) |
| Rain Gauge 2 Total (mm) | Same for gauge 2 |
| Rainfall % Diff | `|RG1 − RG2| / avg(RG1, RG2) × 100` — large values indicate a disagreement between gauges |

The Overall Uptime cell is color-coded: **green** ≥ 80% (pass), **red** < 80% (fail).

### Plots

| File | Description |
|---|---|
| `*_monthly_uptime.png` | Single bar chart: one bar per instrument showing overall monthly uptime. Bars are green (pass) or red (fail). Instruments sorted numerically. |
| `*_monthly_rainfall_totals.png` | Grouped bar chart: Rain Gauge 1 vs Rain Gauge 2 total (mm) per instrument. Full auto-scaled y-axis. |
| `*_monthly_rainfall_totals_scaled.png` | Same chart with y-axis capped at 300 mm for easy comparison when one instrument dominates the scale. |
| `*_FEWSNET_Instrument-N_..._rainfall.png` | Per-instrument grouped daily bar chart: Rain Gauge 1 vs Rain Gauge 2 for each calendar day. Derived from `Total Prior` values. |

### Processed CSVs — `processed/<PREFIX>/`

One QC'd CSV per instrument. Contains the same columns as the raw file with:
- Timestamps normalized to a `time` column
- Exact duplicate rows removed
- Missing timestamps inserted as NaN rows (gap-filled)
- Sentinel values (`-999.9`) replaced with NaN

### Outliers — `*_outliers.csv`

Every value removed during QC across all instruments, with columns: `station`, `time`, `variable`, `original_value`, `reason`.

---

## Command-line overrides

All `config.py` settings can be left as-is and overridden at the command line for one-off runs without editing the file:

```bash
python3 run_pipeline.py \
  --raw-dir  data/raw/Ethiopia-May2026 \
  --out-dir  data \
  --prefix   Ethiopia-May2026 \
  --sampling-rate 15
```

| Flag | Overrides | Description |
|---|---|---|
| `--raw-dir` | `RAW_DIR` | Path to raw CSV folder |
| `--out-dir` | `OUT_DIR` | Root output folder |
| `--prefix` | `PREFIX` | Output prefix and subfolder name |
| `--sampling-rate` | Auto-detection | Force a single sampling rate (minutes) for all instruments |

---

## Pipeline internals

### Sampling rate detection (`pipeline/qc.py`)

The pipeline reads the first 100 rows of each CSV, computes the median of consecutive timestamp differences, and rounds to the nearest whole minute. This means no per-instrument configuration is needed even when instruments in the same portal report at different rates. The `SAMPLING_RATE_DEFAULT` fallback is only used if detection fails (e.g. a file with fewer than two valid timestamps).

### QC steps (`pipeline/qc.py`)

Applied to each raw CSV in order:

1. Normalize the timestamp column name to `time`
2. Sort rows by timestamp
3. Remove exact duplicate rows (all columns identical)
4. Insert NaN rows for any missing timestamps at the inferred sampling rate (gap-fill)
5. Replace sentinel values (`-999.9`) with NaN

### Rainfall calculation (`pipeline/stats.py`)

Daily totals are derived from `Rain Gauge X Total Prior (mm/day)`:

- For each day D in the dataset (except the last): daily total = the `Total Prior` value read from any observation on day D+1, which holds D's complete 24-hour total.
- For the last day in the dataset: falls back to `max(Total Today)` on that day, since no following day exists.
- If `DATA_END` is set, the series is clipped so that any extra "future" day downloaded for its `Total Prior` value does not appear in totals or plots.
- The first day's own `Total Prior` value (= the previous month's final day) is discarded.

### Uptime calculation (`pipeline/stats.py`)

```
uptime = rows with at least one non-NaN sensor reading / total rows after gap-filling
```

If `DATA_START` / `DATA_END` are set, the gap-filled dataframe is clipped to that window before uptime is computed.

### Adding new metrics

- **`pipeline/stats.py`** — implement the stub functions (`flag_excessive_rainfall`, `flag_stuck_bucket`, `flag_bucket_deviation`) and add results to `summarize_station()`
- **`pipeline/report.py`** — add new column names to `_HEADER_NAMES` for readable headers and to `_COLOR_MAP` to get automatic cell color-coding
- **`pipeline/plots.py`** — add new plot functions and call them from `run_pipeline.py`
