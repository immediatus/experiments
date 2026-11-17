/*
 * Part 3, a shared state: one Reflector client re-watching through a queue with a wait limit.
 *
 * Kept from the documented behavior:
 *   - the queue's wait limit, 15 s, and the retained history, 300 s;
 *   - the Reflector's backoff: 0.8 s, doubling to a cap of 30 s, reset to 0.8 s once more than
 *     120 s have passed since its last reset, and jittered to one or two times its base.
 *
 * Abstracted:
 *   - the server becomes a choice of how many times in a row it turns the client away, which
 *     covers any server;
 *   - the jitter is explored at its two extremes, and the served attempt's wait at 0 and at the
 *     full limit (a grid over the jitter gives the same fewest runs; see ../README.md).
 *
 * Time is local to the client, in tenths of a second. The client starts its run fresh, or
 * raised: at the cap, as a client whose last run ended moments ago. That starting state is the
 * seam's history statistic.
 */

// Durations, in tenths of a second.
fun WaitLimit(): int { return 150; }
fun History(): int { return 3000; }
fun BackoffInit(): int { return 8; }
fun BackoffCap(): int { return 300; }
fun BackoffReset(): int { return 1200; }

event eAttempt: machine;    // a client asks to be served
event eRejected;            // the queue turned the attempt away (429)
event eServed: int;         // the attempt was served, after this long in the queue
event eRunStart: bool;      // a run begins; true when the client's backoff starts raised
event eGone: int;           // the re-watch was answered 410, after this many rejections
event eResumed: int;        // the re-watch resumed, after this many rejections

// Turns a client away a chosen number of times in a row, then serves it.
machine Queue {
    var rejectionsLeft: int;

    start state Serve {
        entry (rejections: int) {
            rejectionsLeft = rejections;
        }

        on eAttempt do (client: machine) {
            if (rejectionsLeft > 0) {
                rejectionsLeft = rejectionsLeft - 1;
                send client, eRejected;
            } else if ($) {
                send client, eServed, 0;
            } else {
                send client, eServed, WaitLimit();
            }
        }
    }
}

// One informer's Reflector, retrying a re-watch on its documented backoff.
machine Reflector {
    var queue: machine;
    var now: int;
    var lastReset: int;
    var delay: int;
    var run: int;

    start state Init {
        entry (cfg: (queue: machine, raised: bool)) {
            queue = cfg.queue;
            now = 0;
            lastReset = 0;
            run = 0;
            if (cfg.raised) {
                delay = BackoffCap();
            } else {
                delay = BackoffInit();
            }
            announce eRunStart, cfg.raised;
            send queue, eAttempt, this;
            goto Trying;
        }
    }

    state Trying {
        on eRejected do {
            var jitter: int;

            run = run + 1;
            now = now + WaitLimit();
            if (now - lastReset > BackoffReset()) {
                delay = BackoffInit();
                lastReset = now;
            }
            jitter = 1;
            if ($) {
                jitter = 2;
            }
            now = now + delay * jitter;
            delay = delay * 2;
            if (delay > BackoffCap()) {
                delay = BackoffCap();
            }
            send queue, eAttempt, this;
        }

        on eServed do (wait: int) {
            if (now + wait > History()) {
                announce eGone, run;
            } else {
                announce eResumed, run;
            }
            raise halt;
        }
    }
}
