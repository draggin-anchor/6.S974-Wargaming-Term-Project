"""Workshop 2 learning policies: Bayesian beliefs about the opponent, four choice rules,
regret, a belief about unseen ships, and a multi-period best response.

Setup (planning/workshop2-learning-plan.tex, decisions of Nov 2, 2026):

* Posture is seen only on scene.  A side sees the opponent's posture at zone v only when its
  own ships are at v (for Blue under D2, also next to v).  Counts are detected as before, with
  satellite detection raised to 0.25 (LEARN_PARAMS).
* Each side has a type: theta_v = Pr(it asserts at v | its ships are at v), one rate per
  contested zone, like standing rules of engagement.  Its posture at v is drawn from theta_v
  each period.  Its movements are chosen by the best-response MIP.
* Each side holds a Beta(a_v, b_v) belief on the opponent's theta_v and updates it with Bayes'
  rule from the on-scene sightings: a_v += #assert seen, b_v += #patrol seen.
* A choice rule turns the belief into the rate q_v the MIP uses:
      myopic      posterior mean
      committed   posterior mean, plus at least one ship in every reachable zone for N_e periods
      thompson    one draw from the posterior per zone per period
      optimistic  max(0, h/n - sqrt(2 ln t / n)) (a low rate is good news for the learner)
      oracle      the opponent's true theta (benchmark for regret)
* The MIP option values and risks are the expectation over the opponent's posture,
  (1 - q) a(.|P) + q a(.|A), and over the side's own typed posture (1 - theta) a(P) + theta a(A).
* Unseen ships (FleetBelief): a Bayes filter under a simple movement model.  Each period a ship
  stays with probability 1 - m or moves to a neighboring node (m = 0.33, the share of ships in a
  contested zone that leave it in a period, from rule-based and greedy games).  Where the
  opponent is detected the count is known, and the rest of its public order of battle is shared
  over the nodes not seen in proportion to the prediction.
* Multi-period best response: an H-period plan on a time-expanded copy of the map
  (ships follow paths, one edge or stay per period, endurance tracked along the path).
  Period 1 is carried out, then the plan is solved again next period.  The opponent is held
  at the current belief over the H periods.

Regret (per decision): J_true(oracle plan) - J_true(learner plan), both evaluated with option
values computed from the opponent's true theta on the same state.
"""
import math
import os
import random
from collections import defaultdict

import wargame_gui as W

LEARN_PARAMS = {'posture_on_scene': True, 'q_sat': 0.25}
RULES = ('myopic', 'committed', 'thompson', 'optimistic', 'oracle')

# Default types (assumed): how often each side's crews assert on scene in each zone.
# Red is most assertive at Scarborough and Second Thomas Shoal (Spratlys), less in the Paracels,
# which it already holds.  Blue asserts most in the Taiwan Strait.
TYPES = {
    'R_south': {'SEN': 0.4, 'MIY': 0.3, 'TWN': 0.5, 'EOT': 0.3, 'LUZ': 0.3, 'SCB': 0.8, 'STS': 0.7, 'PAR': 0.2},
    'R_north': {'SEN': 0.8, 'MIY': 0.7, 'TWN': 0.5, 'EOT': 0.3, 'LUZ': 0.3, 'SCB': 0.4, 'STS': 0.3, 'PAR': 0.2},
    'B_base': {'SEN': 0.3, 'MIY': 0.2, 'TWN': 0.5, 'EOT': 0.2, 'LUZ': 0.2, 'SCB': 0.4, 'STS': 0.3, 'PAR': 0.2},
}
# Priors: Beta(a, b) per zone.  'flat' = Beta(1, 1).  'pess_south' = Blue fears the South (mean 0.8, weight 5).
PRIORS = {
    'flat': {},
    'pess_south': {'SCB': (4.0, 1.0), 'STS': (4.0, 1.0), 'PAR': (4.0, 1.0)},
}
DEFAULTS = {'H': 1, 'prior': 'flat', 'type': None, 'opp_type': None, 'N_e': 20, 'm_move': 0.33,
            'regret': False}


