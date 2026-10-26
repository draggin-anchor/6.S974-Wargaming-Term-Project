# Workshop 2 ideas

Working list of ideas for Workshop 2, each fleshed out enough to decide whether to build it.
Nothing here is in the report or the code yet. Version 6, Mon Oct 26, 2026 (7:55 PM ET).

Each idea has the same four parts: **what it is**, **how it enters the game** (state, actions,
dynamics, payoff, MIP), **what it touches** (code and experiments), and **open questions** for Sean.
All numbers are proposals. Learning methods stay "once taught".

## Summary

| # | Idea | From | Size | Suggested milestone |
|---|---|---|---|---|
| 1 | Oilers that follow each side's densest regions | Sean, Oct 26 | Medium | Nov 3 |
| 2 | Reformulate the movement budget $F_i$ with oilers | Report review, Oct 26 | Small (decided with 1) | Nov 3 |
| 3 | LCS as a second Blue ship type | Report review, Oct 23 | Medium | Nov 3 |
| 4 | FONOP as its own Blue posture {P, A, F} | Sean, Oct 23 | Medium | Nov 17 |
| 5 | Separate CCG/militia ports | Report review, Oct 26 | Small | Nov 3 |
| 6 | Weather tied to the real calendar | Report review, Oct 26 | Medium | Nov 17 |
| 7 | ±50% sensitivity sweep on assumed parameters | §6 plan | Small (compute heavy) | Dec 1 |
| 8 | How many simulated games are enough | Report review, Oct 26 | Small | Nov 3 |
| 9 | A cost for D3 de-escalation measures, and splitting D3 | §4.5 results | Small | Dec 1 |
| 10 | Rest of the external-uncertainty plan | Prof. Sapsis, Oct 21 | Medium | Nov 17 |
| 11 | Finer options under patrol and assert, each with its own weights | Sean, Oct 26 | Large | After Workshop 2 (final report) |
| 12 | Information that loses weight as it ages | Sean, Oct 26 | Small | Nov 3 (with beliefs) |
| 13 | Whole ships only in the template game (no fractional hulls) | Sean, Oct 26 | Small, but changes §4.1–4.2 | Nov 3 |

Items 1, 3 and 5 all change the map or the fleets, so every experiment has to be rerun after them.
Doing them together, before Nov 3, means one rerun instead of three.

---

## 1. Oilers that follow each side's densest regions

