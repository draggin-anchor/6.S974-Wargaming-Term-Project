#!/usr/bin/env python3
"""
wargame_gui.py -- Maritime gray-zone wargame prototype
6.S974 Games, Learning, and Security -- Workshop 1 (Deliverable 2)

Two players compete for control of contested maritime nodes in the Western
Pacific while managing escalation risk:

    I = {B (Blue, US Navy), R (Red, PRC)}
    K_B = {DDG}            K_R = {PLAN, CCG}   (CCG = coast guard / maritime militia)

Notation used throughout the code (matches the Workshop 1 report):

    x_{k,v}^t   ships of type k at node v (individual Ship objects are kept)
    d           endurance of a ship (periods of sea time remaining), max D_k
    c_v^t       control index of contested node v in [-1, 1] (+1 Blue, -1 Red)
    ell^t       escalation level in {0, ..., L}
    w_r^t       sea state of region r: 'calm', 'rough' or 'storm' (Nature's move)
    p_{i,v}     posture of player i at node v: 'P' (patrol/presence) or 'A' (assert)
    S_{i,v}     local strength, phi_v instantaneous share, h_v incident hazard
    g_i^t       stage payoff, u_i discounted total payoff

Sequence of play in each period (see Game.step):
    0. Nature draws the sea state of each region (weather scenario omega)
    1. observations  2. simultaneous moves + postures  3. moves resolve (movement budget)
    4. strength / control update  5. incidents + escalation  6. stage payoff
    7. termination (war when ell reaches L, or t = T)

Methods used:
    * per-period best response = mixed-integer program, solved with
      gurobipy (policy 'mip_br');
    * template game in strategic form: best responses, iterated elimination of
      strictly dominated strategies, pure Nash equilibria, maximin LP and
      correlated-equilibrium LP;
    * weather as Nature's scenario omega with probabilities, evaluated by
      expected and worst-case (robust) performance.

The simulator itself uses only the Python standard library.  gurobipy is
imported lazily and is needed only for 'mip_br', 'maximin' and the LP parts of
--equilibrium.  tkinter is imported lazily inside launch_gui().

    python3 wargame_gui.py                       # GUI
    python3 wargame_gui.py --batch --blue mip_br --red mip_br --weather nominal --seeds 100
    python3 wargame_gui.py --equilibrium         # template game analysis
    python3 wargame_gui.py --trace --seed 3 --T 10
    python3 experiments.py all                   # every table/figure in the report
"""

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict

# ============================================================================
# 1.  MODEL PARAMETERS
# ============================================================================

PARAMS = {
    # fleets: see SHIP_TYPES and FLEET below (Workshop 2: realistic fleets by nation)
    # horizon / discounting (one period = 2 days)
    'T': 180, 'delta': 0.98,          # Workshop 2: one year of two-day turns (Workshop 1: T = 60)
    # assert multiplier alpha, share smoothing kappa, control update lambda
    # (endurance D_k and strength weights w_k are per ship type in SHIP_TYPES)
    'alpha': 1.5, 'kappa': 1.0, 'lam': 0.3,
    # movement budgets F_i = F_frac_i * (fleet size), rounded (Workshop 1: 8 of 10 Blue, 10 of 14 Red)
    'F_frac': {'B': 0.8, 'R': 0.7},
    # incident hazard: h = (h0 + hA_B 1[p_B=A] + hA_R 1[p_R=A]) * min(S_B,S_R) * (1 + ell/2), where a
    # side's assert hazard blends its navy and coast guard values by the navy share of its strength.
    # Workshop 1 values: h0 0.006, hA navy 0.03 (B) / 0.036 (R), hA coast guard 0.012 (R).  h_scale
    # multiplies all hazards.  Workshop 2: 0.12, so that rule-based (moderate) play on both sides ends in
    # war in about 5% of one-year games in nominal weather (5.5% over seeds 0-399 at the 1-to-3 scale).
    'h0': 0.006, 'hA_navy': {'B': 0.03, 'R': 0.036}, 'hA_cg': {'B': 0.01, 'R': 0.012}, 'h_scale': 0.12,
    # escalation ladder: L = armed conflict; mu = probability ell drops by one after a quiet period
    'L': 5, 'ell0': 1, 'mu': 0.25,
    # payoffs
    'gamma': 0.1, 'eta': 1.0, 'W': 200.0,
    # penalty per expected incident used by the best-response MIP and the template game
    'Lambda': 20.0,
    # escalation-risk budgets eps_i of the best-response MIP (expected incidents per period)
    'eps': {'B': 0.15, 'R': 0.15},
    # detection probabilities q_{i,v}
    'q_own': 0.95, 'q_adj': 0.6, 'q_sat': 0.2,
    # design (resilient redesign) nominal-efficiency cost charged to Blue per period
    'design_cost': {'D0': 0.0, 'D1': 0.3, 'D2': 0.5, 'D3': 0.0},
    # attacks (implemented for Workshop 2; not used in the Workshop 1 results)
    'jam_start': 20, 'jam_end': 40, 'deception_contacts': 2,
    # weather: storms last storm_len periods; rough seas scale CCG strength and detection
    'storm_len': 3, 'rough_small': 0.5, 'rough_q': 0.7,
    # Workshop 2 readiness.  Maintenance: a ship operates maint_every periods, then spends
    # maint_len periods in its home port (6 months on, 3 months in); maint_init_frac of each
    # side starts in maintenance and the other ships' due dates are staggered at random.
    'maint_every': 90, 'maint_len': 45, 'maint_init_frac': 1 / 3,
    # Engineering casualty: 1% per day at sea, so 1 - 0.99^2 per two-day period; the ship
    # returns to its nearest home port and is repaired there for cas_len periods (10 days).
    'p_cas_day': 0.01, 'cas_len': 5,
    # Oiler: one per side.  It refuels ships in its zone and must return to port to
    # refuel itself every oiler_endurance periods (30 days).
    'oiler': True, 'oiler_endurance': 15,
    # template game: whole ships only (largest-remainder rounding) instead of fractional hulls
    # (Workshop 2; False reproduces the Workshop 1 template game)
    'whole_hulls': True,
}

# Weather scenarios omega in Omega: per region and period, a storm
# starts with probability p_storm (if the region is not already in a storm) and
# otherwise the sea is rough with probability p_rough.  pi = scenario weight used
# for the expected (stochastic) evaluation.
WEATHER = {
    'calm':    {'p_rough': 0.00, 'p_storm': 0.00, 'pi': 0.25},
    'nominal': {'p_rough': 0.20, 'p_storm': 0.02, 'pi': 0.40},
    'typhoon': {'p_rough': 0.35, 'p_storm': 0.06, 'pi': 0.25},
    'extreme': {'p_rough': 0.50, 'p_storm': 0.12, 'pi': 0.10},
}

OPP = {'B': 'R', 'R': 'B'}
SIGMA = {'B': +1, 'R': -1}              # sigma_B = +1, sigma_R = -1

# Ship types k (Workshop 2).  side, nation, strength weight w_k, endurance D_k (two-day periods),
# class ('navy' or 'cg' = coast guard, used by the assert hazard), small (strength halved in rough seas).
# Destroyers and cruisers carry the highest weight.  No aircraft carriers yet.
SHIP_TYPES = {
    'US-DDG': ('B', 'US', 1.0, 10, 'navy', False),   # US destroyers and cruisers (7th Fleet, Yokosuka)
    'US-LCS': ('B', 'US', 0.5, 5, 'navy', True),     # littoral combat ships (rotational)
    'JP-DDG': ('B', 'JP', 1.0, 10, 'navy', False),   # JMSDF destroyers
    'JP-FF':  ('B', 'JP', 0.7, 8, 'navy', False),    # JMSDF frigates (Mogami) and destroyer escorts (Abukuma)
    'JCG':    ('B', 'JP', 0.6, 6, 'cg', True),       # Japan Coast Guard large patrol vessels (Ishigaki)
    'PH-FF':  ('B', 'PH', 0.7, 8, 'navy', False),    # Philippine Navy frigates
    'PH-PS':  ('B', 'PH', 0.4, 5, 'navy', True),     # Philippine Navy corvettes and offshore patrol vessels
    'PCG':    ('B', 'PH', 0.6, 6, 'cg', True),       # Philippine Coast Guard cutters
    'CN-DDG': ('R', 'CN', 1.0, 10, 'navy', False),   # PLAN destroyers (incl. Type 055)
    'CN-FF':  ('R', 'CN', 0.7, 8, 'navy', False),    # PLAN frigates
    'CN-FS':  ('R', 'CN', 0.4, 5, 'navy', True),     # PLAN corvettes
    'CCG':    ('R', 'CN', 0.6, 6, 'cg', True),       # China Coast Guard large cutters
    'KP-DDG': ('R', 'KP', 1.0, 8, 'navy', False),    # North Korean destroyers (Choe Hyon)
    'KP-FS':  ('R', 'KP', 0.3, 5, 'navy', True),     # North Korean light frigates and corvettes
}
KINDS = {i: [k for k, t in SHIP_TYPES.items() if t[0] == i] for i in 'BR'}
W_K = {k: t[2] for k, t in SHIP_TYPES.items()}
D_K = {k: t[3] for k, t in SHIP_TYPES.items()}
CLASS_K = {k: t[4] for k, t in SHIP_TYPES.items()}
SMALL_K = {k: t[5] for k, t in SHIP_TYPES.items()}
NATION_K = {k: t[1] for k, t in SHIP_TYPES.items()}

# Fleets in theater: ships of each type by home port (open-source counts, see the report).
FLEET = {
    'US-DDG': {'YOK': 12}, 'US-LCS': {'GUA': 2},
    'JP-DDG': {'YOK': 13, 'SAS': 13}, 'JP-FF': {'SAS': 16}, 'JCG': {'ISG': 12},
    'PH-FF': {'PHL': 4}, 'PH-PS': {'PHL': 9}, 'PCG': {'PHL': 6},
    'CN-DDG': {'QDO': 8, 'NBO': 10, 'SAN': 12}, 'CN-FF': {'QDO': 7, 'NBO': 9, 'SAN': 11},
    'CN-FS': {'QDO': 6, 'NBO': 9, 'SAN': 10}, 'CCG': {'QDO': 19, 'NBO': 26, 'SAN': 30},
    'KP-DDG': {'NAM': 3}, 'KP-FS': {'NAM': 11},
}


# One game ship stands for HULL_SCALE real ships of its type and carries HULL_SCALE times their
# weight, so local strengths match the real fleets while the best-response MIP stays small enough
# to solve exactly.  Each type's count is divided by HULL_SCALE and rounded (at least one ship),
# then split over home ports by largest remainder.  HULL_SCALE = 1 plays the real fleets.
HULL_SCALE = 3
FLEET_REAL = FLEET
STRENGTH_UNIT = 0.05      # every real weight w_k, also halved in rough seas, is a multiple of this


def scale_fleet(fleet, n):
    out = {}
    for k, by_port in fleet.items():
        total = max(1, int(math.floor(sum(by_port.values()) / n + 0.5)))
        share = {p: c / n for p, c in by_port.items()}
        alloc = {p: int(math.floor(x)) for p, x in share.items()}
        for p in sorted(share, key=lambda p: (alloc[p] - share[p], p))[:total - sum(alloc.values())]:
            alloc[p] += 1
        out[k] = {p: c for p, c in alloc.items() if c > 0}
    return out


def set_hull_scale(n):
    """Play with one game ship per n real ships (module-wide)."""
    global HULL_SCALE, FLEET, FLEET_SIZE, W_K, STRENGTH_UNIT
    HULL_SCALE = n
    FLEET = scale_fleet(FLEET_REAL, n) if n != 1 else FLEET_REAL
    FLEET_SIZE = {i: sum(sum(FLEET[k].values()) for k in KINDS[i]) for i in 'BR'}
    W_K = {k: round(n * t[2], 6) for k, t in SHIP_TYPES.items()}
    STRENGTH_UNIT = round(0.05 * n, 6)


set_hull_scale(HULL_SCALE)

# Each nation refuels and does maintenance only at its own ports (design D1 opens Subic and
# Sasebo to US ships).  The oiler serves every ship of its side.
NATION_PORTS = {'US': ['YOK', 'GUA'], 'JP': ['YOK', 'SAS', 'ISG'], 'PH': ['PHL'],
                'CN': ['QDO', 'NBO', 'SAN'], 'KP': ['NAM']}
D1_EXTRA_PORTS = {'US': ['PHL', 'SAS']}
POLICY_NAMES = ['random', 'conservative', 'moderate', 'aggressive', 'greedy_br', 'mip_br',
                'equilibrium', 'maximin']
DESIGNS = ['D0', 'D1', 'D2', 'D3']
ATTACKS = ['jamming', 'blockade', 'deception']

# ============================================================================
# 2.  GRAPH  G = (V, E)
# ============================================================================

# code: (name, lon, lat, kind, owner)
NODES = {
    'YOK': ('Yokosuka', 139.7, 35.3, 'home', 'B'),
    'GUA': ('Guam', 144.8, 13.4, 'home', 'B'),
    'SAS': ('Sasebo', 129.7, 33.2, 'home', 'B'),
    'ISG': ('Ishigaki', 124.2, 24.3, 'home', 'B'),
    'PHL': ('Subic Bay', 120.3, 14.8, 'home', 'B'),        # Philippine ports (US ships too under D1)
    'NBO': ('Ningbo', 121.9, 29.9, 'home', 'R'),
    'SAN': ('Sanya', 109.5, 18.2, 'home', 'R'),
    'QDO': ('Qingdao', 120.4, 36.1, 'home', 'R'),
    'NAM': ('Nampo', 125.4, 38.7, 'home', 'R'),
    'SEN': ('Senkaku/ECS', 123.5, 25.8, 'contested', None),
    'MIY': ('Miyako Strait', 126.5, 25.0, 'contested', None),
    'TWN': ('Taiwan Strait', 119.8, 24.0, 'contested', None),
    'EOT': ('East of Taiwan', 124.0, 22.5, 'contested', None),
    'LUZ': ('Luzon Strait', 121.0, 20.5, 'contested', None),
    'SCB': ('Scarborough Shoal', 117.8, 15.2, 'contested', None),
    'STS': ('Second Thomas Shoal', 115.9, 9.7, 'contested', None),
    'PAR': ('Paracels', 112.0, 16.5, 'contested', None),
}
EDGES = [('YOK', 'MIY'), ('MIY', 'SEN'), ('MIY', 'EOT'), ('SEN', 'NBO'), ('SEN', 'TWN'),
         ('NBO', 'TWN'), ('TWN', 'EOT'), ('TWN', 'LUZ'), ('EOT', 'LUZ'), ('EOT', 'GUA'),
         ('GUA', 'LUZ'), ('LUZ', 'SCB'), ('LUZ', 'SAN'), ('SCB', 'STS'), ('SCB', 'PAR'),
         ('PAR', 'SAN'), ('SAN', 'STS'), ('STS', 'PAR'),
         # Workshop 2 ports
         ('PHL', 'SCB'), ('PHL', 'LUZ'), ('PHL', 'STS'), ('SAS', 'SEN'), ('SAS', 'MIY'),
         ('ISG', 'SEN'), ('ISG', 'MIY'), ('ISG', 'EOT'), ('ISG', 'TWN'),
         ('QDO', 'SEN'), ('QDO', 'NBO'), ('QDO', 'NAM')]

# node values V_v^B / V_v^R
VALUE = {
    'B': {'TWN': 10, 'SEN': 6, 'MIY': 4, 'EOT': 4, 'LUZ': 6, 'SCB': 5, 'STS': 5, 'PAR': 2},
    'R': {'TWN': 10, 'SEN': 6, 'MIY': 3, 'EOT': 4, 'LUZ': 5, 'SCB': 7, 'STS': 6, 'PAR': 6},
}
# initial control indices c_v^0
C0 = {'SEN': 0.2, 'MIY': 0.3, 'EOT': 0.2, 'PAR': -0.4, 'SCB': -0.2, 'STS': 0.0, 'TWN': 0.0, 'LUZ': 0.1}
# regions used by the template game, weather and jamming
REGIONS = {'N': ['SEN', 'MIY'], 'C': ['TWN', 'EOT', 'LUZ'], 'S': ['SCB', 'STS', 'PAR']}
REGION_OF = {v: r for r, vs in REGIONS.items() for v in vs}
RED_ISR_BONUS = {'TWN', 'SEN', 'PAR', 'LUZ'}      # shore-based sensors give Red q >= 0.6


