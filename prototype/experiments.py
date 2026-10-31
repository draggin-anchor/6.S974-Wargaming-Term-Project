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
from multiprocessing import Pool

import wargame_gui as wg

SEEDS = int(os.environ.get('SEEDS', 200))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get('RESULTS', 'results'))   # RESULTS=results_w2 for Workshop 2 runs
FIG = os.path.join(OUT, 'figures')
EPS_GRID = [0.02, 0.05, 0.10, 0.15, 0.25, 0.40]
TYPES = {'conservative': 0.05, 'moderate': 0.15, 'aggressive': 0.40}


def _run(job):
    """Worker: one configuration -> summary dict."""
    tag, blue, red, design, weather, epsB, epsR = job
    s, _ = wg.run_batch(blue, red, design, (), seeds=SEEDS, weather=weather,
                        params={'eps': {'B': epsB, 'R': epsR}})
    s.update(tag=tag, epsB=epsB, epsR=epsR)
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
    jobs = [('frontier', 'mip_br', 'mip_br', 'D0', 'nominal', e, 0.15) for e in EPS_GRID]
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
    jobs = [('riskgame', 'mip_br', 'mip_br', 'D0', 'nominal', eb, er)
            for eb in TYPES.values() for er in TYPES.values()]
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
    jobs = [('policies', b, r, 'D0', 'nominal', 0.15, 0.15) for b in BLUE_POLICIES for r in RED_POLICIES]
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
        jobs = [('weather', b, 'mip_br', 'D0', w, e, 0.15) for b, e in WX_BLUE for w in wg.WEATHER]
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
    jobs = [('designs', 'mip_br', 'mip_br', d, w, 0.15, 0.15) for d in wg.DESIGNS for w in wg.WEATHER]
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


ALL = ['chicken', 'template', 'gap', 'frontier', 'riskgame', 'policies', 'weather', 'designs']

if __name__ == '__main__':
    which = sys.argv[1:] or ['all']
    if which == ['all']:
        which = ALL
    for name in which:
        globals()[name]()
