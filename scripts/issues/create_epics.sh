#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import json
import subprocess
from pathlib import Path

manifest = Path('scripts/issues/epics.json')
if not manifest.exists():
    raise SystemExit('scripts/issues/epics.json not found')

data = json.loads(manifest.read_text(encoding='utf-8'))
repo = data.get('repo')
if not repo:
    raise SystemExit('repo missing in epics.json')

for epic in data.get('epics', []):
    title = epic['title']
    body = epic['body']
    labels = epic.get('labels', [])
    milestone = epic.get('milestone')

    cmd = [
        'gh', 'issue', 'create',
        '--repo', repo,
        '--title', title,
        '--body', body,
    ]
    if labels:
        cmd += ['--label', ','.join(labels)]
    if milestone:
        cmd += ['--milestone', milestone]

    print('Creating:', title)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)

    print(result.stdout.strip())
PY
