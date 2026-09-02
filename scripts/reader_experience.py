#!/usr/bin/env python3
"""Post-build reader experience: topic hubs, story updates and contextual read-also."""
from __future__ import annotations
import html,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'content'/'articles'; DOCS=ROOT/'docs'

STOPWORDS={'og','i','på','af','for','med','til','om','en','et','den','det','de','der','har','får','fra','som','ikke','at','sig','sin','sine','sit','sag','sagen','ny','nye','efter','under','over','mod','ved','kan','skal','vil','er','var','bliver','blev','mere','seneste'}

def esc(x):return html.escape(str(x or ''),quote=True)
def load(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return d

def slugify(x):
 x=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower();x=re.sub(r'[^a-z0-9]+','-',x).strip('-');return x[:90] or 'emne'
def items():
 out=[]
 for p in ART.glob('*.json'):
  if p.name.startswith('_'):continue
  a=load(p,{})
  if a.get('status')=='published' and a.get('slug'):out.append(a)
 out.sort(key=lambda a:a.get('published_at') or '',reverse=True);return out

def related_for(a,all_items):
 story=a.get('story_id'); rel=a.get('related_news_slug'); rows=[]
 for x in all_items:
  if x.get('slug')==a.get('slug'):continue
  if story and x.get('story_id')==story:rows.append(x);continue
  if rel and x.get('slug')==rel:rows.append(x);continue
  if x.get('related_news_slug')==a.get('slug'):rows.append(x)
 seen=set();uniq=[]
 for x in rows:
  if x['slug'] not in seen:seen.add(x['slug']);uniq.append(x)
 return uniq

def topic_tokens(a):
 raw=' '.join([str(a.get('title') or ''),str(a.get('story_id') or '').replace('-',' ')])
 words=re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+",raw.casefold())
 return {w for w in words if len(w)>=4 and w not in STOPWORDS}

def contextual_candidates(a,all_items):
 """Same story always wins. Otherwise require real topic/entity overlap; never fill Læs også with a random category story."""
 direct=related_for(a,all_items)
 if direct:return direct
 base=topic_tokens(a); scored=[]
 if not base:return []
 for x in all_items:
  if x.get('slug')==a.get('slug'):continue
  overlap=base & topic_tokens(x)
  if not overlap:continue
  # A named/entity-like shared token is enough; two ordinary topical tokens are stronger.
  score=len(overlap)*10 + (2 if x.get('category')==a.get('category') else 0)
  scored.append((score,x.get('published_at') or '',x))
 scored.sort(key=lambda row:(row[0],row[1]),reverse=True)
 return [x for _,__,x in scored]

def inject_context(a,all_items):
 p=DOCS/'artikler'/f"{a['slug']}.html"
 if not p.exists():return
 text=p.read_text(encoding='utf-8'); related=related_for(a,all_items)
 if related and 'story-update-box' not in text:
  rows=''.join(f'<li><a href="{esc(x["slug"])}.html">{esc(x.get("title"))}</a></li>' for x in related[:5])
  box=f'<aside class="story-update-box"><p class="section-label">Seneste udvikling</p><ul>{rows}</ul></aside>'
  pos=text.find('<section class="wrap below">')
  if pos<0:pos=text.find('<footer>')
  if pos>=0:text=text[:pos]+box+'\n'+text[pos:]
 if 'read-also-inline' not in text:
  candidates=contextual_candidates(a,all_items)
  if candidates:
   article_start=text.find('<article class="article-body">'); article_end=text.find('</article>',article_start)
   article_html=text[article_start:article_end if article_end>0 else len(text)]
   # Count only ordinary body paragraphs; header metadata must never decide insertion point.
   body_paras=list(re.finditer(r'<p(?![^>]*class=)[^>]*>.*?</p>',article_html,re.I|re.S))
   if len(body_paras)>=2:
    x=candidates[0]; card=f'<aside class="read-also-inline"><span>Læs også</span><a href="{esc(x["slug"])}.html">{esc(x.get("title"))}</a></aside>'
    chosen=body_paras[1] if len(body_paras)<5 else body_paras[2]
    at=article_start+chosen.end();text=text[:at]+card+text[at:]
 p.write_text(text,encoding='utf-8')

def build_topics(all_items):
 groups=defaultdict(list)
 for a in all_items:
  if a.get('story_id'):groups[str(a['story_id'])].append(a)
 out=DOCS/'emner';out.mkdir(parents=True,exist_ok=True);built=[]
 for story,rows in groups.items():
  if len(rows)<2:continue
  rows.sort(key=lambda a:a.get('published_at') or '',reverse=True);name=slugify(story);title=rows[0].get('title') or story
  cards=''.join(f'<article><p class="section-label">{esc(x.get("category"))}</p><h2><a href="../artikler/{esc(x["slug"])}.html">{esc(x.get("title"))}</a></h2><p>{esc(x.get("standfirst"))}</p></article>' for x in rows[:20])
  page=f'''<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} – emne – Morgentidende</title><link rel="stylesheet" href="../style.css?v=7"><link rel="stylesheet" href="../theme.css?v=4"><link rel="stylesheet" href="../morgentidende-ui.css?v=3"></head><body><header class="masthead"><div class="wrap masthead-inner"><a class="wordmark" href="../"><img class="brand-sun" src="../morning-sun.svg" alt=""><span>Morgentidende</span></a></div></header><main class="wrap topic-page"><p class="section-label">Emne</p><h1>{esc(title)}</h1><p class="standfirst">Samlet dækning og seneste udvikling i denne historie.</p><section class="topic-stream">{cards}</section></main><footer><div class="wrap"><p class="wordmark-sm">Morgentidende</p></div></footer></body></html>'''
  (out/f'{name}.html').write_text(page,encoding='utf-8');built.append(f'emner/{name}.html')
 return built

def main():
 all_items=items()
 for a in all_items:inject_context(a,all_items)
 built=build_topics(all_items)
 print(f'Reader experience OK: {len(built)} emnesider')
if __name__=='__main__':main()
