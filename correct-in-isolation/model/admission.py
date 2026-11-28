"""A chain of mutating admission webhooks under the documented reinvocation contract.

Contract (admissionregistration/v1 API, reinvocationPolicy; Dynamic Admission Control page):
webhooks run in no stable order; with IfNeeded, a webhook "will be called at least one
additional time ... if the object being admitted is modified by other admission plugins after
the initial webhook call", and "if additional invocations result in further modifications to
the object, webhooks are not guaranteed to be invoked again". The apiserver's reinvoker calls
the chain a second time and returns. passes = 2 is that contract; passes = 1 is the weaker
"may be called again" wording; larger values show what the contract does not provide.

An object is a pod-like value: containers (name, image, pull policy, capabilities), labels and
annotations, all immutable so that outcomes can be compared and counted.
"""
import hashlib
import itertools


def pod(containers=(('app', 'registry/app:1', None, frozenset()),), labels=(), annotations=()):
    """A pod-like object, (containers, labels, annotations), immutable so outcomes can be compared: containers as
    (name, image, pull policy or None, frozenset of capabilities), labels as 'key=value' strings, annotations as
    (key, value) pairs, sorted. The default is one application container with no labels or annotations."""
    return (tuple(containers), frozenset(labels), tuple(sorted(annotations)))


def label(obj):
    """Adds the label team=core. Idempotent; touches nothing another webhook reads."""
    c, labels, a = obj
    return (c, labels | {'team=core'}, a)


def sidecar(obj):
    """Adds a proxy container if there is none. Idempotent and inflationary."""
    c, labels, a = obj
    if any(x[0] == 'proxy' for x in c):
        return obj
    return (c + (('proxy', 'registry/proxy:2', None, frozenset()),), labels, a)


def pull_policy(obj):
    """Sets pull policy Always on every container that has none, as AlwaysPullImages does for every
    container. Idempotent and inflationary; a container added later is missed."""
    c, labels, a = obj
    return (tuple((n, i, p or 'Always', k) for n, i, p, k in c), labels, a)


def digest(obj):
    """Pins every image tag to a digest. Idempotent and inflationary."""
    c, labels, a = obj
    def pin(i):
        return i if '@' in i else i + '@sha256:' + hashlib.sha256(i.encode()).hexdigest()[:8]
    return (tuple((n, pin(i), p, k) for n, i, p, k in c), labels, a)


def signer(obj):
    """Writes an annotation hashing the images it sees. Idempotent; correct only if no image
    changes after it runs."""
    c, labels, a = obj
    sig = hashlib.sha256('|'.join(i for _, i, _, _ in c).encode()).hexdigest()[:8]
    rest = tuple(x for x in a if x[0] != 'signature')
    return (c, labels, tuple(sorted(rest + (('signature', sig),))))


def drop_capabilities(obj):
    """Policy: removes every capability from every container. Idempotent; removes what others add."""
    c, labels, a = obj
    return (tuple((n, i, p, frozenset()) for n, i, p, _ in c), labels, a)


def mesh_init(obj):
    """Adds a mesh init container needing NET_ADMIN, and restores the capability if it is
    missing. Idempotent; adds what the policy removes."""
    c, labels, a = obj
    if not any(x[0] == 'mesh-init' for x in c):
        c = c + (('mesh-init', 'registry/mesh-init:1', None, frozenset({'NET_ADMIN'})),)
    c = tuple((n, i, p, k | {'NET_ADMIN'}) if n == 'mesh-init' else (n, i, p, k) for n, i, p, k in c)
    return (c, labels, a)


def matches(w, obj):
    """Whether webhook w's match rules (an object selector or match conditions) select obj. A
    webhook without a match rule matches every object."""
    return getattr(w, 'match', None) is None or w.match(obj)


def _run(obj, order, reinvoke_if_needed=True, passes=2, builtins=()):
    """The rounds of admit_trace, recording each call as (round, index, webhook, before, after)."""
    last_seen = {}
    calls = []
    for r in range(passes):
        if r > 0 and not any(rr == r - 1 and b != a for rr, _, _, b, a in calls):
            break
        for b in builtins:
            obj = b(obj)
        for i, w in enumerate(order):
            if not matches(w, obj):
                continue
            if r > 0 and not (reinvoke_if_needed and not getattr(w, 'never', False) and w in last_seen and last_seen[w] != obj):
                continue
            out = w(obj)
            calls.append((r, i, w.__name__, obj, out))
            obj = out
            last_seen[w] = obj
    return obj, calls


