#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'editorial'/'publication-attempts.jsonl'

def reason_code(status,stage,reason):
 r=(reason or '').lower();s=(stage or '').lower()
 if status=='approved':return 'approved'
 if s=='research' and ('ingen brugbar' in r or 'fetch' in r):return 'research_no_evidence'
 if s=='media-scout':return 'media_scout_pending'
 if s=='media':return 'media_no_legal_hero'
 if s=='fact-check':return 'fact_no_publishable_claim'
 if s=='ethics':return 'ethics_or_ror'
 if s=='final-editor':return 'final_editor_block'
 if s=='newsdesk':return 'newsdesk_selection'
 return f"{s or 'unknown'}_other"

def assessment(status,stage,reason):
 r=(reason or '').lower(); s=(stage or '').lower()
 if status=='approved': return ('published','Godkendt af pipeline','Ingen justering nødvendig.')
 hard=['fact check','fact-check','modsig','etik','duplicate','dublet']
 fix=['language','sprog','seo','image','hero','metadata','schema','format','timeout','fetch','læsbart materiale']
 if any(x in r for x in hard) or s in {'ethics','fact-check'}:
  return ('blocked-correct','Blokeringen beskytter en reel faktuel eller etisk risiko.','Send kun den konkrete mangel til dens eksisterende ejer.')
 if any(x in r for x in fix) or s in {'final-editor','research'}:
  return ('blocked-review','Blokeringen kan være korrekt, men ligner en reparerbar pipeline-/inputmangel.','Forsøg automatisk reparation/research før permanent blokering; gennemgå gentagne mønstre i QA.')
 return ('blocked-review','Blokeringen kræver efterkontrol; årsagen er ikke entydigt klassificeret.','Behold artiklen blokeret nu, men vurder om pipelinen er for streng.')

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);a=p.parse_args()
 payload=json.loads(Path(a.input).read_text(encoding='utf-8'));status=str(payload.get('status') or 'unknown');stage=str(payload.get('stage') or ('release' if status=='approved' else 'unknown'));reason=str(payload.get('reason') or '')
 verdict,why,adjust=assessment(status,stage,reason); article=payload.get('article') or {}
 audit=payload.get('audit') or {}; assignment=audit.get('assignment') or {}; research=audit.get('research') or {}; fact=audit.get('fact_check') or {}
 row={'at':payload.get('generated_at') or datetime.now(timezone.utc).isoformat(timespec='seconds'),'status':status,'stage':stage,'slug':payload.get('slug') or article.get('slug'),'title':article.get('title') or payload.get('title') or audit.get('article_title') or assignment.get('title_hint') or payload.get('slug') or 'Ikke navngivet kandidat','reason':reason or ('Godkendt' if status=='approved' else 'Ingen begrundelse registreret'),'assessment':verdict,'assessment_text':why,'pipeline_action':adjust,'reason_code':reason_code(status,stage,reason),'ai_usage':payload.get('ai_usage'),'diagnostics':{'assignment':assignment,'candidate_claims':research.get('candidate_claims') or [],'researched':research.get('researched') or [],'fact_claims':fact.get('claims') or [],'sources':audit.get('sources') or [],'selected_signals':audit.get('selected_signals') or []}}
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with OUT.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 print(json.dumps(row,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
