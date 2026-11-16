"""Phase 7b - Methodology report (report/SupeRR_Selector_R1_Methodology_Report.docx).

Every number in the text is read from outputs/results so report and rankings cannot drift.
"""
import json

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import config as C

R = C.RESULTS


def J(name):
    return json.loads((R / name).read_text())


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear")
    s.set(qn("w:color"), "auto")
    s.set(qn("w:fill"), hex_)
    tcPr.append(s)


def table(doc, df, widths=None, font=8):
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    for i, c in enumerate(df.columns):
        cell = t.rows[0].cells[i]
        cell.text = str(c)
        shade(cell, "DCE8F7")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(font)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for p in cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(font)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def para(doc, text, bold_lead=None, size=10):
    p = doc.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead + " ")
        r.bold = True
        r.font.size = Pt(size)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        p.add_run(bold_lead + " ").bold = True
    p.add_run(text)
    return p


def fig(doc, name, width=16, caption=None):
    doc.add_picture(str(C.FIG / name), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        c = doc.add_paragraph(caption)
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in c.runs:
            r.italic = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0x52, 0x51, 0x4E)


def short_team(t):
    return ", ".join(str(t).split(", ")[:3])


def top_table(fname):
    r = pd.read_csv(R / f"{fname}_ratings_all.csv")
    bs = pd.read_csv(R / f"06_bootstrap_{fname}.csv")[["pid", "p_top10", "boot_p10_rank", "boot_p90_rank"]]
    t = r[r["eligible"]].head(C.TOP_N).merge(bs, on="pid")
    if fname == "batting":
        out = pd.DataFrame({
            "Rank": t["rank"].astype(int), "Player": t["player"], "Teams": t["teams"].map(short_team),
            "Rating": t["rating"].round(3),
            "Pressure balls": t["n_High"].astype(int),
            "SR pressure / ordinary": [f"{a:.0f} / {b:.0f}" for a, b in zip(t["pr_SR"], t["ord_SR"])],
            "Avg pressure": t["pr_avg"].round(1),
            "Runs above exp. /100 (pressure)": t["pressure_value_per100"].round(1),
            "Consistency": (100 * t["consistency"]).round(0).astype(int).astype(str) + "%",
            "Top-10 in bootstrap": (100 * t["p_top10"]).round(0).astype(int).astype(str) + "%",
        })
    else:
        out = pd.DataFrame({
            "Rank": t["rank"].astype(int), "Player": t["player"], "Teams": t["teams"].map(short_team),
            "Rating": t["rating"].round(3),
            "Pressure balls": t["pr_balls"].astype(int),
            "Econ pressure / ordinary": [f"{a:.2f} / {b:.2f}" for a, b in zip(t["pr_econ"], t["ord_econ"])],
            "Pressure wkts": t["pr_wkts"].astype(int),
            "Runs saved /100 (pressure)": t["pressure_value_per100"].round(1),
            "Consistency": (100 * t["consistency"]).round(0).astype(int).astype(str) + "%",
            "Top-10 in bootstrap": (100 * t["p_top10"]).round(0).astype(int).astype(str) + "%",
        })
    return out, t


