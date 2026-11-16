// Builds submission/SupeRR_Selector_R1_Submission.pptx from outputs/results/deck_data.json (all numbers come from the pipeline).
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "outputs", "results", "deck_data.json"), "utf8"));
const FIG = D.fig_dir;
const OUT = path.join(__dirname, "..", "submission", "SupeRR_Selector_R1_Submission.pptx");

// ---------------------------------------------------------------- theme (hex, no '#')
const NAVY = "1B2A4A", PINK = "D6336C", BLUE = "2A78D6", AQUA = "1BAF7A", ORANGE = "EB6834";
const INK = "1B1B1B", INK2 = "52514E", MUTED = "8A8983", TINT = "F2F4F8", LINE = "DADDE3", WHITE = "FFFFFF";
const HEAD = "Cambria", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "SupeRR Selector Season 2 - Round 1 submission";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
const W = 13.333, H = 7.5, MX = 0.6;

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: W - 2 * MX, h: 0.8, fontFace: HEAD,
      fontSize: 30, bold: true, color: NAVY, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "SupeRR Selector S2 · Round 1 · Most reliable players under pressure",
      options: { x: MX, y: H - 0.42, w: 8, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: W - MX - 0.6, y: H - 0.42, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTED, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: NAVY }, objects: [] });

// ---------------------------------------------------------------- helpers
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function img(slide, name, x, y, maxW, maxH, alt) {
  const f = `${FIG}/${name}`;
  const s = pngSize(f);
  let w = maxW, h = (maxW * s.h) / s.w;
  if (h > maxH) { h = maxH; w = (maxH * s.w) / s.h; }
  slide.addImage({ path: f, x: x + (maxW - w) / 2, y, w, h, altText: alt });
  return { w, h };
}
function txt(slide, text, o) {
  slide.addText(text, Object.assign({ isTextBox: true, fontFace: BODY, fontSize: 14, color: INK, margin: 0,
    valign: "top" }, o));
}
function bullets(slide, items, o) {
  const runs = items.map((t, i) => {
    const parts = Array.isArray(t) ? t : [{ text: t }];
    return parts.map((p, j) => ({ text: p.text, options: Object.assign({ bullet: j === 0 ? { indent: 14 } : undefined,
      breakLine: j === parts.length - 1 && i < items.length - 1, paraSpaceAfter: 6 }, p.options || {}) }));
  }).flat();
  txt(slide, runs, Object.assign({ fontSize: 14, color: INK }, o));
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || TINT },
    line: { color: fill || TINT } });
}
function stat(slide, x, y, w, big, label, color) {
  txt(slide, big, { x, y, w, h: 0.75, fontFace: HEAD, fontSize: 36, bold: true, color: color || NAVY });
  txt(slide, label, { x, y: y + 0.78, w, h: 0.7, fontSize: 12, color: INK2 });
}
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}
const pct = (v) => `${v}%`;
const TIER_COLOR = { "Retain": AQUA, "Priority target": PINK, "Strong option": BLUE, "Depth option": INK2,
  "Lower priority": MUTED, "Unlikely available": MUTED };