class Graph:
    """Undirected graph with per-player shortest-path tables.

    A player may not transit the opponent's home ports, so distances are
    computed separately for Blue and Red (dist[i][u][v]).
    """

    def __init__(self, design='D0'):
        self.design = design
        self.nodes = list(NODES)
        self.edges = list(EDGES)
        self.adj = {n: [] for n in self.nodes}
        for a, b in self.edges:
            self.adj[a].append(b)
            self.adj[b].append(a)
        self.contested = [n for n in self.nodes if NODES[n][3] == 'contested']
        self.homes = {i: [n for n in self.nodes if NODES[n][3] == 'home' and NODES[n][4] == i] for i in 'BR'}
        self.dist, self.home_dist = {}, {}
        for i in 'BR':
            banned = set(self.homes[OPP[i]])
            self.dist[i] = {u: self._bfs(u, banned) for u in self.nodes}
            self.home_dist[i] = {v: min(self.dist[i][v][h] for h in self.homes[i]) for v in self.nodes}
        # ports each nation may refuel and maintain at, and the distance to the nearest one
        self.ports = {n: list(ps) + (D1_EXTRA_PORTS.get(n, []) if design == 'D1' else [])
                      for n, ps in NATION_PORTS.items()}
        side = {'US': 'B', 'JP': 'B', 'PH': 'B', 'CN': 'R', 'KP': 'R'}
        self.port_dist = {n: {v: min(self.dist[side[n]][v][h] for h in ps) for v in self.nodes}
                          for n, ps in self.ports.items()}

    def _bfs(self, src, banned):
        d = {src: 0}
        queue = [src]
        for u in queue:
            for w in self.adj[u]:
                if w in banned or w in d:
                    continue
                d[w] = d[u] + 1
                queue.append(w)
        return {v: d.get(v, 99) for v in self.nodes}

    def is_home(self, i, v):
        return v in self.homes[i]

    def is_port(self, s, v):
        """Can ship s refuel and do maintenance at node v (one of its nation's ports)?"""
        return v in self.ports[NATION_K[s.kind]]

    def nearest_port(self, s, v):
        i = s.owner
        return min(self.ports[NATION_K[s.kind]], key=lambda h: self.dist[i][v][h])


# ============================================================================
# 3.  CORE DYNAMICS HELPERS (shared by the engine and by the policies)
# ============================================================================

def weight(P, k, rough=False):
    """Strength weight w_k, halved for small hulls in rough seas."""
    return W_K[k] * (P['rough_small'] if (rough and SMALL_K[k]) else 1.0)


def raw_strength(P, cnt, i, rough=False):
    """Un-asserted strength sum_k w_k x_k of player i's types in kind-count dict cnt,
    and the navy share of it (the rest is coast guard)."""
    raw = navy = 0.0
    for k in KINDS[i]:
        n = cnt.get(k, 0)
        if n:
            x = weight(P, k, rough) * n
            raw += x
            if CLASS_K[k] == 'navy':
                navy += x
    return raw, (navy / raw if raw > 0 else 1.0)


def strength_parts(P, cnt, pB, pR, rough=False):
    """Local strengths S_B, S_R at a node from kind counts and postures.

    S_{i,v} = alpha^{1[p_iv = A]} * sum_k w_k * x_{k,v}.
    In rough seas small hulls (coast guard, corvettes, patrol ships, LCS) count half.
    Also returns each side's navy share of its strength, used by the hazard.
    """
    a = P['alpha']
    rawB, nsB = raw_strength(P, cnt, 'B', rough)
    rawR, nsR = raw_strength(P, cnt, 'R', rough)
    S_B = rawB * (a if pB == 'A' else 1.0)
    S_R = rawR * (a if pR == 'A' else 1.0)
    return S_B, S_R, (nsB, nsR)


def assert_hazard(P, i, navy_share):
    """hA_i,v: player i's assert hazard, its navy and coast guard values blended by navy share."""
    return P['hA_navy'][i] * navy_share + P['hA_cg'][i] * (1.0 - navy_share)


def hazard_rate(P, design, ell, S_B, S_R, pB, pR, shares):
    """Incident hazard h_v = h_scale (h0 + hA_B,v 1[p_B=A] + hA_R,v 1[p_R=A]) * min(S_B,S_R) * (1 + ell/2).

    hA_i,v blends the navy and coast guard assert hazards by i's navy share of strength at v
    (shares = (navy share Blue, navy share Red)).
    Design D3 (de-escalation measures): assert hazards halved when ell >= 3.
    """
    if S_B <= 0 or S_R <= 0:
        return 0.0
    hAB = assert_hazard(P, 'B', shares[0])
    hAR = assert_hazard(P, 'R', shares[1])
    if design == 'D3' and ell >= 3:
        hAB *= 0.5
        hAR *= 0.5
    base = P['h0'] + (hAB if pB == 'A' else 0.0) + (hAR if pR == 'A' else 0.0)
    return P['h_scale'] * base * min(S_B, S_R) * (1.0 + ell / 2.0)


def node_eval(P, design, ell, me, own_cnt, post_me, opp_cnt, post_opp, sea='calm'):
    """Evaluate a node from player `me`'s point of view.

    Returns (phi_me, p_inc): the instantaneous share signed so that positive is
    good for `me` (sigma_i * phi_v) and the incident probability p_v = 1 - exp(-h_v).
    own_cnt / opp_cnt are kind-count dicts (believed counts for the opponent).
    sea is the sea state at the node; in a storm nobody can operate (phi = p = 0).
    """
    if sea == 'storm':
        return 0.0, 0.0
    cnt = {**{k: opp_cnt.get(k, 0) for k in KINDS[OPP[me]]}, **{k: own_cnt.get(k, 0) for k in KINDS[me]}}
    pB, pR = (post_me, post_opp) if me == 'B' else (post_opp, post_me)
    S_B, S_R, ps = strength_parts(P, cnt, pB, pR, rough=(sea == 'rough'))
    phi = (S_B - S_R) / (S_B + S_R + P['kappa'])
    h = hazard_rate(P, design, ell, S_B, S_R, pB, pR, ps)
    return SIGMA[me] * phi, 1.0 - math.exp(-h)


def horizon_factor(P):
    """Discounted persistence of a one-period change in phi on future control.

    c_{t+1} = (1-lam) c_t + lam phi, so a unit change in phi today contributes
    lam * sum_k (delta (1-lam))^k = lam / (1 - delta (1-lam)) to the discounted
    control stream.  Policies use lam * H as the value multiplier of phi.
    """
    return 1.0 / (1.0 - P['delta'] * (1.0 - P['lam']))


class Ship:
    """One hull: owner i, type k, location x (node code), endurance d.

    Workshop 2 readiness state: due = periods of operation left before maintenance,
    hold = periods left in port (maintenance or repair), cas = has an engineering
    casualty and is heading home for repair."""
    __slots__ = ('id', 'owner', 'kind', 'loc', 'd', 'moved', 'due', 'hold', 'cas', 'maint')

    def __init__(self, sid, owner, kind, loc, d):
        self.id, self.owner, self.kind, self.loc, self.d, self.moved = sid, owner, kind, loc, d, False
        self.due, self.hold, self.cas, self.maint = 10 ** 9, 0, False, False

    @property
    def nation(self):
        return NATION_K[self.kind]

    @property
    def needs_port(self):
        """Must go to a home port (maintenance due or engineering casualty), not just refuel."""
        return self.cas or self.due <= 0

    def __repr__(self):
        return f"{self.owner}-{self.kind}#{self.id}@{self.loc}(d={self.d})"


class Oiler:
    """A side's oiler: sits at a zone of the region where its side has the best control,
    refuels own ships in its zone, and returns to port every oiler_endurance periods."""
    __slots__ = ('owner', 'loc', 'fuel', 'target')

    def __init__(self, owner, loc, fuel):
        self.owner, self.loc, self.fuel, self.target = owner, loc, fuel, None

    @property
    def on_station(self):
        return self.loc in REGION_OF



# ============================================================================
# 4.  OBSERVATIONS  o_i^t
# ============================================================================

class Obs:
    """What player i is allowed to see when choosing an action.

    Own ships, ell, all c_v (public perception), the player's belief about
    opponent ships (last-seen counts per node with an age), the opponent
    postures last observed, region closures and blockades affecting the
    player, and which own ships are under forced return this period.
    """

    def __init__(self, game, player, t, forced):
        self.game = game
        self.player = player
        self.t = t
        self.ell = game.ell
        self.c = dict(game.c)
        self.graph = game.g
        self.P = game.P
        self.design = game.design
        self.rng = game.rng
        self.ships = [s for s in game.ships if s.owner == player]
        self.forced = dict(forced)                      # ship id -> destination (may equal loc)
        self.free = [s for s in self.ships if s.id not in forced]
        self.belief = {v: dict(b) for v, b in game.belief[player].items()}
        self.seen_posture = dict(game.seen_posture[player])
        self.closed = set(game.closed)
        self.sea = dict(game.sea)                       # public sea state per region
        self.blocked = set(game.blocked) if player == 'B' else set()
        self.oiler = game.oilers.get(player)
        # movement budget left for discretionary moves (forced-return moves are charged first)
        n_forced_moves = sum(1 for sid, dest in forced.items() if dest != game.ship_by_id[sid].loc)
        self.fuel = max(0, game.F[player] - n_forced_moves)

    def legal_dests(self, ship):
        return self.game.legal_dests(ship)

    def reach_ok(self, ship, v):
        return self.game.reach_ok(ship, v)

    def opp_counts(self, v):
        """Believed opponent kind counts at node v."""
        b = self.belief.get(v, {})
        return {k: b.get(k, 0) for k in KINDS[OPP[self.player]]}

    def opp_raw(self, v):
        """Believed un-asserted opponent strength at v."""
        return sum(W_K[k] * n for k, n in self.opp_counts(v).items())

    def sea_at(self, v):
        """Sea state at node v ('calm' for home ports)."""
        return self.sea.get(REGION_OF.get(v), 'calm')

    def opp_posture(self, v):
        """Assumed opponent posture at v (last observed, default patrol)."""
        return self.seen_posture.get(v) or 'P'


# ============================================================================
# 5.  GAME ENGINE
# ============================================================================

