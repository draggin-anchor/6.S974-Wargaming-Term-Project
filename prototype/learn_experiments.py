"""Workshop 2 learning experiments (learning.py).  Same claim-based store as experiments.py,
kept in RESULTS/learning/ so the Workshop 2 suite is untouched.

    python3 learn_experiments.py plan        # how many games, how many stored
    python3 learn_experiments.py worker      # cluster job: play the next unplayed game until none is left
    python3 learn_experiments.py tables      # summary tables (markdown) from the stored games

A game is (blocks below): blue rule, red rule, H, blue prior, red type, posture mode, design, seed.
Posture mode 'typed': each side asserts on scene with its type's per-zone rate (correct model).
'mip': posture chosen by the MIP as before (no fixed rate describes the opponent).
"""
import csv
import math
import os
import socket
import statistics
import sys
import time

import experiments as E
import learning as L
import wargame_gui as W

STORE = os.path.join(E.OUT, 'learning')
SEEDS = int(os.environ.get('SEEDS', 200))
KEY = ['blue', 'red', 'H', 'prior', 'rtype', 'mode', 'design', 'seed']
ZONES = ['SEN', 'MIY', 'TWN', 'EOT', 'LUZ', 'SCB', 'STS', 'PAR']
COLS = (['blue_payoff', 'red_payoff', 'control_share', 'war', 'incidents', 'regret_B', 'regret_R']
        + [f'nB_{v}' for v in ZONES] + [f'mB_{v}' for v in ZONES]
        + [f'nR_{v}' for v in ZONES] + [f'mR_{v}' for v in ZONES])

RULES = ['myopic', 'committed', 'thompson', 'optimistic']


def blocks():
    """Every configuration (without seed), most important first."""
    out = []
    # L1: correct model, both sides learn.  Same rule on both sides, the oracle pair, and every
    # Blue rule against a Thompson-sampling Red.  Two Red types and two Blue priors.
    pairs = [(r, r) for r in RULES] + [('oracle', 'oracle')] + [(r, 'thompson') for r in RULES if r != 'thompson']
    for rtype in ('R_south', 'R_north'):
        for prior in ('flat', 'pess_south'):
            for b, r in pairs:
                out.append((b, r, 1, prior, rtype, 'typed', 'D0'))
    # L3: the trap and extra surveillance (D2 reports posture next to Blue ships)
    for b in ('myopic', 'thompson'):
        out.append((b, b, 1, 'pess_south', 'R_south', 'typed', 'D2'))
    # L2: misspecified, posture chosen by the MIP
    for r in RULES:
        out.append((r, r, 1, 'flat', 'R_south', 'mip', 'D0'))
    # M1 (3-period lookahead) is added once its design is settled.  Exact 3-period solves take
    # minutes each (Nov 2 cloud timing: Blue 73 s on turn 1 and over 10 min on turn 4)
    return out


def game_params(blue, red, H, prior, rtype, mode, design):
    """H is Blue's planning horizon.  Red always plans one period ahead."""
    P = dict(L.LEARN_PARAMS)
    typed = mode == 'typed'
    P['learn'] = {
        'B': {'H': H, 'prior': prior, 'type': 'B_base' if typed else None, 'opp_type': rtype if typed else None,
              'regret': typed},
        'R': {'H': 1, 'prior': 'flat', 'type': rtype if typed else None, 'opp_type': 'B_base' if typed else None,
              'regret': typed},
    }
    return P