**What it is (Sean's idea):** each side has a fixed number of oilers in theater (say 2). They are
not commanded ship by ship. Each period every oiler moves toward one of its side's densest regions,
so with two oilers they sit in the two regions (of North, Center, South) where that side has the
most ships. A warship in a region with one of its own oilers can refuel without going home.

**Why it matters for the game:** today the only way to refuel is to sail home and spend a period in
port. Oilers give the side a second refuel point that follows the fleet, so the side's time on station
depends on where it concentrates. That couples logistics to the allocation decision, which is the
point of the model.

**How it enters the game:**

- *State:* add oiler positions $o^t_{i,j}\in\{\text{North},\text{Center},\text{South}\}$ for oiler
  $j=1,\dots,O_i$ of player $i$. Proposed $O_\B=2$; $O_\Rd=2$ or $0$ (open question below).
- *Dynamics (a fixed rule, not a decision):* at the end of period $t$, rank regions by the side's own
  ship count at sea, $n^t_{i,r}=\sum_{v\in r}\sum_k x^t_{k,v}$ (ties broken by region value
  $\sum_{v\in r}V^i_v$). The targets are the top $O_i$ regions. Each oiler sails one region per period
  toward its target (North and South are two steps apart, through Center), and oilers are matched to
  targets so total travel is smallest.
- *Refueling:* a ship that ends a period in a zone of a region holding one of its oilers, and does not
  move that period, regains $r$ periods of endurance, up to $D_k$. Each oiler can serve at most $Q$
  ships per period (proposed $r=3$, $Q=4$; ships nearest to forced return go first).
- *Endurance rule:* "can it get home" becomes "can it reach a refuel point". In the report's endurance
  rule and in the code, distance to home $\text{dist}(v,H_i)$ is replaced by distance to the nearest of
  $H_i$ or a region holding an own oiler. Forced return heads to that nearest refuel point.
- *Information:* oilers are large and easy to see, so detect them like warships ($q_{i,v}$). Because
  oilers follow density, seeing the opponent's oilers tells you which two regions it has massed in.
  That is an information leak the opponent can use, a small, concrete link to the beliefs work
  planned for Nov 3 (Lectures 7 and 8).
- *Payoff:* no new term at first. Optionally a running cost per oiler, like the redesign cost
  $\zeta_D$, if we want "buy a third oiler" to be a Blue redesign.
- *MIP:* oiler positions this period are known, so the MIP stays linear. Only the set of destinations
  a ship may choose changes (reachable refuel points). A later variant could make oiler placement a
  decision: binary $z_{j,r}$ with $\sum_r z_{j,r}=1$ per oiler, an assignment problem (Lecture 2)
  added to the same MIP. Sean's rule is the simpler first step and should come first.
- *Template game:* the 70% deployable share could become region dependent: higher in regions with an
  oiler. This makes the template game's payoffs depend on oiler placement.

**What it touches:**

- `wargame_gui.py`: `PARAMS` (`N_OILER`, `oiler_refuel`, `oiler_capacity`), `Game` state (oiler
  positions, update rule after moves), `reach_ok`, `_forced_move` and `Graph.home_dist` (nearest refuel
  point instead of home), the endurance update, `Obs` (oiler detections), GUI map (draw oilers), and
  `DEPLOYABLE_FRAC` in the template game if we make it region dependent.
- `experiments.py`: a new block, oilers 0 / 1 / 2 / 3 for Blue, with Red at 0 and at 2. Report control
  share, war rate, payoff and the share of ship-periods spent in contested zones.

**A check I ran (Workshop 1 code, nominal weather, 40 games per pair, rule-based and greedy
policies):** Blue ships already spend about 80% of their time in contested zones and Red about 75%,
because every home port is one edge from a zone and a DDG lasts 10 periods (20 days). So with today's
endurance values oilers can add at most about 20 points of time on station, and probably much less.
For oilers to matter, endurance $D_k$ should reflect fuel at patrol speeds rather than stores and crew.
Sean is the right person to set that number.

**Open questions for Sean:**

1. Does Red get oilers too, or is Red's short distance home its logistics advantage? (A claim either
   way about Chinese replenishment practice needs a source before it goes in the report.)
2. Full or partial refuel at an oiler? Is there a limit on ships served per period?
3. Region level (as above) or zone level? Zone level lets an oiler be shadowed or blockaded, which
   would give the Module 3 attacks a new target.
4. Does an oiler leave a region in a storm, or ride it out?
5. Realistic endurance values: how many two-day periods can a DDG (and later an LCS) stay on station
   without refueling?

## 2. Reformulate the movement budget $F_i$ with oilers

