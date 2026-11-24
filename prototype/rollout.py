"""Workshop 2 lookahead by rollout (policy 'rollout').

The one-period best response (MIP-BR) looks one period ahead: the value of a change in control
today is carried forward by the horizon factor, and the incident risk counts only this period.
Rollout looks further ahead by simulation instead of a bigger program:

  1. Candidate plans.  A small set of plans for this period, every one within the risk budget:
       mip        the exact one-period MIP-BR plan
       mip_patrol the same moves with every posture set to patrol
       mip_half   the MIP-BR plan with half the risk budget
       hold       no discretionary moves, patrol everywhere
  2. Simulation.  For each candidate and each of M sampled futures, play this period with the
     candidate, then play h - 1 more periods with a simple base rule for both sides (the greedy
     best response, the solver-free heuristic of the same one-period problem).
  3. Score.  The candidate's score is Blue's mean payoff over the M futures: the discounted stage
     payoffs of the h simulated periods, minus W if war breaks out, plus an approximate future
     after period h (truncated rollout): the last stage payoff held for the rest of the year,
         J_tail = delta^h (sum_v V_v c_v - eta ell) (1 + delta + ... + delta^(T - t - h)).
  4. Keep the MIP-BR plan unless another candidate scores better by more than Z = 2 paired standard
     errors over the M futures; then play the best such candidate.  Next period, do it all again.
     (The greedy plan is not a candidate: the simulation itself continues with the greedy rule,
     so it would score the greedy plan as if it fitted best what follows.  In the first test games
     it was chosen on a third of the turns and Blue did worse than with MIP-BR.)

Every candidate is scored on the same M futures (same random numbers), so the comparison between
candidates is paired.

What a simulated future uses (only what the deciding side knows):
  * its own ships, endurance, maintenance and the oiler: known;
  * opponent ships: the last-seen counts at each node (obs.belief), the rest of the opponent's public
    order of battle in its home ports with the usual third of each fleet in maintenance, all with
    full endurance;
  * the escalation level: known, or drawn from the side's belief when the level is hidden;
  * weather: drawn from the weather scenario's probabilities (Nature's move);
  * attacks are not modeled in the simulation (the side does not know what Red is doing), but
    false contacts already in its picture are simulated as real ships;
  * the opponent plays the base rule.

    python3 rollout.py smoke                 # short timing test (a few turns)
"""
import copy
import random
import sys
import time

import wargame_gui as W

H_ROLL = 10          # periods simulated per future (this period plus 9)
M_ROLL = 8           # sampled futures per candidate
BASE = 'greedy_br'   # base rule for both sides in the simulation
Z = 2.0              # a candidate replaces the MIP-BR plan only if it scores better by more than Z standard errors


class FixedPlan(W.Policy):
    name = 'fixed'

    def __init__(self, player, rng, plan):
        super().__init__(player, rng)
        self.plan = plan

    def act(self, obs):
        return self.plan


