"""The write-back loop: what an organization learns from the reasons it records.

After each decision the organization records a stated reason. With probability-weight phi the reason tracks
the true driver; with weight 1 - phi it is a story with its own bias (a post-mortem's polite narrative, or an
unfaithful chain of thought). Each observation is phi * (driver + e1) + (1 - phi) * (story_bias + e2), with e1
and e2 normal with deviation `noise`. A naive learner averages the observations as if they were the driver
(misspecified learning, Esponda and Pouzo 2016) and converges to phi * driver + (1 - phi) * story_bias. A
calibrated learner removes the story's contribution, which needs story_bias to be known.
"""
import random


def naive_limit(phi: float, true_driver: float, story_bias: float) -> float:
    """Where naive learning converges: phi * true_driver + (1 - phi) * story_bias."""
    return phi * true_driver + (1.0 - phi) * story_bias


def learn(episodes: int, phi: float, true_driver: float, story_bias: float | None, noise: float,
          naive: bool, seed: int) -> float:
    """The organization's belief about the driver after `episodes` recorded reasons. Inputs: faithfulness phi
    in (0, 1], the true driver, the stories' bias (needed when naive is False), observation noise, the
    learning mode and a seed. The belief is the running mean of the (debiased, when calibrated) observations."""
    if not naive and story_bias is None:
        raise ValueError('calibrated learning needs the stories\' bias to be known')
    if not 0.0 < phi <= 1.0:
        raise ValueError('phi must lie in (0, 1], got %r' % phi)
    bias = 0.0 if story_bias is None else story_bias
    rng = random.Random(seed)
    total = 0.0
    for _ in range(episodes):
        obs = phi * (true_driver + rng.gauss(0.0, noise)) + (1.0 - phi) * (bias + rng.gauss(0.0, noise))
        total += obs if naive else (obs - (1.0 - phi) * bias) / phi
    return total / episodes


def reason_moments(phi: float, true_driver: float, story_bias: float, noise: float) -> tuple[float, float]:
    """Mean and standard deviation of one recorded reason: phi * (driver + e1) + (1 - phi) * (bias + e2). Reasons
    are normal with these two moments, so any (phi, driver, bias, noise) with the same two moments produces the
    same records: the driver is not identified from reasons alone."""
    return (phi * true_driver + (1.0 - phi) * story_bias,
            noise * (phi * phi + (1.0 - phi) * (1.0 - phi)) ** 0.5)
