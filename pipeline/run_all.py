"""Run the full pipeline end to end:  python pipeline/run_all.py"""
import runpy
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STEPS = ["01_clean_and_join", "02_match_state", "03_pressure_index", "04_expected_model",
         "05_player_ratings", "06_reliability_checks", "07_figures", "08_build_report",
         "09_rr_fit", "10_deck_data", "BUILD_DECK", "11_export_pdf", "12_dashboard_data", "13_local_dashboard"]

if __name__ == "__main__":
    for s in STEPS:
        t = time.time()
        print(f"\n===== {s} =====", flush=True)
        if s == "BUILD_DECK":   # Node + pptxgenjs (npm install inside deck/ once)
            subprocess.run(["node", str(HERE.parent / "deck" / "build_deck.js")], check=True)
        else:
            runpy.run_path(str(HERE / f"{s}.py"), run_name="__main__")
        print(f"----- {s} done in {time.time() - t:.1f}s", flush=True)
