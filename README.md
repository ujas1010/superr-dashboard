# SupeRR Selector Season 2 · Round 1: Most Reliable Players Under Pressure

A data-driven system that measures how IPL and T20I batters and bowlers (2022–2026) perform in high-pressure match situations compared with their usual level, ranks the 10 most reliable batters and bowlers, and shows how each could strengthen Rajasthan Royals at the IPL 2027 auction.

**Live dashboard:** served from `docs/` by GitHub Pages.

## Results

| Rank | Batter | Bowler |
|---|---|---|
| 1 | Yashasvi Jaiswal | Taskin Ahmed |
| 2 | Travis Head | Matheesha Pathirana |
| 3 | Josh Inglis | Shaheen Afridi |
| 4 | Suryakumar Yadav | Mitchell Santner |
| 5 | Mitchell Marsh | Kuldeep Yadav |
| 6 | Kusal Mendis | Jasprit Bumrah |
| 7 | Rinku Singh | Varun Chakravarthy |
| 8 | Heinrich Klaasen | Rashid Khan |
| 9 | Pathum Nissanka | Lockie Ferguson |
| 10 | Dasun Shanaka | Mustafizur Rahman |

## Method in brief

1. **Match state.** Score, wickets, balls left, target and required rate are rebuilt before every delivery, with DLS revisions applied.
2. **Pressure Index.** A win-probability model, cross-fitted by match, estimates each side's chance of winning. A ball's pressure is its *leverage*: the expected swing in win probability over its possible outcomes. The top 20% of balls form the high-pressure band.
3. **Expected outcome.** Player-blind models estimate what an average player would do in the same situation (over, wickets, chase equation, IPL/T20I, team Elo, venue, pace/spin). Wickets are converted to runs with a run-expectancy model.
4. **Rating.** 50% pressure level, 25% change from the player's own ordinary-situation level, 25% consistency. All three are shrunk for sample size (empirical Bayes) and combined as z-scores.
5. **Reliability.** Split-half tests, 300 bootstrap resamples of matches and 10 sensitivity scenarios.
6. **Rajasthan Royals fit.** RR's pressure gaps by phase in IPL 2025–26 (death bowling ranks #9 of 10) weight each top-10 player's phase strengths.

Running the pipeline also builds the full methodology report, the slide deck (PDF + PPTX) and an offline copy of the dashboard in `submission/`.

## Project structure

```
├── data/raw/                 supplied data pack (not committed; place the CSVs here)
├── pipeline/                 all analysis code (Python)
│   ├── config.py             every path, threshold and weight
│   ├── 01_clean_and_join.py … 13_local_dashboard.py   steps, run in order
│   ├── ratings_lib.py        shared rating logic (shrinkage, components)
│   ├── templates/            dashboard page template
│   └── run_all.py            runs the whole pipeline
├── deck/                     slide-deck builder (Node + pptxgenjs, d3 for the dashboard)
├── outputs/
│   ├── results/              ratings, rankings, diagnostics (CSV/JSON)
│   ├── figures/              charts used in the report and deck
│   ├── dashboard/            dashboard data file
│   └── intermediate/         large per-ball tables (regenerated, not committed)
├── submission/               created by the pipeline: deck (PDF + PPTX), Word report, offline dashboard
├── docs/                     GitHub Pages site (index.html = the dashboard)
└── requirements.txt
```

## Reproduce

Requirements: Python 3.10+, Node 18+. Steps 11 (PDF export) needs Windows with PowerPoint.

```bash
pip install -r requirements.txt
cd deck && npm install && cd ..
# put the data pack CSVs in data/raw/
python pipeline/run_all.py        # about 2 minutes; rebuilds every number, chart and deliverable
```

All parameters are in `pipeline/config.py` (random seed 42). The analysis uses only the supplied data. The one outside fact, that Pakistan players have not played in the IPL since 2008, is labelled wherever it is used.
