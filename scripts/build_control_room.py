#!/usr/bin/env python3
from __future__ import annotations
import html,json,collections
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEALTH=ROOT/'reports'/'editorial'/'pipeline-health.json'; READY=ROOT/'reports'/'editorial'/'production-readiness.json'; ANALYTICS=ROOT/'reports'/'editorial'/'editorial-analytics.json'; ATTEMPTS=ROOT/'reports'/'editorial'/'publication-attempts.jsonl'; OUT=ROOT/'docs'/'kontrolrum'/'index.html'
def e(x):return html.escape(str(x or ''),quote=True)
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
 except Exception:return d
def load_attempts():
 out=[]
 if not ATTEMPTS.exists():return out
 for line in ATTEMPTS.read_text(encoding='utf-8').splitlines():
  try:out.append(json.loads(line))
  except Exception:pass
 return out
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
 except Exception:return None
def badge(status):
 s=str(status or 'ukendt'); low=s.lower(); cls='ok' if low in {'published','approved','pass','green'} else ('bad' if low in {'hold','blocked','blocked-correct','failed','red'} else 'warn');return f'<span class="badge {cls}">{e(s)}</span>'
def window_rows(attempts,days):
 cutoff=datetime.now(timezone.utc)-timedelta(days=days);return [x for x in attempts if dt(x.get('at')) and dt(x.get('at'))>=cutoff]
def report_block(title,rows,open_default=False):
 approved=[x for x in rows if x.get('status')=='approved']; blocked=[x for x in rows if x.get('status')!='approved']
 cards=f'<div class="cards"><div class="card"><b>{len(rows)}</b><span>forsøg</span></div><div class="card"><b>{len(approved)}</b><span>godkendt</span></div><div class="card"><b>{len(blocked)}</b><span>blokeret</span></div><div class="card"><b>{round(100*len(approved)/len(rows)) if rows else 0}%</b><span>godkendelsesrate</span></div></div>'
 if rows:
  body=''.join(f'<tr><td>{e(x.get("at"))}</td><td><strong>{e(x.get("title"))}</strong><small>{e(x.get("slug"))}</small></td><td>{badge(x.get("status"))}<small>{e(x.get("stage"))}</small></td><td>{e(x.get("reason"))}</td><td>{e(x.get("assessment_text"))}<small><strong>Pipeline:</strong> {e(x.get("pipeline_action"))}</small></td></tr>' for x in sorted(rows,key=lambda y:str(y.get('at')),reverse=True))
 else:body='<tr><td colspan="5">Ingen registrerede forsøg endnu.</td></tr>'
 table=f'<table><thead><tr><th>Tid</th><th>Artikel</th><th>Resultat</th><th>Hvorfor</th><th>Vurdering</th></tr></thead><tbody>{body}</tbody></table>'
 if open_default:return f'<section><h2>{e(title)}</h2>{cards}{table}</section>'
 return f'<details><summary>{e(title)} · {len(rows)} forsøg</summary>{cards}{table}</details>'
def main():
 data=load(HEALTH,{'generated_at':None,'articles':[]});ready=load(READY,{'status':'ukendt','hard_failures':[],'warnings':[],'metrics':{}});analytics=load(ANALYTICS,{})
 arts=data.get('articles') or [];attempts=load_attempts(); now=datetime.now(timezone.utc); today=[x for x in attempts if dt(x.get('at')) and dt(x.get('at')).date()==now.date()]
 pipeline_rows=[]
 for a in sorted(arts,key=lambda x:(0 if x.get('reasons') else 1,str(x.get('title') or ''))):
  reasons='<br>'.join(e(x) for x in a.get('reasons') or []) or '—';pipeline_rows.append(f'<tr><td><strong>{e(a.get("title") or a.get("slug"))}</strong><small>{e(a.get("slug"))}</small></td><td>{badge(a.get("status"))}</td><td>{e(a.get("resume_from") or "—")}</td><td>{reasons}</td></tr>')
 m=ready.get('metrics') or {};published=sum(1 for a in arts if a.get('status')=='published');active=sum(1 for a in arts if a.get('status') in {'researching','checking','editing','ready','scheduled'});blocked=sum(1 for a in arts if a.get('reasons'))
 reports=report_block('I dag',today,True)+report_block('Seneste 7 dage',window_rows(attempts,7))+report_block('Seneste 30 dage',window_rows(attempts,30))
 page=f'''<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Kontrolrum – Morgentidende</title><style>:root{{--paper:#f8f5ef;--ink:#161513;--muted:#6f6a62;--dark:#1b2430;--rule:#d8d2c8;--ok:#e7f3e9;--warn:#fff2cc;--bad:#f8ded9}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}}header{{background:var(--dark);color:#fff;padding:18px 24px}}header .inner,main{{max-width:1180px;margin:auto}}header .inner{{display:flex;justify-content:space-between}}header a{{color:#fff}}main{{padding:28px 22px 60px}}h1,h2{{font-family:Georgia,serif}}h1{{font-size:42px;margin:0 0 8px}}h2{{font-size:28px;margin:34px 0 12px}}.intro,small{{color:var(--muted)}}small{{display:block;margin-top:4px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}.card{{background:#fff;border:1px solid var(--rule);padding:18px}}.card b{{display:block;font-size:30px}}table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule);margin-bottom:18px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid var(--rule);vertical-align:top}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:#eee;font-weight:700;font-size:12px}}.badge.ok{{background:var(--ok)}}.badge.warn{{background:var(--warn)}}.badge.bad{{background:var(--bad)}}details{{background:#fff;border:1px solid var(--rule);margin:14px 0;padding:14px}}summary{{cursor:pointer;font:600 24px Georgia,serif}}@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}table,thead,tbody,tr,th,td{{display:block}}thead{{display:none}}}}</style></head><body><header><div class="inner"><strong>Morgentidende · Kontrolrum</strong><a href="../">Til avisen</a></div></header><main><h1>Maskinrummet</h1><p class="intro">Dagens produktionsrapport står øverst. Hvert blokeret publiceringsforsøg viser konkret årsag og en vurdering af, om blokeringen bør bevares eller føre til pipelinejustering.</p>{reports}<h2>Nuværende pipeline</h2><div class="cards"><div class="card"><b>{published}</b><span>publiceret</span></div><div class="card"><b>{active}</b><span>aktive</span></div><div class="card"><b>{blocked}</b><span>blokerede</span></div><div class="card"><b>{badge(ready.get('status'))}</b><span>readiness</span></div></div><table><thead><tr><th>Artikel</th><th>Status</th><th>Fortsæt fra</th><th>Diagnose</th></tr></thead><tbody>{''.join(pipeline_rows)}</tbody></table><p class="intro">Senest genereret: {e(data.get('generated_at') or 'ikke endnu')} · kildehosts: {e(analytics.get('unique_source_hosts') or 0)} · dubletflags: {len(m.get('possible_duplicate_pairs') or [])}</p></main></body></html>'''
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(page,encoding='utf-8');print('Control room built with daily/7d/30d reports')
if __name__=='__main__':main()
