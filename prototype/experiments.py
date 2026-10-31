#!/usr/bin/env python3
"""
experiments.py -- every number, table and figure in the Workshop 1 report.

    python3 experiments.py all          # everything (about 15 minutes on 4 cores)
    python3 experiments.py chicken      # Section 4.1: local 2x2 posture game
    python3 experiments.py template     # Section 4.2: template game (dominance, NE, LPs)
    python3 experiments.py gap          # Section 4.3: greedy heuristic vs exact MIP
    python3 experiments.py frontier     # RQ1: control vs war-risk frontier over eps_B
    python3 experiments.py riskgame     # RQ1: the 3x3 risk-budget game
    python3 experiments.py policies     # RQ2: policy comparison
    python3 experiments.py weather      # RQ3: robustness to weather scenarios
    python3 experiments.py designs      # RQ3: resilient designs under weather
    python3 experiments.py seedcheck    # Workshop 2: how many games each comparison needs
    python3 experiments.py mipcheck     # Workshop 2: flow MIP vs Workshop 1 MIP on the Workshop 1 fleet

Results are written to results/ (CSV + markdown) and figures to results/figures/.
Every configuration is run on the same seeds 0..SEEDS-1, and Nature's weather
draws use a separate random stream, so all policies face identical weather
sequences (common random numbers).  Uncertainty is reported as the standard
error s/sqrt(n).
"""

import csv
import math
import os
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

import wargame_gui as wg

SEEDS = int(os.environ.get('SEEDS', 200))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get('RESULTS', 'results'))   # RESULTS=results_w2 for Workshop 2 runs
FIG = os.path.join(OUT, 'figures')
EPS_GRID = [0.02, 0.05, 0.10, 0.15, 0.25, 0.40]
TYPES = {'conservative': 0.05, 'moderate': 0.15, 'aggressive': 0.40}


# Every finished game is stored in OUT/games/*.csv, one row per (configuration, seed), so a
# configuration is played only once, and games can be played elsewhere (for example as
# cluster jobs, see `worker` below) and summarized here.
GAMES = os.path.join(OUT, 'games')
GAME_KEY = ['blue', 'red', 'design', 'weather', 'epsB', 'epsR', 'seed']
GAME_COLS = ['blue_payoff', 'red_payoff', 'control_share', 'war', 'war_t', 'max_ell', 'mean_ell', 'incidents',
             'blue_fuel', 'red_fuel']


def _key(blue, red, design, weather, epsB, epsR, seed):
    return (blue, red, design, weather, f'{float(epsB):g}', f'{float(epsR):g}', int(seed))


def load_games():
    store = {}
    if os.path.isdir(GAMES):
        for fn in sorted(os.listdir(GAMES)):
            if fn.endswith('.csv'):
                with open(os.path.join(GAMES, fn), newline='') as f:
                    for r in csv.DictReader(f):
                        store[_key(*(r[k] for k in GAME_KEY))] = {c: float(r[c]) for c in GAME_COLS}
    return store


def play_game(blue, red, design, weather, epsB, epsR, seed, out_file):
    """Play one game and append its row to out_file."""
    m = wg.Game(blue, red, design, (), seed=seed, weather=weather,
                params={'eps': {'B': epsB, 'R': epsR}}).run().metrics()
    os.makedirs(GAMES, exist_ok=True)
    new = not os.path.exists(out_file)
    with open(out_file, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(GAME_KEY + GAME_COLS)
        w.writerow([blue, red, design, weather, epsB, epsR, seed] + [m[c] for c in GAME_COLS])
    return m


def _run(job):
    """Worker: one configuration -> summary dict (stored games are reused)."""
    tag, blue, red, design, weather, epsB, epsR = job
    store = load_games()
    rows = []
    for seed in range(SEEDS):
        r = store.get(_key(blue, red, design, weather, epsB, epsR, seed))
        if r is None:
            r = play_game(blue, red, design, weather, epsB, epsR, seed,
                          os.path.join(GAMES, f'local_{os.getpid()}.csv'))
        rows.append(r)
    s = wg.summarize(rows, blue, red, design, ())
    s.update(tag=tag, epsB=epsB, epsR=epsR, weather=weather)
    return s


def run_jobs(jobs, name):
    t0 = time.time()
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        res = pool.map(_run, jobs)
    os.makedirs(OUT, exist_ok=True)
    cols = ['tag', 'epsB', 'epsR'] + wg.SUMMARY_COLS
    with open(os.path.join(OUT, f'{name}.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for s in res:
            w.writerow({k: s.get(k) for k in cols})
    print(f"[{name}] {len(jobs)} configurations x {SEEDS} seeds in {time.time() - t0:.0f}s")
    return res


def md(rows, header):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    out += ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]
    return '\n'.join(out)


def write_md(name, text):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'{name}.md'), 'w') as f:
        f.write(text + '\n')
    print(text)


