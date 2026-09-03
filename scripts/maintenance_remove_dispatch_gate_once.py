#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sync = ROOT / 'scripts' / 'sync_cloudflare_editorial.py'
log = ROOT / 'scripts' / 'log_publication_attempt.py'

# Coverage/source-group remains useful audit metadata, but must not be a second evidence gate.
body = sync.read_text(encoding='utf-8')
old_block = '''    normalize_coverage(ledger)\n    coverage = ledger.get("coverage_sweep") or {}\n    groups = set(coverage.get("independent_source_groups") or [])\n    if coverage.get("status") not in {"pass", "limited"} or not groups:\n        fail("coverage sweep mangler en dokumenteret kildegruppe")\n\n'''
if old_block not in body:
    raise SystemExit('coverage validation block missing')
body = body.replace(old_block, '    normalize_coverage(ledger)\n\n', 1)
sync.write_text(body, encoding='utf-8')

# Publication-attempt logging is diagnostics only; remove obsolete gate vocabulary and old two-source/right-of-reply heuristics.
body = log.read_text(encoding='utf-8')
body = body.replace(" if s=='desk-recheck':return 'desk_staleness_or_scope'\n", '')
body = body.replace(" hard=['forelægg','right of reply','færre end to','kilde','fact check','fact-check','modsig','etik','duplicate','dublet']", " hard=['fact check','fact-check','modsig','etik','duplicate','dublet']")
body = body.replace("return ('blocked-correct','Blokering beskytter en reel journalistisk/etisk risiko.','Behold hård gate; undersøg kun om research kan løse manglen automatisk.')", "return ('blocked-correct','Blokeringen beskytter en reel faktuel eller etisk risiko.','Send kun den konkrete mangel til dens eksisterende ejer.')")
body = body.replace("'reason':reason or ('Alle gates PASS' if status=='approved' else 'Ingen begrundelse registreret')", "'reason':reason or ('Godkendt' if status=='approved' else 'Ingen begrundelse registreret')")
log.write_text(body, encoding='utf-8')

print('coverage/diagnostics simplification patch: PASS')
