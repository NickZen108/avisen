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
 return {"slug":a["slug"],"category":a["category"],"title":a["title"],"standfirst":a["standfirst"],"teaser":a["standfirst"],"published_label":legacy.dk_label(a["published_at"]),"image_src":im.get("src",""),"image_alt":im.get("alt",""),"image_caption":im.get("caption",""),"image_credit":im.get("credit",""),"video":video,"followup_type":a.get("followup_type"),"headline_style":a.get("headline_style")}
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
  category=str(a.get("category") or "Nyhed")
  special=labels.get(kind) if kind in {"video","images","commentary"} else None
  label=category if not special or special.casefold()==category.casefold() else f"{category} · {special}"
  rows.append(f'<a class="lead-followup" href="{legacy.front_item_url(a["slug"])}"><span class="lead-followup__type">{esc(label)}</span><strong>{esc(a["title"])}</strong></a>')
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
 if not l.get("image_src"):return ""
 return f'<figure class="lead-fig"><img src="{esc(l["image_src"])}" alt="{esc(l.get("image_alt",""))}"></figure>'
def front():
 s=load(ROOT/"content"/"frontpage.json");ix=idx();t=(ROOT/"templates"/"index.html").read_text(encoding="utf-8")
 tk=resolve(s["ticker"],ix);ticker_text=str(tk.get("title") or "").strip();ticker=f'<p><a href="{legacy.front_item_url(tk["slug"])}">{esc(ticker_text)}</a></p>'
 l=resolve(s["lead"],ix);visual=lead_visual(l);lead_h=headline_link(l,legacy.front_item_url(l["slug"]),tag="h1",allow_split=True)
 # Forsiden viser rubrikker, ikke artikelmanchet eller brødtekst. Manchetten
 # hører kun til på artikelsiden; ellers kan en lang/manipuleret standfirst få
 # en hel artikel til at ligne forsideindhold.
 lead_article='<section class="lead">'+visual+f'<p class="section-label">{esc(l["category"])}</p>{lead_h}</section>'
 followups=lead_followups(l["slug"],ix)
 lead_class="lead-column lead-column--story-package" if followups else "lead-column"
 lead=f'<div class="{lead_class}">'+lead_article+followups+'</div>'
 rail=['<aside class="rail">']
 seen=set();rail_candidates=[]
 for group in (s.get("rail",[]),s.get("narrow",[]),s.get("stack",[])):
  for raw in group:
   x=resolve(raw,ix)
   if x.get("slug") in seen or not unrelated_to_lead(x,l["slug"],ix):continue
   seen.add(x["slug"]);rail_candidates.append(x)
 seen_images=set()
 for x in rail_candidates[:5]:
  image_src=str(x.get("image_src") or "")
  pic=""
  if image_src and image_src not in seen_images:
   seen_images.add(image_src);pic=f'<img src="{esc(image_src)}" alt="{esc(x.get("image_alt",""))}">'
  style,headline=headline_parts(x,allow_split=False)
  rail.append(f'<a class="rail-item headline--{esc(style)}" href="{legacy.front_item_url(x["slug"])}">{pic}<span><span>{esc(x["category"])}</span> {headline}</span></a>')
 rail.append("</aside>");stack=['<section class="stack">']
 for raw in s.get("stack",[]):
  x=resolve(raw,ix);pic=f'<a href="{legacy.front_item_url(x["slug"])}"><img src="{esc(x["image_src"])}" alt="{esc(x.get("image_alt",""))}"></a>' if x.get("image_src") else "";stack.append(f'<article class="card">{pic}<p class="section-label">{esc(x["category"])}</p>{headline_link(x,legacy.front_item_url(x["slug"]),tag="h2",allow_split=True)}</article>')
 stack.append("</section>");narrow=['<section class="narrow">']
 for raw in s.get("narrow",[]):
  x=resolve(raw,ix);narrow.append(f'<article><p class="section-label">{esc(x["category"])}</p>{headline_link(x,legacy.front_item_url(x["slug"]),tag="h2",allow_split=False)}</article>')
 narrow.append("</section>")
 r={"{{EDITION_LABEL}}":esc(s.get("edition_label","Danmarks nye avis")),"{{TICKER_HTML}}":ticker,"{{LEAD_HTML}}":lead,"{{RAIL_HTML}}":"".join(rail),"{{STACK_HTML}}":"".join(stack),"{{NARROW_HTML}}":"".join(narrow)}
 for k,v in r.items():t=t.replace(k,v)
 (ROOT/"docs"/"index.html").write_text(t,encoding="utf-8")