// ================================================================ 1. Title
pres.addSection({ title: "Answer" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Answer" });
txt(s, "SupeRR Selector Season 2 · Round 1", { x: MX + 0.2, y: 1.1, w: 10, h: 0.4, fontSize: 16, color: "C9D3E6" });
txt(s, "Who delivers when it matters?", { x: MX + 0.2, y: 1.7, w: 11, h: 1.0, fontFace: HEAD, fontSize: 44,
  bold: true, color: WHITE });
txt(s, "A data-driven pressure rating for IPL and T20I batters and bowlers (2022-2026), and what the most reliable " +
  "players could bring to Rajasthan Royals at the IPL 2027 auction", { x: MX + 0.2, y: 2.85, w: 10.5, h: 1.0,
  fontSize: 18, color: "C9D3E6" });
const facts = [[`${D.scope.clean_matches}`, "matches analysed"], [`${(D.scope.clean_balls / 1000).toFixed(0)}k`, "deliveries scored for pressure"],
  [`${D.scope.matches_by_competition.IPL} / ${D.scope.matches_by_competition.T20I}`, "IPL / T20I matches"]];
facts.forEach((f, i) => {
  txt(s, f[0], { x: MX + 0.2 + i * 3.6, y: 4.7, w: 3.3, h: 0.8, fontFace: HEAD, fontSize: 36, bold: true, color: PINK });
  txt(s, f[1], { x: MX + 0.2 + i * 3.6, y: 5.5, w: 3.3, h: 0.4, fontSize: 14, color: "C9D3E6" });
});

// ================================================================ 2. Answer up front
s = content("The 10 most reliable batters and bowlers under pressure", "Answer");
[["Batters", D.batters], ["Bowlers", D.bowlers]].forEach(([lab, rows], c) => {
  const x = MX + c * 6.15;
  card(s, x, 1.35, 5.9, 5.45);
  txt(s, lab, { x: x + 0.3, y: 1.5, w: 3, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: NAVY });
  rows.forEach((r, i) => {
    const y = 2.05 + i * 0.465;
    txt(s, `${r.rank}`, { x: x + 0.3, y, w: 0.45, h: 0.4, fontFace: HEAD, fontSize: 16, bold: true, color: PINK });
    txt(s, r.player, { x: x + 0.8, y, w: 2.7, h: 0.4, fontSize: 15, bold: true });
    txt(s, r.ipl_2026 === "Not in IPL 2026 squads" ? "T20I only (2026)" : r.ipl_2026,
      { x: x + 3.45, y: y + 0.03, w: 2.3, h: 0.4, fontSize: 11, color: r.ipl_2026.includes("Rajasthan") ? PINK : INK2 });
  });
});
txt(s, "Right-hand labels show each player's IPL 2026 franchise; pink means already in Rajasthan Royals' squad.",
  { x: MX, y: 6.85, w: 11, h: 0.3, fontSize: 11, color: INK2 });

// ================================================================ 3. How it works
pres.addSection({ title: "Methodology" });
s = content("Five steps from ball-by-ball data to a ranking", "Methodology");
const steps = [
  ["Rebuild every ball", "Score, wickets, balls left, target and required rate before each of 192k deliveries (DLS-aware)"],
  ["Measure pressure", "Win-probability model, then leverage: how much this one ball can swing the result"],
  ["Set an expectation", "What an average player would produce in exactly this situation, opposition and venue"],
  ["Rate players", "Value above expectation under pressure, compared with the player's own baseline, plus consistency"],
  ["Test reliability", "Split-half checks, 300 bootstrap resamples and 10 sensitivity scenarios"],
];
steps.forEach((st, i) => {
  const x = MX + i * 2.45;
  card(s, x, 1.6, 2.25, 4.2);
  s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.85, w: 0.7, h: 0.7, fill: { color: i === 1 ? PINK : NAVY },
    line: { color: i === 1 ? PINK : NAVY } });
  txt(s, `${i + 1}`, { x: x + 0.25, y: 1.85, w: 0.7, h: 0.7, fontFace: HEAD, fontSize: 22, bold: true, color: WHITE,
    align: "center", valign: "middle" });
  txt(s, st[0], { x: x + 0.25, y: 2.8, w: 1.85, h: 0.8, fontFace: HEAD, fontSize: 17, bold: true, color: NAVY });
  txt(s, st[1], { x: x + 0.25, y: 3.65, w: 1.85, h: 2.0, fontSize: 13, color: INK2 });
});
txt(s, "Every model is cross-fitted by match: no match is scored by a model that saw it. All parameters are in pipeline/config.py.",
  { x: MX, y: 6.2, w: 12, h: 0.4, fontSize: 13, color: INK2, italic: true });