def pm(s, key='blue_mean', se='blue_se', fmt='.1f'):
    return f"{s[key]:{fmt}} ± {s[se]:{fmt}}"


# ---------------------------------------------------------------------------
# Section 4.1: a 2x2 posture game cut out of the template game
# ---------------------------------------------------------------------------
def chicken():
    """Fix the force splits that survive iterated elimination of strictly
    dominated strategies (Blue center-heavy N20C60S20, Red south-heavy
    N20C20S60) and let each side choose only its posture, P or A.  This 2x2 is
    a sub-matrix of the template game M_B, M_R."""
    import gurobipy as gp
    mg = wg.get_meta_game()
    ib = {p: wg.TEMPLATE_LABELS.index(f'N20C60S20-{p}') for p in 'PA'}
    ir = {p: wg.TEMPLATE_LABELS.index(f'N20C20S60-{p}') for p in 'PA'}
    U = {(pb, pr): (mg.MB[ib[pb]][ir[pr]], mg.MR[ib[pb]][ir[pr]]) for pb in 'PA' for pr in 'PA'}
    base = U['P', 'P']
    N = {k: (U[k][0] - base[0], U[k][1] - base[1]) for k in U}
    GB, LB, KB = N['A', 'P'][0], -N['P', 'A'][0], -N['A', 'A'][0]
    GR, LR, KR = N['P', 'A'][1], -N['A', 'P'][1], -N['A', 'A'][1]
    # mixed NE: Blue indifferent between P and A given Red asserts w.p. qR:
    #   -LB qR = GB (1 - qR) - KB qR   =>   qR = GB / (GB + KB - LB)
    qR = GB / (GB + KB - LB)
    qB = GR / (GR + KR - LR)
    vB, vR = -LB * qR, -LR * qB
    # grim trigger: play (P,P); after any assertion revert forever to the mixed NE.
    # One-stage deviation: (1 - d) G + d v <= 0   <=>   d >= G / (G - v)
    dB, dR = GB / (GB - vB), GR / (GR - vR)
    # welfare-maximizing correlated equilibrium of the 2x2 (CE LP)
    m = gp.Model(env=wg.MIPBRPolicy.env())
    pi = {k: m.addVar(lb=0) for k in N}
    m.addConstr(gp.quicksum(pi.values()) == 1)
    for a in 'PA':
        for a2 in 'PA':
            if a2 != a:
                m.addConstr(gp.quicksum(pi[a, b] * (N[a, b][0] - N[a2, b][0]) for b in 'PA') >= 0)
                m.addConstr(gp.quicksum(pi[b, a] * (N[b, a][1] - N[b, a2][1]) for b in 'PA') >= 0)
    m.setObjective(gp.quicksum(pi[k] * (N[k][0] + N[k][1]) for k in N), gp.GRB.MAXIMIZE)
    m.optimize()
    ce = {k: pi[k].X for k in N}
    ceB = sum(ce[k] * N[k][0] for k in N)
    ceR = sum(ce[k] * N[k][1] for k in N)
    f = lambda x: f"({x[0]:.2f}, {x[1]:.2f})"
    lines = [
        "Posture game: Blue center-heavy (N20C60S20), Red south-heavy (N20C20S60), each chooses P or A.",
        f"Raw payoffs (u_B, u_R): (P,P) {f(U['P','P'])}, (P,A) {f(U['P','A'])}, (A,P) {f(U['A','P'])}, (A,A) {f(U['A','A'])}",
        "Normalized so that (P,P) = (0,0):",
        "",
        md([['P', f(N['P', 'P']), f(N['P', 'A'])], ['A', f(N['A', 'P']), f(N['A', 'A'])]], ['Blue \\ Red', 'P', 'A']),
        "",
        f"Blue: G = {GB:.2f} (gain from asserting alone), L = {LB:.2f} (loss when only Red asserts), K = {KB:.2f} (loss when both assert)",
        f"Red:  G = {GR:.2f}, L = {LR:.2f}, K = {KR:.2f}",
        f"Chicken: BR(P) = A because G > 0; BR(A) = P because K > L.  Pure NE: (A,P) and (P,A).",
        f"Mixed NE: Blue asserts w.p. {qB:.3f}, Red w.p. {qR:.3f}; payoffs ({vB:.2f}, {vR:.2f}); both assert w.p. {qB * qR:.4f}",
        f"Welfare-maximizing CE: pi(P,P) = {ce['P','P']:.3f}, pi(A,P) = {ce['A','P']:.3f}, pi(P,A) = {ce['P','A']:.3f},"
        f" pi(A,A) = {ce['A','A']:.3f}; payoffs ({ceB:.2f}, {ceR:.2f})",
        f"Grim trigger (revert to the mixed NE) sustains (P,P) iff delta >= G/(G - v): Blue {dB:.3f}, Red {dR:.3f}"
        f" (model delta = {wg.PARAMS['delta']})",
    ]
    write_md('chicken', '\n'.join(lines))