class RolloutPolicy(W.Policy):
    """Truncated rollout over a small set of candidate plans (see the module docstring)."""
    name = 'rollout'

    def __init__(self, player, game, h=H_ROLL, M=M_ROLL, base=BASE):
        super().__init__(player, game.rng)
        self.h, self.M, self.base = h, M, base
        self.game = game        # copied only to build the simulation model (own side, map, public state)
        self.mip = W.MIPBRPolicy(player, game.rng)          # draws no random numbers
        # the greedy candidate and the simulations use their own random streams, so the real game
        # keeps the same random numbers as a MIP-BR game on the same seed until the plans differ
        self.seed = 7349 * game.seed + (1 if player == 'B' else 2)
        self.log = []                                       # per decision: candidate scores and choice

    # ------------------------------------------------------------ candidates
    def candidates(self, obs):
        me = self.player
        eps = W.risk_budget(obs.P['eps'][me], obs.esc, obs.P)
        out = {}
        mv, po = self.mip.act(obs)
        out['mip'] = (mv, po)
        out['mip_patrol'] = (mv, {})
        half = copy.copy(obs)
        half.P = dict(obs.P, eps=dict(obs.P['eps'], **{me: obs.P['eps'][me] / 2}))
        out['mip_half'] = self.mip.act(half)
        out['hold'] = ({}, {})
        # drop duplicates (same moves and postures), keeping the first name
        seen, uniq = [], {}
        for k, (m_, p_) in out.items():
            key = (tuple(sorted(m_.items())), tuple(sorted((v, x) for v, x in p_.items() if x == 'A')))
            if key not in seen:
                seen.append(key)
                uniq[k] = (m_, p_)
        return uniq

    # ------------------------------------------------------------ simulation
    def _model(self, obs, rng):
        """A copy of the game at this decision with the opponent replaced by what this side believes."""
        game, me = self.game, self.player
        opp = W.OPP[me]
        keep = game.policy, game.hist, game.events, getattr(game, 'truth_events', None)
        game.policy, game.hist, game.events = {}, [], []
        if keep[3] is not None:
            game.truth_events = []
        try:
            sim = copy.deepcopy(game)
        finally:
            game.policy, game.hist, game.events = keep[:3]
            if keep[3] is not None:
                game.truth_events = keep[3]
        sim.attacks = set()
        sim.rng = random.Random(rng.random())
        sim.wx_rng = random.Random(rng.random())
        # opponent ships at their believed positions, the rest of the order of battle at home
        sim.ships = [s for s in sim.ships if s.owner == me]
        left = {k: sum(by.values()) for k, by in W.FLEET.items() if W.SHIP_TYPES[k][0] == opp}
        for v in sim.g.nodes:
            if sim.g.is_home(me, v):
                continue
            b = obs.belief.get(v, {})
            for k in W.KINDS[opp]:
                n = min(left[k], int(round(b.get(k, 0))))
                for _ in range(n):
                    sim.ships.append(W.Ship(len(sim.ships) + 1000, opp, k, v, W.D_K[k]))
                left[k] -= n
        for k, n in left.items():
            ports = list(W.FLEET[k])
            # the usual share of each fleet is in the yard (maint_init_frac), taken from the ships not seen
            n_yard = min(n, round(sim.P['maint_init_frac'] * sum(W.FLEET[k].values())))
            for j in range(n):
                s = W.Ship(len(sim.ships) + 1000, opp, k, ports[j % len(ports)], W.D_K[k])
                if j < n_yard:
                    s.maint, s.hold = True, rng.randint(1, sim.P['maint_len'])
                sim.ships.append(s)
        sim.ship_by_id = {s.id: s for s in sim.ships}
        # the opponent's picture of this side: assumed exact (this side cannot see the opponent's picture)
        cnt = sim.counts()
        for v in sim.g.nodes:
            sim.belief[opp][v] = {k: cnt[v][k] for k in W.KINDS[me]}
            sim.belief[opp][v]['age'] = 0
        if sim.hidden:
            sim.ell = rng.choices(range(len(obs.esc_belief)), weights=obs.esc_belief)[0]
        return sim

    def _score(self, sim, plan, t):
        """Play this period with plan, then h - 1 periods of the base rule; Blue's (or Red's) payoff
        from this period on, in this period's money, plus the approximate future."""
        me, P = self.player, sim.P
        u0, d0 = sim.u[me], P['delta'] ** (t - 1)
        forced = {'B': {}, 'R': {}}
        for s in sim.ships:
            fm = sim._forced_move(s)
            if fm is not None:
                forced[s.owner][s.id] = fm
        sim.policy = {i: W.make_policy(self.base, i, sim) for i in 'BR'}
        sim.policy[me] = FixedPlan(me, sim.rng, plan)
        moves, post, obs_of = sim.decide(t, forced)
        sim.end_period(t, [], forced, moves, post, obs_of)
        sim.policy[me] = W.make_policy(self.base, me, sim)
        for _ in range(self.h - 1):
            if sim.done:
                break
            sim.step()
        val = (sim.u[me] - u0) / d0
        if not sim.done:
            sg = W.SIGMA[me]
            stage = sg * sum(W.VALUE[me][v] * sim.c[v] for v in sim.g.contested) - P['eta'] * sim.ell
            n_left = sim.T - sim.t
            dt = sim.t - (t - 1)
            val += P['delta'] ** dt * stage * sum(P['delta'] ** k for k in range(n_left))
        return val

    def act(self, obs):
        cands = self.candidates(obs)
        if len(cands) == 1:
            plan = next(iter(cands.values()))
            self.log.append({'t': obs.t, 'choice': next(iter(cands)), 'scores': {}})
            return plan
        rng = random.Random(self.seed * 1000003 + obs.t)
        sims = [self._model(obs, rng) for _ in range(self.M)]
        vals = {k: [self._score(copy.deepcopy(sim), plan, obs.t) for sim in sims] for k, plan in cands.items()}
        scores = {k: sum(v) / self.M for k, v in vals.items()}
        # keep the MIP-BR plan unless another candidate beats it by more than Z paired standard errors
        # on the same sampled futures (a single war in eight futures should not decide the turn)
        best = 'mip'
        for k, v in vals.items():
            d = [a - b for a, b in zip(v, vals['mip'])]
            mean = sum(d) / self.M
            se = (sum((x - mean) ** 2 for x in d) / (self.M - 1) / self.M) ** 0.5
            if mean > Z * se and mean > 0 and scores[k] > scores[best]:
                best = k
        self.log.append({'t': obs.t, 'choice': best, 'scores': scores})
        return cands[best]


def smoke(T=4, seed=0):
    t0 = time.time()
    g = W.Game('rollout', 'mip_br', 'D0', (), seed=int(seed), T=int(T), weather='nominal')
    while not g.done:
        t1 = time.time()
        g.step()
        lg = g.policy['B'].log[-1]
        print(f"t={g.t} {time.time() - t1:.1f}s choice {lg['choice']} "
              + ' '.join(f"{k} {v:.1f}" for k, v in lg['scores'].items()), flush=True)
    print(f"u_B {g.u['B']:.2f} in {time.time() - t0:.0f}s")


if __name__ == '__main__':
    globals()[sys.argv[1] if len(sys.argv) > 1 else 'smoke'](*sys.argv[2:])
