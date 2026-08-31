#!/usr/bin/env python3
"""Pipeline-v2 build wrapper: canonical frontpage refs + generated corrections."""
from __future__ import annotations
import html,json,re
from pathlib import Path
import build_all as legacy
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"content"/"articles"
def esc(x):return html.escape(str(x),quote=True)
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def idx():
 o={}
 for p in ART.glob("*.json"):
  if p.name.startswith("_"):continue
  a=load(p)
  if a.get("status")=="published" and a.get("slug"):o[a["slug"]]=a
 return o
def resolve(i,ix):
 a=ix.get(i["slug"])
 if not a or a.get("pipeline_version")!=2:return i
 im=a.get("image") or {};video=a.get("video") or {}
 return {"slug":a["slug"],"category":a["category"],"title":a["title"],"standfirst":a["standfirst"],"teaser":a["standfirst"],"published_label":legacy.dk_label(a["published_at"]),"image_src":im.get("src",""),"image_alt":im.get("alt",""),"video":video,"followup_type":a.get("followup_type"),"headline_style":a.get("headline_style")}
def headline_parts(item,allow_split=True):
 title=str(item.get("title") or "").strip();style=item.get("headline_style")
 if not style:
  if re.match(r"^(Video|Billeder):\s+",title,re.I):style="video"
  elif title.startswith(('“','”','\"','»')):style="quote"
  elif allow_split and ": " in title:style="split"
  else:style="classic"
 if style in {"split","video"} and ": " in title:
  first,rest=title.split(": ",1)
  return style,f'<span class="headline-kicker">{esc(first)}:</span> <span class="headline-rest">{esc(rest)}</span>'
 return style,esc(title)
def headline_link(item,url,tag="h2",allow_split=True):
 style,body=headline_parts(item,allow_split=allow_split)
 return f'<{tag} class="headline headline--{esc(style)}"><a href="{url}">{body}</a></{tag}>'
def lead_followups(lead_slug,ix):
 labels={"update":"Ny udvikling","video":"Video","images":"Billeder","eyewitness":"Øjenvidne","background":"Baggrund","timeline":"Tidslinje","commentary":"Kommentar"}
 items=[a for a in ix.values() if a.get("related_news_slug")==lead_slug and a.get("slug")!=lead_slug]
 items.sort(key=lambda a:a.get("published_at") or "",reverse=True)
 if not items:return ""
 rows=[]
 for a in items[:4]:
  kind=a.get("followup_type") or ("commentary" if a.get("category")=="Kommentar" else "update")
  rows.append(f'<a class="lead-followup" href="{legacy.front_item_url(a["slug"])}"><span class="lead-followup__type">{esc(labels.get(kind,"Mere"))}</span><strong>{esc(a["title"])}</strong></a>')
 return '<aside class="lead-package" aria-label="Mere om sagen"><p class="lead-package__title">Mere om sagen</p>'+''.join(rows)+'</aside>'
def unrelated_to_lead(x,lead_slug,ix):
 slug=x.get("slug")
 if not slug or slug==lead_slug:return False
 a=ix.get(slug)
 return not (a and a.get("related_news_slug")==lead_slug)
def lead_visual(l):
 v=l.get("video") or {}
 if v.get("provider")=="youtube" and v.get("id") and v.get("frontpage_hero") is True:
  return legacy.youtube_embed(v,autoplay=bool(v.get("frontpage_autoplay")),css_class="frontpage-video-hero")
 return f'<figure class="lead-fig"><img src="{esc(l["image_src"])}" alt="{esc(l.get("image_alt",""))}"></figure>' if l.get("image_src") else ""
