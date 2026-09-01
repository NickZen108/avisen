#!/usr/bin/env python3
"""Hard gate against fake source plurality without imposing arbitrary source quotas."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'content'/'articles';ERR=[]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def authoritative_primary(source):
 return bool(source and source.get('type') in {'primary','paper','interview'} and str(source.get('authoritative_for') or '').strip())
def authoritative_editorial(source):
 # Original wire sources may carry an ordinary claim alone.
 if not source:return False
 org=' '.join(str(source.get(k) or '') for k in ('publisher','name','source_group','title')).lower()
 return any(x in org for x in ('reuters','associated press',' ap ','ritzau','agence france-presse','afp'))

STRONG_HOSTS={'reuters.com','apnews.com','bbc.com','bbc.co.uk','dr.dk','tv2.dk','svt.se','nrk.no','ft.com','politico.eu','bloomberg.com','theguardian.com','nytimes.com','wsj.com','france24.com','tagesschau.de','rbb24.de','itv.com'}
HIGH_RISK=re.compile(r'\b(sigtet|tiltalt|anklag|mistænkt|voldtægt|seksual|misbrug|selvmord|mindreår|barn|børn|privat helbred|diagnose|terror|drab|korruption|svindel|hvidvask|overgreb|racist|ekstremist)\b',re.I)
ACCUSED=re.compile(r'\b(sigtet|tiltalt|mistænkt|anklaget)\b',re.I)
NAMED=re.compile(r'\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b')
def strong_editorial(source):
 if not source or source.get('discovery_only'):return False
 if authoritative_editorial(source):return True
 try:host=(urlparse(str(source.get('url') or '')).hostname or '').removeprefix('www.').lower()
 except Exception:host=''
 if any(host==x or host.endswith('.'+x) for x in STRONG_HOSTS):return True
 name=str(source.get('name') or '').strip().lower()
 return name in {'bbc','dr','tv 2','tv2','svt','nrk','financial times','politico','reuters','ap','associated press','afp','ritzau'}
def high_risk(article,ledger,claim):
 if (ledger.get('right_of_reply') or {}).get('required'):return True
 return bool(HIGH_RISK.search(' '.join(str(x or '') for x in (article.get('title'),article.get('standfirst'),claim.get('claim')))))
def named_accused(article,claim):
 text=str(claim.get('claim') or '')
 return bool(ACCUSED.search(text) and NAMED.search(text))
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
   strong_ok=any(strong_editorial(sources.get(i)) for i in cids)
   if named_accused(a,c) and not primary_ok:ERR.append(f'{p.name}: claim {cid} om navngiven sigtet/tiltalt/mistænkt kræver primærkilde')
   elif not primary_ok and not editorial_ok and not (strong_ok and not high_risk(a,l,c)) and (len(cu)<2 or len(cg)<2):ERR.append(f'{p.name}: claim {cid} mangler gyldig evidensklasse: primærkilde, original bureaukilde, stærk original redaktionel kilde for lavrisiko eller to uafhængige kilder')
 if ERR:
  print('SOURCE INDEPENDENCE: FAIL');[print('-',x) for x in ERR];return 1
 print('SOURCE INDEPENDENCE: PASS');return 0
if __name__=='__main__':sys.exit(main())
