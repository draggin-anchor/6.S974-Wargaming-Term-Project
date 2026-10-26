# Workshop 1 presenter notes and Q&A

**Talk:** Tue 2026-10-27. 10 minutes + 2 minutes of questions. 12 slides.
**Synced to:** the paper and the deck as of Mon 2026-10-26, 5:12 PM ET (all changes Sean accepted today: LCS removed, new §1 and RQ wording, stylized weather scenarios, movement budget, ship index j, §3.6 wording).

Part 1 is the game formulation in plain words, so any of the three of you can answer questions on it. Part 2 is the slide-by-slide script with timings. Part 3 is the likely Q&A. Part 4 is the sources for any claim about real U.S. or Chinese behavior.

---

## Part 1. The game formulation, explained

### One-sentence version
Two navies station ships on a network of contested waters every two days and choose to patrol or assert; control of each zone follows the local force ratio, incidents happen only where both sides meet, incidents push an escalation ladder toward war, and war costs both sides.

### The pieces, in the order of the paper (§3)

| Piece | What it is | Values (all our assumptions) |
|---|---|---|
| **Players** | Blue = U.S. Navy. Red = China: navy (PLAN) ships plus coast guard / maritime militia hulls, grouped as CCG. | 10 DDG; 8 PLAN + 6 CCG |
| **Map** | Undirected graph G = (V, E). 8 contested zones: Senkakus, Miyako Strait, Taiwan Strait, east of Taiwan, Luzon Strait, Scarborough Shoal, Second Thomas Shoal, Paracels. Home ports: Blue Yokosuka, Guam; Red Ningbo, Sanya. An edge = one period of sailing. Three weather regions: North, Center, South. | Each zone has a value V for each side; Red values Scarborough and the Paracels more. |
| **Time** | Periods of 2 days, T = 60 (about 4 months). All ships start in port with full endurance: DDGs 5/5 at Yokosuka/Guam, each Red type split evenly between Ningbo and Sanya. Discount δ per period. | δ = 0.98 (0.98⁶⁰ ≈ 0.30) |
| **State** | Ships at each node; each ship's endurance (periods left at sea); control index c of each zone in [−1, 1] (+1 Blue fully in charge, −1 Red); escalation level ℓ from 0 (calm) to L = 5 (war); sea state per region. | Start at ℓ = 1; start control in Table 2 |
| **Information (fog)** | Each side sees its own ships, control, ℓ and weather. Neither side sees the other's entire fleet disposition; only forces present where they also maintain forces. Formally: detect enemy ships at a node with probability 0.95 if you have a ship there, 0.6 next door or near your port, 0.2 elsewhere (satellite), ×0.7 in rough seas. Belief = last count seen. | Bayesian beliefs are the Workshop 2 upgrade |
| **Actions** | Simultaneous. Each ship: stay or sail one edge. Each zone where you have ships: posture **Patrol (P)** = routine presence, or **Assert (A)** = shadowing, close maneuvering, querying and warning, and (U.S. only) freedom-of-navigation operations, modeled as one posture. | Assert multiplies your strength by α = 1.5 |
| **Constraints** | Flow conservation (ships are moved, no new ships added to play). Movement budget: at most F ship moves per period across the theater. Endurance: a ship that could no longer get home is forced home and refits a full period. No entering the other side's ports or a storm-closed zone. Illegal orders: ship stays put. | F = 8 Blue, 10 Red; endurance 10 DDG, 8 PLAN, 6 CCG |
| **Control dynamics** | Strength S = (1.5 if asserting) × weighted hull count. Local balance φ = (S_B − S_R)/(S_B + S_R + κ). Control moves 30% of the way toward φ each period: c ← 0.7c + 0.3φ. Frozen in storms. | DDG, PLAN = 1; CCG = 0.6 (0.3 in rough seas); κ = 1 |
| **Incidents** | An incident is a collision, an unsafe interaction, or negative media coverage. It can happen only where both sides have ships. Hazard h = (baseline + assert terms) × min(S_B, S_R) × (1 + ℓ/2); probability ρ = 1 − e^(−h). Each incident raises ℓ by 1; a quiet period lowers ℓ by 1 with probability μ = 0.25; ℓ = 5 is war and ends the game. | h₀ = 0.006; Blue assert +0.03; Red assert θ·0.036 + (1−θ)·0.012, θ = PLAN share of Red strength in the zone |
| **Stage payoff** | g = (value of control) − 0.1 × (moves) − 1 × ℓ − ζ_D (Blue's redesign cost). Blue's control term is V^B·c summed over zones: positive where Blue holds a zone, negative where Red does. Red's is −V^R·c, the mirror image. It is linear, with no cutoff at zero. The tension term 1 × ℓ stands for the diplomatic and economic strain incurred. | ζ_D: D1 0.3, D2 0.5, D3 0 |
| **Total payoff** | Discounted sum of stage payoffs, minus W = 200 for **both** sides if war. So it is general-sum, not zero-sum: both want to avoid war. | Blue's max per period is 42, so war ≈ 5 perfect periods |
| **Weather** | Four scenarios ω: calm, nominal, typhoon, extreme, weights 0.25/0.40/0.25/0.10. Storms (3 periods) close a region's zones, stop incidents, freeze control. Rough seas halve CCG strength and cut detection. Robustness = expected payoff over ω and worst case over ω. | Storm/rough chance per period in Table 2 |

### Worked example (good to have ready if asked "show me the numbers")
One Blue DDG meets one Red CCG hull, calm seas, ℓ = 1, control starts at 0.
- **Blue patrols:** S_B = 1, S_R = 0.6. φ = 0.4/2.6 = 0.15, so control moves to +0.05. Hazard = 0.006 × 0.6 × 1.5 = 0.0054, so incident chance ≈ 0.5%.
- **Blue asserts:** S_B = 1.5. φ = 0.9/3.1 = 0.29, so control moves to +0.09. Hazard = 0.036 × 0.6 × 1.5 = 0.032, so incident chance ≈ 3.2%.
- **Message:** asserting roughly doubles the control you gain and multiplies incident risk about six times. That trade is the whole game.

### What we measure, and what "200 simulated games per setup" means
**Outcomes.** We report these for every setup we test (a policy pair, a risk budget, a redesign, or a weather scenario):
1. **Blue's control share.** Each period, take every zone's control index (+1 Blue, −1 Red), weight it by the zone's value to Blue (Taiwan Strait 10 ... Paracels 2), and average over the game. +1 means Blue held everything all game, −1 means Red did, and 0 means an even split.
2. **War rate.** The share of games that reach escalation level 5.
3. **Payoffs u_B and u_R.** Each side's total score from §3.5: control gained, minus fuel, tension and redesign costs, minus 200 if the game ends in war.
4. **For RQ3 only:** the payoff averaged over the four weather scenarios, and the payoff in the worst scenario.

**200 simulated games per setup (the code calls them seeds).** Every game has luck in it: detections, incidents, storms, and the random moves of the random policy. A seed is the starting number for the computer's random draws. So one seed is one simulated 60-period game with one particular run of luck, and each setup is played as 200 simulated games with different luck. We report the averages. Every setup uses the same seeds, 0 to 199, and weather is drawn from its own random stream. So the policies we compare face identical luck, and differences come from the policies, not from chance.

### How a player decides: the best-response MIP (§3.6)
- Each period, a player picks ship destinations and postures to maximize **value of control − incident cost − fuel**, given where it believes the enemy is. It is a best response written as a mixed-integer program, solved exactly with Gurobi.
- **Why the option variables b?** A MIP needs a linear objective and linear constraints. But the balance φ = (S_B − S_R)/(S_B + S_R + κ) is a ratio of ship counts, and the incident probability ρ = 1 − e^(−h) is an exponential, so neither is linear in the number of ships sent. Within one turn everything else is fixed (believed enemy ships, sea state, ℓ), and a zone holds only a few hulls. So for each zone we **list every possible (hull count n, posture p)** and compute its value a_v(n,p) and risk ρ_v(n,p) in advance as plain numbers. A binary b_{v,(n,p)} picks exactly one row per zone, so total value Σ a·b and total risk Σ ρ·b are linear. The "option matches the moves" constraint forces the chosen row's n to equal the ships the y variables actually send there. The cost is that the list grows with fleet size and ship types; that is fine for a few hulls per zone.
- **Example option list.** Blue, Senkakus (V = 6), believes one Red CCG hull on patrol there, calm seas, ℓ = 1:

| Option (n, p) | Balance φ | Incident chance ρ | Value a = 6·β·φ − 20·ρ |
|---|---|---|---|
| 0 DDG | −0.38 | 0% | −2.15 |
| 1 DDG, patrol | 0.15 | 0.5% | 0.77 |
| 1 DDG, assert | 0.29 | 3.2% | 1.03 |
| 2 DDG, patrol | 0.39 | 0.5% | 2.12 |
| 2 DDG, assert | 0.52 | 3.2% | 2.35 |

  The MIP picks one row per zone. Asserting adds value here, but it uses 0.032 of the risk budget ε against 0.005 for patrolling. Across all zones, that budget is what decides where assertion is worth it.
- **Risk budget:** expected incidents this period ≤ ε × (1 − ℓ/L). This is the "feasible region" from the D1 feedback. The cap tightens to zero as ℓ approaches war. The proposal's commander types are now budgets: conservative 0.05, moderate 0.15, aggressive 0.40. **Slack ξ:** the budget row is really "expected incidents ≤ ε(1 − ℓ/L) + ξ", with ξ ≥ 0 and a penalty of 1000·ξ in the objective. A ship on forced return may have to pass through a zone the opponent occupies. That risk cannot be avoided, and near war it can exceed the shrinking cap. ξ lets the program exceed the cap by only that unavoidable amount, so it always has a solution (Q19a).
- **Value of an option:** a = V × β × (local balance) − Λ × (incident probability). β = λ/(1 − δ(1 − λ)) ≈ 0.96 converts one period of balance into its total discounted effect on control. Λ = 20 is the price of one expected incident.
- **Limitation to own:** it looks one period ahead.

**MIP pieces at a glance**
- **y_{j,w}** = 1 if free ship j goes to node w: stay, sail home, or sail to a neighbor it can still get home from. Ships on forced return are not decided, so they have no y. y appears in four places: each ship gets exactly one destination; the movement budget (moves ≤ F_i − forced moves); the fuel cost −γ·Σy over moves; and the linking constraint (ships y sends into v, plus forced arrivals, = the n of the chosen option).
- **n and p.** n is the player's own hull count in zone v by type: for Blue, the number of DDGs; for Red, (number of PLAN, number of CCG). p is the single posture in that zone, P or A. The rows run from the ships already committed to v (forced returns) up to that number plus every free ship that can reach v this turn, each with P and A. Zero ships has only a P row.
- **a_v(n,p) = V·β·σ·φ − Λ·ρ** is one option's score: control gain minus incident cost. The MIP adds up a over the chosen rows, subtracts move costs, and maximizes, subject to total ρ ≤ the risk budget. The scores decide what is attractive; the budget decides what is allowed.
- **One option per zone:** Σ over (n,p) of b_{v,(n,p)} = 1 for each contested zone, so each zone ends the turn in exactly one situation (one hull count, one posture). Without it the solver could pick no row, dodging that zone's risk or the negative score of leaving it empty, or several rows, collecting both "2 DDG patrol" and "2 DDG assert". Together with the linking constraint, the one chosen row matches where y actually sent the ships, so the value and risk the MIP adds up belong to the moves it really ordered.
- **The option matches the moves:** Σ over (n,p) of n_k·b_{v,(n,p)} = x̄_{k,v} + Σ over ships j of type k of y_{j,v}, for every zone v and type k. The left side is the chosen row's type-k hull count, since only one b is 1. The right side is the ships actually there: forced-return arrivals x̄ plus free ships ordered to v, including ships that stay. Example: if y puts 2 DDGs in the Senkakus, the solver must pick a row with n = 2, leaving only patrol vs. assert to choose, and cannot claim a 3-DDG row's score. Blue has one such equation per zone; Red has one per type (PLAN, CCG) per zone. It is the link between the orders (y) and the scored outcomes (b).
- **Where are the storm, endurance and port rules?** Mostly in which y variables exist, not in extra rows. y_{j,w} is created only for legal destinations: one edge per period (stay, home, or a neighbor); never into a storm-closed zone, and ships inside a storm stay put; never into the opponent's home ports; and never where the ship could not get home on its remaining endurance d_j, unless the move brings it closer to home. The MIP also requires the ship to have at least one period on station there. Ships on forced return or refitting have no y; their next node is fixed in x̄. The explicit rows are the movement budget (moves ≤ F_i − forced moves), and the fuel cost γ per move sits in the objective. Weather also enters the option scores: storm zones have φ = ρ = 0, and rough seas halve CCG strength, which changes φ and ρ.
- **β is not a linearization.** The option list handles the nonlinearity; β handles time (Q21).

### The template game (§3.7) and the six policies
- The full game is far too big to solve for equilibrium. So we shrink it: each side picks one of **14 templates** = 7 ways to split ships North/Center/South × patrol or assert everywhere. Payoff = settled control (c = φ) minus incident cost, calm seas, ℓ = 1. That is a 14 × 14 strategic-form game, solved with iterated elimination of strictly dominated strategies (IESDS), pure Nash enumeration, the maximin LP and the correlated-equilibrium LP.
- **Policies compared** (slide name, then the paper's name in brackets): Random moves; Rule of thumb (rule-based, the moderate commander); Quick best response (greedy, no solver); Best response (MIP); Nash equilibrium plan (equilibrium: plays a pure NE template; of the two pure NE it uses the one with the higher total payoff, our choice); Safety-first plan (maximin: the template mix that guarantees the best payoff whatever the opponent plays, redrawn every 3 periods). Same random draws and weather for every policy.

### Blue redesigns (§3.8)
- **D1 extra port:** a third Blue port at Subic Bay, linked to Scarborough, Luzon, Second Thomas. Cost 0.3/period. Structural change.
- **D2 extra surveillance:** Blue detects in every zone with probability ≥ 0.6, even in bad weather. Cost 0.5/period.
- **D3 de-escalation measures** (hotline plus CUES-style encounter rules): at ℓ ≥ 3, a quiet period lowers ℓ with probability 0.5 instead of 0.25, and assert hazards are halved. **No cost yet** and it helps Red as much as Blue.

### Simplifying assumptions (say these before someone else does)
Two unitary players (no allies as players); control is a force-ratio index; incidents are the only path to war; beliefs are last-seen counts; best responses look one period ahead; every number is an assumption.

### On the slides but no longer in the 5-page paper
The paper was cut to 5 pages on 10/26, with no numbers changed. If asked "where is that in the report?", these are now only on the slides or in these notes:
- **Theater map and GUI screenshot** (slides 2 and 7). The paper has no figures now.
- **RQ1 frontier** (slide 8, left): raising Blue's budget ε from 0.02 to 0.15 lifts Blue's control share from −0.25 to −0.05, while war rises from 7% to 20%; going to 0.40 adds only 0.06 more control.
- **RQ3 policy-by-weather chart** (slide 10, left).
- **Correlated equilibrium of the 2 × 2** (slide 6): 0.40 on (patrol, patrol), 0.54 on (Blue asserts, Red patrols), 0.06 on (Blue patrols, Red asserts), 0 on (assert, assert).
- **Common random numbers** (same seeds and weather for every policy), **maximin's definition**, and the **full β derivation**: see Q30c, the policies bullet above, and Q21.

**Paper section map now:** §4.1 small example plus template game; §4.2 RQ1 (Table 3, risk-budget game); §4.3 RQ2 (Table 4, policies); §4.4 RQ3 (Table 5, designs).

### Notation cheat sheet (full Table 1)
The paper now keeps only the parameter half of Table 1. Both halves are here. A printable copy is `02-workshop1-notation-table.pdf`, stored next to these notes.

**State, beliefs and choices** (removed from the paper)

| Symbol | Meaning |
|---|---|
| x^t_{k,v} | type-k ships at node v |
| d^t_j | periods ship j can still stay at sea |
| c^t_v | control of zone v: +1 Blue, −1 Red |
| ℓ^t | escalation level (war at L) |
| w^t_r | sea state of region r |
| x̂^t_{−i,v} | i's last-seen opponent count at v |
| p_{i,v} | posture: patrol (P) or assert (A) |
| f^t_{k,uv}; m^t_i | ships sailing u → v; moves made |
| S_{i,v}; φ_v | local strength; local balance |
| h_v; ρ_v | incident hazard; incident probability |
| g^t_i; u_i | stage payoff; total payoff |
| y_{j,w} | MIP: ship j goes to node w |
| b_{v,(n,p)} | MIP: n hulls with posture p at v |
| ω; π_ω | weather scenario; its weight |
| V^i_v; σ_i | value of v to i; +1 Blue, −1 Red |

**Parameters (our assumptions; still in the paper)**

| Symbol | Meaning | Value |
|---|---|---|
| T; δ | periods (2 days each); discount | 60; 0.98 |
| N_k | fleet size | 10 DDG; 8 PLAN, 6 CCG |
| D_k | endurance when refueled (periods) | 10 DDG; 8 PLAN; 6 CCG |
| F_i | ship moves per period | 8 Blue; 10 Red |
| w_k | strength per hull | 1 DDG, PLAN; 0.6 CCG (0.3 in rough seas) |
| α | strength multiplier when asserting | 1.5 |
| κ; λ | presence damping; control rate | 1; 0.3 |
| h₀ | baseline incident hazard | 0.006 |
| h^B_A; h^R_A | extra hazard if asserting | 0.03 Blue; 0.036 PLAN, 0.012 CCG |
| L; ℓ¹ | war level; starting level | 5; 1 |
| μ | chance a quiet period lowers ℓ | 0.25 (D3: 0.5 at ℓ ≥ 3) |
| γ; η | move cost; tension cost per level | 0.1; 1 |
| W | war penalty (both sides) | 200 |
| q_{i,v} | detection: here / nearby / far | 0.95 / 0.6 / 0.2, × 0.7 in rough seas |
| Λ; β | MIP: incident price; persistence factor | 20; 0.96 |
| ε_i | escalation-risk budget | 0.05 / 0.15 / 0.40 |
| ζ_D | Blue's redesign cost per period | D1 0.3; D2 0.5; D3 0 |

---

## Part 2. Slide-by-slide script

Current speaker notes add up to about 11.5 minutes. The timings below fit 10:00. The speaker split is only a suggestion.

| # | Slide | Time | Suggested speaker |
|---|---|---|---|
| 1 | Title | 0:20 | Sean |
| 2 | The problem: control without war | 1:00 | Sean |
| 3 | Research questions and changes | 0:50 | Sean |
| 4 | The game, one period at a time | 1:15 | Sean |
| 5 | How the players decide | 0:50 | Tate |
| 6 | Small example: when does it pay to assert? | 1:00 | Tate |
| 7 | The prototype | 0:45 | Tate |
| 8 | RQ1 | 0:55 | Matthew |
| 9 | RQ2 | 0:50 | Matthew |
| 10 | RQ3 | 1:00 | Matthew |
| 11 | What the evidence does and does not show | 0:35 | Matthew |
| 12 | Plan for Workshop 2 | 0:30 | Sean |

**1. Title (0:20).** We study day-to-day U.S.–China competition for control of the waters inside the First Island Chain, below the threshold of war, as a game on a network. Today: the model, the prototype, and first results on three questions.

**2. The problem (1:00).** China presses its claims with coast guard and militia hulls backed by navy ships; the U.S. keeps the seas open with destroyers on presence and freedom-of-navigation patrols (Helmus 2024; Green 2017). Point at the map: squares are home ports, circles are eight contested zones in three regions; dashed lines are the Philippine port from one of our redesigns. Three things make this a game, not one optimization: control is relative, so my best move depends on yours; escalation risk is shared, because incidents need both sides present and war costs both; and neither side sees the other's entire fleet disposition, only forces where it also has forces.

**3. Research questions (0:50).** RQ1: each side caps the incident risk it accepts per period; how much control does more risk buy, how much likelier is war, and what cap does each side pick when the other is picking too? RQ2: does planning with game theory beat simple rules, and can both sides stay at patrol because asserting once would end the truce and push both into riskier play from then on? RQ3, from Prof. Sapsis: does the best plan or redesign in normal weather stay best across calm, typhoon and extreme weather scenarios, both on average and in the worst scenario? The table maps each piece of feedback to a change; the main ones are a fully formal model, the commander types as one risk-budget number inside a MIP, and preliminary results from 77 setups of 200 simulated games each.

**4. One period (1:15).** Read the timeline top to bottom: one two-day turn. The weather is drawn first; each side sees its own ships and some enemy ships; low-endurance ships head home; both choose moves and postures at the same time; control, incidents, escalation update; payoffs. Right side: control moves 30% of the way toward the local force balance each turn, so presence builds control slowly. Incidents need both sides present and get likelier with assertion and with tension already high. Payoff is zones held minus fuel, tension, and Blue's redesign cost; war costs both 200, so it is not zero-sum. If you have 10 seconds spare, give the DDG vs. CCG example from Part 1.

**5. How the players decide (0:50).** Left: each turn a player solves a MIP with a cap ε on expected incidents. That answers the feedback that Q1 is a feasible region. Middle: to find equilibria we shrink each side to 14 templates and solve that 14 × 14 game exactly with dominance, Nash equilibrium and the two LPs. Right: the six policies; all see the same random draws.

**6. Small example (1:00).** Fix where ships go; each side only picks patrol or assert. Asserting against a patroller pays a little; if both assert, both lose more than 11. So the best reply is the opposite of the other side, which makes it an anti-coordination game: two pure equilibria and a mixed one with mutual assertion 8% of the time. Two fixes: the best correlated equilibrium never recommends both asserting, which a mediator or hotline can implement; and in the repeated game, grim trigger (both patrol; after any assertion, both play the mixed equilibrium forever) makes mutual patrol a subgame perfect equilibrium for any discount factor above 0.18. Ours is 0.98.

**7. Prototype (0:45, or a live demo of the same length).** Pick a plan for each side, a design and the weather; Step or Play. Zone color is control; letters count ships; thick outline = asserting; orange ring = incident; shading = bad weather; bottom left is the escalation ladder, 5 is war. "Run many games" plays the same setup as many simulated games and reports averages. One script reproduces every number in the report.

**8. RQ1 (0:55).** Left: Blue loosens its budget while Red stays moderate. Control rises fast up to about 0.15, then flattens, while war risk keeps rising (7% to 20% from ε = 0.02 to 0.15). Right: when both choose a budget, aggressive is the best reply to anything for both, so the only equilibrium is aggressive–aggressive with the highest war rate, 34%. A prisoner's dilemma. Restraint has to come from repetition or coordination, as on slide 6.

**9. RQ2 (0:50).** Each Blue policy plays three Red policies, 200 games each; the bar is Blue's payoff against its worst opponent. The Nash equilibrium plan has the best worst case, −116, and half the war rate of the MIP best response against the same Red (10% vs 20%). Best responses do well against weak opponents but escalate. Safety-first is cautious but gives up control. Gaps under about 20 points are noise.

**10. RQ3 (1:00).** Robustness means two things here: expected payoff over the four weather scenarios, and worst case. The ranking holds: the top two plans stay on top in every scenario. Bad weather slightly helps Blue because rough seas weaken Red's coast-guard hulls and storms pause incidents. Of the redesigns, de-escalation measures (D3) are best on average and in the worst case and cuts war from 20% to 5%. Caveat: no cost yet, and it helps Red too, so it is a joint gain.

**11. Evidence (0:35).** Left is what the runs support. Right is what they do not: values are assumptions, policies look one turn ahead, the war rate depends heavily on a few parameters, and the de-escalation result is partly built in. A sensitivity sweep is first for Workshop 2.

**12. Workshop 2 (0:30).** Nov 3 Bayesian beliefs, weather tied to the calendar (typhoon season, winter monsoon) with odds from climate records, the three coded Red attacks, and a decision on whether to keep the movement budget or drop it; Nov 17 learning agents; Dec 1 redesigns under attack and long typhoons, with a cost for de-escalation measures; Dec 8 final report. Thank you; happy to take questions.

---

## Part 3. Likely questions and answers

Answers are short on purpose: 15–30 seconds each. ★ = most likely.

### A. Model structure

**★ Q1. Why is this a game and not just an optimization for Blue?**
Because control is relative and risk is shared. My control depends on the ratio of my ships to yours, and an incident needs both of us in the zone. So my best allocation changes when yours does. The small example on slide 6 shows it: the best reply flips depending on what the other side does.

**★ Q2. What does "control" actually mean?**
A proxy for who can operate freely in a zone and enforce its view of the rules there. It is an index from −1 (Red fully in charge) to +1 (Blue). It moves 30% of the way toward the local force balance each period, so you earn it by staying and lose it by leaving. It is a modeling choice, not a measured quantity.

**Q3. Why a force ratio with κ = 1?**
The ratio makes control relative, which is the point. κ stops a token presence from counting as full control: one DDG alone gives balance 0.5, not 1.

**Q3a. Why these starting control values (Taiwan Strait 0, Senkakus +0.2, Miyako +0.3, east of Taiwan +0.2, Luzon +0.1, Scarborough −0.2, Second Thomas 0, Paracels −0.4)?**
They are judgment-call assumptions. Zones next to Japan and Okinawa lean Blue: Japan administers the Senkakus, and the Miyako Strait runs between Japanese islands, with U.S. forces on Okinawa. Features China holds or controls access to lean Red: China occupies the Paracels, and Scarborough leans Red too. The true flashpoints, Taiwan Strait and Second Thomas Shoal, start at 0. Blue is the U.S. Navy only, so allied presence (Japan, the Philippines) is folded into these starting values. They barely matter for the results: control moves 30% of the way to the local balance each period, so after 10 periods (20 days) only 0.7¹⁰ ≈ 3% of the starting value remains. They shape the first weeks, not the four-month results.

**Q3b. When a ship first arrives, does control jump to the balance?**
No. The same update applies every period, c ← 0.7c + 0.3φ, so control closes 30% of the gap each period. Example: one DDG alone on patrol in a zone at c = 0 gives φ = 1/(1 + 0 + 1) = 0.5, and control goes 0.15, 0.26, 0.33, and reaches 0.42 after 5 periods, heading toward 0.5. In closed form, c = φ + (c_start − φ)·0.7ⁿ: 83% of the way in 5 periods (10 days) and 97% in 10. A lone asserting DDG gives φ = 0.6; two DDGs on patrol give φ = 0.67.

**★ Q4. Why are moves simultaneous instead of leader–follower (Stackelberg)?**
Day-to-day gray-zone presence is both sides adjusting at once, each without full knowledge of the other. Leader–follower is in the Workshop 2 plan: an attacker that moves after seeing Blue's posture, solved by backward induction.

**Q5. What kind of game is this, formally?**
A finite-horizon dynamic game with chance moves (weather, incidents) and imperfect information: players decide at information sets that do not reveal the opponent's current positions. It is general-sum because both pay the war penalty.

**★ Q6. Where do the numbers come from?**
They are our assumptions; there is no public data for most of them, and the instructors said to propose reasonable values. Hazards and μ were set so war is uncommon but not rare, so the risk trade-off is measurable. Every value is in Table 1. A ±50% sweep on V, h, W, μ is the first Workshop 2 task.

**Q7. Why is war reached only through incidents? States can choose war.**
A stated simplification. We study the gray zone below the threshold; deliberate escalation is outside this model. Incidents driving escalation follows Schelling's idea of shared, manipulated risk.

**Q7a. What is a "quiet period"?**
One period (2 days) with no incident anywhere in the theater. After each quiet period, ℓ drops one level with probability μ = 0.25. So on average it takes 4 quiet periods (about 8 days) per level, and about 24 days without incidents to get from ℓ = 3 back to calm. Any incident raises ℓ immediately. With de-escalation measures (D3), μ = 0.5 at ℓ ≥ 3, so about 4 days per level up there. The design choice is that crises start fast and cool slowly. μ is our assumption.

**Q8. Why does a CCG hull count less than a navy ship, and less in rough seas?**
Coast guard and militia hulls are smaller and lightly armed, so 0.6 of a warship, and 0.3 in rough seas where small hulls lose effectiveness. That rough-sea effect is why bad weather helps Blue slightly.

**Q8a. Red has 14 hulls, so why is F_R = 10?**
F is a movement budget, not a fleet size: the most ship moves (one move = sailing one edge) a side can make per period across the theater. Each ship's own fuel is its endurance d_j. In the paper's words, the theater-wide movement budget "stands in for operational requirements and station-keeping" (our interpretation, not documented practice). Ships that stay put use none, and forced returns are charged first. So at most 10 of Red's 14 hulls and 8 of Blue's 10 DDGs can reposition in one period, and neither side can shift its whole fleet at once. The values are our assumptions. Workshop 2 will decide whether to keep it or drop it. The per-move cost γ in the payoff is still a fuel cost.

**Q9. Why is PLAN assertion more escalatory than CCG assertion?**
Using coast guard and militia is how China applies pressure while trying to avoid a military response (Helmus et al. 2024). So pressure from CCG hulls carries a lower hazard (0.012) than from navy ships (0.036).

**★ Q10. Why are querying and warning counted as assert, not patrol?**
A query or warning that challenges another ship's presence is a demand to comply: it presses a claim. Patrol is routine presence that presses no one. (Sean can speak to this from experience.)

**Q11. Why is assert one posture? FONOPs and shadowing are very different.**
Simplification for Workshop 1. Making FONOP its own Blue action is planned; that turns the 2 × 2 example into 3 × 2.

**Q12. Where are Japan, the Philippines, Taiwan?**
Not players: two unitary players is a stated simplification. The Philippines enters only as basing access in redesign D1.

**Q13. Why did the littoral combat ships disappear?**
We simplified Blue to destroyers for this submission; adding LCS as a second Blue type is Workshop 2 work.

**Q13a. Why Ningbo and Sanya as Red's ports? CCG and militia don't sail from there.**
They stand for basing areas, not single piers: NBO is the Ningbo–Zhoushan area and SAN is Hainan (Yulin). Coast guard and militia ports are folded into them, as the paper's footnote says. In reality Ningbo hosts the Eastern Theater Command Navy headquarters, with ships mostly berthed at Zhoushan. Yulin, near Sanya, is a major naval base with submarine facilities and is reported as the carrier Shandong's home port. The Southern Theater Navy headquarters is at Zhanjiang. Two ports per side keeps the graph small; adding more is easy if it matters for a question.

**Q13b. What exactly is the state s^t?**
A snapshot of the whole theater at the start of period t. Its parts are full lists: x^t gives the ship count of each type at every node, d^t the endurance left for every ship, c^t the control index of every zone, and w^t the sea state of every region. The escalation level ℓ^t is a single number for the whole theater.

### B. Information and weather

**★ Q14. How exactly do you model fog of war?**
Each period you detect enemy ships at a node with probability 0.95 if you are there, 0.6 next door, 0.2 elsewhere, and 30% less in rough seas. Your belief is the last count you saw. Neither side sees the other's entire fleet disposition; only forces present where they also maintain forces. Bayesian updating is the Workshop 2 upgrade.

**Q15. Why does extra surveillance (D2) show no benefit even when free?**
Because our policies barely use better information: the MIP looks one turn ahead and the template plans hardly react to where the enemy is. That is a finding about the policies, not proof that sensing has no value. Bayesian beliefs should change it.

**★ Q16. Bad weather helps Blue? Isn't that strange?**
In this model, rough seas halve CCG strength and storms pause incidents and freeze control. So calm seas favor Red's coast-guard numbers. An earlier version had storms erase control, which made this effect an artifact; we fixed that, and the effect is small.

**Q17. Why scenarios and not a full weather probability model?**
The weather scenario ω is a chance move with weights, and we score by expected value and by worst case. It answers Prof. Sapsis's question of robustness, not just effectiveness.

**★ Q17a. How does the weather work (Table 2)?**
Each game runs under one scenario ω. The weights π_ω (0.25 / 0.40 / 0.25 / 0.10) are used only to average results in RQ3; the worst case ignores them. Each period, each region (North, Center, South) not already in a storm gets one with probability p_s. A storm lasts 3 periods (6 days), closes the region's zones, stops incidents there and freezes control. Otherwise the sea is rough with probability p_r, which halves CCG strength and cuts detection to 70%; if neither happens, it is calm. Long-run share of time a region spends in storm / rough seas: calm 0% / 0%, nominal about 6% / 19%, typhoon about 15% / 30%, extreme about 26% / 37%. All values are our assumptions, chosen to span "no weather" to "very bad weather"; they are not climate data.

**Q17c. In a storm, is control frozen or just not scored?**
Both frozen and still scored. The control update is skipped, so the zone keeps its pre-storm value; there are no incidents; and the stage payoff still counts V·c every storm period. For example, Blue at c = 0.4 in the Senkakus keeps earning 6 × 0.4 per period. In the MIP, storm-zone options score φ = ρ = 0 because nothing a player does can change that zone this turn (no entry, ships inside stay), not because the zone goes unscored.

**Q17b. Are these real seasons?**
No. They are four stylized weather scenarios, not calendar seasons. In reality, typhoons in the western North Pacific peak around August–September (NOAA), and the winter northeast monsoon (about November–March) brings persistent rough seas in the Taiwan and Luzon Straits (Hong Kong Observatory). Workshop 2 will add scenarios tied to the calendar, with odds taken from climate records.

### C. Decision rules and solution concepts

**★ Q17d. Explain the six policies simply.**
One line: random is the baseline, rule-based is a sensible human, greedy and the MIP best response optimize move by move, and the equilibrium and maximin plans follow a game-theory plan for the whole campaign.
- *Random moves:* the baseline floor.
- *Rule of thumb (rule-based, moderate commander):* goes where value is high and the enemy is thin; asserts only where it thinks it outnumbers the enemy and ℓ ≤ 2; then pulls back until expected incidents fit ε = 0.15(1 − ℓ/L).
- *Quick best response (greedy):* a fast shortcut with no solver, using the same MIP objective and budget.
- *Best response (MIP):* solves the risk-budget best response exactly each period; a larger ε makes it bolder.
- *Nash equilibrium plan:* follows its part of the higher-total-payoff pure equilibrium of the 14-template game, steering ships toward that fleet split and posture.
- *Safety-first plan (maximin):* every 3 periods, draws a template from its maximin mixed strategy, which gives a guaranteed worst case and is unpredictable.

Both template plans patrol when ℓ > 3 and drop any assertion that breaks their risk budget.

**Q17e. Step by step, how does each policy pick its moves?**
The key contrast: greedy and the MIP plan one move ahead and re-decide every period, while the rule of thumb and the two template plans pick a destination and walk to it over several periods.
- *Random:* each free ship stays or moves to a random legal neighbor (50/50); posture is a coin flip per zone. It has no risk budget, and the engine drops moves over F.
- *Rule of thumb (moderate, ε = 0.15):* (1) repeatedly assigns the best ship–zone pair, scoring the control gain of one more hull, discounted for distance, minus fuel, divided by (1 + 0.5 × believed enemy strength), and stops when the best score is below 0.05; targets can be several hops away. (2) Assigned ships step one hop toward their targets, highest score first, up to F. An unassigned ship goes home if it is in a zone where the enemy was seen, and otherwise stays. (3) It asserts only if ℓ ≤ 2 and its own strength exceeds the believed enemy strength. (4) While risk exceeds ε(1 − ℓ/L), it flips the riskiest asserting zone to patrol, or if none is asserting, pulls one hull out of the riskiest zone.
- *Quick best response (greedy):* see Q21b.
- *Best response (MIP):* lists one-edge moves and each zone's options, then Gurobi maximizes value minus fuel subject to the movement budget, option consistency, and risk ≤ ε(1 − ℓ/L) + slack.
- *Nash equilibrium plan:* uses a fixed template, the higher-total-payoff pure equilibrium of the template game. Free ships are split by region per the template, then across zones in proportion to value, and the nearest reachable ship is matched to each slot. Ships step one hop toward their slots, nearest first, up to F. Occupied zones take the template's posture (patrol if ℓ > 3), and the riskiest assertions flip to patrol until risk fits ε(1 − ℓ/L).
- *Safety-first plan (maximin):* the same, but every 3 periods it draws a new template from its maximin mixed strategy.

**Q17f. How does each policy decide between patrol and assert?**
Asserting multiplies a side's strength by 1.5, which means more control, but it raises the incident hazard. Every policy except random computes risk assuming the opponent keeps its last-seen posture (patrol if never seen).
- *Random:* a coin flip, with no budget.
- *Rule of thumb:* asserts only if its own strength exceeds the believed enemy strength (both counted without the assert multiplier, so the enemy's posture is ignored here) and ℓ ≤ 2, then flips the riskiest assertions back to patrol until risk ≤ ε(1 − ℓ/L).
- *Greedy:* in each zone, scores patrol and assert with V·β·φ − Λ·ρ and takes the higher, allowing assert only if total risk stays ≤ ε(1 − ℓ/L).
- *MIP:* uses the same scoring, but posture is part of each zone's option list and is chosen jointly with the moves, so it can trade assertion between zones to fit the budget. Greedy and the MIP both account for enemy posture in the same way; they differ only in search.
- *Template plans (Nash, Safety-first):* use the template's single posture in every occupied zone (patrol everywhere if ℓ > 3), then flip the riskiest assertions to patrol until risk fits the budget.

**★ Q18. Is MIP-BR an equilibrium?**
No. It is a one-period best response to beliefs about where the enemy is. Equilibrium analysis is done on the 14 × 14 template game, and the "Nash equilibrium plan" plays that equilibrium in the full game.

**★ Q19. Why both a risk budget ε and an incident price Λ?**
Λ prices risk in the objective; ε is a hard limit, the commander's risk tolerance or rules of engagement. The budget is what the D1 feedback called a feasible region, and it makes the proposal's three commander types a single number we can vary for RQ1.

**Q19a. How could forced returns break the risk budget?**
A ship on forced return has a fixed next node: one step closer to home, or it stays put if no such node can be entered, for example because of a storm. If that node is a contested zone where the opponent is believed present, the incident risk is above zero even on patrol, and no other move can remove it. The cap ε(1 − ℓ/L) is tiny at high tension: a conservative 0.05 becomes 0.01 at ℓ = 4. So one such hull can exceed it, and without slack the MIP would have no solution. The slack carries a penalty of 1,000 per unit, so it covers only the unavoidable excess, and everything else is made as safe as possible. We do not log how often this happens, so don't claim it is rare.

**Q20. Why enumerate (count, posture) options instead of writing the formula in the MIP?**
Control and incident chance are a ratio and an exponential in ship counts, which a linear program cannot hold. Listing each zone's few possible options as binaries, with value and risk computed beforehand, keeps it linear and exact.

**Q20a. What does "the opponent postures it last saw (patrol if never seen)" mean?**
Each player keeps a memory, zone by zone, of the opponent's posture. When it detects the opponent in a zone, it records that posture (patrol or assert) and assumes it holds until its next detection there. If it has never detected the opponent in that zone, it assumes patrol. The MIP needs this because an asserting opponent counts 1.5 times as strong, which shifts the local balance φ, and raises the incident hazard.

**Q21. What is β?**
β = λ/(1 − δ(1 − λ)) ≈ 0.96 is the total discounted effect on control of one period of local balance. Control updates as c ← 0.7c + 0.3φ, so one period of balance φ moves c by 0.3φ now, and 70% of that shift survives each later period (0.21φ, then 0.147φ, ...). Payoff is V·c per period, discounted by δ = 0.98, so the total is 0.3φ·Σₙ (0.98·0.7)ⁿ = 0.3φ/(1 − 0.686) = 0.955φ. So one period of presence is worth about 0.96·V·φ in total, though only 0.3·V·φ shows up this period. **Why the MIP needs it:** the MIP looks one period ahead. Without β it would credit presence at only 0.3 while charging the full incident cost Λρ, so it would undervalue presence about threefold. **Caveats:** β counts only this period's push (later balances get their own β when they are decided), and it ignores the chance that war ends the game early, so it slightly overstates the value of control at high ℓ.

**Q21a. Why δ = 0.98? Isn't that arbitrary?**
It is our assumption, per two-day period. A payoff 60 periods (about four months) out is worth 0.98⁵⁹ ≈ 0.30 of today's, and the half-life is about 34 periods (about 70 days). It sits far above the 0.18 grim-trigger threshold, so the restraint result does not hinge on the exact value. It also sets β ≈ 0.96 in the MIP.

**Q21b. Does the greedy heuristic apply the constraints?**
Yes, with one gap. It keeps moves legal (one edge, no storm-closed zones or enemy ports, endurance), places forced returns first, and respects the movement budget. How it chooses: (1) start from "every free ship stays, all zones patrol"; (2) for each ship in random order, try every legal destination, reject any that exceeds the movement budget or that is both over ε and riskier, and take the biggest gain in score; (3) in each zone pick patrol or assert by score, allowing assert only if total risk stays ≤ ε; (4) repeat up to 3 more rounds until nothing changes. It is fast but can stop at a good plan rather than the best one. **The gap:** if the starting plan is already over the risk budget, greedy refuses anything that adds risk but never gives up value to get back under it. That is its 14% overrun rate (208 of 1,524 decisions; a rerun found every overrun started over budget and never got worse). The MIP will give up value to get under the budget, so its only overruns (37) come from forced returns that leave no choice.

**Q22. How do you know the MIP solutions are right?**
Gurobi solves it exactly. We compared it to the greedy heuristic over 1,524 Blue decisions: they agreed 67% of the time, but greedy broke the risk budget 14% of the time. That is why the exact MIP matters even though both play about the same.

**Q23. How does the template game relate to the full game?**
If both sides held a template, control would settle at c = φ. Template payoffs are that settled control minus incident cost, in calm seas at ℓ = 1. It is an approximation used to compute equilibria; the simulations then test those plans in the full game.

**Q22a. What is IESDS?**
Iterated elimination of strictly dominated strategies. Cross out any template that another template beats against every opponent choice, then repeat, since each removal can make new templates dominated. Every Nash equilibrium lies in what survives. In our template game it cuts 14 × 14 down to 2 × 4: Blue keeps only center-heavy (20/60/20, patrol or assert), and Red keeps south-heavy (20/20/60) and center/south (20/40/40), each with patrol or assert. That is why the slide 6 example fixes Blue center-heavy and Red south-heavy and varies only the posture.

**Q23a. The template game uses fractional hulls. Isn't that unrealistic?**
Yes. It is a known simplification: templates spread 70% of each fleet evenly over a region's zones, which can leave fractions of a ship in a zone. The full simulation always moves whole ships, but the template game sets which plan the Nash equilibrium and Safety-first policies play. A quick whole-ship check (rounding to Blue 7 DDG, Red 6 PLAN + 4 CCG; not in the paper) changes which side asserts in equilibrium: dominance leaves a single pure equilibrium, Blue center-heavy patrol vs. Red south-heavy assert, instead of the paper's two. So removing fractional hulls is first on our Workshop 2 list.

**Q24. The template game has two pure equilibria. Which do you play?**
The one with higher total payoff (Blue center-heavy assert vs Red south-heavy patrol). That selection is an assumption, stated in the paper.

**Q25. Why does the maximin plan do poorly?**
It guards against Red's worst-case template, which Red rarely plays, so it gives up control. It is the safest (war ≤ 8%) but scores lowest among the strategic plans.

### D. Results

**★ Q26. Slide 6 says restraint is an equilibrium, but RQ1 says both go aggressive. Which is it?**
Different games. Slide 6 is the repeated game: patient players using grim trigger can sustain mutual patrol (any δ above 0.18). The punishment after an assertion is both playing the mixed equilibrium forever, not both asserting forever. RQ1's budget game is a one-shot choice of budget by myopic policies, and there aggressive dominates: a prisoner's dilemma. The gap between the two is the case for coordination devices and for multi-period policies in Workshop 2.

**Q27. Why is slide 6 an anti-coordination game and not a prisoner's dilemma?**
With force splits fixed, asserting against a patroller pays, but asserting against an asserter is worse than backing off. Best reply = opposite of the other side, an anti-coordination structure. In the budget game a looser budget also changes deployment, and it pays against everything.

**★ Q28. A 34% war rate is not realistic.**
Agreed, it is not a forecast. We tuned hazards so war is uncommon but not rare in a four-month game, so differences between strategies show up. What we report is relative: which choices raise or lower war risk. We also flag that W = 200 may be too small, since the top-scoring policy has the most wars.

**Q29. Why are Blue's payoffs negative almost everywhere?**
Red has more hulls, starts with control in the South, and values the South more; and both pay tension costs every period plus the war penalty. Compare rows, not signs.

**★ Q30a. What do you measure, and what does "averaged over 200 simulated games per setup" mean?**
Four outcomes: Blue's control share (zone control weighted by value to Blue and averaged over the game; +1 all Blue, −1 all Red, 0 even), the war rate (share of games reaching level 5), each side's total payoff, and for RQ3 the average and worst payoff over the weather scenarios. A seed is the starting number for the random draws: detections, incidents, storms. Each setup is played as 200 simulated games with different luck, and we average them. Every setup uses the same seeds 0–199, so compared policies face identical luck.

**Q30c. Are the games pseudorandom and seeded? Can you reproduce them?**
Yes. Each game uses Python's `random.Random` (Mersenne Twister) seeded with the game number, 0 to 199, so every run is reproducible. Weather has its own random stream, seeded 10007 × seed + 17. So policies compared on the same seed face identical storms and sea states even when they move differently (common random numbers). Uncertainty is reported as the standard error s/√n. (Code: `prototype/wargame_gui.py`, `Game.__init__`.)

**Q30b. Why 200 simulated games?**
200 simulated games per setup was a practical choice for this stage. We haven't yet done a formal check of how many games are needed; that's on our Workshop 2 list.

**Q30. Are the differences significant?**
Standard errors of the averages are 5–12 payoff points. We treat gaps under about 20 points as ties and say so on the slides.

**★ Q31. Why does the Nash plan beat the MIP best response?**
Our reading (not yet tested separately): the MIP best response looks one turn ahead and reacts to last-seen beliefs, so it escalates more (20% war vs 10%). The Nash plan commits to a center-heavy split and backs off to patrol when tension passes ℓ = 3. Its worst case over Red's policies is the best: −116.

**★ Q32. De-escalation measures (D3) are free. Isn't their win built in?**
Partly, yes, and we say so. It also raises Red's payoff (101 to 144) because fewer wars help both. Workshop 2 prices it. The result is still informative: D3 is a real-world version of the mediator from the correlated-equilibrium example.

**Q32a. Why call D3 "de-escalation measures"?**
It does two things. Once ℓ ≥ 3, a quiet period lowers ℓ with probability 0.5 instead of 0.25; that is the hotline-like part, like the U.S.–China Defense Telephone Link set up in 2008. And assert hazards are halved; that is the CUES-like part, meaning agreed encounter rules and bridge-to-bridge communication. It is bilateral and helps Red too, so "de-escalation measures" covers both effects. The prototype GUI (and the slide 7 screenshot) still labels D3 "Crisis hotline"; it is the same design, renamed in the paper and slides after the code was frozen for this round.

**Q32b. Is Subic Bay an EDCA site?**
We don't claim it is. D1 is a third Blue port at Subic Bay, standing in for added U.S. access in the Philippines that shortens trips to the South. Which specific facility would play that role is outside the model.

**Q33. Why does the extra port (D1) hurt Red but not help Blue much?**
Shorter trips to the South let Blue contest Red's valuable southern zones, which costs Red (101 to 16), but more contact means more incidents (war 28%), which eats Blue's gain.

### E. Prototype and plan

**Q34. How does the code match the model?**
`Game.step` is the 7-step timeline with the control, hazard and payoff equations; `MIPBRPolicy` builds and solves the MIP each turn; `MetaGame` builds the template game and runs dominance, Nash enumeration and both LPs. `experiments.py all` regenerates every number in the report.

**Q35. What will learning add?**
In Workshop 2: a Red that learns from repeated play, and fictitious-play or no-regret updates on the template game. The question is whether they converge or cycle, drift toward restraint or assertion, and exploit predictable Blue play. (Present these only as plans; we have not built them yet.)

**Q36. What attacks will you test?**
Three already coded: a CCG blockade of Blue's routes at Scarborough and Second Thomas, jamming of Blue sensing, and false contacts. Defenses: randomized patrols, D1, D2.

### F. Real-world grounding (cite if pressed; see Part 4)

**Q37. Is this behavior real?**
Yes, in kind. China uses coast guard and maritime militia to keep presence and obstruct others while trying to avoid a military response (Helmus et al. 2024). PLAN ships have made unsafe close maneuvers near U.S. destroyers: USS Decatur near Gaven Reef in September 2018, and USS Chung-Hoon in the Taiwan Strait in June 2023. The U.S. conducts freedom-of-navigation operations against excessive maritime claims and reports them yearly. Encounters between navies are meant to follow CUES (2014).

**Q38. How is this different from existing gray-zone games or patrol models?**
Wasser et al. (2019) built a structured gray-zone game with explicit objectives and probabilistic adjudication; we automate every rule, so thousands of runs can compare strategies. PROTECT (Shieh et al. 2012) is a deployed leader–follower model for Coast Guard port patrols, and Washburn and Wood (1995) model network interdiction as a two-person zero-sum game. Ours is general-sum with simultaneous moves: both sides contest control, and war costs both. The incident hazard follows Schelling's (1966) idea of escalation as a shared risk that each side manipulates.

### If you only get two questions
Have Q6 (numbers are assumptions), Q18 (MIP-BR vs equilibrium), Q26 (restraint vs aggressive), Q28 (war rate) and Q32 (free de-escalation measures) ready. They are the obvious weak spots.

---

## Part 4. Sources for real-world claims

- Helmus, T. C., et al. (2024). *Understanding and Countering China's Maritime Gray Zone Operations*. RAND RR-A2954-1. https://doi.org/10.7249/RRA2954-1
- Green, M., et al. (2017). *Countering Coercion in Maritime Asia*. CSIS.
- Western Pacific Naval Symposium (2014). *Code for Unplanned Encounters at Sea (CUES)*.
- U.S. Indo-Pacific Command (June 2023). Statement on unsafe maritime interaction (USS Chung-Hoon, Taiwan Strait). https://www.pacom.mil/Media/News/News-Article-View/Article/3415952/usindopacom-statement-on-unsafe-maritime-interaction/
- Air Force Times / Navy Times (Oct 2, 2018). U.S. Pacific Fleet says Chinese destroyer came dangerously close to USS Decatur. https://www.airforcetimes.com/news/your-navy/2018/10/02/us-pacific-fleet-says-chinese-destroyer-came-dangerously-close-to-navy-ship
- East Sea Fleet (Eastern Theater Command Navy), Wikipedia. https://en.wikipedia.org/wiki/East_Sea_Fleet
- Yulin Naval Base, Wikipedia. https://en.wikipedia.org/wiki/Yulin_Naval_Base
- Defense News (Sept 21, 2022). Satellite images reveal Chinese expansion of submarine base. https://www.defensenews.com/naval/2022/09/21/satellite-images-reveal-chinese-expansion-of-submarine-base/
- NOAA AOML Hurricane Research Division, Tropical Cyclone FAQ G1 (when is hurricane/typhoon season). https://www.aoml.noaa.gov/hrd/tcfaq/G1.html
- Hong Kong Observatory, Winter monsoon. https://www.weather.gov.hk/en/education/weather/monsoons/00070-winter-monsoon-from-the-perspective-of-strong-monsoon-signal.html
- Arms Control Association (April 2008). Hotline to link U.S.-Chinese militaries. https://www.armscontrol.org/act/2008-04/hotline-link-us-chinese-militaries
- U.S. Indo-Pacific Command (2024). DoD releases Fiscal Year 2023 Freedom of Navigation Report. https://www.pacom.mil/Media/News/Spotlight/Article/3771243/dod-releases-fiscal-year-2023-freedom-of-navigation-report/
