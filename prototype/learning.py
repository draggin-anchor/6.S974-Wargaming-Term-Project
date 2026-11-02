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
* Unseen ships: a sighting of age a is still right with probability (1 - m)^a (m = 0.33, the
  share of ships in a contested zone that leave it in a period, from rule-based and greedy games).  The rest of
  the opponent's known order of battle is spread evenly over the zones and its ports.
* Multi-period best response: an H-period plan on a time-expanded copy of the map
  (ships follow paths, one edge or stay per period, endurance tracked along the path).
  Period 1 is carried out, then the plan is solved again next period.  The opponent is held
  at the current belief over the H periods.

Regret (per decision): J_true(oracle plan) - J_true(learner plan), both evaluated with option
values computed from the opponent's true theta on the same state.
"""
import math
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
def believed_counts(obs, m, extra_age=0):
    """Opponent kind counts per node: last sighting weighted by (1 - m)^age, plus the
    rest of the opponent's (public) order of battle spread evenly over the contested zones
    and the opponent's ports."""
    opp = W.OPP[obs.player]
    g = obs.graph
    total = defaultdict(int)
    for k, by_port in W.FLEET.items():
        if W.SHIP_TYPES[k][0] == opp:
            total[k] += sum(by_port.values())
    cnt, seen = {}, defaultdict(float)
    for v in g.nodes:
        b = obs.belief.get(v, {})
        wgt = (1.0 - m) ** (b.get('age', 0) + extra_age)
        cnt[v] = {k: wgt * b.get(k, 0) for k in W.KINDS[opp]}
        for k in W.KINDS[opp]:
            seen[k] += cnt[v][k]
    spread_nodes = list(g.contested) + list(g.homes[opp])
    for k in W.KINDS[opp]:
        rest = max(0.0, total[k] - seen[k]) / len(spread_nodes)
        for v in spread_nodes:
            cnt[v][k] += rest
    return cnt


# ----------------------------------------------------------------------------
# Paths for the multi-period plan
# ----------------------------------------------------------------------------
def ship_paths(obs, s, H):
    """All H-step paths for free ship s.  Step 1 uses the one-period candidate rule.  Later steps
    stay or move one edge, never into the opponent's ports or a storm-closed node, and a ship
    must keep enough endurance to reach a refuel point (own port or oiler) from where it is."""
    game, g = obs.game, obs.graph
    i = s.owner
    D = W.D_K[s.kind]
    oiler = obs.oiler
    opp_homes = set(g.homes[W.OPP[i]])

    def refuel_dist(v):
        d = g.port_dist[s.nation][v]
        if oiler is not None and oiler.on_station:
            d = min(d, g.dist[i][v][oiler.loc])
        return d

    def next_d(d, prev, w):
        stayed = prev == w
        if g.is_port(s, w):
            return D if stayed else d
        if oiler is not None and oiler.loc == w and stayed:
            return D
        return max(0, d - 1)

    paths = []

    def nexts(u, d):
        if not g.is_port(s, u) and not (oiler is not None and oiler.loc == u) and d <= refuel_dist(u):
            # forced return (as in the engine): step toward the nearest refuel point
            hops = [w for w in g.adj[u] if w not in obs.closed and w not in opp_homes and refuel_dist(w) < refuel_dist(u)]
            return hops or [u]
        out = []
        for w in [u] + list(g.adj[u]):
            if w in obs.closed or w in opp_homes:
                continue
            if i == 'B' and w != u and (w in obs.blocked or u in obs.blocked):
                continue
            if g.is_port(s, w) or next_d(d, u, w) >= refuel_dist(w):
                out.append(w)
        return out or [u]

    def extend(path, d):
        if len(path) == H:
            paths.append(tuple(path))
            return
        u = path[-1]
        for w in nexts(u, d):
            extend(path + [w], next_d(d, u, w))

    for w in W.candidate_dests(obs, s):
        extend([w], next_d(s.d, s.loc, w))
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
        q = self.rates()
        commit = self.rule == 'committed' and self.t <= self.cfg['N_e']
        plan = solve_plan(obs, q, self.type, self.H, self.cfg['m_move'], commit=commit)
        rec = {'t': self.t, 'q': q, 'mean': {v: self.mean(v) for v in self.a},
               'n': {v: self.a[v] + self.b[v] - self.a0[v] - self.b0[v] for v in self.a},
               'obj': plan['obj']}
        if self.cfg['regret'] and self.opp_type is not None:
            if self.rule == 'oracle':
                rec['regret'] = 0.0
            else:
                best = solve_plan(obs, self.opp_type, self.type, self.H, self.cfg['m_move'])
                mine = plan_value_true(obs, plan, self.opp_type, self.type, self.H, self.cfg['m_move'])
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


def _setup(obs, H):
    """Groups of interchangeable free ships with their H-step paths, and fixed (forced) paths."""
    groups = defaultdict(list)
    for s in obs.free:
        groups[(s.kind, s.loc, s.d)].append(s)
    gpaths = {key: ship_paths(obs, members[0], H) for key, members in groups.items()}
    fixed = [(s.kind, (s.loc,) + forced_path(obs, s, obs.forced[s.id], H)) for s in obs.ships if s.id in obs.forced]
    return groups, gpaths, fixed


