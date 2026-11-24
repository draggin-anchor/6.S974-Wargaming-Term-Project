"""Workshop 2: a learning Blue against a Red that changes how it behaves in the middle of the game.

    python3 adapt_experiments.py plan        # how many games, how many stored
    python3 adapt_experiments.py worker      # cluster job: play the next unplayed game until none is left
    python3 adapt_experiments.py tables      # markdown table from the stored games

Setup: the learning games of learn_experiments.py (posture seen only on scene, per-zone Beta beliefs,
Red a Thompson-sampling learner of type R_south, Blue prior flat, typed postures, D0, nominal weather),
with one change.  At period SWITCH (90, half the year) Red's type changes from R_south to R_north: it
now asserts most at the Senkakus and Miyako Strait and less in the South China Sea, and it plans its
movements with the new rates.  Blue is not told.  Its beliefs keep the 90 periods of southern evidence.

Blue rules: the four learning rules and the oracle (told the true rates, including the switch), plus
two variants that forget old evidence at rate g per period (exponential forgetting):
    a_v <- a0_v + g (a_v - a0_v),  b_v <- b0_v + g (b_v - b0_v)   before each update,
so evidence from k periods ago carries weight g^k (g = 0.95: about the last 20 periods count).
'myopic_forget' uses the posterior mean, 'thompson_forget' draws from it.

The games without a switch are the learning suite's own games on the same seeds (store RESULTS/learning,
read only).  The rules with no game there (the oracle against a Thompson Red, the forgetting variants)
get their own no-switch games here.  Both use the same seeds, so the effect of the switch is paired.
"""
import csv
import math
import os
import socket
import statistics
import sys
import time

import experiments as E
import learn_experiments as LE
import learning as L
import wargame_gui as W

STORE = os.path.join(E.OUT, 'adapt')
SEEDS = int(os.environ.get('SEEDS', 200))
SWITCH = int(os.environ.get('ADAPT_SWITCH', 90))
FORGET = 0.95
BLUE_RULES = ['myopic', 'committed', 'thompson', 'optimistic', 'oracle', 'myopic_forget', 'thompson_forget']
RED_RULE = 'thompson'
OLD, NEW = 'R_south', 'R_north'
ZONES = LE.ZONES
NORTH, SOUTH = ['SEN', 'MIY'], ['SCB', 'STS', 'PAR']
KEY = ['blue', 'switch', 'seed']
COLS = ['blue_payoff', 'red_payoff', 'control_share', 'war', 'war_t', 'incidents', 'uB_switch', 'regret_B',
        'regret_B_after'] + [f'mB_{v}' for v in ZONES] + [f'nB_{v}' for v in ZONES]
# no-switch games already in the learning suite (learn_experiments.blocks, R_south, flat prior)
IN_SUITE = {'myopic', 'committed', 'optimistic', 'thompson'}


def cfg_of(blue):
    """learn_experiments configuration (blue rule, red rule, H, prior, red type, mode, design)."""
    base = blue.replace('_forget', '')
    return (base, RED_RULE, 1, 'flat', OLD, 'typed', 'D0')


