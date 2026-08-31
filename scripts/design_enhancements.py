#!/usr/bin/env python3
"""Editorial layout enhancements applied after the canonical build.

Keeps generated pages deterministic: every article gets two eight-story news
continuations with hero images, with the premium magazine shelf between them.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
DOCS = ROOT / "docs"

FEATURE_CATEGORIES = {
    "Feature", "Features", "Videnskab", "Sundhed", "Parforhold", "Kultur",
    "Forbruger", "Guide", "Liv", "Teknologi", "Viden",
}
NEWS_CATEGORIES = {
    "Nyhed", "Nyheder", "Politik", "Økonomi", "Udland", "Krimi", "Sport",
    "Danmark", "Internationalt", "Erhverv",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def published() -> list[dict]:
    items: list[dict] = []
    for path in ARTICLES.glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if article.get("status") == "published" and article.get("slug") and article.get("title"):
            items.append(article)
    items.sort(key=lambda a: a.get("published_at") or "", reverse=True)
    return items


def is_feature(article: dict) -> bool:
    return str(article.get("category") or "") in FEATURE_CATEGORIES


def is_news(article: dict) -> bool:
    category = str(article.get("category") or "")
    if category in NEWS_CATEGORIES:
        return True
    return category not in FEATURE_CATEGORIES and category not in {"Kommentar", "Kronik", "Debat"}


def teaser(article: dict, max_len: int = 150) -> str:
    text = str(article.get("standfirst") or article.get("teaser") or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "…"


def news_choices(items: list[dict], current_slug: str, *, offset: int = 0, exclude: set[str] | None = None) -> list[dict]:
    excluded = set(exclude or set()) | {current_slug}
    candidates = [a for a in items if a.get("slug") not in excluded and is_news(a)]
    choices = candidates[offset:offset + 8]
    if len(choices) < 8:
        used = {a.get("slug") for a in choices} | excluded
        fallback = [a for a in items if a.get("slug") not in used and not is_feature(a)]
        choices += fallback[: 8 - len(choices)]
    return choices[:8]


def more_news_html(items: list[dict], current_slug: str, *, offset: int = 0, heading: str = "Flere nyheder", exclude: set[str] | None = None) -> tuple[str, set[str]]:
    choices = news_choices(items, current_slug, offset=offset, exclude=exclude)
    if not choices:
        return "", set()
    cards = []
    for a in choices:
        image = a.get("image") or {}
        src = str(image.get("src") or "").strip()
        alt = str(image.get("alt") or "").strip()
        hero = f'<a class="more-news-card__hero" href="{esc(a["slug"])}.html"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" decoding="async"></a>' if src else ""
        cards.append(
            '<article class="more-news-card">'
            f'{hero}'
            f'<p class="section-label more-news__category">{esc(a.get("category") or "Nyhed")}</p>'
            f'<h2><a href="{esc(a["slug"])}.html">{esc(a["title"])}</a></h2>'
            f'<p>{esc(teaser(a, 120))}</p>'
            '</article>'
        )
    return '<section class="wrap below"><h2 class="below-heading">' + esc(heading) + '</h2>' + "".join(cards) + "</section>", {str(a.get("slug")) for a in choices}


def feature_html(items: list[dict], *, prefix: str, current_slug: str | None = None) -> str:
    choices = [a for a in items if a.get("slug") != current_slug and is_feature(a)][:4]
    if len(choices) < 4:
        used = {a.get("slug") for a in choices} | ({current_slug} if current_slug else set())
        fallback = [a for a in items if a.get("slug") not in used and a.get("category") not in {"Krimi"}]
        choices += fallback[: 4 - len(choices)]
    if not choices:
        return ""
    cards = []
    for a in choices[:4]:
        cards.append(
            f'<a class="feature-card" href="{prefix}{esc(a["slug"])}.html">'
            f'<span class="feature-card__category">{esc(a.get("category") or "Feature")}</span>'
            f'<strong>{esc(a["title"])}</strong>'
            f'<p>{esc(teaser(a, 105))}</p>'
            '</a>'
        )
    return (
        '<section class="feature-shelf" aria-label="Perspektiv og liv">'
        '<div class="feature-shelf__head"><div>'
        '<p class="feature-shelf__eyebrow">Morgentidende magasin</p>'
        '<h2 class="feature-shelf__title">Perspektiv &amp; liv</h2>'
        '</div><p class="feature-shelf__deck">Videnskab, sundhed, kultur, relationer og historier med længere levetid end nyhedsstrømmen.</p></div>'
        '<div class="feature-shelf__grid">' + "".join(cards) + '</div></section>'
    )


def enhance_article(path: Path, items: list[dict]) -> None:
    current_slug = path.stem
    text = path.read_text(encoding="utf-8")
    # Remove the canonical one-row related block and any enhancement blocks from an earlier build.
    text = re.sub(r'<section class="wrap below">.*?</section>', '', text, flags=re.S)
    text = re.sub(r'<section class="feature-shelf".*?</section>', '', text, flags=re.S)

    first, used = more_news_html(items, current_slug, heading="Flere nyheder")
    shelf = feature_html(items, prefix="", current_slug=current_slug)
    second, _ = more_news_html(items, current_slug, offset=8, heading="Mere fra Morgentidende", exclude=used)
    block = "\n".join(x for x in (first, shelf, second) if x)
    if block:
        text = text.replace("<footer>", block + "\n<footer>", 1)
    path.write_text(text, encoding="utf-8")


def enhance_front(items: list[dict]) -> None:
    path = DOCS / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    shelf = feature_html(items, prefix="artikler/")
    if not shelf:
        return
    marker = "<!-- SHORT_VIDEOS -->"
    if marker in text:
        text = text.replace(marker, shelf + "\n  " + marker, 1)
    else:
        text = text.replace('<section class="signup"', shelf + '\n<section class="signup"', 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    items = published()
    for path in sorted((DOCS / "artikler").glob("*.html")):
        if path.name.startswith("_"):
            continue
        enhance_article(path, items)
    enhance_front(items)
    print(f"Design enhancements OK: {len(items)} published articles")


if __name__ == "__main__":
    main()
