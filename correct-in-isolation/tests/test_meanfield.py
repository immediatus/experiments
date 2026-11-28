"""Checks the mean-field reading of Part 3's storm onset. In a saturated storm every attempt is rejected
with probability p; a re-watch is answered 410 when its run of rejections outlasts the history, which takes
n* rejections on the client's backoff schedule; saturation needs phi B equal to the mean cycle. The
self-consistent equation has solutions only above a fold, a saddle-node, and the fold moves with the
backoff state the clients start their runs in: history the queue does not show. A cost switched down
after a storm has started shows that this memory does not outlive a watch cycle: no hysteresis.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import backoff_schedule, gone_after, meanfield_onset, saturated_storm_possible
from relist import simulate_limited


class Schedule(unittest.TestCase):
    """Fresh schedule doubles from init and resets; raised schedule starts at cap; gone after agrees with the bound
    for a capped client; fresh client needs more than a raised one."""

    def test_fresh_schedule_doubles_from_init_and_resets(self):
        b = backoff_schedule(raised=False, jitter=1.0, length=8)
        self.assertAlmostEqual(b[0], 0.8)
        self.assertAlmostEqual(b[1], 1.6)
        self.assertLessEqual(max(b), 30.0)

    def test_raised_schedule_starts_at_cap(self):
        self.assertAlmostEqual(backoff_schedule(raised=True, jitter=1.0, length=3)[0], 30.0)

    def test_gone_after_agrees_with_the_bound_for_a_capped_client(self):
        # Proposition 20: at least 4 rejections whatever the state; a backoff held at its cap, never reset,
        # at the largest jitter needs exactly that; with the documented two-minute reset a raised run needs more
        self.assertEqual(gone_after(backoff_schedule(raised=True, jitter=2.0, length=40, reset=1e9)), 4)
        self.assertGreaterEqual(gone_after(backoff_schedule(raised=True, jitter=2.0, length=40)), 4)

    def test_fresh_client_needs_more_than_a_raised_one(self):
        fresh = gone_after(backoff_schedule(raised=False, jitter=1.5, length=40))
        raised = gone_after(backoff_schedule(raised=True, jitter=1.5, length=40))
        self.assertGreater(fresh, raised)


class Onset(unittest.TestCase):
    """Fold exists and lies above the necessary bound; fresh fold is near the simulated onset; admitted wait raises
    the fold toward the simulated onset; admitted wait enters the re watch and the list; raised backoff lowers the
    fold."""

    def test_fold_exists_and_lies_above_the_necessary_bound(self):
        b, cost, p, n = meanfield_onset(raised=False)
        self.assertTrue(saturated_storm_possible(cost, 2000, 100.0, 300.0, 450.0))
        self.assertGreater(cost, 37.5)
        self.assertTrue(0.5 < p < 1.0)

    def test_fresh_fold_is_near_the_simulated_onset(self):
        cost = meanfield_onset(raised=False)[1]
        self.assertTrue(95.0 < cost < 113.0)

    def test_admitted_wait_raises_the_fold_toward_the_simulated_onset(self):
        base = meanfield_onset()[1]
        full = meanfield_onset(admitted_wait=15.0)[1]
        self.assertGreater(full, base)
        self.assertLess(full, 113.0)
        self.assertAlmostEqual(full, 110.37, places=2)

    def test_admitted_wait_enters_the_re_watch_and_the_list(self):
        # the wait adds a (1 + phi) / phi to the backlog at every p, so the fold moves by at least the
        # addition at the new fold and at most the addition at the old one
        b0, _, p0, n = meanfield_onset(admitted_wait=0.0)
        b1, _, p1, _ = meanfield_onset(admitted_wait=10.0)
        self.assertGreaterEqual(b1 - b0, 10.0 * (1 + p1 ** n) / p1 ** n - 1e-6)
        self.assertLessEqual(b1 - b0, 10.0 * (1 + p0 ** n) / p0 ** n + 1e-6)

    def test_raised_backoff_lowers_the_fold(self):
        self.assertLess(meanfield_onset(raised=True)[1], meanfield_onset(raised=False)[1])


class Hysteresis(unittest.TestCase):
    """Cost switch keeps the plain run when unused; no hysteresis below the onset; storm entered above onset runs at
    the onset."""

    def test_cost_switch_keeps_the_plain_run_when_unused(self):
        self.assertEqual(simulate_limited(100.0, hours=2, seed=1)[0],
                         simulate_limited(100.0, hours=2, seed=1, cost_switch=None)[0])

    def test_no_hysteresis_below_the_onset(self):
        # the backoff resets two minutes after its last reset, faster than a watch cycle, so a storm entered
        # at 116 and lowered to 110 ends as a cold trigger at 110 does: the memory does not outlive a cycle
        cold = simulate_limited(110.0, hours=8, seed=1)[0]
        warm = simulate_limited(116.0, hours=8, seed=1, cost_switch=(3600.0, 110.0))[0]
        self.assertEqual(cold[-1], 0)
        self.assertEqual(warm[-1], 0)

    def test_storm_entered_above_onset_runs_at_the_onset(self):
        self.assertGreater(simulate_limited(116.0, hours=8, seed=1, cost_switch=(3600.0, 113.0))[0][-1], 0)


if __name__ == '__main__':
    unittest.main()