# ---------------------------------------------------------------------------
# Section 4.2: template game
# ---------------------------------------------------------------------------
def template():
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        wg.print_equilibrium()
    write_md('template_game', '```\n' + buf.getvalue() + '```')


# ---------------------------------------------------------------------------
# Section 4.3: greedy heuristic vs exact MIP (optimality gap)
# ---------------------------------------------------------------------------
def gap(n_games=30):
    """At every Blue decision in n_games of mip_br vs mip_br (nominal weather),
    compare the objective of the greedy plan with the MIP optimum on the same
    observation (both evaluated with wg.plan_value)."""
    rows = []
    for seed in range(n_games):
        gm = wg.Game('mip_br', 'mip_br', 'D0', (), seed=seed, weather='nominal')
        greedy = wg.GreedyBRPolicy('B', gm.rng.__class__(seed))
        orig_act = gm.policy['B'].act

        def act(obs, orig_act=orig_act, greedy=greedy):
            m_mv, m_po = orig_act(obs)
            g_mv, g_po = greedy.act(obs)
            Jm, rm = wg.plan_value(obs, m_mv, m_po)
            Jg, rg = wg.plan_value(obs, g_mv, g_po)
            rows.append((Jm, Jg, rm, rg, wg.risk_budget(obs.P['eps']['B'], obs.ell, obs.P)))
            return m_mv, m_po
        gm.policy['B'].act = act
        gm.run()
    n = len(rows)
    diffs = [jm - jg for jm, jg, *_ in rows]
    rel = sum(diffs) / sum(abs(jm) for jm, *_ in rows)
    within = [(jm, jg) for jm, jg, rm, rg, e in rows if rg <= e + 1e-9]
    loss_within = [jm - jg for jm, jg in within]
    opt = sum(1 for d in diffs if d <= 1e-6)
    viol_g = sum(1 for *_, rg, e in rows if rg > e + 1e-9)
    viol_m = sum(1 for _, _, rm, _, e in rows if rm > e + 1e-9)
    neg = sum(1 for d in diffs if d < -1e-6)
    lines = [
        f"Greedy heuristic vs exact MIP, {n} Blue decisions in {n_games} games (mip_br vs mip_br, nominal weather):",
        f"  greedy plan optimal (within 1e-6) in {opt}/{n} decisions ({100 * opt / n:.0f}%)",
        f"  mean objective loss {sum(diffs) / n:.3f} (total loss / total |MIP objective| = {100 * rel:.1f}%), max {max(diffs):.3f}",
        f"  among the {len(within)} greedy plans that respect the risk budget: mean loss {sum(loss_within) / len(within):.3f},"
        f" greedy optimal in {sum(1 for d in loss_within if d <= 1e-6)}",
        f"  risk-budget violations: greedy {viol_g}/{n}, MIP {viol_m}/{n} (MIP only when forced returns alone exceed eps)",
        f"  decisions where greedy scored higher than the MIP: {neg} (it can only do so by exceeding the risk budget)",
    ]
    write_md('gap', '\n'.join(lines))


