"""Build the stored count files from Stanford HELM's public per-question results. Run once, by hand:

    python3 data/fetch_helm.py lite       -> data/model_errors.json        (HELM Lite, MMLU, five subjects)
    python3 data/fetch_helm.py gpqa       -> data/model_errors_gpqa.json   (HELM Capabilities, GPQA main)
    python3 data/fetch_helm.py mmlu_pro   -> data/model_errors_mmlu_pro.json (HELM Capabilities, MMLU-Pro)

An optional second argument writes elsewhere. For each source it lists every release in the public bucket, keeps
the models that answered every subject, takes each model's latest run per subject, reads each question's score
from the run's display_predictions.json, aligns the models on the questions all of them answered, and stores per
model its accuracy and per pair of models the four counts (both right, only one right, both wrong), overall and
within 5 and 10 strata of question difficulty measured by the other models. The stored files hold no question
text, no answers and no per-question vectors: HELM states no licence for these outputs. reproduce.py never
touches the network; it reads the stored files. A model whose results file the bucket does not serve is skipped
and named in the fetch log.
"""
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'model')]

from correlation import aligned, build_record

BUCKET = 'https://storage.googleapis.com/crfm-helm-public'
STRATA = (5, 10)
SOURCES = {
    'lite': dict(suite='lite', prefix='mmlu', score='exact_match', out='model_errors.json',
                 subjects=('abstract_algebra', 'college_chemistry', 'computer_security', 'econometrics',
                           'us_foreign_policy'),
                 pattern=r'mmlu:subject=([^,]+),method=multiple_choice_joint,model=([^,/]+)/$',
                 label='Stanford HELM Lite, MMLU (%s), exact match'),
    'gpqa': dict(suite='capabilities', prefix='gpqa', score='chain_of_thought_correctness',
                 out='model_errors_gpqa.json', subjects=('gpqa_main',),
                 pattern=r'gpqa:subset=([^,]+),use_chain_of_thought=true,use_few_shot=false,model=([^,/]+)/$',
                 label='Stanford HELM Capabilities, GPQA (%s), chain-of-thought correctness'),
    'mmlu_pro': dict(suite='capabilities', prefix='mmlu_pro', score='chain_of_thought_correctness',
                     out='model_errors_mmlu_pro.json', subjects=('all',),
                     pattern=r'mmlu_pro:subset=([^,]+),use_chain_of_thought=true,use_few_shot=false,model=([^,/]+)/$',
                     label='Stanford HELM Capabilities, MMLU-Pro (%s), chain-of-thought correctness'),
}


def _get(url: str) -> bytes:
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except OSError:
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError('could not fetch %s' % url)


def _version_key(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip('v').split('.'))


def runs(src: dict) -> dict[tuple[str, str], str]:
    """{(model, subject): run prefix} for the latest release that ran it."""
    root = '%s/benchmark_output/runs/' % src['suite']
    listing = _get('%s/?prefix=%s&delimiter=/' % (BUCKET, root)).decode('utf-8')
    versions = [p.split('/')[-2] for p in re.findall(r'<Prefix>([^<]+)</Prefix>', listing)[1:]]
    found = {}
    for v in sorted(versions, key=_version_key):
        text = _get('%s/?prefix=%s%s/%s&delimiter=/&max-keys=1000' % (BUCKET, root, v, src['prefix'])).decode('utf-8')
        for prefix in re.findall(r'<Prefix>([^<]+)</Prefix>', text)[1:]:
            m = re.search(src['pattern'], prefix)
            if m and m.group(1) in src['subjects']:
                found[(m.group(2), m.group(1))] = prefix
    return found


def main(argv: list[str]) -> None:
    src = SOURCES[argv[0] if argv else 'lite']
    found = runs(src)
    models = sorted({m for m, _ in found if all((m, s) in found for s in src['subjects'])})
    errors = {}
    for i, model in enumerate(models):
        scores = {}
        try:
            for subject in src['subjects']:
                rows = json.loads(_get('%s/%sdisplay_predictions.json' % (BUCKET, found[(model, subject)])).decode('utf-8'))
                for row in rows:
                    if row.get('train_trial_index', 0) == 0 and src['score'] in row.get('stats', {}):
                        scores['%s:%s' % (subject, row['instance_id'])] = row['stats'][src['score']] >= 1.0
        except RuntimeError as err:
            print('%3d/%d %s skipped: %s' % (i + 1, len(models), model, err), flush=True)
            continue
        errors[model] = scores
        print('%3d/%d %s %d questions' % (i + 1, len(models), model, len(scores)), flush=True)
    record = build_record((src['label'] + ', latest release per model and subject; %s')
                          % (', '.join(src['subjects']), BUCKET), 'unstated: only counts are stored', aligned(errors),
                          strata=STRATA)
    out = argv[1] if len(argv) > 1 else os.path.join(HERE, src['out'])
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(record, f, separators=(',', ':'), sort_keys=True)
    print('wrote %s: %d models, %d questions' % (out, len(record['models']), record['items']))


if __name__ == '__main__':
    main(sys.argv[1:])
