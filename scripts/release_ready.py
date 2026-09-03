#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ARTICLE_DIR=ROOT/'content'/'articles'; FRONTPAGE=ROOT/'content'/'frontpage.json'; REPORT=ROOT/'reports'/'editorial'/'pipeline-health.json'
NON_EDITORIAL_AFTER_APPROVAL={
 'status','published_at','updated_at','scheduled_for','released_from_schedule_at','release_requested','publication','manual_review_completed','workflow_state',
 'editorial_destination','related_news_slug','followup_type','weight'
}
def parse_iso(v):
 d=datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None: raise ValueError('timezone mangler')
 return d
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def snap(a):
 x=copy.deepcopy(a)
 for k in NON_EDITORIAL_AFTER_APPROVAL:x.pop(k,None)
 return x
def article_for_slug(slug):
 p=ARTICLE_DIR/f'{slug}.json'
 if not p.exists(): return None
 try:return load(p)
 except Exception:return None
def published_slugs():
 out=[]
 for p in sorted(ARTICLE_DIR.glob('*.json'),reverse=True):
  if p.name.startswith('_'): continue
  try:x=load(p)
  except Exception:continue
  if x.get('status')=='published' and x.get('slug'): out.append(x['slug'])
 return out
def set_ticker(state, slug, article=None):
 if slug: state['ticker']={'slug':slug}
 else: state['ticker']={}
 state.pop('ticker_text',None); return state
def write_frontpage(state): FRONTPAGE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def repair_frontpage(blocked_slug):
 if not FRONTPAGE.exists(): return
 state=load(FRONTPAGE); changed=False
 for key in ('rail','stack','narrow'):
  before=state.get(key,[]) or []; after=[x for x in before if x.get('slug')!=blocked_slug]
  if after!=before: state[key]=after; changed=True
 candidates=[]
 for key in ('lead','ticker'):
  s=(state.get(key) or {}).get('slug')
  if s and s!=blocked_slug: candidates.append(s)
 for key in ('rail','narrow','stack'): candidates.extend(x.get('slug') for x in state.get(key,[]) if x.get('slug'))
 candidates.extend(published_slugs()); fallback=next((s for s in candidates if s and s!=blocked_slug),None)
 for key in ('ticker','lead'):
  if (state.get(key) or {}).get('slug')==blocked_slug:
   if key=='ticker': set_ticker(state,fallback)
   elif fallback: state[key]={'slug':fallback}
   else: state[key]={}
   changed=True
 if changed: write_frontpage(state)
def add_to_frontpage(article):
 slug=article['slug']; state=load(FRONTPAGE); state['date']=slug[:10]; set_ticker(state,slug,article)
 if article.get('weight') in {'A','B'} and not article.get('related_news_slug'):
  state['lead']={'slug':slug}; state['lead_rationale']=f"Ny {article.get('weight')}-historie publiceret automatisk; frisk væsentlig nyhed erstatter ældre lead."
 for key,limit in (('rail',5),('narrow',8)):
  items=[x for x in state.get(key,[]) if x.get('slug')!=slug]; items.insert(0,{'slug':slug}); state[key]=items[:limit]
 write_frontpage(state)
