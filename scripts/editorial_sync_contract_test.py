#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / '.github' / 'workflows' / 'cloudflare-editorial-sync.yml').read_text(encoding='utf-8')

required = {
    'manual input is exposed': 'INPUT_CYCLES: ${{ github.event.inputs.cycles }}',
    'dispatch uses expanded max': '--max-cycles "$MAX"',
    'runtime loop uses dispatch output': 'INPUT_CYCLES: ${{ steps.dispatch.outputs.cycles }}',
    'loop respects max': 'for i in $(seq 1 "$MAX"); do',
}
errors = [label for label, needle in required.items() if needle not in workflow]

correct = 'MAX="${INPUT_CYCLES:-3}"'
wrong = "MAX='${INPUT_CYCLES:-3}'"
if workflow.count(correct) != 2:
    errors.append(f'expected exactly 2 safe MAX expansions, found {workflow.count(correct)}')
if wrong in workflow:
    errors.append('literal single-quoted MAX expansion reintroduced')

# Both the cheap dispatch decision and the paid execution loop must clamp identically.
clamp = 'case "$MAX" in 1|2|3) ;; *) MAX=3 ;; esac'
if workflow.count(clamp) != 2:
    errors.append(f'expected exactly 2 identical cycle clamps, found {workflow.count(clamp)}')

if errors:
    raise SystemExit('EDITORIAL SYNC CONTRACT: FAIL: ' + '; '.join(errors))
print('EDITORIAL SYNC CONTRACT: PASS')
