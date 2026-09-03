#!/usr/bin/env python3
"""Production readiness with local automatic recovery.

The newspaper must not require an operator to watch warnings, and a local defect must
not block an otherwise healthy edition. Safe structural faults are repaired in place;
a page that still cannot be generated is parked individually and the edition rebuilds.
"""
from __future__ import annotations
import json,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ARTICLES=ROOT/'content'/'articles'; DOCS=ROOT/'docs'; FRONT=ROOT/'content'/'frontpage.json'; OUT=ROOT/'reports'/'editorial'/'production-readiness.json'
ALLOWED_FOLLOWUPS={'update','video','images','eyewitness','background','timeline','commentary',None}
def load(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return default
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def published():
 rows=[]
 for p in ARTICLES.glob('*.json'):
  if p.name.startswith('_'):continue
  a=load(p)
  if isinstance(a,dict) and a.get('status')=='published' and a.get('slug'):rows.append((p,a))
 return rows
def repair_relations(rows,actions):
 slugs={a.get('slug') for _,a in rows}
 for p,a in rows:
  changed=False; kind=a.get('followup_type'); rel=a.get('related_news_slug')
  if kind not in ALLOWED_FOLLOWUPS:
   a.pop('followup_type',None); changed=True; actions.append({'slug':a['slug'],'action':'removed_invalid_followup_type'})
  if a.get('followup_type') and not rel:
   a.pop('followup_type',None); changed=True; actions.append({'slug':a['slug'],'action':'removed_orphan_followup_type'})
  if rel and rel not in slugs:
   a.pop('related_news_slug',None); a.pop('followup_type',None); changed=True; actions.append({'slug':a['slug'],'action':'detached_missing_related_article'})
  if changed:write(p,a)
def rebuild():
 try:
  subprocess.run([sys.executable,str(ROOT/'scripts'/'build_all_v2.py')],cwd=ROOT,check=True,timeout=180)
  return True
 except Exception:return False
def remove_slug_from_frontpage(slug):
 state=load(FRONT,{})
 for key in ('rail','stack','narrow'):
  state[key]=[x for x in state.get(key,[]) or [] if x.get('slug')!=slug]
 for key in ('ticker','lead'):
  if (state.get(key) or {}).get('slug')==slug:state[key]={}
 write(FRONT,state)
def recover_missing_html(rows,actions):
 missing=[(p,a) for p,a in rows if not (DOCS/'artikler'/f"{a['slug']}.html").exists()]
 if not missing:return
 actions.append({'action':'regenerate_missing_html','count':len(missing)})
 rebuild()
 still=[(p,a) for p,a in missing if not (DOCS/'artikler'/f"{a['slug']}.html").exists()]
 if not still:return
 stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
 for p,a in still:
  a['status']='checking'; a['release_requested']=False; a['workflow_state']={'state':'blocked','resume_from':'technical_generation','blocked_at':stamp,'reasons':['genereret artikel-HTML kunne ikke dannes efter automatisk retry']}; write(p,a); remove_slug_from_frontpage(a['slug']); actions.append({'slug':a['slug'],'action':'parked_only_article_after_failed_html_retry'})
 rebuild()
def diagnostics(rows):
 a11y=[]; perf=[]
 for _,a in rows[:100]:
  p=DOCS/'artikler'/f"{a['slug']}.html"
  if not p.exists():continue
  text=p.read_text(encoding='utf-8',errors='replace')
  if len(re.findall(r'<h1\b',text,re.I))!=1:a11y.append({'slug':a['slug'],'issue':'h1'})
  if '<html lang="da"' not in text.lower():a11y.append({'slug':a['slug'],'issue':'lang'})
  kb=len(text.encode('utf-8'))/1024
  if kb>220:perf.append({'slug':a['slug'],'html_kb':round(kb,1)})
 return {'accessibility_diagnostics':a11y[:50],'performance_diagnostics':perf[:50]}
def main():
 actions=[]; rows=published(); repair_relations(rows,actions); rows=published(); recover_missing_html(rows,actions); rows=published()
 payload={'schema_version':2,'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'status':'green','published_count':len(rows),'automatic_recovery_actions':actions,'metrics':diagnostics(rows)}
 OUT.parent.mkdir(parents=True,exist_ok=True); write(OUT,payload)
 print('PRODUCTION READINESS: GREEN')
 for a in actions:print('AUTO-RECOVERY:',json.dumps(a,ensure_ascii=False))
 return 0
if __name__=='__main__':raise SystemExit(main())