class Game:
    """One play of the wargame.  Use step() per period or run() to the end."""

    def __init__(self, blue='moderate', red='moderate', design='D0', attacks=(), seed=0, T=None, params=None,
                 weather='calm'):
        self.P = dict(PARAMS)
        if params:
            self.P.update(params)
        if T:
            self.P['T'] = int(T)
        self.T = self.P['T']
        self.design = design
        self.attacks = set(a for a in attacks if a)
        self.seed = seed
        self.rng = random.Random(seed)
        # Nature's weather draws use their own stream, so every policy pair faces the
        # same weather sequence for a given seed (common random numbers)
        self.weather = weather
        self.wx = WEATHER[weather]
        self.wx_rng = random.Random(10007 * seed + 17)
        self.sea = {r: 'calm' for r in REGIONS}
        self.g = Graph(design)
        self.policy_names = {'B': blue, 'R': red}
        # --- ships: everybody starts in port with full endurance
        self.ships = []
        for kind, by_port in FLEET.items():
            for port, n in by_port.items():
                for _ in range(n):
                    self._add_ship(SHIP_TYPES[kind][0], kind, port)
        self.F = {i: int(round(self.P['F_frac'][i] * FLEET_SIZE[i])) for i in 'BR'}
        self.ship_by_id = {s.id: s for s in self.ships}
        # --- readiness: a share of each side starts in maintenance, the rest have staggered due dates
        # (own random stream, so the same seed gives the same maintenance schedule for every policy pair)
        ready_rng = random.Random(7919 * seed + 3)
        for i in 'BR':
            own = [s for s in self.ships if s.owner == i]
            n_maint = round(self.P['maint_init_frac'] * len(own))
            for j, s in enumerate(ready_rng.sample(own, len(own))):
                if j < n_maint:
                    s.maint, s.hold, s.due = True, ready_rng.randint(1, self.P['maint_len']), 0
                else:
                    s.due = ready_rng.randint(1, self.P['maint_every'])
        self.p_cas = 1.0 - (1.0 - self.P['p_cas_day']) ** 2
        self.oilers = {}
        if self.P['oiler']:
            for i in 'BR':
                self.oilers[i] = Oiler(i, self.g.homes[i][0], self.P['oiler_endurance'])
        # --- state
        self.c = dict(C0)
        self.ell = self.P['ell0']
        self.t = 0
        self.postures = {'B': {v: 'P' for v in self.g.contested}, 'R': {v: 'P' for v in self.g.contested}}
        self.closed = {}            # node -> periods of storm closure remaining
        self.blocked = set()        # nodes whose incident edges Blue cannot use this period
        self.jam_region = None
        # beliefs: last-seen opponent counts per node (public at t=0)
        self.belief = {i: {} for i in 'BR'}
        self.seen_posture = {i: {} for i in 'BR'}
        counts = self.counts()
        for i in 'BR':
            for v in self.g.nodes:
                self.belief[i][v] = {k: counts[v][k] for k in KINDS[OPP[i]]}
                self.belief[i][v]['age'] = 0
        # --- bookkeeping
        self.u = {'B': 0.0, 'R': 0.0}
        self.fuel_used = {'B': 0, 'R': 0}
        self.n_incidents = 0
        self.war, self.war_t = False, None
        self.max_ell, self.ell_sum, self.share_sum = self.ell, 0.0, 0.0
        self.done = False
        self.hist = []              # per-period records for plots / trace
        self.events = []            # (t, text) event log
        self.last_incidents = set()
        self.last_moves = {'B': 0, 'R': 0}
        self.policy = {i: make_policy(self.policy_names[i], i, self) for i in 'BR'}

    # ------------------------------------------------------------------ setup
    def _add_ship(self, owner, kind, loc):
        self.ships.append(Ship(len(self.ships), owner, kind, loc, D_K[kind]))

    # ------------------------------------------------------------- utilities
    def counts(self):
        """x_{k,v}: kind counts per node."""
        cnt = {v: dict.fromkeys(SHIP_TYPES, 0) for v in self.g.nodes}
        for s in self.ships:
            cnt[s.loc][s.kind] += 1
        return cnt

    def ships_at(self, v, owner=None):
        return [s for s in self.ships if s.loc == v and (owner is None or s.owner == owner)]

    def control_share(self):
        """Blue value-weighted control share: sum_v V^B_v c_v / sum_v V^B_v."""
        tot = sum(VALUE['B'].values())
        return sum(VALUE['B'][v] * self.c[v] for v in self.g.contested) / tot

    def refuel_dist(self, s, v):
        """Distance from v to ship s's nearest refuel point: one of its nation's ports or its side's oiler on station."""
        i = s.owner
        d = self.g.port_dist[s.nation][v]
        o = self.oilers.get(i)
        if o is not None and o.on_station:
            d = min(d, self.g.dist[i][v][o.loc])
        return d

    def legal_dests(self, s, returning=False):
        """Nodes ship s may occupy next period (stay is always allowed).

        Rules: one edge per period; storm-closed nodes cannot be entered and
        ships inside them must stay; a player may not enter the opponent's home
        ports; Blue cannot use edges incident to a blockaded node (except that a
        ship under forced return may leave it, so hulls are not trapped at sea);
        a ship may not sail to a node it could not return home from (unless the
        move takes it closer to home).
        """
        g, i = self.g, s.owner
        if s.loc in self.closed:
            return [s.loc]
        out = [s.loc]
        for w in g.adj[s.loc]:
            if w in self.closed or w in g.homes[OPP[i]]:
                continue
            if i == 'B' and (w in self.blocked or (s.loc in self.blocked and not returning)):
                continue
            toward_home = self.refuel_dist(s, w) < self.refuel_dist(s, s.loc)
            if not toward_home and (s.d - 1) < self.refuel_dist(s, w):
                continue
            out.append(w)
        return out

    def reach_ok(self, s, v):
        """Can ship s reach v and still spend at least one period there before forced return?"""
        g, i = self.g, s.owner
        if s.needs_port:
            return False
        return s.d - g.dist[i][s.loc][v] >= self.refuel_dist(s, v)

    def _forced_move(self, s):
        """Forced return: a ship with d <= distance-to-home must head home.
        A ship that has just arrived in port must spend one period refitting.
        Returns the forced destination or None if the ship is free."""
        g, i = self.g, s.owner
        if g.is_port(s, s.loc):
            if s.hold > 0 or s.needs_port:
                return s.loc                                # in maintenance or repair
            return s.loc if s.d < D_K[s.kind] else None
        pd = g.port_dist[s.nation]
        if s.needs_port:                                    # maintenance due or casualty: head to own port
            hops = [w for w in self.legal_dests(s, returning=True) if w != s.loc and pd[w] < pd[s.loc]]
            return self.rng.choice(hops) if hops else s.loc
        o = self.oilers.get(i)
        if o is not None and o.loc == s.loc and s.d < D_K[s.kind]:
            return s.loc                                    # refueling alongside the oiler
        rd = self.refuel_dist(s, s.loc)
        if s.d <= rd:
            hops = [w for w in self.legal_dests(s, returning=True) if w != s.loc and self.refuel_dist(s, w) < rd]
            return self.rng.choice(hops) if hops else s.loc
        return None

    def detect_prob(self, i, v):
        """q_{i,v}: probability that player i detects opponent ships at v this period."""
        P, g = self.P, self.g
        own_nodes = {s.loc for s in self.ships if s.owner == i}
        if v in own_nodes:
            q = P['q_own']
        elif any(n in own_nodes for n in g.adj[v]) or g.is_home(i, v) or any(g.is_home(i, n) for n in g.adj[v]):
            q = P['q_adj']
        else:
            q = P['q_sat']
        if i == 'R' and v in RED_ISR_BONUS:
            q = max(q, 0.6)
        if self.sea.get(REGION_OF.get(v), 'calm') != 'calm':
            q *= P['rough_q']                               # cloud / sea clutter degrade sensing
        if i == 'B':
            if self.design == 'D2' and v in REGION_OF:
                q = max(q, 0.6)                             # redundant ISR floor
            if self.jam_region and REGION_OF.get(v) == self.jam_region:
                q = max(q * 0.5, 0.45) if self.design == 'D2' else q * 0.5
        return q

    def _observe(self, i):
        """Update player i's belief about opponent ships (step 1 of the period)."""
        counts = self.counts()
        opp = OPP[i]
        for v in self.g.nodes:
            if self.g.is_home(i, v):
                continue
            if self.rng.random() < self.detect_prob(i, v):
                self.belief[i][v] = {k: counts[v][k] for k in KINDS[opp]}
                self.belief[i][v]['age'] = 0
                self.seen_posture[i][v] = self.postures[opp].get(v, 'P') if v in REGION_OF else 'P'
            else:
                self.belief[i][v]['age'] += 1
        if i == 'B' and 'deception' in self.attacks:
            # Red deception: phantom contacts injected into Blue's picture
            for _ in range(self.P['deception_contacts']):
                v = self.rng.choice(self.g.contested)
                kind = self.rng.choice(KINDS['R'])
                self.belief['B'][v][kind] += 1
                self.belief['B'][v]['age'] = 0

    def _blockade_override(self, moves, post, forced):
        """Blockade attack: Red keeps a two-hull CCG detachment asserting at SCB."""
        g = self.g
        ccg = [s for s in self.ships if s.owner == 'R' and s.kind == 'CCG' and s.id not in forced]
        at = [s for s in ccg if s.loc == 'SCB']
        for s in at:
            moves.pop(s.id, None)                           # hold station
        need = 2 - len(at)
        if need > 0:
            cands = [s for s in ccg if s.loc != 'SCB' and self.reach_ok(s, 'SCB')]
            cands.sort(key=lambda s: g.dist['R'][s.loc]['SCB'])
            for s in cands[:need]:
                hops = [w for w in self.legal_dests(s) if g.dist['R'][w]['SCB'] < g.dist['R'][s.loc]['SCB']]
                if hops:
                    moves[s.id] = hops[0]
        post['SCB'] = 'A'
        return moves, post

    # ------------------------------------------------------------- readiness
    def _readiness(self, ev):
        """Maintenance clock, engineering casualties, and repairs (after moves)."""
        P, g = self.P, self.g
        for s in self.ships:
            home = g.is_port(s, s.loc)
            if s.hold > 0:
                s.hold -= 1
                if s.hold == 0:
                    if s.maint:
                        s.maint, s.due = False, P['maint_every']
                    s.cas = False
                    s.d = D_K[s.kind]
                continue
            if home and s.needs_port:
                if s.due <= 0:
                    s.maint, s.hold = True, P['maint_len']
                    s.cas = False                               # repairs folded into the maintenance period
                    ev.append(f"{s.owner} {s.kind}#{s.id} enters maintenance at {s.loc}")
                else:
                    s.hold = P['cas_len']
                continue
            s.due -= 1
            if not home and not s.cas and self.rng.random() < self.p_cas:
                s.cas = True
                ev.append(f"{s.owner} {s.kind}#{s.id} engineering casualty at {s.loc}: returning to port")

    def available(self, i):
        """Ships of player i not in maintenance or repair."""
        return sum(1 for s in self.ships if s.owner == i and s.hold == 0)

    def best_region(self, i):
        """Region where player i has the best value-weighted control."""
        def score(r):
            vs = REGIONS[r]
            return SIGMA[i] * sum(VALUE[i][v] * self.c[v] for v in vs) / sum(VALUE[i][v] for v in vs)
        return max(REGIONS, key=score)

    def _move_oilers(self, ev):
        """Oiler rule: one edge per period toward a random zone of the side's best-control region
        (it wanders among that region's zones and follows if the region changes); it heads home
        when its own fuel only just covers the trip, and refuels with one period in port."""
        g = self.g
        for i, o in self.oilers.items():
            if g.is_home(i, o.loc):
                if o.fuel < self.P['oiler_endurance']:
                    o.fuel = self.P['oiler_endurance']          # one period in port to refuel
                    continue
            else:
                o.fuel -= 1
            if not g.is_home(i, o.loc) and o.fuel <= g.home_dist[i][o.loc]:
                dest = min(g.homes[i], key=lambda h: g.dist[i][o.loc][h])
            else:
                region = self.best_region(i)
                if o.target not in REGIONS[region] or o.loc == o.target:
                    o.target = self.rng.choice(REGIONS[region])
                dest = o.target
            if dest == o.loc or o.loc in self.closed:
                continue
            hops = [w for w in g.adj[o.loc] if w not in self.closed and w not in g.homes[OPP[i]]
                    and g.dist[i][w][dest] < g.dist[i][o.loc][dest]]
            if hops:
                o.loc = hops[0]

    # ------------------------------------------------------------------ step
    def step(self):
        """Advance one period (the transition s^t -> s^{t+1})."""
        if self.done:
            return
        P, g, rng = self.P, self.g, self.rng
        t = self.t + 1
        ev = []
        # ---- 0. Nature: sea state per region (storms persist storm_len periods and close the region)
        for v in list(self.closed):
            self.closed[v] -= 1
            if self.closed[v] <= 0:
                del self.closed[v]
        for r, nodes in REGIONS.items():
            u1, u2 = self.wx_rng.random(), self.wx_rng.random()     # always draw two numbers (common random numbers)
            if nodes[0] in self.closed:
                self.sea[r] = 'storm'
            elif u1 < self.wx['p_storm']:
                self.sea[r] = 'storm'
                for v in nodes:
                    self.closed[v] = P['storm_len']
                ev.append(f"Storm closes region {r} ({', '.join(nodes)}) for {P['storm_len']} periods")
            else:
                self.sea[r] = 'rough' if u2 < self.wx['p_rough'] else 'calm'
        self.blocked = set()
        if 'blockade' in self.attacks:
            for v in ('SCB', 'STS'):
                if self.postures['R'].get(v) == 'A' and any(s.kind == 'CCG' for s in self.ships_at(v, 'R')):
                    self.blocked.add(v)
            if self.blocked:
                ev.append("Red CCG blockade: Blue cannot transit edges at " + ', '.join(sorted(self.blocked)))
        self.jam_region = None
        if 'jamming' in self.attacks and P['jam_start'] <= t <= P['jam_end']:
            counts = self.counts()
            score = {r: sum(VALUE['R'][v] * strength_parts(P, counts[v], 'P', 'P')[1] for v in vs)
                     for r, vs in REGIONS.items()}
            self.jam_region = max(score, key=lambda r: (score[r], r == 'N'))
            if t == P['jam_start']:
                ev.append(f"Red jamming begins: Blue ISR halved in region {self.jam_region} until t={P['jam_end']}")
        # ---- 1. observations
        for i in 'BR':
            self._observe(i)
        # ---- 2. decisions (forced returns are fixed before the policies act)
        forced = {'B': {}, 'R': {}}
        for s in self.ships:
            fm = self._forced_move(s)
            if fm is not None:
                forced[s.owner][s.id] = fm
                if fm != s.loc:
                    ev.append(f"{s.owner} {s.kind}#{s.id} forced return {s.loc}->{fm} (d={s.d})")
        moves, post = {}, {}
        for i in 'BR':
            obs = Obs(self, i, t, forced[i])
            m, p = self.policy[i].act(obs)
            m, p = dict(m), dict(p)
            if i == 'R' and 'blockade' in self.attacks:
                m, p = self._blockade_override(m, p, forced['R'])
            moves[i], post[i] = m, p
        # ---- 3. resolve moves under the movement budget F_i (forced moves charged first)
        for i in 'BR':
            budget = self.F[i]
            plan = {}
            for sid, dest in forced[i].items():
                if dest != self.ship_by_id[sid].loc and budget > 0:
                    plan[sid] = dest
                    budget -= 1
            for sid, dest in moves[i].items():
                s = self.ship_by_id[sid]
                if sid in forced[i] or dest == s.loc or dest not in self.legal_dests(s):
                    continue
                if budget <= 0:
                    ev.append(f"{i}: movement budget exhausted, {s.kind}#{sid} holds at {s.loc}")
                    continue
                plan[sid] = dest
                budget -= 1
            for sid, dest in plan.items():
                self.ship_by_id[sid].loc = dest
                self.ship_by_id[sid].moved = True
            self.last_moves[i] = len(plan)
            self.fuel_used[i] += len(plan)
        # endurance: -1 per period at sea; reset to D_k after a full period in port or alongside the oiler
        for s in self.ships:
            o = self.oilers.get(s.owner)
            if g.is_port(s, s.loc):
                if not s.moved:
                    s.d = D_K[s.kind]
            elif o is not None and o.loc == s.loc and not s.moved:
                s.d = D_K[s.kind]
            else:
                s.d = max(0, s.d - 1)
            s.moved = False
        self._readiness(ev)
        self._move_oilers(ev)
        for i in 'BR':
            self.postures[i] = {v: ('A' if post[i].get(v) == 'A' else 'P') for v in g.contested}
        # ---- 4. strength and control update; 5. incidents
        counts = self.counts()
        incidents = set()
        for v in g.contested:
            pB, pR = self.postures['B'][v], self.postures['R'][v]
            sea = self.sea[REGION_OF[v]]
            S_B, S_R, ps = strength_parts(P, counts[v], pB, pR, rough=(sea == 'rough'))
            if sea == 'storm':
                S_B = S_R = 0.0                             # no operations in a storm
            if sea != 'storm':                              # a storm halts operations: control is frozen
                phi = (S_B - S_R) / (S_B + S_R + P['kappa'])
                self.c[v] = (1 - P['lam']) * self.c[v] + P['lam'] * phi
            h = hazard_rate(P, self.design, self.ell, S_B, S_R, pB, pR, ps)
            if h > 0 and rng.random() < 1.0 - math.exp(-h):
                incidents.add(v)
        for v in incidents:
            self.ell = min(P['L'], self.ell + 1)
            ev.append(f"INCIDENT at {v} ({NODES[v][0]}): ell -> {self.ell}")
        if not incidents:
            mu = 0.5 if (self.design == 'D3' and self.ell >= 3) else P['mu']
            if self.ell > 0 and rng.random() < mu:
                self.ell -= 1
                ev.append(f"Tensions ease: ell -> {self.ell}")
        self.n_incidents += len(incidents)
        self.last_incidents = incidents
        # ---- 6. stage payoffs g_i^t
        disc = P['delta'] ** (t - 1)
        gB = sum(VALUE['B'][v] * self.c[v] for v in g.contested) - P['gamma'] * self.last_moves['B'] \
            - P['eta'] * self.ell - P['design_cost'][self.design]
        gR = -sum(VALUE['R'][v] * self.c[v] for v in g.contested) - P['gamma'] * self.last_moves['R'] \
            - P['eta'] * self.ell
        self.u['B'] += disc * gB
        self.u['R'] += disc * gR
        # ---- 7. termination
        self.t = t
        self.max_ell = max(self.max_ell, self.ell)
        self.ell_sum += self.ell
        self.share_sum += self.control_share()
        if self.ell >= P['L']:
            self.war, self.war_t = True, t
            self.u['B'] -= P['W']
            self.u['R'] -= P['W']
            self.done = True
            ev.append(f"*** ARMED CONFLICT (ell = L) at t={t}: both players receive -W ***")
        elif t >= self.T:
            self.done = True
        for text in ev:
            self.events.append((t, text))
        self.hist.append({'t': t, 'ell': self.ell, 'share': self.control_share(), 'gB': gB, 'gR': gR,
                          'incidents': sorted(incidents), 'postures': {i: dict(self.postures[i]) for i in 'BR'},
                          'c': dict(self.c), 'counts': counts, 'uB': self.u['B'], 'uR': self.u['R'],
                          'sea': dict(self.sea), 'oilers': {i: o.loc for i, o in self.oilers.items()},
                          'avail': {i: self.available(i) for i in 'BR'}})

    def run(self):
        while not self.done:
            self.step()
        return self

    def metrics(self):
        n = max(1, self.t)
        return {
            'seed': self.seed, 'blue_payoff': self.u['B'], 'red_payoff': self.u['R'],
            'control_share': self.share_sum / n, 'war': int(self.war), 'war_t': self.war_t if self.war else '',
            'max_ell': self.max_ell, 'mean_ell': self.ell_sum / n, 'incidents': self.n_incidents,
            'blue_fuel': self.fuel_used['B'], 'red_fuel': self.fuel_used['R'], 'periods': self.t,
            'blue_avail': statistics.fmean(h['avail']['B'] for h in self.hist) if self.hist else 0,
            'red_avail': statistics.fmean(h['avail']['R'] for h in self.hist) if self.hist else 0,
        }


# ============================================================================
# 6.  POLICIES
# ============================================================================
#
# A policy maps an observation to (moves, postures):
#   moves:    {ship_id: destination_node}  for free (non-forced) ships, in priority order
#   postures: {contested_node: 'P' | 'A'}
# The engine validates legality and enforces the movement budget, so a policy that
# returns an illegal move simply has that ship hold position.

def risk_budget(eps, ell, P):
    """Effective per-period expected-incident budget: eps scaled down as ell rises."""
    return eps * max(0.0, 1.0 - ell / P['L'])


