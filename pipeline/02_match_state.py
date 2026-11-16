"""Phase 2 - Rebuild the match state before and after every delivery.

Adds: score, wickets, legal balls, balls left, target, runs required, RRR, CRR,
phase, pre-match team Elo, venue scoring rate and the match-outcome label.
Output: outputs/intermediate/balls_state.parquet
"""
import json

import numpy as np
import pandas as pd

import config as C


def team_elo(m: pd.DataFrame) -> pd.DataFrame:
    """Chronological Elo over all in-scope results; returns pre-match ratings."""
    rating, rows = {}, []
    for r in m.sort_values(["match_date", "match_id"]).itertuples():
        h, a = r.home_team_id, r.away_team_id
        rh, ra = rating.get(h, C.ELO_START), rating.get(a, C.ELO_START)
        rows.append((r.match_id, h, rh))
        rows.append((r.match_id, a, ra))
        eh = 1 / (1 + 10 ** ((ra - rh) / 400))
        sh = 1.0 if r.win_team_id == h else 0.0
        rating[h] = rh + C.ELO_K * (sh - eh)
        rating[a] = ra + C.ELO_K * ((1 - sh) - (1 - eh))
    return pd.DataFrame(rows, columns=["match_id", "team_id", "elo"])


def main():
    b = pd.read_parquet(C.INTER / "balls_clean.parquet")
    m = pd.read_parquet(C.INTER / "matches_clean.parquet")
    g = b.groupby(["match_id", "innings"], sort=False)

    b["runs_after"] = g["total_runs"].cumsum()
    b["wkts_after"] = g["team_wicket"].cumsum()
    b["legal_after"] = g["is_legal"].cumsum()
    b["runs_before"] = b["runs_after"] - b["total_runs"]
    b["wkts_before"] = b["wkts_after"] - b["team_wicket"]
    b["legal_before"] = b["legal_after"] - b["is_legal"]

    # ---------------- overs available (revised overs are stored in balls)
    mi = m.set_index("match_id")
    inn1_avail = mi["first_inn_revised_overs"].fillna(120)
    inn2_avail = mi["second_inn_revised_overs"].fillna(mi["first_inn_revised_overs"]).fillna(120)
    b["balls_avail"] = np.where(b["innings"] == 1, b["match_id"].map(inn1_avail), b["match_id"].map(inn2_avail))
    legal_tot = g["is_legal"].transform("sum")
    b["balls_avail"] = np.maximum(b["balls_avail"], legal_tot)
    b["balls_left"] = (b["balls_avail"] - b["legal_before"]).clip(lower=1)
    b["balls_left_after"] = (b["balls_avail"] - b["legal_after"]).clip(lower=0)
    b["wkts_in_hand"] = 10 - b["wkts_before"]

    # ---------------- target / chase
    inn1_total = b[b["innings"] == 1].groupby("match_id")["total_runs"].sum()
    target = mi["revised_target"].fillna(inn1_total.reindex(mi.index) + 1)
    b["target"] = np.where(b["innings"] == 2, b["match_id"].map(target), np.nan)
    b["runs_required"] = b["target"] - b["runs_before"]
    b["rrr"] = b["runs_required"] * 6 / b["balls_left"]
    b["crr"] = np.where(b["legal_before"] > 0, b["runs_before"] * 6 / b["legal_before"].clip(lower=1), np.nan)
    b["over_no"] = (b["legal_before"] // 6 + 1).clip(upper=20)
    b["phase"] = pd.cut(b["over_no"], [0, 6, 15, 20], labels=["Powerplay", "Middle", "Death"]).astype(str)

    # ---------------- outcome label
    b["bat_team_won"] = (b["batting_team_id"] == b["match_id"].map(mi["win_team_id"])).astype(int)

    # ---------------- context: Elo & venue
    elo = team_elo(m)
    b = b.merge(elo.rename(columns={"team_id": "batting_team_id", "elo": "bat_elo"}),
                on=["match_id", "batting_team_id"], how="left")
    b = b.merge(elo.rename(columns={"team_id": "bowling_team_id", "elo": "bowl_elo"}),
                on=["match_id", "bowling_team_id"], how="left")
    b[["bat_elo", "bowl_elo"]] = b[["bat_elo", "bowl_elo"]].fillna(C.ELO_START)
    b["elo_diff"] = b["bat_elo"] - b["bowl_elo"]

    league_rpb = b["total_runs"].sum() / b["is_legal"].sum()
    v = b.groupby("venue_id").agg(r=("total_runs", "sum"), n=("is_legal", "sum"))
    prior = 3000
    v["venue_rpb"] = (v["r"] + prior * league_rpb) / (v["n"] + prior)
    b["venue_rpb"] = b["venue_id"].map(v["venue_rpb"]).fillna(league_rpb)

    # ---------------- reconciliation checks
    chk = {}
    last = b.groupby(["match_id", "innings"]).tail(1)
    chk["innings_total_reconciles"] = bool(
        (last.set_index(["match_id", "innings"])["runs_after"]
         == b.groupby(["match_id", "innings"])["total_runs"].sum()).all())
    l2 = last[last["innings"] == 2]
    chase_won = l2["bat_team_won"] == 1
    chk["chase_wins"] = int(chase_won.sum())
    chk["chase_wins_below_target"] = int((chase_won & (l2["runs_after"] < l2["target"])).sum())
    chk["chase_losses_reaching_target"] = int((~chase_won & (l2["runs_after"] >= l2["target"])).sum())
    chk["max_legal_balls_in_innings"] = int(b["legal_after"].max())
    (C.RESULTS / "02_state_checks.json").write_text(json.dumps(chk, indent=2))
    print(json.dumps(chk, indent=2))

    b.to_parquet(C.INTER / "balls_state.parquet", index=False)


if __name__ == "__main__":
    main()
