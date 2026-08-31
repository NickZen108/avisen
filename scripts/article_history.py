#!/usr/bin/env python3
"""Persist hashes of published editorial snapshots for audit/version history."""
from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'content'/'articles'; OUT=ROOT/'reports'/'editorial'/'article-versions.json'
VOLATILE={'updated_at','published_at','released_from_schedule_at','publication','workflow_state'}

def load(p,default):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return default

def snapshot(a):
 return {k:v for k,v in a.items() if k not in VOLATILE and not k.startswith('__')}

def digest(obj):
 raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
 return hashlib.sha256(raw).hexdigest()

def main():
 db=load(OUT,{'schema_version':1,'articles':{}}); now=datetime.now(timezone.utc).isoformat(timespec='seconds')
 changed=0
 for p in sorted(ART.glob('*.json')):
  if p.name.startswith('_'):continue
  a=load(p,{})
  if a.get('status')!='published' or not a.get('slug'):continue
  snap=snapshot(a); h=digest(snap); rows=db['articles'].setdefault(a['slug'],[])
  if not rows or rows[-1].get('hash')!=h:
   rows.append({'hash':h,'recorded_at':now,'title':a.get('title'),'story_id':a.get('story_id'),'snapshot':snap}); changed+=1
   if len(rows)>25: del rows[:-25]
 db['generated_at']=now
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Article history OK: {changed} nye versioner')
 return 0
if __name__=='__main__':raise SystemExit(main())
