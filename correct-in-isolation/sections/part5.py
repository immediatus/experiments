"""Sections of Part 5, a shared order: T15, T16, T50, T51, T52, T71, T72, T76, T77, T82, T83, T84, T85, T102."""
import itertools
import math

from admission import (
    admit,
    admit_patches,
    admit_trace,
    chain,
    classify_patches,
    digest,
    drop_capabilities,
    final_round_clean,
    injector,
    iterate_admission,
    label,
    matches,
    mesh_init,
    mesh_label,
    orchestrate,
    outcomes,
    pod,
    pull_policy,
    readmission_clean,
    sidecar,
    signer,
    typed_chain,
    writer,
)
from admission import chain as value_chain
from audit import admission_order, config_order
from formulas import converged_share, fact_passes, match_ceiling, mix_share, mixed_within, never_share, time_to_mixed, typed_chain_share


def t15():
    print('T15 mutating webhooks over every order (1 pass: the weaker reading; 2: the reinvocation contract; '
          '3: beyond it): scenario | reinvocation | passes | admitted objects | of which every webhook leaves '
          'unchanged')
    scenarios = (('S1 label and sidecar (commute)', [label, sidecar]),
                 ('S2 sidecar and pull policy (one enabling step)', [sidecar, pull_policy]),
                 ('S3 sidecar, digest pin, signer (two enabling steps)', [sidecar, digest, signer]),
                 ('S4 capability policy and mesh init (conflict)', [drop_capabilities, mesh_init]))
    for name, ws in scenarios:
        for policy, flag in (('Never', False), ('IfNeeded', True)):
            for passes in (1, 2, 3):
                o = outcomes(ws, reinvoke_if_needed=flag, passes=passes)
                print('  %s | %s | %d | %d | %d' % (name, policy, passes, len(o), sum(o.values())))


def t16():
    print('T16 enabling chain of n webhooks (depth n - 1), all IfNeeded: n | passes the worst order needs | '
          'share of orders converged in 2 passes (closed form) | (enumerated) | share converged in one pass, '
          'as under Never, 1/n! | share for a chain of match links at any number of passes, 1/n!')
    for n in (2, 3, 4, 5, 6):
        ws = chain(n - 1)
        full = admit(pod(), ws, passes=1)
        worst = min(p for p in range(1, n + 2) if admit(pod(), list(reversed(ws)), passes=p) == full)
        orders = list(itertools.permutations(ws))
        hits = sum(admit(pod(), o, passes=2) == full for o in orders)
        print('  %d | %d | %.4f | %.4f | %.4f | %.4f' % (n, worst, converged_share(n, 2), hits / len(orders), converged_share(n, 1),
                                               match_ceiling(('match',) * (n - 1))))


ORDER_SCENARIOS = (('S1 label and sidecar (commute)', [label, sidecar]),
                   ('S2 sidecar and pull policy (one enabling step)', [sidecar, pull_policy]),
                   ('S3 sidecar, digest pin, signer (two enabling steps)', [sidecar, digest, signer]),
                   ('S4 capability policy and mesh init (conflict)', [drop_capabilities, mesh_init]),
                   ('S5 mesh label and an injector selected by it (a match step)', [mesh_label, injector]),
                   ('S6 mesh label, injector, pull policy (a match step, then a value step)',
                    [mesh_label, injector, pull_policy]))


def t50():
    print('T50 a link through a match rule, over every order (as T15; a webhook skipped in round 0 is never '
          'called later): scenario | reinvocation | passes | admitted objects | of which every matching '
          'webhook leaves unchanged')
    for name, ws in ORDER_SCENARIOS[4:]:
        for policy, flag in (('Never', False), ('IfNeeded', True)):
            for passes in (1, 2, 3, 6):
                o = outcomes(ws, reinvoke_if_needed=flag, passes=passes)
                print('  %s | %s | %d | %d | %d' % (name, policy, passes, len(o), sum(o.values())))


