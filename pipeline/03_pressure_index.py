"""Phase 3 - Pressure Index.

1. Win-probability (WP) model for each innings, cross-fitted by match
   (a match is never scored by a model that saw it).
2. Leverage = expected absolute swing in WP caused by the next delivery,
   using the league outcome distribution for that over and innings.
3. Pressure Index (PI) = leverage / mean leverage  (1.0 = average delivery).
   High pressure = top 20% of deliveries by PI; ordinary = bottom 50%.
4. An alternative rule-based index (RRR / wickets / stage) is also built for
   sensitivity testing in phase 6.
Output: outputs/intermediate/balls_pressure.parquet
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

import config as C

F1 = ["runs_before", "balls_left", "wkts_in_hand", "balls_avail", "is_ipl", "elo_diff", "venue_rpb"]
M1 = [1, 1, 1, 0, 0, 1, 0]
F2 = ["runs_required", "balls_left", "wkts_in_hand", "is_ipl", "elo_diff", "venue_rpb"]
M2 = [-1, 1, 1, 0, 1, 0]
# outcome categories: (total runs, wicket, legal)
OUTCOMES = {"dot": (0, 0, 1), "one": (1, 0, 1), "two": (2, 0, 1), "three": (3, 0, 1),
            "four": (4, 0, 1), "six": (6, 0, 1), "wicket": (0, 1, 1), "wide": (1, 0, 0)}


def make_model(mono):
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                          min_samples_leaf=200, l2_regularization=1.0,
                                          monotonic_cst=mono, random_state=C.RANDOM_SEED)


def classify_outcome(df):
    o = np.full(len(df), "dot", dtype=object)
    tr, w, lg = df["total_runs"].values, df["team_wicket"].values, df["is_legal"].values
    o[(lg == 1) & (tr == 1)] = "one"
    o[(lg == 1) & (tr == 2)] = "two"
    o[(lg == 1) & (tr == 3)] = "three"
    o[(lg == 1) & (tr >= 4) & (tr < 6)] = "four"
    o[(lg == 1) & (tr >= 6)] = "six"
    o[lg == 0] = "wide"
    o[w == 1] = "wicket"
    return o


def main():
    b = pd.read_parquet(C.INTER / "balls_state.parquet")
    rng = np.random.default_rng(C.RANDOM_SEED)
    mids = b["match_id"].unique()
    fold_of = dict(zip(mids, rng.integers(0, C.CV_FOLDS, len(mids))))
    b["fold"] = b["match_id"].map(fold_of)
    # opposing-team view (used to turn an end-of-innings-1 state into the chase start)
    b["elo_diff_opp"] = -b["elo_diff"]
    inn2_avail = b[b["innings"] == 2].groupby("match_id")["balls_avail"].first()
    b["avail2"] = b["match_id"].map(inn2_avail).fillna(b["balls_avail"])

    # ---------------- outcome distribution per innings x over
    b["outcome"] = classify_outcome(b)
    dist = (b.groupby(["innings", "over_no"])["outcome"].value_counts(normalize=True)
              .unstack(fill_value=0).reindex(columns=list(OUTCOMES), fill_value=0))

    wp_now = np.zeros(len(b))
    lev = np.zeros(len(b))
    metrics = {}
    oof_true, oof_pred = {1: [], 2: []}, {1: [], 2: []}

    for f in range(C.CV_FOLDS):
        tr = b["fold"] != f
        te = (b["fold"] == f).values
        m1 = make_model(M1).fit(b.loc[tr & (b.innings == 1), F1], b.loc[tr & (b.innings == 1), "bat_team_won"])
        m2 = make_model(M2).fit(b.loc[tr & (b.innings == 2), F2], b.loc[tr & (b.innings == 2), "bat_team_won"])

        def wp2(rr, bl, wk, ipl, elo, ven):
            X = pd.DataFrame({"runs_required": rr, "balls_left": bl, "wkts_in_hand": wk,
                              "is_ipl": ipl, "elo_diff": elo, "venue_rpb": ven})
            p = m2.predict_proba(X)[:, 1]
            p = np.where(rr <= 0, 1.0, p)
            p = np.where((rr > 0) & ((wk <= 0) | (bl <= 0)), 0.0, p)
            return p

        def wp1(rb, bl, wk, d):
            X = pd.DataFrame({"runs_before": rb, "balls_left": bl, "wkts_in_hand": wk,
                              "balls_avail": d["balls_avail"].values, "is_ipl": d["is_ipl"].values,
                              "elo_diff": d["elo_diff"].values, "venue_rpb": d["venue_rpb"].values})
            p = m1.predict_proba(X)[:, 1]
            end = (wk <= 0) | (bl <= 0)
            if end.any():   # innings over -> WP = 1 - chasing side's WP at the start of the chase
                p_end = 1 - wp2(rb + 1, d["avail2"].values, np.full(len(d), 10), d["is_ipl"].values,
                                d["elo_diff_opp"].values, d["venue_rpb"].values)
                p = np.where(end, p_end, p)
            return p

        for inn in (1, 2):
            idx = np.where(te & (b["innings"].values == inn))[0]
            d = b.iloc[idx]
            probs = dist.loc[inn].reindex(d["over_no"].values).values      # n x outcomes
            if inn == 1:
                now = wp1(d["runs_before"].values, d["balls_left"].values, d["wkts_in_hand"].values, d)
            else:
                now = wp2(d["runs_required"].values, d["balls_left"].values, d["wkts_in_hand"].values,
                          d["is_ipl"].values, d["elo_diff"].values, d["venue_rpb"].values)
            swing = np.zeros(len(d))
            for k, (runs, wk, legal) in enumerate(OUTCOMES.values()):
                bl2 = d["balls_left"].values - legal
                wk2 = d["wkts_in_hand"].values - wk
                if inn == 1:
                    post = wp1(d["runs_before"].values + runs, bl2, wk2, d)
                else:
                    post = wp2(d["runs_required"].values - runs, bl2, wk2, d["is_ipl"].values,
                               d["elo_diff"].values, d["venue_rpb"].values)
                swing += probs[:, k] * np.abs(post - now)
            wp_now[idx] = now
            lev[idx] = swing
            oof_true[inn].append(d["bat_team_won"].values)
            oof_pred[inn].append(now)

    for inn in (1, 2):
        y, p = np.concatenate(oof_true[inn]), np.clip(np.concatenate(oof_pred[inn]), 1e-4, 1 - 1e-4)
        metrics[f"wp_innings{inn}"] = {"auc": round(roc_auc_score(y, p), 4),
                                       "brier": round(brier_score_loss(y, p), 4),
                                       "log_loss": round(log_loss(y, p), 4)}
    b["wp"] = wp_now
    b["leverage"] = lev
    b["pressure_index"] = lev / lev.mean()
    hi = b["pressure_index"].quantile(C.HIGH_PRESSURE_QUANTILE)
    lo = b["pressure_index"].quantile(C.LOW_PRESSURE_QUANTILE)
    b["pressure_band"] = np.select([b["pressure_index"] >= hi, b["pressure_index"] <= lo],
                                   ["High", "Ordinary"], "Moderate")
    metrics["pi_high_threshold"] = round(float(hi), 4)
    metrics["pi_ordinary_threshold"] = round(float(lo), 4)

    # calibration table (OOF) for the report
    cal = pd.DataFrame({"p": np.concatenate(oof_pred[1] + oof_pred[2]),
                        "y": np.concatenate(oof_true[1] + oof_true[2])})
    cal["bin"] = pd.cut(cal["p"], np.linspace(0, 1, 11), include_lowest=True)
    cal.groupby("bin", observed=True).agg(pred=("p", "mean"), actual=("y", "mean"), n=("y", "size")) \
       .to_csv(C.RESULTS / "03_wp_calibration.csv")

    # ---------------- alternative rule-based index (sensitivity only)
    rrr = b["rrr"].clip(0, 36)
    wl = 10 - b["wkts_in_hand"]
    stage = b["legal_before"] / b["balls_avail"]
    alt2 = (0.45 * rrr.rank(pct=True) + 0.30 * wl.rank(pct=True) + 0.25 * stage)
    alt2 = np.where((b["rrr"] > 18) | (b["runs_required"] <= 0), alt2 * 0.3, alt2)  # lost / won causes
    # first innings: wickets lost relative to stage (collapse) + death overs
    collapse = (wl - 10 * stage).clip(lower=0) / 10
    alt1 = 0.5 * collapse.rank(pct=True) + 0.5 * stage
    b["alt_pressure_index"] = np.where(b["innings"] == 2, alt2, alt1 * 0.8)  # chases weighted higher
    b["alt_pressure_index"] = b["alt_pressure_index"] / b["alt_pressure_index"].mean()

    # ---------------- validation: outcomes by pressure decile
    b["pi_decile"] = pd.qcut(b["pressure_index"].rank(method="first"), 10, labels=range(1, 11)).astype(int)
    leg = b[b["is_legal"] == 1]
    val = leg.groupby("pi_decile").agg(
        mean_pi=("pressure_index", "mean"), balls=("is_legal", "size"),
        run_rate=("total_runs", lambda s: s.mean() * 6), dot_pct=("total_runs", lambda s: (s == 0).mean() * 100),
        boundary_pct=("is_boundary", lambda s: s.mean() * 100), wicket_pct=("team_wicket", lambda s: s.mean() * 100),
        pct_second_innings=("innings", lambda s: (s == 2).mean() * 100),
        pct_death=("phase", lambda s: (s == "Death").mean() * 100)).round(2)
    val.to_csv(C.RESULTS / "03_pressure_validation_by_decile.csv")
    band = leg.groupby("pressure_band").agg(
        balls=("is_legal", "size"), run_rate=("total_runs", lambda s: s.mean() * 6),
        dot_pct=("total_runs", lambda s: (s == 0).mean() * 100),
        boundary_pct=("is_boundary", lambda s: s.mean() * 100),
        wicket_pct=("team_wicket", lambda s: s.mean() * 100),
        mean_abs_wp_from_half=("wp", lambda s: (s - 0.5).abs().mean())).round(3)
    band.to_csv(C.RESULTS / "03_pressure_band_summary.csv")
    metrics["band_summary"] = band.reset_index().to_dict(orient="records")
    (C.RESULTS / "03_pressure_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps(metrics, indent=2, default=str))
    print(val)

    b.to_parquet(C.INTER / "balls_pressure.parquet", index=False)


if __name__ == "__main__":
    main()
