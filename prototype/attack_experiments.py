"""Workshop 2 contested conditions, rollout lookahead and the cost of design D3.

    python3 attack_experiments.py plan        # how many games, how many stored
    python3 attack_experiments.py worker      # cluster job: play the next unplayed game until none is left
    python3 attack_experiments.py tables      # markdown tables from the stored games
    python3 attack_experiments.py breakeven   # D3 break-even cost from the Workshop 2 suite (no new games)

Games are stored in RESULTS/attacks/ with the same claim-based store as experiments.py.  Every game
has eps_B = eps_R = 0.15.  The no-attack games of the Workshop 2 suite (RESULTS/games/) are the
nominal baseline: they use the same seeds 0-199, so differences are paired.

Blocks, in the order the workers play them:
  R  rollout lookahead.  Blue 'rollout' (rollout.py) against Red MIP-BR and against Red rule of
     thumb, D0, nominal weather, seeds 0-199.  Compared with Blue MIP-BR on the same seeds.
  S  attack screen.  Red picks the target that hurts Blue most: for each Blue setup and each attack,
     every target is played on 40 screening seeds (1000-1039), and the target with the lowest mean
     Blue payoff is Red's choice for that setup.  Screening seeds are not reused below, so the
     choice does not inflate the result.
  F  attack results.  Each setup under each attack at Red's chosen target, seeds 0-199.

Blue setups: every policy against Red MIP-BR in D0 (rule of thumb, greedy, MIP-BR, Nash equilibrium
plan, safety-first plan, rollout), and Blue MIP-BR against Red MIP-BR in D1, D2 and D3.  Red adapts
its target to the setup, so a design that protects one zone can be attacked elsewhere.

Attacks and targets (wargame_gui.py PARAMS):
  jamming    Blue detection halved in one region in periods 60-120.  Targets N, C, S, or 'default'
             (the region where Red is strongest each period).
  blockade   Two CCG hulls hold and assert at one zone for the whole game.  While they assert there,
             Blue cannot use the edges at that zone.  Targets the 8 zones, or 'default' (station at
             Scarborough Shoal, edges closed at Scarborough and Second Thomas Shoal).
  deception  Two false contacts a period in Blue's picture.  Targets the 8 zones, or 'default'
             (a random zone for each contact).
"""
import csv
import math
import os
import socket
import statistics
import sys
import time

import experiments as E
import wargame_gui as W

STORE = os.path.join(E.OUT, 'attacks')
SEEDS = int(os.environ.get('SEEDS', 200))
SCREEN_SEEDS = list(range(1000, 1000 + int(os.environ.get('SCREEN_SEEDS', 40))))
EPS = 0.15
KEY = ['blue', 'red', 'design', 'weather', 'attack', 'target', 'seed']
COLS = E.GAME_COLS + ['rollout_mip_share']
ZONES = ['SEN', 'MIY', 'TWN', 'EOT', 'LUZ', 'SCB', 'STS', 'PAR']
ATTACKS = ['jamming', 'blockade', 'deception']
TARGETS = {'jamming': ['default', 'N', 'C', 'S'], 'blockade': ['default'] + ZONES,
           'deception': ['default'] + ZONES}
BLUE_POLICIES = ['moderate', 'greedy_br', 'mip_br', 'equilibrium', 'maximin', 'rollout']
SETUPS = [(b, 'mip_br', 'D0') for b in BLUE_POLICIES] + [('mip_br', 'mip_br', d) for d in ('D1', 'D2', 'D3')]
ROLLOUT = [('rollout', 'mip_br', 'D0'), ('rollout', 'moderate', 'D0')]
NAMES = {'moderate': 'Rule of thumb', 'greedy_br': 'Quick best response', 'mip_br': 'Best response (MIP)',
         'equilibrium': 'Nash equilibrium plan', 'maximin': 'Safety-first plan', 'rollout': 'Rollout lookahead'}


def attack_params(attack, target):
    if attack == 'none' or target == 'default':
        return {}
    if attack == 'jamming':
        return {'jam_target': target}
    if attack == 'blockade':
        return {'blockade_station': target, 'blockade_zones': (target,)}
    return {'deception_target': target}