class Policy:
    name = 'base'

    def __init__(self, player, rng):
        self.player = player
        self.rng = rng

    def act(self, obs):
        raise NotImplementedError

    # --- helpers shared by the heuristic policies -------------------------
    @staticmethod
    def next_hop(obs, ship, target):
        """One legal step from ship.loc toward target (None if no progress possible)."""
        g, i = obs.graph, ship.owner
        hops = [w for w in obs.legal_dests(ship) if w != ship.loc and g.dist[i][w][target] < g.dist[i][ship.loc][target]]
        if not hops:
            return None
        # prefer stepping through a contested node (presence en route is useful)
        hops.sort(key=lambda w: (w not in REGION_OF, w))
        return hops[0]

    @staticmethod
    def planned_counts(obs, pos):
        """Own kind counts per node given planned positions pos[ship_id]."""
        cnt = defaultdict(lambda: defaultdict(int))
        for s in obs.ships:
            v = pos.get(s.id, obs.forced.get(s.id, s.loc))
            cnt[v][s.kind] += 1
        return cnt


class RandomPolicy(Policy):
    """Benchmark: random feasible moves, random postures."""
    name = 'random'

    def act(self, obs):
        moves, post = {}, {}
        for s in obs.free:
            dests = obs.legal_dests(s)
            if len(dests) > 1 and self.rng.random() < 0.5:
                moves[s.id] = self.rng.choice(dests[1:])
        for v in obs.graph.contested:
            post[v] = 'A' if self.rng.random() < 0.5 else 'P'
        return moves, post


class HeuristicPolicy(Policy):
    """Heuristic types parameterized by risk tolerance theta.

    conservative theta=0.2, moderate theta=0.5, aggressive theta=0.8.
    Allocation: greedy assignment of free ships to contested nodes by a
    value-per-opponent-threat score (marginal control gain of one more hull,
    discounted by transit distance, divided by (1 + (1-theta) * opponent threat)).
    Postures:
      aggressive   asserts unless ell >= 4
      moderate     asserts only where it has local superiority and ell <= 2
      conservative never asserts; withdraws from nodes with opponent present when ell >= 3
    Escalation-risk budget: expected number of incidents this period must be
    <= epsilon(theta) in {0.05, 0.15, 0.40}; postures and then deployments are
    trimmed until the budget holds.  The budget is tightened as the ladder
    rises, eps_eff = eps * (1 - ell/L) (see risk_budget), which is what keeps
    the heuristic types from drifting into war (an ell-dependent threshold).
    """
    EPS = {0.2: 0.05, 0.5: 0.15, 0.8: 0.40}

    def __init__(self, player, rng, theta, label):
        super().__init__(player, rng)
        self.theta = theta
        self.eps = self.EPS[theta]
        self.name = label

    # posture rule for a node where we have ships
    def _posture(self, ell, own_raw, opp_raw):
        if self.theta >= 0.8:
            return 'A' if ell < 4 else 'P'
        if self.theta >= 0.5:
            return 'A' if (ell <= 2 and own_raw > opp_raw) else 'P'
        return 'P'

    def act(self, obs):
        g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
        w, lam, H = W_K, P['lam'], horizon_factor(P)
        V = VALUE[me]
        opp_cnt = {v: obs.opp_counts(v) for v in g.contested}
        opp_raw = {v: obs.opp_raw(v) for v in g.contested}
        targets = list(g.contested)
        if self.theta <= 0.2 and ell >= 3:          # conservative: withdraw where opponent present
            targets = [v for v in targets if opp_raw[v] == 0]
        # ---- greedy allocation of free ships to target nodes
        own = {v: defaultdict(int) for v in g.contested}
        for s in obs.ships:
            if s.id in obs.forced and obs.forced[s.id] in own:
                own[obs.forced[s.id]][s.kind] += 1
        assign, score_of = {}, {}

        def marginal(kind, loc, v):
            base = node_eval(P, obs.design, ell, me, own[v], 'P', opp_cnt[v], 'P', obs.sea_at(v))[0]
            own[v][kind] += 1
            new = node_eval(P, obs.design, ell, me, own[v], 'P', opp_cnt[v], 'P', obs.sea_at(v))[0]
            own[v][kind] -= 1
            dist = g.dist[me][loc][v]
            gain = V[v] * lam * H * (new - base) * (P['delta'] ** dist) - P['gamma'] * dist
            return gain / (1.0 + (1.0 - self.theta) * opp_raw[v])

        # ships of one type at one node that can reach the same targets score the same, so
        # score groups, and after each assignment rescore only the node that changed
        groups = {}
        for s in obs.free:
            key = (s.kind, s.loc, tuple(v for v in targets if obs.reach_ok(s, v)))
            groups.setdefault(key, []).append(s)
        score = {(key, v): marginal(key[0], key[1], v) for key in groups for v in key[2]}
        while True:
            best, best_sc = None, 0.05
            for key, members in groups.items():
                if not members:
                    continue
                for v in key[2]:
                    sc = score[key, v]
                    if sc > best_sc:
                        best, best_sc = (key, v), sc
            if best is None:
                break
            key, v = best
            s = groups[key].pop(0)
            assign[s.id], score_of[s.id] = v, best_sc
            own[v][s.kind] += 1
            for key2 in groups:
                if v in key2[2]:
                    score[key2, v] = marginal(key2[0], key2[1], v)
        # ---- moves: step toward the assigned node; unassigned ships at sea head home
        pos = {}
        moves_pri = []                                    # (priority, ship id, dest)
        for s in obs.free:
            tgt = assign.get(s.id)
            if tgt is None:
                if not g.is_home(me, s.loc) and (s.loc in REGION_OF and (self.theta <= 0.2 or opp_raw[s.loc] > 0)):
                    tgt = g.nearest_port(s, s.loc)
                    pri = -1.0
                else:
                    pos[s.id] = s.loc
                    continue
            else:
                pri = score_of[s.id]
            if tgt == s.loc:
                pos[s.id] = s.loc
                continue
            hop = self.next_hop(obs, s, tgt)
            if hop is None:
                pos[s.id] = s.loc
            else:
                moves_pri.append((pri, s.id, hop))
        moves_pri.sort(key=lambda x: -x[0])
        moves = {}
        for k, (pri, sid, hop) in enumerate(moves_pri):
            if k < obs.fuel:
                moves[sid] = hop
                pos[sid] = hop
            else:
                pos[sid] = obs.game.ship_by_id[sid].loc
        # ---- postures
        cnt = self.planned_counts(obs, pos)
        post = {}
        for v in g.contested:
            if sum(cnt[v].values()) > 0:
                own_raw = sum(w[k] * n for k, n in cnt[v].items())
                post[v] = self._posture(ell, own_raw, opp_raw[v])
        # ---- escalation-risk budget: sum_v p_v <= eps
        def risk(v):
            return node_eval(P, obs.design, ell, me, cnt[v], post.get(v, 'P'), opp_cnt[v], obs.opp_posture(v),
                             obs.sea_at(v))[1]
        for _ in range(40):
            risks = {v: risk(v) for v in g.contested if sum(cnt[v].values()) > 0}
            if sum(risks.values()) <= risk_budget(self.eps, ell, P):
                break
            asserting = [v for v in risks if post.get(v) == 'A']
            if asserting:
                post[max(asserting, key=risks.get)] = 'P'          # de-escalate posture first
                continue
            v = max(risks, key=risks.get)
            # withdraw one hull from the riskiest node: cancel an arrival, else send a ship home
            arriving = [sid for sid, dest in moves.items() if dest == v]
            if arriving:
                sid = arriving[-1]
                del moves[sid]
                pos[sid] = obs.game.ship_by_id[sid].loc
            else:
                here = [s for s in obs.free if pos.get(s.id, s.loc) == v and s.id not in moves]
                if not here or len(moves) >= obs.fuel:
                    break
                s = here[-1]
                home = g.nearest_port(s, v)
                hop = self.next_hop(obs, s, home)
                if hop is None:
                    break
                moves[s.id] = hop
                pos[s.id] = hop
            cnt = self.planned_counts(obs, pos)
            post = {v2: p for v2, p in post.items() if sum(cnt[v2].values()) > 0}
        return moves, post


class GreedyBRPolicy(Policy):
    """Myopic best response: a greedy/local-search heuristic for the per-period
    MIP solved exactly by MIPBRPolicy (kept as a solver-free fallback and to
    measure how much the heuristic loses; see experiments.py gap).

    Given believed opponent positions x_hat (and last-seen postures), choose
    integer ship moves and postures maximizing

        J = sum_v V_v^i sigma_i lam H phi_v(x, x_hat) - gamma * moves - Lambda * E[incidents]

    subject to one-edge moves, forced returns, the movement budget F_i and the risk
    budget sum_v p_v <= epsilon (moderate, 0.15, tightened as ell rises).  The exact problem is a small
    MIP; here it is solved approximately by greedy marginal-gain assignment of
    ships followed by a few rounds of single-ship local search, with a posture
    pass after each round.  (H = horizon factor turning a one-period phi change
    into its discounted control value.)
    """
    name = 'greedy_br'
    ROUNDS = 3

    def act(self, obs):
        g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
        lam, H, Lam, gamma = P['lam'], horizon_factor(P), P['Lambda'], P['gamma']
        V = VALUE[me]
        eps = risk_budget(P['eps'][me], ell, P)
        opp_cnt = {v: obs.opp_counts(v) for v in g.contested}
        opp_post = {v: obs.opp_posture(v) for v in g.contested}
        own = {v: defaultdict(int) for v in g.nodes}
        pos = {}
        for s in obs.ships:
            v = obs.forced.get(s.id, s.loc)
            own[v][s.kind] += 1
            pos[s.id] = v
        post = {v: 'P' for v in g.contested}
        cands = {s.id: candidate_dests(obs, s) for s in obs.free}
        term, risk = {}, {}

        def evaluate(v):
            """(value, p_inc) contribution of contested node v under current plan."""
            if v not in REGION_OF:
                return 0.0, 0.0
            phi, p = node_eval(P, obs.design, ell, me, own[v], post[v], opp_cnt[v], opp_post[v], obs.sea_at(v))
            return V[v] * lam * H * phi - Lam * p, p

        for v in g.contested:
            term[v], risk[v] = evaluate(v)
        nmoves = sum(1 for s in obs.free if pos[s.id] != s.loc)

        def try_move(s, w):
            """Return (delta J, new terms) for moving s from pos[s.id] to w, or None if infeasible."""
            a = pos[s.id]
            if a == w:
                return None
            dm = (1 if w != s.loc else 0) - (1 if a != s.loc else 0)
            if nmoves + dm > obs.fuel:
                return None
            own[a][s.kind] -= 1
            own[w][s.kind] += 1
            ta, ra = evaluate(a)
            tw, rw = evaluate(w)
            own[a][s.kind] += 1
            own[w][s.kind] -= 1
            tot_risk = sum(risk.values())
            new_risk = tot_risk - risk.get(a, 0.0) - risk.get(w, 0.0) + ra + rw
            if new_risk > eps and new_risk > tot_risk:
                return None
            dJ = (ta + tw) - (term.get(a, 0.0) + term.get(w, 0.0)) - gamma * dm
            return dJ, (ta, ra, tw, rw, dm)

        def commit(s, w, info):
            nonlocal nmoves
            a = pos[s.id]
            ta, ra, tw, rw, dm = info
            own[a][s.kind] -= 1
            own[w][s.kind] += 1
            if a in REGION_OF:
                term[a], risk[a] = ta, ra
            if w in REGION_OF:
                term[w], risk[w] = tw, rw
            pos[s.id] = w
            nmoves += dm

        def posture_pass():
            for v in g.contested:
                if sum(own[v].values()) == 0:
                    post[v] = 'P'
                    term[v], risk[v] = evaluate(v)
                    continue
                best = None
                for p in ('P', 'A'):
                    post[v] = p
                    tv, rv = evaluate(v)
                    tot = sum(risk.values()) - risk[v] + rv
                    if p == 'A' and tot > eps:
                        continue
                    if best is None or tv > best[0]:
                        best = (tv, rv, p)
                post[v] = best[2]
                term[v], risk[v] = best[0], best[1]

        order = list(obs.free)
        self.rng.shuffle(order)
        for rnd in range(self.ROUNDS + 1):
            improved = False
            for s in order:
                best = None
                for w in cands[s.id]:
                    r = try_move(s, w)
                    if r and r[0] > 1e-9 and (best is None or r[0] > best[0]):
                        best = (r[0], w, r[1])
                if best:
                    commit(s, best[1], best[2])
                    improved = True
            posture_pass()
            if not improved and rnd > 0:
                break
        moves = {s.id: pos[s.id] for s in obs.free if pos[s.id] != s.loc}
        return moves, {v: p for v, p in post.items() if sum(own[v].values()) > 0}


def candidate_dests(obs, s):
    """Destinations the best response considers for free ship s: stay, go home,
    or a neighbor from which the ship can still operate and return."""
    g, me = obs.graph, obs.player
    return [w for w in obs.legal_dests(s) if w == s.loc or g.is_port(s, w) or obs.reach_ok(s, w)]


def plan_value(obs, moves, post):
    """Objective of the per-period best-response problem for a plan (moves, postures):
        J = sum_v [V_v lam H phi_v - Lambda p_v] - gamma * (#moves),
    and the plan's expected incidents sum_v p_v.  Used to compare plans."""
    g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
    cnt = Policy.planned_counts(obs, {s.id: moves.get(s.id, s.loc) for s in obs.free})
    J, risk = -P['gamma'] * len(moves), 0.0
    for v in g.contested:
        if sum(cnt[v].values()) == 0:
            continue
        phi, pv = node_eval(P, obs.design, ell, me, cnt[v], post.get(v, 'P'), obs.opp_counts(v),
                            obs.opp_posture(v), obs.sea_at(v))
        J += VALUE[me][v] * P['lam'] * horizon_factor(P) * phi - P['Lambda'] * pv
        risk += pv
    return J, risk