# ---------------------------------------------------------------------------
# RQ1: frontier and risk-budget game
# ---------------------------------------------------------------------------
def frontier():
    jobs = jobs_of('frontier')
    res = run_jobs(jobs, 'frontier')
    rows = [[f"{s['epsB']:.2f}", f"{s['control_share']:+.3f} ± {s['control_se']:.3f}",
             f"{s['war_rate']:.2f} ± {s['war_se']:.2f}", pm(s), pm(s, 'red_mean', 'red_se'), f"{s['incidents']:.1f}"]
            for s in res]
    write_md('frontier', "RQ1 frontier: Blue mip_br with risk budget eps_B vs Red mip_br (eps_R = 0.15), nominal weather\n\n"
             + md(rows, ['eps_B', 'Blue control share', 'War rate', 'u_B', 'u_R', 'Incidents']))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        os.makedirs(FIG, exist_ok=True)
        fig, ax = plt.subplots(figsize=(4.6, 3.2))
        x = [s['war_rate'] for s in res]
        y = [s['control_share'] for s in res]
        ax.errorbar(x, y, xerr=[s['war_se'] for s in res], yerr=[s['control_se'] for s in res],
                    fmt='o-', color='#1f4e9c', capsize=2, lw=1.5)
        for s in res:
            ax.annotate(f"ε_B={s['epsB']:.2f}", (s['war_rate'], s['control_share']), textcoords='offset points',
                        xytext=(5, -10), fontsize=7)
        ax.set_xlabel('War rate (fraction of 60-period games)')
        ax.set_ylabel('Blue value-weighted control share')
        ax.grid(alpha=0.3)
        ax.set_title('Control vs. war risk as Blue relaxes its risk budget', fontsize=9)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, 'frontier.pdf'))
        fig.savefig(os.path.join(FIG, 'frontier.png'), dpi=200)
    except ImportError:
        print("matplotlib not installed: figure skipped")


def riskgame():
    jobs = jobs_of('riskgame')
    res = run_jobs(jobs, 'riskgame')
    names = list(TYPES)
    M = {(s['epsB'], s['epsR']): s for s in res}
    e = list(TYPES.values())
    # pure NE by best responses on the estimated payoffs
    ne = []
    for a in e:
        for b in e:
            if M[a, b]['blue_mean'] >= max(M[a2, b]['blue_mean'] for a2 in e) and \
               M[a, b]['red_mean'] >= max(M[a, b2]['red_mean'] for b2 in e):
                ne.append((a, b))
    best_total = max(M, key=lambda k: M[k]['blue_mean'] + M[k]['red_mean'])
    rows = []
    for a, na in zip(e, names):
        rows.append([f"{na} ({a})"] + [f"{M[a, b]['blue_mean']:.0f}, {M[a, b]['red_mean']:.0f} [war {M[a, b]['war_rate']:.2f}]"
                                       for b in e])
    lab = {v: k for k, v in TYPES.items()}
    text = ("RQ1 risk-budget game: both players use mip_br; entries (u_B, u_R) [war rate], nominal weather\n\n"
            + md(rows, ['Blue \\ Red'] + [f"{n} ({v})" for n, v in TYPES.items()])
            + "\n\nPure NE (mutual best responses on the estimated payoffs; s.e. of each payoff about "
            + f"{max(max(s['blue_se'], s['red_se']) for s in res):.0f}): "
            + (', '.join(f"(Blue {lab[a]}, Red {lab[b]})" for a, b in ne) or 'none')
            + f"\nHighest total payoff: (Blue {lab[best_total[0]]}, Red {lab[best_total[1]]})")
    write_md('riskgame', text)


# ---------------------------------------------------------------------------
# RQ2: policy comparison
# ---------------------------------------------------------------------------
BLUE_POLICIES = ['random', 'moderate', 'greedy_br', 'mip_br', 'equilibrium', 'maximin']
RED_POLICIES = ['moderate', 'mip_br', 'equilibrium']


def policies():
    jobs = jobs_of('policies')
    res = run_jobs(jobs, 'policies')
    M = {(s['blue'], s['red']): s for s in res}
    rows = []
    for b in BLUE_POLICIES:
        rows.append([b] + [f"{M[b, r]['blue_mean']:.0f} ± {M[b, r]['blue_se']:.0f} / {M[b, r]['control_share']:+.2f} / "
                           f"{M[b, r]['war_rate']:.2f}" for r in RED_POLICIES]
                    + [f"{min(M[b, r]['blue_mean'] for r in RED_POLICIES):.0f}"])
    write_md('policies', "RQ2 policy comparison, nominal weather. Entry: u_B ± s.e. / control share / war rate\n\n"
             + md(rows, ['Blue \\ Red'] + RED_POLICIES + ['worst case over Red']))


