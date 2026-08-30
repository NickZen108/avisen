#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ARTICLE_DIR=ROOT/'content'/'articles'
def parse_iso(v):
 d=datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None: raise ValueError('timezone mangler')
 return d
def main():
 p=argparse.ArgumentParser(); p.add_argument('--now'); a=p.parse_args(); now=parse_iso(a.now).astimezone(timezone.utc) if a.now else datetime.now(timezone.utc); stamp=now.replace(microsecond=0).isoformat().replace('+00:00','Z'); n=0
 for path in sorted(ARTICLE_DIR.glob('*.json')):
  if path.name.startswith('_'): continue
  x=json.loads(path.read_text(encoding='utf-8'))
  if x.get('pipeline_version')!=2 or x.get('status')!='ready' or x.get('release_requested') is not True: continue
  if x.get('manual_review'): raise SystemExit(f'{path.name}: manual_review må ikke auto-release')
  ledger=json.loads((ROOT/str(x.get('ledger',''))).read_text(encoding='utf-8'))
  if (ledger.get('fact_check') or {}).get('status')!='pass' or (ledger.get('desk_recheck') or {}).get('status') not in {'publish','update'}: raise SystemExit(f'{path.name}: redaktionelle gates mangler')
  if not (ROOT/'reports'/'editorial'/'approvals'/f"{x['slug']}.json").exists(): raise SystemExit(f'{path.name}: final approval mangler')
  x['status']='published'; x['published_at']=stamp; x['release_requested']=False; x['publication']={'release_mode':'immediate','released_at':stamp}; path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); n+=1
 print(f'Ready release: {n} article(s)'); return 0
if __name__=='__main__': raise SystemExit(main())
