#!/usr/bin/env python3
"""Hard gate against fake source plurality using the canonical evidence policy."""
from __future__ import annotations
import json, sys
from pathlib import Path
from evidence_policy import claim_has_required_support
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'content'/'articles'; ERR=[]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 for p in sorted(ART.glob('*.json')):
  if p.name.startswith('_'): continue
  try: a=load(p)
  except Exception: continue
  if a.get('pipeline_version')!=2 or a.get('status') not in {'ready','scheduled','published'}: continue
  if str(a.get('category')) in {'Guide','Kommentar'}: continue
  lp=ROOT/str(a.get('ledger') or '')
  if not lp.exists(): continue
  l=load(lp); sources={s.get('id'):s for s in l.get('sources') or [] if s.get('id')}
  sweep=l.get('coverage_sweep') or {}; ids=sweep.get('editorial_source_ids') or []
  groups={str(sources.get(i,{}).get('source_group') or '') for i in ids}; groups.discard('')
  if sweep.get('status')=='pass' and not groups: ERR.append(f'{p.name}: coverage PASS kræver mindst én reel dokumentationskilde')
  claims={c.get('id'):c for c in l.get('claims') or [] if c.get('id')}
  for cid in a.get('claim_ids') or []:
   c=claims.get(cid)
   if c and not claim_has_required_support(a,l,c,sources): ERR.append(f'{p.name}: claim {cid} mangler gyldig støtte efter canonical evidence policy')
 if ERR:
  print('SOURCE INDEPENDENCE: FAIL'); [print('-',x) for x in ERR]; return 1
 print('SOURCE INDEPENDENCE: PASS'); return 0
if __name__=='__main__': sys.exit(main())