# ---------------------------------------------------------------------------
# RQ3: robustness to weather, and resilient designs
# ---------------------------------------------------------------------------
WX_BLUE = [('moderate', 0.15), ('greedy_br', 0.15), ('mip_br', 0.05), ('mip_br', 0.15), ('mip_br', 0.40),
           ('equilibrium', 0.15), ('maximin', 0.15)]


def load(name):
    """Read a results CSV back as a list of dicts with numeric fields converted."""
    rows = []
    with open(os.path.join(OUT, f'{name}.csv')) as f:
        for r in csv.DictReader(f):
            for k, v in r.items():
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
            rows.append(r)
    return rows


def weather(run=True):
    if run:
        jobs = jobs_of('weather')
        run_jobs(jobs, 'weather')
    res = load('weather')
    M = {(s['blue'], s['epsB'], s['weather']): s for s in res}
    W = list(wg.WEATHER)
    pi = {w: wg.WEATHER[w]['pi'] for w in W}
    rows, stats = [], []
    for b, e in WX_BLUE:
        J = {w: M[b, e, w]['blue_mean'] for w in W}
        JR = {w: M[b, e, w]['red_mean'] for w in W}
        exp = sum(pi[w] * J[w] for w in W)
        worst_w = min(W, key=J.get)
        label = f"{b} (ε={e})" if b in ('mip_br', 'greedy_br') else b
        stats.append((label, J, exp, J[worst_w]))
        rows.append([label] + [f"{J[w]:.0f} / {JR[w]:.0f} / {M[b, e, w]['war_rate']:.2f}" for w in W]
                    + [f"{exp:.0f}", f"{J[worst_w]:.0f} ({worst_w})"])
    ranks = {w: [x[0] for x in sorted(stats, key=lambda x: -x[1][w])] for w in W}
    same = all(ranks[w] == ranks[W[0]] for w in W)
    text = ("RQ3 robustness to weather: Blue policy vs Red mip_br (ε_R = 0.15), design D0. Entry: u_B / u_R / war rate. "
            f"Scenario weights pi = {pi}. s.e. of u_B about {max(s['blue_se'] for s in res):.0f}\n\n"
            + md(rows, ['Blue policy'] + W + ['Blue expected (Σ π_ω J)', 'Blue worst case (min_ω J)'])
            + "\n\nRanking of Blue policies by u_B in each scenario:\n"
            + '\n'.join(f"  {w}: " + ' > '.join(r) for w, r in ranks.items())
            + f"\nRanking identical in every scenario: {same}")
    write_md('weather', text)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        os.makedirs(FIG, exist_ok=True)
        fig, ax = plt.subplots(figsize=(4.8, 3.2))
        xs = list(range(len(W)))
        names = {'moderate': 'rule-based', 'greedy_br': 'greedy', 'mip_br': 'MIP-BR',
                 'equilibrium': 'equilibrium', 'maximin': 'maximin'}
        for (b, e), (label, J, _, _) in zip(WX_BLUE, stats):
            name = f"{names[b]} (ε={e:g})" if b == 'mip_br' else names[b]
            ax.plot(xs, [J[w] for w in W], 'o-', label=name, lw=1.5, ms=3.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(['calm', 'normal', 'typhoon', 'extreme'])
        ax.set_xlabel('Weather scenario (more storms and rough seas →)')
        ax.set_ylabel('Blue payoff $u_B$ (higher is better)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7.5, ncol=2, loc='lower right')
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, 'weather.pdf'))
        fig.savefig(os.path.join(FIG, 'weather.png'), dpi=200)
    except ImportError:
        pass


def designs():
    jobs = jobs_of('designs')
    res = run_jobs(jobs, 'designs')
    M = {(s['design'], s['weather']): s for s in res}
    pi = {w: wg.WEATHER[w]['pi'] for w in wg.WEATHER}
    rows = []
    for d in wg.DESIGNS:
        J = {w: M[d, w]['blue_mean'] for w in wg.WEATHER}
        rows.append([d] + [f"{J[w]:.0f} / {M[d, w]['war_rate']:.2f}" for w in wg.WEATHER]
                    + [f"{sum(pi[w] * J[w] for w in J):.0f}", f"{min(J.values()):.0f}"])
    write_md('designs', "RQ3 resilient designs: Blue mip_br vs Red mip_br (ε = 0.15 each). Entry: u_B / war rate. "
             f"s.e. of u_B about {max(s['blue_se'] for s in res):.0f}\n\n"
             + md(rows, ['Design'] + list(wg.WEATHER) + ['expected', 'worst case']))