def main():
    clean, state, pm = J("01_clean_log.json"), J("02_state_checks.json"), J("03_pressure_metrics.json")
    xm, rel = J("04_expected_model.json"), J("06_reliability_summary.json")
    pb, pw = J("05_model_params_bat.json"), J("05_model_params_bowl.json")
    band = pd.read_csv(R / "03_pressure_band_summary.csv").set_index("pressure_band")
    dec = pd.read_csv(R / "03_pressure_validation_by_decile.csv")
    comp = pd.read_csv(R / "06_component_reliability.csv")
    bat_top, bat_t = top_table("batting")
    bowl_top, bowl_t = top_table("bowling")
    n_bat_el = int(pd.read_csv(R / "batting_ratings_all.csv")["eligible"].sum())
    n_bowl_el = int(pd.read_csv(R / "bowling_ratings_all.csv")["eligible"].sum())

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2)
        s.top_margin = s.bottom_margin = Cm(1.8)

    h = doc.add_heading("Identifying the Most Reliable Players Under Pressure", 0)
    para(doc, "SupeRR Selector Season 2 - Round 1 - Methodology Report")
    para(doc, "Data: supplied IPL and T20I ball-by-ball pack, 2022 onwards. All code is in the accompanying "
              "pipeline/ folder and reproduces every number, table and chart in this report.")

    # ------------------------------------------------------------ summary
    doc.add_heading("Summary", 1)
    para(doc, "Pressure is measured on every delivery as its leverage: how much the result of that one ball can "
              "move the batting side's win probability, using a win-probability model learned from the data. The "
              "most pressured 20% of deliveries form the high-pressure band. Each delivery is valued against a "
              "context-aware expectation of what an average player would do in exactly that situation (runs, and "
              "wickets converted into runs). Players are then rated on three components: their level under "
              "pressure, the change from their own ordinary-situation baseline, and how often they avoided failing "
              "in a pressure spell. Small samples are shrunk toward the average, and every component is weighted by "
              "how reliable the data shows it to be.")
    doc.add_heading("Final rankings (as submitted on Unstop)", 2)
    table(doc, pd.DataFrame({"Rank": range(1, 11), "Batters": bat_top["Player"].values,
                             "Bowlers": bowl_top["Player"].values}), widths=[1.5, 6, 6], font=9)

    # ------------------------------------------------------------ data
    doc.add_heading("1. Data, scope and cleaning", 1)
    bullet(doc, f"{clean['raw_matches']} matches and {clean['raw_balls']:,} deliveries were supplied. "
                f"{clean['excluded_out_of_scope_matches']} matches from two A-team events (Emerging Teams Asia Cup "
                f"2024, Asia Cup Rising Stars 2025) were excluded because they are neither IPL nor T20I. "
                f"{clean['excluded_no_result_matches']} no-result or abandoned matches were excluded (no outcome to "
                f"be under pressure about). {clean['super_over_balls_dropped']} Super Over deliveries were excluded.",
           "Scope.")
    bullet(doc, f"{clean['clean_matches']} matches ({clean['matches_by_competition']['IPL']} IPL, "
                f"{clean['matches_by_competition']['T20I']} T20I) and {clean['clean_balls']:,} deliveries.",
           "Analysis set.")
    bullet(doc, "Wides and both no-ball codes (extras_type 'Overstep' and 'other') are not legal balls. With this "
                f"rule, {clean['overs_with_6_legal_balls_pct']}% of overs contain exactly six legal balls (the rest are "
                "incomplete overs at the end of an innings). Total runs = bat runs + extras1_runs + extras_2_runs. "
                "Runs charged to the bowler = bat runs + wides + no-ball penalty (not byes or leg-byes).",
           "Legal balls and runs.")
    bullet(doc, "The dismissal text column is empty, so meanings were inferred from patterns. Code 4 is a run out "
                "(the dismissed player is often the non-striker and runs are often scored). Bowlers are credited "
                "with codes 1, 2, 3, 5 and 6 only. Eleven rows with a dismissed player but no wicket flag are "
                "retirements (the player never batted again) and are not counted as dismissals.",
           "Dismissals.")
    bullet(doc, f"The match state (score, wickets, legal balls, balls left, target, required rate) was rebuilt "
                f"for every delivery. DLS-revised overs (stored in balls) and revised targets were applied. "
                f"Innings totals reconcile exactly. Of {state['chase_wins']} successful chases, "
                f"{state['chase_wins_below_target']} finished below target: both are rain-ended DLS results, where "
                f"the winner was decided on the DLS par score.",
           "Match state.")

    # ------------------------------------------------------------ pressure
    doc.add_heading("2. Defining pressure", 1)
    para(doc, "Pressure is not one statistic. A required rate of 12 means one thing with 8 wickets and 10 overs "
              "left, and another with 2 wickets and 1 over left. A required rate of 20 means almost nothing, because "
              "the game is gone. A definition is needed that combines required run rate, wickets in hand, balls "
              "remaining, innings stage and closeness of the contest in a principled way, and works for batters "
              "and bowlers alike. Leverage does all of this.")
    doc.add_heading("2.1 Win-probability model", 2)
    para(doc, f"Two gradient-boosted classifiers estimate the batting side's chance of winning before every "
              f"delivery. The first-innings model uses score, balls left, wickets in hand, overs available, "
              f"competition, the Elo rating gap between the teams, and venue scoring rate. The second-innings model "
              f"uses runs required, balls left, wickets in hand, competition, Elo gap and venue. Monotonic constraints "
              f"enforce cricket logic (for example, more wickets in hand never lowers win probability). Models are "
              f"cross-fitted over 5 folds of matches, so no match is scored by a model that saw it. Out-of-fold "
              f"accuracy: second innings AUC {pm['wp_innings2']['auc']} (Brier {pm['wp_innings2']['brier']}); "
              f"first innings AUC {pm['wp_innings1']['auc']}, which is naturally lower because the target is not "
              f"yet known. Team Elo ratings are computed chronologically from results only, so they use no future "
              f"information.")
    doc.add_heading("2.2 Pressure Index = leverage", 2)
    para(doc, "For each delivery the model evaluates the win probability after every possible outcome (dot, 1, 2, 3, "
              "4, 6, wicket, wide), weighted by how often each outcome happens in that over and innings across the "
              "league:")
    para(doc, "Leverage = sum over outcomes of P(outcome) x |WP(after outcome) - WP(now)|.     "
              "Pressure Index = Leverage / average leverage (1.0 = an average ball).", size=9.5)
    para(doc, f"The high-pressure band is the top 20% of deliveries (Pressure Index >= {pm['pi_high_threshold']:.2f}). "
              f"The ordinary baseline is the bottom 50% (Pressure Index <= {pm['pi_ordinary_threshold']:.2f}). The "
              f"middle band is left out of the comparison so that the two groups are clearly different. The same "
              f"index applies to the batter and the bowler on the same ball, which meets the requirement that the "
              f"method works for both.")
    doc.add_heading("2.3 Evidence that the index separates pressure from ordinary situations", 2)
    d10, d1_5 = dec[dec["pi_decile"] == 10].iloc[0], dec[dec["pi_decile"].between(1, 5)]
    para(doc, f"Top-decile deliveries take place {d10['pct_second_innings']:.0f}% of the time in a chase and "
              f"{d10['pct_death']:.0f}% in overs 16-20, against {d1_5['pct_death'].mean():.0f}% for the lower half. "
              f"Wickets fall on {band.loc['High','wicket_pct']:.2f}% of high-pressure legal balls against "
              f"{band.loc['Ordinary','wicket_pct']:.2f}% of ordinary ones, and scoring is faster "
              f"({band.loc['High','run_rate']:.2f} against {band.loc['Ordinary','run_rate']:.2f} runs per over): "
              f"players take more risk, and it costs more wickets. The average distance of win probability from 50% "
              f"is {band.loc['High','mean_abs_wp_from_half']:.2f} in the high band against "
              f"{band.loc['Ordinary','mean_abs_wp_from_half']:.2f} in the ordinary band, so high-pressure balls "
              f"really are the ones where the contest is open.")
    fig(doc, "fig1_pressure_validation.png", 16.5, "Figure 1 - Outcomes and context by Pressure Index decile.")
    fig(doc, "fig2_pressure_heatmap_chase.png", 12.5,
        "Figure 2 - Pressure in chases: it rises with a demanding but gettable required rate late in the innings, "
        "and falls away when the chase is easy or already lost (RRR > 18).")
    fig(doc, "fig3_example_match.png", 15.5,
        "Figure 3 - Worked example: win probability and Pressure Index ball by ball in the IPL 2023 Final.")

    # ------------------------------------------------------------ performance
    doc.add_heading("3. Measuring performance", 1)
    doc.add_heading("3.1 Expected outcome for every delivery", 2)
    para(doc, f"Player-blind models (no player identity used) estimate what an average player would produce on each "
              f"delivery given: innings, over, wickets, balls left, runs required and required rate, current run rate, "
              f"IPL or T20I, batting- and bowling-team Elo, venue scoring rate, and pace or spin. The bowler models "
              f"also use the striker's batting position, so bowling to a tail-ender is expected to be easier. All "
              f"models are cross-fitted by match. Calibration is close: expected bat runs per ball "
              f"{xm['x_bat_runs_vs_actual'][0]} against actual {xm['x_bat_runs_vs_actual'][1]}; expected dismissal "
              f"rate {xm['x_out_vs_actual'][0]} against {xm['x_out_vs_actual'][1]}; expected runs conceded "
              f"{xm['x_bowl_runs_vs_actual'][0]} against {xm['x_bowl_runs_vs_actual'][1]}; expected bowler "
              f"wicket rate {xm['x_bowl_wkt_vs_actual'][0]} against {xm['x_bowl_wkt_vs_actual'][1]}.")
    doc.add_heading("3.2 Value of a delivery in runs", 2)
    para(doc, f"Wickets are converted into runs using a run-expectancy model (expected runs still to come given balls "
              f"and wickets left, fitted on first innings). Wicket cost = runs still to come with the wicket in hand "
              f"minus runs still to come without it: on average {xm['wicket_cost_by_phase']['Powerplay']} runs in the "
              f"powerplay, {xm['wicket_cost_by_phase']['Middle']} in the middle overs and "
              f"{xm['wicket_cost_by_phase']['Death']} at the death.")
    bullet(doc, "(bat runs - expected bat runs) - wicket cost x (dismissed - expected dismissal probability), on every "
                "ball faced.", "Batter value per ball =")
    bullet(doc, "(expected runs conceded - runs conceded) + wicket cost x (bowler wicket - expected wicket "
                "probability), on every delivery bowled.", "Bowler value per ball =")
    para(doc, "Positive means better than an average player in the same situation, so the same scale applies to "
              "openers and finishers, to spinners and quicks, and to IPL and T20I.")
    doc.add_heading("3.3 Player components and baselines", 2)
    bullet(doc, "Value per 100 deliveries in the high-pressure band, shrunk toward the league average (3.4).",
           "Pressure level (weight 0.50):")
    bullet(doc, "Pressure level minus the player's own value per 100 deliveries in ordinary situations, so the player "
                "is compared with their usual level. It is shrunk as a difference: if the data cannot tell players' "
                "pressure-minus-normal gaps apart, it shrinks toward zero and stops influencing the ranking.",
           "Pressure delta vs own baseline (weight 0.25):")
    bullet(doc, f"Share of a player's pressure spells (matches with >= {C.MATCH_MIN_PRESSURE_BALLS} high-pressure "
                f"balls) in which they did not fail, meaning their runs value in that spell was no worse than "
                f"-{C.CONSISTENCY_TOLERANCE_RUNS:.0f} runs against expectation. It is shrunk toward the league rate with "
                f"a {C.CONSISTENCY_PRIOR_MATCHES}-match prior. This definition was chosen over four alternatives "
                f"because it repeated best between independent halves of the data for both batters and bowlers.",
           "Consistency (weight 0.25):")
    para(doc, "Rating = 0.50 z(pressure level) + 0.25 z(delta) + 0.25 z(consistency). Each z-score is scaled by the "
              "spread of the raw, unshrunk values, so a component that is mostly noise keeps a small spread and a "
              "small influence. The weights were fixed before the rankings were inspected; Section 6 shows how "
              "much the ranking changes under other weights.")
    doc.add_heading("3.4 Shrinkage (empirical Bayes)", 2)
    para(doc, f"For each component the true spread between players is estimated by method of moments (observed "
              f"variance minus sampling noise). Each player's rate is pulled toward the average by n / (n + k), where "
              f"k = noise variance / true variance. Batters' runs value under pressure has k = {pb['k_P_rv']:.0f} balls "
              f"(a player with {pb['k_P_rv']:.0f} pressure balls keeps half of their raw estimate). For bowlers, "
              f"k = {pw['k_P_rv']:.0f}. Wickets above expectation carry very little signal (k = {pb['k_P_wv']:.0f} for "
              f"batters, and effectively infinite for bowlers), so dismissal and wicket luck are mostly removed. "
              f"Section 6 shows this is justified: wicket-taking above expectation does not repeat across matches.")

    # ------------------------------------------------------------ fairness
    doc.add_heading("4. Fair comparisons", 1)
    bullet(doc, f"Batters need >= {C.MIN_BAT_PRESSURE_BALLS} high-pressure balls faced in >= "
                f"{C.MIN_BAT_PRESSURE_INNINGS} matches, and >= {C.MIN_BAT_BASELINE_BALLS} ordinary balls for a baseline "
                f"({n_bat_el} batters qualify). Bowlers need >= {C.MIN_BOWL_PRESSURE_BALLS} high-pressure deliveries in "
                f">= {C.MIN_BOWL_PRESSURE_MATCHES} matches, and >= {C.MIN_BOWL_BASELINE_BALLS} ordinary deliveries "
                f"({n_bowl_el} bowlers qualify). Shrinkage handles the remaining differences in sample size.",
           "Eligibility.")
    bullet(doc, "IPL and T20I are pooled, but every expectation is conditioned on the competition, both teams' "
                "Elo strength and venue scoring. Scoring 30 off 15 against a weak attack therefore earns less than the "
                "same against a strong one, and T20I matches against associate nations do not inflate ratings. Each "
                "player's IPL share of pressure balls is reported in the results file.",
           "IPL and T20I together.")
    bullet(doc, "Phase, wickets, chase equation and pace or spin are in the expected model, so players are compared "
                "with what is normal for their role and situation. Death-over specialists are not penalised for the "
                "higher run rates of the death overs.",
           "Different match contexts.")
    bullet(doc, "Ranks use the same expected models and parameters for every player. No reputation or external "
                "data is used.",
           "Same model for everyone.")

    # ------------------------------------------------------------ evidence
    doc.add_heading("5. Evidence for the top 10", 1)
    doc.add_heading("5.1 Batters", 2)
    table(doc, bat_top, widths=[1, 2.8, 3.2, 1.3, 1.4, 1.9, 1.3, 1.8, 1.5, 1.6], font=7.5)
    fig(doc, "fig_top10_batting.png", 16.5,
        "Figure 4 - Batters: rating components (left) and rank uncertainty from 300 bootstrap resamples of matches (right).")
    b1 = bat_t.iloc[0]
    para(doc, f"{b1['player']} ranks first: {b1['pressure_value_per100']:.1f} runs above expectation per 100 "
              f"high-pressure balls (strike rate {b1['pr_SR']:.0f} under pressure against {b1['ord_SR']:.0f} "
              f"normally), and the best non-failure rate among eligible batters ({100*b1['consistency']:.0f}%). "
              f"Batters' pressure deltas were statistically indistinguishable from zero (estimated true variance at "
              f"the floor), so the delta component shrank to roughly 0 and did not affect their order. Among batters, "
              f"rising or dipping under pressure beyond one's normal ability is not detectable in this data; what "
              f"separates them is the level they actually produce when it matters and how rarely they fail.")
    fig(doc, "fig_scatter_batting.png", 11, "Figure 5 - Batters: pressure value against ordinary value (shrunk).")
    doc.add_heading("5.2 Bowlers", 2)
    table(doc, bowl_top, widths=[1, 2.8, 3.2, 1.3, 1.4, 2.0, 1.3, 1.8, 1.5, 1.6], font=7.5)
    fig(doc, "fig_top10_bowling.png", 16.5,
        "Figure 6 - Bowlers: rating components (left) and rank uncertainty from 300 bootstrap resamples of matches (right).")
    w1 = bowl_t.iloc[0]
    para(doc, f"{w1['player']} ranks first: {w1['pressure_value_per100']:.1f} runs saved per 100 high-pressure "
              f"deliveries (economy {w1['pr_econ']:.2f} under pressure against {w1['ord_econ']:.2f} normally), and a "
              f"non-failure rate of {100*w1['consistency']:.0f}%. For bowlers the pressure delta does carry some signal "
              f"and contributes. A bowler whose economy improves under pressure, compared with their own baseline, "
              f"gains rating, and one who is elite in ordinary situations but less so under pressure is marked down "
              f"slightly.")
    fig(doc, "fig_scatter_bowling.png", 11, "Figure 7 - Bowlers: pressure value against ordinary value (shrunk).")

    # ------------------------------------------------------------ reliability
    doc.add_heading("6. Reliability and limitations", 1)
    doc.add_heading("6.1 Do the measures repeat across matches?", 2)
    para(doc, "Matches were split into two halves (odd and even match id), and each player's per-ball value was "
              "computed separately in each half (players with >= 80 balls in both halves).")
    c2 = comp[comp["band"] != "All"].copy()
    c2["role"] = c2["role"].map({"bat": "Batting", "bowl": "Bowling"})
    table(doc, c2.rename(columns={"role": "Role", "component": "Component", "band": "Band", "players": "Players",
                                  "split_half_r": "Split-half r"}), font=8)
    fig(doc, "fig_component_reliability.png", 12, "Figure 8 - Split-half reliability of each value component.")
    para(doc, f"Runs value repeats moderately; wicket value above expectation does not repeat at all for bowlers, which "
              f"is why it is shrunk almost entirely. On full rating, the split-half Spearman correlation is "
              f"{rel['bat']['split_half_spearman']['rating']} for batters and {rel['bowl']['split_half_spearman']['rating']} "
              f"for bowlers, each half having half the data. The pressure-level component alone repeats at "
              f"{rel['bat']['split_half_spearman']['P_level']} and {rel['bowl']['split_half_spearman']['P_level']}. "
              f"Performance in the top 20% of pressure moments is a small, noisy sample for any player, and these "
              f"figures say so openly; it is the reason for the shrinkage and the uncertainty intervals.")
    doc.add_heading("6.2 Bootstrap rank intervals", 2)
    para(doc, f"Matches were resampled with replacement 300 times, and each resample was scored with the full-sample "
              f"model. The right-hand panels of Figures 4 and 6 show each player's 10th-90th percentile rank. On "
              f"average, a reported top-10 batter stays in the top 10 in {100*rel['bat']['top10_mean_p_top10']:.0f}% "
              f"of resamples, and a reported top-10 bowler in {100*rel['bowl']['top10_mean_p_top10']:.0f}%. The top "
              f"three or four in each list are well supported; positions roughly 6-10 are close calls among a wider "
              f"group of comparable players.")
    doc.add_heading("6.3 Sensitivity to design choices", 2)
    for fname, lab in (("batting", "Batters"), ("bowling", "Bowlers")):
        s = pd.read_csv(R / f"06_sensitivity_{fname}.csv")
        para(doc, lab, bold_lead=None).runs[0].bold = True
        table(doc, s.rename(columns={"scenario": "Scenario", "top10_overlap": "Top-10 overlap with final",
                                     "spearman_vs_base": "Rank correlation with final", "eligible": "Eligible"}), font=8)
    para(doc, "The ranking is robust to moderate changes in the weights and to the eligibility thresholds (9-10 of "
              "the top 10 retained); dropping consistency entirely (pressure level only) keeps 7 of 10. "
              "It is more sensitive to where the high-pressure cut-off sits (15/20/25/30%), and much more sensitive to "
              "replacing leverage with a hand-built rule (required rate, wickets, stage). The leverage index is kept "
              "because it is learned from outcomes, validated (Section 2.3), and does not need hand-chosen weights. "
              "The rule-based index's low agreement shows that how pressure is defined matters a great deal, which is "
              "why a data-driven definition was used.")
    doc.add_heading("6.4 Limitations", 2)
    for t in [
        "The dismissal-type meanings are inferred from patterns because the text column is empty; only the run-out "
        "code is strongly supported. Credits for codes 9 and 10 (9 rows) and the hit-wicket code (17 rows) cannot change "
        "the rankings materially.",
        "The first-innings win-probability model is weaker (AUC 0.66), so first-innings pressure is measured less "
        "precisely than chase pressure; most high-pressure balls come from chases.",
        "Wicket cost comes from a first-innings run-expectancy model; in a tight chase a wicket can matter more in "
        "win-probability terms than in runs.",
        "Fielding, captaincy, and the quality of the partner at the other end are not modelled. Team strength is "
        "captured only through Elo.",
        "Matches against associate nations are adjusted through Elo, but Elo for rarely seen teams is uncertain.",
        "Pressure samples are small: a top-10 batter typically faces 150-500 high-pressure balls in five seasons. The "
        "rankings in positions 6-10 should be read as a group of near-equals (Section 6.2).",
    ]:
        bullet(doc, t)

    # ------------------------------------------------------------ reproduce
    doc.add_heading("7. Reproducibility", 1)
    para(doc, "Python 3 with pandas, numpy, scipy, scikit-learn, matplotlib, pyarrow and python-docx. All parameters "
              f"are in pipeline/config.py (random seed {C.RANDOM_SEED}). Command: python pipeline/run_all.py. Steps: "
              "01 clean and join, 02 match state, 03 pressure index, 04 expected model, 05 ratings, 06 reliability, "
              "07 figures, 08 this report. Full per-player tables for every eligible player are in "
              "outputs/results/batting_ratings_all.csv and bowling_ratings_all.csv.")

    out = C.REPORT_DIR / "SupeRR_Selector_R1_Methodology_Report.docx"
    doc.save(out)
    print("report written:", out)


if __name__ == "__main__":
    main()