class MIPBREnumPolicy(Policy):
    """Workshop 1 best-response MIP (count-vector options), kept to check the Workshop 2
    flow version (MIPBRPolicy) on the Workshop 1 fleet.  It cannot be built for the
    Workshop 2 fleets: the option list per zone is 2 * prod_k (A_k,v + 1).

    Exact per-period best response: the mixed-integer program of Section 3 of
    the report, solved with gurobipy.

    Given the believed opponent counts x_hat (and last-seen postures) and the
    current sea state, choose binary moves y_{s,w} (ship s goes to node w, one
    edge per period) and, at each contested node v, one binary option
    b_{v,(n,p)} = "I will have n hulls at v with posture p", to

        max  sum_v sum_(n,p) a_v(n,p) b_{v,(n,p)} - gamma sum_{s, w != loc(s)} y_{s,w}
        s.t. sum_w y_{s,w} = 1                                    (each free ship one destination)
             sum_{s, w != loc(s)} y_{s,w} <= F_i - forced moves   (movement budget)
             x_{k,v} = fixed_{k,v} + sum_{s of type k} y_{s,v}   (flow conservation)
             sum_(n,p) b_{v,(n,p)} = 1,  sum_(n,p) n_k b_{v,(n,p)} = x_{k,v}
             sum_v sum_(n,p) rho_v(n,p) b_{v,(n,p)} <= eps_i (1 - ell/L)   (escalation-risk budget)
             y, b binary

    with a_v(n,p) = V_v lam H phi_v(n,p) - Lambda rho_v(n,p).  phi and rho are
    nonlinear in the counts, so they are tabulated for every count option: the
    b variables make the objective and the risk constraint linear.  The risk
    budget eps_i is the feasible-region parameter: conservative / moderate /
    aggressive = eps in {0.05, 0.15, 0.40}.  If forced returns alone break the
    budget, a penalized slack keeps the problem feasible.
    """
    name = 'mip_br_enum'
    _env = None

    @classmethod
    def env(cls):
        if cls._env is None:
            try:
                import gurobipy as gp
            except ImportError as e:
                raise SystemExit("policy 'mip_br' needs gurobipy (pip install gurobipy; the free "
                                 "size-limited license is enough). Use 'greedy_br' without a solver.") from e
            cls._env = gp.Env(params={'OutputFlag': 0, 'Threads': 1})
        return cls._env

    def act(self, obs):
        import gurobipy as gp
        g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
        lam, H, Lam, gamma = P['lam'], horizon_factor(P), P['Lambda'], P['gamma']
        kinds = KINDS[me]
        eps = risk_budget(P['eps'][me], ell, P)
        fixed = {v: defaultdict(int) for v in g.nodes}
        for s in obs.ships:
            if s.id in obs.forced:
                fixed[obs.forced[s.id]][s.kind] += 1
        cands = {s.id: candidate_dests(obs, s) for s in obs.free}
        m = gp.Model(env=self.env())
        y = {(s.id, w): m.addVar(vtype='B') for s in obs.free for w in cands[s.id]}
        for s in obs.free:
            m.addConstr(gp.quicksum(y[s.id, w] for w in cands[s.id]) == 1)
        moves_expr = gp.quicksum(y[s.id, w] for s in obs.free for w in cands[s.id] if w != s.loc)
        m.addConstr(moves_expr <= obs.fuel)
        obj = -gamma * moves_expr
        risk_terms = []
        self.options = {}
        for v in g.contested:
            arrive = {k: [s for s in obs.free if s.kind == k and v in cands[s.id]] for k in kinds}
            rng_k = [range(fixed[v][k], fixed[v][k] + len(arrive[k]) + 1) for k in kinds]
            opts = []
            for combo in ([(n,) for n in rng_k[0]] if len(kinds) == 1 else
                          [(a, b) for a in rng_k[0] for b in rng_k[1]]):
                for p in (('P', 'A') if sum(combo) > 0 else ('P',)):
                    own_cnt = dict(zip(kinds, combo))
                    phi, rho = node_eval(P, obs.design, ell, me, own_cnt, p, obs.opp_counts(v),
                                         obs.opp_posture(v), obs.sea_at(v))
                    opts.append((combo, p, VALUE[me][v] * lam * H * phi - Lam * rho, rho, m.addVar(vtype='B')))
            m.addConstr(gp.quicksum(o[4] for o in opts) == 1)
            for j, k in enumerate(kinds):
                m.addConstr(gp.quicksum(o[0][j] * o[4] for o in opts) ==
                            fixed[v][k] + gp.quicksum(y[s.id, v] for s in arrive[k]))
            obj += gp.quicksum(o[2] * o[4] for o in opts)
            risk_terms += [o[3] * o[4] for o in opts]
            self.options[v] = opts
        slack = m.addVar(lb=0.0)
        m.addConstr(gp.quicksum(risk_terms) <= eps + slack)
        m.setObjective(obj - 1000.0 * slack, gp.GRB.MAXIMIZE)
        m.optimize()
        moves = {}
        for s in obs.free:
            for w in cands[s.id]:
                if y[s.id, w].X > 0.5 and w != s.loc:
                    moves[s.id] = w
        post = {}
        for v, opts in self.options.items():
            for combo, p, _, _, var in opts:
                if var.X > 0.5 and sum(combo) > 0:
                    post[v] = p
        self.last_obj = m.ObjVal
        return moves, post


def eval_strength(P, design, ell, me, R_own, theta_own, post_me, opp_cnt, post_opp, sea='calm'):
    """node_eval with the own side given by its un-asserted strength R_own and navy share theta_own."""
    if sea == 'storm':
        return 0.0, 0.0
    R_opp, th_opp = raw_strength(P, opp_cnt, OPP[me], rough=(sea == 'rough'))
    a = P['alpha']
    S_me = R_own * (a if post_me == 'A' else 1.0)
    S_op = R_opp * (a if post_opp == 'A' else 1.0)
    if me == 'B':
        S_B, S_R, pB, pR, shares = S_me, S_op, post_me, post_opp, (theta_own, th_opp)
    else:
        S_B, S_R, pB, pR, shares = S_op, S_me, post_opp, post_me, (th_opp, theta_own)
    phi = (S_B - S_R) / (S_B + S_R + P['kappa'])
    h = hazard_rate(P, design, ell, S_B, S_R, pB, pR, shares)
    return SIGMA[me] * phi, 1.0 - math.exp(-h)


class MIPBRPolicy(MIPBREnumPolicy):
    """Workshop 2 best-response MIP (report section 3.8): the same decision problem as the
    Workshop 1 program, written with ship flows and strength levels so it scales to
    many ship types.

        max  sum_v sum_(n,c,p) a_v(n,c,p) b_{v,(n,c,p)} - gamma sum_{g, w != u(g)} f_{g,w} - 1000 xi
        s.t. sum_w f_{g,w} = |g|                               (groups g of interchangeable free ships)
             sum_{g, w != u(g)} f_{g,w} <= F_i - forced moves   (movement budget)
             sum_(n,c,p) b_{v,(n,c,p)} = 1
             sum_(n,c,p) n b_{v,(n,c,p)} = sum_{navy k} u_k (xbar_{k,v} + sum_{g of type k} f_{g,v})
             sum_(n,c,p) c b_{v,(n,c,p)} = sum_{coast guard k} u_k (xbar_{k,v} + sum_{g of type k} f_{g,v})
             sum_v sum_(n,c,p) rho_v(n,c,p) b_{v,(n,c,p)} <= eps_i (1 - ell/L) + xi
             f integer, b binary

    u_k = w_k / STRENGTH_UNIT (integer).  n and c are the navy and coast guard strength levels at v,
    so own strength is R_v = STRENGTH_UNIT (n + c) and the navy share n / (n + c): the option values
    a_v and rho_v are exact.  In the code the options over n are piecewise-linear functions with a
    breakpoint at every level (exact, since n is always a whole number of units), one for each
    coast guard level c and posture p, chosen by the binary y_{v,c,p}.
    """
    name = 'mip_br'

    def act(self, obs):
        import gurobipy as gp
        g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
        lam, H, Lam, gamma = P['lam'], horizon_factor(P), P['Lambda'], P['gamma']
        eps = risk_budget(P['eps'][me], ell, P)
        fixed = {v: defaultdict(int) for v in g.nodes}
        for s in obs.ships:
            if s.id in obs.forced:
                fixed[obs.forced[s.id]][s.kind] += 1
        groups = defaultdict(list)
        for s in obs.free:
            groups[(s.kind, s.loc, tuple(candidate_dests(obs, s)))].append(s)
        m = gp.Model(env=self.env())
        f = {}
        for key, members in groups.items():
            k, u, cands = key
            for w in cands:
                f[key, w] = m.addVar(vtype='I', lb=0, ub=len(members))
            m.addConstr(gp.quicksum(f[key, w] for w in cands) == len(members))
        moves_expr = gp.quicksum(var for (key, w), var in f.items() if w != key[1])
        m.addConstr(moves_expr <= obs.fuel)
        obj = -gamma * moves_expr
        risk_terms = []
        self.options, self.nl = {}, {}
        for v in g.contested:
            sea = obs.sea_at(v)
            unit = {k: int(round(weight(P, k, sea == 'rough') / STRENGTH_UNIT)) for k in KINDS[me]}
            arr = [(key, unit[key[0]]) for key in groups if v in key[2]]
            opp_cnt, opp_post = obs.opp_counts(v), obs.opp_posture(v)

            def option(n, c, p):
                th = n / (n + c) if n + c > 0 else 1.0
                phi, rho = eval_strength(P, obs.design, ell, me, (n + c) * STRENGTH_UNIT, th, p, opp_cnt, opp_post, sea)
                return VALUE[me][v] * lam * H * phi - Lam * rho, rho

            # navy and coast guard levels: fixed arrivals plus flows of free groups
            # and the levels that can actually occur there (breakpoints are needed only at those)
            lev, top, reach = {}, {}, {}
            for cl in ('navy', 'cg'):
                base = sum(unit[k] * n for k, n in fixed[v].items() if CLASS_K[k] == cl)
                terms = [(key, u_k) for key, u_k in arr if CLASS_K[key[0]] == cl]
                lev[cl] = base + gp.quicksum(u_k * f[key, v] for key, u_k in terms)
                top[cl] = base + sum(u_k * len(groups[key]) for key, u_k in terms)
                levels = {base}
                for key, u_k in terms:
                    levels = {x + j * u_k for x in levels for j in range(len(groups[key]) + 1)}
                reach[cl] = sorted(levels)

            if top['navy'] + top['cg'] == 0:
                obj += option(0, 0, 'P')[0]
                continue
            y, lvl = {}, {}

            def add_option(key, levels, val):
                # value and risk as piecewise-linear functions of the level, with a breakpoint at every
                # level that can occur; when the option is off its level is 0, so the value at 0 is
                # taken back out
                x_max = levels[-1]
                y[key] = m.addVar(vtype='B')
                lvl[key] = m.addVar(lb=0, ub=x_max)
                m.addConstr(lvl[key] <= x_max * y[key])
                xs = sorted(set(levels) | {0})
                vals = [val(x) for x in xs]
                if len(xs) == 1:                     # level fixed at 0 (Gurobi needs two breakpoints)
                    xs, vals = [0, 1], vals * 2
                av, rv = m.addVar(lb=-gp.GRB.INFINITY), m.addVar(lb=-gp.GRB.INFINITY)
                m.addGenConstrPWL(lvl[key], av, xs, [a for a, _ in vals])
                m.addGenConstrPWL(lvl[key], rv, xs, [r for _, r in vals])
                risk_terms.append(rv - vals[0][1] * (1 - y[key]))
                return av - vals[0][0] * (1 - y[key])

            # patrol: only the total level matters (the navy share enters only the own assert hazard)
            total = sorted({a + b for a in reach['navy'] for b in reach['cg']})
            obj += add_option(('P', None), total, lambda x: option(x, 0, 'P'))
            # assert: one option per coast guard level c, over the navy level
            for c in reach['cg']:
                obj += add_option(('A', c), reach['navy'], lambda x, c=c: option(x, c, 'A'))
            cg_patrol = m.addVar(lb=0, ub=top['cg'])
            m.addConstr(cg_patrol <= top['cg'] * y['P', None])
            m.addConstr(gp.quicksum(y.values()) == 1)
            m.addConstr(gp.quicksum(c * y['A', c] for c in reach['cg']) + cg_patrol == lev['cg'])
            m.addConstr(lvl['P', None] + gp.quicksum(lvl['A', c] + c * y['A', c] for c in reach['cg'])
                        == lev['navy'] + lev['cg'])
            self.options[v], self.nl[v] = y, lvl
        slack = m.addVar(lb=0.0)
        m.addConstr(gp.quicksum(risk_terms) <= eps + slack)
        m.setObjective(obj - 1000.0 * slack, gp.GRB.MAXIMIZE)
        m.optimize()
        moves = {}
        for key, members in groups.items():
            k, u, cands = key
            todo = [(w, int(round(f[key, w].X))) for w in cands if w != u]
            # ships with the most endurance take the moves (all members may legally take any of them)
            pool = sorted(members, key=lambda s: -s.d)
            for w, n in todo:
                for _ in range(n):
                    moves[pool.pop(0).id] = w
        post, nl_of = {}, self.nl
        for v, y in self.options.items():
            for (p, c), var in y.items():
                if var.X > 0.5 and (c or 0) + nl_of[v][p, c].X > 0.5:
                    post[v] = p
        self.last_obj = m.ObjVal
        self.last_slack = slack.X
        return moves, post


# ============================================================================
# 7.  TEMPLATE GAME (strategic form)
# ============================================================================

SPLITS = [(.6, .2, .2), (.2, .6, .2), (.2, .2, .6), (.4, .4, .2), (.4, .2, .4), (.2, .4, .4), (.34, .33, .33)]
# 14 templates per player: force split across (N, C, S) x posture {P, A}
TEMPLATES = [(split, post) for split in SPLITS for post in ('P', 'A')]
TEMPLATE_LABELS = [f"N{int(s[0]*100):02d}C{int(s[1]*100):02d}S{int(s[2]*100):02d}-{p}" for s, p in TEMPLATES]
DEPLOYABLE_FRAC = 2 / 3   # Workshop 2: two thirds of each fleet out of maintenance (Workshop 1: 0.7)


