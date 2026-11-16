"""Phase 5 - Player ratings and rankings.

Output: outputs/results/batting_ratings_all.csv, bowling_ratings_all.csv,
        top10_batters.csv, top10_bowlers.csv, outputs/intermediate/player_match_*.parquet
"""
import json

import numpy as np
import pandas as pd

import config as C
import ratings_lib as R


def names_and_teams(b, role):
    r = R.ROLE[role]
    teams = pd.read_csv(C.DATA_DIR / "teams.csv")[["team_id", "team_name"]].drop_duplicates("team_id")
    tmap = teams.set_index("team_id")["team_name"]
    d = b[[r["pid"], r["name"], r["team"], "match_date"]].rename(columns={r["pid"]: "pid", r["name"]: "player", r["team"]: "tid"})
    d["team"] = d["tid"].map(tmap)
    nm = d.groupby("pid")["player"].first()
    tm = d.sort_values("match_date").groupby("pid")["team"].agg(lambda s: ", ".join(dict.fromkeys(s.dropna())))
    return pd.DataFrame({"player": nm, "teams": tm})


def describe(p, role):
    o = pd.DataFrame(index=p.index)
    for bd, tag in (("High", "pr"), ("Ordinary", "ord")):
        if role == "bat":
            o[f"{tag}_balls"] = p[f"n_{bd}"]
            o[f"{tag}_runs"] = p[f"runs_{bd}"]
            o[f"{tag}_SR"] = 100 * p[f"runs_{bd}"] / p[f"n_{bd}"].replace(0, np.nan)
            o[f"{tag}_avg"] = p[f"runs_{bd}"] / p[f"outs_{bd}"].replace(0, np.nan)
            o[f"{tag}_dot%"] = 100 * p[f"dots_{bd}"] / p[f"n_{bd}"].replace(0, np.nan)
            o[f"{tag}_bnd%"] = 100 * p[f"bnd_{bd}"] / p[f"n_{bd}"].replace(0, np.nan)
            o[f"{tag}_outs"] = p[f"outs_{bd}"]
        else:
            o[f"{tag}_balls"] = p[f"balls_{bd}"]
            o[f"{tag}_econ"] = 6 * p[f"runs_{bd}"] / p[f"balls_{bd}"].replace(0, np.nan)
            o[f"{tag}_wkts"] = p[f"outs_{bd}"]
            o[f"{tag}_balls_per_wkt"] = p[f"balls_{bd}"] / p[f"outs_{bd}"].replace(0, np.nan)
            o[f"{tag}_dot%"] = 100 * p[f"dots_{bd}"] / p[f"balls_{bd}"].replace(0, np.nan)
            o[f"{tag}_bnd%"] = 100 * p[f"bnd_{bd}"] / p[f"n_{bd}"].replace(0, np.nan)
    return o


def run(role, b):
    band = b["pressure_band"].values
    pm = R.player_match_table(b, role, band)
    pm.to_parquet(C.INTER / f"player_match_{role}.parquet", index=False)
    s2 = R.ball_variance(b, role)
    p = R.rate(pm, role, s2)
    params = p.attrs["params"] | {f"sigma2_{k}": v for k, v in s2.items()}
    (C.RESULTS / f"05_model_params_{role}.json").write_text(json.dumps(params, indent=2))
    p = p.set_index("pid")
    p = p.join(names_and_teams(b, role)).join(describe(p, role))
    p["pressure_value_per100"] = 100 * p["P_level"]
    p["ordinary_value_per100"] = 100 * p["N_level"]
    p["delta_per100"] = 100 * p["delta"]
    p["ipl_share_of_pressure_balls"] = p["ipl_hi"] / p["n_High"].replace(0, np.nan)
    keep = (["rank", "player", "teams", "rating", "z_pressure_level", "z_pressure_delta", "z_consistency",
             "pressure_value_per100", "ordinary_value_per100", "delta_per100", "consistency",
             "match_count", "match_success", "p_matches", "n_High", "n_Ordinary", "ipl_share_of_pressure_balls",
             "eligible"] + list(describe(p, role).columns))
    out = p.reset_index()[["pid"] + keep].sort_values(["eligible", "rating"], ascending=[False, False])
    out.to_csv(C.RESULTS / f"{'batting' if role == 'bat' else 'bowling'}_ratings_all.csv", index=False, float_format="%.4f")
    top = out[out["eligible"]].head(C.TOP_N)
    top.to_csv(C.RESULTS / f"top10_{'batters' if role == 'bat' else 'bowlers'}.csv", index=False, float_format="%.3f")
    print(f"\n{role}: eligible {int(out['eligible'].sum())} of {len(out)}")
    cols = ["rank", "player", "teams", "rating", "pressure_value_per100", "delta_per100", "consistency", "n_High"]
    cols += ["pr_SR", "ord_SR", "pr_avg"] if role == "bat" else ["pr_econ", "ord_econ", "pr_wkts"]
    print(out[out["eligible"]].head(20)[cols].to_string(index=False))
    return out


def main():
    b = pd.read_parquet(C.INTER / "balls_value.parquet")
    run("bat", b)
    run("bowl", b)


if __name__ == "__main__":
    main()
