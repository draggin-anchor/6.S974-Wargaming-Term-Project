"""Timing job for the multi-period best response (learning.py).  One array task plays one game
and logs every solve as it happens, so a job stopped by the time limit still leaves its data.

    python3 cluster/timing.py TASK        # TASK = 0..14, see SETUPS below
    python3 cluster/timing.py summary     # per-setup solve times from logs/timing_*.csv

Setups: Blue and Red both plan 3 periods; both plan 2; Blue plans 3 against a one-period Red.
Seeds 0 to 4.  Thompson sampling on both sides, Red type R_south, nominal weather, D0.
"""
import csv
import glob
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import learning as L          # noqa: E402
import wargame_gui as W       # noqa: E402

SETUPS = [(3, 3), (2, 2), (3, 1)]
SEEDS = 5
LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')


def license_check():
    """True when Gurobi solves a model above the size-limited license's 2,000-variable cap."""
    import gurobipy as gp
    try:
        with gp.Env(params={'OutputFlag': 0}) as env, gp.Model(env=env) as m:
            x = m.addVars(2500)
            m.addConstr(x.sum() <= 1)
            m.optimize()
        return True
    except gp.GurobiError as e:
        print('license check:', e, flush=True)
        return False


def run(task):
    HB, HR = SETUPS[task // SEEDS]
    seed = task % SEEDS
    print(f'task {task}: Blue H={HB}, Red H={HR}, seed {seed}, full license: {license_check()}', flush=True)
    os.makedirs(LOG, exist_ok=True)
    path = os.path.join(LOG, f'timing_B{HB}_R{HR}_s{seed}.csv')
    f = open(path, 'w', newline='')
    w = csv.writer(f)
    w.writerow(['HB', 'HR', 'seed', 't', 'side', 'H', 'secs', 'vars'])
    orig = L.solve_plan

    def timed(obs, q, own_type, H, m=None, commit=False, coarse=None):
        t0 = time.time()
        r = orig(obs, q, own_type, H, m, commit, coarse)
        w.writerow([HB, HR, seed, obs.t, obs.player, H, round(time.time() - t0, 2), r['size'][0]])
        f.flush()
        return r
    L.solve_plan = timed
    P = dict(L.LEARN_PARAMS)
    P['learn'] = {'B': {'H': HB, 'type': 'B_base', 'opp_type': 'R_south', 'regret': False},
                  'R': {'H': HR, 'type': 'R_south', 'opp_type': 'B_base', 'regret': False}}
    t0 = time.time()
    g = W.Game('learn_thompson', 'learn_thompson', 'D0', (), seed=seed, weather='nominal', params=P)
    if os.environ.get('TIMING_T'):
        g.T = int(os.environ['TIMING_T'])
    g.run()
    print(f'done in {(time.time() - t0) / 3600:.2f} h: {g.metrics()}', flush=True)


def summary():
    rows = []
    for fn in glob.glob(os.path.join(LOG, 'timing_*.csv')):
        with open(fn) as f:
            rows += list(csv.DictReader(f))
    for HB, HR in SETUPS:
        for side, H in (('B', HB), ('R', HR)):
            xs = sorted(float(r['secs']) for r in rows if int(r['HB']) == HB and int(r['HR']) == HR and r['side'] == side)
            if not xs:
                continue
            games = {r['seed'] for r in rows if int(r['HB']) == HB and int(r['HR']) == HR}
            turns = max(int(r['t']) for r in rows if int(r['HB']) == HB and int(r['HR']) == HR)
            print(f'Blue H={HB} Red H={HR} | {side} plans {H}: {len(xs)} solves in {len(games)} games (up to turn {turns}), '
                  f'mean {statistics.fmean(xs):.1f} s, median {statistics.median(xs):.1f} s, '
                  f'95th pct {xs[int(0.95 * (len(xs) - 1))]:.1f} s, max {xs[-1]:.0f} s, total {sum(xs) / 3600:.2f} h')


if __name__ == '__main__':
    if sys.argv[1] == 'summary':
        summary()
    else:
        run(int(sys.argv[1]))
