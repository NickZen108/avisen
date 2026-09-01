#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
s = p.read_text(encoding='utf-8')
old = '''  if (numericMaterialClaim(claim)) {
    const nums = String(claim?.claim || "").match(/\\d+(?:[.,]\\d+)?/g) || [];
    if (nums.length && !nums.some((n) => quote.includes(normalizedPassageText(n)))) return false;
  }
'''
new = '''  if (numericMaterialClaim(claim)) {
    const normalizeNumber = (value) => String(value || "").replace(/(?<=\\d)[.\\s](?=\\d{3}(?:\\D|$))/g, "").replace(",", ".");
    const claimNums = (String(claim?.claim || "").match(/\\d+(?:[.,\\s]\\d+)*/g) || []).map(normalizeNumber).filter(Boolean);
    const quoteNums = new Set((String(support?.quote || "").match(/\\d+(?:[.,\\s]\\d+)*/g) || []).map(normalizeNumber).filter(Boolean));
    if (claimNums.length && !claimNums.every((n) => quoteNums.has(n))) return false;
  }
'''
if old not in s:
    raise SystemExit('numeric support anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# Add a source-level regression guard so accidental relaxation is caught in CI.
p = ROOT / 'scripts' / 'claim_passage_contract_test.py'
p.write_text('''#!/usr/bin/env python3
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
''', encoding='utf-8')
print('Numeric claim support hardened')
