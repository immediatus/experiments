"""A language model reading a long design document: how well it uses a fact depends on where the fact sits.

Measured long-context behaviour has three features this module keeps. Use of a fact falls in the middle of the
input and holds at its ends, a U-shaped curve (Liu et al. 2024). As the input approaches the model's effective
window, the advantage of the beginning fades while the advantage of the end stays (Positional Biases Shift as Inputs
Approach Context Window Limits, 2025). And the effective window is shorter than the advertised one (Hsieh et al.
2024), so `fill` is measured against the effective window.

position_recall gives the chance the model uses a fact at relative position x of a document filling `fill` of its
effective window. The shape follows those measurements; document_use and fit_recall fit it to published
accuracy-by-position curves, and the sections sweep or fit its constants. fact_detection
reads a document whole or in overlapping parts, each part read in its own call, and asks whether the decisive fact is
used: a local fact sits at one position, a relational fact needs two positions read together.
"""
import math
import random


def position_recall(x: float, fill: float, base: float = 0.9, depth: float = 0.3, width: float = 0.1,
                    primacy: float | None = None, recency: float = 1.0) -> float:
    """The chance a model uses a fact at relative position x in [0, 1] of a document filling `fill` of its effective
    window: base - depth * fill * (1 - P exp(-x / width) - exp(-(1 - x) / width)), clipped to [0, 1], where the
    primacy weight P is 1 up to half the window and falls linearly to 0 at the window (and stays 0 beyond), unless
    `primacy` gives it directly (as a fit to a measured curve does). `recency` weighs the end the same way (1: the
    end keeps its full advantage, as measured near the window limit)."""
    if primacy is None:
        primacy = 1.0 if fill <= 0.5 else max(0.0, 2.0 * (1.0 - fill))
    dip = 1.0 - primacy * math.exp(-x / width) - recency * math.exp(-(1.0 - x) / width)
    return min(1.0, max(0.0, base - depth * fill * max(0.0, dip)))


def _parts(parts: int, overlap: float) -> list[tuple[float, float]]:
    length = 1.0 if parts == 1 else min(1.0, (1.0 + overlap) / parts)
    step = 0.0 if parts == 1 else (1.0 - length) / (parts - 1)
    return [(i * step, length) for i in range(parts)]


def fact_detection(fill: float, parts: int, overlap: float, relational: bool, trials: int, seed: int,
                   **shape) -> float:
    """The chance the decisive fact of a document filling `fill` of the effective window is used, when the document is
    read in `parts` overlapping parts (1: whole), each covering (1 + overlap) / parts of it and read in its own call
    at fill times that share. A local fact sits at one uniform position; a relational fact at two, and is used only
    by a part that holds both, with the product of their recalls. A fact covered by several parts is used if any
    part uses it. shape passes base, depth and width to position_recall. Averaged over trials drawn from seed."""
    if parts < 1:
        raise ValueError('parts must be at least 1, got %r' % parts)
    rng = random.Random(seed)
    spans = _parts(parts, overlap)
    used = 0.0
    for _ in range(trials):
        xs = [rng.random()] + ([rng.random()] if relational else [])
        miss = 1.0
        for start, length in spans:
            if all(start <= x <= start + length for x in xs):
                r = 1.0
                for x in xs:
                    r *= position_recall((x - start) / length, fill * length, **shape)
                miss *= 1.0 - r
        used += 1.0 - miss
    return used / trials


def document_use(accuracy: float, closed_book: float, oracle: float) -> float:
    """The share of the gain a document gives over answering without it that a reading keeps: (accuracy -
    closed_book) / (oracle - closed_book), clipped to [0, 1]. A reading below the closed-book accuracy uses nothing;
    the oracle, handed only the right document, uses all of it."""
    return min(1.0, max(0.0, (accuracy - closed_book) / (oracle - closed_book)))


def fit_recall(xs: list[float], ys: list[float], width: float = 0.1) -> tuple[float, float, float, float, float]:
    """The base, depth, primacy and recency weights of position_recall at a full fill that fit measured use ys at
    relative positions xs best in least squares. The weights run over a grid of step 0.05 in [0, 1]; for each pair,
    base and depth are the least-squares line through the shape, held to [0, 1] and [0, 1.5]. Returns (base, depth,
    primacy, recency, root-mean-square error of the clipped curve)."""
    best = None
    n = len(xs)
    for pi in range(21):
        for ri in range(21):
            primacy, recency = pi * 0.05, ri * 0.05
            m = [max(0.0, 1.0 - primacy * math.exp(-x / width) - recency * math.exp(-(1.0 - x) / width)) for x in xs]
            mm, my = math.fsum(m) / n, math.fsum(ys) / n
            var = math.fsum((v - mm) ** 2 for v in m)
            depth = 0.0 if var == 0.0 else -math.fsum((v - mm) * (y - my) for v, y in zip(m, ys)) / var
            depth = min(1.5, max(0.0, depth))
            base = min(1.0, max(0.0, my + depth * mm))
            err = math.fsum((min(1.0, max(0.0, base - depth * v)) - y) ** 2 for v, y in zip(m, ys))
            if best is None or err < best[0] - 1e-15:
                best = (err, base, depth, primacy, recency)
    err, base, depth, primacy, recency = best
    return base, depth, primacy, recency, math.sqrt(err / n)
