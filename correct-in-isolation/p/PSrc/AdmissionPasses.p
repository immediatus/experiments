/*
 * Part 5, a shared order: a label webhook and an injector that the label selects, both opted in
 * to reinvocation, run in an order the checker chooses.
 *
 * Kept from the documented contract and the current implementation:
 *   - a first pass over every webhook whose selector matches the object as it stands at its turn;
 *   - a second pass that calls a webhook only if the first pass called it and the object changed
 *     after that call.
 *
 * Abstracted:
 *   - the pod is two facts, the label and the sidecar;
 *   - the dispatcher calls webhooks one at a time and waits for each reply, as the API server does.
 *
 * Which webhooks the first pass called is the seam's history statistic.
 */

type tPod = (label: bool, sidecar: bool);
type tRequest = (pod: tPod, from: machine);
type tCall = (who: int, pass: int);

// Webhook ids.
fun LabelId(): int { return 0; }
fun InjectorId(): int { return 1; }

event eInvoke: tRequest;    // the dispatcher calls a webhook with the pod
event eReply: tPod;         // the webhook returns the pod, possibly changed
event eCalled: tCall;       // a webhook was called in a pass
event eSkipped: tCall;      // a webhook's selector did not match in a pass
event eAdmittedPod: tPod;   // admission ended with this pod

// Sets the label that selects the injector.
machine LabelWebhook {
    start state Serve {
        on eInvoke do (req: tRequest) {
            send req.from, eReply, (label = true, sidecar = req.pod.sidecar);
        }
    }
}

// Adds the sidecar. Its selector matches only a pod that carries the label.
machine Injector {
    start state Serve {
        on eInvoke do (req: tRequest) {
            send req.from, eReply, (label = req.pod.label, sidecar = true);
        }
    }
}

// Runs the two passes of admission over the webhooks, in an order the checker chooses.
machine Dispatcher {
    var hooks: seq[machine];
    var ids: seq[int];
    var pod: tPod;
    var version: int;               // how many times the pod has changed
    var called: map[int, bool];     // whether the first pass called the webhook
    var calledAt: map[int, int];    // the pod's version after the webhook's last call

    start state Admit {
        entry {
            var label: machine;
            var injector: machine;
            var i: int;
            var who: int;

            label = new LabelWebhook();
            injector = new Injector();
            if ($) {
                Order(label, LabelId(), injector, InjectorId());
            } else {
                Order(injector, InjectorId(), label, LabelId());
            }

            pod = (label = false, sidecar = false);
            version = 0;

            // First pass: a webhook is called if its selector matches the pod at its turn.
            i = 0;
            while (i < sizeof(hooks)) {
                who = ids[i];
                called[who] = false;
                if (who == LabelId() || pod.label) {
                    Call(i, 1);
                } else {
                    announce eSkipped, (who = who, pass = 1);
                }
                i = i + 1;
            }

            // Second pass: only webhooks the first pass called, and only if the pod changed since.
            i = 0;
            while (i < sizeof(hooks)) {
                who = ids[i];
                if (called[who] && version > calledAt[who]) {
                    Call(i, 2);
                }
                i = i + 1;
            }

            announce eAdmittedPod, pod;
        }
    }

    fun Order(first: machine, firstId: int, second: machine, secondId: int) {
        hooks += (0, first);
        ids += (0, firstId);
        hooks += (1, second);
        ids += (1, secondId);
    }

    fun Call(i: int, pass: int) {
        var before: tPod;

        before = pod;
        send hooks[i], eInvoke, (pod = pod, from = this);
        receive {
            case eReply: (p: tPod) {
                pod = p;
            }
        }
        if (pod != before) {
            version = version + 1;
        }
        called[ids[i]] = true;
        calledAt[ids[i]] = version;
        announce eCalled, (who = ids[i], pass = pass);
    }
}
