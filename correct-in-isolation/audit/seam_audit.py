#!/usr/bin/env python3
"""Seam audit: the five whole-system tests of Part 6 run on a cluster's own objects.

Input is what `kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations,namespaces,
hpa,vpa -A -o json` prints, and optionally a description of what no object records: the facts each mutating
webhook writes and needs, the informers and their list costs, the server's capacity and history, and the surge
to plan for. Each seam's verdict is reported with its ratio of Definition 21, which passes one where the seam
binds (the assumption's binds at one).

What the objects cannot say is assumed and reported: a webhook with an object selector is taken to skip its own
pods and to match every other component's; the vertical autoscaler runs at its documented defaults. By
Proposition 40 an incomplete description can hide an assumption, order or state failure but never invent one.

Usage: audit/seam_audit.py cluster.json [--description description.json] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model'))

from audit import cyclic_components
from formulas import covered_rounds, fact_passes, rounds
from percolation import stranded
from ratios import assumption_ratio, order_ratio, signal_ratio, state_ratio, time_ratio

Obj = dict[str, Any]


class InputError(ValueError):
    """An object or a description lacks a field the audit needs; the message names both."""


def _field(obj: Obj, path: str, what: str) -> Any:
    """obj's field at a dotted path, or InputError naming `what` and the path."""
    value: Any = obj
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            raise InputError('%s: missing %s' % (what, path))
        value = value[key]
    return value


def _label(obj: Obj) -> str:
    return '%s %s' % (obj.get('kind', 'object'), (obj.get('metadata') or {}).get('name', '(unnamed)'))


def _selector_matches(selector: Optional[Obj], labels: dict[str, str]) -> bool:
    """A Kubernetes label selector against a set of labels; an absent or empty selector matches everything."""
    if not selector:
        return True
    for k, v in (selector.get('matchLabels') or {}).items():
        if labels.get(k) != v:
            return False
    for e in selector.get('matchExpressions') or []:
        key, op, values = e['key'], e['operator'], e.get('values') or []
        if op == 'In' and labels.get(key) not in values:
            return False
        if op == 'NotIn' and labels.get(key) in values:
            return False
        if op == 'Exists' and key not in labels:
            return False
        if op == 'DoesNotExist' and key in labels:
            return False
    return True


def _admits_pods(hook: Obj) -> bool:
    for r in hook.get('rules') or []:
        if any(g in ('', '*') for g in r.get('apiGroups', [])) and \
           any(x in ('pods', '*') for x in r.get('resources', [])) and \
           any(o in ('CREATE', '*') for o in r.get('operations', [])):
            return True
    return False


def _items(cluster: Obj, kind: str) -> list[Obj]:
    return [i for i in cluster.get('items', []) if i.get('kind') == kind]


def _hooks(cluster: Obj) -> list[Obj]:
    out = []
    for kind in ('MutatingWebhookConfiguration', 'ValidatingWebhookConfiguration'):
        for cfg in _items(cluster, kind):
            name = _field(cfg, 'metadata.name', kind)
            for h in cfg.get('webhooks') or []:
                _field(h, 'name', '%s %s webhook' % (kind, name))
                out.append({'kind': kind, 'config': name, 'hook': h})
    return out


def _namespaces(cluster: Obj, hooks: list[Obj]) -> dict[str, dict[str, str]]:
    ns = {_field(i, 'metadata.name', 'Namespace'): dict(i['metadata'].get('labels') or {}) for i in _items(cluster, 'Namespace')}
    for h in hooks:
        svc = (h['hook'].get('clientConfig') or {}).get('service')
        if svc and svc['namespace'] not in ns:
            ns[svc['namespace']] = {}
    for n, labels in ns.items():
        labels.setdefault('kubernetes.io/metadata.name', n)
    return ns


