SENTINEL_VALUE = -999.9

# Default sampling rate (minutes) used when an instrument ID can't be resolved
SAMPLING_RATE_DEFAULT = 1

# Instruments that report at a non-default rate.
# Instruments 1–29 are 15-minute; everything else is 1-minute.
SAMPLING_RATE_OVERRIDES: dict[int, int] = {i: 15 for i in range(1, 30)}

# Rainfall thresholds
EXCESSIVE_RAINFALL_MM = 50.0       # single-period obs flagged as excessive
TIPPING_BUCKET_DEVIATION_MM = 10.0 # max acceptable difference between two rain gauges

# Uptime thresholds (0.0–1.0 fraction of expected observations)
UPTIME_GREEN  = 0.90   # >= 90%
UPTIME_YELLOW = 0.80   # >= 80%, < 90%
                       # < 80% → red

# Rain gauge column names (adjust to match your portal's shortnames)
RAIN_GAUGE_COLS = ["Rain Gauge 1 (mm)", "Rain Gauge 2 (mm)"]  # primary and secondary tipping bucket columns