def play(cfg, seed, out_file):
    blue, red, H, prior, rtype, mode, design = cfg
    T = int(os.environ.get('LEARN_T', 0)) or None          # shorter games for local tests only
    g = W.Game(f'learn_{blue}', f'learn_{red}', design, (), seed=seed, weather='nominal',
               params=game_params(*cfg), T=T).run()
    m = g.metrics()
    row = {c: m.get(c) for c in ('blue_payoff', 'red_payoff', 'control_share', 'war', 'incidents')}
    for i in 'BR':
        pol = g.policy[i]
        row[f'regret_{i}'] = sum(r.get('regret', 0.0) for r in pol.log) if pol.cfg['regret'] else ''
        last = pol.log[-1] if pol.log else {'n': {}, 'mean': {}}
        for v in ZONES:
            row[f'n{i}_{v}'] = pol.a[v] + pol.b[v] - pol.a0[v] - pol.b0[v]
            row[f'm{i}_{v}'] = round(pol.mean(v), 4)
    os.makedirs(STORE, exist_ok=True)
    new = not os.path.exists(out_file)
    with open(out_file, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(KEY + COLS)
        w.writerow(list(cfg) + [seed] + [row[c] for c in COLS])
    return row


def _key(row):
    return (row[0], row[1], int(row[2]), row[3], row[4], row[5], row[6], int(row[7]))


def load():
    store = {}
    if os.path.isdir(STORE):
        for fn in sorted(os.listdir(STORE)):
            if fn.endswith('.csv'):
                with open(os.path.join(STORE, fn), newline='') as f:
                    rd = csv.reader(f)
                    head = next(rd, None)
                    for r in rd:
                        try:
                            store[_key(r)] = {c: float(x) if x not in ('', 'None') else float('nan')
                                              for c, x in zip(COLS, r[len(KEY):])}
                        except (ValueError, IndexError):
                            continue
    return store


def game_list():
    cfgs = blocks()
    first = [c + (s,) for c in cfgs for s in range(min(50, SEEDS))]
    rest = [c + (s,) for c in cfgs for s in range(50, SEEDS)]
    return first + rest


def worker(stale_hours=6.0):
    out = os.path.join(STORE, f'{socket.gethostname()}_{os.getpid()}.csv')
    os.makedirs(STORE, exist_ok=True)
    store = {}

    def done(g):
        if _key(g) not in store:
            store.update(load())
        return _key(g) in store

    def run(g):
        r = play(g[:-1], g[-1], out)
        return f"u_B {r['blue_payoff']:.1f} war {r['war']:.0f} regret_B {r['regret_B']}"
    old = E.GAMES
    E.GAMES = STORE                      # claims go to RESULTS/learning/claims
    try:
        E._claim_loop(game_list(), done, run, stale_hours)
    finally:
        E.GAMES = old


def plan():
    store = load()
    games = game_list()
    print(f"{len(games)} learning games ({len(blocks())} setups x {SEEDS} seeds), "
          f"{sum(_key(g) in store for g in games)} stored")


def _mean_se(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float('nan'), float('nan')
    return statistics.fmean(xs), statistics.stdev(xs) / math.sqrt(len(xs))


def tables():
    store = load()
    lines = ['| Blue rule | Red rule | H | prior | Red type | posture | design | n | u_B | war | regret B | regret R |'
             ' South obs (Blue) |', '|' + '---|' * 13]
    for cfg in blocks():
        rows = [store[cfg + (s,)] for s in range(SEEDS) if cfg + (s,) in store]
        if not rows:
            continue
        uB = _mean_se([r['blue_payoff'] for r in rows])
        war = statistics.fmean(r['war'] for r in rows)
        rB = _mean_se([r['regret_B'] for r in rows])
        rR = _mean_se([r['regret_R'] for r in rows])
        south = statistics.fmean(r['nB_SCB'] + r['nB_STS'] + r['nB_PAR'] for r in rows)
        lines.append(f"| {' | '.join(map(str, cfg))} | {len(rows)} | {uB[0]:.0f} ({uB[1]:.0f}) | {war:.2f} | "
                     f"{rB[0]:.1f} | {rR[0]:.1f} | {south:.0f} |")
    text = '\n'.join(lines) + '\n'
    os.makedirs(STORE, exist_ok=True)
    with open(os.path.join(E.OUT, 'learning.md'), 'w') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    globals()[which](*map(float, sys.argv[2:3]))
