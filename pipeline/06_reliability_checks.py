"""Phase 6 - Reliability and sensitivity.

1. Component reliability: split-half (odd/even match_id) correlation of per-ball value.
2. Split-half rating correlation for eligible players.
3. Bootstrap over matches: rank intervals and probability of a top-10 finish.
4. Sensitivity: thresholds, alternative pressure index, weights, eligibility.
Output: outputs/results/06_*.csv / .json
"""
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import config as C
import ratings_lib as R


def component_reliability(b):
    rows = []
    b = b.assign(h=b["match_id"] % 2)
    for role, pid, filt in (("bat", "striker_id", "faced"), ("bowl", "bowler_id", None)):
        d0 = b[b[filt] == 1] if filt else b
        for comp in ("rv", "wv"):
            col = f"{role}_{comp}"
            for band in ("High", "Ordinary", "All"):
                d = d0 if band == "All" else d0[d0["pressure_band"] == band]
                q = d.groupby([pid, "h"])[col].agg(["sum", "size"]).unstack()
                ok = (q[("size", 0)] >= 80) & (q[("size", 1)] >= 80)
                a = q[("sum", 0)] / q[("size", 0)]
                c = q[("sum", 1)] / q[("size", 1)]
                r = np.corrcoef(a[ok], c[ok])[0, 1] if ok.sum() > 5 else np.nan
                rows.append(dict(role=role, component={"rv": "runs", "wv": "wickets"}[comp], band=band,
                                 players=int(ok.sum()), split_half_r=round(float(r), 3)))
    return pd.DataFrame(rows)


