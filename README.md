# Fews Net 3D-PAWS Station Health Report

Generates a monthly weather station health report to discuss with the team at CHC. For each instrument in a CHORDS portal, the pipeline produces a color-coded Excel summary, daily uptime bar charts, and cumulative rainfall plots to help identify maintenance issues.

---

## Requirements

- Python 3.10+
- `pandas`, `numpy`, `matplotlib`, `openpyxl`

```bash
pip install -r requirements.txt
```

---

## Workflow

### Step 1 — Download data

Use the [CHORDS Data Downloader](https://github.com/3d-paws/CHORDS_Data_Downloader) to download one CSV per instrument for the reporting month. Place all downloaded files in `data/raw/`. Create subdirectories as needed for multiple CHORDS portals (e.g. Kenya, Zimbabwe, Malawi). Just redirect the script to these subdirectories.

Instruments with no data for the period will produce a `[WARNING].txt` file. Leave these in `data/raw/` alongside the CSVs — the pipeline reads them to include those instruments in the report with 0% uptime.

### Step 2 — Run the pipeline

```bash
python3 run_pipeline.py --raw-dir data/raw --out-dir data
```

To force a single sampling rate across all files (useful for testing):

```bash
python3 run_pipeline.py --raw-dir data/raw --out-dir data --sampling-rate 15
```

### Step 3 — Review outputs

| Path | Contents |
|---|---|
| `data/processed/` | QC'd CSV per instrument |
| `data/outliers/outliers.csv` | Every value removed during QC and why |
| `data/reports/station_health_report.xlsx` | Color-coded summary, one row per instrument |
| `data/plots/` | Uptime bar chart + rainfall accumulation chart per instrument |

---

## Pipeline stages

### 1. QC (`pipeline/qc.py`)

Applied to each raw CSV before any analysis:

- **Timestamp normalization** — column named `Time` or `time` is standardized to `time`
- **Sort & deduplicate** — rows sorted by timestamp; exact duplicates removed
- **Gap filling** — missing timestamps inserted as NaN rows so the time index is gap-free
- **Sentinel removal** — values equal to `-999.9` replaced with `NaN`

All removed values (duplicates and sentinels) are recorded in `data/outliers/outliers.csv` with columns: `station`, `time`, `variable`, `original_value`, `reason`.

### 2. Statistics (`pipeline/stats.py`)

**Station uptime** — the fraction of expected observations that contain at least one real (non-NaN) sensor reading:

```
uptime = actual observations / expected observations
```

Computed overall for the month and per day.

### 3. Report (`pipeline/report.py`)

Writes `station_health_report.xlsx`. Each row is one instrument, sorted numerically by instrument ID. Instruments with no data show `N/A` for observation counts and 0% uptime.

**Uptime color coding:**

| Color | Threshold |
|---|---|
| Green | ≥ 90% |
| Yellow | ≥ 80%, < 90% |
| Red | < 80% |

### 4. Plots (`pipeline/plots.py`)

- **Daily uptime bar chart** — one bar per day, colored green/yellow/red by threshold
- **Rainfall accumulation** — cumulative time series for each rain gauge column

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `SENTINEL_VALUE` | `-999.9` | Sensor error code replaced with NaN |
| `SAMPLING_RATE_DEFAULT` | `1` | Minutes between observations (fallback) |
| `SAMPLING_RATE_OVERRIDES` | `{1–29: 15}` | Per-instrument rate overrides |
| `UPTIME_GREEN` | `0.90` | Uptime fraction threshold for green |
| `UPTIME_YELLOW` | `0.80` | Uptime fraction threshold for yellow |
| `RAIN_GAUGE_COLS` | `["Rain Gauge 1 (mm)", "Rain Gauge 2 (mm)"]` | Column names for tipping bucket gauges |
| `EXCESSIVE_RAINFALL_MM` | `50.0` | Single-period rainfall flag threshold (unused until next release) |
| `TIPPING_BUCKET_DEVIATION_MM` | `10.0` | Max acceptable difference between gauges (unused until next release) |

### Sampling rates

Instruments 1–29 report every 15 minutes; all others report every minute. This is controlled by `SAMPLING_RATE_OVERRIDES` in `config.py`. To add or change a rate for a specific instrument:

```python
SAMPLING_RATE_OVERRIDES = {
    **{i: 15 for i in range(1, 30)},
    55: 5,   # example: instrument 55 reports every 5 minutes
}
```

---

## Adding new metrics

After each monthly meeting, new metrics can be added to the report. The intended extension points are:

- **`pipeline/stats.py`** — implement the stub functions (`flag_excessive_rainfall`, `flag_stuck_bucket`, `flag_bucket_deviation`) and add their results to `summarize_station()`
- **`pipeline/report.py`** — add new column names to `_COLOR_MAP` with their corresponding status column to get automatic color coding
- **`pipeline/plots.py`** — add new plot functions and call them from `run_pipeline.py`
