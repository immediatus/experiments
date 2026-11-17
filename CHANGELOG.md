# Changelog

Releases are tagged `<series-slug>-v<major>.<minor>`. A published experiment changes only by a
dated erratum recorded here, with what changed, why, and which numbers moved.

## Unreleased

### Repository

- Shared checks extended: a lint step (`tools/lint.py`), line coverage on demand (`tools/coverage.py`),
  documentation coverage in `tools/check_docs.py`, and every reproduction run under two hash seeds; a
  development container (`.devcontainer/`) with every tool the checks use, so TLC and P run instead of
  being skipped; and the TLA+, P and .NET build output kept out of version control.

### correct-in-isolation

- First version of the experiment behind *Correct in Isolation* (six parts, November and December 2026): the
  simulations and closed forms of the five seams and the whole, 121 result sections, 33 figures, TLA+ models of
  each seam's formal side and P models of three, per-part documentation, the claim map, the falsification criteria, the
  assumptions, and `audit/seam_audit.py`, which runs the five whole-system tests on a cluster's own objects.

### capacity-in-arrears

- First release of the experiment behind *Capacity in Arrears* (four parts, October 2026):
  the port of the Kubernetes v1.34.0 replica calculation and its upstream test cases, the
  simulations, 49 result sections, 24 figures, per-part documentation, the claim map, the
  falsification criteria and the cluster kit.
