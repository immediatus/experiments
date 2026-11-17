"""Cycle lower-bound overheads of five OpenJDK 17 collectors, transcribed from Cai, Blackburn, Bond
and Maas, "Distilling the Real Cost of Production Garbage Collectors", ISPASS 2022
(doi 10.1109/ISPASS55109.2022.00005), table "Cycle LBOs averaged over 16 benchmarks": the
geometric mean, over 16 DaCapo benchmarks, of a lower bound on total CPU cycles relative to the
distilled cost without collection, at heap sizes given as multiples of each benchmark's minimum
heap. None marks the entries the paper leaves blank, where a collector cannot run every benchmark.
The same table is Table 3.7 of Cai's 2026 thesis. The repetition on OpenJDK 21 (Blackburn and five coauthors,
"Rethinking Java Performance Analysis", ASPLOS 2025, Figure 1) is published only as a figure and reports the
same pattern; neither covers ZGC's generational mode.
"""
from formulas import elasticity

HEAPS = (1.4, 1.9, 2.4, 3.0, 3.7, 4.4, 5.2, 6.0)
CYCLE_LBO = {
    'Serial':     (1.22, 1.08, 1.06, 1.06, 1.04, 1.04, 1.04, 1.04),
    'Parallel':   (1.70, 1.15, 1.12, 1.10, 1.07, 1.06, 1.06, 1.05),
    'G1':         (1.54, 1.34, 1.17, 1.14, 1.10, 1.09, 1.09, 1.09),
    'Shenandoah': (None, 1.75, 1.54, 1.47, 1.42, 1.39, 1.36, 1.33),
    'ZGC':        (None, None, 1.92, 1.68, 1.55, 1.46, 1.40, 1.34),
}


def pair_elasticities(gc):
    """(heap from, heap to, beta) for each pair of neighboring heap sizes the collector ran at:
    the elasticity of CPU cycles with respect to heap size, read from the lower bound."""
    row = CYCLE_LBO[gc]
    return [(HEAPS[i], HEAPS[i + 1], elasticity(HEAPS[i], row[i], HEAPS[i + 1], row[i + 1]))
            for i in range(len(HEAPS) - 1) if row[i] is not None and row[i + 1] is not None]


def peak_elasticity(gc):
    """The neighboring pair with the largest elasticity: where the collector's cost per byte of
    heap rises fastest."""
    return max(pair_elasticities(gc), key=lambda p: p[2])