# ---------------------------------------------------------------------------
# Workshop 2: how many simulated games are enough
# ---------------------------------------------------------------------------
# Each pair is (label, setup A, setup B) with setup = (blue, red, design, weather).
# Both setups use the same seeds and weather draws, so the comparison uses the
# per-game difference d_k = u_B(A, k) - u_B(B, k).  Its standard error is
# s_d / sqrt(n).  To tell the two apart at about 95% confidence the mean
# difference must exceed 2 s_d / sqrt(n), so n >= (2 s_d / Delta)^2 games
# resolve a difference Delta.  The unpaired standard error sqrt(s_A^2 + s_B^2)
# is shown for comparison.
SEED_PAIRS = [
    ('RQ2 equilibrium vs MIP-BR (Red MIP-BR)', ('equilibrium', 'mip_br', 'D0', 'nominal'),
     ('mip_br', 'mip_br', 'D0', 'nominal')),
    ('RQ2 greedy vs MIP-BR (Red MIP-BR)', ('greedy_br', 'mip_br', 'D0', 'nominal'),
     ('mip_br', 'mip_br', 'D0', 'nominal')),
    ('RQ3 D3 vs D0 (MIP-BR both)', ('mip_br', 'mip_br', 'D3', 'nominal'), ('mip_br', 'mip_br', 'D0', 'nominal')),
    ('RQ3 D1 vs D0 (MIP-BR both)', ('mip_br', 'mip_br', 'D1', 'nominal'), ('mip_br', 'mip_br', 'D0', 'nominal')),
    ('RQ3 typhoon vs nominal (MIP-BR both)', ('mip_br', 'mip_br', 'D0', 'typhoon'),
     ('mip_br', 'mip_br', 'D0', 'nominal')),
]


def _games(setup):
    blue, red, design, weather = setup
    _, rows = wg.run_batch(blue, red, design, (), seeds=SEEDS, weather=weather)
    return setup, [(r['blue_payoff'], r['war']) for r in rows]


def seedcheck():
    import statistics as st
    setups = sorted({s for _, a, b in SEED_PAIRS for s in (a, b)})
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        G = dict(pool.map(_games, setups))
    rows = []
    for label, a, b in SEED_PAIRS:
        ua, ub = [x[0] for x in G[a]], [x[0] for x in G[b]]
        d = [x - y for x, y in zip(ua, ub)]
        n, mean_d, s_d = len(d), st.fmean(d), st.stdev(d)
        se_unpaired = math.sqrt((st.variance(ua) + st.variance(ub)) / n)
        need = lambda delta: math.ceil((2 * s_d / delta) ** 2)
        rows.append([label, f"{mean_d:+.1f}", f"{s_d / math.sqrt(n):.1f}", f"{se_unpaired:.1f}",
                     f"{abs(mean_d) / (s_d / math.sqrt(n)):.1f}", need(10), need(20)])
    write_md('seedcheck', f"How many games are enough ({SEEDS} paired games per setup, Blue payoff u_B). "
             "Paired s.e. = s_d / sqrt(n) over per-game differences on common seeds. "
             "Games needed to resolve a difference Delta: n = (2 s_d / Delta)^2.\n\n"
             + md(rows, ['Comparison', 'mean difference', 'paired s.e.', 'unpaired s.e.', 'difference / paired s.e.',
                         'n for Delta = 10', 'n for Delta = 20']))


# ---------------------------------------------------------------------------
# Workshop 2: check the flow MIP (report section 3.8) against the Workshop 1 MIP
# ---------------------------------------------------------------------------
def use_workshop1_fleet():
    """Switch the model to the Workshop 1 fleet (10 DDG; 8 PLAN, 6 CCG), the largest
    case where the Workshop 1 count-vector MIP can still be built."""
    wg.SHIP_TYPES = {'US-DDG': ('B', 'US', 1.0, 10, 'navy', False),
                     'CN-DDG': ('R', 'CN', 1.0, 8, 'navy', False),
                     'CCG': ('R', 'CN', 0.6, 6, 'cg', True)}
    wg.FLEET = {'US-DDG': {'YOK': 5, 'GUA': 5}, 'CN-DDG': {'NBO': 4, 'SAN': 4}, 'CCG': {'NBO': 3, 'SAN': 3}}
    T = wg.SHIP_TYPES
    wg.KINDS = {i: [k for k, t in T.items() if t[0] == i] for i in 'BR'}
    wg.W_K = {k: t[2] for k, t in T.items()}
    wg.D_K = {k: t[3] for k, t in T.items()}
    wg.CLASS_K = {k: t[4] for k, t in T.items()}
    wg.SMALL_K = {k: t[5] for k, t in T.items()}
    wg.NATION_K = {k: t[1] for k, t in T.items()}
    wg.FLEET_SIZE = {i: sum(sum(wg.FLEET[k].values()) for k in wg.KINDS[i]) for i in 'BR'}


