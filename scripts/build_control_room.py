#!/usr/bin/env python3
from __future__ import annotations
import html, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / 'reports' / 'editorial' / 'pipeline-health.json'
READY = ROOT / 'reports' / 'editorial' / 'production-readiness.json'
ANALYTICS = ROOT / 'reports' / 'editorial' / 'editorial-analytics.json'
ATTEMPTS = ROOT / 'reports' / 'editorial' / 'publication-attempts.jsonl'
RESET = ROOT / 'reports' / 'editorial' / 'control-room-reset.json'
OUT = ROOT / 'docs' / 'kontrolrum' / 'index.html'
DK = ZoneInfo('Europe/Copenhagen')


def e(x): return html.escape(str(x or ''), quote=True)
def load(path, default):
    try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except Exception: return default

def load_attempts():
    rows=[]
    if not ATTEMPTS.exists(): return rows
    for line in ATTEMPTS.read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows

def dt(value):
    try: return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception: return None

def dk_time(value):
    parsed=dt(value)
    return parsed.astimezone(DK).strftime('%d-%m-%Y kl. %H:%M:%S') if parsed else 'ikke endnu'

def num(value, digits=0):
    try:
        n=float(value)
        return f'{n:,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')
    except Exception: return '0'

def badge(status):
    s=str(status or 'ukendt'); low=s.lower()
    cls='ok' if low in {'published','approved','pass','green'} else ('bad' if low in {'hold','blocked','blocked-correct','failed','red'} else 'warn')
    return f'<span class="badge {cls}">{e(s)}</span>'

def window_rows(attempts, days):
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    return [x for x in attempts if dt(x.get('at')) and dt(x.get('at'))>=cutoff]

def usage_of(row): return row.get('ai_usage') if isinstance(row.get('ai_usage'),dict) else None

def usage_totals(rows):
    measured=[usage_of(x) for x in rows if usage_of(x)]
    return {
        'measured':len(measured),'attempts':len(rows),
        'prompt_tokens':sum(int(x.get('prompt_tokens') or 0) for x in measured),
        'completion_tokens':sum(int(x.get('completion_tokens') or 0) for x in measured),
        'total_tokens':sum(int(x.get('total_tokens') or 0) for x in measured),
        'neurons':sum(float(x.get('estimated_neurons') or 0) for x in measured),
    }

def usage_cell(row):
    u=usage_of(row)
    if not u: return '<span class="muted">Ikke målt</span>'
    total=int(u.get('total_tokens') or 0); prompt=int(u.get('prompt_tokens') or 0); completion=int(u.get('completion_tokens') or 0); neurons=float(u.get('estimated_neurons') or 0)
    return f'<strong>{num(total)} tokens</strong><small>{num(prompt)} ind · {num(completion)} ud<br>≈ {num(neurons,1)} neurons · {int(u.get("calls") or 0)} AI-kald</small>'

def report_block(title, rows, open_default=False):
    approved=[x for x in rows if x.get('status')=='approved']; blocked=[x for x in rows if x.get('status')!='approved']; u=usage_totals(rows)
    measured_note=f'{u["measured"]}/{u["attempts"]} forsøg målt' if u['attempts'] else 'ingen forsøg'
    cards=(
      '<div class="cards">'
      f'<div class="card tone-blue"><b>{len(rows)}</b><span>forsøg</span></div>'
      f'<div class="card tone-green"><b>{len(approved)}</b><span>godkendt</span></div>'
      f'<div class="card tone-rose"><b>{len(blocked)}</b><span>blokeret</span></div>'
      f'<div class="card tone-gold"><b>{round(100*len(approved)/len(rows)) if rows else 0}%</b><span>godkendelsesrate</span></div>'
      f'<div class="card tone-blue"><b>{num(u["total_tokens"])}</b><span>tokens</span><small>{e(measured_note)}</small></div>'
      f'<div class="card tone-purple"><b>≈ {num(u["neurons"],1)}</b><span>neurons</span><small>{e(measured_note)}</small></div>'
      '</div>')
    if rows:
        body=''.join(
          f'<tr><td>{e(dk_time(x.get("at")))}</td><td><strong>{e(x.get("title"))}</strong><small>{e(x.get("slug"))}</small></td>'
          f'<td>{badge(x.get("status"))}<small>{e(x.get("stage"))}</small></td><td>{usage_cell(x)}</td><td>{e(x.get("reason"))}</td>'
          f'<td>{e(x.get("assessment_text"))}<small><strong>Pipeline:</strong> {e(x.get("pipeline_action"))}</small></td></tr>'
          for x in sorted(rows,key=lambda y:str(y.get('at')),reverse=True))
    else: body='<tr><td colspan="6">Ingen registrerede forsøg endnu.</td></tr>'
    table=f'<table><thead><tr><th>Tid (dansk)</th><th>Artikel</th><th>Resultat</th><th>AI-forbrug</th><th>Hvorfor</th><th>Vurdering</th></tr></thead><tbody>{body}</tbody></table>'
    note='<p class="usage-note">Tokens kommer fra Cloudflares usage-data. Neurons vises med ≈, fordi de beregnes ud fra Cloudflares publicerede modelrater; billedforbrug er et konservativt estimat. Ældre forsøg fra før målingen blev aktiveret kan stå som “Ikke målt”.</p>'
    content=cards+table+note
    return f'<section><h2>{e(title)}</h2>{content}</section>' if open_default else f'<details><summary>{e(title)} · {len(rows)} forsøg</summary>{content}</details>'