def t51():
    print('T51 chains with value and match links, all IfNeeded, every order equally likely: links in chain '
          'order | share converged within 2 rounds, closed | enumerated | share converged at any number of '
          'rounds, closed | 1 / (m + 2)!, m the last match link')
    for kinds in (('value', 'value'), ('match', 'value'), ('value', 'match'), ('match', 'match'),
                  ('value', 'value', 'value'), ('match', 'value', 'value'), ('value', 'value', 'match'),
                  ('match', 'match', 'match')):
        ws = typed_chain(kinds)
        full = admit(pod(), ws, passes=1)
        orders = list(itertools.permutations(ws))
        hits = sum(admit(pod(), o, passes=2) == full for o in orders)
        print('  %s | %.4f | %.4f | %.4f | %.4f' % (', '.join(kinds), typed_chain_share(kinds, 2), hits / len(orders),
                                                   typed_chain_share(kinds, len(kinds) + 1), match_ceiling(kinds)))


def t52():
    print('T52 the two cluster checks under the contract (all IfNeeded, two rounds), over every order: '
          'scenario | orders | admitted object a common fixed point | final round clean | clean but not a '
          'fixed point | dirty but a fixed point | second admission clean | second admission disagrees with '
          'the fixed-point verdict')
    for name, ws in ORDER_SCENARIOS:
        rows = []
        for order in itertools.permutations(ws):
            obj, trace = admit_trace(pod(), order, passes=2)
            fp = all(w(obj) == obj for w in ws if matches(w, obj))
            clean = final_round_clean(trace, passes=2)
            again = all(readmission_clean(obj, o) for o in itertools.permutations(ws))
            rows.append((fp, clean, again))
        print('  %s | %d | %d | %d | %d | %d | %d | %d' % (
            name, len(rows), sum(f for f, _, _ in rows), sum(c for _, c, _ in rows),
            sum(c and not f for f, c, _ in rows), sum(f and not c for f, c, _ in rows),
            sum(a for _, _, a in rows), sum(a != f for f, _, a in rows)))


def t71():
    print('T71 two injectors at their chart defaults (Istio sidecar injector, reinvocationPolicy Never; Vault '
          'agent injector, no reinvocationPolicy, so Never): Vault release name | configuration names in the '
          "order the API server calls them | passes Istio needs to see Vault's agent container | under Never "
          "(one call each) | with Istio set to IfNeeded (the contract's two passes)")
    facts = {'agent container': ('vault', set()), 'agent seen by istio': ('istio', {'agent container'})}
    for release in ('vault', 'hashicorp-vault'):
        configs = {'istio-sidecar-injector': ['istio'], release + '-agent-injector-cfg': ['vault']}
        order = config_order(configs)
        need = fact_passes(order, facts)
        print('  %s | %s | %d | %s | %s' % (release, ', '.join(sorted(configs)), need, 'seen' if need <= 1 else 'not seen',
                                            'seen' if need <= 2 else 'not seen'))


def t72():
    print('T72 a mutating admission policy and a webhook with a value link between them, in the order the '
          'current API server runs one pass (built-in plugins, then policies, then webhooks): link | order of '
          'the pass | passes needed | under Never | with the later one IfNeeded | worst case the contract '
          'allows (no order promised)')
    order = admission_order(['injector'], ['policy'])
    for row, facts in (('the policy writes, the webhook reads', {'f': ('policy', set()), 'g': ('injector', {'f'})}),
                         ('the webhook writes, the policy reads', {'f': ('injector', set()), 'g': ('policy', {'f'})})):
        need = fact_passes(order, facts)
        worst = max(fact_passes(o, facts) for o in (['policy', 'injector'], ['injector', 'policy']))
        print('  %s | %s | %d | %s | %s | %d passes' % (row, ', '.join(order), need, 'converges' if need <= 1 else 'does not converge',
                                                       'converges' if need <= 2 else 'does not converge', worst))


