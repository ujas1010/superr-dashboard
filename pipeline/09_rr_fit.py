"""Phase 9 - Rajasthan Royals fit for the IPL 2027 auction.

1. RR's pressure profile in the two most recent IPL seasons (2025-26) vs the other 9 teams,
   by role and phase (where do RR lose value when it matters?).
2. Each top-10 player's pressure value by phase (shrunk), role details, and IPL 2026 status.
3. Indicative impact: (player's shrunk pressure value in RR's weakest phase - RR's current value there)
   x the pressure balls the player typically handles per IPL season.
Output: outputs/results/09_rr_team_profile.csv, 09_rr_player_fit_{batting,bowling}.csv, figures
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C

RR = "Rajasthan Royals"
RECENT = ["2025", "2026"]
PHASES = ["Powerplay", "Middle", "Death"]
BLUE, ORANGE, GREY, INK, INK2, GRID = "#2a78d6", "#eb6834", "#b9b8b2", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.grid": True,
                     "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2, "figure.dpi": 170,
                     "savefig.bbox": "tight", "axes.titleweight": "bold", "legend.frameon": False})


def team_profile(b, tmap):
    ipl = b[(b["competition"] == "IPL") & b["season"].astype(str).isin(RECENT) & (b["pressure_band"] == "High")].copy()
    ipl["bat_team"] = ipl["batting_team_id"].map(tmap)
    ipl["bowl_team"] = ipl["bowling_team_id"].map(tmap)
    f = ipl[ipl["faced"] == 1]
    rows = []
    for side, d, tm, col in (("Batting", f, "bat_team", "bat_value"), ("Bowling", ipl, "bowl_team", "bowl_value")):
        for ph in ["All"] + PHASES:
            x = d if ph == "All" else d[d["phase"] == ph]
            g = x.groupby(tm)[col].agg(["mean", "size"])
            g["val100"] = 100 * g["mean"]
            g["rank"] = g["val100"].rank(ascending=False).astype(int)
            rows.append(dict(side=side, phase=ph, rr_val100=round(g.loc[RR, "val100"], 1),
                             league_avg_val100=round(g["val100"].mean(), 1),
                             rr_rank_of_10=int(g.loc[RR, "rank"]), rr_pressure_balls=int(g.loc[RR, "size"]),
                             best_team=g["val100"].idxmax(), best_val100=round(g["val100"].max(), 1)))
    for kind in ("Pace", "Spin"):
        x = ipl[ipl["pace_or_spin"] == kind].groupby("bowl_team")["bowl_value"].agg(["mean", "size"])
        x["val100"] = 100 * x["mean"]
        rows.append(dict(side="Bowling", phase=f"All ({kind})", rr_val100=round(x.loc[RR, "val100"], 1),
                         league_avg_val100=round(x["val100"].mean(), 1),
                         rr_rank_of_10=int(x["val100"].rank(ascending=False).loc[RR]),
                         rr_pressure_balls=int(x.loc[RR, "size"]), best_team=x["val100"].idxmax(),
                         best_val100=round(x["val100"].max(), 1)))
    prof = pd.DataFrame(rows)

    # RR's own pressure contributors in IPL 2026 death overs (who currently does the job)
    rr26 = ipl[ipl["season"].astype(str) == "2026"]
    death_bowl = (rr26[(rr26["bowl_team"] == RR) & (rr26["phase"] == "Death")]
                  .groupby("bowler_name")["bowl_value"].agg(balls="size", val100=lambda s: 100 * s.mean())
                  .sort_values("balls", ascending=False).round(1))
    death_bat = (rr26[(rr26["bat_team"] == RR) & (rr26["phase"] == "Death") & (rr26["faced"] == 1)]
                 .groupby("striker_name")["bat_value"].agg(balls="size", val100=lambda s: 100 * s.mean())
                 .sort_values("balls", ascending=False).round(1))
    return prof, death_bowl, death_bat


def player_fit(b, role, top, prof, mp26):
    params = json.loads((C.RESULTS / f"05_model_params_{role}.json").read_text())
    pid, val, rv, wv = (("striker_id", "bat_value", "bat_rv", "bat_wv") if role == "bat"
                        else ("bowler_id", "bowl_value", "bowl_rv", "bowl_wv"))
    d = b[b["pressure_band"] == "High"]
    if role == "bat":
        d = d[d["faced"] == 1]
    d = d[d[pid].isin(top["pid"])]
    side = "Batting" if role == "bat" else "Bowling"
    rank = prof[(prof["side"] == side) & prof["phase"].isin(PHASES)].set_index("phase")["rr_rank_of_10"]
    raw_need = {ph: (rank[ph] - 1) / 9 for ph in PHASES}          # rank 1 -> 0 need, rank 10 -> 1
    need = {ph: v / sum(raw_need.values()) for ph, v in raw_need.items()}
    rows = []
    for _, t in top.iterrows():
        x = d[d[pid] == t["pid"]]
        r = dict(rank=int(t["rank"]), player=t["player"], pid=t["pid"])
        for ph in PHASES:
            y = x[x["phase"] == ph]
            n = len(y)
            shr = (y[rv].sum() / (n + params["k_P_rv"]) + y[wv].sum() / (n + params["k_P_wv"])) * 100
            r[f"{ph}_balls"], r[f"{ph}_val100"] = n, round(shr, 1)
        r["main_phase"] = max(PHASES, key=lambda p: r[f"{p}_balls"])
        all_role = b[b[pid] == t["pid"]]
        if role == "bat":
            r["usual_position"] = int(all_role["batting_order"].median())
            r["hand"] = all_role["batting_type"].mode().iat[0]
        else:
            r["bowling_type"] = all_role["bowling_type"].mode().iat[0]
            r["pace_or_spin"] = all_role["pace_or_spin"].mode().iat[0]
        ipl = x[x["competition"] == "IPL"]
        r["ipl_pressure_balls_per_season"] = round(len(ipl) / max(ipl["season"].nunique(), 1)) if len(ipl) else 0
        r["ipl_2026_team"] = mp26.get(t["pid"], "Not in IPL 2026 squads")
        # RR fit index: player's shrunk pressure value in each phase, weighted by RR's need in that phase
        r["rr_fit_index"] = round(sum(need[ph] * r[f"{ph}_val100"] for ph in PHASES), 2)
        r["rr_need_phase"] = max(PHASES, key=lambda ph: need[ph])
        rows.append(r)
    out = pd.DataFrame(rows)
    out.attrs["need"] = need
    return out


def fig_team(prof):
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.0))
    for a, side in zip(ax, ("Batting", "Bowling")):
        p = prof[(prof["side"] == side) & prof["phase"].isin(PHASES)].set_index("phase").loc[PHASES]
        x = np.arange(3)
        a.bar(x - 0.18, p["rr_val100"], 0.34, color=BLUE, label="Rajasthan Royals")
        a.bar(x + 0.18, p["league_avg_val100"], 0.34, color=GREY, label="IPL average")
        for i, (v, rk) in enumerate(zip(p["rr_val100"], p["rr_rank_of_10"])):
            a.text(i - 0.18, v + (1 if v >= 0 else -1), f"#{rk}", ha="center",
                   va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
        a.axhline(0, color=INK2, lw=0.8)
        a.set_xticks(x, PHASES)
        a.set_title(f"{side} under pressure (IPL 2025-26)")
        a.set_ylabel("Value per 100 high-pressure balls")
        a.grid(axis="x", visible=False)
        a.legend(fontsize=7.5, loc="lower left" if side == "Bowling" else "upper right")
    fig.suptitle("Rajasthan Royals: where value is lost when it matters (#n = rank among 10 IPL teams)",
                 color=INK, fontsize=10, y=1.04)
    fig.savefig(C.FIG / "fig_rr_team_profile.png")
    plt.close(fig)


def fig_fit(fit, fname, gap_phase_vals):
    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    f = fit.sort_values("rr_fit_index")
    colors = [ORANGE if "Rajasthan" in str(t) else BLUE for t in f["ipl_2026_team"]]
    ax.barh(f["player"], f["rr_fit_index"], color=colors, height=0.6)
    ax.axvline(0, color=INK2, lw=0.8)
    need = fit.attrs["need"]
    ax.set_xlabel("RR fit index (need-weighted pressure value; weights " +
                  ", ".join(f"{k} {v:.2f}" for k, v in need.items()) + ")")
    ax.set_title(("Batters" if fname == "batting" else "Bowlers") + ": fit to Rajasthan Royals' pressure gaps")
    ax.grid(axis="y", visible=False)
    ax.text(0.99, 0.02, "orange = already in RR's 2026 squad", transform=ax.transAxes, ha="right", fontsize=7.5,
            color=INK2)
    fig.savefig(C.FIG / f"fig_rr_fit_{fname}.png")
    plt.close(fig)


def main():
    b = pd.read_parquet(C.INTER / "balls_value.parquet")
    teams = pd.read_csv(C.DATA_DIR / "teams.csv").drop_duplicates("team_id").set_index("team_id")["team_name"]
    mp = pd.read_csv(C.DATA_DIR / "competition_team_player_mapping.csv")
    mp26 = mp[mp["comp_name"] == "IPL 2026"].drop_duplicates("player_id").set_index("player_id")["team_name"].to_dict()
    prof, death_bowl, death_bat = team_profile(b, teams)
    prof.to_csv(C.RESULTS / "09_rr_team_profile.csv", index=False)
    death_bowl.to_csv(C.RESULTS / "09_rr_2026_death_bowlers_pressure.csv")
    death_bat.to_csv(C.RESULTS / "09_rr_2026_death_batters_pressure.csv")
    print(prof.to_string(index=False))
    print(death_bowl.head(8), death_bat.head(8), sep="\n")
    fig_team(prof)
    for role, fname in (("bat", "batters"), ("bowl", "bowlers")):
        top = pd.read_csv(C.RESULTS / f"top10_{fname}.csv")
        fit = player_fit(b, role, top, prof, mp26)
        fit.to_csv(C.RESULTS / f"09_rr_player_fit_{fname}.csv", index=False)
        (C.RESULTS / f"09_rr_need_weights_{fname}.json").write_text(json.dumps(fit.attrs["need"], indent=2))
        print(fit.drop(columns="pid").to_string(index=False))
        fig_fit(fit, "batting" if role == "bat" else "bowling", None)
    rr26 = mp[(mp["comp_name"] == "IPL 2026") & (mp["team_name"] == RR)]["player_name"].tolist()
    (C.RESULTS / "09_rr_2026_squad.json").write_text(json.dumps(rr26, indent=2))


if __name__ == "__main__":
    main()