def correction_page():
 data=load(ROOT/"content"/"corrections.json");ix=idx();lab={"clarification":"Præcisering","correction":"Rettelse","retraction":"Tilbagetrækning"};rows=[]
 for e in sorted(data.get("entries",[]),key=lambda z:z.get("timestamp",""),reverse=True):
  slug=e["article_slug"];title=ix.get(slug,{}).get("title",slug);rows.append(f'<article><p class="section-label">{lab.get(e.get("type"),"Rettelse")} · {legacy.dk_label(e["timestamp"])}</p><h2><a href="artikler/{esc(slug)}.html">{esc(title)}</a></h2><p>{esc(e["summary"])}</p></article>')
 log="".join(rows) or "<p>Der er endnu ingen registrerede væsentlige rettelser.</p>"
 page='<!DOCTYPE html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rettelser – Morgentidende</title><meta name="description" content="Morgentidendes åbne log over væsentlige rettelser og præciseringer."><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="style.css?v=7"><link rel="stylesheet" href="theme.css?v=2"><script src="theme.js?v=1"></script></head><body class="subpage"><header class="masthead"><div class="wrap masthead-inner"><a class="wordmark" href="./">Morgentidende</a><button class="theme-toggle" type="button" role="switch" aria-checked="false" aria-label="Skift mellem lyst og mørkt tema"><span class="theme-toggle__label">Mørk</span><span class="theme-toggle__track" aria-hidden="true"><span class="theme-toggle__thumb"></span></span></button></div></header><main class="wrap subpage-main"><article class="subpage-card"><p class="section-label">Rettelser</p><h1>Vi retter fejl åbent</h1><p class="subpage-intro">Troværdighed kræver også, at man viser det, når noget blev forkert. Væsentlige faktuelle fejl og præciseringer registreres her.</p><h2>Aktuel log</h2>'+log+'</article></main><footer><div class="wrap"><p class="wordmark-sm">Morgentidende</p><p><a href="./">Forside</a> · <a href="nyhedsbrev.html">Nyhedsbrev</a> · <a href="om.html">Om</a> · <a href="rettelser.html">Rettelser</a></p></div></footer></body></html>\n'
 (ROOT/"docs"/"rettelser.html").write_text(page,encoding="utf-8")
def public_surface():
 """Keep public pages tool-neutral and strip internal pipeline metadata."""
 ai=ROOT/"docs"/"ai-politik.html"
 if ai.exists():ai.unlink()
 for p in [ROOT/"docs"/"index.html",*sorted((ROOT/"docs"/"artikler").glob("*.html"))]:
  if not p.exists():continue
  t=p.read_text(encoding="utf-8")
  t=t.replace(' · <a href="ai-politik.html">AI-politik</a>',"")
  t=t.replace(' · <a href="../ai-politik.html">AI-politik</a>',"")
  t=re.sub(r"\s*·\s*Public domain\s*\(PD automated\)","",t,flags=re.I)
  t=re.sub(r"\s*·\s*PD automated\b","",t,flags=re.I)
  t=re.sub(r"\s*·\s*(?:pipeline|agent|cache)[-_ ](?:status|flag|hash)\s*[:=]\s*[^<·]+","",t,flags=re.I)
  p.write_text(t,encoding="utf-8")
 sm=ROOT/"docs"/"sitemap.xml"
 if sm.exists():
  lines=[x for x in sm.read_text(encoding="utf-8").splitlines() if "/ai-politik.html" not in x]
  sm.write_text("\n".join(lines)+"\n",encoding="utf-8")
def main():
 for p in sorted(ART.glob("*.json")):legacy.build_article(p)
 front();correction_page();legacy.build_news_sitemap();legacy.build_sitemap();public_surface();print("Build v2 OK")
if __name__=="__main__":main()
