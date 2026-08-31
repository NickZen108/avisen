#!/usr/bin/env python3
"""Turn scan/latest.md into a deterministic, machine-readable newsroom queue.

Includes conservative story-level clustering so differently worded headlines can
be reviewed as one event before drafting. Clusters are leads, never verification.
"""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCAN=ROOT/'scan'/'latest.md';OUT=ROOT/'queue'/'candidates.json'
STOP={'og','i','på','af','for','med','til','fra','en','et','den','det','de','der','som','the','a','an','of','to','in','on','for','with','after','as'}
def normalize_title(v):
 v=str(v).casefold();v=re.sub(r'[^a-z0-9æøåäöüéèáàíìóòúùß ]+',' ',v);return ' '.join(v.split())
def tokens(v):return {x for x in normalize_title(v).split() if len(x)>2 and x not in STOP}
def sim(a,b):
 na,nb=normalize_title(a),normalize_title(b);ta,tb=tokens(a),tokens(b);jac=len(ta&tb)/max(1,len(ta|tb));seq=SequenceMatcher(None,na,nb).ratio();return max(jac,seq)
def parse_scan(text):
 label=None;signals=[];source=None
 for raw in text.splitlines():
  line=raw.strip()
  if line.startswith('# Scan '):label=line.removeprefix('# Scan ').strip()
  elif line.startswith('## '):source=line[3:].strip()
  elif line.startswith('- ') and source:
   h=line[2:].strip()
   if h and not h.startswith('('):signals.append({'source':source,'headline':h,'normalized':normalize_title(h)})
 signals.sort(key=lambda x:(x['normalized'],x['source'],x['headline']));return label,signals
def cluster(signals):
 clusters=[]
 for s in signals:
  best=None;score=0
  for c in clusters:
   sc=max(sim(s['headline'],x['headline']) for x in c['items'])
   if sc>score:best,score=c,sc
  if best is not None and score>=0.72:
   best['items'].append(s);best['max_similarity']=max(best['max_similarity'],round(score,3))
  else:clusters.append({'items':[s],'max_similarity':1.0})
 out=[]
 for c in clusters:
  sources=sorted({x['source'] for x in c['items']});heads=[x['headline'] for x in c['items']]
  event_key=hashlib.sha256('|'.join(sorted(normalize_title(x) for x in heads)).encode()).hexdigest()[:16]
  out.append({'event_key':event_key,'sources':sources,'headlines':heads,'signal_count':len(c['items']),'multi_source':len(sources)>=2,'max_similarity':c['max_similarity'],'note':'Likely same-event cluster; editorial/source independence must still be verified.'})
 out.sort(key=lambda x:(-x['signal_count'],-len(x['sources']),x['event_key']));return out
def main():
 if not SCAN.exists():raise SystemExit('scan/latest.md mangler')
 label,signals=parse_scan(SCAN.read_text(encoding='utf-8'));stable=[{'source':x['source'],'headline':x['headline'],'normalized':x['normalized']} for x in signals];fp=hashlib.sha256(json.dumps(stable,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text(encoding='utf-8'))
   if old.get('fingerprint')==fp:print('Newsroom queue uændret');return 0
  except Exception:pass
 grouped={}
 for s in signals:grouped.setdefault(s['normalized'],[]).append(s)
 exact=[{'normalized':n,'sources':sorted({x['source'] for x in rows}),'headlines':[x['headline'] for x in rows],'note':'Exact normalized headline match; not proof of independent sourcing.'} for n,rows in grouped.items() if len({x['source'] for x in rows})>=2]
 story_clusters=cluster(signals)
 payload={'schema_version':2,'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'scan_label':label,'fingerprint':fp,'signal_count':len(signals),'signals':signals,'exact_clusters':exact,'story_clusters':story_clusters,'editorial_status':'UNRANKED','warning':'Clusters are inventory/deduplication hints, not news-value or verification decisions.'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f'Newsroom queue opdateret: {len(signals)} signaler / {len(story_clusters)} story-clusters');return 0
if __name__=='__main__':raise SystemExit(main())
