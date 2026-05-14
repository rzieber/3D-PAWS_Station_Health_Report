SENTINEL_VALUE = -999.99
SAMPLING_RATE = 1  # minutes

# Rainfall thresholds
EXCESSIVE_RAINFALL_MM = 50.0       # single-period obs flagged as excessive
TIPPING_BUCKET_DEVIATION_MM = 10.0 # max acceptable difference between two rain gauges

# Uptime thresholds (0.0–1.0 fraction of expected observations)
UPTIME_GREEN  = 0.95   # >= 95%
UPTIME_YELLOW = 0.80   # >= 80%, < 95%
                       # < 80% → red

# Rain gauge column names (adjust to match your portal's shortnames)
RAIN_GAUGE_COLS = ["rs", "rs2"]  # primary and secondary tipping bucket columns
