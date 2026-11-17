/*
 * A re-watch is answered 410 only after a run of consecutive rejections at least as long as its
 * starting backoff state requires: 11 from a fresh backoff, 8 from a raised one (Proposition 20
 * with the history statistic).
 *
 * The fresh bound is 11, not the 13 the largest jitter throughout gives: a shorter delay early
 * postpones the two-minute reset and lets the capped delays run longer. This checker found it.
 *
 * RunBeforeGoneTight asks for one rejection more, so the checker must find a 410 at exactly the
 * bound: the bound is reached, not only respected.
 */

fun FreshBound(): int { return 11; }
fun RaisedBound(): int { return 8; }

spec RunBeforeGone observes eRunStart, eGone {
    var need: int;

    start state Watch {
        on eRunStart do (raised: bool) {
            if (raised) {
                need = RaisedBound();
            } else {
                need = FreshBound();
            }
        }

        on eGone do (run: int) {
            assert run >= need,
                format("410 after {0} rejections, fewer than {1}", run, need);
        }
    }
}

spec RunBeforeGoneTight observes eRunStart, eGone {
    var need: int;

    start state Watch {
        on eRunStart do (raised: bool) {
            if (raised) {
                need = RaisedBound() + 1;
            } else {
                need = FreshBound() + 1;
            }
        }

        on eGone do (run: int) {
            assert run >= need, format("410 after {0} rejections", run);
        }
    }
}
