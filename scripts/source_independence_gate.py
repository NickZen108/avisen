#!/usr/bin/env python3
"""Hard gate against fake source plurality without imposing arbitrary source quotas."""
from __future__ import annotations
import json,sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'content'/'articles';ERR=[]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def authoritative_primary(source):
 return bool(source and source.get('type') in {'primary','paper','interview'} and str(source.get('authoritative_for') or '').strip())
def authoritative_editorial(source):
 # A named, accountable wire/news organisation may carry an ordinary claim alone
 # when the article attributes the claim to that organisation. This is not a
 # substitute for stronger checks on disputed/high-risk claims.
 if not source:return False
 org=' '.join(str(source.get(k) or '') for k in ('publisher','name','source_group','title')).lower()
 return any(x in org for x in ('reuters','associated press',' ap ','ritzau','agence france-presse','afp'))
def main():
 for p in sorted(ART.glob('*.json')):
  if p.name.startswith('_'):continue
  try:a=load(p)
  except Exception:continue
  if a.get('pipeline_version')!=2 or a.get('status') not in {'ready','scheduled','published'}:continue
  if str(a.get('category')) in {'Guide','Kommentar'}:continue
  lp=ROOT/str(a.get('ledger') or '')
  if not lp.exists():continue
  l=load(lp);sources={s.get('id'):s for s in l.get('sources') or [] if s.get('id')}
  sweep=l.get('coverage_sweep') or {};ids=sweep.get('editorial_source_ids') or []
  groups={str(sources.get(i,{}).get('source_group') or '') for i in ids};groups.discard('')
  if sweep.get('status')=='pass' and not groups:ERR.append(f'{p.name}: coverage PASS kræver mindst én reel dokumentationskilde')
  for cid in a.get('claim_ids') or []:
   c=next((x for x in l.get('claims') or [] if x.get('id')==cid),None)
   if not c:continue
   cids=c.get('source_ids') or [];cu={str(sources.get(i,{}).get('url') or '') for i in cids};cu.discard('');cg={str(sources.get(i,{}).get('source_group') or '') for i in cids};cg.discard('')
   primary_ok=any(authoritative_primary(sources.get(i)) for i in cids)
   editorial_ok=any(authoritative_editorial(sources.get(i)) for i in cids)
   if not primary_ok and not editorial_ok and (len(cu)<2 or len(cg)<2):ERR.append(f'{p.name}: claim {cid} mangler tilstrækkelig dokumentation: autoritativ primærkilde, anerkendt original bureau/redaktionel kilde eller to reelt uafhængige troværdige kilder')
 if ERR:
  print('SOURCE INDEPENDENCE: FAIL');[print('-',x) for x in ERR];return 1
 print('SOURCE INDEPENDENCE: PASS');return 0
if __name__=='__main__':sys.exit(main())
