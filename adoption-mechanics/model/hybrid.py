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
