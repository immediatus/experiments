"""Part 6: whole-system tests on incomplete descriptions. Each function drops part of a description at random,
as an inventory that missed it would, so that a test's verdict on the part can be set against its verdict on
the whole."""
from __future__ import annotations

import random
from typing import Hashable

from interaction import signal_set_passes

Needs = dict[Hashable, set]  # component -> the components it needs to start
Facts = dict[str, tuple[str, set]]  # fact -> (the webhook that writes it, the facts it needs)


def omit_needs(needs: Needs, share: float, rng: random.Random) -> Needs:
    """The start-time graph with each need dropped independently with probability share, drawn in sorted
    order so that the result does not depend on how Python hashes the names."""
    return {i: {j for j in sorted(needs[i], key=str) if rng.random() >= share} for i in sorted(needs, key=str)}


def omit_prereqs(facts: Facts, share: float, rng: random.Random) -> Facts:
    """The facts with each prerequisite dropped independently with probability share: a webhook whose reads
    were listed incompletely."""
    return {f: (w, {g for g in sorted(pre) if rng.random() >= share}) for f, (w, pre) in sorted(facts.items())}


def random_facts(webhooks: int, rng: random.Random, most: int = 8, link: float = 0.35) -> tuple[list[str], Facts]:
    """Webhooks w0.. and between their count and `most` facts, each written by a random webhook and needing
    each earlier fact with probability `link`, the draws of Proposition 37's check."""
    writers = ['w%d' % i for i in range(webhooks)]
    facts = {}
    for f in range(rng.randint(webhooks, most)):
        facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in range(f) if rng.random() < link})
    return writers, facts


def signal_flips(loops: int, draws: int, rng: random.Random, span: float = 0.8) -> dict[str, int]:
    """Random gain matrices with unit self-gains and couplings uniform in [-span, span]; in each, one coupling
    chosen at random is set to zero, a coupling nobody measured. Counts the whole-system verdicts it moves:
    {'fails', 'fail_to_pass', 'fail_kept', 'pass_to_fail', 'pass_kept'}."""
    out = {'fails': 0, 'fail_to_pass': 0, 'fail_kept': 0, 'pass_to_fail': 0, 'pass_kept': 0}
    every = list(range(loops))
    for _ in range(draws):
        g = [[1.0 if i == j else rng.uniform(-span, span) for j in every] for i in every]
        i, j = rng.choice([(a, b) for a in every for b in every if a != b])
        h = [row[:] for row in g]
        h[i][j] = 0.0
        before, after = signal_set_passes(g, every), signal_set_passes(h, every)
        if not before:
            out['fails'] += 1
            out['fail_to_pass' if after else 'fail_kept'] += 1
        else:
            out['pass_to_fail' if not after else 'pass_kept'] += 1
    return out
