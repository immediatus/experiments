/*
 * NoFirstCallOnSecondPass: a webhook its selector skipped in the first pass is never called in
 * the second (the mechanism of Proposition 30).
 *
 * FixedPoint: the admitted pod is one every webhook that matches it would leave unchanged. A pod
 * with the label and no sidecar is not: the injector matches it and would add the sidecar.
 */

spec NoFirstCallOnSecondPass observes eCalled, eSkipped {
    var skipped: set[int];

    start state Watch {
        on eSkipped do (e: tCall) {
            skipped += (e.who);
        }

        on eCalled do (e: tCall) {
            assert !(e.pass == 2 && e.who in skipped),
                format("webhook {0} called in the second pass after a skip", e.who);
        }
    }
}

spec FixedPoint observes eAdmittedPod {
    start state Watch {
        on eAdmittedPod do (p: tPod) {
            assert !(p.label && !p.sidecar), "admitted with the injector's label and no sidecar";
        }
    }
}
