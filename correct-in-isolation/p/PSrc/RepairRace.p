/*
 * Part 4, a shared assumption: repairing a bound start-time cycle by deleting the webhook's
 * configuration.
 *
 * Kept from the documented behavior:
 *   - one webhook replica, whose configuration fails closed and matches its own pods;
 *   - a pod is admitted once, at creation, if the configuration is absent or a webhook pod is
 *     ready, and it is ready 90 s later whatever the configuration does after its admission;
 *   - a reconciler with self-heal re-applies the configuration 5 s after it is deleted;
 *   - the ReplicaSet retries a rejected creation on a doubling backoff, or at once when nudged.
 *
 * Abstracted:
 *   - where the ReplicaSet's backoff stands after the outage is a choice of 1, 2, 4 ... 512 s;
 *   - nodes, scheduling and image pulls are folded into the 90 s.
 *
 * Time is in seconds. The operator deletes the configuration at second 0.
 */

// Durations, in seconds.
fun Horizon(): int { return 600; }
fun ReadyAfter(): int { return 90; }
fun SelfHealAfter(): int { return 5; }
fun RetryCap(): int { return 1000; }
fun ClockListeners(): int { return 3; }

event eRegister: machine;   // a machine asks the clock for ticks
event eTick: int;           // the clock reaches this second
event eAck;                 // a machine has handled the current second
event eEnd;                 // the horizon is reached
event eReapply;             // the reconciler re-applies the webhook's configuration
event eCreate: int;         // the ReplicaSet creates the webhook's pod at this second
event eAdmitted: int;       // the API server admitted the pod at this second
event eReady: int;          // the admitted pod became ready at this second

// Advances to the next second only when every machine has acknowledged the last one, so a
// request sent at second t reaches the API server before second t + 1. Within one second the
// order of the machines' requests is left to the checker.
machine Clock {
    var listeners: seq[machine];

    start state Run {
        entry (horizon: int) {
            var m: machine;
            var k: int;
            var t: int;

            k = 0;
            while (k < ClockListeners()) {
                receive {
                    case eRegister: (who: machine) {
                        listeners += (sizeof(listeners), who);
                    }
                }
                k = k + 1;
            }

            t = 0;
            while (t <= horizon) {
                foreach (m in listeners) {
                    send m, eTick, t;
                }
                k = 0;
                while (k < sizeof(listeners)) {
                    receive {
                        case eAck: {
                            k = k + 1;
                        }
                    }
                }
                t = t + 1;
            }

            foreach (m in listeners) {
                send m, eEnd;
            }
        }
    }
}

// Admits the webhook's pod when nothing blocks it, and reports when the pod becomes ready.
machine ApiServer {
    var clock: machine;
    var configured: bool;
    var admittedAt: int;
    var readyAt: int;

    start state Serve {
        entry (c: machine) {
            clock = c;
            configured = false;
            admittedAt = -1;
            readyAt = -1;
        }

        on eReapply do {
            configured = true;
        }

        on eCreate do (t: int) {
            if (admittedAt < 0 && (!configured || (readyAt >= 0 && t >= readyAt))) {
                admittedAt = t;
                readyAt = t + ReadyAfter();
                announce eAdmitted, t;
            }
        }

        on eTick do (t: int) {
            if (readyAt >= 0 && t == readyAt) {
                announce eReady, t;
            }
            send clock, eAck;
        }

        on eEnd do {
            raise halt;
        }
    }
}

// Keeps the cluster equal to its repository: with self-heal on, it re-applies the deleted
// configuration after SelfHealAfter seconds.
machine Reconciler {
    var api: machine;
    var clock: machine;
    var selfHeal: bool;

    start state Run {
        entry (cfg: (clock: machine, api: machine, selfHeal: bool)) {
            api = cfg.api;
            clock = cfg.clock;
            selfHeal = cfg.selfHeal;
            send clock, eRegister, this;
        }

        on eTick do (t: int) {
            if (selfHeal && t == SelfHealAfter()) {
                send api, eReapply;
            }
            send clock, eAck;
        }

        on eEnd do {
            raise halt;
        }
    }
}

// Creates the webhook's pod at its next retry, then doubles the retry up to RetryCap.
machine ReplicaSet {
    var api: machine;
    var clock: machine;
    var nextTry: int;

    start state Run {
        entry (cfg: (clock: machine, api: machine, nudged: bool)) {
            var retries: seq[int];
            var r: int;

            api = cfg.api;
            clock = cfg.clock;

            // Where the doubling backoff can stand after the outage: 1, 2, 4 ... 512 s.
            r = 1;
            while (r <= 512) {
                retries += (sizeof(retries), r);
                r = r * 2;
            }

            if (cfg.nudged) {
                nextTry = 1;
            } else {
                nextTry = choose(retries);
            }
            send clock, eRegister, this;
        }

        on eTick do (t: int) {
            if (t == nextTry) {
                send api, eCreate, t;
                nextTry = nextTry * 2;
                if (nextTry > RetryCap()) {
                    nextTry = RetryCap();
                }
            }
            send clock, eAck;
        }

        on eEnd do {
            raise halt;
        }
    }
}
