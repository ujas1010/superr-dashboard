"""Phase 1 - Clean and join.

Output: outputs/intermediate/balls_clean.parquet, matches_clean.parquet
"""
import json

import numpy as np
import pandas as pd

import config as C


def main():
    b = pd.read_csv(C.DATA_DIR / "ball_by_ball.csv", low_memory=False)
    m = pd.read_csv(C.DATA_DIR / "matches.csv")
    comp = pd.read_csv(C.DATA_DIR / "competitions.csv")
    log = {"raw_balls": len(b), "raw_matches": len(m)}

    # ---------------- matches: scope + results
    m = m.merge(comp, on="comp_id", how="left")
    m["is_ipl"] = m["comp_name"].str.startswith("IPL").astype(int)
    in_scope = ~m["comp_name"].isin(C.EXCLUDED_COMPETITIONS)
    has_result = ~m["result"].isin(C.NO_RESULT_LABELS) & m["win_team_id"].notna()
    has_balls = m["match_id"].isin(b["match_id"])
    log["excluded_out_of_scope_matches"] = int((~in_scope).sum())
    log["excluded_no_result_matches"] = int((in_scope & ~has_result).sum())
    log["excluded_no_ball_data_matches"] = int((in_scope & has_result & ~has_balls).sum())
    m = m[in_scope & has_result & has_balls].copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    m["competition"] = np.where(m["is_ipl"] == 1, "IPL", "T20I")

    # ---------------- balls
    log["super_over_balls_dropped"] = int((b["innings"] > 2).sum())
    b = b[(b["innings"] <= 2) & b["match_id"].isin(m["match_id"])].copy()
    b = b.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    dup = b.duplicated(["match_id", "innings", "innings_ball_num"]).sum()
    assert dup == 0, f"{dup} duplicated deliveries"

    et = b["extras_type"]
    b["is_wide"] = (et == "wide").astype(int)
    b["is_noball"] = et.isin(C.NO_BALL_EXTRAS).astype(int)
    b["is_legal"] = (~et.isin(C.ILLEGAL_EXTRAS)).astype(int)
    b["total_runs"] = b["runs"] + b["extras1_runs"] + b["extras_2_runs"]
    # runs charged to the bowler: bat runs + wides + no-ball penalty (+ runs off a no-ball not byes)
    b["bowler_runs"] = b["runs"] + np.where(et.isin(["wide"] + C.NO_BALL_EXTRAS), b["extras1_runs"], 0)
    b["faced"] = (b["is_wide"] == 0).astype(int)          # wides are not balls faced
    b["is_boundary"] = (b["is_four"] | b["is_six"]).astype(int)

    b["is_wicket"] = b["is_wicket"].astype(bool)
    dtid = b["dismissal_type_id"]
    b["team_wicket"] = b["is_wicket"].astype(int)
    b["striker_out"] = (b["is_wicket"] & (b["dismissed_player_id"] == b["striker_id"])).astype(int)
    b["nonstriker_out"] = (b["is_wicket"] & (b["dismissed_player_id"] == b["non_striker_id"])).astype(int)
    b["bowler_wicket"] = (b["is_wicket"] & dtid.isin(C.BOWLER_CREDITED_DISMISSALS)
                          & (b["dismissed_player_id"] == b["striker_id"])).astype(int)
    # retirements: dismissed_player_id set, is_wicket False, no dismissal type (12 rows)
    b["retired"] = (b["dismissed_player_id"].notna() & ~b["is_wicket"]).astype(int)
    log["retirement_rows"] = int(b["retired"].sum())

    b = b.merge(m[["match_id", "is_ipl", "competition", "season", "match_date", "venue_id",
                   "comp_name", "stage"]], on="match_id", how="left")

    # sanity: legal balls per complete over
    lp = b.groupby(["match_id", "innings", "overid"])["is_legal"].sum()
    log["overs_with_6_legal_balls_pct"] = round(float((lp == 6).mean() * 100), 2)
    log["clean_balls"] = len(b)
    log["clean_matches"] = int(m["match_id"].nunique())
    log["matches_by_competition"] = m["competition"].value_counts().to_dict()

    keep_b = [c for c in b.columns if c not in ("dismissal_type", "delivery_ist_time")]
    b[keep_b].to_parquet(C.INTER / "balls_clean.parquet", index=False)
    m.to_parquet(C.INTER / "matches_clean.parquet", index=False)
    (C.RESULTS / "01_clean_log.json").write_text(json.dumps(log, indent=2, default=str))
    print(json.dumps(log, indent=2, default=str))


if __name__ == "__main__":
    main()
