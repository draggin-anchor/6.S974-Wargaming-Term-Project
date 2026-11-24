"""Caution sweep: Blue's war-payoff frontier with the escalation level seen vs hidden.

Red plays the fixed moderate rule throughout (seen or hidden like Blue, at the default esc_tau).
Blue's caution is varied by two knobs, applied to Blue only:
  eps_mult  multiplies Blue's escalation-risk budget (the moderate rule's eps = 0.15, or
            greedy_br's eps directly), in both the seen and hidden games;
  tau       Blue's threshold for Pr(ell >= k) in the rule tests (hidden games only; there is no
            belief when the level is seen).
If cautious play can bring hidden-game war back to the seen level, not knowing the level costs
payoff only; the payoff gap at equal war rate is then the value of seeing the level.

usage: python belief_sweep.py [--seeds N] [--workers W]
writes results_w2/belief_sweep.csv (one row per game), belief_sweep.md and figures/belief_sweep.png"""
import argparse, csv, os, statistics, sys, time
from multiprocessing import Pool

import wargame_gui as W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results_w2')
T, WEATHER, DESIGN = 180, 'nominal', 'D0'


def cells(n_rule, n_greedy):
    out = []
    for m in (0.25, 0.5, 1.0, 1.5):
        out.append(('moderate', 'seen', m, None, n_rule))
        for tau in (0.05, 0.1, 0.25, 0.5):
            out.append(('moderate', 'hidden', m, tau, n_rule))
    for eps in (0.03, 0.06, 0.1, 0.15, 0.3):
        out.append(('greedy_br', 'seen', eps, None, n_greedy))
        out.append(('greedy_br', 'hidden', eps, 0.25, n_greedy))
    return out


def play(job):
    blue, arm, knob, tau, seed = job
    params = {'esc_hidden': arm == 'hidden'}
    if blue == 'greedy_br':
        params['eps'] = dict(W.PARAMS['eps'], B=knob)
    g = W.Game(blue, 'moderate', DESIGN, seed=seed, T=T, weather=WEATHER, params=params)
    pol = g.policy['B']
    if blue == 'moderate':
        pol.eps = pol.eps * knob
    if tau is not None:
        inner = pol.act

        def act(obs, _inner=inner):
            obs.P = dict(obs.P, esc_tau=tau)          # Blue's threshold only; Red keeps the default
            return _inner(obs)
        pol.act = act
    g.run()
    m = g.metrics()
    bm = g.belief_metrics('B') if arm == 'hidden' else {}
    return {'blue': blue, 'arm': arm, 'knob': knob, 'tau': '' if tau is None else tau, 'seed': seed,
            'war': m['war'], 'war_t': m['war_t'], 'blue_payoff': m['blue_payoff'], 'red_payoff': m['red_payoff'],
            'control_share': m['control_share'], 'incidents': m['incidents'], 'mean_ell': m['mean_ell'],
            'periods': m['periods'], 'p_true': bm.get('mean_p_true', '')}


def summarize(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r['blue'], r['arm'], float(r['knob']), r['tau']), []).append(r)
    summ = []
    for (blue, arm, knob, tau), rs in sorted(groups.items(), key=lambda x: (x[0][0], x[0][2], x[0][1], str(x[0][3]))):
        n = len(rs)
        war = statistics.fmean(float(r['war']) for r in rs)
        pay = [float(r['blue_payoff']) for r in rs]
        summ.append({'blue': blue, 'arm': arm, 'knob': knob, 'tau': tau, 'n': n, 'war': war,
                     'war_se': (war * (1 - war) / n) ** 0.5, 'blue_payoff': statistics.fmean(pay),
                     'pay_se': statistics.stdev(pay) / n ** 0.5 if n > 1 else 0.0,
                     'control_share': statistics.fmean(float(r['control_share']) for r in rs),
                     'incidents': statistics.fmean(float(r['incidents']) for r in rs)})
    return summ


def write_md(summ, path):
    with open(path, 'w') as f:
        f.write(f"# Caution sweep: escalation level seen vs hidden (Blue varies caution, Red moderate)\n\n"
                f"{DESIGN}, {WEATHER} weather, T = {T}. knob = multiplier of Blue's risk budget (moderate) or "
                f"Blue's eps (greedy_br); tau = Blue's Pr(ell >= k) threshold (hidden only). +- = one standard error.\n\n"
                "| Blue | knob | arm | tau | n | war | Blue payoff | control share | incidents |\n"
                "|---|---|---|---|---|---|---|---|---|\n")
        for s in summ:
            f.write(f"| {s['blue']} | {s['knob']:g} | {s['arm']} | {s['tau']} | {s['n']} | "
                    f"{s['war']:.2f} +- {s['war_se']:.2f} | {s['blue_payoff']:.1f} +- {s['pay_se']:.1f} | "
                    f"{s['control_share']:.3f} | {s['incidents']:.1f} |\n")


def plot(summ, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=False)
    for ax, blue in zip(axes, ('moderate', 'greedy_br')):
        series = {}
        for s in summ:
            if s['blue'] != blue:
                continue
            key = 'seen' if s['arm'] == 'seen' else f"hidden, tau={s['tau']}"
            series.setdefault(key, []).append(s)
        for key, ss in sorted(series.items(), key=lambda x: (x[0] != 'seen', x[0])):
            ss.sort(key=lambda s: s['knob'])
            style = dict(color='black', lw=2, marker='s') if key == 'seen' else dict(marker='o', lw=1.2)
            ax.errorbar([s['war'] for s in ss], [s['blue_payoff'] for s in ss],
                        xerr=[s['war_se'] for s in ss], yerr=[s['pay_se'] for s in ss], label=key, capsize=2, **style)
            for s in ss:
                ax.annotate(f"{s['knob']:g}", (s['war'], s['blue_payoff']), fontsize=7, xytext=(3, 3),
                            textcoords='offset points')
        ax.set_xlabel('share of games ending in war')
        ax.set_ylabel('Blue payoff (discounted)')
        ax.set_title(f"Blue {blue} v Red moderate (labels: {'budget multiplier' if blue == 'moderate' else 'eps'})",
                     fontsize=10)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=60)
    ap.add_argument('--greedy-seeds', type=int, default=40)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--replot', action='store_true', help='only re-summarize the existing CSV')
    a = ap.parse_args()
    csv_path = os.path.join(OUT, 'belief_sweep.csv')
    if not a.replot:
        jobs = [(blue, arm, knob, tau, seed) for blue, arm, knob, tau, n in cells(a.seeds, a.greedy_seeds)
                for seed in range(n)]
        jobs.sort(key=lambda j: j[0] != 'greedy_br')      # slow ones first
        t0, rows = time.time(), []
        with Pool(a.workers) as pool:
            for k, r in enumerate(pool.imap_unordered(play, jobs, chunksize=1), 1):
                rows.append(r)
                if k % 50 == 0 or k == len(jobs):
                    el = time.time() - t0
                    print(f"{k}/{len(jobs)} games, {el / 60:.1f} min, about {el / k * (len(jobs) - k) / 60:.0f} min left",
                          flush=True)
        with open(csv_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r['blue'], r['arm'], r['knob'], str(r['tau']), r['seed'])))
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    summ = summarize(rows)
    write_md(summ, os.path.join(OUT, 'belief_sweep.md'))
    os.makedirs(os.path.join(OUT, 'figures'), exist_ok=True)
    plot(summ, os.path.join(OUT, 'figures', 'belief_sweep.png'))
    print(open(os.path.join(OUT, 'belief_sweep.md')).read())


if __name__ == '__main__':
    main()
