#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ATTEMPTS = ROOT / 'reports' / 'editorial' / 'publication-attempts.jsonl'
HEALTH = ROOT / 'reports' / 'editorial' / 'pipeline-health.json'
THRESHOLDS = ROOT / 'config' / 'pipeline-thresholds.json'
OUT = ROOT / 'reports' / 'editorial' / 'pipeline-feedback.json'
DK = ZoneInfo('Europe/Copenhagen')


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except Exception:
        return default


def load_attempts():
    rows=[]
    if not ATTEMPTS.exists(): return rows
    for line in ATTEMPTS.read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows


def parse_dt(value):
    try: return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception: return None


def classify(row):
    reason=str(row.get('reason') or '').lower()
    stage=str(row.get('stage') or '').lower()
    if any(x in reason for x in ['used up your daily free allocation','quota','rate limit','timeout','runtime-error','connection','network']):
        return ('infrastructure','Ingen redaktionel tærskel bør ændres. Løs kapacitet/drift eller genkør forsøget.')
    if 'ledger' in reason or 'schema' in reason or 'approval' in reason and 'missing' in reason:
        return ('process','Bevar kvalitetskravet; reparer dokumentation/legacy-format automatisk, hvis evidensen faktisk findes.')
    if 'language' in reason or 'sprog' in reason:
        return ('repairable','Sprog bør normalt auto-repareres. Hvis samme fejl gentages, test flere auto-repair-cycles før blokering.')
    if 'seo' in reason:
        return ('repairable','SEO bør normalt auto-repareres. Gentagne stop bør flyttes fra hard stop til automatisk reparation før final editor.')
    if 'image' in reason or 'billede' in reason:
        return ('repairable','Tekniske billedproblemer bør normalt auto-repareres; rettigheds- eller integritetsproblemer skal fortsat blokere.')
    if 'færre end to' in reason or 'fact' in reason or 'claim' in reason:
        return ('evidence','Bevar fact-check som hard gate. Undersøg først kildeindhentning og claim-opdeling før krav sænkes.')
    if 'source' in reason or 'kilde' in reason or 'coverage' in reason or stage=='research':
        return ('evidence','Bevar kildekrav som udgangspunkt. Undersøg om fetch, source-grouping eller legacy-data skaber falske stop.')
    if 'ethic' in reason or 'etik' in reason or 'forelægg' in reason or 'right of reply' in reason:
        return ('safety','Ingen lempelse anbefales: etik og forelæggelse er hard gates.')
    if 'final' in reason:
        return ('editorial','Bevar final editor som hard gate; skel mellem materielle fejl og reparerbare formalia.')
    return ('review','Manuel pipeline-vurdering: afgør om blokeringen beskyttede kvalitet eller var unødig friktion.')


def stage_from_reason(row):
    reason=str(row.get('reason') or '').lower(); stage=str(row.get('stage') or '').lower()
    for key in ['newsdesk','research','fact_check','desk_recheck','journalist','language','ethics','image','seo','final_editor','publisher','live_qa']:
        variants={key,key.replace('_',' '),key.replace('_','-')}
        if any(v in reason or v==stage for v in variants): return key
    if 'fact' in stage: return 'fact_check'
    if 'runtime' in stage: return 'infrastructure'
    return stage or 'unknown'


def main():
    now=datetime.now(timezone.utc); now_dk=now.astimezone(DK)
    attempts=load_attempts(); rejected=[x for x in attempts if str(x.get('status') or '').lower() not in {'approved','published','pass'}]
    today=[x for x in rejected if parse_dt(x.get('at')) and parse_dt(x.get('at')).astimezone(DK).date()==now_dk.date()]
    last7=[x for x in rejected if parse_dt(x.get('at')) and parse_dt(x.get('at'))>=now-timedelta(days=7)]
    reviews=[]
    for x in sorted(today,key=lambda r:str(r.get('at') or ''),reverse=True):
        cls,assessment=classify(x)
        reviews.append({
            'at':x.get('at'),'slug':x.get('slug'),'title':x.get('title'),'stage':stage_from_reason(x),
            'reason':x.get('reason'),'class':cls,'assessment':assessment,
            'pipeline_change_considered':True,
        })

    counts=Counter(stage_from_reason(x) for x in last7)
    suggestions=[]
    if counts['language'] >= 2:
        suggestions.append({'stage':'language','parameter':'max_auto_repair_cycles','current':1,'proposed':2,'status':'experiment','why':f'{counts["language"]} sprogstop på 7 dage; test én ekstra automatisk reparation før blokering.'})
    if counts['seo'] >= 2:
        suggestions.append({'stage':'seo','parameter':'repair_policy','current':'1 auto-repair','proposed':'2 auto-repair','status':'experiment','why':f'{counts["seo"]} SEO-stop på 7 dage; dette er normalt reparerbar friktion.'})
    if counts['image'] >= 2:
        suggestions.append({'stage':'image','parameter':'technical_auto_repair','current':1,'proposed':2,'status':'experiment','why':f'{counts["image"]} billedstop på 7 dage; gælder kun tekniske/promptmæssige fejl, ikke rettigheder/integritet.'})
    evidence_stops=counts['research']+counts['fact_check']
    if evidence_stops >= 3:
        suggestions.append({'stage':'research','parameter':'source_retrieval','current':'2 kilder / 3 gruppe-mål','proposed':'bevar tærskel; forbedr retrieval','status':'investigate','why':f'{evidence_stops} evidensstop på 7 dage. Før krav sænkes skal source fetch, syndikering og source_group-lineage måles.'})
    infra=counts['infrastructure']
    if infra:
        suggestions.append({'stage':'infrastructure','parameter':'capacity','current':'observeret driftsstop','proposed':'genkør/kapacitetsstyring','status':'fix-system','why':f'{infra} driftsstop på 7 dage er ikke et argument for at svække redaktionelle gates.'})

    health=load_json(HEALTH,{'articles':[]})
    blockers=[]
    for a in health.get('articles') or []:
        if not a.get('reasons'): continue
        blockers.append({'slug':a.get('slug'),'title':a.get('title'),'resume_from':a.get('resume_from'),'reasons':a.get('reasons') or []})

    thresholds=load_json(THRESHOLDS,{'stages':[]})
    result={
        'schema_version':1,
        'generated_at':now.isoformat().replace('+00:00','Z'),
        'date_dk':now_dk.date().isoformat(),
        'policy':{
            'review_every_rejection':True,
            'automatic_threshold_changes':False,
            'hard_gates_not_relaxed_automatically':['fact_check','ethics','right_of_reply','final_editor'],
            'rule':'Hver afvisning vurderes for falsk blokering, reparerbar friktion eller legitim hard gate. Ændringer foreslås først; målbare eksperimenter kan derefter skrues op/ned.'
        },
        'today':{'rejections':len(today),'reviews':reviews},
        'last7_stage_counts':dict(sorted(counts.items())),
        'suggested_adjustments':suggestions,
        'current_blockers':blockers,
        'flow':thresholds.get('stages') or [],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Pipeline feedback: {len(today)} rejection reviews, {len(suggestions)} suggestions')


if __name__=='__main__': main()