def learn_config(side, P):
    cfg = dict(DEFAULTS)
    cfg.update(P.get('learn', {}).get(side, {}))
    return cfg


def make_learner(name, player, game):
    rule = name.split('_', 1)[1] if '_' in name else 'myopic'
    if rule not in RULES:
        raise ValueError(f"unknown learning rule {rule!r}; choose from {RULES}")
    return LearnPolicy(player, game, rule, learn_config(player, game.P))


def resolve(x):
    """A type or prior given by name or as a dict."""
    if isinstance(x, str):
        return TYPES.get(x, PRIORS.get(x))
    return x


# ----------------------------------------------------------------------------
# Belief about unseen ships
# ----------------------------------------------------------------------------
class FleetBelief:
    """Expected opponent ships of each type at each node, by Bayes' rule under a simple
    movement model: each period a ship stays with probability 1 - m, or moves to one of its
    node's neighbors with equal probability.

    Predict: x_k(v) <- (1 - m) x_k(v) + sum_{u in N(v)} m x_k(u) / |N(u)|.
    Update: where the opponent was detected this period the count is known.  The rest of the
    opponent's (public) order of battle is shared over the nodes not seen, in proportion to the
    predicted counts there.  A forecast tau periods ahead applies the prediction tau more times.
    """

    def __init__(self, game, player, m):
        self.player, self.m = player, m
        self.opp = W.OPP[player]
        g = game.g
        banned = set(g.homes[player])                # the opponent cannot enter my ports
        self.nodes = [v for v in g.nodes if v not in banned]
        self.adj = {v: [u for u in g.adj[v] if u not in banned] for v in self.nodes}
        self.kinds = W.KINDS[self.opp]
        counts = game.counts()
        self.total = {k: sum(counts[v][k] for v in g.nodes) for k in self.kinds}
        self.x = {k: {v: float(counts[v][k]) for v in self.nodes} for k in self.kinds}
        self._fc = None

    def _predict(self, x):
        m = self.m
        out = {}
        for k, xk in x.items():
            nk = {v: (1 - m) * xk[v] for v in self.nodes}
            for u in self.nodes:
                if xk[u] and self.adj[u]:
                    share = m * xk[u] / len(self.adj[u])
                    for v in self.adj[u]:
                        nk[v] += share
                elif xk[u]:
                    nk[u] += m * xk[u]
            out[k] = nk
        return out

    def step(self, obs):
        """One period: predict, then condition on this period's detections."""
        x = self._predict(self.x)
        seen = [v for v in self.nodes if obs.belief.get(v, {}).get('age', 1) == 0]
        for k in self.kinds:
            known = 0.0
            for v in seen:
                x[k][v] = float(obs.belief[v].get(k, 0))
                known += x[k][v]
            rest = [v for v in self.nodes if v not in seen]
            mass = sum(x[k][v] for v in rest)
            left = max(0.0, self.total[k] - known)
            if mass > 0:
                for v in rest:
                    x[k][v] *= left / mass
            elif rest and left > 0:
                for v in rest:
                    x[k][v] = left / len(rest)
        self.x = x
        self._fc = [x]

    def forecast(self, tau):
        """Expected counts tau periods after the current one: {node: {type: count}}."""
        if self._fc is None:
            self._fc = [self.x]
        while len(self._fc) <= tau:
            self._fc.append(self._predict(self._fc[-1]))
        xt = self._fc[tau]
        return defaultdict(dict, {v: {k: xt[k][v] for k in self.kinds} for v in self.nodes})


def _opp_counts(obs, belief, tau):
    """Believed opponent counts per node tau periods ahead.  belief is a FleetBelief, or None for
    the engine's last-seen counts (as in the Workshop 2 MIP-BR)."""
    if belief is None:
        return {v: obs.opp_counts(v) for v in obs.graph.nodes}
    fc = belief.forecast(tau)
    return {v: fc.get(v, {}) for v in obs.graph.nodes}


