"""Every number of the series Correct in Isolation, one section per table or figure.

    python3 reproduce.py                   every section          python3 reproduce.py T3   one section
    python3 reproduce.py --check           the tests, then every section against expected/results.txt
    python3 reproduce.py --figures         redraw the figures     --figures --check         compare them

The sections live in sections/, one module per part. Part 1 (a shared signal): T1 to T5, T19 to T24, T39, T78, T90 to T92, T103, T107, T113, T118 to T120. Part 2
(a shared time scale): T6 to T9, T25 to T38, T40, T79, T93 to T96, T106, T121. Part 3 (a shared state): T10 to T12,
T41 to T46, T57, T65 to T70, T86 to T87, T97 to T99, T104 to T105, T108. Part 4 (a shared assumption): T13 to
T14, T47 to T49, T58 to T64, T80, T89, T100 to T101, T114. Part 5 (a shared order): T15 to T16, T50 to T52,
T71 to T72, T76 to T77, T82 to T85, T102. Part 6 (the whole): T17 to T18, T53 to T56, T73 to T75, T81, T88,
T109 to T112, T115 to T117.
The command line is the repository's shared tools/harness.py. Inputs are documented contracts and named parameters
(docs/ASSUMPTIONS.md); trace inputs are stated in each section's header.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'model'), os.path.join(HERE, '..', 'tools')]

import harness
from sections import part1, part2, part3, part4, part5, part6

PARTS = (part1, part2, part3, part4, part5, part6)
SECTIONS = harness.collect({name: fn for part in PARTS for name, fn in vars(part).items()})

if __name__ == '__main__':
    sys.exit(harness.main(sys.argv[1:], HERE, SECTIONS))
