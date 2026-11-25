"""The human energy budget of a review: how many disagreements people must settle, and what that buys.

A design is reviewed as `pieces` pieces, as in Part 1's law of triviality. Each of `reviewers` holds an opinion on a
piece with chance min(0.95, share_whole * pieces ** steepness). Settling one disagreement takes one owner an
exponential time of mean mean_settle, one at a time, and the review must settle all of them within `window`
(settle_in_time). Human energy is the number of settlements, and the owner-time they take.

Three ways to run the review:

- 'meeting', Part 1's mesh: every pair of holders of a piece settles its disagreement, h(h - 1)/2 settlements for h
  holders, and every holder's objection is a veto. This reproduces Part 1's triviality exactly.
- 'residual', a star: the machines' consensus is a reference recorded after the people judge alone. A holder who
  agrees with it costs nothing; each holder who departs from it is one settlement, against the reference. A disputed
  piece is resolved to the truth with chance `verify` (people checking against the design and the running system).
- 'machine', the reference heard first: every holder follows it, no human energy is spent, and the reference decides.
- 'protocol', the Residual Protocol: the machines settle what they can and list each piece they cannot, with
  chance `lists` whatever the piece hides (their uncertainty does not see a blind spot); a listed piece is reviewed
  as in 'residual' by `route` holders (or by Part 1's opinion holders when route is None); an unlisted piece is
  closed by the reference, unless it hides the flaw and a holder of the fact adds it, with chance `adds`.

A worse design has one flawed piece, a local fact. A holder of it catches the flaw with chance `catch` (and otherwise
judges it as a fine piece); the machines see it with chance `machine_catch` (0: the fact is in no training text).
Everything is computed exactly, by summing over the binomial holder counts and convolving the settlement counts
across pieces, so that the shared window is evaluated on the exact total.
"""
import math

from pipeline import settle_in_time

PROTOCOLS = ('meeting', 'residual', 'machine', 'protocol')
SHARE_CAP = 0.95   # the most of the reviewers who hold an opinion on a piece, as in Part 1's triviality


def expected_settlements(n: int, share: float, depart: float | None = None) -> float:
    """The expected settlements one piece costs when each of n people holds an opinion on it with chance `share`:
    the mesh's C(n, 2) share^2 when every pair of holders settles (depart None), or the star's n share depart when
    only holders who depart from a reference, each with chance `depart`, settle once against it."""
    if depart is None:
        return n * (n - 1) / 2.0 * share * share
    return n * share * depart


def _binom(n: int, k: int, p: float) -> float:
    return math.comb(n, k) * p ** k * (1.0 - p) ** (n - k)


def _holders(n: int, share: float, route: int | None) -> list[tuple[int, float]]:
    """The number of people judging a piece: binomial over the n reviewers, or exactly `route` routed holders."""
    if route is not None:
        return [(route, 1.0)]
    return [(h, _binom(n, h, share)) for h in range(n + 1)]


def _piece(protocol: str, flawed: bool, n: int, share: float, accept: float, catch: float, verify: float,
           machine_catch: float, route: int | None = None, lists: float = 1.0,
           adds: float = 0.0) -> list[tuple[int, float, float]]:
    """The outcomes of one piece as (settlements, probability, chance the piece is accepted) triples."""
    out = []
    if protocol == 'machine':
        return [(0, 1.0, 1.0 - machine_catch if flawed else 1.0)]
    if protocol == 'protocol':
        reviewed = lists + ((1.0 - lists) * adds if flawed else 0.0)
        if reviewed:
            out = [(k, p * reviewed, a) for k, p, a in _piece('residual', flawed, n, share, accept, catch, verify,
                                                              machine_catch, route)]
        if reviewed < 1.0:
            out.append((0, 1.0 - reviewed, 1.0 - machine_catch if flawed else 1.0))
        return out
    says_no = catch + (1.0 - catch) * (1.0 - accept) if flawed else 1.0 - accept
    for h, ph in _holders(n, share, route):
        if protocol == 'meeting':
            out.append((h * (h - 1) // 2, ph, (1.0 - says_no) ** h))
            continue
        for o in range(h + 1):
            po = ph * _binom(h, o, says_no)
            if not flawed:
                out.append((o, po, 1.0 if o == 0 else verify))
                continue
            # the reference says the flawed piece is fine (it misses the local fact) or flawed (it sees it)
            out.append((o, po * (1.0 - machine_catch), 1.0 if o == 0 else 1.0 - verify))
            out.append((h - o, po * machine_catch, 0.0 if o == h else 1.0 - verify))
    return out


def _convolve(dist: dict[int, float], piece: list[tuple[int, float, float]], weighted: bool) -> dict[int, float]:
    out: dict[int, float] = {}
    for k, w in dist.items():
        for kk, p, acc in piece:
            m = p * (acc if weighted else 1.0)
            if m:
                out[k + kk] = out.get(k + kk, 0.0) + w * m
    return out


def review_energy(pieces: int, protocol: str, better: bool, reviewers: int = 15, share_whole: float = 0.2,
                  steepness: float = 0.75, accept: float = 0.9, window: float = 13.0, mean_settle: float = 0.25,
                  catch: float = 0.4, verify: float = 0.9, machine_catch: float = 0.0, route: int | None = None,
                  lists: float = 1.0, adds: float = 0.0) -> dict[str, float]:
    """The review of a better design (better True) or a worse one with one flawed piece, under `protocol`
    ('meeting', 'residual' or 'machine'). Returns exact values: 'adopted', the chance the review decides in time and
    accepts every piece; 'in_time', the chance it settles every disagreement within the window; 'settlements', the
    expected number of settlements, the human energy; 'weeks', the owner-time they take, settlements * mean_settle.
    Defaults are Part 1's triviality constants, Part 2's informed share (catch) and Part 3's verified share (verify).
    route, lists and adds shape 'protocol' (route also routes 'meeting' and 'residual'): see the module notes."""
    if protocol not in PROTOCOLS:
        raise ValueError('protocol must be one of %s, got %r' % (', '.join(PROTOCOLS), protocol))
    if not (0.0 <= lists <= 1.0 and 0.0 <= adds <= 1.0):
        raise ValueError('lists and adds must lie in [0, 1], got %r and %r' % (lists, adds))
    if route is not None and not 1 <= route <= reviewers:
        raise ValueError('route must be between 1 and the reviewers, got %r' % route)
    share = min(SHARE_CAP, share_whole * pieces ** steepness)
    kinds = [False] * pieces if better else [False] * (pieces - 1) + [True]
    outcomes = [_piece(protocol, f, reviewers, share, accept, catch, verify, machine_catch, route, lists, adds)
                for f in kinds]
    adopted_by, timed_by = {0: 1.0}, {0: 1.0}
    for piece in outcomes:
        adopted_by = _convolve(adopted_by, piece, True)
        timed_by = _convolve(timed_by, piece, False)
    adopted = math.fsum(w * settle_in_time(k, window, mean_settle) for k, w in adopted_by.items())
    in_time = math.fsum(w * settle_in_time(k, window, mean_settle) for k, w in timed_by.items())
    settlements = math.fsum(k * p for piece in outcomes for k, p, _ in piece)
    return {'adopted': adopted, 'in_time': in_time, 'settlements': settlements, 'weeks': settlements * mean_settle}