class MetaGame:
    """Template game Gamma = <{B,R}, (S_B, S_R), (u_B, u_R)> with |S_i| = 14.

    M_i[a_B][a_R] is player i's steady-state payoff when Blue plays template
    a_B and Red template a_R: deployable ships (70% of each fleet; Red uses
    PLAN and CCG proportionally) are split across regions by the template's
    fractions and evenly over the nodes of a region (fractional hulls allowed);
    phi_v is the steady-state share, and the payoff is
        sum_v V_v^i sigma_i phi_v - Lambda * sum_v p_v   (incident probabilities at ell = 1, calm seas).
    The game is general-sum (V^B != V^R, and the incident penalty hits both).
    CB is the control-only part (zero-sum when Red receives -CB).

    Solution methods:
      best_responses / pure_nash  -- s* is a pure NE iff s*_i in BR_i(s*_-i) for both players
      iesds                       -- iterated elimination of strictly dominated (pure) strategies
      maximin_lp(A)               -- max z s.t. z <= sum_a sigma(a) A[a][b] for all b (the maximin LP);
                                     for the zero-sum part this gives the value and an equilibrium,
                                     for a general-sum payoff matrix it gives the security strategy
      ce_lp                       -- correlated equilibrium maximizing total expected payoff
    """

    def __init__(self, P=None):
        self.P = dict(PARAMS)
        if P:
            self.P.update(P)
        self.n = len(TEMPLATES)
        self.MB = [[0.0] * self.n for _ in range(self.n)]     # Blue payoff (control - Lambda * incidents)
        self.MR = [[0.0] * self.n for _ in range(self.n)]     # Red payoff
        self.CB = [[0.0] * self.n for _ in range(self.n)]     # Blue control payoff only (zero-sum part)
        for a in range(self.n):
            for b in range(self.n):
                self.MB[a][b], self.MR[a][b], self.CB[a][b] = self._payoff(TEMPLATES[a], TEMPLATES[b])

    def _payoff(self, tB, tR):
        P = self.P
        alloc = {k: self._spread(DEPLOYABLE_FRAC * sum(FLEET[k].values()), tB[0] if SHIP_TYPES[k][0] == 'B' else tR[0])
                 for k in SHIP_TYPES}
        ctrlB = ctrlR = inc = 0.0
        for ri, (r, nodes) in enumerate(REGIONS.items()):
            for v in nodes:
                cnt = {k: alloc[k][v] for k in alloc}
                S_B, S_R, ps = strength_parts(P, cnt, tB[1], tR[1])
                phi = (S_B - S_R) / (S_B + S_R + P['kappa'])
                ctrlB += VALUE['B'][v] * phi
                ctrlR -= VALUE['R'][v] * phi
                inc += 1.0 - math.exp(-hazard_rate(P, 'D0', P['ell0'], S_B, S_R, tB[1], tR[1], ps))
        return ctrlB - P['Lambda'] * inc, ctrlR - P['Lambda'] * inc, ctrlB

    def _spread(self, n, split):
        """Ships of one kind per node: n split over regions by the template's fractions,
        then evenly over each region's nodes.  With whole_hulls, n is rounded to whole
        ships and each split uses largest-remainder rounding (ties go to the earlier
        region or node in list order)."""
        def lr_round(total, shares):
            raw = [total * f for f in shares]
            out = [math.floor(x) for x in raw]
            order = sorted(range(len(raw)), key=lambda i: -(raw[i] - out[i]))
            for i in order[:total - sum(out)]:
                out[i] += 1
            return out
        nodes_by_region = list(REGIONS.values())
        if not self.P.get('whole_hulls'):
            return {v: n * split[ri] / len(nodes) for ri, nodes in enumerate(nodes_by_region) for v in nodes}
        per_region = lr_round(int(round(n)), split)
        out = {}
        for ri, nodes in enumerate(nodes_by_region):
            for v, c in zip(nodes, lr_round(per_region[ri], [1.0 / len(nodes)] * len(nodes))):
                out[v] = float(c)
        return out

    # ---------------------------------------------------------- pure analysis
    def best_responses(self, MB=None, MR=None):
        """BR_B(b) for every Red template b and BR_R(a) for every Blue template a."""
        MB, MR, n = MB or self.MB, MR or self.MR, self.n
        brB = {b: [a for a in range(n) if MB[a][b] >= max(MB[k][b] for k in range(n)) - 1e-9] for b in range(n)}
        brR = {a: [b for b in range(n) if MR[a][b] >= max(MR[a][k] for k in range(n)) - 1e-9] for a in range(n)}
        return brB, brR

    def pure_nash(self, MB=None, MR=None):
        """All pure Nash equilibria (a, b): mutual best responses."""
        brB, brR = self.best_responses(MB, MR)
        return [(a, b) for a in range(self.n) for b in range(self.n) if a in brB[b] and b in brR[a]]

    def iesds(self):
        """Iterated elimination of strictly dominated pure strategies.
        Returns the surviving template indices (S_B', S_R')."""
        SB, SR = list(range(self.n)), list(range(self.n))
        changed = True
        while changed:
            changed = False
            for a in list(SB):
                if any(all(self.MB[a2][b] > self.MB[a][b] for b in SR) for a2 in SB if a2 != a):
                    SB.remove(a)
                    changed = True
            for b in list(SR):
                if any(all(self.MR[a][b2] > self.MR[a][b] for a in SB) for b2 in SR if b2 != b):
                    SR.remove(b)
                    changed = True
        return SB, SR

    # ------------------------------------------------------------------- LPs
    @staticmethod
    def maximin_lp(A):
        """Maximin LP for the row player of payoff matrix A:
            max z  s.t.  z <= sum_a sigma(a) A[a][b]  for all columns b,  sigma in the simplex.
        Returns (sigma, z)."""
        import gurobipy as gp
        n, mcols = len(A), len(A[0])
        m = gp.Model(env=MIPBRPolicy.env())
        sig = [m.addVar(lb=0.0) for _ in range(n)]
        z = m.addVar(lb=-gp.GRB.INFINITY)
        m.addConstr(gp.quicksum(sig) == 1)
        for b in range(mcols):
            m.addConstr(z <= gp.quicksum(sig[a] * A[a][b] for a in range(n)))
        m.setObjective(z, gp.GRB.MAXIMIZE)
        m.optimize()
        return [v.X for v in sig], z.X

    def ce_lp(self):
        """Correlated equilibrium maximizing total expected payoff (an LP):
            max sum_s pi(s) (u_B(s) + u_R(s))
            s.t. sum_b pi(a,b) [u_B(a,b) - u_B(a',b)] >= 0   for all a, a'
                 sum_a pi(a,b) [u_R(a,b) - u_R(a,b')] >= 0   for all b, b'
                 pi a probability distribution.
        Returns the joint distribution pi[a][b]."""
        import gurobipy as gp
        n = self.n
        m = gp.Model(env=MIPBRPolicy.env())
        pi = [[m.addVar(lb=0.0) for _ in range(n)] for _ in range(n)]
        m.addConstr(gp.quicksum(pi[a][b] for a in range(n) for b in range(n)) == 1)
        for a in range(n):
            for a2 in range(n):
                if a2 != a:
                    m.addConstr(gp.quicksum(pi[a][b] * (self.MB[a][b] - self.MB[a2][b]) for b in range(n)) >= 0)
        for b in range(n):
            for b2 in range(n):
                if b2 != b:
                    m.addConstr(gp.quicksum(pi[a][b] * (self.MR[a][b] - self.MR[a][b2]) for a in range(n)) >= 0)
        m.setObjective(gp.quicksum(pi[a][b] * (self.MB[a][b] + self.MR[a][b]) for a in range(n) for b in range(n)),
                       gp.GRB.MAXIMIZE)
        m.optimize()
        return [[pi[a][b].X for b in range(n)] for a in range(n)]

    def selected_nash(self):
        """Pure NE used by the 'equilibrium' policy: the one with the highest total payoff
        (Nash equilibrium alone does not say which equilibrium is played; we state the
        selection rule as an assumption).  None if no pure NE exists."""
        ne = self.pure_nash()
        if not ne:
            return None
        return max(ne, key=lambda ab: self.MB[ab[0]][ab[1]] + self.MR[ab[0]][ab[1]])


_META_CACHE = {}


def get_meta_game():
    """Cached template game."""
    if 'meta' not in _META_CACHE:
        _META_CACHE['meta'] = MetaGame()
    return _META_CACHE['meta']


class TemplatePolicy(Policy):
    """Base for policies that play a template (region split + posture) and move
    ships toward the template's target allocation.  Subclasses implement
    choose_template(); a template is re-drawn every `resample` periods."""
    resample = 3

    def __init__(self, player, rng):
        super().__init__(player, rng)
        self.meta = get_meta_game()
        self.cur = None

    def choose_template(self, obs):
        raise NotImplementedError

    def act(self, obs):
        g, me, P, ell = obs.graph, obs.player, obs.P, obs.ell
        if self.cur is None or (obs.t - 1) % self.resample == 0:
            self.cur = self.choose_template(obs)
        split, posture = TEMPLATES[self.cur]
        # ---- target allocation: region quotas -> node slots (weighted by node value)
        free = [s for s in obs.free]
        n_dep = len(free)
        slots = []
        for ri, (r, nodes) in enumerate(REGIONS.items()):
            n_r = int(round(split[ri] * n_dep))
            wts = [VALUE[me][v] for v in nodes]
            tot = sum(wts)
            alloc = {v: int(n_r * VALUE[me][v] / tot) for v in nodes}
            rem = n_r - sum(alloc.values())
            for v in sorted(nodes, key=lambda v: -(n_r * VALUE[me][v] / tot - alloc[v]))[:rem]:
                alloc[v] += 1
            for v, k in alloc.items():
                slots += [v] * k
        # ---- greedy nearest ship <-> slot matching
        pos = {s.id: s.loc for s in free}
        assign = {}
        pairs = sorted(((g.dist[me][s.loc][v], self.rng.random(), s.id, v) for s in free for v in slots
                        if obs.reach_ok(s, v)), key=lambda x: (x[0], x[1]))
        open_slots = defaultdict(int)
        for v in slots:
            open_slots[v] += 1
        for d, _, sid, v in pairs:
            if sid in assign or open_slots[v] == 0:
                continue
            open_slots[v] -= 1
            assign[sid] = v
        moves = {}
        order = sorted(assign.items(), key=lambda kv: g.dist[me][obs.game.ship_by_id[kv[0]].loc][kv[1]])
        for sid, v in order:
            s = obs.game.ship_by_id[sid]
            if v == s.loc or len(moves) >= obs.fuel:
                continue
            hop = self.next_hop(obs, s, v)
            if hop:
                moves[sid] = hop
                pos[sid] = hop
        # ---- postures: the template's posture, guarded against imminent war and by a risk budget
        cnt = self.planned_counts(obs, pos)
        post = {}
        for v in g.contested:
            if sum(cnt[v].values()) > 0:
                post[v] = posture if ell <= 3 else 'P'
        for _ in range(10):
            risks = {v: node_eval(P, obs.design, ell, me, cnt[v], post[v], obs.opp_counts(v), obs.opp_posture(v),
                                  obs.sea_at(v))[1] for v in post}
            asserting = [v for v in post if post[v] == 'A']
            if sum(risks.values()) <= risk_budget(P['eps'][me], ell, P) or not asserting:
                break
            post[max(asserting, key=risks.get)] = 'P'
        return moves, post


class EquilibriumPolicy(TemplatePolicy):
    """Plays its part of the selected pure Nash equilibrium of the template game."""
    name = 'equilibrium'

    def choose_template(self, obs):
        ne = self.meta.selected_nash()
        if ne is None:
            raise SystemExit("template game has no pure Nash equilibrium; use 'maximin'")
        return ne[0] if self.player == 'B' else ne[1]


class MaximinPolicy(TemplatePolicy):
    """Samples a template from the player's maximin (security) mixed strategy,
    computed with the maximin LP on its own payoff matrix: the best payoff it
    can guarantee whatever template the opponent plays."""
    name = 'maximin'

    def choose_template(self, obs):
        if not hasattr(self.meta, 'sec'):
            n = self.meta.n
            AR = [[self.meta.MR[a][b] for a in range(n)] for b in range(n)]     # Red as row player
            self.meta.sec = {'B': self.meta.maximin_lp(self.meta.MB)[0], 'R': self.meta.maximin_lp(AR)[0]}
        probs = self.meta.sec[self.player]
        u = self.rng.random()
        for k, p in enumerate(probs):
            u -= p
            if u <= 0:
                return k
        return len(probs) - 1


def make_policy(name, player, game):
    """Policy factory (each Game gets fresh policy instances)."""
    rng = game.rng
    if name == 'random':
        return RandomPolicy(player, rng)
    if name == 'conservative':
        return HeuristicPolicy(player, rng, 0.2, name)
    if name == 'moderate':
        return HeuristicPolicy(player, rng, 0.5, name)
    if name == 'aggressive':
        return HeuristicPolicy(player, rng, 0.8, name)
    if name == 'greedy_br':
        return GreedyBRPolicy(player, rng)
    if name == 'mip_br':
        return MIPBRPolicy(player, rng)
    if name == 'mip_br_enum':
        return MIPBREnumPolicy(player, rng)
    if name == 'equilibrium':
        return EquilibriumPolicy(player, rng)
    if name == 'maximin':
        return MaximinPolicy(player, rng)
    raise ValueError(f"unknown policy {name!r}; choose from {POLICY_NAMES}")


# ============================================================================
# 10.  GUI (tkinter; imported lazily so headless modes never need it)
# ============================================================================

REGION_NAMES = {'N': 'North', 'C': 'Center', 'S': 'South'}


def plain_events(texts):
    """Rewrite one turn's engine events in plain words for the GUI log.

    Forced returns are grouped into one line per side; other events are
    shortened (e.g. 'ell' becomes 'escalation level').
    """
    out, home = [], {'B': 0, 'R': 0}
    side = {'B': 'Blue', 'R': 'Red'}
    for x in texts:
        if ' forced return ' in x:
            home[x[0]] += 1
        elif x.startswith('Storm closes region'):
            r = x.split()[3]
            out.append(x.replace(f'region {r}', f"the {REGION_NAMES.get(r, r)}").replace(' periods', ' turns'))
        elif x.startswith('INCIDENT'):
            out.append(x.replace('INCIDENT at', 'Incident at').replace('ell ->', 'escalation rises to'))
        else:
            out.append(x.replace('Tensions ease: ell ->', 'Tensions ease: escalation falls to').replace(' periods', ' turns')
                        .replace('(ell = L)', '').replace('-W', 'the war penalty'))
    for i in 'BR':
        if home[i]:
            out.insert(0, f"{home[i]} {side[i]} ship(s) low on endurance, heading home")
    return out