// ================================================================ 4. Pressure definition
s = content("Pressure = how much one ball can change who wins", "Methodology");
bullets(s, [
  [{ text: "Win-probability model ", options: { bold: true } }, { text: `learned from the data: runs required, balls left, wickets, overs, competition, team Elo gap and venue. Out-of-sample AUC ${D.wp.wp_innings2.auc} (chase) and ${D.wp.wp_innings1.auc} (first innings).` }],
  [{ text: "Leverage ", options: { bold: true } }, { text: "= expected absolute swing in win probability over the possible outcomes of the next ball (dot, 1, 2, 3, 4, 6, wicket, wide)." }],
  [{ text: "Pressure Index ", options: { bold: true } }, { text: `= leverage ÷ average (1.0 = a typical ball). High pressure = top 20% (PI ≥ ${D.pi_high.toFixed(2)}). Ordinary baseline = bottom 50%.` }],
  [{ text: "Why this definition: ", options: { bold: true } }, { text: "it combines required rate, wickets, balls left, phase and closeness in one number, applies identically to batter and bowler, and gives no credit for dead games." }],
], { x: MX, y: 1.45, w: 5.6, h: 5.2, fontSize: 15 });
img(s, "fig2_pressure_heatmap_chase.png", 6.5, 1.5, 6.25, 5.1, "Heatmap of mean pressure index by required run rate and overs remaining in chases");

// ================================================================ 5. Validation
s = content("High-pressure balls really are different", "Methodology");
const hb = D.band.find((b) => b.pressure_band === "High"), ob = D.band.find((b) => b.pressure_band === "Ordinary");
stat(s, MX, 1.45, 2.9, `${D.top_decile.pct_second_innings.toFixed(0)}%`, "of top-decile pressure balls come in run chases", PINK);
stat(s, MX + 3.1, 1.45, 2.9, `${D.top_decile.pct_death.toFixed(0)}%`, `are in overs 16-20 (vs ${D.low_half_death.toFixed(0)}% for the lower half)`);
stat(s, MX + 6.2, 1.45, 2.9, `${hb.wicket_pct.toFixed(1)}%`, `wicket rate per legal ball under high pressure vs ${ob.wicket_pct.toFixed(1)}% ordinary`);
stat(s, MX + 9.3, 1.45, 2.9, `${hb.mean_abs_wp_from_half.toFixed(2)} vs ${ob.mean_abs_wp_from_half.toFixed(2)}`, "average distance of win probability from 50/50: high-pressure games are genuinely open");
img(s, "fig1_pressure_validation.png", MX, 3.25, 12.1, 3.6, "Bar charts of wicket rate, share of chase balls and death-over balls by pressure decile");

// ================================================================ 6. Worked example
s = content("Worked example: the IPL 2023 Final, ball by ball", "Methodology");
img(s, "fig3_example_match.png", MX, 1.35, 8.4, 5.6, "Win probability and pressure index trace for the IPL 2023 final");
bullets(s, [
  "First-innings balls rarely reach the high-pressure band: the result is still far away.",
  "Pressure builds through the rain-reduced chase as win probability hovers near 50%.",
  "The last two balls (10 needed, then 4) carry the highest Pressure Index in the match: one ball decides the title.",
  "The same index scores the batter and the bowler on that ball, so both roles are judged on identical moments.",
], { x: 9.3, y: 1.6, w: 3.45, h: 5.2, fontSize: 14 });