def play(g, out_file):
    blue, switch, seed = g
    cfg = cfg_of(blue)
    T = int(os.environ.get('ADAPT_T', 0)) or None             # shorter games for local tests only
    gm = W.Game(f'learn_{cfg[0]}', f'learn_{cfg[1]}', 'D0', (), seed=seed, weather='nominal',
                params=LE.game_params(*cfg), T=T)
    pb, pr = gm.policy['B'], gm.policy['R']
    act_b = pb.act
    state = {'uB': ''}

    def blue_act(obs):
        # Blue acts first each period, so the switch is applied here, before either side decides
        if switch == 'yes' and obs.t == SWITCH:
            pr.type = L.resolve(NEW)
            pb.opp_type = L.resolve(NEW)         # the oracle and the regret benchmark use the true rates
            state['uB'] = gm.u['B']
        elif switch == 'no' and obs.t == SWITCH:
            state['uB'] = gm.u['B']
        if blue.endswith('_forget'):
            for v in pb.a:
                pb.a[v] = pb.a0[v] + FORGET * (pb.a[v] - pb.a0[v])
                pb.b[v] = pb.b0[v] + FORGET * (pb.b[v] - pb.b0[v])
        return act_b(obs)
    pb.act = blue_act
    gm.run()
    m = gm.metrics()
    row = {c: m.get(c) for c in ('blue_payoff', 'red_payoff', 'control_share', 'war', 'war_t', 'incidents')}
    row['uB_switch'] = state['uB']
    reg = [r.get('regret', 0.0) for r in pb.log]
    row['regret_B'] = sum(reg)
    row['regret_B_after'] = sum(r.get('regret', 0.0) for r in pb.log if r['t'] >= SWITCH)
    for v in ZONES:
        row[f'mB_{v}'] = round(pb.mean(v), 4)
        row[f'nB_{v}'] = pb.a[v] + pb.b[v] - pb.a0[v] - pb.b0[v]
    os.makedirs(STORE, exist_ok=True)
    new = not os.path.exists(out_file)
    with open(out_file, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(KEY + COLS)
        w.writerow(list(g) + [row[c] for c in COLS])
    return row


def _key(g):
    return (g[0], g[1], int(g[2]))


def load():
    store = {}
    if os.path.isdir(STORE):
        for fn in sorted(os.listdir(STORE)):
            if fn.endswith('.csv'):
                with open(os.path.join(STORE, fn), newline='') as f:
                    for r in csv.DictReader(f):
                        try:
                            store[_key([r[k] for k in KEY])] = {
                                c: float(r[c]) if r[c] not in ('', 'None') else float('nan') for c in COLS}
                        except (TypeError, ValueError, KeyError):
                            continue
    return store


def game_list():
    first, rest = [], []
    for sd in range(SEEDS):
        for b in BLUE_RULES:
            for sw in ('yes', 'no'):
                if sw == 'no' and b in IN_SUITE:
                    continue
                (first if sd < 50 else rest).append((b, sw, sd))
    return first + rest


def worker(stale_hours=6.0):
    out = os.path.join(STORE, f'{socket.gethostname()}_{os.getpid()}.csv')
    os.makedirs(STORE, exist_ok=True)
    store = {}
    last = [0.0]

    def done(g):
        if _key(g) not in store and time.time() - last[0] > 60:
            store.update(load())
            last[0] = time.time()
        return _key(g) in store

    def run(g):
        r = play(g, out)
        return f"u_B {r['blue_payoff']:.1f} war {r['war']:.0f} regret_B {r['regret_B']:.1f}"
    old = E.GAMES
    E.GAMES = STORE
    try:
        E._claim_loop(game_list(), done, run, stale_hours)
    finally:
        E.GAMES = old


def plan():
    store = load()
    games = game_list()
    print(f"{len(games)} games, {sum(_key(g) in store for g in games)} stored")


def _ms(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float('nan'), float('nan')
    return statistics.fmean(xs), statistics.stdev(xs) / math.sqrt(len(xs))


def tables():
    store, suite = load(), LE.load()
    rows = []
    for b in BLUE_RULES:
        yes = {sd: store[_key((b, 'yes', sd))] for sd in range(SEEDS) if _key((b, 'yes', sd)) in store}
        if b in IN_SUITE:
            no = {sd: suite[LE._key(list(cfg_of(b)) + [sd])] for sd in range(SEEDS)
                  if LE._key(list(cfg_of(b)) + [sd]) in suite}
        else:
            no = {sd: store[_key((b, 'no', sd))] for sd in range(SEEDS) if _key((b, 'no', sd)) in store}
        seeds = sorted(set(yes) & set(no))
        if len(yes) < 2:
            continue
        d = _ms([yes[s]['blue_payoff'] - no[s]['blue_payoff'] for s in seeds]) if len(seeds) > 1 else (math.nan,) * 2
        after = _ms([yes[s]['blue_payoff'] - yes[s]['uB_switch'] for s in yes])
        north = statistics.fmean(statistics.fmean(yes[s][f'mB_{v}'] for v in NORTH) for s in yes)
        south = statistics.fmean(statistics.fmean(yes[s][f'mB_{v}'] for v in SOUTH) for s in yes)
        reg = _ms([yes[s]['regret_B_after'] for s in yes])
        rows.append([b, len(yes), f"{_ms([r['blue_payoff'] for r in yes.values()])[0]:.0f}",
                     f"{_ms([r['blue_payoff'] for r in no.values()])[0]:.0f}" if no else '-',
                     f"{d[0]:+.0f} ± {d[1]:.0f}" if seeds else '-', f"{after[0]:.0f}",
                     f"{reg[0]:.1f} ± {reg[1]:.1f}", f"{_ms([r['war'] for r in yes.values()])[0]:.2f}",
                     f"{north:.2f}", f"{south:.2f}"])
    t = L.resolve(NEW)
    text = (f"Learning Blue against a Thompson-sampling Red whose type switches from {OLD} to {NEW} at period {SWITCH}. "
            f"True rates after the switch: North {statistics.fmean(t[v] for v in NORTH):.2f}, "
            f"South {statistics.fmean(t[v] for v in SOUTH):.2f}. Change = per-seed difference from the same rule "
            "without the switch (± s.e.).\n\n"
            + E.md(rows, ['Blue rule', 'games', 'u_B switch', 'u_B no switch', 'change from the switch',
                          'u_B after the switch', 'regret after the switch', 'war rate',
                          'Blue belief North at end', 'Blue belief South at end']))
    with open(os.path.join(E.OUT, 'adapt.md'), 'w') as f:
        f.write(text + '\n')
    print(text)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    globals()[which](*map(float, sys.argv[2:3]))