def assumption(cluster: Obj) -> Obj:
    """Start-time graph over namespaces: a namespace needs the namespace of every webhook that fails closed,
    admits pods, and selects that namespace."""
    hooks = _hooks(cluster)
    ns = _namespaces(cluster, hooks)
    needs: dict[str, set[str]] = {n: set() for n in ns}
    for h in hooks:
        hk = h['hook']
        svc = (hk.get('clientConfig') or {}).get('service')
        if not svc or hk.get('failurePolicy', 'Fail') != 'Fail' or not _admits_pods(hk):
            continue
        home = _field(svc, 'namespace', '%s %s service' % (h['kind'], h['config']))
        for n, labels in ns.items():
            if not _selector_matches(hk.get('namespaceSelector'), labels):
                continue
            if n == home and hk.get('objectSelector'):
                continue
            needs[n].add(home)
    cycles = sorted(sorted(c) for c in cyclic_components(needs))
    return {'needs': {k: sorted(v) for k, v in needs.items()}, 'cycles': cycles,
            'stranded': sorted(stranded(needs)), 'ratio': assumption_ratio(needs)}


def order(cluster: Obj, description: Obj) -> Obj:
    """Mutating webhooks in the order the API server calls them, configurations sorted by name, and the passes
    the described facts need under two passes (Proposition 37)."""
    seq = []
    for cfg in sorted(_items(cluster, 'MutatingWebhookConfiguration'), key=lambda c: _field(c, 'metadata.name', 'MutatingWebhookConfiguration')):
        for h in cfg.get('webhooks') or []:
            seq.append((h['name'], h.get('reinvocationPolicy', 'Never')))
    names = [n for n, _ in seq]
    facts = {}
    for f, entry in (description.get('facts') or {}).items():
        if not isinstance(entry, list) or len(entry) != 2:
            raise InputError('description: fact %s must be [writer, [facts it needs]]' % f)
        facts[f] = (entry[0], set(entry[1]))
    unknown = sorted({w for w, _ in facts.values()} - set(names))
    known = {f: v for f, v in facts.items() if v[0] in names}
    passes = fact_passes(names, known) if known else 1
    never_readers = sorted({w for w, pre in known.values() if pre and dict(seq)[w] == 'Never'})
    return {'sequence': names, 'policies': dict(seq), 'passes': passes, 'ratio': order_ratio(passes),
            'readers_never_reinvoked': never_readers, 'writers_not_found': unknown}


def signal(cluster: Obj, margin: float = 0.15, q: float = 1.0, tol: float = 0.1) -> list[Obj]:
    """Every workload a horizontal autoscaler scales on CPU or memory utilization while a vertical one, not Off,
    sizes it."""
    vpas = {}
    for v in _items(cluster, 'VerticalPodAutoscaler'):
        ref = _field(v, 'spec.targetRef', _label(v))
        mode = ((v['spec'].get('updatePolicy') or {}).get('updateMode')) or 'Auto'
        if mode != 'Off':
            vpas[(v['metadata'].get('namespace', 'default'), ref['kind'], ref['name'])] = v
    out = []
    for h in _items(cluster, 'HorizontalPodAutoscaler'):
        ref = _field(h, 'spec.scaleTargetRef', _label(h))
        key = (h['metadata'].get('namespace', 'default'), ref['kind'], ref['name'])
        if key not in vpas:
            continue
        for m in h['spec'].get('metrics') or []:
            res = m.get('resource') or {}
            target = (res.get('target') or {}).get('averageUtilization')
            if m.get('type') == 'Resource' and res.get('name') in ('cpu', 'memory') and target:
                u_h = target / 100.0
                out.append({'workload': '/'.join(key), 'resource': res['name'], 'target': u_h, 'shared_metric': True,
                            'ratio': signal_ratio(u_h, margin, q, tol)})
    return out


