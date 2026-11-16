"""Phase 10 - Collect every number used in the submission deck into outputs/results/deck_data.json.

The deck builder (deck/build_deck.js) only formats; all values come from here.
"""
import json

import pandas as pd

import config as C

R = C.RESULTS

# Facts that are not in the supplied data, kept separate and labelled in the deck.
EXTERNAL_CAVEATS = {
    "Shaheen Afridi": "Pakistan players have not played in the IPL since 2008",
}


def J(n):
    return json.loads((R / n).read_text())


def bat_role(pos, hand):
    pos = int(pos)
    lab = "Opener" if pos <= 2 else "Top order (#3)" if pos == 3 else "Middle order" if pos <= 5 else "Finisher"
    return f"{lab}, {hand}"


def tiers(fit, strong_phases):
    """Retain (in RR 2026) / Priority target / Strong option / Lower priority, by RR fit index."""
    out = {}
    cand = fit[~fit["ipl_2026_team"].str.contains("Rajasthan")].sort_values("rr_fit_index", ascending=False)
    for i, (_, r) in enumerate(cand.iterrows()):
        if r["player"] in EXTERNAL_CAVEATS:
            out[r["player"]] = "Unlikely available"
        elif i < 3:
            out[r["player"]] = "Priority target"
        elif r["main_phase"] in strong_phases:
            out[r["player"]] = "Lower priority"
        elif i < 6:
            out[r["player"]] = "Strong option"
        else:
            out[r["player"]] = "Depth option"
    for p in fit.loc[fit["ipl_2026_team"].str.contains("Rajasthan"), "player"]:
        out[p] = "Retain"
    return out


def why(r, role, prof_rank):
    ph = {"Powerplay": "PP", "Middle": "Mid", "Death": "Death"}
    vals = ", ".join(f"{ph[p]} {r[f'{p}_val100']:+.1f}" for p in ("Powerplay", "Middle", "Death"))
    best = max(("Powerplay", "Middle", "Death"), key=lambda p: r[f"{p}_val100"])
    side = "batting" if role == "bat" else "bowling"
    return f"Best: {best} (RR {side} there #{prof_rank[best]}/10). Per 100 pressure balls: {vals}."


def main():
    clean, pm, xm = J("01_clean_log.json"), J("03_pressure_metrics.json"), J("04_expected_model.json")
    rel = J("06_reliability_summary.json")
    band = pd.read_csv(R / "03_pressure_band_summary.csv").set_index("pressure_band")
    dec = pd.read_csv(R / "03_pressure_validation_by_decile.csv").set_index("pi_decile")
    prof = pd.read_csv(R / "09_rr_team_profile.csv")
    data = {"scope": clean, "wp": {k: pm[k] for k in ("wp_innings1", "wp_innings2")},
            "pi_high": pm["pi_high_threshold"], "pi_ord": pm["pi_ordinary_threshold"],
            "band": band.round(2).reset_index().to_dict(orient="records"),
            "top_decile": dec.loc[10].round(1).to_dict(), "low_half_death": round(dec.loc[1:5, "pct_death"].mean(), 1),
            "wicket_cost": xm["wicket_cost_by_phase"], "weights": C.WEIGHTS,
            "elig": dict(bat=[C.MIN_BAT_PRESSURE_BALLS, C.MIN_BAT_PRESSURE_INNINGS, C.MIN_BAT_BASELINE_BALLS],
                         bowl=[C.MIN_BOWL_PRESSURE_BALLS, C.MIN_BOWL_PRESSURE_MATCHES, C.MIN_BOWL_BASELINE_BALLS]),
            "reliability": rel, "rr_profile": prof.to_dict(orient="records")}

    for role, fname, long in (("bat", "batters", "batting"), ("bowl", "bowlers", "bowling")):
        top = pd.read_csv(R / f"top10_{fname}.csv")
        bs = pd.read_csv(R / f"06_bootstrap_{long}.csv")[["pid", "p_top10"]]
        top = top.merge(bs, on="pid")
        fit = pd.read_csv(R / f"09_rr_player_fit_{fname}.csv")
        side = "Batting" if role == "bat" else "Bowling"
        pr = prof[(prof["side"] == side)].set_index("phase")["rr_rank_of_10"]
        strong = [p for p in ("Powerplay", "Middle", "Death") if pr[p] <= 2]
        tier = tiers(fit, strong)
        rows = []
        for _, t in top.iterrows():
            f = fit[fit["pid"] == t["pid"]].iloc[0]
            row = dict(rank=int(t["rank"]), player=t["player"], rating=round(t["rating"], 3),
                       pressure_balls=int(t["n_High"]), value100=round(t["pressure_value_per100"], 1),
                       consistency=round(100 * t["consistency"]), p_top10=round(100 * t["p_top10"]),
                       ipl_2026=f["ipl_2026_team"], fit_index=round(f["rr_fit_index"], 2),
                       main_phase=f["main_phase"], best_phase=max(("Powerplay", "Middle", "Death"), key=lambda q: f[f"{q}_val100"]), tier=tier[t["player"]], why=why(f, role, pr),
                       caveat=EXTERNAL_CAVEATS.get(t["player"], ""))
            if role == "bat":
                row.update(sr_p=round(t["pr_SR"]), sr_o=round(t["ord_SR"]),
                           avg_p=None if pd.isna(t["pr_avg"]) else round(t["pr_avg"], 1),
                           role=bat_role(f["usual_position"], f["hand"]))
            else:
                row.update(econ_p=round(t["pr_econ"], 2), econ_o=round(t["ord_econ"], 2), wkts_p=int(t["pr_wkts"]),
                           role=f"{f['bowling_type']}")
            if f["ipl_2026_team"] == "Not in IPL 2026 squads" and not row["caveat"]:
                row["caveat"] = "not in an IPL 2026 squad, must enter the auction pool"
            rows.append(row)
        data[fname] = rows
        data[f"need_{fname}"] = J(f"09_rr_need_weights_{fname}.json")
    data["rr_death_bowlers_2026"] = (pd.read_csv(R / "09_rr_2026_death_bowlers_pressure.csv")
                                     .head(6).to_dict(orient="records"))
    data["rr_squad_2026"] = J("09_rr_2026_squad.json")
    for fname in ("batting", "bowling"):
        data[f"sens_{fname}"] = pd.read_csv(R / f"06_sensitivity_{fname}.csv").to_dict(orient="records")
    data["component_rel"] = pd.read_csv(R / "06_component_reliability.csv").to_dict(orient="records")
    data["fig_dir"] = str(C.FIG).replace("\\", "/")
    C.DECK_DATA.write_text(json.dumps(data, indent=2, default=str))
    for k in ("batters", "bowlers"):
        print(pd.DataFrame(data[k])[["rank", "player", "ipl_2026", "fit_index", "tier", "caveat"]].to_string(index=False))


if __name__ == "__main__":
    main()
