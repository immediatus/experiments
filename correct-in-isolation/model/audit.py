"""Whole-system tests for the seams, and the pairwise tests they replace (Part 6).

A pairwise test looks at two mechanisms with the rest left out. The whole-system tests:
- signal: Bristol's relative gain array of the full n x n gain matrix (one inversion);
- assumption: strongly connected components of the start-time graph (Tarjan, linear time);
- order: the longest enabling chain among mutators, against the passes the contract gives,
  with a cycle of enabling (one mutator undoing another) reported as having no fixed point.
"""
import itertools


def inverse(m):
    """Inverse of a square matrix by Gauss-Jordan elimination with partial pivoting; None if
    singular."""
    n = len(m)
    a = [list(map(float, row)) + [float(i == j) for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-12:
            return None
        a[c], a[p] = a[p], a[c]
        pivot = a[c][c]
        a[c] = [x / pivot for x in a[c]]
        for r in range(n):
            if r != c:
                f = a[r][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [row[n:] for row in a]


def relative_gains(g):
    """Bristol's relative gain array of an n x n gain matrix, g elementwise times the transpose
    of its inverse; None when g is singular."""
    inv = inverse(g)
    if inv is None:
        return None
    n = len(g)
    return [[g[r][c] * inv[c][r] for c in range(n)] for r in range(n)]


def pairwise_relative_gains(g):
    """The (0, 0) relative gain of every 2 x 2 sub-matrix: the pairwise reading, with every other
    loop left open."""
    out = {}
    for i, j in itertools.combinations(range(len(g)), 2):
        sub = [[g[i][i], g[i][j]], [g[j][i], g[j][j]]]
        rga = relative_gains(sub)
        out[(i, j)] = None if rga is None else rga[0][0]
    return out


def cyclic_components(needs):
    """Sets of components that need each other to start, directly or through others: the
    strongly connected components of the start-time graph that contain a cycle (Tarjan 1972)."""
    nodes = sorted(set(needs) | {d for ds in needs.values() for d in ds})
    index, low, stack, on, found, counter = {}, {}, [], set(), [], [0]

    def visit(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(needs.get(v, ())):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = set()
            while True:
                w = stack.pop()
                on.discard(w)
                comp.add(w)
                if w == v:
                    break
            if len(comp) > 1 or v in needs.get(v, ()):
                found.append(comp)

    for v in nodes:
        if v not in index:
            visit(v)
    return found


def enabling_depth(enables):
    """Longest chain in the enabling graph (mutator -> mutators that act on what it writes), or
    None if the graph has a cycle, where some mutator undoes another and no common fixed point
    need exist."""
    if cyclic_components(enables):
        return None
    memo = {}

    def depth(v):
        if v not in memo:
            memo[v] = max((1 + depth(w) for w in enables.get(v, ())), default=0)
        return memo[v]
    return max((depth(v) for v in set(enables) | {w for ws in enables.values() for w in ws}), default=0)


def config_order(configs):
    """The order the API server calls mutating webhooks in: configurations sorted by name, "to have
    a deterministic order", and the webhooks of each in the order the configuration lists them.
    configs maps a configuration name to its list of webhook names."""
    return [w for name in sorted(configs) for w in configs[name]]


def min_feedback_arc_set(needs):
    """A smallest set of start-time edges (a, b), a needing b, whose removal leaves no cycle: the backward
    edges of the best linear order, found by trying every order (exact for the handful of components an
    admission audit has; the problem is NP-hard in general, Karp 1972)."""
    nodes = sorted(set(needs) | {b for bs in needs.values() for b in bs})
    best = None
    for order in itertools.permutations(nodes):
        pos = {v: i for i, v in enumerate(order)}
        back = {(a, b) for a in needs for b in needs[a] if pos[b] >= pos[a]}
        if best is None or len(back) < len(best):
            best = back
    return best or set()


def min_feedback_vertex_set(needs):
    """A smallest set of components whose removal leaves no start-time cycle, by trying sets in order of
    size (exact for small graphs; NP-hard in general, Karp 1972)."""
    nodes = sorted(set(needs) | {b for bs in needs.values() for b in bs})
    for r in range(len(nodes) + 1):
        for sub in itertools.combinations(nodes, r):
            rest = {a: {b for b in needs.get(a, ()) if b not in sub} for a in nodes if a not in sub}
            if not cyclic_components(rest):
                return set(sub)
    return set(nodes)


def admission_order(webhook_configs, policies, builtins=()):
    """The order of one mutating pass in the current kube-apiserver (pkg/kubeapiserver/options/plugins.go,
    AllOrderedPlugins): the built-in mutating plugins first, then the MutatingAdmissionPolicy plugin, then
    the MutatingAdmissionWebhook plugin, whose webhooks run sorted by configuration name. Policies are
    taken in name order here; the contract promises no order among them either."""
    return list(builtins) + sorted(policies) + sorted(webhook_configs)


# Shipped defaults of the surveyed projects (Parts 4 and 5), each installed in its own namespace.
# fail_closed: the webhook that sees pods has failurePolicy Fail; scope 'all' matches every pod outside
# `excludes`, 'opt-in' only pods or namespaces carrying a label nobody sets by default, 'none' no pods;
# skips_own: the webhook's selectors leave its own pods out. Kyverno is taken with a policy on Pods,
# without which it registers no resource webhook for them.
SURVEY_DEFAULTS = {
    'kyverno': {'ns': 'kyverno', 'fail_closed': True, 'scope': 'all', 'excludes': frozenset({'kube-system', 'kyverno'}), 'skips_own': True},
    'consul': {'ns': 'consul', 'fail_closed': True, 'scope': 'all',
               'excludes': frozenset({'kube-system', 'local-path-storage', 'openebs', 'gmp-system', 'gke-managed-cim'}), 'skips_own': True},
    'istio': {'ns': 'istio-system', 'fail_closed': True, 'scope': 'opt-in', 'excludes': frozenset(), 'skips_own': True},
    'kuma': {'ns': 'kuma-system', 'fail_closed': True, 'scope': 'opt-in', 'excludes': frozenset(), 'skips_own': True},
    'azure-workload-identity': {'ns': 'azure-workload-identity-system', 'fail_closed': True, 'scope': 'opt-in', 'excludes': frozenset(), 'skips_own': True},
    'cert-manager': {'ns': 'cert-manager', 'fail_closed': True, 'scope': 'none', 'excludes': frozenset(), 'skips_own': True},
    'gatekeeper': {'ns': 'gatekeeper-system', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset({'gatekeeper-system'}), 'skips_own': True},
    'linkerd': {'ns': 'linkerd', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': True},
    'vault': {'ns': 'vault', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': True},
    'dapr': {'ns': 'dapr-system', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': False},
    'opentelemetry-operator': {'ns': 'opentelemetry-operator-system', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': False},
    'aws-load-balancer-controller': {'ns': 'kube-system', 'fail_closed': False, 'scope': 'opt-in', 'excludes': frozenset(), 'skips_own': True},
    'eks-pod-identity-webhook': {'ns': 'default', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': False},
    'vertical-pod-autoscaler': {'ns': 'kube-system', 'fail_closed': False, 'scope': 'all', 'excludes': frozenset(), 'skips_own': False},
    'coredns': {'ns': 'kube-system', 'fail_closed': False, 'scope': 'none', 'excludes': frozenset(), 'skips_own': True},
}


def default_start_graph(components):
    """Start-time edges from shipped defaults: component c needs webhook w when w fails closed, matches
    every pod outside its excluded namespaces, c's namespace is not excluded, and c is not w itself
    with selectors that skip its own pods. Returns {component: set of components it needs}."""
    needs = {c: set() for c in components}
    for w, wd in components.items():
        if not wd['fail_closed'] or wd['scope'] != 'all':
            continue
        for c, cd in components.items():
            if cd['ns'] in wd['excludes'] or (c == w and wd['skips_own']):
                continue
            needs[c].add(w)
    return needs
