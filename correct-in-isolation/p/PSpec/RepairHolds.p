/*
 * The repair holds when the webhook's pod is admitted before the horizon. Readiness is not an
 * admission: a pod admitted before the configuration comes back still becomes ready after it,
 * so admission alone decides the race.
 */

spec RepairHolds observes eAdmitted, eEnd {
    var admitted: bool;

    start state Watch {
        entry {
            admitted = false;
        }

        on eAdmitted do (t: int) {
            admitted = true;
        }

        on eEnd do {
            assert admitted, format("{0}{1}",
                "the webhook's pod was never admitted: ",
                "the reconciler re-applied the configuration first");
        }
    }
}
