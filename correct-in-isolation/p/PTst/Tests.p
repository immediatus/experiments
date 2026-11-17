/*
 * Test drivers and test cases. Each test case checks one property against one configuration;
 * p/run.py runs them all and p/expected.txt holds their frozen verdicts.
 */

// Part 3: the queue turns the client away 0 to 20 times in a row.
fun MostRejections(): int { return 20; }

machine BackoffFresh {
    start state Init {
        entry {
            var queue: machine;

            queue = new Queue(choose(MostRejections() + 1));
            new Reflector((queue = queue, raised = false));
        }
    }
}

machine BackoffRaised {
    start state Init {
        entry {
            var queue: machine;

            queue = new Queue(choose(MostRejections() + 1));
            new Reflector((queue = queue, raised = true));
        }
    }
}

// Part 4: the repair race, with the reconciler's self-heal on or off and the ReplicaSet nudged
// or left on its backoff.
machine RepairDriver {
    start state Init {
        entry (cfg: (selfHeal: bool, nudged: bool)) {
            var clock: machine;
            var api: machine;

            clock = new Clock(Horizon());
            api = new ApiServer(clock);
            send clock, eRegister, api;
            new Reconciler((clock = clock, api = api, selfHeal = cfg.selfHeal));
            new ReplicaSet((clock = clock, api = api, nudged = cfg.nudged));
        }
    }
}

machine RepairSelfHeal {
    start state Init {
        entry {
            new RepairDriver((selfHeal = true, nudged = false));
        }
    }
}

machine RepairPaused {
    start state Init {
        entry {
            new RepairDriver((selfHeal = false, nudged = false));
        }
    }
}

machine RepairNudged {
    start state Init {
        entry {
            new RepairDriver((selfHeal = true, nudged = true));
        }
    }
}

// Part 5: one admission of one pod.
machine AdmissionDriver {
    start state Init {
        entry {
            new Dispatcher();
        }
    }
}

test tcBackoffFresh [main = BackoffFresh]:
    assert RunBeforeGone in { Queue, Reflector, BackoffFresh };

test tcBackoffFreshTight [main = BackoffFresh]:
    assert RunBeforeGoneTight in { Queue, Reflector, BackoffFresh };

test tcBackoffRaised [main = BackoffRaised]:
    assert RunBeforeGone in { Queue, Reflector, BackoffRaised };

test tcBackoffRaisedTight [main = BackoffRaised]:
    assert RunBeforeGoneTight in { Queue, Reflector, BackoffRaised };

test tcRepairSelfHeal [main = RepairSelfHeal]:
    assert RepairHolds in {
        Clock, ApiServer, Reconciler, ReplicaSet, RepairDriver, RepairSelfHeal
    };

test tcRepairPaused [main = RepairPaused]:
    assert RepairHolds in {
        Clock, ApiServer, Reconciler, ReplicaSet, RepairDriver, RepairPaused
    };

test tcRepairNudged [main = RepairNudged]:
    assert RepairHolds in {
        Clock, ApiServer, Reconciler, ReplicaSet, RepairDriver, RepairNudged
    };

test tcAdmissionNoFirstCall [main = AdmissionDriver]:
    assert NoFirstCallOnSecondPass in { Dispatcher, LabelWebhook, Injector, AdmissionDriver };

test tcAdmissionFixedPoint [main = AdmissionDriver]:
    assert FixedPoint in { Dispatcher, LabelWebhook, Injector, AdmissionDriver };
