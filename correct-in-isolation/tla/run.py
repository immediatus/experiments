"""Runs TLC, the TLA+ model checker, on every specification and configuration in this folder and prints
one line per check: the specification, the configuration, the verdict, and the distinct states TLC
found. `run.py --check` compares the lines with expected.txt.

The checks are the formal side of the series: each seam's contracts checked on their own, where they
hold, and composed, where TLC finds the counterexample. TLC needs Java (the java on PATH, or $JAVA)
and tla2tools.jar ($TLA2TOOLS); nothing else is installed by this folder.

Run: python3 tla/run.py [--check]
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def tools():
    java = os.environ.get('JAVA') or shutil.which('java')
    jar = os.environ.get('TLA2TOOLS')
    return (java, jar) if java and jar and os.path.isfile(jar) else (None, None)


def verdict(out):
    m = re.search(r'(Temporal property|Invariant) (\w+) (?:was|is) violated', out)
    if m:
        v = 'violated: %s' % m.group(2)
    elif 'Model checking completed. No error has been found.' in out:
        v = 'holds'
    else:
        v = 'error'
    states = re.search(r'([\d,]+) distinct states found', out)
    return v, states.group(1).replace(',', '') if states else '?'


def run():
    java, jar = tools()
    if not java:
        sys.exit('TLC needs java on PATH (or $JAVA) and $TLA2TOOLS pointing at tla2tools.jar')
    lines = []
    for cfg in sorted(glob.glob(os.path.join(HERE, '*.cfg'))):
        spec = os.path.basename(cfg).split('_')[0] + '.tla'
        with tempfile.TemporaryDirectory() as meta:
            out = subprocess.run([java, '-XX:+UseParallelGC', '-cp', jar, 'tlc2.TLC', '-config', cfg, '-workers', '1',
                                  '-deadlock', '-noGenerateSpecTE', '-metadir', meta, spec],
                                 cwd=HERE, capture_output=True, text=True).stdout
        v, states = verdict(out)
        lines.append('%s | %s | %s | %s distinct states' % (spec[:-4], os.path.basename(cfg)[:-4], v, states))
    return lines


if __name__ == '__main__':
    lines = run()
    if sys.argv[1:] == ['--check']:
        expected = open(os.path.join(HERE, 'expected.txt'), encoding='utf-8').read().splitlines()
        if lines != expected:
            print('\n'.join(line for line in lines if line not in expected))
            sys.exit('TLC results differ from tla/expected.txt')
        print('TLC results match tla/expected.txt')
    else:
        print('\n'.join(lines))
