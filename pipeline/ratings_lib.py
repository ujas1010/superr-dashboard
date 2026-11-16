"""Shared rating logic (used by phase 5 and by the reliability checks in phase 6).

Work happens on a player x match table so bootstrap resampling of matches is cheap.
"""
import numpy as np
import pandas as pd

import config as C

ROLE = {
    "bat": dict(pid="striker_id", name="striker_name", team="batting_team_id", value="bat_value", filt="faced"),
    "bowl": dict(pid="bowler_id", name="bowler_name", team="bowling_team_id", value="bowl_value", filt=None),
}


def assign_band(b: pd.DataFrame, col: str, hi_q=C.HIGH_PRESSURE_QUANTILE, lo_q=C.LOW_PRESSURE_QUANTILE):
    hi, lo = b[col].quantile(hi_q), b[col].quantile(lo_q)
    return np.select([b[col] >= hi, b[col] <= lo], ["High", "Ordinary"], "Moderate")


def player_match_table(b: pd.DataFrame, role: str, band: np.ndarray) -> pd.DataFrame:
    r = ROLE[role]
    d = b.assign(band=band)
    if r["filt"]:
        d = d[d[r["filt"]] == 1]
    d = d.assign(pid=d[r["pid"]], v=d[r["value"]], rv=d[f"{role}_rv"], wv=d[f"{role}_wv"])
    if role == "bat":
        d = d.assign(runs_=d["runs"], balls_=1, out_=d["striker_out"], dot_=(d["runs"] == 0).astype(int),
                     bnd_=d["is_boundary"])
    else:
        d = d.assign(runs_=d["bowler_runs"], balls_=d["is_legal"], out_=d["bowler_wicket"],
                     dot_=((d["total_runs"] == 0) & (d["is_legal"] == 1)).astype(int), bnd_=d["is_boundary"])
    agg = {"n": ("v", "size"), "v": ("v", "sum"), "rv": ("rv", "sum"), "wv": ("wv", "sum"), "runs": ("runs_", "sum"), "balls": ("balls_", "sum"),
           "outs": ("out_", "sum"), "dots": ("dot_", "sum"), "bnd": ("bnd_", "sum")}
    t = d.groupby(["pid", "match_id", "band"]).agg(**agg).unstack("band", fill_value=0)
    t.columns = [f"{a}_{bd}" for a, bd in t.columns]
    for bd in ("High", "Moderate", "Ordinary"):
        for a in agg:
            if f"{a}_{bd}" not in t:
                t[f"{a}_{bd}"] = 0
    t = t.reset_index()
    t = t.merge(b[["match_id", "competition"]].drop_duplicates(), on="match_id", how="left")
    return t


def ball_variance(b: pd.DataFrame, role: str) -> dict:
    """Per-ball variance of each value component (the 'noise' term for shrinkage)."""
    r = ROLE[role]
    d = b[b[r["filt"]] == 1] if r["filt"] else b
    return {"rv": float(d[f"{role}_rv"].var()), "wv": float(d[f"{role}_wv"].var())}


def _shrink(total, n, sigma2, prior_mean=0.0, min_n=60, k=None):
    """Empirical-Bayes normal shrinkage of a per-ball rate toward the prior mean.

    k = sigma2 / tau2 is the number of balls at which a player's own data gets 50% weight.
    tau2 (true between-player variance) is estimated by method of moments unless k is given.
    """
    raw = np.where(n > 0, total / np.maximum(n, 1), prior_mean)
    if k is None:
        ok = n >= min_n
        tau2 = np.var(raw[ok]) - np.mean(sigma2 / n[ok]) if ok.sum() > 5 else 1e-5
        k = sigma2 / max(tau2, 1e-5)
    return prior_mean + (raw - prior_mean) * n / (n + k), raw, k


