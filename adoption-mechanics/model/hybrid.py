"""Mixed panels and the surprisingly-popular rule (Prelec, Seung and McCoy 2017).

The true answer is 1 (the successor is better) or 0 (it is worse). People: each holds the local private signal
with probability `people_private` and then answers the truth; the rest answer 1 with probability UNINFORMED_YES. Agents
share a blind spot: each errs (answers 0) with probability `agent_error`, shifted by `agent_info` toward the
truth when agents know something of the local fact, errors correlated at `agent_rho` by
the one-factor model, and none holds the local signal. Every member also predicts the share of the panel that
will answer 1. A member who holds the signal believes the successor world and predicts that world's expected
share; every other member believes the incumbent world and predicts its expected share. With
agent_predicts_crowd False, agents predict one half (no model of the crowd).

The rule picks 1 when the actual share answering 1 exceeds the panel's mean prediction.

dilution_limit and dilution_bound give the large-panel law of the unweighted threshold rule (Proposition 6 of the
series, common-mode dilution): with agents that carry no information about the local fact and share one latent
factor, adoption of a worse design does not depend on the people at all, and the gap between the two worlds is
bounded by a term that shrinks as the agents' correlation grows and as the informed people's share falls.
"""
import math
import random
from statistics import NormalDist

from correlation import bivariate_normal_cdf
from sensors import latent_votes

UNINFORMED_YES = 0.2
_N = NormalDist()


def surprisingly_popular(votes: list[int], predictions: list[float]) -> int:
    """1 if the share of votes for 1 exceeds the mean predicted share, else 0 (a tie keeps 0, the status quo)."""
    share = sum(votes) / len(votes)
    return 1 if share > math.fsum(predictions) / len(predictions) else 0


def panel_run(n_people: int, n_agents: int, people_private: float, agent_rho: float, agent_predicts_crowd: bool,
              trials: int, seed: int, agent_error: float = 0.7, truth: int = 1,
              agent_info: float = 0.0) -> dict[str, float]:
    """Probability that each rule picks the successor (answer 1) when the true answer is `truth`: the panel's
    majority (a tie keeps the incumbent), the surprisingly-popular rule, and a static threshold at the share the
    incumbent world predicts (no predictions asked), and the majority of the people alone (a tie keeps the incumbent). With truth 1 these are adoption of a better design, A+;
    with truth 0, adoption of a worse one, A-. Informed people answer the truth; uninformed people answer 1 with
    probability UNINFORMED_YES; agents answer 1 with probability 1 - agent_error + agent_info * (truth - 1/2), so
    agent_info 0 is a blind spot they cannot see past and a positive agent_info is partial knowledge of the local
    fact, correlated at agent_rho. A fifth rule, the midpoint, adopts when the panel's share for the successor
    exceeds the mean of the two worlds' expected shares. Informed people predict the true world's expected share;
    uninformed people, and agents that model the crowd, predict the incumbent world's; other agents predict
    one half."""
    n = n_people + n_agents
    def agent_yes(w):
        return min(1.0, max(0.0, 1.0 - agent_error + agent_info * (w - 0.5)))
    def expected(w):
        return (n_people * (people_private * w + (1.0 - people_private) * UNINFORMED_YES) + n_agents * agent_yes(w)) / n
    world0 = expected(0)
    midpoint = (expected(0) + expected(1)) / 2.0
    # Predictions conditioned on one's own answer (Prelec, Seung and McCoy): each member predicts the share of the
    # whole panel answering 1, counting their own answer and the expected answers of the others in the world they
    # believe. An agent that models the crowd believes the incumbent world, and because agents' answers share a
    # factor, its own answer moves its expectation of the other agents' answers.
    def person_yes(w):
        return people_private * w + (1.0 - people_private) * UNINFORMED_YES
    y0 = agent_yes(0)
    if 0.0 < y0 < 1.0 and agent_rho > 0.0:
        t = _N.inv_cdf(1.0 - y0)
        both = bivariate_normal_cdf(-t, -t, agent_rho)
        other_given = {1: both / y0, 0: (y0 - both) / (1.0 - y0)}
    else:
        other_given = {1: y0, 0: y0}
    rng = random.Random(seed)
    maj = sp = thr = ppl = mid = 0
    for _ in range(trials):
        votes, preds = [], []
        for _ in range(n_people):
            if rng.random() < people_private:
                votes.append(truth)
                preds.append((truth + (n_people - 1) * person_yes(truth) + n_agents * agent_yes(truth)) / n)
            else:
                v = 1 if rng.random() < UNINFORMED_YES else 0
                votes.append(v)
                preds.append((v + (n_people - 1) * person_yes(0) + n_agents * y0) / n)
        for err in latent_votes(n_agents, 1.0 - agent_yes(truth), agent_rho, rng):
            v = 0 if err else 1
            votes.append(v)
            if agent_predicts_crowd:
                preds.append((v + n_people * person_yes(0) + (n_agents - 1) * other_given[v]) / n)
            else:
                preds.append(0.5)
        share = sum(votes) / n
        ppl += n_people > 0 and 2 * sum(votes[:n_people]) > n_people
        maj += 2 * sum(votes) > n
        sp += surprisingly_popular(votes, preds) == 1
        thr += share > world0
        mid += share > midpoint
    return {'majority': maj / trials, 'surprisingly_popular': sp / trials, 'threshold': thr / trials,
            'people': ppl / trials, 'midpoint': mid / trials}