**What it is:** $F_i$ caps how many ship moves a side makes per period (8 Blue, 10 Red). In the report
(§3.3) it stands in for operational requirements and station-keeping; each ship's own fuel is its
endurance. The Workshop 2 plan (§6, Sean's wording) is to *reformulate the movement budget $F_i$ with
considerations for oilers*, so this idea is built together with idea 1.

**Data from the Workshop 1 code (same 40-game check as idea 1):** the budget rarely binds. Blue uses on
average about 4 of its 8 moves and hits the cap in 10% of periods (19% for greedy best response); Red
uses about 6 of 10 and hits the cap in 11 to 12% of periods. MIP-BR was not in this check (no Gurobi
license in this container), so it should be repeated for MIP-BR. If the new $F_i$ is meant to matter,
its base value has to be lower than today's.

**Proposed formulation: regional budgets that oilers raise.**

- Split the budget by region: $F^t_{i,r}=f_i+g\,o^t_{i,r}$, where $f_i$ is a small base allowance per
  region (routine station-keeping), $o^t_{i,r}$ is the number of player $i$'s oilers in region $r$ (idea 1)
  and $g$ is the extra moves one oiler supports. A move is charged to the region the ship sails from;
  moves out of home ports are charged to a separate port allowance.
- Constraint, replacing the single fuel line in §3.3 and in the MIP (§3.6):
  $$\textstyle\sum_{k}\sum_{u\in r}\sum_{v}f^t_{k,uv}\le F^t_{i,r}\quad\text{for each region } r.$$
  Still linear, so the MIP stays a MIP; only one constraint becomes three (four with ports).
- Effect: a region with an oiler is one where the side can reposition and hold station more freely.
  Since oilers go to the side's two densest regions, the third region is both thinly held and slow to
  reinforce, which is the trade-off the allocation decision should face.
- Endurance stays per ship. Oilers can refuel endurance as in idea 1, or act only through the budget;
  doing both is the fuller version, doing only the budget is the simpler first step.
- Proposed values to start: $f_\B=2$, $f_\Rd=3$, $g=2$, port allowance 2 per side. All assumptions, and
  all go into the sensitivity analysis (idea 7).

**Alternatives considered:**

| Option | What changes | For | Against |
|---|---|---|---|
| Regional budgets raised by oilers (proposed) | As above | Ties $F_i$ to logistics; stays linear | Three or four budget lines instead of one |
| One theater-wide budget raised by oilers | $F^t_i=F^0_i+g\cdot(\text{oilers in theater})$ | Smallest change | Oiler location does not matter, which loses Sean's density idea |
| Keep $F_i$ as is | Nothing | No rerun for this item | Rarely binds, so it does little |
| Drop $F_i$ | Endurance and oilers are the only limits | Simplest | Allows every ship to move at once |

**What it touches:** `PARAMS['F']` (becomes `f_base`, `g_oiler`, `f_port`), the budget loop in
`Game.step` (charge each move to its region), `Obs.fuel` (per region), the fuel constraint in
`MIPBRPolicy` (one per region) and the greedy and rule-based policies, Table 1, and §3.3 and §3.6.

**Open questions for Sean:** is a region the right unit, or should the budget follow the oiler's own
zone? Should moves out of port count against the oilers at all? Values for $f_i$ and $g$.

## 3. LCS as a second Blue ship type

**What it is:** littoral combat ships next to the DDGs. They were cut from §1 for Workshop 1 and a
`% TODO` in §3.1 marks where they go.

**How it enters the game:**

- *Ship types:* $\K_\B=\{\text{DDG},\text{LCS}\}$ with proposed $N_{\text{LCS}}=4$, endurance
  $D_{\text{LCS}}=5$ periods (shorter range), strength $w_{\text{LCS}}=0.6$, halved in rough seas like
  CCG hulls. All assumptions for Sean to set.
- *Hazard:* Blue's assert hazard becomes a mix, as Red's already is:
  $h^\B_{\As,v}=h_{\text{DDG}}\,\theta^\B_v+h_{\text{LCS}}\,(1-\theta^\B_v)$, where $\theta^\B_v$ is the
  DDG share of Blue's strength at $v$. Whether an LCS asserting is less escalatory than a DDG is a
  question for Sean.
- *MIP:* options become $b_{v,(n_{\text{DDG}},n_{\text{LCS}},p)}$. The number of options per zone grows
  roughly by a factor of $N_{\text{LCS}}+1$ before trimming. Cap counts per zone to keep the MIP fast.
- *Template game:* Blue's deployable hulls are split in proportion, as Red's PLAN and CCG already are.
- *Link to oilers:* short LCS endurance is exactly where oilers pay off, so ideas 1 and 3 should be
  tested together.

**What it touches:** `KINDS['B']`, `PARAMS` (`N_LCS`, `D_max`, `w`), `strength_parts` (rough-sea
penalty), `hazard_rate` (Blue mix), the starting split of Blue ships, the MIP option list, the template
game hull counts, GUI and snapshot labels; Table 1 rows and §3.1 text. Every experiment reruns.

**Open questions:** number, endurance and strength of the LCS; whether LCS may assert; any real-world
claim about where LCS operate needs a citation.

## 4. FONOP as its own Blue posture {P, A, F}

**What it is:** freedom-of-navigation operations become a separate Blue posture instead of one of the
things "assert" stands for. Assert keeps shadowing, close maneuvering, and querying and warning.

**How it enters the game:**

- *Actions:* Blue's posture $p_{\B,v}\in\{\Pt,\As,\text{F}\}$. Red keeps $\{\Pt,\As\}$.
- *Where:* only in zones where Red claims more than international law allows. Which zones count is
  Sean's call (candidates: SCB, STS, PAR).
- *Effect, proposed:* a FONOP does not add control the way asserting does; it challenges the claim. Two
  ways to model that: (a) while Blue is in F at $v$, Red's control there decays: control moves toward
  $\max\{\phi_v,0\}$ instead of $\phi_v$; or (b) a payoff term: Blue gains $V^\text{F}_v$ per FONOP and
  Red loses it, standing for the political value of contesting the claim. (a) keeps everything inside
  the control index and is easier to explain.
- *Hazard:* its own extra hazard $h^\B_\text{F}$, which Red's response sets: if Red asserts against a
  FONOP the hazard is higher than either alone.
- *MIP:* Blue's options become $b_{v,(n,p)}$ with $p\in\{\Pt,\As,\text{F}\}$, 1.5 times as many.
- *Template game:* Blue's templates grow from 14 to 21; the posture game in §4.1 becomes $3\times2$.
  We re-solve dominance, pure Nash, maximin and correlated equilibrium (all Lectures 3 and 4). The
  interesting question is whether F changes the chicken structure: if F is a safer way to contest than
  A, Blue's best reply to a Red assert might change.

**What it touches:** posture handling in `Game.step`, `node_eval`, `hazard_rate`, `TEMPLATES`, the
MIP option list, rule-based policy logic, GUI posture menu; §3.3, §3.4 and §4.1 in the report.

**Open questions:** which zones; does F require transiting inside 12 nm of a feature (so it needs a
specific zone, not a region); effect form (a) or (b); does a FONOP last one period (a transit) or can
it be held?

## 5. Separate CCG/militia ports

**What it is:** CCG and militia hulls now share Red's two home ports (Ningbo and Sanya, footnoted as
the Ningbo–Zhoushan and Hainan basing areas). Give them their own port nodes.

