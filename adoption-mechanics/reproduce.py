"""Every number of the series Adoption Mechanics, one section per table or figure.

    python3 reproduce.py                   every section          python3 reproduce.py T3   one section
    python3 reproduce.py --check           the tests, then every section against expected/results.txt
    python3 reproduce.py --figures         redraw the figures     --figures --check         compare them

The sections live in sections/, one module per post. The command line is the repository's shared
tools/harness.py. Inputs are named parameters documented in docs/ASSUMPTIONS.md; the public model data is
read from the count files in data/, which data/fetch_helm.py builds once.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'model'), os.path.join(HERE, '..', 'tools')]

import harness
from sections import post1, post2, post3

POSTS = (post1, post2, post3)
SECTIONS = harness.collect({name: fn for post in POSTS for name, fn in vars(post).items()})

if __name__ == '__main__':
    sys.exit(harness.main(sys.argv[1:], HERE, SECTIONS))
