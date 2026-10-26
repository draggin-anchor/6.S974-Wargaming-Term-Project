const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./theme.js");
const FIG = process.env.FIG || (__dirname + "/../prototype/results/figures/");

const THEME = {
  name: "Gray Zone", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2430", lt1: "FFFFFF", dk2: "0B2545", lt2: "EEF3F8",
    accent1: "1F4E9C", accent2: "B23A48", accent3: "E8A33D", accent4: "13807A",
    accent5: "6B7A8F", accent6: "8DA9C4", hlink: "1F4E9C", folHlink: "6B7A8F",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "Gray-Zone Maritime Control: Workshop 1";
pres.author = "Sean Bowman, Tate Murphy, Matthew Newell";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "DARK", background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.6, fontSize: 40, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.05, w: 11.7, h: 1.6, fontSize: 18, color: C.accent6, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.8, fontSize: 28, bold: true, color: C.text2, valign: "middle" }, text: "" } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5 },
});

let n = 0;
function T(slide, text, opt) { n++; slide.addText(text, Object.assign({ isTextBox: true, objectName: "t" + n, fontSize: 16, color: C.text1, margin: 0 }, opt)); }
function bullets(slide, items, opt) {
  const runs = items.map((it, i) => {
    const o = { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 };
    const last = i < items.length - 1;
    if (Array.isArray(it)) return it.map((r, j) => ({ text: r.text, options: Object.assign({}, j === 0 ? { bullet: true, paraSpaceAfter: 6 } : {}, r.options || {}, j === it.length - 1 ? { breakLine: last } : {}) }));
    return [{ text: it, options: o }];
  }).flat();
  T(slide, runs, Object.assign({ valign: "top" }, opt));
}
function takeaway(slide, text, y) {
  n++;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: "tk" + n, x: 0.6, y: y || 6.25, w: 12.1, h: 0.65, fill: { color: C.background2 }, line: { color: C.accent1, width: 1 }, rectRadius: 0.08 });
  T(slide, [{ text: "Takeaway  ", options: { bold: true, color: C.accent1 } }, { text }], { x: 0.85, y: (y || 6.25) + 0.05, w: 11.6, h: 0.55, fontSize: 16, valign: "middle" });
}
function img(slide, file, x, y, w, h) { n++; slide.addImage({ path: FIG + file, x, y, w, h, objectName: "img" + n }); }
function content(section, title) { const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section }); s.addText(title, { placeholder: "title" }); return s; }