def t76():
    print('T76 built-in mutating plugins in the chain: the API server runs them before every webhook in each '
          'pass, and runs a second pass whenever a webhook changed the object. Row "injector": webhooks | '
          'built-in | passes | the injected container\'s pull policy. Rows "chain": webhooks in a chain of '
          "value links that ends in a built-in | share of the webhooks' orders that converge within 2 passes "
          '(built-in first, Proposition 37) | 1/n! | share for a chain of the same length made of webhooks '
          'only, (2^m - m)/m!. Row "match": label webhook, injector selected by the label, AlwaysPullImages | '
          'orders converging within 2 passes, of 2')
    for passes in (1, 2):
        out = admit(pod(), [sidecar], builtins=[pull_policy], passes=passes)
        print('  injector | sidecar injector | AlwaysPullImages as pull_policy | %d | %s' % (passes, dict((c[0], c[2]) for c in out[0])['proxy']))
    for n in (1, 2, 3, 4):
        writers = ['w%d' % i for i in range(n)]
        facts = {'f0': ('w0', set())}
        for i in range(1, n):
            facts['f%d' % i] = ('w%d' % i, {'f%d' % (i - 1)})
        facts['fb'] = ('B', {'f%d' % (n - 1)})
        ok = sum(fact_passes(('B',) + o, facts) <= 2 for o in itertools.permutations(writers))
        m = n + 1
        print('  chain | %d | %.4f | %.4f | %.4f' % (n, ok / math.factorial(n), 1 / math.factorial(n), converged_share(m, 2)))
    full = admit(pod(), [mesh_label, injector], builtins=[pull_policy], passes=6)
    ok = 0
    for o in itertools.permutations([mesh_label, injector]):
        got = admit(pod(), list(o), builtins=[pull_policy], passes=2)
        ok += got == full
    print('  match | %d' % ok)


def t77():
    print('T77 a digest pin that reads the registry, applied to each Pod at creation: replicas | days between '
          'node failures per node (pods replaced at replicas / that rate) | days between tag moves | mean days '
          'until the ReplicaSet runs two images | probability it does within 30 days | within 90 days. Pinned '
          'once in the pod template, it runs one image until the next rollout')
    for n in (3, 10):
        r = n / 30.0
        for days in (1, 7, 30, 90):
            lam = 1.0 / days
            print('  %d | 30 | %d | %.1f | %.3f | %.3f' % (n, days, time_to_mixed(lam, r), mixed_within(lam, r, 30.0), mixed_within(lam, r, 90.0)))


def t82():
    print('T82 a chain of value links with a member whose configuration keeps the default reinvocationPolicy '
          'Never (Istio, Linkerd, Vault and Gatekeeper ship it), every other member IfNeeded, two passes, '
          'every order equally likely: members | position of the last Never member, the first counted as 0 | '
          'share of orders that converge, closed form [1 + sum over k from eta+1 to n-1 of (C(n,k) - 1)] / n! '
          '| enumerated over every order (to 5 members) | 1 / (eta + 1)!, the share of Proposition 30 with '
          'passes enough')
    for n in range(2, 7):
        for eta in range(n):
            enum = '-'
            if n <= 5:
                ws = value_chain(n - 1)
                if eta:
                    ws[eta].never = True
                full = admit(pod(), ws, passes=n + 2)
                orders = list(itertools.permutations(ws))
                enum = '%.4f' % (sum(admit(pod(), list(o)) == full for o in orders) / len(orders))
            print('  %d | %d | %.4f | %s | %.4f' % (n, eta, never_share(n, eta), enum, 1 / math.factorial(eta + 1)))


def t83():
    print('T83 a conflict: webhooks that each set one field to a value of their own, two passes, every order: '
          'policies of the writers | the writer whose value is admitted, as a share of orders | the last '
          'writer in the order, as a share of orders it is admitted in')
    for policies in (('IfNeeded', 'IfNeeded'), ('Never', 'Never'), ('IfNeeded', 'Never'), ('IfNeeded', 'IfNeeded', 'IfNeeded'), ('IfNeeded', 'Never', 'Never'), ('IfNeeded', 'IfNeeded', 'Never')):
        ws = [writer('w%d' % i, 'v%d' % i, never=(p == 'Never')) for i, p in enumerate(policies)]
        wins, last = {}, 0
        orders = list(itertools.permutations(ws))
        for o in orders:
            got = dict(admit(pod(), list(o))[2])['owner']
            wins[got] = wins.get(got, 0) + 1
            last += got == 'v' + o[-1].__name__[1:]
        share = ', '.join('w%s %s %.3f' % (k[1:], policies[int(k[1:])], wins.get(k, 0) / len(orders)) for k in sorted('v%d' % i for i in range(len(ws))))
        print('  %s | %s | %.3f' % (' + '.join(policies), share, last / len(orders)))


