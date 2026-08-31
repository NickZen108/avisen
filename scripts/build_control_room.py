#!/usr/bin/env python3
from __future__ import annotations
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEALTH=ROOT/'reports'/'editorial'/'pipeline-health.json'
OUT=ROOT/'docs'/'kontrolrum'/'index.html'

def e(x): return html.escape(str(x or ''),quote=True)
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def badge(status):
    s=str(status or 'ukendt')
    cls='ok' if s=='published' else ('warn' if s in {'checking','editing','researching','ready','scheduled'} else 'muted')
    return f'<span class="badge {cls}">{e(s)}</span>'
def main():
    data=load(HEALTH) if HEALTH.exists() else {'generated_at':None,'counts':{},'blocked_count':0,'articles':[]}
    arts=data.get('articles') or []
    published=sum(1 for a in arts if a.get('status')=='published')
    active=sum(1 for a in arts if a.get('status') in {'researching','checking','editing','ready','scheduled'})
    blocked=sum(1 for a in arts if a.get('reasons'))
    rows=[]
    for a in sorted(arts,key=lambda x:(0 if x.get('reasons') else 1,str(x.get('title') or ''))):
        reasons='<br>'.join(e(x) for x in a.get('reasons') or []) or '—'
        resume=e(a.get('resume_from') or '—')
        rows.append(f'<tr><td><strong>{e(a.get("title") or a.get("slug"))}</strong><small>{e(a.get("slug"))}</small></td><td>{badge(a.get("status"))}</td><td>{resume}</td><td>{reasons}</td></tr>')
    page=f'''<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Kontrolrum – Morgentidende</title><link href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@700&family=Source+Serif+4:wght@400;600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet"><style>
:root{{--paper:#f8f5ef;--ink:#161513;--muted:#6f6a62;--dark:#1b2430;--rule:#d8d2c8;--ok:#e7f3e9;--warn:#fff2cc}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Source Sans 3",sans-serif}}header{{background:var(--dark);color:white;padding:18px 24px}}header strong{{font:700 26px "Roboto Slab",serif}}main{{max-width:1180px;margin:auto;padding:28px 22px 60px}}h1{{font:600 42px/1.05 "Source Serif 4",serif;margin:0 0 8px}}.intro{{color:var(--muted);max-width:720px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:26px 0}}.card{{background:#fff;border:1px solid var(--rule);padding:18px}}.card b{{display:block;font:700 34px "Roboto Slab",serif}}.card span{{color:var(--muted)}}table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule)}}th,td{{text-align:left;padding:13px 12px;border-bottom:1px solid var(--rule);vertical-align:top}}th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em}}td small{{display:block;color:var(--muted);margin-top:4px;word-break:break-all}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:#eee;font-weight:700;font-size:12px}}.badge.ok{{background:var(--ok)}}.badge.warn{{background:var(--warn)}}.note{{margin-top:18px;padding:14px;border-left:4px solid #c9a227;background:#fff}}@media(max-width:760px){{.cards{{grid-template-columns:1fr}}h1{{font-size:34px}}table,thead,tbody,tr,th,td{{display:block}}thead{{display:none}}tr{{border-bottom:1px solid var(--rule)}}td{{border:0;padding:8px 12px}}}}
</style></head><body><header><strong>Morgentidende · Kontrolrum</strong></header><main><h1>Maskinrummet</h1><p class="intro">Read-only status for pipeline v2. Her kan du se, hvad der er publiceret, hvad der arbejder videre, og præcis hvorfor en artikel er parkeret.</p><div class="cards"><div class="card"><b>{published}</b><span>publicerede pipeline-v2 artikler</span></div><div class="card"><b>{active}</b><span>under arbejde / klar</span></div><div class="card"><b>{blocked}</b><span>med aktiv stopårsag</span></div></div><table><thead><tr><th>Artikel</th><th>Status</th><th>Fortsæt fra</th><th>Teknisk diagnose</th></tr></thead><tbody>{''.join(rows)}</tbody></table><div class="note"><strong>V1 er read-only.</strong> Siden indeholder ingen hemmelige nøgler eller persondata og er markeret noindex. Rigtigt login, roller og skriveadgang skal ligge bag autentificering i næste trin – ikke bag en skjult URL.</div><p class="intro">Senest genereret: {e(data.get('generated_at') or 'ikke endnu')}</p></main></body></html>'''
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(page,encoding='utf-8'); print('Control room built')
if __name__=='__main__': main()
