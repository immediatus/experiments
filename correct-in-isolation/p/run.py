"""Runs the P checker on every test case of this folder and prints one line per check: the test case,
the schedules explored, and the verdict, either that no schedule broke the property or the first
assertion a schedule broke. `run.py --check` compares the lines with expected.txt.

P checks communicating state machines with their queues and timers, where the hidden memory of Parts 3,
4 and 5 lives: a client's backoff, a reconciler's timer against a ReplicaSet's retry, the calls a first
admission pass made. It explores schedules and choices at random from a fixed seed, so a verdict that no
schedule broke a property is a finding over the schedules explored, not a proof. P needs the .NET 8 SDK
and the `p` tool on PATH (`dotnet tool install P`); nothing is installed by this folder.

Run: python3 p/run.py [--check]
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# test case: schedules explored. The backoff cases choose a run length and a jitter at every rejection, so
# they get many schedules; the repair and admission cases have a handful of choices each.
CASES = (('tcBackoffFresh', 20000), ('tcBackoffFreshTight', 20000), ('tcBackoffRaised', 20000),
         ('tcBackoffRaisedTight', 20000), ('tcRepairSelfHeal', 500), ('tcRepairPaused', 500),
         ('tcRepairNudged', 500), ('tcAdmissionNoFirstCall', 2000), ('tcAdmissionFixedPoint', 2000))


def tool():
    """The p executable on PATH, or None."""
    return shutil.which('p')


def verdict(out):
    """'holds' when no schedule broke the property; otherwise the first broken assertion's message and
    the schedule that broke it, read from the bug log the checker writes."""
    if 'Found 0 bugs' in out:
        return 'holds'
    if 'Found 1 bug' not in out:
        return 'error'
    found = (re.findall(r'Schedule #(\d+)', out) or [None])[-1]
    found = found or (re.search(r'Explored (\d+) schedules', out).group(1) if re.search(r'Explored (\d+) schedules', out) else '?')
    log = os.path.join(HERE, 'PCheckerOutput', 'BugFinding')
    msg = 'assertion'
    for name in sorted(os.listdir(log)):
        if name.endswith('_0_0.txt'):
            m = re.search(r'Assertion Failed: \S+ (.+)', open(os.path.join(log, name), encoding='utf-8').read())
            if m:
                msg = m.group(1).strip()
    return 'violated in schedule %s: %s' % (found, msg)


def run():
    """Compile the P project and check each test case for its fixed number of schedules with seed 1,
    returning one line per case: case | schedules | verdict."""
    if not tool():
        sys.exit('P needs the p tool on PATH (dotnet tool install P) and the .NET 8 SDK')
    subprocess.run(['p', 'compile'], cwd=HERE, capture_output=True, text=True, check=True)
    lines = []
    for case, schedules in CASES:
        shutil.rmtree(os.path.join(HERE, 'PCheckerOutput'), ignore_errors=True)
        out = subprocess.run(['p', 'check', '-tc', case, '-s', str(schedules), '--seed', '1', '-ms', '200000'],
                             cwd=HERE, capture_output=True, text=True).stdout
        lines.append('%s | %d schedules | %s' % (case, schedules, verdict(out)))
    return lines


if __name__ == '__main__':
    lines = run()
    if sys.argv[1:] == ['--check']:
        expected = open(os.path.join(HERE, 'expected.txt'), encoding='utf-8').read().splitlines()
        if lines != expected:
            print('\n'.join(lines))
            sys.exit('P verdicts differ from expected.txt')
        print('P verdicts match expected.txt (%d checks)' % len(lines))
    else:
        print('\n'.join(lines))
