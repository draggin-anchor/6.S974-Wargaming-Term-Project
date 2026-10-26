# Workshop 1 presenter notes and Q&A

**Talk:** Tue 2026-10-27. 10 minutes + 2 minutes of questions. 12 slides.
**Synced to:** the paper and the deck as of Mon 2026-10-26, 7:45 PM ET, when Sean finished his paper review. This includes all changes Sean accepted today. LCS are removed, §1 and the RQ wording are new, weather is now stylized scenarios, the fuel budget is now a movement budget, the ship index is j, and §3.6, §4.1 and §4.2 are revised.

Part 1 is the game formulation in plain words, so any of the three of you can answer questions on it. Part 2 is the slide-by-slide script with timings. Part 3 is the likely Q&A. Part 4 is the sources for any claim about real U.S. or Chinese behavior.

---

## Part 1. The game formulation, explained

### One-sentence version
Two navies station ships on a network of contested waters every two days and choose to patrol or assert. Control of each zone follows the local force ratio. Incidents happen only where both sides meet, incidents push an escalation ladder toward war, and war costs both sides.

### The pieces, in the order of the paper (§3)

| Piece | What it is | Values (all our assumptions) |
|---|---|---|
| **Players** | Blue = U.S. Navy. Red = China. Red has navy (PLAN) ships plus coast guard and maritime militia hulls, grouped as CCG. | 10 DDG. 8 PLAN + 6 CCG |
| **Map** | Undirected graph G = (V, E). There are 8 contested zones. They are the Senkakus, Miyako Strait, Taiwan Strait, east of Taiwan, Luzon Strait, Scarborough Shoal, Second Thomas Shoal and the Paracels. Blue's home ports are Yokosuka and Guam. Red's are Ningbo and Sanya. An edge is one period of sailing. There are three weather regions, North, Center and South. | Each zone has a value V for each side. Red values Scarborough and the Paracels more. |
| **Time** | Periods of 2 days, T = 60 (about 4 months). All ships start in port with full endurance. DDGs start 5 at Yokosuka and 5 at Guam. Each Red type is split evenly between Ningbo and Sanya. Payoffs are discounted by δ per period. | δ = 0.98 (0.98⁶⁰ ≈ 0.30) |
| **State** | Ships at each node, and each ship's endurance (periods left at sea). The control index c of each zone, in [−1, 1], where +1 is Blue fully in charge and −1 is Red. The escalation level ℓ, from 0 (calm) to L = 5 (war). The sea state of each region. | Start at ℓ = 1. Starting control is in Table 2 |
| **Information (fog)** | Each side sees its own ships, control, ℓ and weather. Neither side sees the other's entire fleet disposition. It sees only forces present where it also maintains forces. Formally, you detect enemy ships at a node with probability 0.95 if you have a ship there, 0.6 next door or near your port, and 0.2 elsewhere (satellite). Rough seas multiply these by 0.7. Your belief is the last count you saw. | Bayesian beliefs are the Workshop 2 upgrade |
| **Actions** | Moves are simultaneous. Each ship stays or sails one edge. In each zone where you have ships, you pick a posture. **Patrol (P)** is routine presence. **Assert (A)** covers shadowing, close maneuvering, querying and warning, and (U.S. only) freedom-of-navigation operations, modeled as one posture. | Assert multiplies your strength by α = 1.5 |
| **Constraints** | Flow conservation, so ships are moved and no new ships enter play. The movement budget allows at most F ship moves per period across the theater. A ship that could no longer get home on its endurance is forced home and refits for a full period. No ship enters the other side's ports or a storm-closed zone. An illegal order leaves the ship where it is. | F = 8 Blue, 10 Red. Endurance 10 DDG, 8 PLAN, 6 CCG |
| **Control dynamics** | Strength S = (1.5 if asserting) × weighted hull count. Local balance φ = (S_B − S_R)/(S_B + S_R + κ). Control moves 30% of the way toward φ each period, c ← 0.7c + 0.3φ. Control is frozen in storms. | DDG, PLAN = 1. CCG = 0.6 (0.3 in rough seas). κ = 1 |
| **Incidents** | An incident is a collision, an unsafe interaction, or negative media coverage. It can happen only where both sides have ships. Hazard h = (baseline + assert terms) × min(S_B, S_R) × (1 + ℓ/2), and probability ρ = 1 − e^(−h). Each incident raises ℓ by 1. A quiet period lowers ℓ by 1 with probability μ = 0.25. ℓ = 5 is war and ends the game. | h₀ = 0.006. Blue assert adds 0.03. Red assert adds θ·0.036 + (1−θ)·0.012, where θ is the PLAN share of Red strength in the zone |
| **Stage payoff** | g = (value of control) − 0.1 × (moves) − 1 × ℓ − ζ_D (Blue's redesign cost). Blue's control term is V^B·c summed over zones. It is positive where Blue holds a zone and negative where Red does. Red's is −V^R·c, the mirror image. It is linear, with no cutoff at zero. The tension term 1 × ℓ stands for the diplomatic and economic strain incurred. | ζ_D is 0.3 for D1, 0.5 for D2 and 0 for D3 |
| **Total payoff** | Discounted sum of stage payoffs, minus W = 200 for **both** sides if war comes. So it is general-sum, not zero-sum. Both want to avoid war. | Blue's max per period is 42, so war costs about 5 perfect periods |
| **Weather** | Four scenarios ω (calm, nominal, typhoon, extreme) with weights 0.25/0.40/0.25/0.10. Storms last 3 periods. They close a region's zones, stop incidents and freeze control. Rough seas halve CCG strength and cut detection. Robustness is the expected payoff over ω and the worst case over ω. | Storm and rough-sea chances per period are in Table 2 |

### Worked example (good to have ready if asked "show me the numbers")
One Blue DDG meets one Red CCG hull in calm seas, at ℓ = 1, with control starting at 0.
- **Blue patrols.** S_B = 1 and S_R = 0.6. φ = 0.4/2.6 = 0.15, so control moves to +0.05. Hazard = 0.006 × 0.6 × 1.5 = 0.0054, so the incident chance is about 0.5%.
- **Blue asserts.** S_B = 1.5. φ = 0.9/3.1 = 0.29, so control moves to +0.09. Hazard = 0.036 × 0.6 × 1.5 = 0.032, so the incident chance is about 3.2%.
- **Message.** Asserting roughly doubles the control you gain and multiplies incident risk about six times. That trade is the whole game.

### What we measure, and what "200 simulated games per setup" means
**Outcomes.** We report these for every setup we test (a policy pair, a risk budget, a redesign, or a weather scenario).
1. **Blue's control share.** Each period, take every zone's control index (+1 Blue, −1 Red), weight it by the zone's value to Blue (Taiwan Strait 10 ... Paracels 2), and average over the game. +1 means Blue held everything all game, −1 means Red did, and 0 means an even split.
2. **War rate.** The share of games that reach escalation level 5.
3. **Payoffs u_B and u_R.** Each side's total score from §3.5. That is control gained, minus fuel, tension and redesign costs, minus 200 if the game ends in war.
4. **For RQ3 only.** The payoff averaged over the four weather scenarios, and the payoff in the worst scenario.

**200 simulated games per setup (the code calls them seeds).** Every game has luck in it. Detections, incidents, storms and the moves of the random policy are all random draws. A seed is the starting number for the computer's random draws. So one seed is one simulated 60-period game with one particular run of luck, and each setup is played as 200 simulated games with different luck. We report the averages. Every setup uses the same seeds, 0 to 199, and weather is drawn from its own random stream. So the policies we compare face identical luck, and differences come from the policies, not from chance.

### How a player decides. The best-response MIP (§3.6)
- Each period, a player picks ship destinations and postures to maximize **value of control − incident cost − fuel**, given where it believes the enemy is. It is a best response written as a mixed-integer program, solved exactly with Gurobi.
- **Why the option variables b?** A MIP needs a linear objective and linear constraints. But the balance φ = (S_B − S_R)/(S_B + S_R + κ) is a ratio of ship counts, and the incident probability ρ = 1 − e^(−h) is an exponential, so neither is linear in the number of ships sent. Within one turn everything else is fixed (believed enemy ships, sea state, ℓ), and a zone holds only a few hulls. So for each zone we **list every possible (hull count n, posture p)** and compute its value a_v(n,p) and risk ρ_v(n,p) in advance as plain numbers. A binary b_{v,(n,p)} picks exactly one row per zone, so total value Σ a·b and total risk Σ ρ·b are linear. The "option matches the moves" constraint forces the chosen row's n to equal the ships the y variables actually send there. The cost is that the list grows with fleet size and ship types. That is fine for a few hulls per zone.
- **Example option list.** Blue is in the Senkakus (V = 6) and believes one Red CCG hull is on patrol there, in calm seas, at ℓ = 1.

| Option (n, p) | Balance φ | Incident chance ρ | Value a = 6·β·φ − 20·ρ |
|---|---|---|---|
| 0 DDG | −0.38 | 0% | −2.15 |
| 1 DDG, patrol | 0.15 | 0.5% | 0.77 |
| 1 DDG, assert | 0.29 | 3.2% | 1.03 |
| 2 DDG, patrol | 0.39 | 0.5% | 2.12 |
| 2 DDG, assert | 0.52 | 3.2% | 2.35 |

  The MIP picks one row per zone. Asserting adds value here, but it uses 0.032 of the risk budget ε against 0.005 for patrolling. Across all zones, that budget is what decides where assertion is worth it.
- **Risk budget.** Expected incidents this period ≤ ε × (1 − ℓ/L). This is the "feasible region" from the D1 feedback. The cap tightens to zero as ℓ approaches war. The proposal's commander types are now budgets. Conservative is 0.05, moderate 0.15 and aggressive 0.40. **Slack ξ.** The budget row is really "expected incidents ≤ ε(1 − ℓ/L) + ξ", with ξ ≥ 0 and a penalty of 1000·ξ in the objective. A ship on forced return may have to pass through a zone the opponent occupies. That risk cannot be avoided, and near war it can exceed the shrinking cap. ξ lets the program exceed the cap by only that unavoidable amount, so it always has a solution (Q19a).
- **Value of an option.** a = V × β × (local balance) − Λ × (incident probability). β = λ/(1 − δ(1 − λ)) ≈ 0.96 converts one period of balance into its total discounted effect on control. Λ = 20 is the price of one expected incident.
- **Limitation to own.** It looks one period ahead.

**MIP pieces at a glance**
- **y_{j,w}** = 1 if free ship j goes to node w. The choices are stay, sail home, or sail to a neighbor it can still get home from. Ships on forced return are not decided, so they have no y. y appears in four places. Each ship gets exactly one destination. The movement budget limits moves to F_i minus forced moves. The fuel cost −γ·Σy charges each move. The linking constraint sets the ships y sends into v, plus forced arrivals, equal to the n of the chosen option.
- **n and p.** n is the player's own hull count in zone v by type. For Blue it is the number of DDGs. For Red it is (number of PLAN, number of CCG). p is the single posture in that zone, P or A. The rows run from the ships already committed to v (forced returns) up to that number plus every free ship that can reach v this turn, each with P and A. Zero ships has only a P row.
- **a_v(n,p) = V·β·σ·φ − Λ·ρ** is one option's score, control gain minus incident cost. The MIP adds up a over the chosen rows, subtracts move costs, and maximizes, subject to total ρ ≤ the risk budget. The scores decide what is attractive. The budget decides what is allowed.
- **One option per zone.** Σ over (n,p) of b_{v,(n,p)} = 1 for each contested zone, so each zone ends the turn in exactly one situation (one hull count, one posture). Without it the solver could pick no row, dodging that zone's risk or the negative score of leaving it empty. Or it could pick several rows, collecting both "2 DDG patrol" and "2 DDG assert". Together with the linking constraint, the one chosen row matches where y actually sent the ships. So the value and risk the MIP adds up belong to the moves it really ordered.
- **The option matches the moves.** Σ over (n,p) of n_k·b_{v,(n,p)} = x̄_{k,v} + Σ over ships j of type k of y_{j,v}, for every zone v and type k. The left side is the chosen row's type-k hull count, since only one b is 1. The right side is the ships actually there. That is forced-return arrivals x̄ plus free ships ordered to v, including ships that stay. For example, if y puts 2 DDGs in the Senkakus, the solver must pick a row with n = 2. Only patrol vs. assert is left to choose, and it cannot claim a 3-DDG row's score. Blue has one such equation per zone. Red has one per type (PLAN, CCG) per zone. It is the link between the orders (y) and the scored outcomes (b).
- **Where are the storm, endurance and port rules?** Mostly in which y variables exist, not in extra rows. y_{j,w} is created only for legal destinations. A ship moves at most one edge per period (stay, home, or a neighbor). It never enters a storm-closed zone, and ships inside a storm stay put. It never enters the opponent's home ports. It never goes where it could not get home on its remaining endurance d_j, unless the move brings it closer to home. The MIP also requires the ship to have at least one period on station there. Ships on forced return or refitting have no y. Their next node is fixed in x̄. The explicit row is the movement budget (moves ≤ F_i − forced moves), and the fuel cost γ per move sits in the objective. Weather also enters the option scores. Storm zones have φ = ρ = 0, and rough seas halve CCG strength, which changes φ and ρ.
- **β is not a linearization.** The option list handles the nonlinearity. β handles time (Q21).

### The template game (§3.7) and the six policies
- The full game is far too big to solve for equilibrium. So we shrink it. Each side picks one of **14 templates**, which are 7 ways to split ships North/Center/South, times patrol or assert everywhere. The payoff is settled control (c = φ) minus incident cost, in calm seas at ℓ = 1. That is a 14 × 14 strategic-form game. We solve it with iterated elimination of strictly dominated strategies (IESDS), pure Nash enumeration, the maximin LP and the correlated-equilibrium LP.
- **Policies compared** (slide name, then the paper's name in brackets).
  - Random moves.
  - Rule of thumb (rule-based, the moderate commander).
  - Quick best response (greedy, no solver).
  - Best response (MIP).
  - Nash equilibrium plan (equilibrium). It plays a pure NE template. Of the two pure NE it uses the one with the higher total payoff, which is our choice.
  - Safety-first plan (maximin). It plays the template mix that guarantees the best payoff whatever the opponent plays, redrawn every 3 periods.
  - Every policy faces the same random draws and weather.

### Blue redesigns (§3.8)
- **D1 extra port.** A third Blue port at Subic Bay, linked to Scarborough, Luzon and Second Thomas. It costs 0.3 per period. It is a structural change.
- **D2 extra surveillance.** Blue detects in every zone with probability at least 0.6, even in bad weather. It costs 0.5 per period.
- **D3 de-escalation measures** (hotline plus CUES-style encounter rules). At ℓ ≥ 3, a quiet period lowers ℓ with probability 0.5 instead of 0.25, and assert hazards are halved. **It has no cost yet**, and it helps Red as much as Blue.

### Simplifying assumptions (say these before someone else does)
There are two unitary players, with no allies as players. Control is a force-ratio index. Incidents are the only path to war. Beliefs are last-seen counts. Best responses look one period ahead. Every number is an assumption.

### On the slides but no longer in the 5-page paper
The paper was cut to 5 pages on 10/26. If asked "where is that in the report?", these are now only on the slides or in these notes.
- **Theater map and GUI screenshot** (slides 2 and 7). The paper has no figures now.
- **RQ1 frontier** (slide 8, left). Raising Blue's budget ε from 0.02 to 0.15 lifts Blue's control share from −0.25 to −0.05, while war rises from 7% to 20%. Going to 0.40 adds only 0.06 more control.
- **RQ3 policy-by-weather chart** (slide 10, left).
- **Correlated equilibrium of the 2 × 2** (slide 6). It puts 0.40 on (patrol, patrol), 0.54 on (Blue asserts, Red patrols), 0.06 on (Blue patrols, Red asserts), and 0 on (assert, assert).
- **Common random numbers** (same seeds and weather for every policy), **maximin's definition**, and the **full β derivation**. See Q30c, the policies bullet above, and Q21.

**Paper section map now.** §4.1 is the small example plus the template game. §4.2 is RQ1 (Table 3, risk-budget game). §4.3 is RQ2 (Table 4, policies). §4.4 is RQ3 (Table 5, designs).

### Notation cheat sheet (full Table 1)
The paper now keeps only the parameter half of Table 1. Both halves are here. A printable copy is `02-workshop1-notation-table.pdf`, stored next to these notes.

**State, beliefs and choices** (removed from the paper)

| Symbol | Meaning |
|---|---|
| x^t_{k,v} | type-k ships at node v |
| d^t_j | periods ship j can still stay at sea |
| c^t_v | control of zone v, +1 Blue, −1 Red |
| ℓ^t | escalation level (war at L) |
| w^t_r | sea state of region r |
| x̂^t_{−i,v} | i's last-seen opponent count at v |
| p_{i,v} | posture, patrol (P) or assert (A) |
| f^t_{k,uv}; m^t_i | ships sailing u → v; moves made |
| S_{i,v}; φ_v | local strength; local balance |
| h_v; ρ_v | incident hazard; incident probability |
| g^t_i; u_i | stage payoff; total payoff |
| y_{j,w} | MIP. Ship j goes to node w |
| b_{v,(n,p)} | MIP. n hulls with posture p at v |
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
| q_{i,v} | detection here / nearby / far | 0.95 / 0.6 / 0.2, × 0.7 in rough seas |
| Λ; β | MIP incident price; persistence factor | 20; 0.96 |
| ε_i | escalation-risk budget | 0.05 / 0.15 / 0.40 |
| ζ_D | Blue's redesign cost per period | D1 0.3; D2 0.5; D3 0 |

---

## Part 2. Slide-by-slide script

The current speaker notes add up to about 11.5 minutes. The timings below fit 10:00. The speaker split is only a suggestion.

| # | Slide | Time | Suggested speaker |
|---|---|---|---|
| 1 | Title | 0:20 | Sean |
| 2 | The problem. Control without war | 1:00 | Sean |
| 3 | Research questions and changes | 0:50 | Sean |
| 4 | The game, one period at a time | 1:15 | Sean |
| 5 | How the players decide | 0:50 | Tate |
| 6 | Small example. When does it pay to assert? | 1:00 | Tate |
| 7 | The prototype | 0:45 | Tate |
| 8 | RQ1 | 0:55 | Matthew |
| 9 | RQ2 | 0:50 | Matthew |
| 10 | RQ3 | 1:00 | Matthew |
| 11 | What the evidence does and does not show | 0:35 | Matthew |
| 12 | Plan for Workshop 2 | 0:30 | Sean |

**1. Title (0:20).** We study day-to-day U.S.-China competition for control of the waters inside the First Island Chain, below the threshold of war, as a game on a network. Today we cover the model, the prototype, and first results on three questions.

**2. The problem (1:00).** China presses its claims with coast guard and militia hulls backed by navy ships. The U.S. keeps the seas open with destroyers on presence and freedom-of-navigation patrols (Helmus 2024; Green 2017). Point at the map. Squares are home ports, and circles are eight contested zones in three regions. Dashed lines are the Philippine port from one of our redesigns. Three things make this a game, not one optimization. Control is relative, so my best move depends on yours. Escalation risk is shared, because incidents need both sides present and war costs both. And neither side sees the other's entire fleet disposition, only forces where it also has forces.

**3. Research questions (0:50).** RQ1. Each side caps the incident risk it accepts per period. How much control does more risk buy, how much likelier is war, and what cap does each side pick when the other is picking too? RQ2. Does planning with game theory beat simple rules? And can both sides stay at patrol because asserting once would end the truce and push both into riskier play from then on? RQ3, from Prof. Sapsis. Does the best plan or redesign in normal weather stay best across calm, typhoon and extreme weather scenarios, both on average and in the worst scenario? The table maps each piece of feedback to a change. The main ones are a fully formal model, the commander types as one risk-budget number inside a MIP, and preliminary results from 77 setups of 200 simulated games each.

**4. One period (1:15).** Read the timeline top to bottom. It is one two-day turn. The weather is drawn first. Each side sees its own ships and some enemy ships. Low-endurance ships head home. Both choose moves and postures at the same time. Then control, incidents and escalation update, and payoffs are scored. On the right, control moves 30% of the way toward the local force balance each turn, so presence builds control slowly. Incidents need both sides present and get likelier with assertion and with tension already high. Payoff is zones held minus fuel, tension, and Blue's redesign cost. War costs both 200, so it is not zero-sum. If you have 10 seconds spare, give the DDG vs. CCG example from Part 1.

**5. How the players decide (0:50).** On the left, each turn a player solves a MIP with a cap ε on expected incidents. That answers the feedback that Q1 is a feasible region. In the middle, to find equilibria we shrink each side to 14 templates and solve that 14 × 14 game exactly with dominance, Nash equilibrium and the two LPs. On the right are the six policies. All see the same random draws.

**6. Small example (1:00).** Fix where ships go, so each side only picks patrol or assert. Asserting against a patroller pays a little. If both assert, both lose more than 11. So the best reply is the opposite of the other side, which makes it an anti-coordination game. It has two pure equilibria and a mixed one with mutual assertion 8% of the time. There are two fixes. First, the best correlated equilibrium never recommends both asserting, and a mediator or hotline can implement it. Second, in the repeated game, a standing threat makes mutual patrol a subgame perfect equilibrium for any discount factor above 0.18. The threat is that if either side pushes, the truce is off for good and both fall back to the mixed equilibrium. Ours is 0.98.

**7. Prototype (0:45, or a live demo of the same length).** Pick a plan for each side, a design and the weather, then Step or Play. Zone color is control. Letters count ships. A thick outline means asserting. An orange ring is an incident. Shading is bad weather. Bottom left is the escalation ladder, and 5 is war. "Run many games" plays the same setup as many simulated games and reports averages. One script reproduces every number in the report.

**8. RQ1 (0:55).** On the left, Blue loosens its budget while Red stays moderate. Control rises fast up to about 0.15, then flattens, while war risk keeps rising, from 7% to 20% as ε goes from 0.02 to 0.15. On the right, both sides choose a budget. Aggressive is the best reply to anything for both, so the only equilibrium is both aggressive, with the highest war rate, 34%. Both would do better at moderate–moderate (war 20%). That is a prisoner's dilemma. Restraint has to come from repetition or coordination, as on slide 6.

**9. RQ2 (0:50).** Each Blue policy plays three Red policies, 200 games each. The bar is Blue's payoff against its worst opponent. The Nash equilibrium plan has the best worst case, −116, and half the war rate of the MIP best response against the same Red (10% vs 20%). Best responses do well against weak opponents but escalate. Safety-first is cautious but gives up control. Differences under about 20 points are ties.

**10. RQ3 (1:00).** Robustness means two things here. One is expected payoff over the four weather scenarios. The other is the worst case. The ranking holds. The top two plans stay on top in every scenario. Bad weather slightly helps Blue because rough seas weaken Red's coast-guard hulls and storms pause incidents. Of the redesigns, de-escalation measures (D3) are best on average and in the worst case, and they cut war from 20% to 5%. The caveat is that they have no cost yet and help Red too, so it is a joint gain.

**11. Evidence (0:35).** Left is what the runs support. Right is what they do not. Values are assumptions, policies look one turn ahead, the war rate depends heavily on a few parameters, and the de-escalation result is partly built in. A sensitivity analysis is first for Workshop 2.

**12. Workshop 2 (0:30).** First comes a sensitivity analysis on the zone values, hazards, war penalty and cool-down rate. Then we add Bayesian beliefs and calendar-based weather from real data, and we reformulate the movement budget with oilers in mind. Next come learning agents, three Red attacks and Blue's defenses. Last, we test the redesigns under attack, with a cost for de-escalation measures. Thank you. We are happy to take questions.

---

## Part 3. Likely questions and answers

Answers are short on purpose, 15 to 30 seconds each. ★ = most likely.

### A. Model structure

**★ Q1. Why is this a game and not just an optimization for Blue?**
Because control is relative and risk is shared. My control depends on the ratio of my ships to yours, and an incident needs both of us in the zone. So my best allocation changes when yours does. The small example on slide 6 shows it. The best reply flips depending on what the other side does.

**★ Q2. What does "control" actually mean?**
It is a proxy for who can operate freely in a zone and enforce its view of the rules there. It is an index from −1 (Red fully in charge) to +1 (Blue). It moves 30% of the way toward the local force balance each period, so you earn it by staying and lose it by leaving. It is a modeling choice, not a measured quantity.

**Q3. Why a force ratio with κ = 1?**
The ratio makes control relative, which is the point. κ stops a token presence from counting as full control. One DDG alone gives balance 0.5, not 1.

**Q3a. Why these starting control values (Taiwan Strait 0, Senkakus +0.2, Miyako +0.3, east of Taiwan +0.2, Luzon +0.1, Scarborough −0.2, Second Thomas 0, Paracels −0.4)?**
They are judgment-call assumptions. Zones next to Japan and Okinawa lean Blue. Japan administers the Senkakus, and the Miyako Strait runs between Japanese islands, with U.S. forces on Okinawa. Features China holds or controls access to lean Red. China occupies the Paracels, and Scarborough leans Red too. The true flashpoints, Taiwan Strait and Second Thomas Shoal, start at 0. Blue is the U.S. Navy only, so allied presence (Japan, the Philippines) is folded into these starting values. They barely matter for the results. Control moves 30% of the way to the local balance each period, so after 10 periods (20 days) only 0.7¹⁰ ≈ 3% of the starting value remains. They shape the first weeks, not the four-month results.

**Q3b. When a ship first arrives, does control jump to the balance?**
No. The same update applies every period, c ← 0.7c + 0.3φ, so control closes 30% of the gap each period. For example, one DDG alone on patrol in a zone at c = 0 gives φ = 1/(1 + 0 + 1) = 0.5. Control goes 0.15, 0.26, 0.33, and reaches 0.42 after 5 periods, heading toward 0.5. In closed form, c = φ + (c_start − φ)·0.7ⁿ. That is 83% of the way in 5 periods (10 days) and 97% in 10. A lone asserting DDG gives φ = 0.6. Two DDGs on patrol give φ = 0.67.

**★ Q4. Why are moves simultaneous instead of leader-follower (Stackelberg)?**
Day-to-day gray-zone presence is both sides adjusting at once, each without full knowledge of the other. Leader-follower is in the Workshop 2 plan. That is an attacker that moves after seeing Blue's posture, solved by backward induction.

**Q5. What kind of game is this, formally?**
A finite-horizon dynamic game with chance moves (weather, incidents) and imperfect information. Players decide at information sets that do not reveal the opponent's current positions. It is general-sum because both pay the war penalty.

**★ Q6. Where do the numbers come from?**
They are our assumptions. There is no public data for most of them, and the instructors said to propose reasonable values. Hazards and μ were set so war is uncommon but not rare, so the risk trade-off is measurable. Every value is in Table 1. A sensitivity analysis on V, h, W and μ is the first Workshop 2 task (Q6a).

**Q6a. What is the sensitivity analysis?**
We rerun the experiments with the zone values V, the hazards h, the war penalty W (100 and 300) and the cool-down rate μ (0.125 and 0.375) each set 50% lower and 50% higher. Then we check whether the three headline results survive. Those are both sides choosing aggressive in the risk-budget game, the Nash plan having the best worst case, and de-escalation measures winning.

**Q7. Why is war reached only through incidents? States can choose war.**
It is a stated simplification. We study the gray zone below the threshold, and deliberate escalation is outside this model. Incidents driving escalation follows Schelling's idea of shared, manipulated risk.

**Q7a. What is a "quiet period"?**
One period (2 days) with no incident anywhere in the theater. After each quiet period, ℓ drops one level with probability μ = 0.25. So on average it takes 4 quiet periods (about 8 days) per level, and about 24 days without incidents to get from ℓ = 3 back to calm. Any incident raises ℓ immediately. With de-escalation measures (D3), μ = 0.5 at ℓ ≥ 3, so it takes about 4 days per level up there. The design choice is that crises start fast and cool slowly. μ is our assumption.

**Q8. Why does a CCG hull count less than a navy ship, and less in rough seas?**
Coast guard and militia hulls are smaller and lightly armed, so they count as 0.6 of a warship. In rough seas small hulls lose effectiveness, so they count 0.3. That rough-sea effect is why bad weather helps Blue slightly.

**Q8a. Red has 14 hulls, so why is F_R = 10?**
F is a movement budget, not a fleet size. It is the most ship moves (one move = sailing one edge) a side can make per period across the theater. Each ship's own fuel is its endurance d_j. In the paper's words, the theater-wide movement budget "stands in for operational requirements and station-keeping". That is our interpretation, not documented practice. Ships that stay put use none, and forced returns are charged first. So at most 10 of Red's 14 hulls and 8 of Blue's 10 DDGs can reposition in one period, and neither side can shift its whole fleet at once. The values are our assumptions. Workshop 2 will reformulate it with oilers (refueling ships) in mind. The per-move cost γ in the payoff is still a fuel cost.

**Q9. Why is PLAN assertion more escalatory than CCG assertion?**
Using coast guard and militia is how China applies pressure while trying to avoid a military response (Helmus et al. 2024). So pressure from CCG hulls carries a lower hazard (0.012) than from navy ships (0.036).

**★ Q10. Why are querying and warning counted as assert, not patrol?**
A query or warning that challenges another ship's presence is a demand to comply. It presses a claim. Patrol is routine presence that presses no one. (Sean can speak to this from experience.)

**Q11. Why is assert one posture? FONOPs and shadowing are very different.**
It is a simplification for Workshop 1. Making FONOP its own Blue action is planned. That turns the 2 × 2 example into 3 × 2.

**Q12. Where are Japan, the Philippines, Taiwan?**
They are not players. Two unitary players is a stated simplification. The Philippines enters only as basing access in redesign D1.

**Q13. Why did the littoral combat ships disappear?**
We simplified Blue to destroyers for this submission. Adding LCS as a second Blue type is Workshop 2 work.

**Q13a. Why Ningbo and Sanya as Red's ports? CCG and militia don't sail from there.**
They stand for basing areas, not single piers. NBO is the Ningbo-Zhoushan area and SAN is Hainan (Yulin). Coast guard and militia ports are folded into them, as the paper's footnote says. In reality Ningbo hosts the Eastern Theater Command Navy headquarters, with ships mostly berthed at Zhoushan. Yulin, near Sanya, is a major naval base with submarine facilities and is reported as the carrier Shandong's home port. The Southern Theater Navy headquarters is at Zhanjiang. Two ports per side keeps the graph small. Adding more is easy if it matters for a question.

**Q13b. What exactly is the state s^t?**
A snapshot of the whole theater at the start of period t. Its parts are full lists. x^t gives the ship count of each type at every node, d^t the endurance left for every ship, c^t the control index of every zone, and w^t the sea state of every region. The escalation level ℓ^t is a single number for the whole theater.

### B. Information and weather

**★ Q14. How exactly do you model fog of war?**
Each period you detect enemy ships at a node with probability 0.95 if you are there, 0.6 next door and 0.2 elsewhere, and 30% less in rough seas. Your belief is the last count you saw. Neither side sees the other's entire fleet disposition. It sees only forces present where it also maintains forces. Bayesian updating is the Workshop 2 upgrade.

**Q15. Why does extra surveillance (D2) show no benefit even when free?**
Because our policies barely use better information. The MIP looks one turn ahead, and the template plans hardly react to where the enemy is. That is a finding about the policies, not proof that sensing has no value. Bayesian beliefs should change it.

**★ Q16. Bad weather helps Blue? Isn't that strange?**
In this model, rough seas halve CCG strength, and storms pause incidents and freeze control. So calm seas favor Red's coast-guard numbers. An earlier version had storms erase control, which made this effect an artifact. We fixed that, and the effect is small.

**Q17. Why scenarios and not a full weather probability model?**
The weather scenario ω is a chance move with weights, and we score by expected value and by worst case. It answers Prof. Sapsis's question of robustness, not just effectiveness.

**★ Q17a. How does the weather work (Table 2)?**
Each game runs under one scenario ω. The weights π_ω (0.25 / 0.40 / 0.25 / 0.10) are used only to average results in RQ3. The worst case ignores them. Each period, each region (North, Center, South) not already in a storm gets one with probability p_s. A storm lasts 3 periods (6 days). It closes the region's zones, stops incidents there and freezes control. Otherwise the sea is rough with probability p_r, which halves CCG strength and cuts detection to 70%. If neither happens, it is calm. The long-run share of time a region spends in storm and in rough seas is 0% and 0% for calm, about 6% and 19% for nominal, about 15% and 30% for typhoon, and about 26% and 37% for extreme. All values are our assumptions, chosen to span "no weather" to "very bad weather". They are not climate data.

**Q17c. In a storm, is control frozen or just not scored?**
It is frozen and still scored. The control update is skipped, so the zone keeps its pre-storm value. There are no incidents. The stage payoff still counts V·c every storm period. For example, Blue at c = 0.4 in the Senkakus keeps earning 6 × 0.4 per period. In the MIP, storm-zone options score φ = ρ = 0 because nothing a player does can change that zone this turn (no entry, and ships inside stay). It is not because the zone goes unscored.

**Q17b. Are these real seasons?**
No. They are four stylized weather scenarios, not calendar seasons. In reality, typhoons in the western North Pacific peak around August and September (NOAA). The winter northeast monsoon (about November to March) brings persistent rough seas in the Taiwan and Luzon Straits (Hong Kong Observatory). Workshop 2 will add calendar-based weather from real data.

### C. Decision rules and solution concepts

**★ Q17d. Explain the six policies simply.**
In one line, random is the baseline, rule-based is a sensible human, greedy and the MIP best response optimize move by move, and the equilibrium and maximin plans follow a game-theory plan for the whole campaign.
- *Random moves.* The baseline floor.
- *Rule of thumb (rule-based, moderate commander).* It goes where value is high and the enemy is thin. It asserts only where it thinks it outnumbers the enemy and ℓ ≤ 2. Then it pulls back until expected incidents fit ε = 0.15(1 − ℓ/L).
- *Quick best response (greedy).* A fast shortcut with no solver, using the same MIP objective and budget.
- *Best response (MIP).* It solves the risk-budget best response exactly each period. A larger ε makes it bolder.
- *Nash equilibrium plan.* It follows its part of the higher-total-payoff pure equilibrium of the 14-template game, steering ships toward that fleet split and posture.
- *Safety-first plan (maximin).* Every 3 periods, it draws a template from its maximin mixed strategy. That gives a guaranteed worst case and is unpredictable.

Both template plans patrol when ℓ > 3 and drop any assertion that breaks their risk budget.

**Q17e. Step by step, how does each policy pick its moves?**
The key contrast is this. Greedy and the MIP plan one move ahead and re-decide every period. The rule of thumb and the two template plans pick a destination and walk to it over several periods.
- *Random.* Each free ship stays or moves to a random legal neighbor (50/50). Posture is a coin flip per zone. It has no risk budget, and the engine drops moves over F.
- *Rule of thumb (moderate, ε = 0.15).* (1) It repeatedly assigns the best ship-zone pair and stops when the best score is below 0.05. The score is the control gain of one more hull, discounted for distance, minus fuel, divided by (1 + 0.5 × believed enemy strength). Targets can be several hops away. (2) Assigned ships step one hop toward their targets, highest score first, up to F. An unassigned ship goes home if it is in a zone where the enemy was seen, and otherwise stays. (3) It asserts only if ℓ ≤ 2 and its own strength exceeds the believed enemy strength. (4) While risk exceeds ε(1 − ℓ/L), it flips the riskiest asserting zone to patrol. If none is asserting, it pulls one hull out of the riskiest zone.
- *Quick best response (greedy).* See Q21b.
- *Best response (MIP).* It lists one-edge moves and each zone's options. Then Gurobi maximizes value minus fuel subject to the movement budget, option consistency, and risk ≤ ε(1 − ℓ/L) + slack.
- *Nash equilibrium plan.* It uses a fixed template, the higher-total-payoff pure equilibrium of the template game. Free ships are split by region per the template, then across zones in proportion to value, and the nearest reachable ship is matched to each slot. Ships step one hop toward their slots, nearest first, up to F. Occupied zones take the template's posture (patrol if ℓ > 3). The riskiest assertions flip to patrol until risk fits ε(1 − ℓ/L).
- *Safety-first plan (maximin).* The same, but every 3 periods it draws a new template from its maximin mixed strategy.

**Q17f. How does each policy decide between patrol and assert?**
Asserting multiplies a side's strength by 1.5, which means more control, but it raises the incident hazard. Every policy except random computes risk assuming the opponent keeps its last-seen posture (patrol if never seen).
- *Random.* A coin flip, with no budget.
- *Rule of thumb.* It asserts only if its own strength exceeds the believed enemy strength and ℓ ≤ 2. Both strengths are counted without the assert multiplier, so the enemy's posture is ignored here. Then it flips the riskiest assertions back to patrol until risk ≤ ε(1 − ℓ/L).
- *Greedy.* In each zone, it scores patrol and assert with V·β·φ − Λ·ρ and takes the higher. It allows assert only if total risk stays ≤ ε(1 − ℓ/L).
- *MIP.* It uses the same scoring, but posture is part of each zone's option list and is chosen jointly with the moves. So it can trade assertion between zones to fit the budget. Greedy and the MIP both account for enemy posture in the same way. They differ only in search.
- *Template plans (Nash, Safety-first).* They use the template's single posture in every occupied zone (patrol everywhere if ℓ > 3), then flip the riskiest assertions to patrol until risk fits the budget.

**★ Q18. Is MIP-BR an equilibrium?**
No. It is a one-period best response to beliefs about where the enemy is. Equilibrium analysis is done on the 14 × 14 template game, and the "Nash equilibrium plan" plays that equilibrium in the full game.

**★ Q19. Why both a risk budget ε and an incident price Λ?**
Λ prices risk in the objective. ε is a hard limit, the commander's risk tolerance or rules of engagement. The budget is what the D1 feedback called a feasible region, and it makes the proposal's three commander types a single number we can vary for RQ1.

**Q19a. How could forced returns break the risk budget?**
A ship on forced return has a fixed next node. It moves one step closer to home, or it stays put if no such node can be entered, for example because of a storm. If that node is a contested zone where the opponent is believed present, the incident risk is above zero even on patrol, and no other move can remove it. The cap ε(1 − ℓ/L) is tiny at high tension. A conservative 0.05 becomes 0.01 at ℓ = 4. So one such hull can exceed it, and without slack the MIP would have no solution. The slack carries a penalty of 1,000 per unit, so it covers only the unavoidable excess, and everything else is made as safe as possible. We do not log how often this happens, so don't claim it is rare.

**Q20. Why enumerate (count, posture) options instead of writing the formula in the MIP?**
Control and incident chance are a ratio and an exponential in ship counts, which a linear program cannot hold. Listing each zone's few possible options as binaries, with value and risk computed beforehand, keeps it linear and exact.

**Q20a. What does "the opponent postures it last saw (patrol if never seen)" mean?**
Each player keeps a memory, zone by zone, of the opponent's posture. When it detects the opponent in a zone, it records that posture (patrol or assert) and assumes it holds until its next detection there. If it has never detected the opponent in that zone, it assumes patrol. The MIP needs this because an asserting opponent counts 1.5 times as strong. That shifts the local balance φ and raises the incident hazard.

**Q21. What is β?**
β = λ/(1 − δ(1 − λ)) ≈ 0.96 is the total discounted effect on control of one period of local balance. Control updates as c ← 0.7c + 0.3φ. So one period of balance φ moves c by 0.3φ now, and 70% of that shift survives each later period (0.21φ, then 0.147φ, ...). Payoff is V·c per period, discounted by δ = 0.98. So the total is 0.3φ·Σₙ (0.98·0.7)ⁿ = 0.3φ/(1 − 0.686) = 0.955φ. One period of presence is worth about 0.96·V·φ in total, though only 0.3·V·φ shows up this period. **Why the MIP needs it.** The MIP looks one period ahead. Without β it would credit presence at only 0.3 while charging the full incident cost Λρ, so it would undervalue presence about threefold. **Caveats.** β counts only this period's push, and later balances get their own β when they are decided. It also ignores the chance that war ends the game early, so it slightly overstates the value of control at high ℓ.

**Q21a. Why δ = 0.98? Isn't that arbitrary?**
It is our assumption, per two-day period. A payoff 60 periods (about four months) out is worth 0.98⁵⁹ ≈ 0.30 of today's, and the half-life is about 34 periods (about 70 days). It sits far above the 0.18 threshold for sustaining restraint, so the restraint result does not hinge on the exact value. It also sets β ≈ 0.96 in the MIP.

**Q21b. Does the greedy heuristic apply the constraints?**
Yes, with one gap. It keeps moves legal (one edge, no storm-closed zones or enemy ports, endurance), places forced returns first, and respects the movement budget. Here is how it chooses. (1) Start from "every free ship stays, all zones patrol". (2) For each ship in random order, try every legal destination. Reject any that exceeds the movement budget or that is both over ε and riskier. Take the biggest gain in score. (3) In each zone, pick patrol or assert by score, allowing assert only if total risk stays ≤ ε. (4) Repeat up to 3 more rounds until nothing changes. It is fast but can stop at a good plan rather than the best one. **The gap.** If the starting plan is already over the risk budget, greedy refuses anything that adds risk but never gives up value to get back under it. That is its 14% overrun rate, 208 of 1,524 decisions. A rerun found every overrun started over budget and never got worse. The MIP will give up value to get under the budget, so its only overruns (37) come from forced returns that leave no choice.

**Q22. How do you know the MIP solutions are right?**
Gurobi solves it exactly. We compared it to the greedy heuristic over 1,524 Blue decisions. They agreed 67% of the time, but greedy broke the risk budget 14% of the time. That is why the exact MIP matters even though both play about the same.

**Q23. How does the template game relate to the full game?**
If both sides held a template, control would settle at c = φ. Template payoffs are that settled control minus incident cost, in calm seas at ℓ = 1. It is an approximation used to compute equilibria. The simulations then test those plans in the full game.

**Q22a. What is IESDS?**
Iterated elimination of strictly dominated strategies. Cross out any template that another template beats against every opponent choice. Then repeat, since each removal can make new templates dominated. Every Nash equilibrium lies in what survives. In our template game it cuts 14 × 14 down to 2 × 4. Blue keeps only center-heavy (20/60/20, patrol or assert). Red keeps south-heavy (20/20/60) and center/south (20/40/40), each with patrol or assert. That is why the slide 6 example fixes Blue center-heavy and Red south-heavy and varies only the posture.

**Q22b. Is slide 6 / §4.1 analytical or simulated?**
Analytical. The template game's payoffs come from the settled-control formula in calm seas at ℓ = 1, with no randomness. Dominance elimination and the pure equilibria come from enumeration. Maximin and the correlated equilibrium come from LPs. The mixed equilibrium comes from indifference equations, and the restraint threshold from a closed form. Only §4.2 to §4.4 (RQ1 to RQ3) are simulations, with 60 periods and 200 simulated games each. Present §4.1 as an illustration of the structure. Its numbers use fractional hulls, and the whole-ship check gives a single equilibrium (Q23a).

**Q22c. What is the zero-sum check in §4.1?**
Drop the shared incident cost and the game becomes zero-sum, with Red getting minus Blue's control score. Then assert only adds strength, so it dominates. The maximin LP has a pure saddle point. Both sides concentrate on the Center (20/60/20) and assert, with value −2.26 for Blue. The Center holds the value, since Taiwan Strait is worth 10 to each side. Restore the shared incident cost and mutual assertion becomes costly. Each pure equilibrium then has exactly one side asserting, and Red shifts South. The takeaway is that shared risk produces restraint.

**Q22d. How do you get the mixed and correlated equilibria on slide 6?**
*Mixed equilibrium.* Each side randomizes to make the other indifferent. If Red asserts with probability q, Blue's payoff from patrol is −9.61q and from assert 0.28(1 − q) − 11.41q. Setting them equal gives q = 0.28/2.08 ≈ 0.13. The same for Red gives Blue asserting with p = 1.20/2.08 ≈ 0.58. Payoffs are −1.30 for Blue and −6.02 for Red, and both assert about 8% of the time. The restraint thresholds use these. They are 0.18 for Blue and 0.17 for Red.
*Correlated equilibrium (LP).* A referee draws a cell with probability π and tells each side only its own posture. The LP maximizes total payoff subject to four "obey your recommendation" constraints. For example, for Red told P, −10.45·π(AP) ≥ 1.20·π(PP) − 11.33·π(AP). The solution is π(PP) = 0.40, π(AP) = 0.54, π(PA) = 0.06, π(AA) = 0, with payoffs (−0.45, −5.57). That is better for both sides than the mixed equilibrium.

**Q23a. The template game uses fractional hulls. Isn't that unrealistic?**
Yes. It is a known simplification. Templates spread 70% of each fleet evenly over a region's zones, which can leave fractions of a ship in a zone. The full simulation always moves whole ships, but the template game sets which plan the Nash equilibrium and Safety-first policies play. We ran a quick whole-ship check that is not in the paper, rounding to Blue 7 DDG and Red 6 PLAN + 4 CCG. It changes which side asserts in equilibrium. Dominance leaves a single pure equilibrium, Blue center-heavy patrol vs. Red south-heavy assert, instead of the paper's two. So removing fractional hulls is first on our Workshop 2 list.

**Q24. The template game has two pure equilibria. Which do you play?**
The one with higher total payoff, Blue center-heavy assert vs Red south-heavy patrol. That selection is an assumption, stated in the paper.

**Q25. Why does the maximin plan do poorly?**
It guards against Red's worst-case template, which Red rarely plays, so it gives up control. It is the safest (war ≤ 8%) but scores lowest among the strategic plans.

### D. Results

**★ Q26. Slide 6 says restraint is an equilibrium, but RQ1 says both go aggressive. Which is it?**
They are different games. Slide 6 is the repeated game. Patient players can sustain mutual patrol with a standing threat, for any δ above 0.18. The course term for this strategy is grim trigger. The punishment after an assertion is both playing the mixed equilibrium forever, not both asserting forever. RQ1's budget game is a one-shot choice of budget by policies that look one turn ahead. There aggressive is the best reply to every budget, so both end up aggressive, with payoffs (−151, 39) and war 34%. Both would be better off at moderate–moderate, with payoffs (−144, 101) and war 20%. That is a prisoner's dilemma. The gap between the two games is the case for coordination devices and for multi-period policies in Workshop 2.

**Q26a. In Table 3, does "moderate" mean the rule-of-thumb commander?**
No. In Table 3 the labels conservative, moderate and aggressive mean the MIP best response with risk budget ε = 0.05, 0.15 and 0.40. The rule-of-thumb policy also uses ε = 0.15 and is called the moderate commander in the paper, but it is a different policy and does not appear in Table 3.

**Q26b. Is all of §4.2 run with the MIP best response?**
Yes. Both experiments are MIP best response against MIP best response, with no redesign, nominal weather and 200 simulated games each. The frontier fixes Red at ε = 0.15 and runs Blue's ε over 0.02, 0.05, 0.10, 0.15, 0.25 and 0.40. The risk-budget game is a 3 × 3 game built from simulated payoffs, with ε of 0.05, 0.15 or 0.40 for each side.

**Q27. Why is slide 6 an anti-coordination game and not a prisoner's dilemma?**
With force splits fixed, asserting against a patroller pays, but asserting against an asserter is worse than backing off. The best reply is the opposite of the other side, which is an anti-coordination structure. In the budget game a looser budget also changes deployment, and it pays against everything.

**★ Q28. A 34% war rate is not realistic.**
Agreed. It is not a forecast. We tuned hazards so war is uncommon but not rare in a four-month game, so differences between strategies show up. What we report is relative, meaning which choices raise or lower war risk. We also flag that W = 200 may be too small, since the top-scoring policy has the most wars.

**Q29. Why are Blue's payoffs negative almost everywhere?**
Red has more hulls, starts with control in the South, and values the South more. Both also pay tension costs every period plus the war penalty. Compare rows, not signs.

**★ Q30a. What do you measure, and what does "averaged over 200 simulated games per setup" mean?**
We measure four outcomes. The first is Blue's control share, which is zone control weighted by value to Blue and averaged over the game (+1 all Blue, −1 all Red, 0 even). The second is the war rate, the share of games reaching level 5. The third is each side's total payoff. The fourth, for RQ3, is the average and worst payoff over the weather scenarios. A seed is the starting number for the random draws, such as detections, incidents and storms. Each setup is played as 200 simulated games with different luck, and we average them. Every setup uses the same seeds 0 to 199, so compared policies face identical luck.

**Q30c. Are the games pseudorandom and seeded? Can you reproduce them?**
Yes. Each game uses Python's `random.Random` (Mersenne Twister) seeded with the game number, 0 to 199, so every run is reproducible. Weather has its own random stream, seeded 10007 × seed + 17. So policies compared on the same seed face identical storms and sea states even when they move differently. This is called common random numbers. Uncertainty is reported as the standard error s/√n. (Code is in `prototype/wargame_gui.py`, `Game.__init__`.)

**Q30b. Why 200 simulated games?**
200 simulated games per setup was a practical choice for this stage. We haven't yet done a formal check of how many games are needed. That is on our Workshop 2 list.

**Q30. Are the differences significant?**
Standard errors of the averages are 5 to 12 payoff points. We treat differences under about 20 points as ties, and the slides say so.

**★ Q31. Why does the Nash plan beat the MIP best response?**
This is our reading, not yet tested separately. The MIP best response looks one turn ahead and reacts to last-seen beliefs, so it escalates more (20% war vs 10%). The Nash plan commits to a center-heavy split and backs off to patrol when tension passes ℓ = 3. Its worst case over Red's policies is the best, −116.

**★ Q32. De-escalation measures (D3) are free. Isn't their win built in?**
Partly, yes, and we say so. It also raises Red's payoff (101 to 144) because fewer wars help both. Workshop 2 prices it. The result is still informative. D3 is a real-world version of the mediator from the correlated-equilibrium example.

**Q32a. Why call D3 "de-escalation measures"?**
It does two things. Once ℓ ≥ 3, a quiet period lowers ℓ with probability 0.5 instead of 0.25. That is the hotline-like part, like the U.S.-China Defense Telephone Link set up in 2008. And assert hazards are halved. That is the CUES-like part, meaning agreed encounter rules and bridge-to-bridge communication. It is bilateral and helps Red too, so "de-escalation measures" covers both effects. The slide 7 screenshot was taken before the rename, so it may still show "Crisis hotline". It is the same design.

**Q32b. Is Subic Bay an EDCA site?**
No. EDCA is the 2014 U.S.-Philippines Enhanced Defense Cooperation Agreement. Its first five sites are Antonio Bautista Air Base, Basa Air Base, Fort Magsaysay, Lumbia Air Base and Benito Ebuen Air Base. Four more were added in April 2023. They are Lal-lo airfield, Naval Base Camilo Osias, Camp Melchor Dela Cruz and Balabac Island (RFA). The U.S. does use Subic's port and airfield, and the Marines preposition equipment there. In 2025 the Navy sought a leased storage facility there (USNI News). D1 is a hypothetical full home port at Subic.

**Q33. Why does the extra port (D1) hurt Red but not help Blue much?**
Shorter trips to the South let Blue contest Red's valuable southern zones, which costs Red (101 to 16). But more contact means more incidents (war 28%), which eats Blue's gain.

### E. Prototype and plan

**Q34. How does the code match the model?**
`Game.step` is the 7-step timeline with the control, hazard and payoff equations. `MIPBRPolicy` builds and solves the MIP each turn. `MetaGame` builds the template game and runs dominance, Nash enumeration and both LPs. `experiments.py all` regenerates every number in the report.

**Q35. What will learning add?**
In Workshop 2 we add learning agents, such as a Red that adapts over repeated play. The question is whether they converge or cycle, drift toward restraint or assertion, and exploit predictable Blue play. Say "other learning methods" as the paper does. Name fictitious play or no-regret learning only if asked which ones. (Present these only as plans. We have not built them yet.)

**Q36. What attacks will you test?**
Three are already coded. In the blockade, Blue cannot pass through Scarborough or Second Thomas while Red's coast guard asserts there. In jamming, Blue's detection is halved in one region from period 20 to 40. In deception, Blue sees 2 phantom contacts each period. The defenses are randomized patrols, D1 and D2.

**Q36a. Did you use AI tools?**
Yes, and the paper says how in the AI-usage statement after the references. Point to it.

### F. Real-world grounding (cite if pressed; see Part 4)

**Q37. Is this behavior real?**
Yes, in kind. China uses coast guard and maritime militia to keep presence and obstruct others while trying to avoid a military response (Helmus et al. 2024). PLAN ships have made unsafe close maneuvers near U.S. destroyers. USS Decatur was approached near Gaven Reef in September 2018, and USS Chung-Hoon in the Taiwan Strait in June 2023. The U.S. conducts freedom-of-navigation operations against excessive maritime claims and reports them yearly. Encounters between navies are meant to follow CUES (2014).

**Q38. How is this different from existing gray-zone games or patrol models?**
Wasser et al. (2019) built a structured gray-zone game with explicit objectives and probabilistic adjudication. We automate every rule, so thousands of runs can compare strategies. PROTECT (Shieh et al. 2012) is a deployed leader-follower model for Coast Guard port patrols. Washburn and Wood (1995) model network interdiction as a two-person zero-sum game. Ours is general-sum with simultaneous moves. Both sides contest control, and war costs both. The incident hazard follows Schelling's (1966) idea of escalation as a shared risk that each side manipulates.

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
- Radio Free Asia (Aug 2023). Philippines EDCA sites. https://www.rfa.org/english/news/southchinasea/philippines-bases-08032023134505.html
- USNI News (Sept 23, 2025). U.S. Navy wants to open Subic Bay storage facility in the Philippines. https://news.usni.org/2025/09/23/u-s-navy-wants-to-open-subic-bay-storage-facility-in-the-philippines
- U.S. Indo-Pacific Command (2024). DoD releases Fiscal Year 2023 Freedom of Navigation Report. https://www.pacom.mil/Media/News/Spotlight/Article/3771243/dod-releases-fiscal-year-2023-freedom-of-navigation-report/
