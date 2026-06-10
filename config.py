# Directories — overridden by --raw-dir / --out-dir on the command line if provided.
RAW_DIR = "data/raw/Kenya-May2026"
OUT_DIR = "data"

# Prefix applied to all output files and sub-folders for this run.
# Overridden by --prefix on the command line if provided.
# Example: "Kenya_April2026"
PREFIX = "Kenya-May2026"

# Analysis period (YYYY-MM-DD, inclusive on both ends).
# Download raw data 1 day beyond DATA_END so that day's Total Prior gives
# the last analysis day's complete rainfall total.  Leave empty to use
# whatever date range is present in the raw files without clipping.
DATA_START = "2026-05-01"
DATA_END   = "2026-05-31"

SENTINEL_VALUE = -999.9

# Fallback sampling rate (minutes) used when rate cannot be inferred from the CSV
SAMPLING_RATE_DEFAULT = 1

# Rainfall thresholds
EXCESSIVE_RAINFALL_MM = 50.0       # single-period obs flagged as excessive
TIPPING_BUCKET_DEVIATION_MM = 10.0 # max acceptable difference between two rain gauges

# Uptime pass/fail threshold (0.0–1.0 fraction of expected observations)
UPTIME_PASS_THRESHOLD = 0.80   # >= 80% → green (pass), < 80% → red (fail)

# Rain gauge column names (adjust to match your portal's shortnames).
# Each entry is a list of candidate names for that gauge — the pipeline uses
# the first one that exists in a given file.  Add more variants as needed.
RAIN_GAUGE_COLS       = ["Rain Gauge 1 (mm)",         "Rain Gauge 2 (mm)"]
RAIN_GAUGE_PRIOR_COLS = [
    ["Rain Gauge 1 Total Prior (mm/day)", "Rain Gauge 1 Total Prior (mm)"],
    ["Rain Gauge 2 Total Prior (mm/day)", "Rain Gauge 2 Total Prior (mm)"],
]
RAIN_GAUGE_TODAY_COLS = [
    ["Rain Gauge 1 Total Today (mm/day)", "Rain Gauge 1 Total Today (mm)"],
    ["Rain Gauge 2 Total Today (mm/day)", "Rain Gauge 2 Total Today (mm)"],
]
