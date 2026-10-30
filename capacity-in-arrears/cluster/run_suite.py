"""Runs the falsification criteria of Capacity in Arrears on a kind cluster, one run at a time,
and judges each criterion against its frozen prediction. Standard library only.

  python3 run_suite.py list                         # criteria, their runs and run times
  python3 run_suite.py run calibrate --node $NODE   # measure the dead time first
  python3 run_suite.py run P1-F2 --node $NODE       # every run a criterion needs, then its verdict
  python3 run_suite.py all --node $NODE             # calibration, then every criterion in order
  python3 run_suite.py verdict P1-F2                # judge saved runs again, without running

Set up the cluster as the header of kit.py describes (kind with maxPods 250,
metrics-server, KEDA 2.19), then export NODE, the kind node's address. Runs never overlap:
they share one node, and overlapping runs would distort each other's CPU and start times.
Each run is applied fresh and torn down after, and writes runs/<run>/ with exp.yaml,
hpa.csv (the recorder), load.csv (the load generator, if any) and meta.json. Every run
gets its own namespace, cia-<run>, which is deleted and waited out before the next run
starts, so no HPA, ScaledObject or cached metric can carry over. The load generator starts
only after the recorder has logged a live metric from the HPA.

Calibration comes first because every prediction assumes a 90 s dead time. On kind the real
dead time is the start delay plus scheduling, container start and readiness. If the measured
value is more than 15 s from 90, `all` stops: the predictions must be regenerated for the
measured dead time before any verdict means anything.

Verdicts are one of: "as predicted"; "REFUTED", when the criterion's own refutation clause
holds; "not as predicted", when the outcome differs from the prediction without meeting the
refutation clause; "incomplete", when a run is missing. A refutation is reported as such and
is never averaged away.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from statistics import fmean

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, 'kit.py')
RUNS_DIR = os.path.join(HERE, 'runs')
DEAD = 90
POD_RATE = 10.0          # requests a second one 250m pod serves at 25 ms of CPU each

# One entry per run. mode: manifests (CPU HPA), signals or queue. load: load-generator
# arguments, or None for queue runs, whose broker generates demand itself.
NO_RETRY = ['--timeout', '600', '--retries', '0']
RETRY = ['--timeout', '10', '--retries', '2']


def step(rate, k, dur, extra):
    return ['--rate', str(rate), '--spike', str(k), '--spike-start', '120', '--spike-len', str(dur), '--duration', str(dur + 120)] + extra


def spike(rate, k, total, extra):
    return ['--rate', str(rate), '--spike', str(k), '--spike-start', '120', '--spike-len', '300', '--duration', str(total)] + extra


RUNS = {
    'p1-3x':        dict(mode='manifests', kit=[], load=step(20, 3, 1200, NO_RETRY)),
    'p1-5x':        dict(mode='manifests', kit=[], load=step(20, 5, 1200, NO_RETRY)),
    'p1-limit':     dict(mode='manifests', kit=['--limit-millicores', '1000'], load=step(20, 5, 1200, NO_RETRY)),
    'p1-hot':       dict(mode='manifests', kit=['--target', '93'], load=step(20, 3, 900, NO_RETRY)),
    'q-60-300':     dict(mode='queue', kit=['--delay', '60', '--window', '300'], load=None, duration=18000),
    'q-150-300':    dict(mode='queue', kit=['--delay', '150', '--window', '300'], load=None, duration=18000),
    'q-60-60':      dict(mode='queue', kit=['--delay', '60', '--window', '60'], load=None, duration=18000),
    'q-1-300':      dict(mode='queue', kit=['--delay', '1', '--window', '300'], load=None, duration=18000),
    'q-1-0':        dict(mode='queue', kit=['--delay', '1', '--window', '0'], load=None, duration=18000),
    'p3-steady':    dict(mode='manifests', kit=['--min', '4', '--max', '4'], load=['--rate', '20', '--spike', '1', '--duration', '10800'] + RETRY),
    'p3-spike-30':  dict(mode='manifests', kit=['--min', '4', '--max', '4'], load=spike(12, 5, 13500, RETRY)),
    'p3-spike-40':  dict(mode='manifests', kit=['--min', '4', '--max', '4'], load=spike(16, 5, 7200, RETRY)),
    'p3-first':     dict(mode='signals', kit=['--signal', 'first'], load=step(20, 5, 7200, RETRY), meter=True),
    'p3-ingress':   dict(mode='signals', kit=['--signal', 'ingress'], load=step(20, 5, 7200, RETRY), meter=True),
    'p3-pair':      dict(mode='signals', kit=['--signal', 'pair'], load=step(20, 5, 7200, RETRY), meter=True),
    'p3-pair-flat': dict(mode='signals', kit=['--signal', 'pair'], load=['--rate', '20', '--spike', '1', '--duration', '3600'] + RETRY, meter=True),
    'p4-nobound':   dict(mode='manifests', kit=[], load=step(20, 5, 7200, RETRY)),
    'p4-bound-5':   dict(mode='manifests', kit=['--max-queue-s', '5'], load=step(20, 5, 7200, RETRY)),
    'p4-bound-20':  dict(mode='manifests', kit=['--max-queue-s', '20'], load=step(20, 5, 7200, RETRY)),
    'p4-ceil-6':    dict(mode='manifests', kit=['--max', '6'], load=spike(20, 5, 7200, RETRY)),
    'p4-ceil-7':    dict(mode='manifests', kit=['--max', '7'], load=spike(20, 5, 9600, RETRY)),
    'p4-ceil-12':   dict(mode='manifests', kit=['--max', '12'], load=spike(20, 5, 3600, RETRY)),
}
for _r in RUNS.values():
    _r.setdefault('meter', False)
    if _r['mode'] == 'queue':
        _r.update(deploy='consumer', hpa='keda-hpa-consumer')
    else:
        _r.update(deploy='hp', hpa='keda-hpa-hp' if _r['mode'] == 'signals' else 'hp')
        _r['duration'] = int(_r['load'][_r['load'].index('--duration') + 1])


# ---------------------------------------------------------------- reading saved runs

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def load_run(name):
    d = os.path.join(RUNS_DIR, name)
    if not os.path.exists(os.path.join(d, 'meta.json')):
        return None
    meta = read_json(os.path.join(d, 'meta.json'))
    hpa = read_csv(os.path.join(d, 'hpa.csv'))
    for r in hpa:
        r['t'] = float(r['t']) - meta.get('load_offset', 0.0)          # seconds on the load generator's clock
        for k in ('spec_replicas', 'ready_replicas'):
            r[k] = int(float(r[k] or 0))
    load = None
    if os.path.exists(os.path.join(d, 'load.csv')):
        load = [{k: int(v) for k, v in r.items()} for r in read_csv(os.path.join(d, 'load.csv'))]
    return dict(meta=meta, hpa=hpa, load=load)


def arg(run, flag, default=None):
    a = run['meta']['load_args']
    return float(a[a.index(flag) + 1]) if flag in a else default


def spec_after(run, t0):
    return [r for r in run['hpa'] if r['t'] >= t0]


def first_time(rows, cond):
    for r in rows:
        if cond(r):
            return r['t']
    return None


def distinct(seq):
    out = []
    for v in seq:
        if not out or out[-1] != v:
            out.append(v)
    return out


def last_bad(run):
    """Last second with a timeout or a rejection, and whether it is near the end of the run."""
    bad = [r['t'] for r in run['load'] if r['timeouts'] or r['rejects']]
    if not bad:
        return None, False
    return bad[-1], bad[-1] >= run['meta']['duration'] - 600


def recovery(run):
    """Seconds from the end of a spike (or the start of a sustained step) to the last timeout or rejection."""
    start = arg(run, '--spike-start', 0)
    length = arg(run, '--spike-len', 0)
    end = start + length if length < run['meta']['duration'] - start else start
    t, stuck = last_bad(run)
    if stuck:
        return 'stuck'
    return 0 if t is None else int(max(0, t - end))


def lost_pct(run):
    first = sum(r['first'] for r in run['load'])
    return 100.0 * sum(r['given_up'] for r in run['load']) / first if first else 0.0


def swing(run, need=20):
    """Pod count swing over the last hour, as a share of the pods needed (Definition 5)."""
    end = max(r['t'] for r in run['hpa'])
    tail = [r['spec_replicas'] for r in run['hpa'] if r['t'] >= end - 3600]
    return (max(tail) - min(tail)) / need, min(tail), max(tail)


def peak(run):
    return max(r['spec_replicas'] for r in run['hpa'])


def need(runs, names):
    got = {n: load_run(n) for n in names}
    missing = [n for n, r in got.items() if r is None]
    return got, missing


# ---------------------------------------------------------------- judges

def judge_calibrate(R):
    """The predictions rest on two numbers: the dead time (order to ready, 90 s) and the round
    (one order to the next, 120 s at kit size: dead time plus the 30 s metric window and sync).
    Both are measured here from the recorder, at 5 s polling, together with the lag from the
    step to the first order (15 s in the model), which shows the metrics pipeline's latency.
    A pod that never becomes ready within the run makes the calibration incomplete, and `all`
    stops; an initial rollout that is not ready within 900 s aborts the run itself."""
    dead, rounds, lags, last = [], [], [], []
    for n in ('p1-3x', 'p1-5x'):
        run = R[n]
        s0 = arg(run, '--spike-start')
        rows = spec_after(run, s0)
        n0 = rows[0]['spec_replicas']
        t1 = first_time(rows, lambda r: r['spec_replicas'] > n0)
        if t1 is None:
            return 'incomplete', '%s: no scale-up observed' % n, None
        first_round = max(r['spec_replicas'] for r in rows if t1 <= r['t'] <= t1 + 60)
        t_ready = first_time(rows, lambda r: r['ready_replicas'] > n0)
        t_all = first_time(rows, lambda r: r['ready_replicas'] >= first_round)
        t2 = first_time(rows, lambda r: r['spec_replicas'] > first_round)
        if t_ready is None or t_all is None or t2 is None:
            return 'incomplete', '%s: the first round never completed (no pod ready, or no second order) within the run' % n, None
        dead.append(t_ready - t1)
        last.append(t_all - t1)
        rounds.append(t2 - t1)
        lags.append(t1 - s0)
    ok = abs(fmean(dead) - DEAD) <= 15 and abs(fmean(rounds) - 120) <= 20
    detail = ('dead time %s s (predictions assume %d); last pod of the first round ready after %s s; round %s s (predictions assume 120); '
              'step to first order %s s (model 15)' % ('/'.join('%.0f' % x for x in dead), DEAD, '/'.join('%.0f' % x for x in last),
                                                        '/'.join('%.0f' % x for x in rounds), '/'.join('%.0f' % x for x in lags)))
    if not ok:
        detail += '; REGENERATE THE PREDICTIONS for the measured dead time and round before judging anything else'
    return ('as predicted' if ok else 'not as predicted'), detail, fmean(dead)


def judge_p1_f1(R):
    seqs = {}
    for n in ('p1-3x', 'p1-5x'):
        run = R[n]
        s0 = arg(run, '--spike-start')
        t_cap3 = first_time(spec_after(R['p1-3x'], s0), lambda r: r['ready_replicas'] >= 20 * 3 / POD_RATE)
        rows = [r for r in spec_after(run, s0) if t_cap3 is None or r['t'] <= t_cap3]
        seqs[n] = distinct(r['spec_replicas'] for r in rows)
    same = seqs['p1-3x'] == seqs['p1-5x']
    return ('as predicted' if same else 'REFUTED'), 'orders before the 3x run met its load: 3x %s, 5x %s; predicted 4, 7, 8 in both (4 is the count before the step)' % (seqs['p1-3x'], seqs['p1-5x'])


def judge_p1_f2(R):
    caps, peaks, fastest = {}, {}, 0.0
    for n, k in (('p1-3x', 3), ('p1-5x', 5)):
        run = R[n]
        s0 = arg(run, '--spike-start')
        rows = spec_after(run, s0)
        caps[n] = first_time(rows, lambda r: r['ready_replicas'] >= 20 * k / POD_RATE)
        caps[n] = None if caps[n] is None else caps[n] - s0
        peaks[n] = peak(run)
        for r in rows:
            later = [x for x in rows if x['t'] >= r['t'] + 2 * DEAD - 60]
            if later and r['ready_replicas']:
                fastest = max(fastest, (later[0]['ready_replicas'] - 1) / r['ready_replicas'])
    if None in caps.values():
        return 'incomplete', 'capacity never met: %s' % caps
    refuted = fastest > 2.0 or caps['p1-5x'] - caps['p1-3x'] < 60
    detail = 'time to capacity 3x %.0f s, 5x %.0f s (predicted 105 and 225); peaks %d and %d (predicted 16 and 32); fastest ready growth per round %.2f (at most 2)' % (
        caps['p1-3x'], caps['p1-5x'], peaks['p1-3x'], peaks['p1-5x'], fastest)
    if refuted:
        return 'REFUTED', detail
    close = abs(caps['p1-3x'] - 105) <= 30 and abs(caps['p1-5x'] - 225) <= 30
    return ('as predicted' if close else 'not as predicted'), detail


def judge_p1_f3(R):
    p = peak(R['p1-limit'])
    return ('as predicted' if p <= 22 else 'REFUTED'), 'peak %d pods with the limit at four times the request; predicted 20, refuted above the 10%% tolerance (22)' % p


def judge_p1_f4(R):
    p = peak(R['p1-hot'])
    return ('as predicted' if p <= 4 else 'REFUTED'), 'peak %d pods at a 93%% target under a 3x step; predicted no scale-up from 4' % p


def judge_queue(R, hunts, rests, refute_if):
    out, s = {}, []
    for n in hunts + rests:
        sw, lo, hi = swing(R[n])
        out[n] = sw > 0.30
        s.append('%s %d..%d (swing %.0f%%, %s)' % (n, lo, hi, 100 * sw, 'hunts' if out[n] else 'rests'))
    predicted = all(out[n] for n in hunts) and not any(out[n] for n in rests)
    verdict = 'REFUTED' if refute_if(out) else ('as predicted' if predicted else 'not as predicted')
    return verdict, '; '.join(s)


def judge_p2_f1(R):
    return judge_queue(R, ['q-60-300'], ['q-150-300'], lambda o: (not o['q-60-300']) or o['q-150-300'])


def judge_p2_f2(R):
    return judge_queue(R, ['q-60-300'], ['q-60-60'], lambda o: (not o['q-60-300']) and o['q-60-60'])


def judge_p2_f3(R):
    return judge_queue(R, ['q-1-300', 'q-1-0'], [], lambda o: not o['q-1-0'])


def judge_p3_f1(R):
    run = R['p3-steady']
    end = run['meta']['duration']
    tail = [r for r in run['load'] if r['t'] >= end - 3600]
    ok = sum(r['ok'] for r in tail)
    first = sum(r['first'] for r in tail)
    timeouts = sum(r['timeouts'] for r in run['load'])
    failed = first and ok < 0.5 * first
    return ('REFUTED' if failed else ('as predicted' if timeouts == 0 else 'not as predicted')), \
        '%d timeouts over %d s at 50%% utilization with no spike; last hour served %.0f%% of first attempts; predicted no timeouts' % (timeouts, end, 100.0 * ok / first if first else 0)


def judge_p3_f2(R):
    r30, r40 = recovery(R['p3-spike-30']), recovery(R['p3-spike-40'])
    refuted = r40 != 'stuck' or r30 == 'stuck'
    return ('REFUTED' if refuted else 'as predicted'), 'recovery after the spike: 30%% %s (predicted about 9,756 s), 40%% %s (predicted never)' % (
        '%s s' % r30 if r30 != 'stuck' else 'never', '%s s' % r40 if r40 != 'stuck' else 'never')


def judge_p3_f3(R):
    rf, ri = recovery(R['p3-first']), recovery(R['p3-ingress'])
    refuted = rf != 'stuck' or ri == 'stuck'
    return ('REFUTED' if refuted else 'as predicted'), \
        'first attempts: %s, peak %d, lost %.1f%% (predicted never, 20, 99.3%%); ingress: %s, peak %d, lost %.1f%% (predicted 270 s, 50, 3.2%%)' % (
            'never' if rf == 'stuck' else '%s s' % rf, peak(R['p3-first']), lost_pct(R['p3-first']),
            'never' if ri == 'stuck' else '%s s' % ri, peak(R['p3-ingress']), lost_pct(R['p3-ingress']))


def judge_p3_f4(R):
    rp = recovery(R['p3-pair'])
    flat = R['p3-pair-flat']
    end = max(r['t'] for r in flat['hpa'])
    held = max(r['spec_replicas'] for r in flat['hpa'] if r['t'] >= end - 600)
    refuted = rp == 'stuck' or held > 4
    return ('REFUTED' if refuted else 'as predicted'), 'paired run %s (predicted 270 s); with no step it holds %d pods (predicted 4, as the clean signal alone)' % (
        'never recovers' if rp == 'stuck' else 'recovers after %s s' % rp, held)


def judge_p4_f1(R):
    pn, pb = peak(R['p4-nobound']), peak(R['p4-bound-5'])
    ln, lb = lost_pct(R['p4-nobound']), lost_pct(R['p4-bound-5'])
    refuted = pb >= 50 or lb >= ln
    return ('REFUTED' if refuted else 'as predicted'), 'no bound: peak %d, lost %.1f%% (predicted 50, 10.3%%); 5 s bound: peak %d, lost %.1f%% (predicted 21, 1.2%%)' % (pn, ln, pb, lb)


def judge_p4_f2(R):
    r6, r7, r12 = recovery(R['p4-ceil-6']), recovery(R['p4-ceil-7']), recovery(R['p4-ceil-12'])
    detail = 'ceiling 6: %s (predicted never); 7: %s (predicted about 6,974 s); 12: %s (predicted about 1,085 s)' % tuple(
        'never' if x == 'stuck' else '%s s' % x for x in (r6, r7, r12))
    if r6 != 'stuck':
        return 'REFUTED', detail
    if 'stuck' in (r7, r12) or not r12:
        return 'not as predicted', detail
    ratio = (r7 * 1) / (r12 * 6)
    detail += '; recovery x margin: %.0f against %.0f, ratio %.2f' % (r7, r12 * 6, ratio)
    return ('as predicted' if 0.5 <= ratio <= 2 else 'REFUTED'), detail


def judge_p4_f3(R):
    # The load generator cannot see work served for nobody. An admitted attempt that times out
    # was still queued, and the server finishes it later, so client timeouts count abandoned work.
    t20 = sum(r['timeouts'] for r in R['p4-bound-20']['load'])
    t5 = sum(r['timeouts'] for r in R['p4-bound-5']['load'])
    l20, l5 = lost_pct(R['p4-bound-20']), lost_pct(R['p4-bound-5'])
    return ('REFUTED' if t20 <= t5 else 'as predicted'), \
        'admitted attempts that timed out: 20 s bound %d, 5 s bound %d; lost %.1f%% and %.1f%% (predicted 7.5%% and 1.2%%, peaks %d and %d against 50 and 21)' % (
            t20, t5, l20, l5, peak(R['p4-bound-20']), peak(R['p4-bound-5']))


CRITERIA = [
    ('calibrate', ['p1-3x', 'p1-5x'], judge_calibrate, 'dead time on this cluster against the 90 s the predictions assume'),
    ('P1-F1', ['p1-3x', 'p1-5x'], judge_p1_f1, 'One Bit per Dead Time: the same first request'),
    ('P1-F2', ['p1-3x', 'p1-5x'], judge_p1_f2, 'One Bit per Dead Time: at most one factor per round'),
    ('P1-F3', ['p1-limit'], judge_p1_f3, 'One Bit per Dead Time: the ceiling causes the overshoot'),
    ('P1-F4', ['p1-hot'], judge_p1_f4, 'One Bit per Dead Time: the dead band'),
    ('P3-F1', ['p3-steady'], judge_p3_f1, 'Demand Is Not Debt: a trigger is required'),
    ('P3-F2', ['p3-spike-30', 'p3-spike-40'], judge_p3_f2, 'Demand Is Not Debt: the threshold'),
    ('P3-F3', ['p3-first', 'p3-ingress'], judge_p3_f3, 'Demand Is Not Debt: the signal decides'),
    ('P3-F4', ['p3-pair', 'p3-pair-flat'], judge_p3_f4, 'Demand Is Not Debt: pairing restores recovery'),
    ('P4-F1', ['p4-nobound', 'p4-bound-5'], judge_p4_f1, 'The Barrier the Scaler Cannot Hold: the bound removes the overshoot and the loss'),
    ('P4-F2', ['p4-ceil-6', 'p4-ceil-7', 'p4-ceil-12'], judge_p4_f2, 'The Barrier the Scaler Cannot Hold: the ceiling floor'),
    ('P4-F3', ['p4-bound-20', 'p4-bound-5'], judge_p4_f3, 'The Barrier the Scaler Cannot Hold: the bound must be shorter than the timeout'),
    ('P2-F1', ['q-60-300', 'q-150-300'], judge_p2_f1, 'The Delay a Window Demands: the boundary exists'),
    ('P2-F2', ['q-60-300', 'q-60-60'], judge_p2_f2, 'The Delay a Window Demands: the window raises the boundary'),
    ('P2-F3', ['q-1-300', 'q-1-0'], judge_p2_f3, 'The Delay a Window Demands: removing the window does not rescue the default'),
]
BY_NAME = {c[0]: c for c in CRITERIA}


def verdict(name):
    _, runs, fn, title = BY_NAME[name]
    got, missing = need(None, runs)
    if missing:
        return 'incomplete', 'missing runs: %s' % ', '.join(missing)
    res = fn(got)
    return res[0], res[1]


# ---------------------------------------------------------------- running

class Cluster:
    def __init__(self, dry):
        self.dry = dry

    def sh(self, cmd, check=True, capture=False, stdin=None):
        print('  $ ' + ' '.join(cmd), flush=True)
        if self.dry:
            return ''
        r = subprocess.run(cmd, input=stdin, capture_output=capture, text=True)
        if check and r.returncode:
            raise SystemExit('command failed (%d): %s\n%s' % (r.returncode, ' '.join(cmd), r.stderr if capture else ''))
        return r.stdout if capture else ''

    def sleep(self, s):
        print('  ... waiting %d s' % s, flush=True)
        if not self.dry:
            time.sleep(s)


def namespace(name):
    return 'cia-' + name


def ensure_configmap(c, ns):
    files = []
    for f in ('server.py', 'meter.py', 'broker.py', 'consumer.py'):
        files += ['--from-file=' + os.path.join(HERE, f)]
    y = c.sh(['kubectl', '-n', ns, 'create', 'configmap', 'hp-server'] + files + ['--dry-run=client', '-o', 'yaml'], capture=True)
    c.sh(['kubectl', '-n', ns, 'apply', '-f', '-'], stdin=y)


def purge(c, ns, timeout=900):
    """Delete the run's namespace and block until it is gone. Namespace deletion waits for every
    object in it, including KEDA's finalizer on the ScaledObject and the HPA KEDA owns, so the
    next run cannot inherit a dying autoscaler or its cached metrics. A final cluster-wide check
    confirms no HPA or ScaledObject in this namespace survives. NodePorts are cluster-wide,
    so the next run's apply would also fail loudly if a service outlived its namespace."""
    c.sh(['kubectl', 'delete', 'namespace', ns, '--ignore-not-found', '--wait=true', '--timeout=%ds' % timeout], check=False)
    end = time.time() + timeout
    while not c.dry:
        gone = subprocess.run(['kubectl', 'get', 'namespace', ns], capture_output=True).returncode != 0
        left = c.sh(['kubectl', '-n', ns, 'get', 'hpa,scaledobject', '-o', 'name', '--ignore-not-found'],
                    capture=True, check=False).strip()
        if gone and not left:
            return
        if time.time() > end:
            raise SystemExit('namespace %s or its autoscaler still exists after %d s; resolve by hand before the next run' % (ns, timeout))
        time.sleep(5)