def front():
 s=load(ROOT/"content"/"frontpage.json");ix=idx();t=(ROOT/"templates"/"index.html").read_text(encoding="utf-8")
 from datetime import datetime
 d=datetime.fromisoformat(s["date"]).date();dl=f"{legacy.WEEKDAYS[d.weekday()]} {d.day}. {legacy.MONTHS[d.month-1]} {d.year}"
 tk=resolve(s["ticker"],ix);ticker=f'<p><a href="{legacy.front_item_url(tk["slug"])}">{esc(tk["title"])}</a></p>'
 l=resolve(s["lead"],ix);visual=lead_visual(l);lead_h=headline_link(l,legacy.front_item_url(l["slug"]),tag="h1",allow_split=True)
 lead_article='<section class="lead">'+visual+f'<p class="section-label">{esc(l["category"])}</p>{lead_h}<p class="standfirst">{esc(l.get("standfirst",l.get("teaser","")))}</p><p class="meta">{esc(l.get("published_label",""))} · {esc(l["category"])}</p></section>'
 followups=lead_followups(l["slug"],ix)
 lead_class="lead-column lead-column--story-package" if followups else "lead-column"
 lead=f'<div class="{lead_class}">'+lead_article+followups+'</div>'
 rail=['<aside class="rail"><p class="rail-title">Også i dag</p>']
 seen=set();rail_candidates=[]
 for group in (s.get("rail",[]),s.get("narrow",[]),s.get("stack",[])):
  for raw in group:
   x=resolve(raw,ix)
   if x.get("slug") in seen or not unrelated_to_lead(x,l["slug"],ix):continue
   seen.add(x["slug"]);rail_candidates.append(x)
 for x in rail_candidates[:5]:
  pic=f'<img src="{esc(x["image_src"])}" alt="{esc(x.get("image_alt",""))}">' if x.get("image_src") else ""
  style,headline=headline_parts(x,allow_split=False)
  rail.append(f'<a class="rail-item headline--{esc(style)}" href="{legacy.front_item_url(x["slug"])}">{pic}<span><span>{esc(x["category"])}</span> {headline}</span></a>')
 rail.append("</aside>");stack=['<section class="stack">']
 for raw in s.get("stack",[]):
  x=resolve(raw,ix);pic=f'<a href="{legacy.front_item_url(x["slug"])}"><img src="{esc(x["image_src"])}" alt="{esc(x.get("image_alt",""))}"></a>' if x.get("image_src") else "";stack.append(f'<article class="card">{pic}<p class="section-label">{esc(x["category"])}</p>{headline_link(x,legacy.front_item_url(x["slug"]),tag="h2",allow_split=True)}<p>{esc(x.get("teaser",x.get("standfirst","")))}</p></article>')
 stack.append("</section>");narrow=['<section class="narrow">']
 for raw in s.get("narrow",[]):
  x=resolve(raw,ix);narrow.append(f'<article><p class="section-label">{esc(x["category"])}</p>{headline_link(x,legacy.front_item_url(x["slug"]),tag="h2",allow_split=False)}<p>{esc(x.get("teaser",x.get("standfirst","")))}</p></article>')
 narrow.append("</section>")
 r={"{{DATE_ISO}}":esc(s["date"]),"{{DATE_LABEL}}":esc(dl),"{{EDITION_LABEL}}":esc(s.get("edition_label","Danmarks nye avis")),"{{TICKER_HTML}}":ticker,"{{LEAD_HTML}}":lead,"{{RAIL_HTML}}":"".join(rail),"{{STACK_HTML}}":"".join(stack),"{{NARROW_HTML}}":"".join(narrow)}
 for k,v in r.items():t=t.replace(k,v)
 (ROOT/"docs"/"index.html").write_text(t,encoding="utf-8")
def correction_page():
 data=load(ROOT/"content"/"corrections.json");ix=idx();lab={"clarification":"Præcisering","correction":"Rettelse","retraction":"Tilbagetrækning"};rows=[]
 for e in sorted(data.get("entries",[]),key=lambda z:z.get("timestamp",""),reverse=True):
  slug=e["article_slug"];title=ix.get(slug,{}).get("title",slug);rows.append(f'<article><p class="section-label">{lab.get(e.get("type"),"Rettelse")} · {legacy.dk_label(e["timestamp"])}</p><h2><a href="artikler/{esc(slug)}.html">{esc(title)}</a></h2><p>{esc(e["summary"])}</p></article>')
 log="".join(rows) or "<p>Der er endnu ingen registrerede materielle rettelser i den nye offentlige log.</p>";page='<!DOCTYPE html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rettelser – Morgentidende</title><link rel="stylesheet" href="style.css?v=5"></head><body><header class="masthead"><div class="wrap"><a class="wordmark" href="./">Morgentidende</a></div></header><main class="wrap article-grid"><article class="article-body"><p class="section-label">Rettelser</p><h1>Rettelser og præciseringer</h1><p>Væsentlige faktuelle fejl bliver rettet synligt.</p><h2>Aktuel log</h2>'+log+'</article></main></body></html>\n';(ROOT/"docs"/"rettelser.html").write_text(page,encoding="utf-8")
def public_surface():
 """Keep public pages tool-neutral without making false human-authorship claims."""
 ai=ROOT/"docs"/"ai-politik.html"
 if ai.exists():ai.unlink()
 for p in [ROOT/"docs"/"index.html",*sorted((ROOT/"docs"/"artikler").glob("*.html"))]:
  if not p.exists():continue
  t=p.read_text(encoding="utf-8")
  t=t.replace(' · <a href="ai-politik.html">AI-politik</a>',"")
  t=t.replace(' · <a href="../ai-politik.html">AI-politik</a>',"")
  p.write_text(t,encoding="utf-8")
 sm=ROOT/"docs"/"sitemap.xml"
 if sm.exists():
  lines=[x for x in sm.read_text(encoding="utf-8").splitlines() if "/ai-politik.html" not in x]
  sm.write_text("\n".join(lines)+"\n",encoding="utf-8")
def main():
 for p in sorted(ART.glob("*.json")):legacy.build_article(p)
 front();correction_page();legacy.build_news_sitemap();legacy.build_sitemap();public_surface();print("Build v2 OK")
if __name__=="__main__":main()
