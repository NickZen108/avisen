#!/usr/bin/env python3
"""Generate editorial analytics without click-chasing.

Measures category mix, source diversity, correction rate, story follow-ups and
article depth from repository facts only. Intended for Kontrolrummet, not ranking.
"""
from __future__ import annotations
import json,statistics
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'content'/'articles';OUT=ROOT/'reports'/'editorial'/'editorial-analytics.json'

def load(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return d

def main():
 arts=[]; hosts=Counter();groups=Counter();body_lengths=[];followups=0
 for p in ART.glob('*.json'):
  if p.name.startswith('_'):continue
  a=load(p,{})
  if a.get('status')!='published':continue
  arts.append(a); body_lengths.append(sum(len(str(b.get('text') or '')) for b in a.get('body') or []))
  if a.get('related_news_slug'):followups+=1
  lp=ROOT/str(a.get('ledger') or '')
  l=load(lp,{}) if lp.exists() else {}
  for s in l.get('sources') or []:
   h=urlparse(str(s.get('url') or '')).hostname
   if h:hosts[h]+=1
   g=str(s.get('source_group') or '').strip()
   if g:groups[g]+=1
 corr=load(ROOT/'content'/'corrections.json',{'entries':[]}).get('entries') or []
 cats=Counter(str(a.get('category') or 'Ukendt') for a in arts)
 payload={'schema_version':1,'published_count':len(arts),'category_mix':dict(cats.most_common()),'top_source_hosts':dict(hosts.most_common(20)),'top_source_groups':dict(groups.most_common(20)),'unique_source_hosts':len(hosts),'unique_source_groups':len(groups),'followup_share':round(followups/max(1,len(arts)),3),'correction_rate':round(len(corr)/max(1,len(arts)),3),'median_body_characters':int(statistics.median(body_lengths)) if body_lengths else 0,'principle':'These metrics are diagnostic. Clicks alone must not determine editorial priority.'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Editorial analytics OK')
if __name__=='__main__':main()