// ---------------------------------------------------------------- 1 title
pres.addSection({ title: "Introduction" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Introduction" });
s.addText("Gray-Zone Maritime Control in the First Island Chain", { placeholder: "title" });
s.addText("A networked escalation game  |  Workshop 1\nSean Bowman, Tate Murphy, Matthew Newell", { placeholder: "body" });
s.addNotes("(~30 s) We study day-to-day U.S.-China competition for control of the waters inside the First Island Chain, below the threshold of war. We built it as a game on a network. Today we cover the model, the prototype, and first results on three research questions.");

// ---------------------------------------------------------------- 2 problem
s = content("Introduction", "The problem: control without war");
img(s, "network.png", 0.6, 1.35, 4.9, 4.33);
T(s, "Network of 8 contested zones and 4 home ports", { x: 0.6, y: 5.75, w: 4.9, h: 0.3, fontSize: 12, color: C.accent5, italic: true });
bullets(s, [
  [{ text: "Players. ", options: { bold: true, color: C.accent1 } }, { text: "Blue: 10 U.S. destroyers (DDG). Red: 8 navy ships (PLAN) + 6 coast guard / militia hulls (CCG)." }],
  [{ text: "Each period (2 days). ", options: { bold: true } }, { text: "Each side chooses where its ships go and whether to patrol (P) or assert (A). Asserting means shadowing, close maneuvering, or querying and warning. For the U.S. it also covers freedom-of-navigation operations." }],
  [{ text: "Control ", options: { bold: true } }, { text: "of a zone follows the local force ratio, so each side's best move depends on the other's." }],
  [{ text: "Incidents ", options: { bold: true, color: C.accent2 } }, { text: "can happen when both sides are present, and are likelier if someone asserts. Incidents raise an escalation level. At the top is war, which costs both sides." }],
  [{ text: "Fog. ", options: { bold: true } }, { text: "Neither side sees the other's entire fleet disposition, only forces present where it also maintains forces. Storms can close zones." }],
], { x: 6.0, y: 1.45, w: 6.7, h: 4.6, fontSize: 18 });
s.addNotes("(~60 s) China claims most of the South China Sea and contests the Senkakus, pressing those claims with coast guard and militia hulls backed by navy ships. The U.S. keeps the seas open with destroyers on presence and freedom-of-navigation patrols (Helmus 2024; Green 2017). Squares are home ports, circles are the eight contested zones, grouped North, Center, South. Dashed lines are the extra Philippine port, one of our redesigns. Three things make this a game rather than a single optimization. Control is relative, so my best move depends on yours. Escalation risk is shared, because incidents need both sides present and war costs both. And neither side sees the other's full fleet, only the ships where it also has ships.");

// ---------------------------------------------------------------- 3 RQs + feedback
s = content("Introduction", "Research questions and what changed since the proposal");
const rq = [
  ["RQ1", "Control vs. war risk", "Each side caps how much incident risk it will accept each period (its risk budget ε). How much more control does a side gain by accepting more risk, how much more likely does war become, and what risk level does each side pick when it knows the other side is picking too?"],
  ["RQ2", "Game theory vs. rules of thumb", "Does planning with game theory (best responses, equilibrium or maximin plans) beat simple rules or random moves? Can both sides stay at patrol over many periods, because asserting once would end the truce and push both into riskier play from then on?"],
  ["RQ3", "Weather and redesign", "Does the plan or Blue redesign that works best in normal weather still work best across calm, typhoon and extreme weather scenarios, both on average and in the worst scenario?"],
];
rq.forEach((r, i) => {
  const y = 1.35 + i * 1.6;
  n++; s.addShape(pres.shapes.OVAL, { objectName: "c" + n, x: 0.6, y: y + 0.1, w: 0.8, h: 0.8, fill: { color: C.accent1 } });
  T(s, r[0], { x: 0.6, y: y + 0.1, w: 0.8, h: 0.8, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
  T(s, [{ text: r[1], options: { bold: true, breakLine: true } }, { text: r[2], options: { fontSize: 13 } }], { x: 1.6, y, w: 5.2, h: 1.5, fontSize: 16, valign: "top" });
});
n++;
s.addTable([
  [{ text: "Feedback", options: { bold: true, color: C.background1, fill: { color: C.text2 } } }, { text: "What we did", options: { bold: true, color: C.background1, fill: { color: C.text2 } } }],
  ["Model too high level", "Formal game on a graph"],
  ["Q1 is a feasible region, use a MIP", "Best response is an exact MIP. Commander types become risk budgets ε"],
  ["More ambitious questions", "Budget-game equilibrium (RQ1), equilibrium play (RQ2), robustness and redesign (RQ3)"],
  ["Define the resilient redesign", "Three Blue designs"],
  ["Propose values for missing data", "Assumed values, listed in the report"],
  ["Show preliminary results", "Analytical results, plus 77 setups × 200 simulated games"],
  ["Add weather (Prof. Sapsis)", "Weather scenarios, scored by expected and worst-case payoff"],
], { objectName: "fbtable", x: 7.0, y: 1.45, w: 5.7, colW: [2.0, 3.7], fontSize: 12, color: C.text1, border: { type: "solid", pt: 0.5, color: HEX.accent6 }, valign: "middle", rowH: 0.56 });
s.addNotes("(~60 s) Three questions. RQ1 asks this. Each side caps the incident risk it accepts per period. How much control does more risk buy, how much likelier does war become, and what cap does each side pick when the other is picking too? RQ2 asks whether a side that plans with game theory beat one that follows simple rules, and can both sides stay at patrol over many periods, because asserting once would end the truce and push both into riskier play from then on? RQ3 comes from Prof. Sapsis's comment. Does the best plan or Blue redesign in normal weather stay best across calm, typhoon and extreme weather scenarios, on average and in the worst scenario? The table maps each piece of Deliverable 1 feedback to what we changed. The main change is that the model is now fully formal, and the proposal's strategy types are a single risk-budget number inside a MIP.");

// ---------------------------------------------------------------- 4 model
pres.addSection({ title: "Model" });
s = content("Model", "The game, one period at a time");
const steps = ["The weather (sea state) of each region is drawn", "Each side sees its own ships and detects some enemy ships", "Ships low on endurance head home", "Both sides choose moves and postures at the same time", "Moves happen within movement budgets", "Control updates. Incidents are drawn. The escalation level moves", "Payoffs are paid. The game stops at war or after 60 periods"];
steps.forEach((t, i) => {
  const y = 1.4 + i * 0.66;
  n++; s.addShape(pres.shapes.OVAL, { objectName: "st" + n, x: 0.6, y, w: 0.5, h: 0.5, fill: { color: i === 0 ? C.accent4 : (i === 5 ? C.accent2 : C.accent1) } });
  T(s, String(i + 1), { x: 0.6, y, w: 0.5, h: 0.5, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  T(s, t, { x: 1.25, y, w: 5.2, h: 0.5, fontSize: 16, valign: "middle" });
});
n++; s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: "eqbox", x: 6.9, y: 1.4, w: 5.8, h: 4.55, fill: { color: C.background2 }, line: { color: C.accent6, width: 1 }, rectRadius: 0.08 });
T(s, [
  { text: "Control of zone v", options: { bold: true, color: C.accent1, breakLine: true } },
  { text: "c ← (1 − λ)·c + λ·φ,  λ = 0.3,   φ = (S_B − S_R) / (S_B + S_R + κ)", options: { fontFace: "Cambria", breakLine: true } },
  { text: "Presence builds control slowly. Leaving lets it decay.", options: { fontSize: 13, color: C.accent5, breakLine: true } },
  { text: " ", options: { fontSize: 8, breakLine: true } },
  { text: "Incident chance", options: { bold: true, color: C.accent2, breakLine: true } },
  { text: "h = (h₀ + h_A·[asserts]) · min(S_B, S_R) · (1 + ℓ/2),  ρ = 1 − e^(−h)", options: { fontFace: "Cambria", breakLine: true } },
  { text: "Needs both sides present. Grows with assertion and with the escalation level ℓ.", options: { fontSize: 13, color: C.accent5, breakLine: true } },
  { text: " ", options: { fontSize: 8, breakLine: true } },
  { text: "Payoff", options: { bold: true, color: C.text2, breakLine: true } },
  { text: "g = Σ V·c − γ·moves − η·ℓ − ζ_D,   minus W = 200 at war", options: { fontFace: "Cambria", breakLine: true } },
  { text: "Value of control minus fuel, tension and Blue's redesign cost ζ_D. War hurts both sides, so the game is not zero-sum.", options: { fontSize: 13, color: C.accent5 } },
], { x: 7.15, y: 1.55, w: 5.3, h: 4.3, fontSize: 14, valign: "top" });
takeaway(s, "Every rule is explicit, so the same game can be played thousands of times by different strategies.");
s.addNotes("(~70 s) Walk the timeline top to bottom. This is one two-day turn. The weather is drawn first, then both sides move at the same time without seeing each other's full fleet. The box holds all the dynamics. Control moves 30% of the way toward the local force ratio each turn. Incidents need both sides present, and are likelier when someone asserts and when tensions are already high. Payoff is value of zones held minus fuel, tension, and for Blue the running cost of its redesign, zeta-D. War costs both sides 200, so the game is not zero-sum. If asked, every number is our assumption, listed in Table 1 of the report.");

// ---------------------------------------------------------------- 5 decisions
s = content("Model", "How the players decide");
const cards = [
  ["Best response as a MIP", C.accent1, "Each period, choose moves and postures to maximize value of control minus costs, subject to the movement budget, endurance, and an escalation-risk budget.\n\nExpected incidents ≤ ε", "Conservative / moderate / aggressive = ε of 0.05 / 0.15 / 0.40"],
  ["Template game", C.accent4, "Abstract each side to 14 templates. A template says how to split ships North / Center / South, and whether to patrol or assert.\n\nA 14×14 strategic-form game", "Solved with iterated elimination of strictly dominated strategies (IESDS), Nash equilibrium, maximin LP, correlated-equilibrium LP"],
  ["Policies we compare", C.accent2, "Random moves\nRule of thumb (rule-based)\nQuick best response (greedy)\nBest response (MIP)\nNash equilibrium plan (equilibrium)\nSafety-first plan (maximin)", "Same random draws and weather for every policy"],
];
cards.forEach((c, i) => {
  const x = 0.6 + i * 4.1;
  n++; s.addShape(pres.shapes.RECTANGLE, { objectName: "cd" + n, x, y: 1.4, w: 3.9, h: 4.6, fill: { color: C.background2 }, line: { color: c[1], width: 1.5 } });
  n++; s.addShape(pres.shapes.RECTANGLE, { objectName: "cdh" + n, x, y: 1.4, w: 3.9, h: 0.6, fill: { color: c[1] }, line: { color: c[1], width: 1.5 } });
  T(s, c[0], { x: x + 0.2, y: 1.4, w: 3.5, h: 0.6, fontSize: 18, bold: true, color: C.background1, valign: "middle" });
  T(s, c[2], { x: x + 0.2, y: 2.15, w: 3.5, h: 2.7, fontSize: 15, valign: "top" });
  T(s, c[3], { x: x + 0.2, y: 4.95, w: 3.5, h: 0.9, fontSize: 13, italic: true, color: C.accent5, valign: "top" });
});
takeaway(s, "The proposal's strategy types are now one number, ε, inside an optimization (a MIP).");
s.addNotes("(~60 s) Two ways to decide. On the left, each turn a player solves a mixed-integer program (MIP) to pick moves, with a cap on expected incidents, epsilon. This answers the feedback that Q1 is a feasible region. In the middle, for equilibrium analysis we shrink each side to 14 templates and solve the 14-by-14 game exactly. On the right are the six policies we compare. All of them see the same random draws.");

// ---------------------------------------------------------------- 6 chicken
pres.addSection({ title: "Results" });
s = content("Results", "Small example: when does it pay to assert?");
n++;
const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, align: "center" } });
s.addTable([
  [hdr("Blue \\ Red"), hdr("Red patrols"), hdr("Red asserts")],
  [{ text: "Blue patrols", options: { bold: true } }, { text: "0 , 0", options: { align: "center" } }, { text: "−9.6 , +1.2", options: { align: "center" } }],
  [{ text: "Blue asserts", options: { bold: true } }, { text: "+0.3 , −10.5", options: { align: "center" } }, { text: "−11.4 , −11.3", options: { align: "center", color: C.accent2, bold: true } }],
], { objectName: "chicken", x: 0.6, y: 1.5, w: 6.0, colW: [1.8, 2.1, 2.1], rowH: 0.75, fontSize: 18, border: { type: "solid", pt: 0.75, color: HEX.accent6 }, valign: "middle" });
T(s, "Payoffs (Blue, Red) with force splits fixed, relative to both patrolling", { x: 0.6, y: 3.85, w: 6.0, h: 0.35, fontSize: 12, italic: true, color: C.accent5 });
bullets(s, [
  [{ text: "Best reply: ", options: { bold: true } }, { text: "assert if the other patrols, patrol if the other asserts. Two pure equilibria, plus a mixed one with mutual assertion 8% of the time." }],
  [{ text: "A mediator helps: ", options: { bold: true } }, { text: "the best correlated equilibrium never recommends (assert, assert). A hotline can play that role." }],
  [{ text: "Repetition helps: ", options: { bold: true } }, { text: "if both patrol and any assertion makes both fall back to the mixed equilibrium for good, mutual patrolling is a subgame perfect equilibrium for any discount factor above 0.18. Ours is 0.98." }],
], { x: 7.0, y: 1.5, w: 5.7, h: 4.5, fontSize: 17 });
takeaway(s, "Restraint is not stable in a one-shot encounter, but it can be sustained by repeated play or a coordination device.");
s.addNotes("(~70 s) A small example from our own game. Fix where ships go, so each side only chooses patrol or assert. In the table, asserting against a patroller pays a little, but if both assert, both lose more than 11. So the best reply is to do the opposite of the other side. That is an anti-coordination game. There are two fixes. First, a correlated equilibrium, which a mediator or hotline can implement, never recommends both asserting. Second, in the repeated game, a standing threat (if either side pushes, the truce is off for good and both fall back to the mixed equilibrium) makes mutual patrolling a subgame perfect equilibrium whenever the discount factor is above 0.18. Ours is 0.98.");

// ---------------------------------------------------------------- 7 prototype
s = content("Results", "The prototype: watch a game play out");
img(s, "gui_screenshot.png", 0.6, 1.45, 7.2, 4.57);
bullets(s, [
  [{ text: "Pick ", options: { bold: true } }, { text: "a plan for each side, a design and the weather on the right. Press New game, then Step or Play. Help explains the map." }],
  [{ text: "Zone color ", options: { bold: true } }, { text: "shows control. Blue = Blue, red = Red." }],
  [{ text: "B / P / C ", options: { bold: true } }, { text: "= destroyers, navy ships, coast guard. Thick outline = asserting." }],
  [{ text: "Orange ring ", options: { bold: true, color: C.accent3 } }, { text: "= incident. Shaded region = rough sea or storm." }],
  [{ text: "Run many games ", options: { bold: true } }, { text: "plays the same setup as many simulated games and reports averages." }],
], { x: 8.1, y: 1.45, w: 4.6, h: 4.7, fontSize: 16 });
s.addNotes("(~60 s, or a 60 s live demo) This is the prototype. Pick a plan for each side, a design and the weather, then Step or Play. Zone color is who controls it. Letters count ships. Thick outlines mean asserting, an orange ring is an incident, shading is bad weather. Bottom left is the escalation ladder. Level 5 is war. 'Run many games' gives averages. The screenshot is turn 12 with a storm over the North. The same file runs batch experiments, and a second script reproduces every number in the report.");

// ---------------------------------------------------------------- 8 RQ1
s = content("Results", "RQ1: more risk buys control, up to a point");
img(s, "frontier.png", 0.6, 1.35, 6.0, 4.17);
n++;
const cell = (t, war, bold) => ({ text: t + "\nwar " + war, options: { align: "center", bold: !!bold, color: bold ? C.accent2 : C.text1 } });
s.addTable([
  [hdr("Blue \\ Red"), hdr("Conservative"), hdr("Moderate"), hdr("Aggressive")],
  [{ text: "Conservative", options: { bold: true } }, cell("−194, 199", "10%"), cell("−303, 315", "11%"), cell("−308, 318", "12%")],
  [{ text: "Moderate", options: { bold: true } }, cell("18, −36", "15%"), cell("−144, 101", "20%"), cell("−192, 140", "21%")],
  [{ text: "Aggressive", options: { bold: true } }, cell("74, −80", "14%"), cell("−83, 16", "25%"), cell("−151, 39", "34%", true)],
], { objectName: "riskgame", x: 6.9, y: 1.5, w: 5.8, colW: [1.6, 1.4, 1.4, 1.4], rowH: 0.8, fontSize: 13, border: { type: "solid", pt: 0.5, color: HEX.accent6 }, valign: "middle" });
T(s, "Risk-budget game. Payoffs (Blue, Red) and war rate. Red bold = the only equilibrium.", { x: 6.9, y: 4.85, w: 5.8, h: 0.5, fontSize: 12, italic: true, color: C.accent5 });
T(s, "Raising Blue's budget from 0.02 to 0.15 lifts its control a lot. Beyond 0.25 it barely moves.", { x: 0.6, y: 5.55, w: 6.0, h: 0.5, fontSize: 13, color: C.accent5 });
takeaway(s, "Both sides choose aggressive (war 34%), yet both do better at moderate (war 20%). That is a prisoner's dilemma.");
s.addNotes("(~60 s) On the left, Blue loosens its risk budget while Red stays moderate. Control rises fast up to about 0.15, then flattens, while war risk keeps rising. On the right, both sides choose a budget. Aggressive is the best reply to anything, for both, so the only equilibrium is aggressive-aggressive, with the highest war rate, 34%. Both would do better at moderate-moderate. Blue gets −144 instead of −151, Red gets 101 instead of 39, and war falls to 20%. That is a prisoner's dilemma. Restraint has to come from repetition or coordination, as in the previous example.");

// ---------------------------------------------------------------- 9 RQ2
s = content("Results", "RQ2: the Nash equilibrium plan is the safest bet against any Red");
n++;
s.addChart(pres.charts.BAR, [{ name: "Blue payoff vs. its worst Red opponent", labels: ["Random moves", "Rule of thumb (rule-based)", "Safety-first plan (maximin)", "Best response (MIP)", "Quick best response (greedy)", "Nash equilibrium plan (equilibrium)"], values: [-319, -184, -221, -144, -137, -116] }], {
  objectName: "rq2chart", x: 0.6, y: 1.35, w: 7.2, h: 4.7, barDir: "bar",
  chartColors: [HEX.accent5, HEX.accent5, HEX.accent5, HEX.accent1, HEX.accent1, HEX.accent4],
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelColor: HEX.dk1,
  showTitle: true, title: "Blue payoff against its worst Red opponent (higher is better)", titleFontSize: 14, titleFontFace: "+mn-lt", titleColor: HEX.dk2,
  catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: HEX.dk1, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.accent5,
  valGridLine: { color: "DDE3EA", size: 0.5 }, catGridLine: { style: "none" }, catAxisLabelPos: "low", showLegend: false, valAxisMinVal: -350, valAxisMaxVal: 0,
});
bullets(s, [
  [{ text: "Nash equilibrium plan ", options: { bold: true, color: C.accent4 } }, { text: "has the best worst case (−116) and half the war rate of the MIP best response against the same opponent (10% vs 20%)." }],
  [{ text: "Best responses ", options: { bold: true, color: C.accent1 } }, { text: "(quick and MIP) win against weak opponents but escalate more." }],
  [{ text: "Safety-first plan ", options: { bold: true } }, { text: "is the most cautious (war ≤ 8%) but gives up the most control." }],
  [{ text: "Quick vs MIP: ", options: { bold: true } }, { text: "the quick heuristic matches the MIP 67% of the time but breaks the risk budget 14% of the time." }],
], { x: 8.1, y: 1.45, w: 4.6, h: 4.7, fontSize: 16 });
s.addNotes("(~60 s) Each Blue policy plays three Red policies, 200 games each. The bar is Blue's payoff against its worst opponent. The Nash equilibrium plan has the best worst case, and half the war rate of the MIP best response. Best responses do well against weak opponents but escalate. The safety-first plan is cautious but gives up control. Differences under about 20 points are ties.");

// ---------------------------------------------------------------- 10 RQ3
s = content("Results", "RQ3: the best strategy holds up in bad weather");
img(s, "weather.png", 0.6, 1.35, 5.9, 3.93);
T(s, "Rough seas weaken Red's coast guard hulls and storms pause operations, so most policies do slightly worse in calm seas. The top two plans stay on top in every scenario.", { x: 0.6, y: 5.35, w: 5.9, h: 0.75, fontSize: 13, color: C.accent5 });
n++;
s.addChart(pres.charts.BAR, [
  { name: "Expected", labels: ["D0 Baseline", "D1 Extra port", "D2 Extra surveillance", "D3 De-escalation"], values: [-144, -137, -162, -120] },
  { name: "Worst case", labels: ["D0 Baseline", "D1 Extra port", "D2 Extra surveillance", "D3 De-escalation"], values: [-164, -153, -181, -140] },
], {
  objectName: "rq3chart", x: 6.8, y: 1.35, w: 5.9, h: 3.6, barDir: "col", barGrouping: "clustered",
  chartColors: [HEX.accent1, HEX.accent2], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt", dataLabelColor: HEX.dk1,
  showTitle: true, title: "Blue payoff by design over weather scenarios", titleFontSize: 14, titleFontFace: "+mn-lt", titleColor: HEX.dk2,
  showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt",
  catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: HEX.dk1, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.accent5,
  valGridLine: { color: "DDE3EA", size: 0.5 }, catGridLine: { style: "none" }, catAxisLabelPos: "low", valAxisMinVal: -200, valAxisMaxVal: 0,
});
T(s, "War rate in normal weather is D0 20%, D1 28%, D2 23%, D3 5%. De-escalation measures were given no cost yet.", { x: 6.8, y: 5.0, w: 5.9, h: 0.4, fontSize: 13, color: C.accent5 });
takeaway(s, "The plan that is best on average is also best in the worst weather. De-escalation measures are the best design and cut war about 4×.");
s.addNotes("(~70 s) Robustness here means two numbers, expected payoff over the four weather scenarios, and worst case. On the left, the policy ranking does not change across weather. The top two plans stay on top. Bad weather slightly helps Blue here, because rough seas weaken Red's coast-guard hulls. On the right, of the three redesigns, de-escalation measures are best on average and in the worst case, and cut war about four times. We gave them no cost yet, and they also help Red, so it is a joint gain.");

// ---------------------------------------------------------------- 11 caveats
s = content("Results", "What the evidence does and does not show");
const col = (x, head, color, items) => {
  n++; s.addShape(pres.shapes.RECTANGLE, { objectName: "cv" + n, x, y: 1.4, w: 5.9, h: 0.6, fill: { color }, line: { color } });
  T(s, head, { x: x + 0.2, y: 1.4, w: 5.5, h: 0.6, fontSize: 18, bold: true, color: C.background1, valign: "middle" });
  bullets(s, items, { x: x + 0.1, y: 2.2, w: 5.7, h: 3.9, fontSize: 16 });
};
col(0.6, "Supported", C.accent4, [
  "Loosening the risk budget has sharply diminishing returns",
  "Left alone, both sides loosen their budgets (prisoner's dilemma)",
  "Restraint can be an equilibrium of the repeated game",
  "The Nash equilibrium plan is the most robust Blue policy here",
  "De-escalation measures are a joint gain under every weather scenario",
]);
col(6.8, "Not yet shown", C.accent2, [
  "All numbers are assumptions, not calibrated to data",
  "Policies look only one period ahead",
  "War penalty may be too small. The top-payoff policy also has the most wars",
  "De-escalation measures have no cost yet, so part of their win is built in",
  "Differences under about 20 payoff points are ties",
]);
s.addNotes("(~45 s) Be direct about limits. Left is what the runs support. Right is what they do not show. Values are assumptions, policies look one turn ahead, the war rate depends heavily on a few parameters, and the de-escalation result is partly built in. A sensitivity sweep is the first item for Workshop 2.");

// ---------------------------------------------------------------- 12 plan
pres.addSection({ title: "Next steps" });
s = content("Next steps", "Plan for Workshop 2");
const plan = [
  ["Nov 3", "Beliefs and attacks", "Bayesian beliefs about enemy positions. Weather tied to the calendar (typhoon season, winter monsoon) with odds from climatology data. Test the three coded Red attacks (blockade, jamming, false contacts). Decide whether to keep the movement budget"],
  ["Nov 17", "Learning", "Red agents that learn from experience. Do they exploit predictable Blue play? An attacker that moves after seeing Blue"],
  ["Dec 1", "Redesign", "Designs and combinations under attacks, persistent weather and a rare long typhoon. A cost for de-escalation measures"],
  ["Dec 8", "Report", "Final report and presentation"],
];
n++; s.addShape(pres.shapes.LINE, { objectName: "tl", x: 1.0, y: 2.1, w: 11.3, h: 0, line: { color: C.accent6, width: 3 } });
plan.forEach((p, i) => {
  const x = 0.6 + i * 3.05;
  n++; s.addShape(pres.shapes.OVAL, { objectName: "tp" + n, x: x + 0.2, y: 1.85, w: 0.5, h: 0.5, fill: { color: i === 3 ? C.accent2 : C.accent1 } });
  T(s, p[0], { x, y: 1.35, w: 2.8, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  T(s, p[1], { x, y: 2.55, w: 2.8, h: 0.45, fontSize: 18, bold: true, color: C.text2 });
  T(s, p[2], { x, y: 3.05, w: 2.8, h: 2.8, fontSize: 15, valign: "top" });
});
takeaway(s, "Next come learning, attacks and defenses, and resilient design, in that order.");
s.addNotes("(~45 s) Workshop 2 plan. First, Bayesian beliefs, weather scenarios tied to the calendar with odds from climatology data, and the three Red attacks already coded. We also decide whether to keep the theater-wide movement budget, which stands in for operational requirements and station-keeping. Then learning agents. Does a learning Red exploit predictable Blue play? Then redesigns under attack and long typhoons, with a cost for de-escalation measures. Final report December 8. Thank you. We are happy to take questions.");

(async () => {
  const out = __dirname + "/../deliverables/02-workshop1-slides.pptx";
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();