def wait_first_reading(c, path, timeout=600):
    """Block until the recorder has logged a row with a live metric value from the HPA, so the
    autoscaler is reading its signal before the load generator's countdown starts."""
    print('  ... waiting for the first metric the HPA reports', flush=True)
    end = time.time() + timeout
    while not c.dry:
        if os.path.exists(path):
            rows = read_csv(path)
            if any(r.get('metric') for r in rows):
                return time.time()
        if time.time() > end:
            raise SystemExit('the HPA reported no metric within %d s; check metrics-server or KEDA before rerunning' % timeout)
        time.sleep(2)
    return time.time()


def run_one(c, name, node, duration=None):
    spec = RUNS[name]
    ns = namespace(name)
    d = os.path.join(RUNS_DIR, name)
    os.makedirs(d, exist_ok=True)
    print('\n== run %s (%s, %d s, namespace %s)' % (name, spec['mode'], duration or spec['duration'], ns), flush=True)
    yaml = c.sh([sys.executable, KIT, spec['mode'], '--namespace', ns] + spec['kit'], capture=True)
    if not c.dry:
        write_text(os.path.join(d, 'exp.yaml'), yaml)
    purge(c, ns)                                 # a leftover from an aborted earlier attempt
    c.sh(['kubectl', 'create', 'namespace', ns])
    ensure_configmap(c, ns)
    c.sh(['kubectl', '-n', ns, 'apply', '-f', os.path.join(d, 'exp.yaml')])
    c.sh(['kubectl', '-n', ns, 'rollout', 'status', 'deploy/' + spec['deploy'], '--timeout=900s'])
    hpa_csv = os.path.join(d, 'hpa.csv')
    if os.path.exists(hpa_csv):
        os.remove(hpa_csv)
    rec_cmd = [sys.executable, KIT, 'record', '--namespace', ns, '--deploy', spec['deploy'], '--hpa', spec['hpa'], '--out', hpa_csv]
    if spec['mode'] == 'queue':
        rec_cmd += ['--metrics', 'http://%s:30090/metrics' % node]
    print('  $ ' + ' '.join(rec_cmd), flush=True)
    rec = None if c.dry else subprocess.Popen(rec_cmd)
    t_rec = time.time()
    meta = dict(run=name, namespace=ns, mode=spec['mode'], kit_args=spec['kit'], load_args=[], duration=duration or spec['duration'],
                dead_time_assumed=DEAD, started=time.strftime('%Y-%m-%dT%H:%M:%S'))
    try:
        t_metric = wait_first_reading(c, hpa_csv)
        meta['first_metric_after'] = round(t_metric - t_rec, 1)
        if spec['load']:
            c.sleep(60)                          # a minute of baseline readings, then the load's own 120 s before the step
            largs = list(spec['load'])
            if duration:
                largs[largs.index('--duration') + 1] = str(duration)
            if spec['meter']:
                largs += ['--meter', '%s:30081' % node]
            lg = [sys.executable, os.path.join(HERE, 'loadgen.py'), node, '30080'] + largs + ['--out', os.path.join(d, 'load.csv')]
            meta['load_args'] = largs
            meta['load_offset'] = time.time() - t_rec
            c.sh(lg)
        else:
            meta['load_offset'] = 0.0
            c.sleep(meta['duration'])
    finally:
        if rec:
            rec.terminate()
            rec.wait()
        purge(c, ns)
    if not c.dry:
        write_text(os.path.join(d, 'meta.json'), json.dumps(meta, indent=1))


