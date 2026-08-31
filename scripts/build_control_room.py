#!/usr/bin/env python3
from __future__ import annotations
import html,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEALTH=ROOT/'reports'/'editorial'/'pipeline-health.json'
COLUMN_EVENTS=ROOT/'reports'/'editorial'/'column-review-events.json'
OUT=ROOT/'docs'/'kontrolrum'/'index.html'

def e(x): return html.escape(str(x or ''),quote=True)
def load(p,default):
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default
def badge(status):
    s=str(status or 'ukendt')
    cls='ok' if s in {'published','PASS'} else ('warn' if s in {'checking','editing','researching','ready','scheduled','REVISE'} else ('bad' if s in {'ESCALATE','rejected','failed'} else 'muted'))
    return f'<span class="badge {cls}">{e(s)}</span>'
def main():
    data=load(HEALTH,{'generated_at':None,'counts':{},'blocked_count':0,'articles':[]})
    arts=data.get('articles') or []
    events=(load(COLUMN_EVENTS,{'events':[]}).get('events') or [])
    published=sum(1 for a in arts if a.get('status')=='published')
    active=sum(1 for a in arts if a.get('status') in {'researching','checking','editing','ready','scheduled'})
    blocked=sum(1 for a in arts if a.get('reasons'))
    attention=[x for x in events if str(x.get('status') or '').upper() in {'REVISE','ESCALATE'}]
    stage_counts=collections.Counter(str(a.get('resume_from') or a.get('status') or 'ukendt') for a in arts if a.get('status')!='published')
    reason_counts=collections.Counter()
    for a in arts:
        for reason in a.get('reasons') or []:
            key=str(reason).split(':',1)[0].strip()
            reason_counts[key]+=1
    rows=[]
    for a in sorted(arts,key=lambda x:(0 if x.get('reasons') else 1,str(x.get('title') or ''))):
        reasons='<br>'.join(e(x) for x in a.get('reasons') or []) or '—'
        resume=e(a.get('resume_from') or '—')
        rows.append(f'<tr><td><strong>{e(a.get("title") or a.get("slug"))}</strong><small>{e(a.get("slug"))}</small></td><td>{badge(a.get("status"))}</td><td>{resume}</td><td>{reasons}</td></tr>')
    stage_html=''.join(f'<li><span>{e(k)}</span><b>{v}</b></li>' for k,v in stage_counts.most_common()) or '<li><span>Ingen aktive artikler</span><b>0</b></li>'
    reason_html=''.join(f'<li><span>{e(k)}</span><b>{v}</b></li>' for k,v in reason_counts.most_common(8)) or '<li><span>Ingen stopårsager</span><b>0</b></li>'
    column_rows=[]
    for x in sorted(attention,key=lambda y:str(y.get('created_at') or ''),reverse=True)[:20]:
        column_rows.append(f'<tr><td><strong>{e(x.get("title") or "Uden titel")}</strong><small>{e(x.get("column_id") or "—")}</small></td><td>{badge(str(x.get("status") or "").upper())}</td><td>{e(x.get("risk_type") or "—")}</td><td>{e(x.get("reason") or "—")}</td><td>{e(x.get("created_at") or "—")}</td></tr>')
    column_section=''.join(column_rows) or '<tr><td colspan="5">Ingen afviste eller eskalerede kronikker.</td></tr>'
    page=f'''<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Kontrolrum – Morgentidende</title><link href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@700&family=Source+Serif+4:wght@400;600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet"><style>
:root{{--paper:#f8f5ef;--ink:#161513;--muted:#6f6a62;--dark:#1b2430;--rule:#d8d2c8;--ok:#e7f3e9;--warn:#fff2cc;--bad:#f8ded9}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Source Sans 3",sans-serif}}header{{background:var(--dark);color:white;padding:18px 24px}}header .inner{{max-width:1180px;margin:auto;display:flex;justify-content:space-between;align-items:center;gap:16px}}header strong{{font:700 26px "Roboto Slab",serif}}header a{{color:#fff;text-decoration:none;font-weight:600}}main{{max-width:1180px;margin:auto;padding:28px 22px 60px}}h1{{font:600 42px/1.05 "Source Serif 4",serif;margin:0 0 8px}}h2{{font:600 28px/1.1 "Source Serif 4",serif;margin:34px 0 12px}}.intro{{color:var(--muted);max-width:780px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}}.card,.panel{{background:#fff;border:1px solid var(--rule);padding:18px}}.card b{{display:block;font:700 34px "Roboto Slab",serif}}.card span{{color:var(--muted)}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0 28px}}.metric-list{{list-style:none;margin:0;padding:0}}.metric-list li{{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid #eee}}.metric-list li:last-child{{border-bottom:0}}table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule)}}th,td{{text-align:left;padding:13px 12px;border-bottom:1px solid var(--rule);vertical-align:top}}th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em}}td small{{display:block;color:var(--muted);margin-top:4px;word-break:break-all}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:#eee;font-weight:700;font-size:12px}}.badge.ok{{background:var(--ok)}}.badge.warn{{background:var(--warn)}}.badge.bad{{background:var(--bad)}}.note{{margin-top:18px;padding:14px;border-left:4px solid #c9a227;background:#fff}}@media(max-width:760px){{.cards,.two{{grid-template-columns:1fr 1fr}}h1{{font-size:34px}}table,thead,tbody,tr,th,td{{display:block}}thead{{display:none}}tr{{border-bottom:1px solid var(--rule)}}td{{border:0;padding:8px 12px}}}}@media(max-width:480px){{.cards,.two{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="inner"><strong>Morgentidende · Kontrolrum</strong><a href="../">Til avisen</a></div></header><main><h1>Maskinrummet</h1><p class="intro">Pipeline-status, flaskehalse og kronikker der kræver opmærksomhed. Målet er at skelne mellem sund redaktionel kontrol og unødige tekniske stop.</p><div class="cards"><div class="card"><b>{published}</b><span>publiceret</span></div><div class="card"><b>{active}</b><span>under arbejde / klar</span></div><div class="card"><b>{blocked}</b><span>med aktiv stopårsag</span></div><div class="card"><b>{len(attention)}</b><span>kronikker kræver opmærksomhed</span></div></div><div class="two"><section class="panel"><h2 style="margin-top:0">Aktive trin</h2><ul class="metric-list">{stage_html}</ul></section><section class="panel"><h2 style="margin-top:0">Hyppigste stopårsager</h2><ul class="metric-list">{reason_html}</ul></section></div><h2>Artikler i pipeline</h2><table><thead><tr><th>Artikel</th><th>Status</th><th>Fortsæt fra</th><th>Teknisk diagnose</th></tr></thead><tbody>{''.join(rows)}</tbody></table><h2>Kronikker der kræver opmærksomhed</h2><p class="intro">Kronik-agentens REVISE og ESCALATE bliver vist her. Kronikøren får samtidig selv den konkrete begrundelse.</p><table><thead><tr><th>Kronik</th><th>Status</th><th>Risikotype</th><th>Årsag</th><th>Tid</th></tr></thead><tbody>{column_section}</tbody></table><div class="note"><strong>V1 er driftsdashboardet.</strong> Det viser pipeline, flaskehalse og kronik-advarsler. Det er stadig read-only, indtil sikker rollebaseret login er koblet på; vi lægger ikke redaktionelle skrivehandlinger bag en skjult URL.</div><p class="intro">Senest genereret: {e(data.get('generated_at') or 'ikke endnu')}</p></main></body></html>'''
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(page,encoding='utf-8'); print('Control room built')
if __name__=='__main__': main()