def main():
    data=load(HEALTH,{'generated_at':None,'articles':[]}); ready=load(READY,{'status':'ukendt','hard_failures':[],'warnings':[],'metrics':{}}); analytics=load(ANALYTICS,{})
    arts=data.get('articles') or []; attempts=load_attempts(); now_dk=datetime.now(DK)
    reset=load(RESET,{})
    reset_at=dt(reset.get('reset_at'))
    if reset_at:
        attempts=[x for x in attempts if dt(x.get('at')) and dt(x.get('at')) >= reset_at]
    today=[x for x in attempts if dt(x.get('at')) and dt(x.get('at')).astimezone(DK).date()==now_dk.date()]
    pipeline_rows=[]
    for a in sorted(arts,key=lambda x:(0 if x.get('reasons') else 1,str(x.get('title') or ''))):
        reasons='<br>'.join(e(x) for x in a.get('reasons') or []) or '—'
        pipeline_rows.append(f'<tr><td><strong>{e(a.get("title") or a.get("slug"))}</strong><small>{e(a.get("slug"))}</small></td><td>{badge(a.get("status"))}</td><td>{e(a.get("resume_from") or "—")}</td><td>{reasons}</td></tr>')
    m=ready.get('metrics') or {}; published=sum(1 for a in arts if a.get('status')=='published'); active=sum(1 for a in arts if a.get('status') in {'researching','checking','editing','ready','scheduled'}); blocked=sum(1 for a in arts if a.get('reasons'))
    reports=report_block('I dag',today,True)+report_block('Seneste 7 dage',window_rows(attempts,7))+report_block('Seneste 30 dage',window_rows(attempts,30)); generated=e(dk_time(data.get('generated_at')))
    page=f'''<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="30"><title>Kontrolrum – Morgentidende</title><style>
:root{{--paper:#f5f1e9;--surface:#fffdf8;--surface-2:#eee8dd;--ink:#1d2025;--muted:#6f6b66;--header:#243246;--rule:#d7d0c6;--blue:#e5edf5;--green:#e4efe7;--rose:#f2e5e4;--gold:#f2ead4;--purple:#e9e3f1;--ok:#dcebdd;--warn:#f4e7bd;--bad:#efd9d7;--shadow:0 6px 20px rgba(35,40,48,.06)}}
html[data-theme="dark"]{{--paper:#15191f;--surface:#20262e;--surface-2:#2a313a;--ink:#edf0f2;--muted:#abb3bc;--header:#111820;--rule:#3b444f;--blue:#273747;--green:#263a31;--rose:#432f33;--gold:#403a29;--purple:#352f43;--ok:#284333;--warn:#4d4123;--bad:#4a2d31;--shadow:0 8px 24px rgba(0,0,0,.2)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}}header{{background:var(--header);color:#fff;padding:16px 24px;box-shadow:var(--shadow)}}header .inner,main{{max-width:1220px;margin:auto}}header .inner{{display:flex;align-items:center;justify-content:space-between;gap:16px}}.header-actions{{display:flex;align-items:center;gap:14px}}header a{{color:#fff}}button.theme-toggle{{border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.08);color:#fff;border-radius:999px;padding:7px 11px;cursor:pointer;font-weight:700}}main{{padding:24px 22px 60px}}h1,h2{{font-family:Georgia,serif}}h1{{font-size:42px;margin:0 0 6px}}h2{{font-size:28px;margin:30px 0 12px}}.intro,.muted,small,.usage-note{{color:var(--muted)}}small{{display:block;margin-top:4px}}.usage-note{{font-size:12px;margin:-8px 0 18px}}.freshness{{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;background:var(--surface);border:1px solid var(--rule);border-left:5px solid #7892ab;padding:11px 14px;margin:0 0 22px;border-radius:8px;box-shadow:var(--shadow)}}.freshness strong{{font-size:14px}}.freshness span{{font-variant-numeric:tabular-nums}}.freshness .live{{margin-left:auto;color:var(--muted);font-size:13px}}.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:16px 0}}.card{{background:var(--surface);border:1px solid var(--rule);padding:16px;border-radius:9px;box-shadow:var(--shadow)}}.card b{{display:block;font-size:26px}}.tone-blue{{background:var(--blue)}}.tone-green{{background:var(--green)}}.tone-rose{{background:var(--rose)}}.tone-gold{{background:var(--gold)}}.tone-purple{{background:var(--purple)}}table{{width:100%;border-collapse:separate;border-spacing:0;background:var(--surface);border:1px solid var(--rule);border-radius:9px;overflow:hidden;margin-bottom:18px;box-shadow:var(--shadow)}}th,td{{text-align:left;padding:12px;border-bottom:1px solid var(--rule);vertical-align:top}}th{{background:var(--surface-2);font-size:13px}}tr:last-child td{{border-bottom:0}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:var(--surface-2);font-weight:700;font-size:12px}}.badge.ok{{background:var(--ok)}}.badge.warn{{background:var(--warn)}}.badge.bad{{background:var(--bad)}}details{{background:var(--surface);border:1px solid var(--rule);border-radius:9px;margin:14px 0;padding:14px;box-shadow:var(--shadow)}}summary{{cursor:pointer;font:600 24px Georgia,serif}}@media(max-width:980px){{.cards{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}header .inner{{align-items:flex-start}}.header-actions{{flex-direction:column;align-items:flex-end;gap:8px}}.freshness .live{{margin-left:0;width:100%}}table,thead,tbody,tr,th,td{{display:block}}thead{{display:none}}}}
</style></head><body><header><div class="inner"><strong>Morgentidende · Kontrolrum</strong><div class="header-actions"><button class="theme-toggle" id="theme-toggle" type="button">Dark mode</button><a href="../">Til avisen</a></div></div></header><main><div class="freshness"><strong>Data senest genereret:</strong><span>{generated}</span><span class="live">Siden hentet: <b id="loaded-at">nu</b> · næste opdatering om <b id="countdown">30</b> sek.</span></div><h1>Maskinrummet</h1><p class="intro">Dagens produktionsrapport står øverst. Hvert forsøg viser resultat, konkret årsag, vurdering og nu også AI-forbrug.</p>{f'<p class="usage-note">Visning nulstillet: {e(dk_time(reset.get("reset_at")))}</p>' if reset_at else ''}{reports}<h2>Nuværende pipeline</h2><div class="cards"><div class="card tone-blue"><b>{published}</b><span>publiceret</span></div><div class="card tone-gold"><b>{active}</b><span>aktive</span></div><div class="card tone-rose"><b>{blocked}</b><span>blokerede</span></div><div class="card tone-green"><b>{badge(ready.get('status'))}</b><span>readiness</span></div></div><table><thead><tr><th>Artikel</th><th>Status</th><th>Fortsæt fra</th><th>Diagnose</th></tr></thead><tbody>{''.join(pipeline_rows)}</tbody></table><p class="intro">Kildehosts: {e(analytics.get('unique_source_hosts') or 0)} · dubletflags: {len(m.get('possible_duplicate_pairs') or [])}</p></main><script>
(()=>{{const root=document.documentElement,btn=document.getElementById('theme-toggle');const saved=localStorage.getItem('mt-control-theme');const initial=saved||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');const apply=t=>{{root.dataset.theme=t;btn.textContent=t==='dark'?'Light mode':'Dark mode'}};apply(initial);btn.addEventListener('click',()=>{{const next=root.dataset.theme==='dark'?'light':'dark';localStorage.setItem('mt-control-theme',next);apply(next)}});const fmt=new Intl.DateTimeFormat('da-DK',{{timeZone:'Europe/Copenhagen',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}});document.getElementById('loaded-at').textContent=fmt.format(new Date()).replace(',',' kl.');let left=30;setInterval(()=>{{if(--left<=0){{location.reload();return}}document.getElementById('countdown').textContent=String(left)}},1000)}})();
</script></body></html>'''
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(page,encoding='utf-8'); print('Control room built with AI usage telemetry, Danish time and 30-second refresh')

if __name__=='__main__': main()