def rate(pm: pd.DataFrame, role: str, sigma2: dict, weights=None, mins=None, match_w=None, fixed=None):
    """Return the rating table for every player (eligible flag included).

    fixed: parameters from a previous full-sample fit (returned in .attrs["params"]).
           Used by the bootstrap so resampled data is scored with the same model.
    """
    weights = weights or C.WEIGHTS
    fx = fixed or {}
    params = {}
    if mins is None:
        mins = (dict(balls=C.MIN_BAT_PRESSURE_BALLS, matches=C.MIN_BAT_PRESSURE_INNINGS, base=C.MIN_BAT_BASELINE_BALLS)
                if role == "bat" else
                dict(balls=C.MIN_BOWL_PRESSURE_BALLS, matches=C.MIN_BOWL_PRESSURE_MATCHES, base=C.MIN_BOWL_BASELINE_BALLS))
    t = pm if match_w is None else pm.assign(_w=pm["match_id"].map(match_w).fillna(0)).query("_w > 0")
    w = t["_w"] if match_w is not None else 1
    num = [c for c in t.columns if c not in ("pid", "match_id", "competition", "_w")]
    tw = t[num].multiply(w, axis=0)
    tw["pid"] = t["pid"].values
    tw["match_success"] = ((t["n_High"] >= C.MATCH_MIN_PRESSURE_BALLS)
                           & (t["rv_High"] >= -C.CONSISTENCY_TOLERANCE_RUNS)).astype(int) * w
    tw["match_count"] = (t["n_High"] >= C.MATCH_MIN_PRESSURE_BALLS).astype(int) * w
    tw["p_matches"] = (t["n_High"] > 0).astype(int) * w
    tw["ipl_hi"] = np.where(t["competition"] == "IPL", t["n_High"], 0) * w
    p = tw.groupby("pid").sum()

    # each component shrunk on its own reliability, then summed (runs currency per ball)
    for bd, tag in (("High", "P"), ("Ordinary", "N")):
        for comp in ("rv", "wv"):
            key = f"k_{tag}_{comp}"
            p[f"{tag}_{comp}"], p[f"{tag}_{comp}_raw"], params[key] = _shrink(
                p[f"{comp}_{bd}"].values, p[f"n_{bd}"].values, sigma2[comp], k=fx.get(key))
        p[f"{tag}_level"] = p[f"{tag}_rv"] + p[f"{tag}_wv"]
        p[f"{tag}_raw"] = (p[f"v_{bd}"] / p[f"n_{bd}"].replace(0, np.nan)).fillna(0)

    # pressure delta (own pressure vs own ordinary), shrunk as a difference per component
    nH, nO = p["n_High"].clip(lower=1).values, p["n_Ordinary"].clip(lower=1).values
    both = (p["n_High"] >= 60) & (p["n_Ordinary"] >= 60)
    p["delta"], p["delta_raw"] = 0.0, 0.0
    for comp in ("rv", "wv"):
        d = p[f"{comp}_High"].values / nH - p[f"{comp}_Ordinary"].values / nO
        noise = sigma2[comp] * (1 / nH + 1 / nO)
        key = f"tau2_delta_{comp}"
        tau2 = fx.get(key)
        if tau2 is None:
            tau2 = max(np.var(d[both]) - np.mean(noise[both]), 1e-5) if both.sum() > 5 else 1e-5
        params[key] = float(tau2)
        p["delta"] += d * tau2 / (tau2 + noise)
        p["delta_raw"] += d

    base_rate = fx.get("consistency_base_rate", p["match_success"].sum() / max(p["match_count"].sum(), 1))
    params["consistency_base_rate"] = float(base_rate)
    a = C.CONSISTENCY_PRIOR_MATCHES
    p["consistency"] = (p["match_success"] + a * base_rate) / (p["match_count"] + a)
    p["consistency_raw"] = (p["match_success"] / p["match_count"].replace(0, np.nan)).fillna(base_rate)
    p["eligible"] = ((p["n_High"] >= mins["balls"]) & (p["p_matches"] >= mins["matches"])
                     & (p["n_Ordinary"] >= mins["base"]))

    # z-scores use the spread of the RAW (unshrunk) estimates, so shrinkage is not undone:
    # a component that is mostly noise keeps a small spread and therefore a small influence.
    e = p["eligible"]
    for col, raw, key in (("P_level", "P_raw", "pressure_level"), ("delta", "delta_raw", "pressure_delta"),
                          ("consistency", "consistency_raw", "consistency")):
        mu = fx.get(f"mu_{key}", p.loc[e, col].mean())
        sd = fx.get(f"sd_{key}", p.loc[e, raw].std())
        params[f"mu_{key}"], params[f"sd_{key}"] = float(mu), float(sd)
        p[f"z_{key}"] = (p[col] - mu) / sd
    p["rating"] = sum(weights[k] * p[f"z_{k}"] for k in weights)
    p["rank"] = np.nan
    p.loc[e, "rank"] = p.loc[e, "rating"].rank(ascending=False, method="first")
    out = p.reset_index().sort_values("rank")
    out.attrs["params"] = params
    return out