def diagnose(path,x):
 reasons=[]; missing=[]
 if x.get('manual_review') and not x.get('manual_review_completed'):
  reasons.append('manual_review kræver menneskelig afslutning'); missing.append('manual_review')
 lp=ROOT/str(x.get('ledger',''))
 if not lp.exists(): return ['ledger mangler'],'research'
 l=load(lp); f=l.get('fact_check') or {}
 if f.get('status')!='pass' or not f.get('checked_at'): reasons.append('fact-check PASS mangler'); missing.append('fact_check')
 ap=ROOT/'reports'/'editorial'/'approvals'/f"{x['slug']}.json"
 if not ap.exists(): reasons.append('final approval mangler'); missing.append('final_editor')
 else:
  a=load(ap); gates=a.get('gates') or {}
  if a.get('status')!='pass': reasons.append('final approval status er ikke PASS'); missing.append('final_editor')
  for g in ['language','ethics','image','seo']:
   if gates.get(g)!='pass': reasons.append(f'approval gate {g} er ikke PASS'); missing.append(g)
  if gates.get('final_editor')!='pass': reasons.append('approval gate final_editor er ikke PASS'); missing.append('final_editor')
  if a.get('editorial_snapshot')!=snap(x): reasons.append('artiklens redaktionelle indhold er ændret efter final approval'); missing.append('final_editor')
 priority=['manual_review','fact_check','language','ethics','image','seo','final_editor']
 resume=next((step for step in priority if step in missing),None)
 return reasons,resume
def write_health(rows,stamp):
 REPORT.parent.mkdir(parents=True,exist_ok=True); counts={}
 for r in rows: counts[r['status']]=counts.get(r['status'],0)+1
 REPORT.write_text(json.dumps({'generated_at':stamp,'counts':counts,'blocked_count':sum(bool(r.get('reasons')) for r in rows),'articles':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser(); p.add_argument('--now'); p.add_argument('--normalize-only',action='store_true'); a=p.parse_args(); now=parse_iso(a.now).astimezone(timezone.utc) if a.now else datetime.now(timezone.utc); stamp=now.replace(microsecond=0).isoformat().replace('+00:00','Z'); released=0; recovered=0; rows=[]
 for path in sorted(ARTICLE_DIR.glob('*.json')):
  if path.name.startswith('_'): continue
  x=load(path)
  if x.get('pipeline_version')!=2: continue
  reasons,resume=diagnose(path,x) if x.get('status') in {'ready','checking','editing','researching'} else ([],None)
  if x.get('status')=='ready' and x.get('release_requested') is True and reasons:
   x['status']='checking'; x['release_requested']=False; x['workflow_state']={'state':'blocked','blocked_at':stamp,'resume_from':resume,'reasons':reasons}; path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); repair_frontpage(x.get('slug')); recovered+=1
  elif x.get('status') in {'checking','editing','researching'} and reasons:
   repair_frontpage(x.get('slug')); ws=x.get('workflow_state') or {}; changed=ws.get('resume_from')!=resume or ws.get('reasons')!=reasons or ws.get('state') not in {'blocked','needs_attention'}
   if changed:
    ws.update({'state':'blocked','resume_from':resume,'reasons':reasons}); ws.setdefault('blocked_at',stamp); x['workflow_state']=ws; path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  elif x.get('status')=='ready' and x.get('release_requested') is True and not reasons and not a.normalize_only:
   x['status']='published'; x['published_at']=stamp; x['release_requested']=False; x['publication']={'release_mode':'immediate','released_at':stamp}; x.pop('workflow_state',None); path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); add_to_frontpage(x); released+=1
  rows.append({'slug':x.get('slug'),'title':x.get('title'),'status':x.get('status'),'release_requested':x.get('release_requested'),'resume_from':resume if reasons else None,'reasons':reasons})
 write_health(rows,stamp); print(f'Ready release: {released}; recovered/parked: {recovered}'); return 0
def self_test():
 state={'ticker':{'slug':'old-slug'},'ticker_text':'Gammel ticker','lead':{'slug':'old-lead'},'rail':[],'narrow':[],'stack':[]}; article={'slug':'new-slug','title':'Ny titel','standfirst':'Ny standfirst om sagen.'}; set_ticker(state,'new-slug',article); assert state['ticker']=={'slug':'new-slug'},state; assert 'ticker_text' not in state,state; set_ticker(state,None); assert state['ticker']=={}; assert 'ticker_text' not in state; print('release_ready self-test: PASS')
if __name__=='__main__':
 import sys
 if '--self-test' in sys.argv: self_test(); raise SystemExit(0)
 raise SystemExit(main())
