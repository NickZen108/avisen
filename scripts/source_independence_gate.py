#!/usr/bin/env python3
"""Hard gate against fake source plurality caused by duplicated URLs/syndication."""
from __future__ import annotations
import json,sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'content'/'articles';ERR=[]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
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
  urls={str(sources.get(i,{}).get('url') or '') for i in ids};urls.discard('')
  hosts={urlparse(u).hostname for u in urls};hosts.discard(None)
  groups={str(sources.get(i,{}).get('source_group') or '') for i in ids};groups.discard('')
  if sweep.get('status')=='pass' and (len(urls)<3 or len(hosts)<2 or len(groups)<3):ERR.append(f'{p.name}: coverage PASS kræver >=3 unikke URLer, >=2 domæner og >=3 source-groups')
  for cid in a.get('claim_ids') or []:
   c=next((x for x in l.get('claims') or [] if x.get('id')==cid),None)
   if not c:continue
   cids=c.get('source_ids') or [];cu={str(sources.get(i,{}).get('url') or '') for i in cids};cu.discard('');cg={str(sources.get(i,{}).get('source_group') or '') for i in cids};cg.discard('')
   if len(cu)<2 or len(cg)<2:ERR.append(f'{p.name}: claim {cid} mangler mindst 2 reelt forskellige URLer/source-groups')
 if ERR:
  print('SOURCE INDEPENDENCE: FAIL');[print('-',x) for x in ERR];return 1
 print('SOURCE INDEPENDENCE: PASS');return 0
if __name__=='__main__':sys.exit(main())
