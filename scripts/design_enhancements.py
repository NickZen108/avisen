#!/usr/bin/env python3
"""Editorial layout enhancements applied after the canonical build.

Every article gets two distinct eight-story hero grids. Recommendations are
deterministic, contextual and diverse. The legacy Perspektiv & liv shelf has
been retired in favour of the dedicated front-page magazine blocks.
"""
from __future__ import annotations
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ARTICLES=ROOT/'content'/'articles';DOCS=ROOT/'docs'
FEATURE_CATEGORIES={'Feature','Features','Videnskab','Sundhed','Parforhold','Kultur','Forbruger','Guide','Liv','Teknologi','Viden'}
NEWS_CATEGORIES={'Nyhed','Nyheder','Politik','Økonomi','Udland','Krimi','Sport','Danmark','Internationalt','Erhverv'}
def esc(v):return html.escape(str(v or ''),quote=True)
def published():
 items=[]
 for p in ARTICLES.glob('*.json'):
  if p.name.startswith('_'):continue
  try:a=json.loads(p.read_text(encoding='utf-8'))
  except Exception:continue
  if a.get('status')=='published' and a.get('slug') and a.get('title'):items.append(a)
 items.sort(key=lambda a:a.get('published_at') or '',reverse=True);return items
def is_feature(a):return str(a.get('category') or '') in FEATURE_CATEGORIES
def is_news(a):
 c=str(a.get('category') or '');return c in NEWS_CATEGORIES or (c not in FEATURE_CATEGORIES and c not in {'Kommentar','Kronik','Debat'})
def teaser(a,max_len=150):
 t=str(a.get('standfirst') or a.get('teaser') or '').strip()
 if len(t)<=max_len:return t
 return t[:max_len].rsplit(' ',1)[0].rstrip(' ,;:-')+'…'
def news_choices(items,current_slug,*,offset=0,exclude=None):
 excluded=set(exclude or set())|{current_slug};current=next((x for x in items if x.get('slug')==current_slug),{});story=current.get('story_id');category=current.get('category')
 pool=[a for a in items if a.get('slug') not in excluded and is_news(a)]
 if offset:
  # Second shelf deliberately broadens away from the first shelf.
  pool=pool[offset:]+pool[:offset]
 scored=[]
 for rank,a in enumerate(pool):
  score=max(0,1000-rank)
  if story and a.get('story_id')==story:score+=5000
  if category and a.get('category')==category:score+=900
  if a.get('related_news_slug')==current_slug or current.get('related_news_slug')==a.get('slug'):score+=4000
  scored.append((score,a))
 scored.sort(key=lambda x:x[0],reverse=True)
 choices=[];cat_counts={}
 for _,a in scored:
  c=str(a.get('category') or '')
  # Keep a shelf from turning into eight versions of one category unless it is the same developing story.
  if cat_counts.get(c,0)>=3 and not (story and a.get('story_id')==story):continue
  choices.append(a);cat_counts[c]=cat_counts.get(c,0)+1
  if len(choices)==8:break
 if len(choices)<8:
  used={a.get('slug') for a in choices}|excluded
  choices += [a for a in pool if a.get('slug') not in used][:8-len(choices)]
 return choices[:8]
def more_news_html(items,current_slug,*,offset=0,heading='Flere nyheder',exclude=None):
 choices=news_choices(items,current_slug,offset=offset,exclude=exclude)
 if not choices:return '',set()
 cards=[]
 for i,a in enumerate(choices):
  image=a.get('image') or {};src=str(image.get('src') or '').strip();alt=str(image.get('alt') or '').strip();hero=f'<a class="more-news-card__hero" href="{esc(a["slug"])}.html"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" decoding="async"></a>' if src else ''
  variant=' more-news-card--anchor' if i==0 else (' more-news-card--compact' if i in {3,7} else '')
  cards.append(f'<article class="more-news-card{variant}">{hero}<p class="section-label more-news__category">{esc(a.get("category") or "Nyhed")}</p><h2><a href="{esc(a["slug"])}.html">{esc(a["title"])}</a></h2><p>{esc(teaser(a,120))}</p></article>')
 return '<section class="wrap below"><h2 class="below-heading">'+esc(heading)+'</h2>'+''.join(cards)+'</section>',{str(a.get('slug')) for a in choices}
def enhance_article(path,items):
 current_slug=path.stem;text=path.read_text(encoding='utf-8');text=re.sub(r'<section class="wrap below">.*?</section>','',text,flags=re.S);text=re.sub(r'<section class="feature-shelf".*?</section>','',text,flags=re.S)
 first,used=more_news_html(items,current_slug,heading='Flere nyheder');second,_=more_news_html(items,current_slug,offset=8,heading='Mere fra Morgentidende',exclude=used);block='\n'.join(x for x in (first,second) if x)
 if block:text=text.replace('<footer>',block+'\n<footer>',1)
 path.write_text(text,encoding='utf-8')
def enhance_front(items):
 path=DOCS/'index.html'
 if not path.exists():return
 text=path.read_text(encoding='utf-8');text=re.sub(r'\n?<section class="feature-shelf"[\s\S]*?</section>\n?','\n',text)
 path.write_text(text,encoding='utf-8')
def main():
 items=published()
 for p in sorted((DOCS/'artikler').glob('*.html')):
  if not p.name.startswith('_'):enhance_article(p,items)
 enhance_front(items);print(f'Design enhancements OK: {len(items)} published articles')
if __name__=='__main__':main()
