"""Central configuration for the SupeRR Selector pressure-rating pipeline.

Every tunable number used anywhere in the pipeline lives here so that the
methodology report can quote it and a third party can reproduce the run.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"          # the supplied data pack (CSV files)
OUT = ROOT / "outputs"
INTER = OUT / "intermediate"
FIG = OUT / "figures"
RESULTS = OUT / "results"
SUBMISSION = ROOT / "submission"          # final deliverables (deck, report, offline dashboard)
REPORT_DIR = SUBMISSION
DOCS = ROOT / "docs"                      # GitHub Pages site (dashboard as index.html)
DECK_DATA = RESULTS / "deck_data.json"
for _d in (OUT, INTER, FIG, RESULTS, SUBMISSION, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

# ---------------------------------------------------------------- scope
# Problem statement: "historical IPL and T20 International (T20I) data".
# The pack also contains two A-team events (Emerging Teams Asia Cup 2024,
# Asia Cup Rising Stars 2025) tagged match_format == "T20". They are neither
# IPL nor T20I, so they are excluded.
EXCLUDED_COMPETITIONS = [
    "Mens T20 Emerging Teams Asia Cup 2024",
    "Asia Cup Rising Stars 2025",
]
NO_RESULT_LABELS = ["No Result", "Match Abandoned"]

# ---------------------------------------------------------------- encoding
# Verified in data: overs contain exactly 6 deliveries once these are removed.
ILLEGAL_EXTRAS = ["wide", "Overstep", "other"]   # Overstep / other = no-balls
NO_BALL_EXTRAS = ["Overstep", "other"]
# Bowler is charged wides + no-ball runs + bat runs; NOT byes / leg-byes / penalty.
# dismissal_type_id meanings are inferred (text column is empty):
#   1 bowled, 2 caught, 3 lbw, 4 run out, 5 stumped, 6 hit wicket, 9/10 rare non-bowler
BOWLER_CREDITED_DISMISSALS = [1, 2, 3, 5, 6]

# ---------------------------------------------------------------- pressure
CV_FOLDS = 5                     # match-grouped cross-fitting for all models
HIGH_PRESSURE_QUANTILE = 0.80    # top 20% of deliveries by Pressure Index = "high pressure"
LOW_PRESSURE_QUANTILE = 0.50     # bottom 50% = "ordinary" baseline (middle band ignored for baseline)
ELO_K = 24
ELO_START = 1500

# ---------------------------------------------------------------- ratings
MIN_BAT_PRESSURE_BALLS = 120     # balls faced in the high-pressure band
MIN_BAT_PRESSURE_INNINGS = 12    # innings with >=1 high-pressure ball faced
MIN_BAT_BASELINE_BALLS = 150
MIN_BOWL_PRESSURE_BALLS = 120    # deliveries bowled in the high-pressure band
MIN_BOWL_PRESSURE_MATCHES = 12
MIN_BOWL_BASELINE_BALLS = 150
MATCH_MIN_PRESSURE_BALLS = 3     # min pressure balls in a match for it to count toward consistency
CONSISTENCY_PRIOR_MATCHES = 6    # Beta prior strength for consistency shrinkage
# A pressure spell (one match) is a "delivery" if runs value >= -2 runs vs expectation.
# Chosen because it had the highest split-half reliability among the tested definitions
# (v>0, rv>0, v>-3, rv>-2, mean rv) for BOTH batters and bowlers - see report.
CONSISTENCY_TOLERANCE_RUNS = 2.0

# Final rating = weighted sum of z-scores (computed among eligible players)
WEIGHTS = {"pressure_level": 0.50, "pressure_delta": 0.25, "consistency": 0.25}

BOOTSTRAP_REPS = 300
TOP_N = 10