def admit_trace(obj, order, reinvoke_if_needed=True, passes=2, builtins=()):
    """The admitted object after `passes` rounds over `order`, and the audit trace: one entry
    (round, index, webhook, mutated) per call, as the mutation.webhook.admission.k8s.io/round_r_index_i
    annotation records it. A webhook's match rules are checked against the object as it stands
    when its turn comes, in every round. A webhook not called in round 0 is never called later
    (the dispatcher's comment: "during reinvocation, a webhook will not be called for the first
    time"); in a later round a webhook is called again only if it opts in (IfNeeded) and the
    object changed after its last call. builtins are the in-tree mutating plugins, which the API
    server runs before every webhook in each round; a later round runs only if a webhook changed
    the object in the round before (reinvocation.go: "Calling admit a second time will reinvoke all
    in-tree plugins"), and the trace, like the audit annotations, records webhooks only. A webhook
    with the attribute never = True has reinvocationPolicy Never on its own configuration and is
    called at most once, whatever reinvoke_if_needed says for the others."""
    obj, calls = _run(obj, order, reinvoke_if_needed, passes, builtins)
    return obj, [(r, i, name, before != after) for r, i, name, before, after in calls]


def changed_fields(before, after):
    """The fields a call changed, as the paths of its JSON patch would name them: a container's
    image, pull policy or capabilities (containers keyed by name, so that an insertion does not
    shift the others' paths), a container added or removed, a label, an annotation."""
    out = set()
    cb, ca = {x[0]: x for x in before[0]}, {x[0]: x for x in after[0]}
    for n in set(cb) | set(ca):
        if n not in cb or n not in ca:
            out.add(('container', n))
            continue
        for k, attr in ((1, 'image'), (2, 'pull'), (3, 'caps')):
            if cb[n][k] != ca[n][k]:
                out.add(('container', n, attr))
    for x in before[1] ^ after[1]:
        out.add(('label', x.split('=')[0]))
    ab, aa = dict(before[2]), dict(after[2])
    for k in set(ab) | set(aa):
        if ab.get(k) != aa.get(k):
            out.add(('annotation', k))
    return frozenset(out)


def admit_patches(obj, order, reinvoke_if_needed=True, passes=2, builtins=()):
    """admit_trace at the Request audit level: each call's entry carries the fields its patch
    changed (patch.webhook.admission.k8s.io/round_r_index_i) instead of the mutated flag."""
    obj, calls = _run(obj, order, reinvoke_if_needed, passes, builtins)
    return obj, [(r, i, name, changed_fields(before, after)) for r, i, name, before, after in calls]


def classify_patches(trail):
    """What the patch trail of one admission says, field by field and webhook by webhook. A field
    patched by two or more webhooks is 'contested': two owners wrote it, a conflict or a deliberate
    override. A webhook that patched in round 1 only fields no other webhook wrote acted on input
    that arrived after its first call: 'late input', the mark of an enabling link in the wrong
    order. Returns (contested: {field: writers}, late: {webhook}). A webhook its match rules
    skipped leaves no entry at all, so a match link is absent from both."""
    writers = {}
    for _, _, name, fields in trail:
        for f in fields:
            writers.setdefault(f, set()).add(name)
    contested = {f: w for f, w in writers.items() if len(w) > 1}
    late = {name for r, _, name, fields in trail if r > 0 and fields and not any(f in contested for f in fields)}
    return contested, late


def writer(name, value, never=False):
    """A webhook that sets the annotation owner to its own value: one side of a conflict on one
    field. never marks its configuration reinvocationPolicy Never."""
    def w(obj):
        c, labels, a = obj
        rest = tuple(x for x in a if x[0] != 'owner')
        return (c, labels, tuple(sorted(rest + (('owner', value),))))
    w.__name__ = name
    w.never = never
    return w


def mesh_label(obj):
    """Defaulting webhook: sets the label mesh=on, the label a sidecar injector selects on.
    Idempotent; touches nothing another webhook reads, but changes what one matches."""
    c, labels, a = obj
    return (c, labels | {'mesh=on'}, a)


def injector(obj):
    """Sidecar injector selected by the label mesh=on (an objectSelector): adds a proxy container
    if there is none. Idempotent and inflationary where it is called."""
    return sidecar(obj)


injector.match = lambda obj: 'mesh=on' in obj[1]


def admit(obj, order, reinvoke_if_needed=True, passes=2, builtins=()):
    """The admitted object after `passes` rounds over `order` (see admit_trace)."""
    return admit_trace(obj, order, reinvoke_if_needed, passes, builtins)[0]


def final_round_clean(trace, passes=2):
    """The audit check: no webhook mutated the object in the last round the contract runs."""
    return not any(r == passes - 1 and mutated for r, _, _, mutated in trace)


def readmission_clean(obj, order):
    """The second-admission check: a dry-run create of the admitted object, in any order, with
    no webhook mutating it. One round decides it, whatever the reinvocation policy."""
    return not any(mutated for _, _, _, mutated in admit_trace(obj, order, passes=1)[1])


def readmission_unchanged(obj, order):
    """The weaker check a cluster operator might run instead: the object a dry-run second admission
    returns, compared field by field with the admitted one. It agrees with readmission_clean unless
    two webhooks write one field, where a later writer can restore what an earlier one changed."""
    return admit(obj, order, passes=1) == obj


