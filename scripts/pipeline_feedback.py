#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
ATTEMPTS=ROOT/'reports'/'editorial'/'publication-attempts.jsonl'; HEALTH=ROOT/'reports'/'editorial'/'pipeline-health.json'; OUT=ROOT/'reports'/'editorial'/'pipeline-feedback.json'; DK=ZoneInfo('Europe/Copenhagen')
CANONICAL_FLOW=['scan','newsdesk','research','fact_check','journalist','media','final_editor','release']
def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except Exception:return default
def load_attempts():
    rows=[]
    if not ATTEMPTS.exists():return rows
    for line in ATTEMPTS.read_text(encoding='utf-8').splitlines():
        try:rows.append(json.loads(line))
        except Exception:pass
    return rows
def parse_dt(value):
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None
def classify(row):
    reason=str(row.get('reason') or '').lower(); stage=str(row.get('stage') or '').lower()
    if any(x in reason for x in ['quota','rate limit','timeout','runtime-error','connection','network']):return 'infrastructure','Ret drift eller genkør; ændr ikke redaktionelle krav.'
    if 'language' in reason or 'sprog' in reason:return 'repairable','Lokal sprogreparation; genresearch ikke.'
    if 'seo' in reason or 'metadata' in reason:return 'technical','Reparer deterministisk; må ikke være redaktionelt stop.'
    if 'image' in reason or 'billede' in reason or stage=='media':return 'media','Send kun til Media; tekstkæden skal ikke genkøres.'
    if 'fact' in reason or 'claim' in reason or 'source' in reason or 'kilde' in reason or stage=='research':return 'evidence','Send kun konkret evidensmangel til Research/Fact checker.'
    if 'ethic' in reason or 'etik' in reason or 'fairness' in reason or 'forelægg' in reason:return 'fairness','Løs konkret fairnessproblem lokalt; ingen automatisk deadline eller generel gate.'
    if 'final' in reason:return 'editorial','Skeln mellem lokal tekstreparation og reel evidensmangel.'
    return 'review','Diagnostisk efterkontrol; opret ikke nye gates.'
def stage_from_reason(row):
    stage=str(row.get('stage') or '').lower().replace('-','_')
    if stage:return stage
    reason=str(row.get('reason') or '').lower()
    for key in ['newsdesk','research','fact_check','journalist','language','ethics','media','final_editor','release']:
        if key.replace('_',' ') in reason or key in reason:return key
    return 'unknown'
def main():
    now=datetime.now(timezone.utc); day=now.astimezone(DK).date(); attempts=load_attempts(); rejected=[x for x in attempts if str(x.get('status') or '').lower() not in {'approved','published','pass'}]
    today=[x for x in rejected if parse_dt(x.get('at')) and parse_dt(x.get('at')).astimezone(DK).date()==day]; last7=[x for x in rejected if parse_dt(x.get('at')) and parse_dt(x.get('at'))>=now-timedelta(days=7)]
    reviews=[]
    for x in sorted(today,key=lambda r:str(r.get('at') or ''),reverse=True):
        cls,assessment=classify(x); reviews.append({'at':x.get('at'),'slug':x.get('slug'),'title':x.get('title'),'stage':stage_from_reason(x),'reason':x.get('reason'),'class':cls,'assessment':assessment})
    counts=Counter(stage_from_reason(x) for x in last7); health=load_json(HEALTH,{'articles':[]}); blockers=[{'slug':a.get('slug'),'title':a.get('title'),'resume_from':a.get('resume_from'),'reasons':a.get('reasons') or []} for a in health.get('articles') or [] if a.get('reasons')]
    result={'schema_version':2,'generated_at':now.isoformat().replace('+00:00','Z'),'date_dk':day.isoformat(),'policy':{'diagnostic_only':True,'automatic_rule_changes':False,'principle':'Færre fejl, færre afvisninger og færre neurons pr. godkendt artikel. Feedback må ikke skabe nye gates.'},'canonical_flow':CANONICAL_FLOW,'today':{'rejections':len(today),'reviews':reviews},'last7_stage_counts':dict(sorted(counts.items())),'current_blockers':blockers}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(f'Pipeline feedback: {len(today)} rejection reviews; diagnostic only')
if __name__=='__main__':main()
