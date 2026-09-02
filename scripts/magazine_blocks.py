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
    pic = f'<a href="artikler/{esc(a["slug"])}.html"><img src="{esc(src)}" alt="{esc(image.get("alt") or "")}"></a>' if src else ""
    return (
        '<article class="card magazine-card">'
        + pic
        + f'<p class="section-label">{esc(a.get("category") or "")}</p>'
        + f'<h2><a href="artikler/{esc(a["slug"])}.html">{esc(a["title"])}</a></h2>'
        + f'<p>{esc(a.get("standfirst") or "")}</p></article>'
    )


def section(title: str, intro: str, items: list[dict]) -> str:
    if not items:
        return ""
    return (
        f'<section class="magazine-section" aria-label="{esc(title)}">'
        f'<div class="magazine-section__head"><p class="section-label">Magasin</p><h2>{esc(title)}</h2><p>{esc(intro)}</p></div>'
        f'<div class="stack magazine-grid">{"".join(card(a) for a in items)}</div></section>'
    )


def main() -> int:
    if not INDEX.exists():
        print("magazine blocks: docs/index.html missing")
        return 0
    page = INDEX.read_text(encoding="utf-8")
    page = re.sub(r"\n?<section class=\"magazine-section\"[\s\S]*?</section>\s*<section class=\"magazine-section\"[\s\S]*?</section>\n?", "\n", page)
    items = load_published()
    used: set[str] = set()
    tech = pick(items, TECH, {"Videnskab & teknologi"}, used)
    people = pick(items, PEOPLE, {"Sundhed", "Liv"}, used)
    blocks = section("Viden & teknologi", "Videnskab, teknologi, AI, naturvidenskab og militær – nyheder, forskning og stærke evergreens.", tech)
    blocks += section("Mennesker & liv", "Psykologi, sundhed, hormoner, parforhold, sex, dating, familie og evolutionær psykologi.", people)
    if not blocks:
        print("magazine blocks: no matching published articles")
        return 0
    css = '''<style id="magazine-block-style">
.magazine-section{margin:3rem 0 2.5rem;padding:1.5rem 0;border-top:2px solid currentColor}.magazine-section__head{max-width:760px;margin-bottom:1.2rem}.magazine-section__head h2{font-family:"Roboto Slab",serif;font-size:clamp(1.7rem,3vw,2.5rem);margin:.15rem 0 .35rem}.magazine-section__head>p:last-child{margin:0;opacity:.78}.magazine-grid{margin-top:0}.magazine-card h2{font-size:1.25rem}
</style>'''
    page = page.replace("</head>", css + "</head>") if "magazine-block-style" not in page else page
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