def play(g, out_file):
    blue, red, design, weather, attack, target, seed = g
    params = {'eps': {'B': EPS, 'R': EPS}, **attack_params(attack, target)}
    T = int(os.environ.get('ATTACK_T', 0)) or None           # shorter games for local tests only
    gm = W.Game(blue, red, design, () if attack == 'none' else (attack,), seed=seed, weather=weather,
                params=params, T=T).run()
    m = gm.metrics()
    pol = gm.policy['B']
    m['rollout_mip_share'] = (sum(r['choice'] == 'mip' for r in pol.log) / len(pol.log)
                              if getattr(pol, 'name', '') == 'rollout' and pol.log else '')
    os.makedirs(STORE, exist_ok=True)
    new = not os.path.exists(out_file)
    with open(out_file, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(KEY + COLS)
        w.writerow(list(g) + [m[c] for c in COLS])
    return m


def _key(g):
    return (g[0], g[1], g[2], g[3], g[4], g[5], int(g[6]))


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


def screen_list():
    return [s + ('nominal', a, t, sd) for sd in SCREEN_SEEDS for s in SETUPS for a in ATTACKS for t in TARGETS[a]]


def worst_target(store, setup, attack):
    """Red's target for this setup and attack: lowest mean Blue payoff on the screening seeds
    (None until every screening game of this setup and attack is stored)."""
    mean = {}
    for t in TARGETS[attack]:
        rows = [store.get(_key(setup + ('nominal', attack, t, sd))) for sd in SCREEN_SEEDS]
        if any(r is None for r in rows):
            return None
        mean[t] = statistics.fmean(r['blue_payoff'] for r in rows)
    return min(mean, key=mean.get)


def final_list(store):
    out = []
    for s in SETUPS:
        for a in ATTACKS:
            t = worst_target(store, s, a)
            if t is not None:
                out += [s + ('nominal', a, t, sd) for sd in range(SEEDS)]
    return out


def rollout_list():
    n = min(50, SEEDS)
    first = [s + ('nominal', 'none', 'none', sd) for sd in range(n) for s in ROLLOUT]
    return first + [s + ('nominal', 'none', 'none', sd) for sd in range(n, SEEDS) for s in ROLLOUT]


def game_list(store=None):
    store = load() if store is None else store
    return rollout_list() + screen_list() + final_list(store)


def complete(store):
    """Every game listed, including the final games, which are listed only once the screen is done."""
    return all(worst_target(store, s, a) is not None for s in SETUPS for a in ATTACKS) and \
        all(_key(g) in store for g in game_list(store))


def worker(stale_hours=6.0):
    """Cluster job.  When nothing is left to claim but the screen is still being played elsewhere,
    wait and look again: the final games are listed as soon as their screen is complete."""
    out = os.path.join(STORE, f'{socket.gethostname()}_{os.getpid()}.csv')
    os.makedirs(STORE, exist_ok=True)
    store = {}
    last = [0.0]

    def done(g):
        # reread the store at most once a minute (thousands of games can be claimed by other jobs)
        if _key(g) not in store and time.time() - last[0] > 60:
            store.update(load())
            last[0] = time.time()
        return _key(g) in store

    def run(g):
        m = play(g, out)
        return f"u_B {m['blue_payoff']:.1f} war {m['war']:.0f}"
    old = E.GAMES
    E.GAMES = STORE                      # claims go to RESULTS/attacks/claims
    try:
        while True:
            store.update(load())
            E._claim_loop(game_list(store), done, run, stale_hours)
            store.update(load())
            if complete(store):
                return
            print('waiting for screening games held by other jobs', flush=True)
            time.sleep(600)
    finally:
        E.GAMES = old


def plan():
    store = load()
    r, s = rollout_list(), screen_list()
    f = final_list(store)
    n_f = len(SETUPS) * len(ATTACKS) * SEEDS
    print(f"rollout {sum(_key(g) in store for g in r)}/{len(r)}, screen {sum(_key(g) in store for g in s)}/{len(s)}, "
          f"final {sum(_key(g) in store for g in f)}/{n_f} ({len(f)} listed so far)")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def _ms(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float('nan'), float('nan')
    return statistics.fmean(xs), statistics.stdev(xs) / math.sqrt(len(xs))


def _paired(a, b, key='blue_payoff'):
    """Mean and standard error of the per-seed difference a - b over the seeds both have."""
    seeds = sorted(set(a) & set(b))
    return _ms([a[s][key] - b[s][key] for s in seeds]) + (len(seeds),)


def _suite(suite, blue, red, design, weather='nominal'):
    return {sd: suite[E._key(blue, red, design, weather, EPS, EPS, sd)] for sd in range(SEEDS)
            if E._key(blue, red, design, weather, EPS, EPS, sd) in suite}


def _mine(store, setup, attack, target, seeds):
    return {sd: store[_key(setup + ('nominal', attack, target, sd))] for sd in seeds
            if _key(setup + ('nominal', attack, target, sd)) in store}


def tables():
    store, suite = load(), E.load_games()
    out = []
    # rollout lookahead
    out.append("Rollout lookahead against one-period best response (MIP-BR), D0, nominal weather. "
               "Gain = per-seed difference in Blue payoff, rollout minus MIP-BR on the same seeds (± standard error).\n")
    rows = []
    for blue, red, d in ROLLOUT:
        ro = _mine(store, (blue, red, d), 'none', 'none', range(SEEDS))
        base = _suite(suite, 'mip_br', red, d)
        if len(ro) < 2:
            continue
        g, se, n = _paired(ro, base)
        w = _paired(ro, base, 'war')
        rows.append([f"Red {NAMES[red]}", n, f"{_ms([r['blue_payoff'] for r in ro.values()])[0]:.0f}",
                     f"{_ms([r['blue_payoff'] for r in base.values()])[0]:.0f}", f"{g:+.1f} ± {se:.1f}",
                     f"{_ms([r['war'] for r in ro.values()])[0]:.2f}", f"{_ms([r['war'] for r in base.values()])[0]:.2f}",
                     f"{w[0]:+.3f} ± {w[1]:.3f}",
                     f"{_ms([r['rollout_mip_share'] for r in ro.values()])[0]:.2f}"])
    out.append(E.md(rows, ['Opponent', 'games', 'u_B rollout', 'u_B MIP-BR', 'gain', 'war rollout', 'war MIP-BR',
                           'war difference', 'share of turns rollout kept the MIP-BR plan']))
    # attacks
    out.append("\n\nEvery Blue setup under attack, Red MIP-BR, nominal weather.  Red's target is the one with the lowest "
               f"Blue payoff on {len(SCREEN_SEEDS)} screening seeds.  Entry: target / u_B / change from no attack "
               "(paired, ± s.e.) / war rate.\n")
    rows = []
    for s in SETUPS:
        nom = _suite(suite, *s) if s[0] != 'rollout' else _mine(store, s, 'none', 'none', range(SEEDS))
        label = f"{NAMES[s[0]]}, {s[2]}"
        row = [label, f"{_ms([r['blue_payoff'] for r in nom.values()])[0]:.0f} / {_ms([r['war'] for r in nom.values()])[0]:.2f}"
               if nom else '']
        for a in ATTACKS:
            t = worst_target(store, s, a)
            att = _mine(store, s, a, t, range(SEEDS)) if t else {}
            if len(att) < 2 or not nom:
                row.append(f"{t or '?'} / not played")
                continue
            g, se, n = _paired(att, nom)
            row.append(f"{t} / {_ms([r['blue_payoff'] for r in att.values()])[0]:.0f} / {g:+.0f} ± {se:.0f} / "
                       f"{_ms([r['war'] for r in att.values()])[0]:.2f}")
        rows.append(row)
    out.append(E.md(rows, ['Blue setup', 'no attack: u_B / war'] + ATTACKS))
    # screen detail
    out.append(f"\n\nScreen: mean Blue payoff over {len(SCREEN_SEEDS)} screening seeds for every target.\n")
    rows = []
    for s in SETUPS:
        for a in ATTACKS:
            cells = []
            for t in TARGETS[a]:
                r = [store.get(_key(s + ('nominal', a, t, sd))) for sd in SCREEN_SEEDS]
                r = [x for x in r if x]
                cells.append(f"{t} {statistics.fmean(x['blue_payoff'] for x in r):.0f}" if r else f"{t} -")
            rows.append([f"{NAMES[s[0]]}, {s[2]}", a, ', '.join(cells)])
    out.append(E.md(rows, ['Blue setup', 'attack', 'target: mean u_B']))
    text = '\n'.join(out) + '\n\n' + breakeven(store, suite, quiet=True)
    os.makedirs(E.OUT, exist_ok=True)
    with open(os.path.join(E.OUT, 'attacks.md'), 'w') as f:
        f.write(text)
    print(text)


def breakeven(store=None, suite=None, quiet=False):
    """Break-even cost of D3 (de-escalation measures).  D3 costs Blue zeta per period it is in place
    (charged like design_cost in the stage payoff, so discounted and only while the game lasts).
    D3 pays for itself while
        E[u_B(D3)] - zeta E[sum_{t=1}^{n} delta^(t-1)] >= E[u_B(D0)],
    n = periods played in the D3 game (180, or the period of war).  So
        zeta* = E[u_B(D3) - u_B(D0)] / E[sum_t delta^(t-1)],
    estimated on the same seeds (MIP-BR against MIP-BR, eps = 0.15).  The standard error is the
    standard error of the paired difference divided by the mean discounted periods."""
    suite = E.load_games() if suite is None else suite
    store = load() if store is None else store
    d = W.PARAMS['delta']
    T = W.PARAMS['T']

    def disc_periods(r):
        n = T if r['war'] == 0 else int(r['war_t'])
        return (1 - d ** n) / (1 - d)

    rows, exp = [], 0.0
    for w in W.WEATHER:
        a, b = _suite(suite, 'mip_br', 'mip_br', 'D3', w), _suite(suite, 'mip_br', 'mip_br', 'D0', w)
        if len(set(a) & set(b)) < 2:
            continue
        g, se, n = _paired(a, b)
        dw = _paired(a, b, 'war')
        D = statistics.fmean(disc_periods(a[s]) for s in set(a) & set(b))
        exp += W.WEATHER[w]['pi'] * g / D
        rows.append([w, n, f"{g:+.1f} ± {se:.1f}", f"{dw[0]:+.3f} ± {dw[1]:.3f}", f"{D:.1f}",
                     f"{g / D:.2f} ± {se / D:.2f}"])
    for a_ in ATTACKS:
        s3, s0 = ('mip_br', 'mip_br', 'D3'), ('mip_br', 'mip_br', 'D0')
        if s3 not in SETUPS or s0 not in SETUPS:
            continue
        t3, t0 = worst_target(store, s3, a_), worst_target(store, s0, a_)
        if not (t3 and t0):
            continue
        a = _mine(store, s3, a_, t3, range(SEEDS))
        b = _mine(store, s0, a_, t0, range(SEEDS))
        if len(set(a) & set(b)) < 2:
            continue
        g, se, n = _paired(a, b)
        dw = _paired(a, b, 'war')
        D = statistics.fmean(disc_periods(a[s]) for s in set(a) & set(b))
        rows.append([f"nominal, {a_} (D3 at {t3}, D0 at {t0})", n, f"{g:+.1f} ± {se:.1f}",
                     f"{dw[0]:+.3f} ± {dw[1]:.3f}", f"{D:.1f}", f"{g / D:.2f} ± {se / D:.2f}"])
    text = ("D3 (de-escalation measures) break-even cost per period, MIP-BR against MIP-BR, eps = 0.15. "
            "D3 is worth its cost while the cost per period is below zeta*.\n\n"
            + E.md(rows, ['weather / attack', 'paired games', 'u_B(D3) - u_B(D0)', 'war rate D3 - D0',
                          'mean discounted periods (D3 games)', 'zeta*'])
            + f"\n\nWeather-weighted zeta* (weights pi): {exp:.2f} per period.  For scale, D1 and D2 are charged "
            f"{W.PARAMS['design_cost']['D1']} and {W.PARAMS['design_cost']['D2']} per period, and Blue's stage payoff "
            "is the value-weighted control sum_v V_v c_v (at most 42) minus eta ell.")
    if not quiet:
        print(text)
        with open(os.path.join(E.OUT, 'breakeven.md'), 'w') as f:
            f.write(text + '\n')
    return text


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    globals()[which](*map(float, sys.argv[2:3]))
