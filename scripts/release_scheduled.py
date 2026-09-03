#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from release_ready import diagnose
ROOT=Path(__file__).resolve().parents[1]; ARTICLE_DIR=ROOT/'content'/'articles'
def parse_iso(v):
 d=datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None: raise ValueError('timezone mangler')
 return d
def main():
 p=argparse.ArgumentParser(); p.add_argument('--now'); a=p.parse_args(); now=parse_iso(a.now).astimezone(timezone.utc) if a.now else datetime.now(timezone.utc); stamp=now.replace(microsecond=0).isoformat().replace('+00:00','Z'); n=0; skipped=0
 for path in sorted(ARTICLE_DIR.glob('*.json')):
  if path.name.startswith('_'): continue
  x=json.loads(path.read_text(encoding='utf-8'))
  if x.get('status')!='scheduled': continue
  sf=x.get('scheduled_for')
  if not sf: raise SystemExit(f'{path.name}: scheduled_for mangler')
  if parse_iso(sf).astimezone(timezone.utc)>now: continue
  if x.get('pipeline_version')==2:
   reasons,_=diagnose(x)
   if reasons:
    skipped+=1
    print(f'{path.name}: ikke frigivet: ' + '; '.join(reasons))
    continue
  x['status']='published'; x['published_at']=stamp; x['released_from_schedule_at']=stamp; x['release_requested']=False; x['publication']={'release_mode':'scheduled','released_at':stamp,'scheduled_for':sf}; path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); n+=1
 print(f'Scheduled release: {n} article(s); skipped: {skipped}'); return 0
if __name__=='__main__': raise SystemExit(main())