# ----------------------------------------------------------------------------
# Paths for the multi-period plan
# ----------------------------------------------------------------------------
class Mover:
    """Movement rules of one ship type for planning.  Step 1 uses the one-period candidate rule
    for the actual ship.  Later steps stay or move one edge, never into the opponent's ports or a
    storm-closed node, and the ship must keep enough endurance to reach a refuel point (own port or
    oiler).  A ship with no endurance to spare heads for a refuel point, as forced returns do."""

    def __init__(self, obs, s):
        self.obs, self.s = obs, s
        self.g = obs.graph
        self.i = s.owner
        self.D = W.D_K[s.kind]
        self.oiler = obs.oiler
        self.opp_homes = set(self.g.homes[W.OPP[self.i]])

    def refuel_dist(self, v):
        g, o = self.g, self.oiler
        d = g.port_dist[self.s.nation][v]
        if o is not None and o.on_station:
            d = min(d, g.dist[self.i][v][o.loc])
        return d

    def next_d(self, d, prev, w):
        stayed = prev == w
        if self.g.is_port(self.s, w):
            return self.D if stayed else d
        if self.oiler is not None and self.oiler.loc == w and stayed:
            return self.D
        return max(0, d - 1)

    def nexts(self, u, d):
        g, obs, s = self.g, self.obs, self.s
        if not g.is_port(s, u) and not (self.oiler is not None and self.oiler.loc == u) and d <= self.refuel_dist(u):
            hops = [w for w in g.adj[u] if w not in obs.closed and w not in self.opp_homes
                    and self.refuel_dist(w) < self.refuel_dist(u)]
            return hops or [u]
        out = []
        for w in [u] + list(g.adj[u]):
            if w in obs.closed or w in self.opp_homes:
                continue
            if self.i == 'B' and w != u and (w in obs.blocked or u in obs.blocked):
                continue
            if g.is_port(s, w) or self.next_d(d, u, w) >= self.refuel_dist(w):
                out.append(w)
        return out or [u]


def ship_paths(obs, s, H):
    """All H-step paths for free ship s (used for checks; the MIP uses the state graph below)."""
    mv = Mover(obs, s)
    paths = []

    def extend(path, d):
        if len(path) == H:
            paths.append(tuple(path))
            return
        u = path[-1]
        for w in mv.nexts(u, d):
            extend(path + [w], mv.next_d(d, u, w))

    for w in W.candidate_dests(obs, s):
        extend([w], mv.next_d(s.d, s.loc, w))
    return paths


def forced_path(obs, s, dest, H):
    """A ship under forced return: it goes to dest, then keeps stepping toward its nearest port."""
    g = obs.graph
    pd = g.port_dist[s.nation]
    path = [dest]
    while len(path) < H:
        u = path[-1]
        if g.is_port(s, u) or pd[u] == 0:
            path.append(u)
            continue
        hops = [w for w in g.adj[u] if pd[w] < pd[u] and w not in obs.closed]
        path.append(min(hops, key=lambda w: (pd[w], w)) if hops else u)
    return tuple(path)