**How it enters the game:**

- *Map:* add one or two Red nodes that only CCG may use as home (for example a forward port closer to
  the South zones). Each needs a cited source for the location; Sean picks.
- *Effect:* a forward CCG port shortens CCG trips south, so CCG spend more time at SCB and STS. It is the
  Red counterpart to Blue's D1 dispersed basing and to the oilers.
- *MIP and dynamics:* no new math; home ports become type dependent, $H_{i,k}$, and endurance distance
  uses $H_{\Rd,\text{CCG}}$ for CCG.

**What it touches:** `NODES`, `EDGES`, `Graph.homes` and `home_dist` (by ship type), Red's starting
split, map figure in §3.1, GUI map.

**Open questions:** which ports; does the PLAN keep its ports unchanged; is this worth it if the oilers
already change the logistics story?

## 6. Weather tied to the real calendar

**What it is:** today's four weather scenarios are stylized (Sean does not want them called seasons).
This idea ties storm and rough-sea odds to the month, so a 60-period game (about four months) can
start in, say, August and run from typhoon season into the winter monsoon.

**How it enters the game:**

- *State:* the month $m(t)$, set by a start month $m_0$.
- *Dynamics:* storm odds $p_s(r,m)$ and rough-sea odds $p_r(r,m)$ per region and month, estimated from
  climatology: storm tracks from the JTWC or JMA best-track records, and wave heights from a reanalysis
  such as ERA5 (count a period as rough when wave height passes a threshold Sean sets).
- *Evaluation:* the scenario $\omega$ becomes the start month, with weight $\pi_\omega=1/12$ or weights for
  months the team cares about. Expected and worst case over $\omega$ stay exactly as in Lecture 1.

**What it touches:** `WEATHER` becomes a monthly table; the weather draw in `Game.step`; a small script
to turn the climatology data into that table; §3.2 text and Table 2.

**Open questions:** which regions get which data (the regions are large); whether the winter monsoon's
rough seas should hit CCG hulls even harder; data access (the sources are public but the processing is
real work).

## 7. ±50% sensitivity sweep on assumed parameters

**What it is:** every number in Tables 1 and 2 is an assumption. Change each one by −50% and +50%,
one at a time, and see whether the conclusions change.

**How it enters the game:** no model change. Parameters from §6: zone values $V$, hazards
($h_0$, $h^\B_\As$, $h^\Rd_\As$), war penalty $W$, and de-escalation chance $\mu$. Add any new ones from
ideas 1, 3 and 4 (oiler count, $w_{\text{LCS}}$, $h^\B_\text{F}$).