def t84():
    print('T84 the patch trail (Request audit level) over every order of each scenario, two passes, every '
          'webhook IfNeeded: scenario | orders | orders admitting a common fixed point | orders with a '
          'contested field | orders with late input | orders with neither that do not admit a common fixed '
          'point')
    scenarios = (('label + injector', [label, sidecar]), ('injector + pull policy', [sidecar, pull_policy]),
                 ('injector + digest + signer', [sidecar, digest, signer]), ('capability policy + mesh init', [drop_capabilities, mesh_init]),
                 ('label webhook + labeled injector', [mesh_label, injector]), ('label + labeled injector + pull policy', [mesh_label, injector, pull_policy]))
    for name, ws in scenarios:
        orders = list(itertools.permutations(ws))
        fixed = contested = late = silent_bad = 0
        for o in orders:
            obj, trail = admit_patches(pod(), list(o))
            ok = all(w(obj) == obj for w in ws if matches(w, obj))
            fields, late_hooks = classify_patches(trail)
            fixed += ok
            contested += bool(fields)
            late += bool(late_hooks)
            silent_bad += (not fields and not late_hooks and not ok)
        print('  %s | %d | %d | %d | %d | %d' % (name, len(orders), fixed, contested, late, silent_bad))


def t85():
    print("T85 the survey's mix: each member of a value chain after the first keeps reinvocationPolicy Never "
          'with probability q, two passes, every order equally likely: members | share of orders that converge '
          'with every member IfNeeded | expected share at q = 10/13, the share of the thirteen surveyed '
          'projects that keep Never | expected share at q = 1/2 | share with every member after the first Never')
    for n in range(2, 7):
        print('  %d | %.4f | %.4f | %.4f | %.4f' % (n, mix_share(n, 0.0), mix_share(n, 10 / 13), mix_share(n, 0.5), never_share(n, n - 1)))


def t102():
    print('T102 the passes a chain needs, and an orchestrator that iterates dry-run admission to a common '
          'fixed point. Rows "frontier": webhooks in an enabling chain of value links | passes allowed | share '
          'of orders that converge, Eulerian sum | mean passes needed, 1 + (n - 1)/2. Rows "orchestrate": '
          'chain | webhooks | orders | share converged after one admission | mean admissions | most admissions '
          '| mean webhook calls | mean webhook calls of one admission | as the orchestrator must run, stopping '
          'on a dry run that returns the object unchanged and then creating it: mean dry runs | most dry runs '
          '| mean admissions, the creation included | mean webhook calls, the creation included. Row '
          '"writers": two conflicting writers | admissions | fixed point | cycle detected. Row '
          '"writers-online": two conflicting writers, stopping on an unchanged object | dry runs | created | '
          'created object a common fixed point')
    for n in range(3, 8):
        for p in range(1, n + 1):
            print('  frontier | %d | %d | %.4f | %.1f' % (n, p, converged_share(n, p), 1 + (n - 1) / 2.0))
    for row, hooks in [('value', chain(n - 1)) for n in range(3, 8)] + [('match', typed_chain(['match'] * 3)), ('mixed', typed_chain(['value', 'match', 'value', 'match']))]:
        outs, first, online = [], [], []
        for order in itertools.permutations(hooks):
            outs.append(iterate_admission(pod(), list(order)))
            online.append(orchestrate(pod(), list(order)))
            first.append(len(admit_trace(pod(), list(order))[1]))
        one = sum(1 for o in outs if o['admissions'] == 1) / len(outs)
        print('  orchestrate | %s | %d | %d | %.4f | %.3f | %d | %.2f | %.2f | %.3f | %d | %.2f | %.2f' % (
            row, len(hooks), len(outs), one, sum(o['admissions'] for o in outs) / len(outs),
            max(o['admissions'] for o in outs), sum(o['calls'] for o in outs) / len(outs), sum(first) / len(first),
            sum(o['dry_runs'] for o in online) / len(online), max(o['dry_runs'] for o in online),
            sum(o['dry_runs'] + 1 for o in online) / len(online), sum(o['calls'] for o in online) / len(online)))
    out = iterate_admission(pod(), [writer('a', 'A'), writer('b', 'B')])
    print('  writers | 2 | %d | %s | %s' % (out['admissions'], out['fixed_point'], out['cycle']))
    out = orchestrate(pod(), [writer('a', 'A'), writer('b', 'B')])
    print('  writers-online | 2 | %d | %s | %s' % (out['dry_runs'], out['created'], out['fixed_point']))