def launch_gui():
    """Build and run the tkinter front end."""
    import tkinter as tk
    from tkinter import ttk

    MAP_W, MAP_H = 710, 520
    # per-node placement of the name label and the ship-count row:
    # (label anchor, dx, dy, ships anchor, dx, dy) relative to the node center
    LAYOUT = {
        'YOK': ('n', 0, 18, 'n', 0, 31), 'GUA': ('e', -18, -8, 'e', -18, 8),
        'NBO': ('s', 0, -22, 'n', 0, 18), 'SAN': ('s', 0, -16, 'e', -16, 0),
        'PHL': ('w', 18, 10, 'w', 18, 22), 'SAS': ('w', 18, -6, 'w', 18, 8),
        'ISG': ('n', 0, 18, 'n', 0, 31), 'QDO': ('e', -18, -6, 'e', -18, 8), 'NAM': ('w', 18, -6, 'w', 18, 8),
        'SEN': ('s', 0, -20, 'e', -18, 2), 'MIY': ('w', 18, -8, 'w', 18, 7),
        'TWN': ('e', -18, -6, 'e', -18, 8), 'EOT': ('w', 18, 4, 'w', 18, 18),
        'LUZ': ('e', -18, 4, 'n', 0, 18), 'SCB': ('w', 18, -6, 'e', -18, 8),
        'PAR': ('n', 0, 18, 'w', 18, 6), 'STS': ('s', 0, -20, 'w', 18, 4),
    }
    LON0, LON1, LAT0, LAT1 = 108.0, 146.0, 8.0, 40.0
    BLUE, RED, CCG_COL = '#1f4e9c', '#b22222', '#d2691e'
    # plain-language names shown in the dropdowns -> internal names used by the model
    POLICY_LABELS = {
        'random': 'Random moves (benchmark)',
        'conservative': 'Rule of thumb: cautious',
        'moderate': 'Rule of thumb: balanced',
        'aggressive': 'Rule of thumb: bold',
        'greedy_br': 'Quick best response (greedy)',
        'mip_br': 'Best response (optimization/MIP)',
        'equilibrium': 'Nash equilibrium plan',
        'maximin': 'Safety-first plan (maximin)',
    }
    DESIGN_LABELS = {
        'D0': 'D0 Baseline',
        'D1': 'D1 Extra port in Philippines (dispersed basing)',
        'D2': 'D2 Extra surveillance (redundant sensing)',
        'D3': 'D3 De-escalation measures',
    }
    WEATHER_LABELS = {
        'calm': 'Calm seas',
        'nominal': 'Nominal weather',
        'typhoon': 'Typhoon weather',
        'extreme': 'Extreme weather',
    }
    LEVEL_NAMES = ['peace', 'tension', 'friction', 'crisis', 'brink', 'WAR']
    HELP_TEXT = (
        "WHAT IS THIS?\n"
        "Blue (US Navy destroyers) and Red (Chinese Navy plus coast guard) move ships between "
        "8 contested waters (circles) and their home ports (squares). Each turn is 2 days.\n\n"
        "GOAL: hold more of the contested waters than the other side without starting a war. "
        "Ships that 'assert' (thick outline) push control harder but make incidents more likely. "
        "Each incident raises the escalation level (bottom left); reaching level 5 means war "
        "and a large loss for both sides.\n\n"
        "HOW TO USE: pick a plan for each side, the design and the weather, press New game, then "
        "Step (one turn) or Play. 'Run many games' plays the same setup with different random "
        "draws and reports averages.\n\n"
        "READING THE MAP: circle color and number = who controls that water, from -1 (fully Red) "
        "to +1 (fully Blue). B = Blue destroyers, P = Red navy ships, C = Red coast guard. "
        "Orange ring = incident this turn. Shaded box = rough sea or storm (no one operates in a "
        "storm). 'Blue view' / 'Red view' show what each side believes; ~n[a] means n ships "
        "last seen a turns ago.\n\n"
        "SCORE: each side earns points every turn for the waters it controls, minus movement cost "
        "and minus the escalation level. Higher is better.")

    def project(lon, lat):
        """Equirectangular projection of (lon, lat) onto the map canvas."""
        x = 36 + (lon - LON0) / (LON1 - LON0) * (MAP_W - 72)
        y = (MAP_H - 30) - (lat - LAT0) / (LAT1 - LAT0) * (MAP_H - 60)
        return x, y

    def control_color(c):
        """Interpolate red (c=-1) -> white (0) -> blue (+1)."""
        c = max(-1.0, min(1.0, c))
        if c >= 0:
            r, g, b = int(255 - c * (255 - 0x3b)), int(255 - c * (255 - 0x6f)), int(255 - c * (255 - 0xd6))
        else:
            k = -c
            r, g, b = int(255 - k * (255 - 0xd9)), int(255 - k * (255 - 0x53)), int(255 - k * (255 - 0x4f))
        return f"#{r:02x}{g:02x}{b:02x}"

    class App:
        def __init__(self, root):
            self.root = root
            root.title("Maritime Gray-Zone Wargame (6.S974)")
            root.geometry("1260x800")
            root.minsize(1240, 760)
            self.game = None
            self.running = False
            self.n_events_shown = 0
            self.batch_job = None
            self._build()
            self.reset()

        # ------------------------------------------------------------ layout
        def _build(self):
            root = self.root
            root.columnconfigure(0, weight=1)
            root.rowconfigure(0, weight=1)
            left = tk.Frame(root)
            left.grid(row=0, column=0, sticky='nsew', padx=(6, 3), pady=6)
            right = tk.Frame(root, width=400)
            right.grid(row=0, column=1, sticky='ns', padx=(3, 6), pady=6)
            # --- map
            self.map = tk.Canvas(left, width=MAP_W, height=MAP_H, bg='#e8f1f8', highlightthickness=1,
                                 highlightbackground='#99a')
            self.map.pack(fill='both', expand=False)
            # --- ladder + time series
            bottom = tk.Frame(left)
            bottom.pack(fill='x', pady=(6, 0))
            self.ladder = tk.Canvas(bottom, width=110, height=170, bg='white', highlightthickness=1, highlightbackground='#99a')
            self.ladder.pack(side='left')
            self.ts = tk.Canvas(bottom, width=MAP_W - 116, height=170, bg='white', highlightthickness=1, highlightbackground='#99a')
            self.ts.pack(side='left', padx=(6, 0))
            # --- status line
            self.status = tk.Label(left, text='', anchor='w', font=('TkDefaultFont', 10, 'bold'))
            self.status.pack(fill='x', pady=(6, 0))

            # --- scenario controls
            sc = ttk.LabelFrame(right, text='Scenario')
            sc.pack(fill='x')
            self.v_blue = tk.StringVar(value=POLICY_LABELS['moderate'])
            self.v_red = tk.StringVar(value=POLICY_LABELS['greedy_br'])
            self.v_design = tk.StringVar(value=DESIGN_LABELS['D0'])
            self.v_weather = tk.StringVar(value=WEATHER_LABELS['nominal'])
            self.v_seed = tk.StringVar(value='0')
            self.v_T = tk.StringVar(value=str(PARAMS['T']))
            self.v_view = tk.StringVar(value='truth')
            self.v_attacks = {a: tk.BooleanVar(value=False) for a in ATTACKS}
            row = 0
            for label, var, vals in (('Blue plan', self.v_blue, list(POLICY_LABELS.values())),
                                     ('Red plan', self.v_red, list(POLICY_LABELS.values())),
                                     ('Blue design', self.v_design, list(DESIGN_LABELS.values())),
                                     ('Weather', self.v_weather, list(WEATHER_LABELS.values()))):
                ttk.Label(sc, text=label).grid(row=row, column=0, sticky='w', padx=4, pady=2)
                ttk.Combobox(sc, textvariable=var, values=vals, state='readonly', width=27).grid(row=row, column=1, columnspan=3, sticky='w', pady=2)
                row += 1
            ttk.Label(sc, text='Red attacks\n(Workshop 2)').grid(row=row, column=0, sticky='nw', padx=4, pady=2)
            af = tk.Frame(sc)
            af.grid(row=row, column=1, columnspan=3, sticky='w')
            for k, a in enumerate(ATTACKS):
                ttk.Checkbutton(af, text=a.capitalize(), variable=self.v_attacks[a]).grid(row=k // 2, column=k % 2, sticky='w', padx=2)
            row += 1
            ttk.Label(sc, text='Random seed').grid(row=row, column=0, sticky='w', padx=4, pady=2)
            ttk.Entry(sc, textvariable=self.v_seed, width=7).grid(row=row, column=1, sticky='w')
            ttk.Label(sc, text='Turns').grid(row=row, column=2, sticky='e', padx=4)
            ttk.Entry(sc, textvariable=self.v_T, width=6).grid(row=row, column=3, sticky='w')
            row += 1
            ttk.Label(sc, text='Show').grid(row=row, column=0, sticky='w', padx=4, pady=2)
            vf = tk.Frame(sc)
            vf.grid(row=row, column=1, columnspan=3, sticky='w')
            for text, val in (('Everything', 'truth'), ('Blue view', 'B'), ('Red view', 'R')):
                ttk.Radiobutton(vf, text=text, value=val, variable=self.v_view, command=self.redraw).pack(side='left')
            # --- run controls
            rc = ttk.LabelFrame(right, text='Run')
            rc.pack(fill='x', pady=(6, 0))
            bf = tk.Frame(rc)
            bf.pack(fill='x', padx=4, pady=2)
            ttk.Button(bf, text='New game', command=self.reset).pack(side='left', padx=2)
            ttk.Button(bf, text='Step', command=self.step_once).pack(side='left', padx=2)
            self.run_btn = ttk.Button(bf, text='Play', command=self.toggle_run)
            self.run_btn.pack(side='left', padx=2)
            ttk.Label(bf, text='Speed').pack(side='left', padx=(10, 2))
            # slider runs slow -> fast; the delay between turns is 1550 - value (ms)
            self.speed = tk.Scale(bf, from_=50, to=1500, orient='horizontal', showvalue=False, length=90)
            self.speed.set(1150)
            self.speed.pack(side='left')
            ttk.Button(bf, text='Help', command=self.show_help).pack(side='left', padx=(8, 2))
            ttk.Label(rc, text="Pick plans and settings above, press New game, then Step or Play.",
                      foreground='#445').pack(fill='x', padx=6, pady=(0, 3))
            # --- event log
            lf = ttk.LabelFrame(right, text='What happened')
            lf.pack(fill='both', expand=True, pady=(6, 0))
            self.log = tk.Text(lf, height=11, width=46, font=('TkFixedFont', 9), state='disabled', wrap='word')
            sb = ttk.Scrollbar(lf, command=self.log.yview)
            self.log.configure(yscrollcommand=sb.set)
            self.log.pack(side='left', fill='both', expand=True)
            sb.pack(side='right', fill='y')
            # --- batch
            bt = ttk.LabelFrame(right, text='Run many games (same settings, different random draws)')
            bt.pack(fill='both', expand=True, pady=(6, 0))
            hf = tk.Frame(bt)
            hf.pack(fill='x', padx=4, pady=2)
            ttk.Label(hf, text='Games').pack(side='left')
            self.v_nseeds = tk.StringVar(value='50')
            ttk.Entry(hf, textvariable=self.v_nseeds, width=6).pack(side='left', padx=4)
            self.batch_btn = ttk.Button(hf, text='Run many games', command=self.run_batch_gui)
            self.batch_btn.pack(side='left', padx=4)
            self.batch_out = tk.Text(bt, height=8, width=46, font=('TkFixedFont', 9), state='disabled', wrap='none')
            self.batch_out.pack(fill='both', expand=True)
            self._set_batch_text("Plays the current settings many times with different random seeds\nand reports average scores and how often war breaks out.")

        # ------------------------------------------------------------ control
        def _settings(self):
            try:
                seed = int(self.v_seed.get())
            except ValueError:
                seed = 0
            try:
                T = max(1, int(self.v_T.get()))
            except ValueError:
                T = PARAMS['T']
            attacks = tuple(a for a, var in self.v_attacks.items() if var.get())

            def key(labels, var):
                return next(k for k, v in labels.items() if v == var.get())
            return dict(blue=key(POLICY_LABELS, self.v_blue), red=key(POLICY_LABELS, self.v_red),
                        design=key(DESIGN_LABELS, self.v_design), attacks=attacks, seed=seed, T=T,
                        weather=key(WEATHER_LABELS, self.v_weather))

        def reset(self):
            self.running = False
            self.run_btn.configure(text='Play')
            s = self._settings()
            self.game = Game(s['blue'], s['red'], s['design'], s['attacks'], seed=s['seed'], T=s['T'],
                             weather=s['weather'])
            self.n_events_shown = 0
            self.log.configure(state='normal')
            self.log.delete('1.0', 'end')
            self.log.configure(state='disabled')
            self.append_log(f"New game: Blue plays '{POLICY_LABELS[s['blue']]}', Red plays '{POLICY_LABELS[s['red']]}', "
                            f"{DESIGN_LABELS[s['design']]}, {WEATHER_LABELS[s['weather']]}, "
                            f"Red attacks: {', '.join(s['attacks']) or 'none'}, seed {s['seed']}, {s['T']} turns")
            self.redraw()

        def step_once(self):
            if self.game.done:
                return
            self.game.step()
            self.redraw()

        def toggle_run(self):
            if self.game.done:
                return
            self.running = not self.running
            self.run_btn.configure(text='Pause' if self.running else 'Play')
            if self.running:
                self.tick()

        def tick(self):
            if not self.running:
                return
            self.step_once()
            if self.game.done:
                self.running = False
                self.run_btn.configure(text='Play')
                return
            self.root.after(1550 - int(self.speed.get()), self.tick)

        def show_help(self):
            from tkinter import messagebox
            messagebox.showinfo('How the wargame works', HELP_TEXT)

        def append_log(self, text):
            self.log.configure(state='normal')
            self.log.insert('end', text + '\n')
            self.log.see('end')
            self.log.configure(state='disabled')

        def run_batch_gui(self):
            """Run N seeds of the current scenario in chunks so the window stays responsive."""
            if self.batch_job:
                return
            s = self._settings()
            try:
                n = max(1, int(self.v_nseeds.get()))
            except ValueError:
                n = 50
            rows = []
            self.batch_btn.configure(state='disabled')

            def chunk(k=0):
                for j in range(k, min(n, k + 5)):
                    rows.append(Game(s['blue'], s['red'], s['design'], s['attacks'], seed=s['seed'] + j, T=s['T'],
                                     weather=s['weather']).run().metrics())
                k = min(n, k + 5)
                self._set_batch_text(f"running... {k}/{n}")
                if k < n:
                    self.batch_job = self.root.after(1, chunk, k)
                else:
                    self.batch_job = None
                    self.batch_btn.configure(state='normal')
                    sm = summarize(rows, s['blue'], s['red'], s['design'], s['attacks'])
                    self._set_batch_text(
                        f"{n} games: Blue '{POLICY_LABELS[s['blue']]}' vs Red '{POLICY_LABELS[s['red']]}'\n"
                        f"{DESIGN_LABELS[s['design']]}, {WEATHER_LABELS[s['weather']]}\n\n"
                        f"Average Blue score  {sm['blue_mean']:8.1f}  (+/- {sm['blue_se']:.1f})\n"
                        f"Average Red score   {sm['red_mean']:8.1f}  (+/- {sm['red_se']:.1f})\n"
                        f"Blue control share  {sm['control_share']:+.2f}  (-1 all Red, +1 all Blue)\n"
                        f"Games ending in war {100 * sm['war_rate']:.0f}%\n"
                        f"Incidents per game  {sm['incidents']:.1f}\n"
                        f"(+/- = standard error of the average)")
            chunk()

        def _set_batch_text(self, text):
            self.batch_out.configure(state='normal')
            self.batch_out.delete('1.0', 'end')
            self.batch_out.insert('end', text)
            self.batch_out.configure(state='disabled')

        # ------------------------------------------------------------ drawing
        def redraw(self):
            gm = self.game
            new = gm.events[self.n_events_shown:]
            for t in sorted({t for t, _ in new}):
                for text in plain_events([x for tt, x in new if tt == t]):
                    self.append_log(f"Turn {t:2d}: {text}")
            self.n_events_shown = len(gm.events)
            self.draw_map()
            self.draw_ladder()
            self.draw_timeseries()
            war = '  *** WAR ***' if gm.war else ('  (end)' if gm.done else '')
            self.status.configure(
                text=f"Turn {gm.t}/{gm.T}   Escalation {gm.ell} ({LEVEL_NAMES[gm.ell]})   "
                     f"Score: Blue {gm.u['B']:.0f}, Red {gm.u['R']:.0f}   "
                     f"Blue control {gm.control_share():+.2f}   Incidents {gm.n_incidents}{war}",
                fg='#b00' if gm.war else 'black')

        def draw_map(self):
            cv, gm, g = self.map, self.game, self.game.g
            cv.delete('all')
            view = self.v_view.get()
            pos = {v: project(NODES[v][1], NODES[v][2]) for v in g.nodes}
            # regions shaded by sea state (rough = light grey-blue, storm = grey)
            for r, nodes in REGIONS.items():
                st = gm.sea.get(r, 'calm')
                if st != 'calm':
                    xs = [pos[v][0] for v in nodes]
                    ys = [pos[v][1] for v in nodes]
                    cv.create_rectangle(min(xs) - 34, min(ys) - 34, max(xs) + 34, max(ys) + 34, outline='',
                                        fill='#d6e2ee' if st == 'rough' else '#b9b9b9')
                    cv.create_text(min(xs) - 30, max(ys) + 30, anchor='sw', text=st, font=('TkDefaultFont', 8, 'italic'),
                                   fill='#445')
            # edges (dashed when blockaded for Blue, grey when a storm closes an endpoint)
            for a, b in g.edges:
                (x1, y1), (x2, y2) = pos[a], pos[b]
                blocked = a in gm.blocked or b in gm.blocked
                closed = a in gm.closed or b in gm.closed
                cv.create_line(x1, y1, x2, y2, fill='#c33' if blocked else ('#bbb' if closed else '#7a8a99'),
                               width=2, dash=(5, 4) if (blocked or closed) else None)
            counts = gm.counts()
            for v in g.nodes:
                x, y = pos[v]
                name, kind, owner = NODES[v][0], NODES[v][3], NODES[v][4]
                la, ldx, ldy, sa, sdx, sdy = LAYOUT[v]
                if kind == 'home':
                    col = BLUE if owner == 'B' else RED
                    cv.create_rectangle(x - 12, y - 12, x + 12, y + 12, fill=col, outline='black', width=1)
                else:
                    pB, pR = gm.postures['B'].get(v, 'P') == 'A', gm.postures['R'].get(v, 'P') == 'A'
                    outline = '#6a1b9a' if (pB and pR) else (BLUE if pB else (RED if pR else 'black'))
                    width = 4 if (pB or pR) else 1
                    if v in gm.last_incidents:
                        cv.create_oval(x - 22, y - 22, x + 22, y + 22, outline='#ff8c00', width=4)
                    if v in gm.closed:
                        cv.create_oval(x - 20, y - 20, x + 20, y + 20, outline='#888', width=2, dash=(3, 3))
                    cv.create_oval(x - 15, y - 15, x + 15, y + 15, fill=control_color(gm.c[v]), outline=outline, width=width)
                    cv.create_text(x, y, text=f"{gm.c[v]:+.2f}", font=('TkDefaultFont', 8))
                cv.create_text(x + ldx, y + ldy, text=f"{v} {name}", anchor=la, font=('TkDefaultFont', 8, 'bold'))
                # ship markers: true own side(s); believed opponent counts (~n, age in brackets) in the side views
                segs = []

                def by_class(cnt, i):
                    navy = sum(cnt.get(k, 0) for k in KINDS[i] if CLASS_K[k] == 'navy')
                    cg = sum(cnt.get(k, 0) for k in KINDS[i] if CLASS_K[k] == 'cg')
                    return navy, cg
                if view in ('truth', 'B'):
                    navy, cg = by_class(counts[v], 'B')
                    if navy:
                        segs.append((f"B{navy}", BLUE))
                    if cg:
                        segs.append((f"G{cg}", BLUE))
                elif not g.is_home('R', v):
                    b = gm.belief['R'][v]
                    navy, cg = by_class(b, 'B')
                    if navy:
                        segs.append((f"B~{navy}[{b['age']}]", BLUE))
                    if cg:
                        segs.append((f"G~{cg}[{b['age']}]", BLUE))
                if view in ('truth', 'R'):
                    navy, cg = by_class(counts[v], 'R')
                    if navy:
                        segs.append((f"P{navy}", RED))
                    if cg:
                        segs.append((f"C{cg}", CCG_COL))
                elif not g.is_home('B', v):
                    b = gm.belief['B'][v]
                    navy, cg = by_class(b, 'R')
                    if navy:
                        segs.append((f"P~{navy}[{b['age']}]", RED))
                    if cg:
                        segs.append((f"C~{cg}[{b['age']}]", CCG_COL))
                self._draw_segments(cv, x + sdx, y + sdy, sa, segs)
            # legend / overlays
            cv.create_text(8, MAP_H - 6, anchor='sw', font=('TkDefaultFont', 8), fill='#334',
                           text="Circle color/number = control (-1 Red ... +1 Blue).  B = Blue navy, G = Blue coast guard, P = Red navy, C = Red coast guard.\n"
                                "Thick outline = side is asserting.  Orange ring = incident.  Grey box = storm, light box = rough sea.  Squares = home ports.")
            if gm.jam_region:
                cv.create_text(8, 8, anchor='nw', fill='#b00', font=('TkDefaultFont', 9, 'bold'),
                               text=f"Red jamming active in region {gm.jam_region} ({', '.join(REGIONS[gm.jam_region])})")
            label = {'truth': 'Showing everything', 'B': "Blue's view (where Blue thinks Red is)",
                     'R': "Red's view (where Red thinks Blue is)"}[view]
            cv.create_text(MAP_W - 26, 8, anchor='ne', font=('TkDefaultFont', 9, 'bold'), text=label)

        @staticmethod
        def _draw_segments(cv, x, y, anchor, segs):
            """Draw a row of small colored count labels (e.g. 'B3 P2 C1') at (x, y)."""
            if not segs:
                return
            widths = [7 * len(t) + 4 for t, _ in segs]
            total = sum(widths)
            if anchor == 'e':
                x0 = x - total
            elif anchor == 'w':
                x0 = x
            else:
                x0 = x - total / 2
            for (text, col), w in zip(segs, widths):
                cv.create_text(x0, y, text=text, fill=col, anchor='w', font=('TkDefaultFont', 8, 'bold'))
                x0 += w

        def draw_ladder(self):
            cv, gm = self.ladder, self.game
            cv.delete('all')
            L = gm.P['L']
            cv.create_text(55, 10, text='Escalation level', font=('TkDefaultFont', 9, 'bold'))
            names = LEVEL_NAMES
            for lvl in range(L + 1):
                y1 = 160 - lvl * 23
                y0 = y1 - 20
                hue = ['#dff5df', '#f3f7c9', '#ffe6b3', '#ffc999', '#ff9f80', '#e53935'][lvl]
                cv.create_rectangle(12, y0, 98, y1, fill=hue if lvl <= gm.ell else 'white',
                                    outline='black', width=3 if lvl == gm.ell else 1)
                cv.create_text(55, (y0 + y1) / 2, text=f"{lvl} {names[lvl] if lvl < len(names) else ''}", font=('TkDefaultFont', 8))

        def draw_timeseries(self):
            cv, gm = self.ts, self.game
            cv.delete('all')
            W = cv.winfo_width()
            if W < 100:                      # not yet mapped: use the configured width
                W = MAP_W - 116
            H = 170
            x0, x1, y0, y1 = 40, W - 10, 15, H - 22
            T = max(1, gm.T)
            cv.create_rectangle(x0, y0, x1, y1, outline='#aaa')
            mid = (y0 + y1) / 2
            cv.create_line(x0, mid, x1, mid, fill='#ddd')
            cv.create_text(x0 - 4, y0, text='+1', anchor='e', font=('TkDefaultFont', 8))
            cv.create_text(x0 - 4, mid, text='0', anchor='e', font=('TkDefaultFont', 8))
            cv.create_text(x0 - 4, y1, text='-1', anchor='e', font=('TkDefaultFont', 8))
            cv.create_text(x0, y1 + 4, text='turn 0', anchor='n', font=('TkDefaultFont', 8))
            cv.create_text(x1, y1 + 4, text=f'turn {T}', anchor='ne', font=('TkDefaultFont', 8))
            cv.create_text(x0 + 6, y0 + 2, anchor='nw', fill=BLUE, font=('TkDefaultFont', 8, 'bold'), text='Blue control share (-1 to +1)')
            cv.create_text(x0 + 190, y0 + 2, anchor='nw', fill='#ff8c00', font=('TkDefaultFont', 8, 'bold'),
                           text='Escalation (bottom = 0, top = war); dots = incidents')

            def X(t):
                return x0 + (x1 - x0) * t / T
            share0 = sum(VALUE['B'][v] * C0[v] for v in C0) / sum(VALUE['B'].values())
            share = [(0, share0)]
            share += [(h['t'], h['share']) for h in gm.hist]
            ells = [(0, gm.P['ell0'])] + [(h['t'], h['ell']) for h in gm.hist]
            if len(share) > 1:
                cv.create_line([(X(t), mid - s * (y1 - y0) / 2) for t, s in share], fill=BLUE, width=2)
                cv.create_line([(X(t), y1 - e / gm.P['L'] * (y1 - y0)) for t, e in ells], fill='#ff8c00', width=2)
            for h in gm.hist:
                if h['incidents']:
                    cv.create_oval(X(h['t']) - 3, y1 - h['ell'] / gm.P['L'] * (y1 - y0) - 3,
                                   X(h['t']) + 3, y1 - h['ell'] / gm.P['L'] * (y1 - y0) + 3, fill='#ff8c00', outline='')

    root = tk.Tk()
    root.app = App(root)
    root.mainloop()


# ============================================================================
# 8.  BATCH RUNS, EXPERIMENTS, TRACE, EQUILIBRIUM REPORT
# ============================================================================

def run_batch(blue, red, design='D0', attacks=(), seeds=100, T=None, seed0=0, progress=None, weather='calm',
              params=None):
    """Run `seeds` games and summarize.  Returns (summary dict, list of per-game metrics)."""
    rows = []
    for k in range(seeds):
        rows.append(Game(blue, red, design, attacks, seed=seed0 + k, T=T, weather=weather, params=params).run().metrics())
        if progress and (k + 1) % 10 == 0:
            progress(k + 1, seeds)
    s = summarize(rows, blue, red, design, attacks)
    s['weather'] = weather
    return s, rows


def summarize(rows, blue='', red='', design='', attacks=()):
    """Sample mean, standard deviation and standard error (std / sqrt(n)) of the metrics."""
    n = len(rows)

    def mean(key):
        return statistics.fmean(r[key] for r in rows)

    def sd(key):
        return statistics.stdev([r[key] for r in rows]) if n > 1 else 0.0
    return {
        'blue': blue, 'red': red, 'design': design, 'attacks': '+'.join(sorted(attacks)) or 'none', 'n': n,
        'blue_mean': mean('blue_payoff'), 'blue_std': sd('blue_payoff'), 'blue_se': sd('blue_payoff') / math.sqrt(n),
        'red_mean': mean('red_payoff'), 'red_std': sd('red_payoff'), 'red_se': sd('red_payoff') / math.sqrt(n),
        'control_share': mean('control_share'), 'control_se': sd('control_share') / math.sqrt(n),
        'war_rate': mean('war'), 'war_se': sd('war') / math.sqrt(n),
        'war_t_mean': statistics.fmean([r['war_t'] for r in rows if r['war']]) if any(r['war'] for r in rows) else float('nan'),
        'max_ell': mean('max_ell'), 'mean_ell': mean('mean_ell'), 'incidents': mean('incidents'),
        'blue_fuel': mean('blue_fuel'), 'red_fuel': mean('red_fuel'),
    }


SUMMARY_COLS = ['blue', 'red', 'design', 'attacks', 'weather', 'n', 'blue_mean', 'blue_std', 'blue_se', 'red_mean',
                'red_std', 'red_se', 'control_share', 'control_se', 'war_rate', 'war_se', 'war_t_mean', 'max_ell',
                'mean_ell', 'incidents', 'blue_fuel', 'red_fuel']


def format_summary(s):
    return (f"Blue {s['blue']} vs Red {s['red']} | design {s['design']} | attacks {s['attacks']} | n={s['n']}\n"
            f"  Blue payoff  mean {s['blue_mean']:8.2f}  (std {s['blue_std']:7.2f}, s.e. {s['blue_se']:5.2f})\n"
            f"  Red  payoff  mean {s['red_mean']:8.2f}  (std {s['red_std']:7.2f}, s.e. {s['red_se']:5.2f})\n"
            f"  control share {s['control_share']:+.3f} | war rate {s['war_rate']:.2f} (mean war t {s['war_t_mean']:.1f})"
            f" | max ell {s['max_ell']:.2f} | mean ell {s['mean_ell']:.2f}\n"
            f"  incidents {s['incidents']:.2f} | moves B {s['blue_fuel']:.1f} R {s['red_fuel']:.1f}")


def print_trace(blue, red, design, attacks, seed, T, weather='calm'):
    """Per-period text trace of one game."""
    gm = Game(blue, red, design, attacks, seed=seed, T=T, weather=weather)
    print(f"Trace: Blue={blue} Red={red} design={design} attacks={sorted(gm.attacks) or 'none'} seed={seed} T={gm.T}")
    print(f"t=0  ell={gm.ell}  c: " + ' '.join(f"{v}{gm.c[v]:+.2f}" for v in gm.g.contested))
    while not gm.done:
        gm.step()
        h = gm.hist[-1]
        cnt = h['counts']

        def side(i):
            parts = []
            for v in gm.g.nodes:
                ks = [f"{cnt[v][k]}{k[0]}" for k in KINDS[i] if cnt[v][k] > 0]
                if ks:
                    tag = '(A)' if h['postures'][i].get(v) == 'A' else ''
                    parts.append(f"{v}:{'/'.join(ks)}{tag}")
            return ' '.join(parts)
        sea = ' '.join(f"{r}:{st}" for r, st in h['sea'].items() if st != 'calm') or 'calm'
        print(f"t={h['t']:<2d} ell={h['ell']} inc={','.join(h['incidents']) or '-':<8s} gB={h['gB']:7.2f} gR={h['gR']:7.2f}"
              f"  sea {sea}")
        print(f"     Blue: {side('B')}")
        print(f"     Red : {side('R')}")
        print("     c   : " + ' '.join(f"{v}{h['c'][v]:+.2f}" for v in gm.g.contested))
        for t, text in gm.events:
            if t == h['t'] and not text.startswith('INCIDENT'):
                print(f"     * {text}")
    m = gm.metrics()
    print(f"END t={gm.t}: u_B={m['blue_payoff']:.2f} u_R={m['red_payoff']:.2f} war={m['war']} incidents={m['incidents']} "
          f"max_ell={m['max_ell']} share={m['control_share']:+.3f}")


def print_equilibrium():
    """Template game report: payoff matrices, dominance, pure NE, maximin LP, CE LP."""
    mg = get_meta_game()
    n, L = mg.n, TEMPLATE_LABELS
    print("Template game: 14 templates per player (region split N/C/S in % x posture P/A)")
    for title, M in (("M_B (Blue payoff; rows = Blue template, cols = Red template)", mg.MB),
                     ("M_R (Red payoff)", mg.MR)):
        print("\n" + title)
        print(" " * 16 + ' '.join(f"{'#' + str(k + 1):>6s}" for k in range(n)) + "   (column #k = Red template k)")
        for a in range(n):
            print(f"{'#' + str(a + 1):>3s} {L[a]:>12s}" + ' '.join(f"{M[a][b]:6.1f}" for b in range(n)))
    SB, SR = mg.iesds()
    print(f"\nIterated elimination of strictly dominated strategies leaves {len(SB)} Blue and {len(SR)} Red templates:")
    print("  Blue: " + ', '.join(L[a] for a in SB))
    print("  Red : " + ', '.join(L[b] for b in SR))
    ne = mg.pure_nash()
    print(f"\nPure Nash equilibria (mutual best responses): {len(ne)}")
    for a, b in ne:
        print(f"  Blue {L[a]}  Red {L[b]}  payoffs ({mg.MB[a][b]:.2f}, {mg.MR[a][b]:.2f})")
    sel = mg.selected_nash()
    if sel:
        print(f"  played by 'equilibrium': Blue {L[sel[0]]}, Red {L[sel[1]]}")
    try:
        x, z = mg.maximin_lp(mg.CB)
        print(f"\nZero-sum part (Blue control payoff CB, Red gets -CB): maximin LP value {z:.3f}")
        print("  Blue maximin strategy: " + ', '.join(f"{L[k]} {x[k]:.3f}" for k in range(n) if x[k] > 1e-4))
        AR = [[-mg.CB[a][b] for a in range(n)] for b in range(n)]
        y, zr = mg.maximin_lp(AR)
        print(f"  Red minimax strategy:  " + ', '.join(f"{L[k]} {y[k]:.3f}" for k in range(n) if y[k] > 1e-4)
              + f"   (value check {-zr:.3f})")
        xb, zb = mg.maximin_lp(mg.MB)
        AR = [[mg.MR[a][b] for a in range(n)] for b in range(n)]
        yr, zr = mg.maximin_lp(AR)
        print(f"\nSecurity (maximin) strategies of the full general-sum game ('maximin' policy):")
        print(f"  Blue guarantees {zb:.2f}: " + ', '.join(f"{L[k]} {xb[k]:.3f}" for k in range(n) if xb[k] > 1e-4))
        print(f"  Red  guarantees {zr:.2f}: " + ', '.join(f"{L[k]} {yr[k]:.3f}" for k in range(n) if yr[k] > 1e-4))
        pi = mg.ce_lp()
        eB = sum(pi[a][b] * mg.MB[a][b] for a in range(n) for b in range(n))
        eR = sum(pi[a][b] * mg.MR[a][b] for a in range(n) for b in range(n))
        print(f"\nWelfare-maximizing correlated equilibrium (CE LP): expected payoffs B {eB:.2f}, R {eR:.2f}")
        for a in range(n):
            for b in range(n):
                if pi[a][b] > 1e-4:
                    print(f"  pi(Blue {L[a]}, Red {L[b]}) = {pi[a][b]:.3f}")
    except SystemExit as e:
        print(f"\n(LP parts skipped: {e})")


# ============================================================================
# 9.  COMMAND LINE
# ============================================================================

def parse_attacks(s):
    if not s or s.lower() == 'none':
        return ()
    out = tuple(a.strip() for a in s.split(',') if a.strip())
    for a in out:
        if a not in ATTACKS:
            raise SystemExit(f"unknown attack {a!r}; choose from {ATTACKS}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Maritime gray-zone wargame (GUI + batch simulator)")
    ap.add_argument('--batch', action='store_true', help='run a batch of games and print a summary')
    ap.add_argument('--equilibrium', action='store_true', help='print the template game and its equilibria')
    ap.add_argument('--trace', action='store_true', help='print a per-period trace of one game')
    ap.add_argument('--blue', default='moderate', choices=POLICY_NAMES)
    ap.add_argument('--red', default='moderate', choices=POLICY_NAMES)
    ap.add_argument('--design', default='D0', choices=DESIGNS)
    ap.add_argument('--weather', default='calm', choices=list(WEATHER), help='weather scenario omega')
    ap.add_argument('--epsB', type=float, default=None, help="Blue risk budget eps_B for greedy_br / mip_br / templates")
    ap.add_argument('--epsR', type=float, default=None, help="Red risk budget eps_R")
    ap.add_argument('--attacks', default='', help='comma-separated subset of ' + ','.join(ATTACKS) + ' (Workshop 2)')
    ap.add_argument('--seed', type=int, default=0, help='seed for --trace (and first seed of a batch)')
    ap.add_argument('--seeds', type=int, default=100, help='number of seeds for --batch')
    ap.add_argument('--T', type=int, default=None, help='horizon in periods (default 60)')
    args = ap.parse_args(argv)
    attacks = parse_attacks(args.attacks)
    if args.epsB is not None:
        PARAMS['eps'] = dict(PARAMS['eps'], B=args.epsB)
    if args.epsR is not None:
        PARAMS['eps'] = dict(PARAMS['eps'], R=args.epsR)
    if args.equilibrium:
        print_equilibrium()
    elif args.trace:
        print_trace(args.blue, args.red, args.design, attacks, args.seed, args.T or 10, args.weather)
    elif args.batch:
        t0 = time.time()
        s, _ = run_batch(args.blue, args.red, args.design, attacks, seeds=args.seeds, T=args.T, seed0=args.seed,
                         weather=args.weather)
        print(format_summary(s))
        print(f"({time.time() - t0:.1f}s)")
    else:
        launch_gui()


if __name__ == '__main__':
    main()