def preflight(c):
    """Record the intervals the predictions depend on, as this cluster actually sets them, in
    runs/cluster.json. Nothing here is gated: calibration measures their combined effect. From 1
    to N replicas the HPA polls KEDA at its own sync period and KEDA caches nothing unless
    useCachedMetrics is set (KEDA 2.19 ScaledObject spec), so the HPA sync period, the
    metrics-server resolution and the window each CPU sample reports are what set the round."""
    if c.dry:
        print('  (preflight skipped in a dry run)')
        return
    def get(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ''
    def flag(args, name):
        for x in args:
            if x.startswith(name + '='):
                return x.split('=', 1)[1]
        return 'not set (binary default)'
    def field(fn, missing):
        try:
            return fn()
        except (KeyError, IndexError, ValueError, TypeError):
            return missing
    def cm_cmd():
        cm = json.loads(get(['kubectl', '-n', 'kube-system', 'get', 'pods', '-l', 'component=kube-controller-manager', '-o', 'json']))
        return cm['items'][0]['spec']['containers'][0]['command']
    def ms_args():
        ms = json.loads(get(['kubectl', '-n', 'kube-system', 'get', 'deploy', 'metrics-server', '-o', 'json']))
        return ms['spec']['template']['spec']['containers'][0].get('args', [])
    unseen = 'unknown (controller-manager not visible)'
    info = {
        'hpa_sync_period': field(lambda: flag(cm_cmd(), '--horizontal-pod-autoscaler-sync-period'), unseen),
        'hpa_tolerance': field(lambda: flag(cm_cmd(), '--horizontal-pod-autoscaler-tolerance'), unseen),
        'hpa_downscale_window': field(lambda: flag(cm_cmd(), '--horizontal-pod-autoscaler-downscale-stabilization'), unseen),
        'metrics_server_resolution': field(lambda: flag(ms_args(), '--metric-resolution'), 'metrics-server not found'),
        'cpu_sample_window': field(lambda: sorted({p['window'] for p in json.loads(get(
            ['kubectl', 'get', '--raw', '/apis/metrics.k8s.io/v1beta1/namespaces/kube-system/pods']))['items']}) or 'no pod metrics yet', 'metrics API not answering'),
        'keda_image': field(lambda: json.loads(get(['kubectl', '-n', 'keda', 'get', 'deploy', 'keda-operator', '-o', 'json']))
                            ['spec']['template']['spec']['containers'][0]['image'], 'keda-operator not found'),
        'kubernetes': field(lambda: json.loads(get(['kubectl', 'version', '-o', 'json']))['serverVersion']['gitVersion'], 'unknown'),
    }
    info['model_assumes'] = dict(hpa_sync_period='15s', cpu_sample_window='30s', dead_time='%ds' % DEAD, kubernetes='v1.34.0', keda='2.19')
    write_text(os.path.join(RUNS_DIR, 'cluster.json'), json.dumps(info, indent=1))
    print('  preflight: ' + '; '.join('%s %s' % (k, v) for k, v in info.items() if k != 'model_assumes'), flush=True)


def run_criterion(c, name, node, rerun, duration=None):
    _, runs, _, title = BY_NAME[name]
    print('\n#### %s: %s' % (name, title), flush=True)
    for r in runs:
        if rerun or load_run(r) is None:
            run_one(c, r, node, duration)
        else:
            print('  (reusing saved run %s)' % r)
    if c.dry:
        return None
    v, detail = verdict(name)
    print('  VERDICT %s: %s\n    %s' % (name, v, detail), flush=True)
    with open(os.path.join(RUNS_DIR, 'verdicts.txt'), 'a', encoding='utf-8') as f:
        f.write('%s %s | %s | %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), name, v, detail))
    return v


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('cmd', choices=['list', 'run', 'all', 'verdict'])
    p.add_argument('criterion', nargs='?')
    p.add_argument('--node', default=os.environ.get('NODE', ''))
    p.add_argument('--rerun', action='store_true', help='repeat runs already saved')
    p.add_argument('--dry-run', action='store_true', help='print the commands without running them')
    p.add_argument('--duration', type=int, default=None, help='override every run length (smoke tests only)')
    a = p.parse_args()
    if a.cmd == 'list':
        total = 0
        for name, runs, _, title in CRITERIA:
            print('%-10s %s\n           runs: %s' % (name, title, ', '.join('%s (%d s)' % (r, RUNS[r]['duration']) for r in runs)))
        uniq = {r for _, runs, _, _ in CRITERIA for r in runs}
        total = sum(RUNS[r]['duration'] + 300 for r in uniq)
        print('\n%d distinct runs, about %.0f hours of cluster time including setup and teardown' % (len(uniq), total / 3600))
        return
    if a.cmd == 'verdict':
        for name in ([a.criterion] if a.criterion else [c[0] for c in CRITERIA]):
            v, detail = verdict(name)
            print('%-10s %s\n           %s' % (name, v, detail))
        return
    if not a.node and not a.dry_run:
        raise SystemExit('set --node or NODE to the kind node address')
    c = Cluster(a.dry_run)
    os.makedirs(RUNS_DIR, exist_ok=True)
    if a.cmd == 'all' or a.criterion == 'calibrate':
        preflight(c)
    if a.cmd == 'run':
        if a.criterion not in BY_NAME:
            raise SystemExit('unknown criterion; see: python3 run_suite.py list')
        run_criterion(c, a.criterion, a.node, a.rerun, a.duration)
        return
    for name, _, _, _ in CRITERIA:
        v = run_criterion(c, name, a.node, a.rerun, a.duration)
        if name == 'calibrate' and v not in (None, 'as predicted'):
            raise SystemExit('calibration failed: regenerate the predictions for the measured dead time, then rerun with `all`')


if __name__ == '__main__':
    main()
