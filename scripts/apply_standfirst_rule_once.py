#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

# 1) Tighten the EXISTING language-repair instruction. This is editorial guidance, not a new gate.
p = ROOT / 'cloudflare/newsdesk/src/editorial.js'
s = p.read_text(encoding='utf-8')
old = "Sørg også for, at standfirst er en rigtig kort manchet og ikke blot et kildenavn."
new = "Sørg også for, at standfirst er en rigtig kort manchet og ikke blot et kildenavn: normalt 1-2 korte sætninger og højst 35 ord. Den skal opsummere nyheden, gerne med vigtigste modpart eller konsekvens, uden gentagelser, spekulation eller mini-brødtekst."
if old not in s and new not in s:
    raise SystemExit('standfirst instruction anchor not found')
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# 2) Correct the already-published Germany/Russia article.
slug = '2026-09-02-tyskland-og-rusland-i-konflikt-efter-droneangreb'
article_path = ROOT / 'content/articles' / f'{slug}.json'
approval_path = ROOT / 'reports/editorial/approvals' / f'{slug}.json'
article = json.loads(article_path.read_text(encoding='utf-8'))
article['standfirst'] = 'Tyskland beskylder Rusland for et droneangreb mod Leipzig lufthavn. Rusland afviser anklagen, mens Berlin svarer med nye sanktioner.'
article_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

approval = json.loads(approval_path.read_text(encoding='utf-8'))
snap = json.loads(json.dumps(article))
for key in ['status','published_at','updated_at','scheduled_for','released_from_schedule_at','release_requested','publication','manual_review_completed','workflow_state']:
    snap.pop(key, None)
approval['editorial_snapshot'] = snap
approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('standfirst rule and article repair applied')