# ----------------------------------------------------------------------------
# The learning policy
# ----------------------------------------------------------------------------
class LearnPolicy(W.Policy):
    """Bayesian learner with a choice rule and an H-period best-response MIP."""

    def __init__(self, player, game, rule, cfg):
        super().__init__(player, game.rng)
        self.rule, self.cfg = rule, cfg
        self.name = f'learn_{rule}'
        self.H = int(cfg['H'])
        # own random stream (Thompson draws, typed postures), so games stay on common random numbers
        self.lrng = random.Random(104729 * game.seed + (11 if player == 'B' else 23))
        prior = resolve(cfg['prior']) or {}
        self.a = {v: prior.get(v, (1.0, 1.0))[0] for v in game.g.contested}
        self.b = {v: prior.get(v, (1.0, 1.0))[1] for v in game.g.contested}
        self.a0, self.b0 = dict(self.a), dict(self.b)
        self.type = resolve(cfg['type'])            # own on-scene assertion rates (None: MIP chooses posture)
        self.opp_type = resolve(cfg['opp_type'])    # opponent's true rates (oracle and regret only)
        self.fleet = FleetBelief(game, player, cfg['m_move']) if cfg.get('fleet_belief', True) else None
        self.t = 0
        self.log = []                               # per-period records: beliefs, rates used, regret

    # ---------------------------------------------------------------- beliefs
    def update(self, obs):
        for v, p in obs.scene_obs:
            if p == 'A':
                self.a[v] += 1
            else:
                self.b[v] += 1

    def mean(self, v):
        return self.a[v] / (self.a[v] + self.b[v])

    def rates(self):
        """Rate q_v the MIP uses for the opponent's assertion at each zone."""
        if self.rule == 'oracle':
            return dict(self.opp_type)
        if self.rule == 'thompson':
            return {v: self.lrng.betavariate(self.a[v], self.b[v]) for v in self.a}
        if self.rule == 'optimistic':
            q = {}
            for v in self.a:
                n = (self.a[v] - self.a0[v]) + (self.b[v] - self.b0[v])
                h = self.a[v] - self.a0[v]
                q[v] = 0.0 if n == 0 else max(0.0, h / n - math.sqrt(2.0 * math.log(max(self.t, 2)) / n))
            return q
        return {v: self.mean(v) for v in self.a}

    # ---------------------------------------------------------------- act
    def act(self, obs):
        self.t = obs.t
        self.update(obs)
        if self.fleet is not None:
            self.fleet.step(obs)
        q = self.rates()
        commit = self.rule == 'committed' and self.t <= self.cfg['N_e']
        plan = solve_plan(obs, q, self.type, self.H, self.fleet, commit=commit)
        rec = {'t': self.t, 'q': q, 'mean': {v: self.mean(v) for v in self.a},
               'n': {v: self.a[v] + self.b[v] - self.a0[v] - self.b0[v] for v in self.a},
               'obj': plan['obj']}
        if self.cfg['regret'] and self.opp_type is not None:
            if self.rule == 'oracle':
                rec['regret'] = 0.0
            else:
                best = solve_plan(obs, self.opp_type, self.type, self.H, self.fleet)
                mine = plan_value_true(obs, plan, self.opp_type, self.type, self.H, self.fleet)
                rec['regret'] = max(0.0, best['obj'] - mine)
        self.log.append(rec)
        moves = plan['moves']
        if self.type is not None:
            # typed posture: at each zone where its ships will be, assert with probability theta_v
            pos = {s.id: moves.get(s.id, obs.forced.get(s.id, s.loc)) for s in obs.ships}
            occ = {v for v in pos.values() if v in W.REGION_OF}
            post = {v: ('A' if self.lrng.random() < self.type[v] else 'P') for v in sorted(occ)}
        else:
            post = plan['post']
        return moves, post


# ----------------------------------------------------------------------------
# The H-period best-response MIP
# ----------------------------------------------------------------------------
def _option_fn(obs, v, opp_cnt, q_v, own_theta):
    """Value and risk of own levels (n navy, c coast guard units) at v with own posture p,
    in expectation over the opponent's posture (assert with probability q_v).
    p = 'T' means the own posture is typed: assert with probability own_theta."""
    P, me, ell = obs.P, obs.player, obs.ell
    lam, Hf, Lam = P['lam'], W.horizon_factor(P), P['Lambda']
    sea = obs.sea_at(v)

    def one(n, c, p, po):
        th = n / (n + c) if n + c > 0 else 1.0
        phi, rho = W.eval_strength(P, obs.design, ell, me, (n + c) * W.STRENGTH_UNIT, th, p, opp_cnt, po, sea)
        return W.VALUE[me][v] * lam * Hf * phi - Lam * rho, rho

    def option(n, c, p):
        out_a = out_r = 0.0
        own = [(own_theta, 'A'), (1 - own_theta, 'P')] if p == 'T' else [(1.0, p)]
        for w1, p1 in own:
            for w2, p2 in ((q_v, 'A'), (1 - q_v, 'P')):
                if w1 * w2 == 0:
                    continue
                a_, r_ = one(n, c, p1, p2)
                out_a += w1 * w2 * a_
                out_r += w1 * w2 * r_
        return out_a, out_r
    return option


def _fixed(obs, H):
    """Ships under forced return: (kind, positions at periods 0..H)."""
    return [(s.kind, (s.loc,) + forced_path(obs, s, obs.forced[s.id], H)) for s in obs.ships if s.id in obs.forced]


