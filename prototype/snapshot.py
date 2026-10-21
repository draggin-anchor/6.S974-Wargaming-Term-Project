#!/usr/bin/env python3
"""
snapshot.py -- draw the theater graph and the state of one game at chosen periods
(a static version of the GUI map, for the report and slides).

    python3 snapshot.py --blue mip_br --red mip_br --weather typhoon --seed 4 --periods 1 8 16 --out results/figures/snapshot
"""

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import wargame_gui as wg

CMAP = LinearSegmentedColormap.from_list('ctrl', ['#c62828', '#ffffff', '#1565c0'])
# schematic (not to scale) positions, roughly preserving geography
XY = {'NBO': (10, 25), 'SEN': (17, 22.5), 'MIY': (24.5, 21), 'YOK': (33, 26), 'TWN': (9, 17.5), 'EOT': (20, 15.5),
      'LUZ': (12.5, 11), 'GUA': (31, 9), 'SAN': (-1, 8), 'PAR': (2.5, 3), 'SCB': (10, 3.5), 'STS': (6.5, -3),
      'PHL': (16, 1)}


def draw(ax, gm, h, title):
    g = gm.g
    pos = {v: XY[v] for v in g.nodes}
    for r, nodes in wg.REGIONS.items():
        st = h['sea'][r]
        if st != 'calm':
            xs = [pos[v][0] for v in nodes]
            ys = [pos[v][1] for v in nodes]
            ax.add_patch(plt.Rectangle((min(xs) - 2.2, min(ys) - 2.2), max(xs) - min(xs) + 4.4, max(ys) - min(ys) + 4.4,
                                       color='#9e9e9e' if st == 'storm' else '#cfd8e3', alpha=0.6, lw=0, zorder=0))
            ax.text(max(xs) + 2.0, min(ys) - 2.0, st, fontsize=7, style='italic', color='#37474f', ha='right', va='bottom')
    for a, b in g.edges:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color='#90a4ae', lw=1, zorder=1)
    cnt = h['counts']
    for v in g.nodes:
        x, y = pos[v]
        kind, owner = wg.NODES[v][3], wg.NODES[v][4]
        if kind == 'home':
            ax.scatter([x], [y], marker='s', s=90, color='#1565c0' if owner == 'B' else '#c62828', zorder=3,
                       edgecolor='k', lw=0.5)
        else:
            pB = h['postures']['B'].get(v) == 'A' and cnt[v]['DDG'] > 0
            pR = h['postures']['R'].get(v) == 'A' and (cnt[v]['PLAN'] + cnt[v]['CCG']) > 0
            edge = '#6a1b9a' if (pB and pR) else ('#1565c0' if pB else ('#c62828' if pR else 'k'))
            ax.scatter([x], [y], s=260, c=[h['c'][v]], cmap=CMAP, vmin=-1, vmax=1, zorder=3, edgecolor=edge,
                       lw=2.5 if (pB or pR) else 0.6)
            if v in h['incidents']:
                ax.scatter([x], [y], s=520, facecolor='none', edgecolor='#ff8f00', lw=2, zorder=2)
        lab = []
        if cnt[v]['DDG']:
            lab.append(f"B{cnt[v]['DDG']}")
        if cnt[v]['PLAN']:
            lab.append(f"P{cnt[v]['PLAN']}")
        if cnt[v]['CCG']:
            lab.append(f"C{cnt[v]['CCG']}")
        ax.text(x, y - 1.55, v, ha='center', va='top', fontsize=6.5, weight='bold')
        if lab:
            ax.text(x, y + 1.45, ' '.join(lab), ha='center', va='bottom', fontsize=6)
    ax.set_title(title, fontsize=8)
    ax.set_xlim(-4, 36)
    ax.set_ylim(-7, 30)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blue', default='mip_br')
    ap.add_argument('--red', default='mip_br')
    ap.add_argument('--weather', default='typhoon')
    ap.add_argument('--design', default='D0')
    ap.add_argument('--seed', type=int, default=4)
    ap.add_argument('--periods', type=int, nargs='+', default=[1, 8, 16])
    ap.add_argument('--out', default='results/figures/snapshot')
    a = ap.parse_args()
    gm = wg.Game(a.blue, a.red, a.design, (), seed=a.seed, weather=a.weather).run()
    hs = [h for h in gm.hist if h['t'] in a.periods]
    fig, axes = plt.subplots(1, len(hs), figsize=(3.0 * len(hs), 2.9))
    axes = axes if len(hs) > 1 else [axes]
    for ax, h in zip(axes, hs):
        draw(ax, gm, h, f"t = {h['t']}   escalation ℓ = {h['ell']}   Blue share {h['share']:+.2f}")
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    fig.savefig(a.out + '.pdf')
    fig.savefig(a.out + '.png', dpi=220)
    # matching ell / share time series
    fig, ax = plt.subplots(figsize=(5.6, 1.9))
    ax.plot([h['t'] for h in gm.hist], [h['share'] for h in gm.hist], color='#1565c0', label='Blue control share')
    ax.plot([h['t'] for h in gm.hist], [h['ell'] / wg.PARAMS['L'] for h in gm.hist], color='#c62828', label='ℓ / L')
    inc = [h['t'] for h in gm.hist if h['incidents']]
    ax.scatter(inc, [gm.hist[t - 1]['ell'] / wg.PARAMS['L'] for t in inc], color='#ff8f00', s=12, zorder=3,
               label='incident')
    for h in gm.hist:
        if any(st == 'storm' for st in h['sea'].values()):
            ax.axvspan(h['t'] - 0.5, h['t'] + 0.5, color='#9e9e9e', alpha=0.25, lw=0)
    ax.set_xlabel('period t (2 days); grey = storm somewhere')
    ax.legend(fontsize=6, loc='upper left', bbox_to_anchor=(1.0, 1.0))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(a.out + '_series.pdf')
    fig.savefig(a.out + '_series.png', dpi=220)
    m = gm.metrics()
    print(f"seed {a.seed}: u_B {m['blue_payoff']:.1f} u_R {m['red_payoff']:.1f} war {m['war']} incidents {m['incidents']}"
          f" share {m['control_share']:+.3f}")


if __name__ == '__main__':
    main()