class _BothMIPs(wg.MIPBRPolicy):
    """Plays the flow MIP, and on every decision also solves the Workshop 1 MIP on the same
    observation and records both plans' exact objective (plan_value) and incident risk."""
    log = []

    def act(self, obs):
        old = wg.MIPBREnumPolicy(self.player, self.rng)
        mo, po = old.act(obs)
        mn, pn = super().act(obs)
        Jo, ro = wg.plan_value(obs, mo, po)
        Jn, rn = wg.plan_value(obs, mn, pn)
        cnt = lambda mv: wg.Policy.planned_counts(obs, {s.id: mv.get(s.id, s.loc) for s in obs.free})
        co, cn = cnt(mo), cnt(mn)
        same = all({k: c for k, c in co[v].items() if c} == {k: c for k, c in cn[v].items() if c}
                   and (po.get(v, 'P') == pn.get(v, 'P') or not any(co[v].values()))
                   for v in obs.graph.contested)
        eps = wg.risk_budget(obs.P['eps'][self.player], obs.ell, obs.P)
        _BothMIPs.log.append((self.player, same, Jo, Jn, ro, rn, eps))
        return mn, pn


def _mipcheck_games(seed):
    use_workshop1_fleet()
    _BothMIPs.log = []
    orig = wg.make_policy
    wg.make_policy = lambda name, player, game: _BothMIPs(player, game.rng) if name == 'both' else orig(name, player, game)
    wg.Game('both', 'both', seed=seed, weather='nominal').run()
    wg.make_policy = orig
    return list(_BothMIPs.log)


def _mipcheck_batch(args):
    pol, seed0, n = args
    use_workshop1_fleet()
    s, rows = wg.run_batch(pol, pol, seeds=n, seed0=seed0, weather='nominal')
    return pol, rows


