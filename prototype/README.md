# Prototype: gray-zone maritime control wargame

Python 3.10+. The simulator uses only the standard library. Three things need extra packages:

| Needs | For |
|---|---|
| `gurobipy` (`pip install gurobipy`; the free size-limited license is enough) | the exact best-response MIP (`mip_br`), the `maximin` policy, and the LP parts of `--equilibrium` |
| `matplotlib` | figures (`experiments.py`, `snapshot.py`) |
| `tkinter` | the GUI only (python.org Python on macOS includes it; Homebrew needs `brew install python-tk`) |

## Quick start

```
python3 wargame_gui.py                                   # GUI
python3 wargame_gui.py --trace --blue mip_br --red mip_br --weather typhoon --seed 4 --T 10
python3 wargame_gui.py --batch --blue mip_br --red mip_br --weather nominal --seeds 200
python3 wargame_gui.py --batch --blue mip_br --red mip_br --epsB 0.40 --epsR 0.15 --seeds 200
python3 wargame_gui.py --equilibrium                     # template game: dominance, pure NE, maximin LP, CE LP
python3 experiments.py all                               # every table and figure in the Workshop 1 report
python3 snapshot.py --seed 4                             # map snapshots used in the report
```

`experiments.py all` takes about 20 minutes on 4 cores (`SEEDS=50 python3 experiments.py all` for a quick look).
Outputs go to `results/` (CSV and markdown tables) and `results/figures/`.

## Options

| Option | Values |
|---|---|
| `--blue`, `--red` | `random` (benchmark), `conservative` / `moderate` / `aggressive` (rule-based), `greedy_br` (heuristic for the MIP), `mip_br` (exact MIP best response), `equilibrium` (pure Nash equilibrium of the template game), `maximin` (maximin mixed strategy of the template game) |
| `--epsB`, `--epsR` | escalation-risk budget of `greedy_br` / `mip_br` (expected incidents per period; default 0.15). Conservative / moderate / aggressive = 0.05 / 0.15 / 0.40 |
| `--weather` | `calm`, `nominal`, `typhoon`, `extreme` (scenario omega: storm and rough-sea frequencies) |
| `--design` | `D0` baseline, `D1` dispersed basing (Subic/EDCA port), `D2` redundant sensing, `D3` crisis hotline |
| `--attacks` | `jamming`, `blockade`, `deception` (implemented for Workshop 2; not used in the Workshop 1 results) |
| `--seed`, `--seeds`, `--T` | first seed, number of seeds, horizon in periods (1 period = 2 days, default 60) |

## GUI

`python3 wargame_gui.py` opens the game. Press **Help** for a one-screen explanation.

1. On the right, pick a plan for each side, Blue's design, and the weather (plain-language names; the
   command-line names are in brackets below), then press **New game**.
2. **Step** plays one turn (2 days); **Play** animates the game; **Run many games** plays the same settings
   over many random seeds and reports average scores and how often the game ends in war.
3. Map: circle color and number = who controls each contested water (-1 fully Red, +1 fully Blue);
   B = Blue destroyers, P = Red navy, C = Red coast guard; thick outline = that side is asserting;
   orange ring = incident; grey box = storm, light box = rough sea. **Blue view** / **Red view** show what each
   side believes about the other's ships (`~n[a]` = n ships last seen a turns ago).
4. Bottom left: the escalation ladder (0 peace to 5 war) and the history of Blue control and escalation.

Plan names: Random moves (`random`), Rule of thumb: cautious / balanced / bold (`conservative` / `moderate` /
`aggressive`), Quick best response (`greedy_br`), Best response (`mip_br`), Nash equilibrium plan
(`equilibrium`), Safety-first plan (`maximin`). Designs: D0 Baseline, D1 Extra port in Philippines,
D2 Extra surveillance, D3 Crisis hotline. Weather: Calm seas, Normal season, Typhoon season, Extreme weather
(`calm`, `nominal`, `typhoon`, `extreme`).

## Where things are in `wargame_gui.py`

1 parameters and weather scenarios, 2 graph, 3 dynamics helpers (strength, hazard, node evaluation),
4 observations, 5 game engine (`Game.step` is the sequence of play), 6 policies (rule-based, greedy, `MIPBRPolicy`),
7 template game (`MetaGame`: best responses, dominance, pure NE, maximin LP, CE LP) and template policies,
8 batch runs and reports, 9 command line, 10 GUI.