def _limit_check(agent_yes: float, rho: float, people_ratio: float, informed: float) -> None:
    if not 0.0 < rho < 1.0:
        raise ValueError('rho must lie in (0, 1), got %r' % rho)
    if not 0.0 < agent_yes < 1.0:
        raise ValueError('agent_yes must lie in (0, 1), got %r' % agent_yes)
    if people_ratio < 0.0 or not 0.0 <= informed <= 1.0:
        raise ValueError('need people_ratio >= 0 and informed in [0, 1], got %r, %r' % (people_ratio, informed))


def dilution_limit(agent_yes: float, rho: float, people_ratio: float, informed: float) -> tuple[float, float]:
    """The large-panel limit of the threshold rule of panel_run: (A+, A-), adoption of the successor when it is
    better and when it is worse, as the numbers of agents and people grow with people_ratio people per agent. Agents
    answer 1 with probability agent_yes in either world, errors correlated at rho in (0, 1) by the one-factor model,
    and carry no information about the local fact; a share `informed` of the people answer the truth and the rest
    answer independently of it; the rule adopts when the panel's share answering 1 exceeds the share the incumbent
    world predicts. Given the shared factor g the agents' share tends to a(g) = Phi((sqrt(rho) g + Phi^-1(agent_yes))
    / sqrt(1 - rho)) and the people's share to its mean, so the rule adopts in world w exactly when a(g) exceeds
    c_w = agent_yes - people_ratio * informed * w, which has probability Phi((Phi^-1(agent_yes) - sqrt(1 - rho)
    Phi^-1(c_w)) / sqrt(rho)), and 1 when c_w <= 0."""
    _limit_check(agent_yes, rho, people_ratio, informed)
    tau, a, b = _N.inv_cdf(agent_yes), math.sqrt(rho), math.sqrt(1.0 - rho)

    def adopt(c):
        return 1.0 if c <= 0.0 else _N.cdf((tau - b * _N.inv_cdf(c)) / a)
    return adopt(agent_yes - people_ratio * informed), adopt(agent_yes)


def dilution_bound(agent_yes: float, rho: float, people_ratio: float, informed: float) -> float:
    """An upper bound on A+ - A- from dilution_limit, by the mean value theorem with the normal density at most
    1/sqrt(2 pi): sqrt((1 - rho) / (2 pi rho)) (Phi^-1(agent_yes) - Phi^-1(c_+)), with c_+ = agent_yes - people_ratio
    * informed, and 1 when c_+ <= 0. It shrinks as rho grows and as the informed people's weight falls."""
    _limit_check(agent_yes, rho, people_ratio, informed)
    c = agent_yes - people_ratio * informed
    if c <= 0.0:
        return 1.0
    return math.sqrt((1.0 - rho) / (2.0 * math.pi * rho)) * (_N.inv_cdf(agent_yes) - _N.inv_cdf(c))