**What to report:** for each parameter, whether (1) the policy ranking from RQ2, (2) the equilibrium of
the risk-budget game from RQ1, and (3) the design ranking from RQ3 change. A tornado chart of Blue's
payoff for the main matchup. "The ranking holds within ±50% of every assumed value" is a strong
sentence if it is true.

**What it touches:** `experiments.py` (a sweep block using the existing `params=` override in
`run_batch`). Run it last, after the model is final, because it multiplies runtime by about
$2\times(\text{number of parameters})+1$.

**Open question:** one at a time is cheap but misses interactions; is a few two-parameter grids (for
example $W$ by $\mu$) worth it?

## 8. How many simulated games are enough

**What it is:** we used 200 games (seeds) per setup. Check that this is enough, and say so in the
report with a formula instead of a bare number.

**Method:** a setup's mean payoff has standard error $s/\sqrt n$ for sample standard deviation $s$ over
$n$ games. Workshop 1 standard errors were about 7 to 13 at $n=200$, so $s$ is about 100 to 180. To
tell apart two setups whose payoffs differ by $\Delta$ with about 95% confidence, the difference must
exceed about $2\times$ its standard error. Because every setup uses the same seeds (common random
numbers), compare *paired* differences per seed: the standard deviation of the difference is usually
much smaller than $s$, so fewer games are needed. Required $n\approx(2\,s_\Delta/\Delta)^2$.

**Example:** with $s=100$ and unpaired comparison, telling apart a 20-point difference needs
$n\approx(2\cdot100\sqrt2/20)^2\approx200$. For war rates (a yes/no per game) the standard error is
$\sqrt{p(1-p)/n}$: about 0.03 at $p=0.2$, $n=200$.

**What it touches:** `summarize` in `wargame_gui.py` (add paired differences against a baseline),
one table in `experiments.py`, one sentence in §4.

**Open question:** none; this is a quick, mechanical item.

## 9. A cost for D3 de-escalation measures, and splitting D3

**What it is:** D3 was renamed from "crisis hotline" to **de-escalation measures** (Sean, Oct 26; the
code and GUI still say "Crisis hotline" and need the new label). D3 currently costs nothing ($\zeta_{\text{D3}}=0$), so part of its win is by assumption
(§4.5 says Workshop 2 will price it).

**A first number from Workshop 1 results:** D3 beats D0 by 24 in expected payoff and by 24 in the worst
case. A running cost $\zeta$ for 60 periods discounted at 0.98 adds up to about $35\,\zeta$ (if the game
lasts the full 60 periods). So D3 stays best for Blue up to about $\zeta_{\text{D3}}\approx0.7$ per period,
more than D1 (0.3) and D2 (0.5). Reporting this break-even value is more useful than picking one cost.

**A richer version (strategic form, Lecture 3):** de-escalation measures need both sides. Make adoption a $2\times2$
game: each side chooses join or not, the measures exist only if both join, and each side pays its own
cost. Workshop 1 results say D3 raises Red's payoff too (101 to 144), so if costs are small both
joining is an equilibrium; the question is how high costs can go before one side stays out.

**What it touches:** `PARAMS['design_cost']`, a sweep over $\zeta_{\text{D3}}$ in `experiments.py`;
§3.8 and §4.5 text.

**Open question:** should the cost be political (a payoff cost) or operational (for example, the
measures only work with some probability)?

**Splitting D3 into its two effects:** D3 bundles two mechanisms: (1) faster de-escalation, where a quiet
period at $\ell\ge3$ lowers $\ell$ with probability 0.5 instead of 0.25, and (2) halved assert hazards.
Today we cannot tell which one produces D3's fourfold drop in war rate. Run them as two designs, D3a
(faster de-escalation only) and D3b (halved hazards only), next to the full D3. This is cheap (two more
rows in the design table) and tells the team which measure to describe and price. It also makes the
join-or-not game above more interesting, since the two parts may help Blue and Red by different amounts.

## 10. The rest of the external-uncertainty plan

The full plan is in `deliverable2/claude/Plan_External_Uncertainty.md`. Workshop 1 already did the core
of it: weather as random scenarios, scored by expected and worst-case payoff. What is left:

- *Persistence:* weather as a Markov chain per region, so bad spells last.
- *Forecasts:* each side sees a noisy forecast one or two periods ahead, and weather-aware policies use it
  (for example, do not sail into a storm; stage ships before calm returns).
- *More channels:* rough seas raise endurance use and the cost of moving, not just CCG strength and
  detection.
- *Weather windows:* does a side gain by surging right after a storm, while the other side's ships are
  refueling? With oilers (idea 1), the answer depends on where oilers were.
- *Results:* the effectiveness-versus-robustness plot (nominal payoff against worst-case payoff, one dot
  per policy and per design).

Class scope: expected and worst case are Lecture 1. The plan's tail-risk measure (CVaR), regret across
scenarios and learning to exploit weather are not yet covered and stay out unless taught.

---

## 11. Finer options under patrol and assert, each with its own weights

**What it is (Sean, Oct 26):** split the two postures into the specific actions they stand for, each
with its own weights. Sean filed this for "Workshop 3"; the course has no Workshop 3, so it is listed
here as a later-stage idea for the final report (Dec 8) unless he says otherwise. FONOP as its own
action (idea 4) is one piece of this, so idea 4 could be built as the first step of idea 11.

**Candidate options (from §1 of the report; Sean to confirm and extend):**

| Posture | Option | Who | Strength multiplier | Extra hazard | Other effect |
|---|---|---|---|---|---|
| Patrol | Routine presence | Both | 1.0 | 0 | none |
| Patrol | (other patrol variants: Sean to name) | | | | e.g. surveillance raises detection $q$ |
| Assert | Shadowing | Both | $\alpha_\text{sh}$ | $h_\text{sh}$ | raises own detection of the shadowed ships |
| Assert | Close maneuvering | Both | $\alpha_\text{cm}$ | $h_\text{cm}$ (highest) | |
| Assert | Querying and warning | Both | $\alpha_\text{qw}$ | $h_\text{qw}$ | Sean: escalatory, not weak |
| Assert | FONOP | Blue | see idea 4 | $h_\text{F}$ | challenges Red's claim (idea 4) |

All multipliers, hazards and costs would be our assumptions, set so the options are ordered the way
Sean ranks them by escalation, and checked in the sensitivity sweep (idea 7).

**How it enters the game:**

- *Actions:* posture $p_{i,v}\in\mathcal P_i$, a list of options instead of $\{\Pt,\As\}$. Each option $a$
  has a strength multiplier $\alpha_a$, an extra hazard $h_a$ (by ship type for Red, as now), and
  optionally a cost $\gamma_a$ in the stage payoff and an effect on detection.
- *Dynamics:* local strength becomes $S_{i,v}=\alpha_{p_{i,v}}\sum_k w_kx_{k,v}$ and the hazard sums the
  two sides' $h_{p_{i,v}}$. Nothing else in §3.4 changes. The hazard could also depend on the pair of
  options (for example close maneuvering against shadowing is worse than either alone): a small table
  $h_{a,a'}$.
- *MIP:* the option variables $b_{v,(n,p)}$ already range over postures, so the program stays the same
  size per option; with 4 to 5 options instead of 2 the number of variables per zone roughly doubles or
  more.
- *Template game:* with one option for all zones, Blue's templates grow from 14 to 7 times the number
  of options; the posture game of §4.1 grows from $2\times2$ to, say, $5\times4$. Dominance (IESDS), pure
  and mixed Nash, maximin and correlated equilibrium all still apply (Lectures 3 and 4). A useful
  question: which options survive dominance? If most do not, the extra detail does not change the
  strategic answer, and that is itself a result.

**What it touches:** the posture logic in `Game.step`, `strength_parts`, `hazard_rate`, `node_eval`,
`TEMPLATES`, the MIP option list, the rule-based policy, GUI posture menus, Table 1 (one row per option)
and §3.3 to §3.4 of the report. Every experiment reruns.

**Open questions for Sean:** the list of patrol options; the escalation order of the assert options;
whether options differ by ship type (for example CCG doing close maneuvering versus PLAN); whether to
add pair-dependent hazards or keep each side's hazard additive.

## 12. Information that loses weight as it ages

**What it is (Sean, Oct 26):** a decay on information that grows with the number of periods since it
was received. A sighting from this period is trusted fully; a sighting from five periods ago is trusted
much less, because the ships have had time to leave.

**Where the code is today:** each player's belief about each node already carries an age (0 when the
opponent was detected there this period, plus 1 for every period without a detection; `Game._observe`).
But no policy uses the age. `Obs.opp_counts` and `Obs.opp_posture` return the last-seen count and
posture however old they are, so a 5-period-old sighting counts as much as a fresh one. The age is only
shown in the GUI.