def iterate_admission(obj, order, max_admissions=50):
    """An orchestrator that iterates admission to a common fixed point: it submits the object as a dry run
    (the contract's two passes over `order`), feeds the admitted object back in, and stops once every
    webhook that matches the object leaves it unchanged. It also stops when an admission returns an object
    it has already seen without reaching a common fixed point, as conflicting writers make it do. Returns
    {'object', 'admissions', 'calls', 'fixed_point', 'cycle'}; calls counts webhook calls over every
    admission, the orchestrator's price in latency."""
    seen, calls = set(), 0
    for n in range(1, max_admissions + 1):
        out, trace = admit_trace(obj, order)
        calls += len(trace)
        if all(w(out) == out for w in order if matches(w, out)):
            return {'object': out, 'admissions': n, 'calls': calls, 'fixed_point': True, 'cycle': False}
        if out in seen:
            return {'object': out, 'admissions': n, 'calls': calls, 'fixed_point': False, 'cycle': True}
        seen.add(out)
        obj = out
    return {'object': obj, 'admissions': max_admissions, 'calls': calls, 'fixed_point': False, 'cycle': False}


def orchestrate(obj, order, max_admissions=50):
    """The orchestrator of iterate_admission as it must run without knowing the webhooks: it stops when a dry
    run returns the object unchanged, and then creates it for real with one more admission. With webhooks that
    only add, an unchanged object is a common fixed point, since every matching webhook was called on it and
    added nothing; conflicting writers can hand an object back unchanged that one of them would change.
    Returns {'object', 'dry_runs', 'calls', 'fixed_point', 'created'}: dry_runs counts the confirming run,
    calls every webhook call with the real creation's, and fixed_point whether the created object is a
    common fixed point, which the orchestrator itself cannot see."""
    calls = 0
    for n in range(1, max_admissions + 1):
        out, trace = admit_trace(obj, order)
        calls += len(trace)
        if out == obj:
            calls += len(admit_trace(out, order)[1])
            fixed = all(w(out) == out for w in order if matches(w, out))
            return {'object': out, 'dry_runs': n, 'calls': calls, 'fixed_point': fixed, 'created': True}
        obj = out
    return {'object': obj, 'dry_runs': max_admissions, 'calls': calls, 'fixed_point': False, 'created': False}


def outcomes(webhooks, start=None, reinvoke_if_needed=True, passes=2):
    """Distinct admitted objects over every order of the webhooks, and whether each is a common
    fixed point (every webhook that matches it leaves it unchanged)."""
    start = start if start is not None else pod()
    seen = {admit(start, order, reinvoke_if_needed, passes) for order in itertools.permutations(webhooks)}
    return {o: all(w(o) == o for w in webhooks if matches(w, o)) for o in seen}


def chain(depth):
    """depth + 1 webhooks in an enabling chain: the first adds annotation level0, and webhook i
    adds level<i> once level<i-1> is present. Idempotent and inflationary; webhook i can act
    only after webhook i - 1 has."""
    def make(i):
        def w(obj):
            c, labels, a = obj
            keys = {k for k, _ in a}
            if 'level%d' % i in keys or (i > 0 and 'level%d' % (i - 1) not in keys):
                return obj
            return (c, labels, tuple(sorted(a + (('level%d' % i, 'set'),))))
        w.__name__ = 'level%d' % i
        return w
    return [make(i) for i in range(depth + 1)]


def typed_chain(kinds):
    """len(kinds) + 1 webhooks in a chain. Webhook i adds annotation level<i>; link i (between
    webhooks i and i + 1) is 'value' if webhook i + 1 reads level<i> from the object and acts only
    once it is present, or 'match' if webhook i + 1 is selected only once level<i> is present (a
    match condition on the object). Value links are what reinvocation repairs; match links it
    does not."""
    def make(i):
        need = None if i == 0 else 'level%d' % (i - 1)
        value = i > 0 and kinds[i - 1] == 'value'

        def w(obj):
            c, labels, a = obj
            keys = {k for k, _ in a}
            if 'level%d' % i in keys or (value and need not in keys):
                return obj
            return (c, labels, tuple(sorted(a + (('level%d' % i, 'set'),))))
        w.__name__ = 'level%d' % i
        if i > 0 and not value:
            w.match = lambda obj: need in {k for k, _ in obj[2]}
        return w
    return [make(i) for i in range(len(kinds) + 1)]


def fact_webhooks(facts, names=()):
    """Webhooks that each write facts, as annotations, once the facts they need are present; facts
    maps each fact to (writer, prerequisites). A webhook adds, in one call, every fact it writes
    whose prerequisites are present, repeating within the call until it adds nothing more. Each is
    idempotent, inflationary and monotone: the general form of a chain of value links. names adds
    webhooks that write nothing."""
    writers = sorted({w for w, _ in facts.values()} | set(names))

    def make(name):
        mine = {f: pre for f, (w, pre) in facts.items() if w == name}

        def w(obj):
            c, labels, a = obj
            keys = {k for k, _ in a}
            added = True
            while added:
                added = False
                for f, pre in sorted(mine.items()):
                    if f not in keys and pre <= keys:
                        keys.add(f)
                        added = True
            if keys == {k for k, _ in a}:
                return obj
            new = tuple(sorted(set(a) | {(k, 'set') for k in keys - {k for k, _ in a}}))
            return (c, labels, new)
        w.__name__ = name
        return w
    return {name: make(name) for name in writers}