def _flows(m_, obs, H):
    """Integer flows of the free ships on a time-expanded state graph.  A state is (ship type,
    node, endurance left), so ships of one type in the same state are interchangeable and a
    solution splits into whole-ship paths (flow decomposition).  Returns the first-period arcs,
    the arrivals per (node, period) and type, and the moves per period."""
    import gurobipy as gp
    start = defaultdict(list)
    for s in obs.free:
        start[(s.kind, s.loc, s.d)].append(s)
    movers, n_kind = {}, defaultdict(int)
    first = {}
    into = defaultdict(list)                  # (v, tau, k) -> arc vars arriving at v in period tau
    moves = [[] for _ in range(H)]
    inflow = defaultdict(list)
    layer = defaultdict(int)                  # state -> most ships that can be in it
    for (k, u, d), members in start.items():
        rep = members[0]
        mv = movers.setdefault(k, Mover(obs, rep))
        n_kind[k] += len(members)
        out = []
        for w in W.candidate_dests(obs, rep):
            d2 = mv.next_d(d, u, w)
            x = m_.addVar(vtype='I', lb=0, ub=len(members))
            first[(k, u, d), w] = x
            out.append(x)
            into[w, 0, k].append(x)
            if w != u:
                moves[0].append(x)
            inflow[1, (k, w, d2)].append(x)
            layer[(k, w, d2)] += len(members)
        m_.addConstr(gp.quicksum(out) == len(members))
    for tau in range(1, H):
        new = defaultdict(int)
        for (k, u, d), ub in layer.items():
            mv = movers[k]
            ub = min(ub, n_kind[k])
            out = []
            for w in mv.nexts(u, d):
                d2 = mv.next_d(d, u, w)
                x = m_.addVar(vtype='I', lb=0, ub=ub)
                out.append(x)
                into[w, tau, k].append(x)
                if w != u:
                    moves[tau].append(x)
                inflow[tau + 1, (k, w, d2)].append(x)
                new[(k, w, d2)] += ub
            m_.addConstr(gp.quicksum(out) == gp.quicksum(inflow[tau, (k, u, d)]))
        layer = new
    return start, first, into, moves, n_kind


def _navy_share(obs):
    """Navy share of the side's strength units (used by the coarse plan in later periods)."""
    P = obs.P
    navy = sum(W.weight(P, s.kind) for s in obs.ships if W.CLASS_K[s.kind] == 'navy')
    tot = sum(W.weight(P, s.kind) for s in obs.ships)
    return navy / tot if tot else 1.0


