"""Checks the cluster kit's verdicts (cluster/run_suite.py) on hand-built runs whose outcome is
known, in a scratch directory. Standard library only.

Run: python3 tests/test_cluster_suite.py   or   python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), p) for p in [os.path.join('..', 'cluster')]]

import json
import shutil
import tempfile
import unittest

import run_suite as rs


def write_run(name, hpa, load=None, load_args=None, duration=None):
    d = os.path.join(rs.RUNS_DIR, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'hpa.csv'), 'w', encoding='utf-8') as f:
        f.write('t,spec_replicas,ready_replicas,hpa_current,hpa_desired,metric,source\n')
        for t, spec, ready in hpa:
            f.write('%d,%d,%d,%d,%d,,\n' % (t, spec, ready, spec, spec))
    if load is not None:
        with open(os.path.join(d, 'load.csv'), 'w', encoding='utf-8') as f:
            f.write('t,first,attempts,ok,timeouts,rejects,given_up\n')
            for row in load:
                f.write(','.join(str(x) for x in row) + '\n')
    rs.write_text(os.path.join(d, 'meta.json'), json.dumps(dict(
        run=name, load_args=load_args or rs.RUNS[name].get('load') or [], duration=duration or rs.RUNS[name]['duration'], load_offset=0.0)))


def staircase(dead, orders, end=1200, start=120, n0=4):
    """hpa rows every 5 s: each (seconds after the step, spec) order becomes ready `dead` s later."""
    rows = []
    for t in range(0, end, 5):
        spec = max([n0] + [n for s, n in orders if start + s <= t])
        ready = max([n0] + [n for s, n in orders if start + s + dead <= t])
        rows.append((t, spec, ready))
    return rows


def load_rows(duration, bad_until, first=20):
    """One row per second; timeouts every second up to bad_until (None: never)."""
    return [(t, first, first, first if (bad_until is None or t > bad_until) else 0, 0 if (bad_until is None or t > bad_until) else first, 0, 0)
            for t in range(duration + 1)]


ORDERS_3X = [(15, 7), (30, 8), (135, 14), (150, 16)]                       # T19, 3x
ORDERS_5X = [(15, 7), (30, 8), (135, 14), (150, 16), (255, 28), (270, 32)]   # T19, 5x
CASES = []


def case(name, want):
    def deco(fn):
        CASES.append((name, want, fn))
        return fn
    return deco


@case('calibrate at a 95 s dead time', 'as predicted')
def _():
    write_run('p1-3x', staircase(95, ORDERS_3X))
    write_run('p1-5x', staircase(95, ORDERS_5X))
    return rs.verdict('calibrate')


@case('calibrate: a pod never becomes ready', 'incomplete')
def _():
    write_run('p1-3x', staircase(5000, ORDERS_3X))
    write_run('p1-5x', staircase(5000, ORDERS_5X))
    return rs.verdict('calibrate')


@case('calibrate at a 130 s dead time', 'not as predicted')
def _():
    write_run('p1-3x', staircase(130, ORDERS_3X))
    write_run('p1-5x', staircase(130, ORDERS_5X))
    return rs.verdict('calibrate')


@case('P1-F1 identical first orders', 'as predicted')
def _():
    write_run('p1-3x', staircase(90, ORDERS_3X))
    write_run('p1-5x', staircase(90, ORDERS_5X))
    return rs.verdict('P1-F1')


@case('P1-F1 the 5x run orders more at once', 'REFUTED')
def _():
    write_run('p1-3x', staircase(90, ORDERS_3X))
    write_run('p1-5x', staircase(90, [(15, 12)] + ORDERS_5X[2:]))
    return rs.verdict('P1-F1')


@case('P1-F2 one round apart', 'as predicted')
def _():
    write_run('p1-3x', staircase(90, ORDERS_3X))
    write_run('p1-5x', staircase(90, ORDERS_5X))
    return rs.verdict('P1-F2')


@case('P1-F4 controller scales at 93%', 'REFUTED')
def _():
    write_run('p1-hot', staircase(90, [(15, 6)]))
    return rs.verdict('P1-F4')


@case('P2-F1 hunts at 60 s, rests at 150 s', 'as predicted')
def _():
    write_run('q-60-300', [(t, 35 if (t // 600) % 2 else 6, 0) for t in range(0, 18000, 5)])
    write_run('q-150-300', [(t, 20 + (t // 5) % 2, 0) for t in range(0, 18000, 5)])
    return rs.verdict('P2-F1')


@case('P2-F1 rests at 60 s', 'REFUTED')
def _():
    write_run('q-60-300', [(t, 20, 0) for t in range(0, 18000, 5)])
    return rs.verdict('P2-F1')


@case('P3-F2 30% recovers, 40% stuck', 'as predicted')
def _():
    write_run('p3-spike-30', [(0, 4, 4)], load_rows(13500, 420 + 9800))
    write_run('p3-spike-40', [(0, 4, 4)], load_rows(7200, 7200))
    return rs.verdict('P3-F2')


@case('P3-F2 40% recovers', 'REFUTED')
def _():
    write_run('p3-spike-40', [(0, 4, 4)], load_rows(7200, 3000))
    return rs.verdict('P3-F2')


@case('P3-F4 pair recovers and holds 4 when flat', 'as predicted')
def _():
    write_run('p3-pair', [(t, 50 if t < 600 else 20, 0) for t in range(0, 7320, 5)], load_rows(7320, 390))
    write_run('p3-pair-flat', [(t, 4, 4) for t in range(0, 3600, 5)], load_rows(3600, None))
    return rs.verdict('P3-F4')


@case('P4-F2 ceiling floor and one over the margin', 'as predicted')
def _():
    write_run('p4-ceil-6', [(0, 6, 6)], load_rows(7200, 7200))
    write_run('p4-ceil-7', [(0, 7, 7)], load_rows(9600, 420 + 6974))
    write_run('p4-ceil-12', [(0, 12, 12)], load_rows(3600, 420 + 1085))
    return rs.verdict('P4-F2')


@case('P4-F2 ceiling of 6 recovers', 'REFUTED')
def _():
    write_run('p4-ceil-6', [(0, 6, 6)], load_rows(7200, 3000))
    return rs.verdict('P4-F2')


class VerdictCases(unittest.TestCase):
    """The cases run in order in one scratch directory: later cases reuse runs earlier ones wrote."""

    def test_verdicts(self):
        tmp = tempfile.mkdtemp()
        saved, rs.RUNS_DIR = rs.RUNS_DIR, tmp
        try:
            for name, want, fn in CASES:
                with self.subTest(name):
                    got, detail = fn()
                    self.assertEqual(got, want, detail)
        finally:
            rs.RUNS_DIR = saved
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