def split_half_ratings(pm, role, s2, base):
    e = base.loc[base["eligible"], "pid"]
    half_mins = (dict(balls=C.MIN_BAT_PRESSURE_BALLS // 2, matches=C.MIN_BAT_PRESSURE_INNINGS // 2,
                      base=C.MIN_BAT_BASELINE_BALLS // 2) if role == "bat" else
                 dict(balls=C.MIN_BOWL_PRESSURE_BALLS // 2, matches=C.MIN_BOWL_PRESSURE_MATCHES // 2,
                      base=C.MIN_BOWL_BASELINE_BALLS // 2))
    out = {}
    for h in (0, 1):
        r = R.rate(pm[pm["match_id"] % 2 == h], role, s2, mins=half_mins).set_index("pid")
        out[h] = r
    j = out[0][["rating", "P_level", "consistency", "delta"]].join(
        out[1][["rating", "P_level", "consistency", "delta"]], lsuffix="_a", rsuffix="_b", how="inner")
    j = j.loc[j.index.isin(e)]
    return {k: round(float(spearmanr(j[f"{k}_a"], j[f"{k}_b"]).statistic), 3)
            for k in ("rating", "P_level", "delta", "consistency")} | {"players": int(len(j))}


def bootstrap(pm, role, s2, base, reps):
    rng = np.random.default_rng(C.RANDOM_SEED)
    mids = pm["match_id"].unique()
    fixed = R.rate(pm, role, s2).attrs["params"]   # score every resample with the full-sample model
    ranks = []
    for _ in range(reps):
        w = pd.Series(rng.choice(mids, len(mids), replace=True)).value_counts()
        r = R.rate(pm, role, s2, match_w=w, fixed=fixed).set_index("pid")["rank"]
        ranks.append(r)
    rk = pd.concat(ranks, axis=1)
    e = base[base["eligible"]].set_index("pid")
    rk = rk.reindex(e.index)
    res = pd.DataFrame({
        "player": e["player"], "rank": e["rank"],
        "boot_median_rank": rk.median(axis=1, skipna=True),
        "boot_p10_rank": rk.quantile(0.10, axis=1),
        "boot_p90_rank": rk.quantile(0.90, axis=1),
        "p_top10": (rk <= C.TOP_N).sum(axis=1) / reps,
        "p_eligible": rk.notna().sum(axis=1) / reps,
    })
    return res.sort_values("rank").reset_index()


def sensitivity(b, role, base):
    top_base = set(base.loc[base["eligible"]].head(C.TOP_N)["pid"])
    base_r = base.set_index("pid")["rating"]
    scen = {
        "High = top 15%": dict(col="pressure_index", hi=0.85),
        "High = top 25%": dict(col="pressure_index", hi=0.75),
        "High = top 30%": dict(col="pressure_index", hi=0.70),
        "Alternative rule-based index": dict(col="alt_pressure_index", hi=C.HIGH_PRESSURE_QUANTILE),
        "Equal weights (1/3 each)": dict(weights={"pressure_level": 1 / 3, "pressure_delta": 1 / 3, "consistency": 1 / 3}),
        "Level 0.6 / delta 0.2 / consistency 0.2": dict(weights={"pressure_level": .6, "pressure_delta": .2, "consistency": .2}),
        "Pressure level only": dict(weights={"pressure_level": 1, "pressure_delta": 0, "consistency": 0}),
        "No delta (level 0.67 / consistency 0.33)": dict(weights={"pressure_level": 2 / 3, "pressure_delta": 0, "consistency": 1 / 3}),
        "Stricter eligibility (+50%)": dict(mult=1.5),
        "Looser eligibility (-33%)": dict(mult=0.67),
    }
    s2 = R.ball_variance(b, role)
    rows, tops = [], {}
    for name, s in scen.items():
        col = s.get("col", "pressure_index")
        band = R.assign_band(b, col, hi_q=s.get("hi", C.HIGH_PRESSURE_QUANTILE))
        pm = R.player_match_table(b, role, band)
        mins = None
        if "mult" in s:
            k = s["mult"]
            mins = (dict(balls=int(C.MIN_BAT_PRESSURE_BALLS * k), matches=int(C.MIN_BAT_PRESSURE_INNINGS * k),
                         base=int(C.MIN_BAT_BASELINE_BALLS * k)) if role == "bat" else
                    dict(balls=int(C.MIN_BOWL_PRESSURE_BALLS * k), matches=int(C.MIN_BOWL_PRESSURE_MATCHES * k),
                         base=int(C.MIN_BOWL_BASELINE_BALLS * k)))
        r = R.rate(pm, role, s2, weights=s.get("weights"), mins=mins)
        top = r.loc[r["eligible"]].head(C.TOP_N)
        tops[name] = list(top["pid"])
        common = r.loc[r["eligible"], ["pid", "rating"]].set_index("pid")["rating"]
        idx = common.index.intersection(base.loc[base["eligible"], "pid"])
        rho = spearmanr(common.loc[idx], base_r.loc[idx]).statistic
        rows.append(dict(scenario=name, top10_overlap=len(top_base & set(top["pid"])),
                         spearman_vs_base=round(float(rho), 3), eligible=int(r["eligible"].sum())))
    return pd.DataFrame(rows), tops


def main():
    b = pd.read_parquet(C.INTER / "balls_value.parquet")
    comp = component_reliability(b)
    comp.to_csv(C.RESULTS / "06_component_reliability.csv", index=False)
    print(comp.to_string(index=False))

    summary = {}
    for role, fname in (("bat", "batting"), ("bowl", "bowling")):
        base = pd.read_csv(C.RESULTS / f"{fname}_ratings_all.csv")
        base = base.sort_values(["eligible", "rating"], ascending=[False, False])
        pm = pd.read_parquet(C.INTER / f"player_match_{role}.parquet")
        s2 = R.ball_variance(b, role)

        sh = split_half_ratings(pm, role, s2, base)
        bs = bootstrap(pm, role, s2, base, C.BOOTSTRAP_REPS)
        bs.to_csv(C.RESULTS / f"06_bootstrap_{fname}.csv", index=False, float_format="%.3f")
        sens, tops = sensitivity(b, role, base)
        sens.to_csv(C.RESULTS / f"06_sensitivity_{fname}.csv", index=False)
        names = base.set_index("pid")["player"]
        pd.DataFrame({k: [names.get(p, p) for p in v] + [""] * (C.TOP_N - len(v)) for k, v in tops.items()},
                     index=range(1, C.TOP_N + 1)).to_csv(C.RESULTS / f"06_sensitivity_top10_{fname}.csv")
        summary[role] = {"split_half_spearman": sh,
                         "top10_mean_p_top10": round(float(bs.head(C.TOP_N)["p_top10"].mean()), 3)}
        print(f"\n== {role} split-half", sh)
        print(bs.head(15).to_string(index=False))
        print(sens.to_string(index=False))
    (C.RESULTS / "06_reliability_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