def solve_plan(obs, q, own_type, H, m=None, commit=False, coarse=None):
    """Solve the H-period plan.  Returns moves and postures for period 1, the objective, and the
    planned levels, moves and postures in every period (to evaluate the plan under other rates)."""
    import gurobipy as gp
    P, me, g = obs.P, obs.player, obs.graph
    eps = W.risk_budget(P['eps'][me], obs.ell, P)
    delta, gamma = P['delta'], P['gamma']
    fixed = _fixed(obs, H)
    if coarse is None:
        coarse = os.environ.get('LEARN_COARSE', '0') == '1'
    share = _navy_share(obs)
    m_ = gp.Model(env=W.MIPBRPolicy.env())
    m_.Params.PreSOS2Encoding = 3           # how Gurobi encodes the piecewise-linear terms (faster here; same optimum)
    start, first, into, moves, n_kind = _flows(m_, obs, H)
    obj = 0
    post_vars, lev_expr, move_expr = {}, {}, []
    for tau in range(H):
        disc = delta ** tau
        forced_moves = sum(1 for k, path in fixed if path[tau + 1] != path[tau])
        moves_tau = gp.quicksum(moves[tau])
        move_expr.append(moves_tau)
        if tau == 0:
            m_.addConstr(moves_tau <= obs.fuel)
        else:                                   # later periods: forced returns inside the plan may need more
            over = m_.addVar(lb=0)
            m_.addConstr(moves_tau <= max(0, obs.game.F[me] - forced_moves) + over)
            obj += -50.0 * disc * over
        obj += -gamma * disc * moves_tau
        opp_cnt_all = _opp_counts(obs, m, tau)
        risk_terms = []
        for v in g.contested:
            sea = obs.sea_at(v)
            unit = {k: int(round(W.weight(P, k, sea == 'rough') / W.STRENGTH_UNIT)) for k in W.KINDS[me]}
            option = _option_fn(obs, v, opp_cnt_all[v], q[v], own_type[v] if own_type else 0.0)
            lev, top, reach = {}, {}, {}
            for cl in ('navy', 'cg'):
                base = sum(unit[k] for k, path in fixed if path[tau + 1] == v and W.CLASS_K[k] == cl)
                kinds = [k for k in n_kind if W.CLASS_K[k] == cl and into.get((v, tau, k))]
                lev[cl] = base + gp.quicksum(unit[k] * x for k in kinds for x in into[v, tau, k])
                top[cl] = base + sum(unit[k] * n_kind[k] for k in kinds)
                levels = {base}
                for k in kinds:
                    levels = {x + j * unit[k] for x in levels for j in range(n_kind[k] + 1)}
                reach[cl] = sorted(levels)
            lev_expr[v, tau] = (lev['navy'], lev['cg'])
            if commit and tau == 0 and top['navy'] + top['cg'] > 0:
                short = m_.addVar(lb=0, ub=1)
                m_.addConstr(lev['navy'] + lev['cg'] >= 1 - short)
                obj += -500.0 * short
            if top['navy'] + top['cg'] == 0:
                obj += disc * option(0, 0, 'P')[0]
                continue
            y, lvl = {}, {}

            def add_option(okey, levels, val):
                x_max = levels[-1]
                y[okey] = m_.addVar(vtype='B')
                lvl[okey] = m_.addVar(lb=0, ub=x_max)
                m_.addConstr(lvl[okey] <= x_max * y[okey])
                xs = sorted(set(levels) | {0})
                vals = [val(x) for x in xs]
                if len(xs) == 1:
                    xs, vals = [0, 1], vals * 2
                av, rv = m_.addVar(lb=-gp.GRB.INFINITY), m_.addVar(lb=-gp.GRB.INFINITY)
                m_.addGenConstrPWL(lvl[okey], av, xs, [a for a, _ in vals])
                m_.addGenConstrPWL(lvl[okey], rv, xs, [r for _, r in vals])
                risk_terms.append(rv - vals[0][1] * (1 - y[okey]))
                return av - vals[0][0] * (1 - y[okey])

            if coarse and tau > 0:
                # later periods (coarse plan): value over the total level, at the fleet's navy share
                total = sorted({a + b for a in reach['navy'] for b in reach['cg']})
                sh = share
                if own_type:
                    obj += disc * add_option(('T', None), total, lambda x: option(x * sh, x * (1 - sh), 'T'))
                else:
                    obj += disc * add_option(('P', None), total, lambda x: option(x, 0, 'P'))
                    obj += disc * add_option(('A', None), total, lambda x: option(x * sh, x * (1 - sh), 'A'))
                m_.addConstr(gp.quicksum(y.values()) == 1)
                m_.addConstr(gp.quicksum(lvl.values()) == lev['navy'] + lev['cg'])
            elif own_type:
                # typed posture: one option per coast guard level c, over the navy level
                for c in reach['cg']:
                    obj += disc * add_option(('T', c), reach['navy'], lambda x, c=c: option(x, c, 'T'))
                m_.addConstr(gp.quicksum(y.values()) == 1)
                m_.addConstr(gp.quicksum(c * y['T', c] for c in reach['cg']) == lev['cg'])
                m_.addConstr(gp.quicksum(lvl['T', c] for c in reach['cg']) == lev['navy'])
            else:
                total = sorted({a + b for a in reach['navy'] for b in reach['cg']})
                obj += disc * add_option(('P', None), total, lambda x: option(x, 0, 'P'))
                for c in reach['cg']:
                    obj += disc * add_option(('A', c), reach['navy'], lambda x, c=c: option(x, c, 'A'))
                cg_patrol = m_.addVar(lb=0, ub=top['cg'])
                m_.addConstr(cg_patrol <= top['cg'] * y['P', None])
                m_.addConstr(gp.quicksum(y.values()) == 1)
                m_.addConstr(gp.quicksum(c * y['A', c] for c in reach['cg']) + cg_patrol == lev['cg'])
                m_.addConstr(lvl['P', None] + gp.quicksum(lvl['A', c] + c * y['A', c] for c in reach['cg'])
                             == lev['navy'] + lev['cg'])
            post_vars[v, tau] = (y, lvl)
        slack = m_.addVar(lb=0.0)
        m_.addConstr(gp.quicksum(risk_terms) <= eps + slack)
        obj += -1000.0 * disc * slack
    m_.setObjective(obj, gp.GRB.MAXIMIZE)
    m_.optimize()
    dump = os.environ.get('LEARN_DUMP')
    if dump and m_.Runtime > float(os.environ.get('LEARN_DUMP_SECS', 10)):
        m_.write(os.path.join(dump, f'{me}_t{obs.t}_H{H}_{m_.Runtime:.0f}s.mps'))
    out = {}
    for (k, u, d), members in start.items():
        pool = sorted(members, key=lambda s: s.id)
        for (key, w), x in first.items():
            if key != (k, u, d) or w == u:
                continue
            for _ in range(int(round(x.X))):
                out[pool.pop(0).id] = w
    post, post_tau = {}, {}
    for (v, tau), (y, lvl) in post_vars.items():
        chosen = next((pc for pc, var in y.items() if var.X > 0.5), ('P', None))
        p, c = chosen
        if p == 'T':
            continue
        occupied = (c if (p == 'A' and c is not None and not (coarse and tau > 0)) else 0) + lvl[p, c].X > 0.5
        post_tau[v, tau] = p if occupied else 'P'
        if tau == 0 and occupied:
            post[v] = p
    levels = {vt: (int(round(_val(a))), int(round(_val(b)))) for vt, (a, b) in lev_expr.items()}
    return {'moves': out, 'post': post, 'obj': m_.ObjVal, 'levels': levels, 'coarse': coarse, 'share': share,
            'nmoves': [int(round(_val(e))) for e in move_expr], 'post_tau': post_tau,
            'size': (m_.NumVars, m_.NumConstrs, m_.NumGenConstrs), 'runtime': m_.Runtime}