// ================================================================ 7. Performance measurement
s = content("Performance = value above an average player in the same spot", "Methodology");
const fcards = [
  ["Batter value per ball", "(runs − expected runs) − wicket cost × (out − expected out)", BLUE],
  ["Bowler value per ball", "(expected conceded − conceded) + wicket cost × (wicket − expected wicket)", AQUA],
];
fcards.forEach((c, i) => {
  card(s, MX, 1.45 + i * 1.45, 6.2, 1.25);
  txt(s, c[0], { x: MX + 0.3, y: 1.58 + i * 1.45, w: 5.6, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: c[2] });
  txt(s, c[1], { x: MX + 0.3, y: 2.0 + i * 1.45, w: 5.7, h: 0.6, fontSize: 14 });
});
bullets(s, [
  "Expectations come from player-blind models using over, wickets, chase equation, IPL or T20I, team strength (Elo), venue and pace or spin.",
  `Wickets are converted to runs with a run-expectancy model: a wicket costs ${D.wicket_cost.Powerplay} runs in the powerplay, ${D.wicket_cost.Middle} in the middle overs and ${D.wicket_cost.Death} at the death.`,
], { x: MX, y: 4.5, w: 6.2, h: 2.3, fontSize: 14 });
const comps = [["Pressure level", D.weights.pressure_level, "Value per 100 high-pressure balls, shrunk for sample size", PINK],
  ["Delta vs own baseline", D.weights.pressure_delta, "Pressure value minus the player's ordinary-situation value", BLUE],
  ["Consistency", D.weights.consistency, "Share of pressure spells without a failure (no worse than −2 runs vs expected)", AQUA]];