def solve_plan(obs, q, own_type, H, m, commit=False):
    """Solve the H-period plan.  Returns moves (period 1), postures (period 1), objective, and the
    path counts (for evaluating the plan under other rates)."""
    import gurobipy as gp
    P, me, g = obs.P, obs.player, obs.graph
    eps = W.risk_budget(P['eps'][me], obs.ell, P)
    delta, gamma = P['delta'], P['gamma']
    groups, gpaths, fixed = _setup(obs, H)
    m_ = gp.Model(env=W.MIPBRPolicy.env())
    z = {}
    for key, members in groups.items():
        for pi in gpaths[key]:
            z[key, pi] = m_.addVar(vtype='I', lb=0, ub=len(members))
        m_.addConstr(gp.quicksum(z[key, pi] for pi in gpaths[key]) == len(members))
    obj = 0
    slacks = []
    post_vars = {}
    for tau in range(H):
        disc = delta ** tau
        # moves in period tau (forced moves are charged first, as in the engine)
        forced_moves = sum(1 for k, path in fixed if path[tau + 1] != path[tau])
        moves_tau = gp.quicksum(var for (key, pi), var in z.items()
                                if pi[tau] != (key[1] if tau == 0 else pi[tau - 1]))
        budget = obs.fuel if tau == 0 else max(0, obs.game.F[me] - forced_moves)
        if tau == 0:
            m_.addConstr(moves_tau <= budget)
        else:                                   # later periods: forced returns inside the plan may need more
            over = m_.addVar(lb=0)
            m_.addConstr(moves_tau <= budget + over)
            obj += -50.0 * disc * over
        obj += -gamma * disc * moves_tau
        opp_cnt_all = believed_counts(obs, m, extra_age=tau)
        risk_terms = []
        for v in g.contested:
            sea = obs.sea_at(v)
            unit = {k: int(round(W.weight(P, k, sea == 'rough') / W.STRENGTH_UNIT)) for k in W.KINDS[me]}
            option = _option_fn(obs, v, opp_cnt_all[v], q[v], own_type[v] if own_type else 0.0)
            lev, top, reach = {}, {}, {}
            arr = [(key, pi) for (key, pi) in z if pi[tau] == v]
            for cl in ('navy', 'cg'):
                base = sum(unit[k] for k, path in fixed if path[tau + 1] == v and W.CLASS_K[k] == cl)
                terms = [(key, pi) for key, pi in arr if W.CLASS_K[key[0]] == cl]
                lev[cl] = base + gp.quicksum(unit[key[0]] * z[key, pi] for key, pi in terms)
                gmax = defaultdict(int)
                for key, pi in terms:
                    gmax[key] = len(groups[key])
                top[cl] = base + sum(unit[key[0]] * nmax for key, nmax in gmax.items())
                levels = {base}
                for key, nmax in gmax.items():
                    levels = {x + j * unit[key[0]] for x in levels for j in range(nmax + 1)}
                reach[cl] = sorted(levels)
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

            if own_type:
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
        slacks.append(slack)
    m_.setObjective(obj, gp.GRB.MAXIMIZE)
    m_.optimize()
    counts = {(key, pi): int(round(var.X)) for (key, pi), var in z.items() if var.X > 0.5}
    moves = {}
    for key, members in groups.items():
        pool = sorted(members, key=lambda s: -s.d)
        for pi in gpaths[key]:
            n = counts.get((key, pi), 0)
            if pi[0] == key[1]:
                for _ in range(n):
                    pool.pop(0)
                continue
            for _ in range(n):
                moves[pool.pop(0).id] = pi[0]
    post = {}
    for (v, tau), (y, lvl) in post_vars.items():
        if tau > 0:
            continue
        for (p, c), var in y.items():
            if p in 'PA' and var.X > 0.5 and (c or 0) + lvl[p, c].X > 0.5:
                post[v] = p
    return {'moves': moves, 'post': post, 'obj': m_.ObjVal, 'counts': counts,
            'size': (m_.NumVars, m_.NumConstrs, m_.NumGenConstrs), 'slack': [s.X for s in slacks],
            'post_tau': _post_all(post_vars)}


def _post_all(post_vars):
    return {vt: next((p for (p, c), var in y.items() if var.X > 0.5), 'P') for vt, (y, lvl) in post_vars.items()}


def plan_value_true(obs, plan, q, own_type, H, m):
    """The MIP objective of a solved plan (its paths and postures) when the option values and
    risks are computed from rates q instead of the rates the plan was made with."""
    P, me, g = obs.P, obs.player, obs.graph
    groups, gpaths, fixed = _setup(obs, H)
    eps = W.risk_budget(P['eps'][me], obs.ell, P)
    delta, gamma = P['delta'], P['gamma']
    total = 0.0
    for tau in range(H):
        disc = delta ** tau
        moves_tau = sum(n for (key, pi), n in plan['counts'].items()
                        if pi[tau] != (key[1] if tau == 0 else pi[tau - 1]))
        total += -gamma * disc * moves_tau
        opp_cnt_all = believed_counts(obs, m, extra_age=tau)
        risk = 0.0
        for v in g.contested:
            sea = obs.sea_at(v)
            unit = {k: int(round(W.weight(P, k, sea == 'rough') / W.STRENGTH_UNIT)) for k in W.KINDS[me]}
            lev = {'navy': 0, 'cg': 0}
            for k, path in fixed:
                if path[tau + 1] == v:
                    lev[W.CLASS_K[k]] += unit[k]
            for (key, pi), n in plan['counts'].items():
                if pi[tau] == v:
                    lev[W.CLASS_K[key[0]]] += unit[key[0]] * n
            option = _option_fn(obs, v, opp_cnt_all[v], q[v], own_type[v] if own_type else 0.0)
            n_, c_ = lev['navy'], lev['cg']
            if own_type:
                a_, r_ = option(n_, c_, 'T')
            elif plan['post_tau'].get((v, tau), 'P') == 'A' and n_ + c_ > 0:
                a_, r_ = option(n_, c_, 'A')
            else:
                a_, r_ = option(n_ + c_, 0, 'P')
            total += disc * a_
            risk += r_
        total += -1000.0 * disc * max(0.0, risk - eps)
    return total
