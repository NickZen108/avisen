#!/usr/bin/env python3
"""Reject obvious hero entity/geography mismatches before publication."""
from __future__ import annotations
import json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARTICLES=ROOT/'content'/'articles'
PLACE_COUNTRY={
 'aalborg':'DK','aarhus':'DK','århus':'DK','odense':'DK','copenhagen':'DK','københavn':'DK','denmark':'DK','danmark':'DK',
 'washington':'US','new york':'US','san francisco':'US','chicago':'US','los angeles':'US','united states':'US','usa':'US',
 'london':'GB','manchester':'GB','birmingham':'GB','united kingdom':'GB','england':'GB',
 'paris':'FR','france':'FR','berlin':'DE','germany':'DE','madrid':'ES','spain':'ES','españa':'ES',
 'rome':'IT','italy':'IT','brussels':'BE','belgium':'BE','stockholm':'SE','sweden':'SE','oslo':'NO','norway':'NO'
}

def changed():
 names=set()
 for cmd in (["git","diff","--name-only","HEAD^..HEAD"],["git","diff","--name-only"],["git","diff","--cached","--name-only"]):
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=False)
  if p.returncode==0:names.update(x.strip() for x in p.stdout.splitlines() if x.strip())
 return [ROOT/n for n in names if n.startswith('content/articles/') and n.endswith('.json') and (ROOT/n).exists()]

def main():
 faults=[]
 paths=changed() or []
 if not paths:
  print('MEDIA ENTITY SANITY: no changed articles');return 0
 for path in paths:
  a=json.loads(path.read_text(encoding='utf-8'))
  if a.get('status') not in {'ready','scheduled','published'}:continue
  img=a.get('image') or {}; loc=a.get('story_location') or {}; expected=str(loc.get('country_code') or '').upper()
  if not expected:continue
  bag=' '.join(str(img.get(k) or '') for k in ('alt','source_url','caption')).lower().replace('_',' ')
  found={code for place,code in PLACE_COUNTRY.items() if re.search(rf'(?<![a-zæøå]){re.escape(place)}(?![a-zæøå])',bag)}
  foreign={x for x in found if x!=expected}
  if foreign:
   faults.append(f"{path.name}: hero peger på geografi {sorted(foreign)} men story_location={expected}")
 if faults:
  print('MEDIA ENTITY SANITY: FAIL')
  for f in faults:print('-',f)
  return 1
 print('MEDIA ENTITY SANITY: PASS');return 0
if __name__=='__main__':raise SystemExit(main())