txt(s, "Rating = weighted z-scores of three components", { x: 7.3, y: 1.45, w: 5.5, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: NAVY });
comps.forEach((c, i) => {
  const y = 2.05 + i * 1.5;
  s.addShape(pres.shapes.OVAL, { x: 7.3, y, w: 1.0, h: 1.0, fill: { color: c[3] }, line: { color: c[3] } });
  txt(s, `${Math.round(c[1] * 100)}%`, { x: 7.3, y, w: 1.0, h: 1.0, fontFace: HEAD, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle" });
  txt(s, c[0], { x: 8.5, y: y + 0.02, w: 4.2, h: 0.4, fontSize: 16, bold: true });
  txt(s, c[2], { x: 8.5, y: y + 0.42, w: 4.2, h: 0.7, fontSize: 13, color: INK2 });
});

// ================================================================ 8. Fair comparisons
s = content("Fair comparisons across samples, roles and competitions", "Methodology");
const fair = [
  ["Eligibility", `Batters: ≥${D.elig.bat[0]} high-pressure balls in ≥${D.elig.bat[1]} matches, ≥${D.elig.bat[2]} ordinary balls. Bowlers: ≥${D.elig.bowl[0]} / ≥${D.elig.bowl[1]} / ≥${D.elig.bowl[2]}. About 105 qualify in each list.`],
  ["Shrinkage for small samples", "Each rate is pulled toward average in proportion to how noisy it is (empirical Bayes). The runs and wicket parts are shrunk separately because their reliability differs greatly."],
  ["IPL and T20I together", "Pooled, but every expectation is conditioned on competition, both teams' Elo and venue, so runs against weak attacks or associate nations count for less."],
  ["Roles and contexts", "Phase, wickets, chase state and pace or spin are in the expectation, so death specialists and openers are each judged against what is normal for that job."],
];
fair.forEach((f, i) => {
  const x = MX + (i % 2) * 6.15, y = 1.45 + Math.floor(i / 2) * 2.7;
  card(s, x, y, 5.95, 2.45);
  txt(s, f[0], { x: x + 0.3, y: y + 0.25, w: 5.3, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: NAVY });
  txt(s, f[1], { x: x + 0.3, y: y + 0.8, w: 5.35, h: 1.5, fontSize: 14, color: INK2 });
});

// ================================================================ 9-12. Evidence
pres.addSection({ title: "Evidence" });
function topTable(title, rows, bat) {
  const sl = content(title, "Evidence");
  const hdr = bat ? ["#", "Batter", "Pressure balls", "SR pressure / ordinary", "Avg (pressure)", "Runs above exp. /100", "Consistency", "Top-10 in bootstrap"]
    : ["#", "Bowler", "Pressure balls", "Econ pressure / ordinary", "Wkts (pressure)", "Runs saved /100", "Consistency", "Top-10 in bootstrap"];
  const H_ = hdr.map((h) => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 12, valign: "middle" } }));
  const body = rows.map((r, i) => {
    const fill = { color: i % 2 ? WHITE : TINT };
    const cells = bat ? [r.rank, r.player, r.pressure_balls, `${r.sr_p} / ${r.sr_o}`, r.avg_p ?? "-", `${r.value100 > 0 ? "+" : ""}${r.value100}`, pct(r.consistency), pct(r.p_top10)]
      : [r.rank, r.player, r.pressure_balls, `${r.econ_p.toFixed(2)} / ${r.econ_o.toFixed(2)}`, r.wkts_p, `${r.value100 > 0 ? "+" : ""}${r.value100}`, pct(r.consistency), pct(r.p_top10)];
    return cells.map((c, j) => ({ text: String(c), options: { fill, fontSize: 13, bold: j === 1, color: j === 0 ? PINK : INK } }));
  });
  sl.addTable([H_, ...body], { x: MX, y: 1.4, w: 12.1, colW: [0.5, 2.6, 1.3, 2.0, 1.4, 1.6, 1.3, 1.4], rowH: 0.42,
    fontFace: BODY, border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle", margin: 0.06 });
  return sl;
}
s = topTable("Top 10 batters: the numbers behind the order", D.batters, true);
txt(s, `Pressure balls = deliveries faced in the top-20% pressure band. "Runs above exp. /100" is shrunk for sample size. Batters' change from their own baseline had no detectable spread between players, so it shrank to about zero and does not move the order.`,
  { x: MX, y: 6.25, w: 12.1, h: 0.7, fontSize: 12, color: INK2 });

s = content("Batters: level under pressure and consistency drive the order", "Evidence");
img(s, "fig_top10_batting.png", MX, 1.35, 12.1, 5.55, "Rating components and bootstrap rank intervals for the top 10 batters");

s = topTable("Top 10 bowlers: the numbers behind the order", D.bowlers, false);
txt(s, `Pressure balls = deliveries bowled in the top-20% band. "Runs saved /100" includes wickets converted to runs, but wickets above expectation did not repeat across matches, so they are shrunk almost entirely: runs saved under pressure decide the order.`,
  { x: MX, y: 6.25, w: 12.1, h: 0.7, fontSize: 12, color: INK2 });

s = content("Bowlers: level, consistency and a small baseline effect", "Evidence");
img(s, "fig_top10_bowling.png", MX, 1.35, 12.1, 5.55, "Rating components and bootstrap rank intervals for the top 10 bowlers");

// ================================================================ 13. Reliability
s = content("How much to trust the ranking", "Evidence");
const sb = D.sens_batting, sw = D.sens_bowling;
const ov = (arr, name) => arr.find((r) => r.scenario === name).top10_overlap;
stat(s, MX, 1.45, 3.0, `${Math.round(D.reliability.bat.top10_mean_p_top10 * 100)}% / ${Math.round(D.reliability.bowl.top10_mean_p_top10 * 100)}%`,
  "average chance a listed batter / bowler stays top 10 across 300 resamples", PINK);
stat(s, MX + 3.2, 1.45, 3.0, `${ov(sb, "Equal weights (1/3 each)")} / ${ov(sw, "Equal weights (1/3 each)")} of 10`, "top 10 kept with equal weights (batters / bowlers)");
stat(s, MX, 3.25, 3.0, `${ov(sb, "High = top 25%")} / ${ov(sw, "High = top 25%")} of 10`, "kept if the pressure band is widened to the top 25%");
stat(s, MX + 3.2, 3.25, 3.0, `${ov(sb, "Stricter eligibility (+50%)")} / ${ov(sw, "Stricter eligibility (+50%)")} of 10`, "kept with 50% stricter eligibility");
bullets(s, [
  "Top 3-4 in each list are well supported; ranks 6-10 are close calls among similar players.",
  "Wicket-taking above expectation does not repeat across matches, so it is shrunk out.",
  "Results depend most on where the pressure cut-off sits; leverage was kept because it is validated, not hand-tuned.",
  "Dismissal codes are inferred (the text column is empty); first-innings pressure is measured less precisely (AUC 0.66).",
], { x: MX, y: 5.0, w: 6.3, h: 2.0, fontSize: 13 });
img(s, "fig_component_reliability.png", 7.1, 1.5, 5.65, 5.2, "Split-half reliability of runs and wicket value components");

// ================================================================ 14. RR gaps
pres.addSection({ title: "Rajasthan Royals" });
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Rajasthan Royals" });
txt(s, "Building for IPL 2027", { x: MX + 0.2, y: 2.3, w: 11, h: 1.0, fontFace: HEAD, fontSize: 44, bold: true, color: WHITE });
txt(s, "Where Rajasthan Royals lose value under pressure, and which of the most reliable players fill those gaps",
  { x: MX + 0.2, y: 3.45, w: 10.5, h: 1.0, fontSize: 20, color: "C9D3E6" });

s = content("RR's pressure gap is death bowling, then death batting", "Rajasthan Royals");
const P = (side, ph) => D.rr_profile.find((r) => r.side === side && r.phase === ph);
const phases = ["Powerplay", "Middle", "Death"];
["Batting", "Bowling"].forEach((side, i) => {
  s.addChart(pres.charts.BAR, [
    { name: "Rajasthan Royals", labels: phases, values: phases.map((p) => P(side, p).rr_val100) },
    { name: "IPL average", labels: phases, values: phases.map((p) => P(side, p).league_avg_val100) },
  ], { x: MX + i * 4.0, y: 1.4, w: 3.85, h: 3.9, barDir: "col", barGrouping: "clustered", chartColors: [PINK, "B9B8B2"],
    showTitle: true, title: `${side} under pressure, IPL 2025-26`, titleFontSize: 13, titleColor: NAVY, titleFontFace: BODY,
    showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: BODY,
    showValue: true, dataLabelFontSize: 10, dataLabelFormatCode: "0.0", dataLabelColor: INK2, dataLabelFontFace: BODY,
    catAxisLabelColor: INK2, catAxisLabelFontSize: 11, catAxisLabelFontFace: BODY, valAxisLabelColor: INK2, valAxisLabelFontSize: 10,
    valAxisLabelFontFace: BODY, valGridLine: { color: "E6E5E0", size: 0.5 }, catGridLine: { style: "none" },
    valAxisTitle: "value per 100 pressure balls", showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: INK2 });
});
const bAll = P("Batting", "All"), wAll = P("Bowling", "All"), wD = P("Bowling", "Death"), bD = P("Batting", "Death"), pace = P("Bowling", "All (Pace)"), spin = P("Bowling", "All (Spin)");
txt(s, "Rank among 10 IPL teams, IPL 2025-26 high-pressure balls", { x: MX, y: 5.45, w: 7.8, h: 0.3, fontSize: 11, color: INK2 });
[[`#${bAll.rr_rank_of_10}`, "batting overall"], [`#${bD.rr_rank_of_10}`, "batting at the death"], [`#${wAll.rr_rank_of_10}`, "bowling overall"], [`#${wD.rr_rank_of_10}`, "bowling at the death"]]
  .forEach((k, i) => {
    txt(s, k[0], { x: MX + i * 1.95, y: 5.8, w: 1.8, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: i === 3 ? PINK : NAVY });
    txt(s, k[1], { x: MX + i * 1.95, y: 6.4, w: 1.8, h: 0.4, fontSize: 12, color: INK2 });
  });
card(s, 8.75, 1.4, 4.0, 5.4);
const db = D.rr_death_bowlers_2026;
bullets(s, [
  [{ text: "Batting: ", options: { bold: true } }, { text: `#1 in the powerplay (Jaiswal and Sooryavanshi), but #${bD.rr_rank_of_10} at the death. A proven pressure finisher is the batting need.` }],
  [{ text: "Bowling: ", options: { bold: true } }, { text: `#${wD.rr_rank_of_10} of 10 at the death. Pace under pressure is #${pace.rr_rank_of_10} (${pace.rr_val100}), while spin is above average (#${spin.rr_rank_of_10}).` }],
  [{ text: "2026 death overs: ", options: { bold: true } }, { text: `${db[0].bowler_name} carried the load (${db[0].balls} pressure balls, ${db[0].val100 > 0 ? "+" : ""}${db[0].val100}); the next options were well below average on small samples.` }],
], { x: 9.0, y: 1.65, w: 3.55, h: 5.0, fontSize: 13 });

// ================================================================ 15-16. Player fit
function fitSlide(title, rows, bat) {
  const sl = content(title, "Rajasthan Royals");
  const hdr = ["#", bat ? "Batter" : "Bowler", "Role", "IPL 2026", "RR fit", "Recommendation", "Why (data)"];
  const H_ = hdr.map((h) => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, valign: "middle" } }));
  const body = rows.map((r, i) => {
    const fill = { color: i % 2 ? WHITE : TINT };
    const why = r.caveat ? `${r.why} Note: ${r.caveat}.` : r.why;
    return [
      { text: String(r.rank), options: { fill, color: PINK, bold: true } },
      { text: r.player, options: { fill, bold: true } },
      { text: r.role, options: { fill } },
      { text: r.ipl_2026 === "Not in IPL 2026 squads" ? "None (T20I)" : r.ipl_2026, options: { fill } },
      { text: r.fit_index.toFixed(1), options: { fill, align: "center" } },
      { text: r.tier, options: { fill, bold: true, color: TIER_COLOR[r.tier] } },
      { text: why, options: { fill, fontSize: 10, color: INK2 } },
    ];
  });
  sl.addTable([H_, ...body], { x: MX, y: 1.3, w: 12.1, colW: [0.4, 1.75, 1.8, 1.75, 0.65, 1.45, 4.3], fontSize: 11,
    fontFace: BODY, color: INK, border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle", margin: 0.05, rowH: 0.46 });
  return sl;
}
const nb = D.need_batters, nw = D.need_bowlers;
s = fitSlide("How each top-10 batter fits Rajasthan Royals", D.batters, true);
txt(s, `RR fit = shrunk pressure value per phase, weighted by RR's need (phase weights from RR's rank among 10 teams: PP ${nb.Powerplay.toFixed(2)}, middle ${nb.Middle.toFixed(2)}, death ${nb.Death.toFixed(2)}).`,
  { x: MX, y: 6.78, w: 12.1, h: 0.35, fontSize: 11, color: INK2 });
s = fitSlide("How each top-10 bowler fits Rajasthan Royals", D.bowlers, false);
txt(s, `RR fit weights: PP ${nw.Powerplay.toFixed(2)}, middle ${nw.Middle.toFixed(2)}, death ${nw.Death.toFixed(2)}. Auction availability (retentions, releases, player registration) is outside the supplied data; "Not in IPL 2026" status is from the squad file.`,
  { x: MX, y: 6.78, w: 12.1, h: 0.35, fontSize: 11, color: INK2 });

// ================================================================ 17. Fit charts (native)
s = content("Who adds the most where RR need it", "Rajasthan Royals");
[["Batters", D.batters], ["Bowlers", D.bowlers]].forEach(([lab, rows], i) => {
  const sorted = [...rows].sort((a, b) => a.fit_index - b.fit_index);
  s.addChart(pres.charts.BAR, [{ name: "RR fit", labels: sorted.map((r) => r.player), values: sorted.map((r) => r.fit_index) }], {
    x: MX + i * 6.15, y: 1.35, w: 5.95, h: 5.0, barDir: "bar", chartColors: [i === 0 ? BLUE : AQUA], showLegend: false,
    showTitle: true, title: `${lab}: RR fit index (need-weighted pressure value)`, titleFontSize: 13, titleColor: NAVY, titleFontFace: BODY,
    showValue: true, dataLabelFormatCode: "0.0", dataLabelFontSize: 10, dataLabelColor: INK2, dataLabelFontFace: BODY,
    catAxisLabelColor: INK, catAxisLabelFontSize: 11, catAxisLabelFontFace: BODY, catAxisLabelPos: "low", valAxisLabelColor: INK2, valAxisLabelFontSize: 10,
    valAxisLabelFontFace: BODY, valGridLine: { color: "E6E5E0", size: 0.5 }, catGridLine: { style: "none" } });
});
txt(s, "Higher = more value in the phases where RR rank worst under pressure. Fit ranks players for RR's needs; it does not replace the overall pressure ranking.",
  { x: MX, y: 6.5, w: 12.1, h: 0.4, fontSize: 12, color: INK2 });

// ================================================================ 18. Auction plan
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Rajasthan Royals" });
txt(s, "IPL 2027 auction plan for Rajasthan Royals", { x: MX, y: 0.45, w: 12, h: 0.8, fontFace: HEAD, fontSize: 32, bold: true, color: WHITE });
const all = [...D.batters.map((r) => ({ ...r, kind: "bat" })), ...D.bowlers.map((r) => ({ ...r, kind: "bowl" }))];
const by = (t) => all.filter((r) => r.tier === t).sort((a, b) => b.fit_index - a.fit_index);
const cols = [
  ["Retain", by("Retain"), "Already in RR's 2026 squad and in our top 10: keep the core"],
  ["Priority targets", by("Priority target"), "Best fit for RR's death-over pressure gaps"],
  ["Options", [...by("Strong option"), ...by("Depth option")], "Reliable under pressure; useful cover"],
  ["Lower priority", [...by("Lower priority"), ...by("Unlikely available")], "Duplicate RR strengths (powerplay) or availability doubts"],
];
cols.forEach(([h, rows, sub], i) => {
  const x = MX + i * 3.08;
  card(s, x, 1.5, 2.9, 5.35, "24365C");
  txt(s, h, { x: x + 0.22, y: 1.65, w: 2.5, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: i === 1 ? "F39AB8" : WHITE });
  txt(s, sub, { x: x + 0.22, y: 2.12, w: 2.5, h: 0.7, fontSize: 12, color: "C9D3E6" });
  txt(s, rows.length ? rows.flatMap((r, j) => [
    { text: r.player, options: { bold: true, color: WHITE, breakLine: true } },
    { text: `${r.kind === "bat" ? "Bat" : "Bowl"} · best: ${r.best_phase} · fit ${r.fit_index.toFixed(1)}`, options: { color: "C9D3E6", fontSize: 11, breakLine: j < rows.length - 1, paraSpaceAfter: 6 } },
  ]) : "-", { x: x + 0.22, y: 2.95, w: 2.55, h: 3.8, fontSize: 14, color: WHITE });
});
txt(s, "Order within each column = RR fit. Auction availability depends on 2027 retentions and registrations, which are not in the supplied data.",
  { x: MX, y: 6.95, w: 12.1, h: 0.35, fontSize: 11, color: "C9D3E6" });

// ================================================================ 19. Reproducibility
pres.addSection({ title: "Appendix" });
s = content("Reproducibility", "Appendix");
bullets(s, [
  "Python pipeline (pandas, scikit-learn, scipy, matplotlib): python pipeline/run_all.py rebuilds every number, chart, the Word report and this deck.",
  "Steps: 01 clean and join · 02 match state · 03 pressure index · 04 expected model · 05 ratings · 06 reliability · 07-08 figures and report · 09 RR fit · 10 deck data.",
  `Scope: IPL 2022-26 and T20Is only. Excluded: ${D.scope.excluded_out_of_scope_matches} A-team matches, ${D.scope.excluded_no_result_matches} no-result or abandoned matches, Super Overs.`,
  "Legal balls exclude wides and both no-ball codes (98.2% of overs then have exactly six). Run outs are never credited to bowlers. Retirements are not dismissals.",
  "Fixed random seed; 5-fold match-grouped cross-fitting; all thresholds and weights in pipeline/config.py were set before the rankings were inspected.",
  "Full per-player tables: outputs/results/batting_ratings_all.csv, bowling_ratings_all.csv, 09_rr_player_fit_*.csv.",
], { x: MX, y: 1.45, w: 12.1, h: 5.4, fontSize: 15 });

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote", OUT));