**How it enters the game:**

- *Confidence weight:* for a sighting of age $a$ at node $v$, the weight is $\psi^{a}$, with a decay
  constant $\psi\in(0,1]$. $\psi=1$ is today's model. The decay grows with age, as Sean asked: at
  $\psi=0.6$ the weight is 1 now, 0.6 after one period, 0.36 after two, under 0.1 after five.
- *Belief:* the believed opponent count blends the last sighting with a fallback guess $\bar x_{-i,v}$:
  $$\hat x_{-i,v}=\psi^{a}\,x^{\text{last}}_{-i,v}+(1-\psi^{a})\,\bar x_{-i,v}.$$
  Candidate fallbacks, simplest first: (a) the opponent's ships not seen anywhere this period, spread
  evenly over the zones; (b) the average count seen at $v$ over the game so far (plain averaging, not a
  learning method); (c) a spread over the nodes those ships could have reached in $a$ periods, using
  graph distance on $G$ (Lecture 2). Option (c) is the most physical: uncertainty grows because ships
  move one edge per period.
- *Postures:* the same weight on the last-seen posture. The chance the opponent asserts at $v$ becomes
  $\psi^{a}\,\mathbf{1}[\text{last seen A}]+(1-\psi^{a})\,\bar p_\As$, where $\bar p_\As$ is a default (0, which is
  today's "assume patrol", or the opponent's share of assertions seen so far).
- *Where $\psi$ comes from:* if each opponent ship leaves its node with probability $m$ per period, the
  chance it is still there after $a$ periods is $(1-m)^{a}$, so $\psi=1-m$. In the Workshop 1 runs (same
  40-game check as idea 1), Blue moves about 4 of 10 ships per period and Red about 6 of 14, so $m\approx0.4$
  and $\psi\approx0.6$. That gives a defensible default instead of a free parameter.
- *MIP:* nothing structural changes. The option values $a_v(n,p)$ and risks $\rho_v(n,p)$ are computed in
  advance from the believed opponent count and posture, so they are computed from the blended belief
  instead. A slightly better version takes the expectation over the two cases (opponent as last seen
  with probability $\psi^{a}$, fallback otherwise) for $\phi_v$ and $\rho_v$, which is still computed in
  advance, so the program stays linear. A cautious variant uses the larger of the two opponent counts in
  the risk constraint (a worst case over the two cases, Lecture 1).
- *Template game:* unchanged; it assumes both sides know the templates.

**Link to other ideas and results:**

- *D2 redundant sensing:* D2 showed no benefit in Workshop 1. One likely reason is that stale
  information is never penalized, so seeing more often adds little. With decay, fresher sightings carry
  more weight, so D2 should help if information matters at all. This is a direct test: rerun D0 and D2
  at $\psi=1$ and $\psi=0.6$.
- *Attacks (Module 3):* jamming makes sightings age faster; with decay, that now costs Blue something.
  False contacts from the deception attack fade on their own after a few periods.
- *Oilers (idea 1):* an old oiler sighting also decays, which limits how much it gives away.
- *Bayesian beliefs (§6 plan, Lectures 7 and 8):* this is the simple first step. A Bayes update would
  replace the fixed weight $\psi^{a}$ with a posterior over where each ship could be. Building the decay
  first gives a baseline the Bayes version has to beat.

**What it touches:** `PARAMS` (new `psi`), `Obs.opp_counts` and `Obs.opp_posture` (apply the weight
and fallback; every policy reads beliefs through these, so the change is in one place), GUI belief
panel (show confidence instead of age), `experiments.py` (a block: $\psi\in\{1,0.8,0.6,0.4\}$ times D0/D2,
with and without jamming); one paragraph and one Table 1 row in §3.2.

