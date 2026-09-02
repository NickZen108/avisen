#!/usr/bin/env python3
"""Inject two automatic magazine blocks into the generated front page.

Runs after build_all_v2.py. It does not change templates; the generated page gets
recomputed on every build from published article JSON.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
INDEX = ROOT / "docs" / "index.html"

TECH = {
    "videnskab", "forskning", "naturvidenskab", "teknologi", "kunstig intelligens", " ai ",
    "rumfart", "rum", "militær", "militaer", "forsvar", "drone", "robot", "energi",
    "fysik", "biologi", "astronomi", "ingeniør", "ingenioer", "computer", "chip", "halvleder",
}
PEOPLE = {
    "psykologi", "psykisk", "sundhed", "testosteron", "hormon", "overgangsalder", "menopause",
    "parforhold", "ægteskab", "aegteskab", "sex", "single", "dating", "date", "opdragelse",
    "forældre", "foraeldre", "bedsteforældre", "bedsteforaeldre", "familie", "relation",
    "evolutionær psykologi", "evolutionaer psykologi", "tilknytning", "kærlighed", "kaerlighed",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def article_text(a: dict) -> str:
    tags = a.get("tags") or []
    if isinstance(tags, list):
        tags = " ".join(str(x) for x in tags)
    return f" {a.get('category','')} {a.get('title','')} {a.get('standfirst','')} {tags} ".lower()


def score(a: dict, terms: set[str], preferred_categories: set[str]) -> int:
    text = article_text(a)
    s = 4 if str(a.get("category") or "") in preferred_categories else 0
    for term in terms:
        if term in text:
            s += 2
    fmt = str(a.get("format") or "").lower()
    if fmt in {"feature", "guide", "baggrund"}:
        s += 1
    return s


def load_published() -> list[dict]:
    out = []
    for p in ARTICLES.glob("*.json"):
        if p.name.startswith("_"):
            continue
        try:
            a = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if a.get("status") == "published" and a.get("slug") and a.get("title"):
            out.append(a)
    out.sort(key=lambda a: str(a.get("published_at") or ""), reverse=True)
    return out


def pick(items: list[dict], terms: set[str], categories: set[str], used: set[str], limit: int = 4) -> list[dict]:
    ranked = []
    for a in items:
        if a.get("slug") in used:
            continue
        s = score(a, terms, categories)
        if s > 0:
            ranked.append((s, str(a.get("published_at") or ""), a))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    chosen = [row[2] for row in ranked[:limit]]
    used.update(str(a["slug"]) for a in chosen)
    return chosen


def card(a: dict) -> str:
    image = a.get("image") or {}
    src = str(image.get("src") or "")
    pic = f'<a class="magazine-card__image" href="artikler/{esc(a["slug"])}.html"><img src="{esc(src)}" alt="{esc(image.get("alt") or "")}"></a>' if src else ""
    return (
        '<article class="card magazine-card">'
        + pic
        + '<div class="magazine-card__body">'
        + f'<p class="section-label">{esc(a.get("category") or "")}</p>'
        + f'<h2><a href="artikler/{esc(a["slug"])}.html">{esc(a["title"])}</a></h2>'
        + f'<p>{esc(a.get("standfirst") or "")}</p></div></article>'
    )


def section(title: str, intro: str, items: list[dict], theme: str) -> str:
    if not items:
        return ""
    return (
        f'<section class="magazine-section magazine-section--{esc(theme)}" aria-label="{esc(title)}">'
        f'<div class="magazine-section__head"><p class="magazine-eyebrow">Morgentidende Magasin</p><h2>{esc(title)}</h2><p>{esc(intro)}</p></div>'
        f'<div class="magazine-grid">{"".join(card(a) for a in items)}</div></section>'
    )


def main() -> int:
    if not INDEX.exists():
        print("magazine blocks: docs/index.html missing")
        return 0
    page = INDEX.read_text(encoding="utf-8")
    page = re.sub(r'\n?<section class="[^"]*magazine-section[^"]*"[\s\S]*?</section>\s*', "\n", page)
    page = re.sub(r'<style id="magazine-block-style">[\s\S]*?</style>', "", page)
    items = load_published()
    used: set[str] = set()
    tech = pick(items, TECH, {"Videnskab & teknologi"}, used)
    people = pick(items, PEOPLE, {"Sundhed", "Liv", "Parforhold"}, used)
    blocks = section("Viden & teknologi", "Videnskab, teknologi, AI, naturvidenskab og militær – nyheder, forskning og stærke evergreens.", tech, "tech")
    blocks += section("Mennesker & liv", "Psykologi, sundhed, hormoner, parforhold, sex, dating, familie og evolutionær psykologi.", people, "people")
    if not blocks:
        print("magazine blocks: no matching published articles")
        return 0
    css = '''<style id="magazine-block-style">
.magazine-section{position:relative;overflow:hidden;margin:3.4rem 0 2.8rem;padding:clamp(1.35rem,3vw,2.25rem);border-radius:22px;color:#f7f7fb;box-shadow:0 20px 45px rgba(10,15,30,.16),inset 0 1px 0 rgba(255,255,255,.12)}
.magazine-section::before{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 92% 0%,rgba(255,255,255,.12),transparent 34%),linear-gradient(120deg,rgba(255,255,255,.035),transparent 48%)}
.magazine-section--tech{background:linear-gradient(145deg,#0c2039 0%,#173653 58%,#244b68 100%);border:1px solid rgba(166,201,226,.22)}
.magazine-section--people{background:linear-gradient(145deg,#29152f 0%,#4a2650 58%,#613b62 100%);border:1px solid rgba(226,188,224,.20)}
.magazine-section__head{position:relative;z-index:1;max-width:790px;margin-bottom:1.55rem}.magazine-eyebrow{margin:0 0 .45rem;font:600 .72rem/1.2 "Source Sans 3",sans-serif;letter-spacing:.16em;text-transform:uppercase;opacity:.72}.magazine-section__head h2{font-family:"Roboto Slab",serif;font-size:clamp(2rem,4vw,3.15rem);line-height:1.02;letter-spacing:-.025em;margin:0 0 .55rem;color:#fff}.magazine-section__head>p:last-child{max-width:690px;margin:0;font-size:1rem;line-height:1.5;color:rgba(255,255,255,.78)}
.magazine-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem}.magazine-card{overflow:hidden;margin:0!important;padding:0!important;border:1px solid rgba(255,255,255,.12)!important;border-radius:15px!important;background:rgba(255,255,255,.075)!important;box-shadow:0 9px 22px rgba(0,0,0,.12)!important;backdrop-filter:blur(3px);transition:transform .18s ease,background .18s ease,border-color .18s ease}.magazine-card:hover{transform:translateY(-3px);background:rgba(255,255,255,.11)!important;border-color:rgba(255,255,255,.22)!important}.magazine-card__image{display:block;aspect-ratio:16/10;overflow:hidden}.magazine-card__image img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .28s ease}.magazine-card:hover .magazine-card__image img{transform:scale(1.025)}.magazine-card__body{padding:1rem 1rem 1.15rem}.magazine-card .section-label{margin:0 0 .45rem;color:rgba(255,255,255,.67)!important;font-size:.68rem!important;letter-spacing:.09em;text-transform:uppercase}.magazine-card h2{margin:0 0 .55rem;font-family:"Roboto Slab",serif;font-size:1.13rem;line-height:1.16}.magazine-card h2 a{color:#fff!important;text-decoration:none}.magazine-card__body>p:last-child{margin:0;color:rgba(255,255,255,.72);font-size:.9rem;line-height:1.42}.magazine-section a:focus-visible{outline:2px solid #fff;outline-offset:3px}
@media(max-width:900px){.magazine-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.magazine-section{margin:2.5rem -.15rem 2.1rem;padding:1.2rem;border-radius:18px}.magazine-grid{grid-template-columns:1fr}.magazine-section__head h2{font-size:2rem}.magazine-card__image{aspect-ratio:16/9}}
</style>'''
    page = page.replace("</head>", css + "</head>")
    marker = "</main>"
    if marker in page:
        page = page.replace(marker, blocks + marker, 1)
    else:
        page = page.replace("<footer", blocks + "<footer", 1)
    INDEX.write_text(page, encoding="utf-8")
    print(f"magazine blocks: tech={len(tech)} people={len(people)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