def mipcheck(n_games=40, n_batch=SEEDS):
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        logs = [x for L in pool.map(_mipcheck_games, range(n_games)) for x in L]
        chunks = [(p, k, n_batch // 4) for p in ('mip_br_enum', 'mip_br') for k in range(0, n_batch, n_batch // 4)]
        batch = defaultdict(list)
        for pol, rows in pool.map(_mipcheck_batch, chunks):
            batch[pol] += rows
    rows = []
    for side in 'BR':
        L = [x for x in logs if x[0] == side]
        n = len(L)
        same = sum(x[1] for x in L)
        gap = [x[2] - x[3] for x in L]
        rows.append([{'B': 'Blue', 'R': 'Red'}[side], n, f"{100 * same / n:.1f}%",
                     f"{sum(abs(d) for d in gap) / n:.3f}", f"{max(gap):.3f}", f"{min(gap):.3f}",
                     sum(1 for x in L if x[5] > x[6] + 1e-6), sum(1 for x in L if x[4] > x[6] + 1e-6)])
    txt = (f"Flow MIP vs Workshop 1 MIP on the Workshop 1 fleet, nominal weather, {n_games} games played by the "
           "flow MIP on both sides; at every decision both programs are solved on the same observation.\n"
           "Objective = exact per-period objective of each plan (plan_value). gap = old - new (positive: old plan better).\n\n"
           + md(rows, ['Side', 'decisions', 'same plan', 'mean |gap|', 'max gap', 'min gap',
                       'new over risk budget', 'old over risk budget']))
    import statistics as st
    brow = []
    for pol in ('mip_br_enum', 'mip_br'):
        R = batch[pol]
        n = len(R)
        ub = [r['blue_payoff'] for r in R]
        ur = [r['red_payoff'] for r in R]
        war = [r['war'] for r in R]
        brow.append([pol, n, f"{st.fmean(ub):.1f} ± {st.stdev(ub) / math.sqrt(n):.1f}",
                     f"{st.fmean(ur):.1f} ± {st.stdev(ur) / math.sqrt(n):.1f}",
                     f"{st.fmean(war):.3f}", f"{st.fmean(r['control_share'] for r in R):+.3f}"])
    txt += ("\n\nWhole games, both sides the same MIP, same seeds:\n\n"
            + md(brow, ['MIP', 'games', 'u_B', 'u_R', 'war rate', 'control share']))
    write_md('mipcheck', txt)


ALL = ['chicken', 'template', 'gap', 'frontier', 'riskgame', 'policies', 'weather', 'designs']


def jobs_of(name):
    """Configurations (tag, blue, red, design, weather, eps_B, eps_R) of one experiment."""
    return {
        'frontier': [('frontier', 'mip_br', 'mip_br', 'D0', 'nominal', e, 0.15) for e in EPS_GRID],
        'riskgame': [('riskgame', 'mip_br', 'mip_br', 'D0', 'nominal', eb, er)
                     for eb in TYPES.values() for er in TYPES.values()],
        'policies': [('policies', b, r, 'D0', 'nominal', 0.15, 0.15) for b in BLUE_POLICIES for r in RED_POLICIES],
        'weather': [('weather', b, 'mip_br', 'D0', w, e, 0.15) for b, e in WX_BLUE for w in wg.WEATHER],
        'designs': [('designs', 'mip_br', 'mip_br', d, w, 0.15, 0.15) for d in wg.DESIGNS for w in wg.WEATHER],
    }[name]


# Headline setups, played first: the RQ1 frontier and risk game, RQ2 policies against Red MIP-BR,
# RQ3 designs and typhoon weather.
HEADLINE_SEEDS = 50


def headline(job):
    tag, blue, red, design, weather, epsB, epsR = job
    return weather in ('nominal', 'typhoon') and (tag in ('frontier', 'riskgame') or red == 'mip_br') and \
        (tag != 'weather' or blue == 'mip_br') and (weather == 'nominal' or (design == 'D0' and blue == red and epsB == 0.15))


def game_list(names=('frontier', 'riskgame', 'policies', 'weather', 'designs')):
    """Every game of the suite once, headline setups first (seeds below HEADLINE_SEEDS), then the rest."""
    configs = list(dict.fromkeys(j[1:] for name in names for j in jobs_of(name)))
    first = [c + (sd,) for c in configs if headline(('',) + c) for sd in range(HEADLINE_SEEDS)]
    done = set(first)
    rest = [c + (sd,) for c in configs for sd in range(SEEDS) if c + (sd,) not in done]
    return first + rest


def worker(stale_hours=3.0):
    """Cluster job: play the suite's games in order, one at a time, until none is left.

    Any number of workers can run at once (on any partition).  A worker claims a game by creating
    GAMES/claims/<game>.claim (atomic), so no game is played twice.  A claim older than stale_hours
    without a stored result (its job was stopped) is taken over."""
    import socket
    claims = os.path.join(GAMES, 'claims')
    os.makedirs(claims, exist_ok=True)
    out = os.path.join(GAMES, f'{socket.gethostname()}_{os.getpid()}.csv')
    games = game_list()
    while True:
        store = load_games()
        todo = None
        for i, g in enumerate(games):
            if _key(*g) in store:
                continue
            path = os.path.join(claims, '_'.join(map(str, g)) + '.claim')
            try:
                os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            except FileExistsError:
                if time.time() - os.path.getmtime(path) < stale_hours * 3600:
                    continue
                os.utime(path)                 # stale claim: take it over
            todo = (i, g)
            break
        if todo is None:
            print('no games left', flush=True)
            return
        i, g = todo
        t0 = time.time()
        m = play_game(*g, out)
        print(f"game {i}: {g} u_B {m['blue_payoff']:.1f} war {m['war']:.0f} in {time.time() - t0:.0f}s", flush=True)


def plan():
    """Print how many games the suite has and how many are already stored."""
    store = load_games()
    games = game_list()
    first = sum(1 for g in games if g[-1] < HEADLINE_SEEDS and headline(('',) + g[:-1]))
    mip = sum(1 for g in games if 'mip_br' in g[:2])
    print(f"{len(games)} games ({first} headline, {mip} with MIP-BR), {sum(_key(*g) in store for g in games)} stored")

if __name__ == '__main__':
    which = sys.argv[1:] or ['all']
    if which == ['all']:
        which = ALL
    if which[0] == 'worker':
        worker(*map(float, which[1:2]))
        sys.exit()
    for name in which:
        globals()[name]()
