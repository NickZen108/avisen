#!/usr/bin/env python3
from __future__ import annotations
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'content'/'short-videos.json'; INDEX=ROOT/'docs'/'index.html'
def e(x): return html.escape(str(x or ''),quote=True)
def main():
    if not DATA.exists() or not INDEX.exists(): return 0
    cfg=json.loads(DATA.read_text(encoding='utf-8')); items=[]
    for x in cfg.get('items') or []:
        if x.get('status')!='verified' or x.get('provider')!='youtube': continue
        vid=re.sub(r'[^A-Za-z0-9_-]','',str(x.get('id') or ''))
        if not vid: continue
        y=dict(x); y['id']=vid; items.append(y)
    minimum=int(cfg.get('minimum_to_render') or 3); maximum=int(cfg.get('maximum_on_frontpage') or 6)
    section=''
    if len(items)>=minimum:
        cards=[]
        for x in items[:maximum]:
            thumb=f'https://i.ytimg.com/vi/{x["id"]}/hqdefault.jpg'
            cards.append(f'<button class="short-video-card" type="button" data-youtube-id="{e(x["id"])}" data-video-title="{e(x.get("title") or "Video")}" aria-label="Afspil: {e(x.get("title") or "Video")}"><img src="{e(thumb)}" alt="" loading="lazy"><span class="short-video-card__shade"></span><strong>{e(x.get("title") or "Video")}</strong><small>{e(x.get("topic") or "Video")}</small><span class="short-video-card__play" aria-hidden="true">▶</span></button>')
        section='<section class="short-videos wrap" aria-labelledby="short-video-title"><div class="short-videos__head"><h2 id="short-video-title">Korte videoer</h2><p>Nyheder, natur, sport, teknologi og øjeblikke værd at se.</p></div><div class="short-videos__rail">'+''.join(cards)+'</div></section><dialog class="video-dialog" id="short-video-dialog"><button class="video-dialog__close" type="button" aria-label="Luk video">×</button><div class="video-dialog__frame"></div></dialog><script src="short-videos.js" defer></script>'
    text=INDEX.read_text(encoding='utf-8')
    marker='<!-- SHORT_VIDEOS -->'
    if marker in text: text=text.replace(marker,section)
    INDEX.write_text(text,encoding='utf-8'); print(f'Short videos rendered: {len(items[:maximum]) if len(items)>=minimum else 0}')
    return 0
if __name__=='__main__': raise SystemExit(main())