**Scope:** uses only ideas from Lectures 1, 2 and 7 to 8 (expectation over cases, worst case, graph
distance, beliefs). No learning method is involved.

**Open questions for Sean:** one $\psi$ for both sides or different (for example Red with shore-based
sensors near its coast keeps track longer)? Different by ship type (CCG and militia hulls harder to
track than navy ships)? Which fallback guess, (a), (b) or (c)? Should the symbol be $\psi$ ($\kappa$ and
$\lambda$ are already taken)?

## 13. Whole ships only in the template game (no fractional hulls)

**What it is (Sean, Oct 26):** the template game (§3.7) splits 70% of each fleet across North, Center
and South by percentage and spreads each region's share evenly over its zones, so zones get fractional
hulls (for example, Blue's 20% North share is 1.4 DDGs, or 0.7 per zone). Sean wants this removed. The
simulations themselves already use whole ships; only the template game, and the equilibrium and maximin
policies built on it, use fractions.

**Ways to do it:**

| Option | How | Strategies per side | Comment |
|---|---|---|---|
| A. Round the current templates | Deployable fleet in whole ships (Blue 7 DDG; Red 6 PLAN, 4 CCG). Split by the template percentages with largest-remainder rounding, then place each region's hulls on its most valuable zones first | 14 (unchanged) | Smallest change; keeps the template labels; rounding and tie rules are assumptions |
| B. Integer templates per region | A template is any whole-number split of the deployable hulls over the three regions, plus a posture | Blue $2\times36=72$; Red about $2\times28\times15=840$ (PLAN and CCG split separately) | No arbitrary percentages; dominance should cut it down fast; LPs of this size are easy for Gurobi |
| C. Integer per zone | Any whole-number placement of hulls on the eight zones | Thousands | Too large to be useful |

**Recommendation:** A now, because it is a small change and keeps the report's structure; B as a
check that the answer does not depend on the seven chosen splits.

**A check I ran (option A, same payoffs as §3.7, only the hull counts changed):** removing fractional
hulls changes the analytical results.

- Today (fractional): IESDS leaves $2\times4$ and there are two pure equilibria, (Blue center-heavy
  assert, Red south-heavy patrol) and (Blue center-heavy patrol, Red center/south assert).
- Whole ships (Blue 7 DDG; Red 6 PLAN, 4 CCG): IESDS solves the game to a single cell, and there is
  **one** pure equilibrium: **Blue center-heavy patrol, Red south-heavy assert**, payoffs
  $(-6.75,\ 4.01)$. The same answer holds with 5 instead of 6 PLAN and with 8 DDG, 6 PLAN, 5 CCG. With
  the full fleets (10, 8, 6) the equilibrium becomes (Blue 40/40/20 patrol, Red 20/40/40 patrol).

So the fractional hulls are not a cosmetic detail: they decide which side asserts in equilibrium. This
was a quick check (rounding and placement rules as in option A, no MIP or LP rerun), and it should be
redone carefully before anything goes in the report.

**What it changes in the report:** §3.7 (template definition and the "fractional hulls are allowed"
sentence); §4.1 (the $2\times2$ patrol-or-assert example is built from the two surviving splits, so its
numbers and possibly its chicken structure change); §4.2 (IESDS, pure equilibria, maximin LP); and the
RQ2 and RQ3 rows for the equilibrium and maximin policies, since those policies play the template
equilibrium.

**What it touches:** `MetaGame._payoff` and `DEPLOYABLE_FRAC` in `wargame_gui.py` (whole-ship counts,
rounding rule); `TemplatePolicy` (it already steers whole ships, so little or no change);
`experiments.py` (rerun the template-game outputs and the equilibrium and maximin rows);
`results/template_game.md` and `chicken.md`.

**Open questions for Sean:** how many hulls are deployable (7 of 10 DDG; 6 of 8 PLAN, 4 of 6 CCG)?
Within a region, should leftover hulls go to the most valuable zone first, as above, or does the
template choose? Option A or B?

## Already in the §6 plan, not expanded here

Bayesian beliefs instead of last-seen counts (Lectures 7 and 8); a multi-period best response; learning
agents (once taught); the three coded Red attacks and a Red attacker that moves after seeing Blue's
posture; designs D0 to D3 under attack and a rare long typhoon.
