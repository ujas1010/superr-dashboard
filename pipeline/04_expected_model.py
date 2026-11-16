"""Phase 4 - Context-adjusted expected outcomes and per-ball value.

Expected values come from player-blind models (no player identity used), cross-fitted
by match, conditioned on: innings, over, wickets, balls left, chase equation, current
run rate, competition (IPL/T20I), team strengths (Elo), venue scoring rate, pace/spin
and (bowler model only) the striker's batting position.

Wicket cost (in runs) = run expectancy with the wicket in hand minus run expectancy
without it, from a first-innings run-expectancy model.

  Batter value per ball faced   = (bat runs - xRuns)  - wicket_cost * (out - xOut)
  Bowler value per delivery     = (xConceded - conceded) + wicket_cost * (wicket - xWicket)

Positive = better than an average player in the identical situation.
Output: outputs/intermediate/balls_value.parquet
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

import config as C

CTX = ["innings", "over_no", "wkts_before", "balls_left", "runs_required", "rrr", "crr",
       "is_ipl", "bat_elo", "bowl_elo", "venue_rpb", "is_pace"]
BAT_F = CTX
BOWL_F = CTX + ["batting_order"]
RE_F = ["balls_left", "wkts_in_hand", "is_ipl", "venue_rpb", "balls_avail"]


def reg(loss="poisson", mono=None):
    return HistGradientBoostingRegressor(loss=loss, max_iter=250, learning_rate=0.05, max_leaf_nodes=31,
                                         min_samples_leaf=300, monotonic_cst=mono, random_state=C.RANDOM_SEED)


def clf():
    return HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=31,
                                          min_samples_leaf=300, random_state=C.RANDOM_SEED)


def main():
    b = pd.read_parquet(C.INTER / "balls_pressure.parquet")
    b["is_pace"] = (b["pace_or_spin"] == "Pace").astype(float)
    b.loc[b["pace_or_spin"].isna(), "is_pace"] = np.nan
    final = b.groupby(["match_id", "innings"])["total_runs"].transform("sum")
    b["runs_rest"] = final - b["runs_before"]

    for col in ["x_bat_runs", "x_out", "x_bowl_runs", "x_bowl_wkt", "re_keep", "re_lose"]:
        b[col] = np.nan
    diag = {"auc_out": [], "auc_bowl_wkt": []}

    for f in range(C.CV_FOLDS):
        tr = (b["fold"] != f).values
        te = (b["fold"] == f).values
        fc = tr & (b["faced"].values == 1)
        tf = te & (b["faced"].values == 1)

        m = reg().fit(b.loc[fc, BAT_F], b.loc[fc, "runs"])
        b.loc[tf, "x_bat_runs"] = m.predict(b.loc[tf, BAT_F])
        m = clf().fit(b.loc[fc, BAT_F], b.loc[fc, "striker_out"])
        b.loc[tf, "x_out"] = m.predict_proba(b.loc[tf, BAT_F])[:, 1]
        diag["auc_out"].append(roc_auc_score(b.loc[tf, "striker_out"], b.loc[tf, "x_out"]))

        m = reg().fit(b.loc[tr, BOWL_F], b.loc[tr, "bowler_runs"])
        b.loc[te, "x_bowl_runs"] = m.predict(b.loc[te, BOWL_F])
        m = clf().fit(b.loc[tr, BOWL_F], b.loc[tr, "bowler_wicket"])
        b.loc[te, "x_bowl_wkt"] = m.predict_proba(b.loc[te, BOWL_F])[:, 1]
        diag["auc_bowl_wkt"].append(roc_auc_score(b.loc[te, "bowler_wicket"], b.loc[te, "x_bowl_wkt"]))

        # run expectancy from first innings (unconstrained by a target)
        r1 = tr & (b["innings"].values == 1)
        re = reg(loss="squared_error", mono=[1, 1, 0, 1, 0]).fit(b.loc[r1, RE_F], b.loc[r1, "runs_rest"])
        post = b.loc[te, RE_F].copy()
        post["balls_left"] = b.loc[te, "balls_left_after"].values
        keep = post.copy()
        keep["wkts_in_hand"] = b.loc[te, "wkts_in_hand"].values
        lose = post.copy()
        lose["wkts_in_hand"] = b.loc[te, "wkts_in_hand"].values - 1
        b.loc[te, "re_keep"] = re.predict(keep)
        b.loc[te, "re_lose"] = np.where(lose["wkts_in_hand"].values <= 0, 0.0, re.predict(lose))

    b["wicket_cost"] = (b["re_keep"] - b["re_lose"]).clip(lower=0)
    fc = b["faced"] == 1
    b["bat_value"] = np.where(fc, (b["runs"] - b["x_bat_runs"]) - b["wicket_cost"] * (b["striker_out"] - b["x_out"]), np.nan)
    b["bowl_value"] = (b["x_bowl_runs"] - b["bowler_runs"]) + b["wicket_cost"] * (b["bowler_wicket"] - b["x_bowl_wkt"])
    # components (shrunk separately in phase 5 because their reliabilities differ greatly)
    b["bat_rv"] = np.where(fc, b["runs"] - b["x_bat_runs"], np.nan)
    b["bat_wv"] = np.where(fc, -b["wicket_cost"] * (b["striker_out"] - b["x_out"]), np.nan)
    b["bowl_rv"] = b["x_bowl_runs"] - b["bowler_runs"]
    b["bowl_wv"] = b["wicket_cost"] * (b["bowler_wicket"] - b["x_bowl_wkt"])

    out = {
        "mean_bat_value_per_ball": round(float(b.loc[fc, "bat_value"].mean()), 4),
        "mean_bowl_value_per_ball": round(float(b["bowl_value"].mean()), 4),
        "x_bat_runs_vs_actual": [round(float(b.loc[fc, "x_bat_runs"].mean()), 4), round(float(b.loc[fc, "runs"].mean()), 4)],
        "x_out_vs_actual": [round(float(b.loc[fc, "x_out"].mean()), 4), round(float(b.loc[fc, "striker_out"].mean()), 4)],
        "x_bowl_runs_vs_actual": [round(float(b["x_bowl_runs"].mean()), 4), round(float(b["bowler_runs"].mean()), 4)],
        "x_bowl_wkt_vs_actual": [round(float(b["x_bowl_wkt"].mean()), 4), round(float(b["bowler_wicket"].mean()), 4)],
        "auc_striker_out": round(float(np.mean(diag["auc_out"])), 4),
        "auc_bowler_wicket": round(float(np.mean(diag["auc_bowl_wkt"])), 4),
        "wicket_cost_by_phase": b.groupby("phase")["wicket_cost"].mean().round(2).to_dict(),
        "wicket_cost_by_band": b.groupby("pressure_band")["wicket_cost"].mean().round(2).to_dict(),
    }
    (C.RESULTS / "04_expected_model.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    b.to_parquet(C.INTER / "balls_value.parquet", index=False)


if __name__ == "__main__":
    main()
