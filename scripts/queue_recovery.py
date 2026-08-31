#!/usr/bin/env python3
"""Maintain deterministic retry/dead-letter state for incomplete pipeline items."""
from __future__ import annotations
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HEALTH=ROOT/'reports'/'editorial'/'pipeline-health.json';OUT=ROOT/'queue'/'recovery.json'

def load(p,d):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return d

def main():
 now=datetime.now(timezone.utc);health=load(HEALTH,{'articles':[]});old=load(OUT,{'items':{}});items=old.get('items') or {};seen=set()
 for a in health.get('articles') or []:
  slug=str(a.get('slug') or '')
  if not slug or a.get('status')=='published':continue
  reasons=[str(x) for x in a.get('reasons') or []]
  if not reasons:continue
  seen.add(slug);prev=items.get(slug,{})
  signature=' | '.join(sorted(reasons))
  attempts=int(prev.get('attempts') or 0)
  if prev.get('reason_signature')!=signature:attempts=0
  attempts+=1
  dead=attempts>=4
  delay=min(360,15*(2**max(0,attempts-1)))
  items[slug]={'status':'dead-letter' if dead else 'retry','attempts':attempts,'resume_from':a.get('resume_from') or a.get('status'),'reasons':reasons,'reason_signature':signature,'last_seen_at':now.isoformat(timespec='seconds'),'next_retry_at':None if dead else (now+timedelta(minutes=delay)).isoformat(timespec='seconds')}
 for slug in list(items):
  if slug not in seen:items.pop(slug,None)
 payload={'schema_version':1,'generated_at':now.isoformat(timespec='seconds'),'retry_count':sum(1 for x in items.values() if x['status']=='retry'),'dead_letter_count':sum(1 for x in items.values() if x['status']=='dead-letter'),'items':items}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f"Recovery queue: {payload['retry_count']} retry, {payload['dead_letter_count']} dead-letter")
if __name__=='__main__':main()