def _val(e):
    return e.getValue() if hasattr(e, 'getValue') else float(e)


def plan_value_true(obs, plan, q, own_type, H, m=None):
    """The MIP objective of a solved plan (its levels, moves and postures in every period) when the
    option values and risks are computed from rates q instead of the rates the plan was made with."""
    P, me, g = obs.P, obs.player, obs.graph
    eps = W.risk_budget(P['eps'][me], obs.ell, P)
    delta, gamma = P['delta'], P['gamma']
    total = 0.0
    for tau in range(H):
        disc = delta ** tau
        total += -gamma * disc * plan['nmoves'][tau]
        opp_cnt_all = _opp_counts(obs, m, tau)
        risk = 0.0
        for v in g.contested:
            n_, c_ = plan['levels'].get((v, tau), (0, 0))
            option = _option_fn(obs, v, opp_cnt_all[v], q[v], own_type[v] if own_type else 0.0)
            if plan.get('coarse') and tau > 0:
                x, sh = n_ + c_, plan['share']
                if own_type:
                    a_, r_ = option(x * sh, x * (1 - sh), 'T')
                elif plan['post_tau'].get((v, tau), 'P') == 'A' and x > 0:
                    a_, r_ = option(x * sh, x * (1 - sh), 'A')
                else:
                    a_, r_ = option(x, 0, 'P')
            elif own_type:
                a_, r_ = option(n_, c_, 'T')
            elif plan['post_tau'].get((v, tau), 'P') == 'A' and n_ + c_ > 0:
                a_, r_ = option(n_, c_, 'A')
            else:
                a_, r_ = option(n_ + c_, 0, 'P')
            total += disc * a_
            risk += r_
        total += -1000.0 * disc * max(0.0, risk - eps)
    return total
