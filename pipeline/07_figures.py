"""Phase 7a - Figures for the methodology report (outputs/figures/*.png)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY, INK, INK2, GRID = "#b9b8b2", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 10,
    "axes.titlecolor": INK, "figure.dpi": 160, "savefig.bbox": "tight", "legend.frameon": False,
})


def fig_pressure_validation():
    v = pd.read_csv(C.RESULTS / "03_pressure_validation_by_decile.csv")
    fig, ax = plt.subplots(1, 3, figsize=(9.5, 2.8))
    for a, col, lab in zip(ax, ["wicket_pct", "pct_second_innings", "pct_death"],
                           ["Wicket % per legal ball", "% of balls in a run chase", "% of balls in overs 16-20"]):
        colors = [BLUE if d >= 9 else GREY for d in v["pi_decile"]]
        a.bar(v["pi_decile"], v[col], color=colors, width=0.7)
        a.set_title(lab)
        a.set_xlabel("Pressure Index decile (10 = highest)")
        a.set_xticks(range(1, 11))
        a.grid(axis="x", visible=False)
    fig.suptitle("High-pressure deliveries differ from ordinary ones (top-20% band in blue)", color=INK, fontsize=10, y=1.04)
    fig.savefig(C.FIG / "fig1_pressure_validation.png")
    plt.close(fig)


def fig_pressure_heatmap(b):
    d = b[(b["innings"] == 2) & (b["is_legal"] == 1)].copy()
    d["overs_left"] = pd.cut(d["balls_left"], [0, 12, 24, 36, 48, 60, 72, 90, 120],
                             labels=["1-2", "3-4", "5-6", "7-8", "9-10", "11-12", "13-15", "16-20"])
    d["rrr_b"] = pd.cut(d["rrr"], [-1, 6, 8, 10, 12, 14, 18, 99],
                        labels=["<6", "6-8", "8-10", "10-12", "12-14", "14-18", ">18"])
    h = d.pivot_table(index="rrr_b", columns="overs_left", values="pressure_index", aggfunc="mean", observed=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    im = ax.imshow(h.values, cmap="Blues", aspect="auto", origin="lower", vmin=0)
    ax.set_xticks(range(h.shape[1]), h.columns)
    ax.set_yticks(range(h.shape[0]), h.index)
    ax.set_xlabel("Overs remaining in the chase")
    ax.set_ylabel("Required run rate")
    ax.grid(False)
    for i in range(h.shape[0]):
        for j in range(h.shape[1]):
            val = h.values[i, j]
            if np.isfinite(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7,
                        color="white" if val > np.nanmax(h.values) * 0.55 else INK)
    ax.set_title("Mean Pressure Index in chases: highest when the game is close and late")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pressure Index (1 = average ball)")
    fig.savefig(C.FIG / "fig2_pressure_heatmap_chase.png")
    plt.close(fig)


def fig_example_match(b):
    m = pd.read_parquet(C.INTER / "matches_clean.parquet")
    finals = m[m["stage"] == "Final"]["match_id"]
    s = b[b["match_id"].isin(finals) & (b["innings"] == 2)].groupby("match_id")["pressure_index"].mean()
    mid = s.idxmax()
    d = b[b["match_id"] == mid].reset_index(drop=True)
    info = m.set_index("match_id").loc[mid]
    x = np.arange(len(d))
    chase_team = d.loc[d["innings"] == 2, "batting_team_id"].iloc[0]
    wp_chase = np.where(d["batting_team_id"] == chase_team, d["wp"], 1 - d["wp"])
    fig, ax = plt.subplots(2, 1, figsize=(8, 3.8), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
    ax[0].plot(x, wp_chase, color=BLUE, lw=2)
    ax[0].set_ylabel("Chasing side\nwin probability")
    ax[0].set_ylim(0, 1)
    ax[1].bar(x, d["pressure_index"], color=np.where(d["pressure_band"] == "High", ORANGE, GREY), width=1.0)
    ax[1].set_ylabel("Pressure Index")
    ax[1].set_xlabel("Delivery number in match (innings break marked)")
    brk = int((d["innings"] == 1).sum())
    for a in ax:
        a.axvline(brk, color=INK2, lw=1, ls="--")
        a.grid(axis="x", visible=False)
    ax[0].set_title(f"Worked example: {info['comp_name']} Final - {info['home_team']} v {info['away_team']}\n"
                    f"{' '.join(str(info['result']).split())}", fontsize=9)
    ax[1].text(0.01, 0.85, "orange = high-pressure band", transform=ax[1].transAxes, color=INK2, fontsize=8)
    fig.savefig(C.FIG / "fig3_example_match.png")
    plt.close(fig)
    return mid


def fig_top10(role, fname):
    r = pd.read_csv(C.RESULTS / f"{fname}_ratings_all.csv")
    bs = pd.read_csv(C.RESULTS / f"06_bootstrap_{fname}.csv")
    top = r[r["eligible"]].head(C.TOP_N).merge(bs[["pid", "boot_p10_rank", "boot_p90_rank", "boot_median_rank", "p_top10"]], on="pid")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6), gridspec_kw={"width_ratios": [1.4, 1]})
    y = np.arange(len(top))[::-1]
    comps = [("z_pressure_level", "Pressure level", BLUE, C.WEIGHTS["pressure_level"]),
             ("z_consistency", "Consistency", AQUA, C.WEIGHTS["consistency"]),
             ("z_pressure_delta", "Delta vs own baseline", ORANGE, C.WEIGHTS["pressure_delta"])]
    left_pos, left_neg = np.zeros(len(top)), np.zeros(len(top))
    for col, lab, colr, w in comps:
        v = top[col].values * w
        start = np.where(v >= 0, left_pos, left_neg)
        ax[0].barh(y, v, left=start, color=colr, height=0.62, label=lab, edgecolor="white", linewidth=1)
        left_pos += np.where(v >= 0, v, 0)
        left_neg += np.where(v < 0, v, 0)
    ax[0].set_yticks(y, [f"{int(k)}. {n}" for k, n in zip(top["rank"], top["player"])])
    ax[0].axvline(0, color=INK2, lw=0.8)
    ax[0].set_xlabel("Weighted contribution to rating (z units)")
    ax[0].set_title("What drives each rating")
    ax[0].legend(loc="lower right", fontsize=7.5)
    ax[0].grid(axis="y", visible=False)
    ax[1].hlines(y, top["boot_p10_rank"], top["boot_p90_rank"], color=GREY, lw=3)
    ax[1].plot(top["boot_median_rank"], y, "o", color=INK2, ms=5, label="bootstrap median rank")
    ax[1].plot(top["rank"], y, "o", color=BLUE, ms=7, label="reported rank")
    ax[1].set_yticks(y, [""] * len(y))
    ax[1].set_xlabel("Rank (grey bar = 10th-90th percentile,\n300 bootstrap resamples of matches)")
    ax[1].set_title("How certain is the rank?")
    ax[1].set_xlim(0, max(55, top["boot_p90_rank"].max() + 2))
    ax[1].legend(loc="lower right", fontsize=7.5)
    ax[1].grid(axis="y", visible=False)
    title = "Top 10 batters" if role == "bat" else "Top 10 bowlers"
    fig.suptitle(title, color=INK, fontsize=11, fontweight="bold", y=1.02)
    fig.savefig(C.FIG / f"fig_top10_{fname}.png")
    plt.close(fig)


def fig_scatter(role, fname):
    r = pd.read_csv(C.RESULTS / f"{fname}_ratings_all.csv")
    e = r[r["eligible"]]
    top = e.head(C.TOP_N)
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    ax.scatter(e["ordinary_value_per100"], e["pressure_value_per100"], s=18, color=GREY, label="eligible players",
               edgecolor="white", linewidth=0.8)
    ax.scatter(top["ordinary_value_per100"], top["pressure_value_per100"], s=40, color=BLUE, label="top 10",
               edgecolor="white", linewidth=1)
    lim = [min(e["ordinary_value_per100"].min(), e["pressure_value_per100"].min()) - 1,
           max(e["ordinary_value_per100"].max(), e["pressure_value_per100"].max()) + 1]
    ax.plot(lim, lim, color=INK2, lw=0.8, ls="--")
    ax.text(lim[1], lim[1], " pressure = ordinary", color=INK2, fontsize=7, ha="right", va="bottom")
    for _, t in top.iterrows():
        ax.annotate(t["player"], (t["ordinary_value_per100"], t["pressure_value_per100"]), fontsize=6.5,
                    color=INK, xytext=(3, 2), textcoords="offset points")
    unit = "runs" if role == "bat" else "runs saved"
    ax.set_xlabel(f"Ordinary situations: {unit} above expected per 100 balls (shrunk)")
    ax.set_ylabel(f"High pressure: {unit} above expected per 100 balls (shrunk)")
    ax.set_title(("Batters" if role == "bat" else "Bowlers") + ": pressure vs ordinary performance")
    ax.legend(loc="lower right", fontsize=7.5)
    fig.savefig(C.FIG / f"fig_scatter_{fname}.png")
    plt.close(fig)


def fig_reliability():
    c = pd.read_csv(C.RESULTS / "06_component_reliability.csv")
    c = c[c["band"] != "All"]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    labels = [f"{'Bat' if r.role == 'bat' else 'Bowl'}\n{r.component}\n{'high' if r.band == 'High' else 'ord.'}" for r in c.itertuples()]
    ax.bar(range(len(c)), c["split_half_r"], color=[BLUE if v > 0.1 else GREY for v in c["split_half_r"]], width=0.6)
    ax.set_xticks(range(len(c)), labels, fontsize=7)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("Split-half correlation")
    ax.set_title("Runs value repeats across matches; wicket value above expectation does not")
    ax.grid(axis="x", visible=False)
    fig.savefig(C.FIG / "fig_component_reliability.png")
    plt.close(fig)


def main():
    b = pd.read_parquet(C.INTER / "balls_value.parquet")
    fig_pressure_validation()
    fig_pressure_heatmap(b)
    mid = fig_example_match(b)
    for role, fname in (("bat", "batting"), ("bowl", "bowling")):
        fig_top10(role, fname)
        fig_scatter(role, fname)
    fig_reliability()
    (C.RESULTS / "07_example_match.txt").write_text(str(mid))
    print("figures written to", C.FIG)


if __name__ == "__main__":
    main()
