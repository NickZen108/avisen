#!/usr/bin/env python3
from pathlib import Path
s = (Path(__file__).resolve().parents[1] / "cloudflare/newsdesk/src/editorial.js").read_text(encoding="utf-8")
required = [
    'quote.length < 24 || !hay.includes(quote)',
    'overlap < Math.min(2, claimWords.length)',
    'claimNums.every((n) => quoteNums.has(n))',
    'support_passages',
    'match_verified: true',
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('CLAIM PASSAGE CONTRACT: FAIL: ' + ', '.join(missing))
print('CLAIM PASSAGE CONTRACT: PASS')