def state(description: Obj) -> Optional[Obj]:
    """The forced list work of the described informers against the server's capacity, mean watch and history."""
    if not description.get('informers'):
        return None
    for i, inf in enumerate(description['informers']):
        for key in ('count', 'list_cost'):
            _field(inf, key, 'description: informers[%d]' % i)
    for key in ('capacity', 'mean_watch', 'history'):
        _field(description, key, 'description')
    work = sum(i['count'] * i['list_cost'] for i in description['informers'])
    n = sum(i['count'] for i in description['informers'])
    return {'informers': n, 'list_work': work,
            'ratio': state_ratio(1, work, description['capacity'], description['mean_watch'], description['history'])}


def time_scale(cluster: Obj, description: Obj) -> Optional[Obj]:
    """The rounds a described surge needs at the lowest utilization target, and the rounds the free slots cover."""
    if 'surge' not in description:
        return None
    targets = [m['resource']['target']['averageUtilization'] / 100.0
               for h in _items(cluster, 'HorizontalPodAutoscaler') for m in h['spec'].get('metrics') or []
               if m.get('type') == 'Resource' and (m.get('resource') or {}).get('target', {}).get('averageUtilization')]
    u_h = min(targets) if targets else 0.5
    k, n0, slots = description['surge'], description.get('running_pods', 16), description.get('free_slots', 0)
    r, c = rounds(k, u_h), covered_rounds(slots, n0, k, u_h)
    return {'target': u_h, 'rounds': r, 'covered': c, 'ratio': time_ratio(k, c, u_h)}


def audit(cluster: Obj, description: Optional[Obj] = None) -> Obj:
    """Every seam's verdict on the cluster's objects and the description; InputError on a missing field."""
    description = description or {}
    return {'signal': signal(cluster), 'time': time_scale(cluster, description), 'state': state(description),
            'assumption': assumption(cluster), 'order': order(cluster, description)}


def _verdict(ratio: Optional[float], at_one: bool = False) -> str:
    if ratio is None:
        return 'not tested'
    return 'binds' if (ratio >= 1.0 if at_one else ratio > 1.0) else 'holds'


def render(report: Obj) -> str:
    """The report as one line per seam."""
    lines = []
    for s in report['signal']:
        lines.append('signal      %-28s ratio %.3f  %s  (target %.2f on %s, with a vertical autoscaler)' % (
            s['workload'], s['ratio'], _verdict(s['ratio']), s['target'], s['resource']))
    if not report['signal']:
        lines.append('signal      no workload with both autoscalers on one resource')
    t = report['time']
    lines.append('time scale  ' + ('ratio %.3f  %s  (%d rounds, %d covered)' % (t['ratio'], _verdict(t['ratio']), t['rounds'], t['covered']) if t else 'not tested: no surge described'))
    s = report['state']
    lines.append('state       ' + ('ratio %.3f  %s  (%d informers)' % (s['ratio'], _verdict(s['ratio']), s['informers']) if s else 'not tested: no informers described'))
    a = report['assumption']
    lines.append('assumption  ratio %.3f  %s  cycles %s; stranded by a full restart: %s' % (
        a['ratio'], _verdict(a['ratio'], at_one=True), a['cycles'] or 'none', ', '.join(a['stranded']) or 'none'))
    o = report['order']
    lines.append('order       ratio %.3f  %s  (%d passes; order %s)' % (o['ratio'], _verdict(o['ratio']), o['passes'], ', '.join(o['sequence'])))
    if o['readers_never_reinvoked']:
        lines.append('            readers that are never called again: %s' % ', '.join(o['readers_never_reinvoked']))
    if o['writers_not_found']:
        lines.append('            described writers not found among the webhooks: %s' % ', '.join(o['writers_not_found']))
    return '\n'.join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cluster')
    ap.add_argument('--description')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    with open(args.cluster, encoding='utf-8') as f:
        cluster = json.load(f)
    description = {}
    if args.description:
        with open(args.description, encoding='utf-8') as f:
            description = json.load(f)
    try:
        report = audit(cluster, description)
    except InputError as e:
        print('seam_audit: %s' % e, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, default=list) if args.json else render(report))
    return 0


if __name__ == '__main__':
    sys.exit(main())
