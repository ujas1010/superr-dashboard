"""Phase 12 - Export everything the online dashboard shows into one JSON file.

Output: outputs/dashboard/superr_dashboard_data.json  ({tables: {...}, meta: [...]})
Every table is read by the dashboard through a small loader that picks its key.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import config as C

R = C.RESULTS
OUT = C.OUT / "dashboard"
OUT.mkdir(exist_ok=True)


def clean(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(v) else round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def rows(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict(orient="records")]


def ratings(long, short):
    r = pd.read_csv(R / f"{long}_ratings_all.csv")
    r = r[r["eligible"]].copy()
    bs = pd.read_csv(R / f"06_bootstrap_{long}.csv")[["pid", "p_top10", "boot_p10_rank", "boot_p90_rank", "boot_median_rank"]]
    fit = pd.read_csv(R / f"09_rr_player_fit_{short}.csv")[["pid", "ipl_2026_team"]]
    r = r.merge(bs, on="pid", how="left").merge(fit, on="pid", how="left")
    r["in_top10"] = r["rank"] <= C.TOP_N
    common = ["pid", "rank", "player", "teams", "rating", "z_pressure_level", "z_pressure_delta", "z_consistency",
              "pressure_value_per100", "ordinary_value_per100", "consistency", "n_High", "match_count",
              "ipl_share_of_pressure_balls", "p_top10", "boot_p10_rank", "boot_p90_rank", "boot_median_rank",
              "ipl_2026_team", "in_top10"]
    extra = (["pr_SR", "ord_SR", "pr_avg", "pr_dot%", "pr_bnd%"] if long == "batting"
             else ["pr_balls", "pr_econ", "ord_econ", "pr_wkts", "pr_dot%"])
    out = r[common + extra].rename(columns={"pr_dot%": "pr_dot_pct", "pr_bnd%": "pr_bnd_pct"})
    out["rank"] = out["rank"].astype(int)
    out["pid"] = out["pid"].astype(str)
    # rounded to the precision the dashboard displays, so every shown number equals its cell
    out["rating"] = out["rating"].round(3)
    for c in ("z_pressure_level", "z_pressure_delta", "z_consistency"):
        out[c] = out[c].round(3)
    for c in ("pressure_value_per100", "ordinary_value_per100", "boot_p10_rank", "boot_p90_rank", "boot_median_rank"):
        out[c] = out[c].round(1)
    out["consistency_pct"] = (100 * out.pop("consistency")).round(0).astype(int)
    out["p_top10_pct"] = (100 * out.pop("p_top10")).round(0).astype(int)
    out["ipl_share_pct"] = (100 * out.pop("ipl_share_of_pressure_balls")).round(0).astype(int)
    if long == "batting":
        out["pr_SR"] = out["pr_SR"].round(0).astype(int)
        out["ord_SR"] = out["ord_SR"].round(0).astype(int)
        out["pr_avg"] = out["pr_avg"].round(1)
        out["pr_dot_pct"] = out["pr_dot_pct"].round(1)
        out["pr_bnd_pct"] = out["pr_bnd_pct"].round(1)
    else:
        out["pr_balls"] = out["pr_balls"].astype(int)
        out["pr_econ"] = out["pr_econ"].round(2)
        out["ord_econ"] = out["ord_econ"].round(2)
        out["pr_wkts"] = out["pr_wkts"].astype(int)
        out["pr_dot_pct"] = out["pr_dot_pct"].round(1)
    return rows(out.sort_values("rank"))


def heat():
    b = pd.read_parquet(C.INTER / "balls_value.parquet", columns=["innings", "is_legal", "balls_left", "rrr", "pressure_index"])
    d = b[(b["innings"] == 2) & (b["is_legal"] == 1)].copy()
    d["overs_left"] = pd.cut(d["balls_left"], [0, 12, 24, 36, 48, 60, 72, 90, 120],
                             labels=["1-2", "3-4", "5-6", "7-8", "9-10", "11-12", "13-15", "16-20"])
    d["rrr_band"] = pd.cut(d["rrr"], [-1, 6, 8, 10, 12, 14, 18, 99], labels=["<6", "6-8", "8-10", "10-12", "12-14", "14-18", ">18"])
    h = d.groupby(["rrr_band", "overs_left"], observed=True)["pressure_index"].agg(mean_pi="mean", balls="size").reset_index()
    h["mean_pi"] = h["mean_pi"].round(2)
    h["key"] = h["rrr_band"].astype(str) + "|" + h["overs_left"].astype(str)
    for c in ("rrr_band", "overs_left"):
        h[c] = h[c].astype(str)
    return rows(h[h["balls"] >= 30])


def main():
    clean_log = json.loads((R / "01_clean_log.json").read_text())
    pm = json.loads((R / "03_pressure_metrics.json").read_text())
    rel = json.loads((R / "06_reliability_summary.json").read_text())
    band = pd.read_csv(R / "03_pressure_band_summary.csv")
    bat, bowl = ratings("batting", "batters"), ratings("bowling", "bowlers")
    summary = [{
        "matches": clean_log["clean_matches"], "ipl_matches": clean_log["matches_by_competition"]["IPL"],
        "t20i_matches": clean_log["matches_by_competition"]["T20I"], "deliveries": clean_log["clean_balls"],
        "eligible_batters": len(bat), "eligible_bowlers": len(bowl),
        "pi_high_threshold": round(pm["pi_high_threshold"], 2), "wp_auc_chase": round(pm["wp_innings2"]["auc"], 2),
        "wp_auc_first": round(pm["wp_innings1"]["auc"], 2),
        "bat_mean_p_top10_pct": round(100 * rel["bat"]["top10_mean_p_top10"]), "bowl_mean_p_top10_pct": round(100 * rel["bowl"]["top10_mean_p_top10"]),
        "top_batter": bat[0]["player"], "top_bowler": bowl[0]["player"],
    }]
    dec = pd.read_csv(R / "03_pressure_validation_by_decile.csv")
    prof = pd.read_csv(R / "09_rr_team_profile.csv")
    prof["key"] = prof["side"] + "|" + prof["phase"]
    fits = []
    for short, role in (("batters", "Batter"), ("bowlers", "Bowler")):
        f = pd.read_csv(R / f"09_rr_player_fit_{short}.csv")
        d = json.loads(C.DECK_DATA.read_text())[short]
        tier = {x["player"]: (x["tier"], x["caveat"], x["role"], x["best_phase"]) for x in d}
        f["role"] = role
        f["tier"] = f["player"].map(lambda p: tier[p][0])
        f["note"] = f["player"].map(lambda p: tier[p][1])
        f["style"] = f["player"].map(lambda p: tier[p][2])
        f["best_phase"] = f["player"].map(lambda p: tier[p][3])
        f["key"] = role + "|" + f["rank"].astype(str)
        f["rr_fit_index"] = f["rr_fit_index"].round(1)
        fits.append(f[["key", "role", "rank", "player", "style", "ipl_2026_team", "Powerplay_val100", "Middle_val100",
                       "Death_val100", "best_phase", "rr_fit_index", "tier", "note"]])
    fit = pd.concat(fits)
    sens = []
    for long, role in (("batting", "Batters"), ("bowling", "Bowlers")):
        s = pd.read_csv(R / f"06_sensitivity_{long}.csv")
        s["role"] = role
        s["key"] = role + "|" + s["scenario"]
        sens.append(s)
    comp = pd.read_csv(R / "06_component_reliability.csv")
    comp = comp[comp["band"] != "All"].copy()
    comp["key"] = comp["role"] + "|" + comp["component"] + "|" + comp["band"]

    here = Path(__file__)
    meta = [
        {"label": "Made by", "value": "python pipeline/run_all.py (steps 01-12) on the supplied IPL + T20I data pack, 2022-2026"},
        {"label": "12_dashboard_data.py", "value": here.read_text(), "type": "code", "lang": "python"},
        {"label": "ratings_lib.py (rating logic)", "value": (here.parent / "ratings_lib.py").read_text(), "type": "code", "lang": "python"},
        {"label": "config.py (all parameters)", "value": (here.parent / "config.py").read_text(), "type": "code", "lang": "python"},
    ]
    data = {"tables": {"summary": summary, "batters": bat, "bowlers": bowl, "band": rows(band.round(2)),
                       "deciles": rows(dec), "heat": heat(), "rr_profile": rows(prof), "rr_fit": rows(fit),
                       "sensitivity": rows(pd.concat(sens)), "reliability": rows(comp)},
            "meta": meta}
    p = OUT / "superr_dashboard_data.json"
    p.write_text(json.dumps(data, separators=(",", ":")))
    print(p, p.stat().st_size // 1024, "KB", {k: len(v) for k, v in data["tables"].items()})


if __name__ == "__main__":
    main()
