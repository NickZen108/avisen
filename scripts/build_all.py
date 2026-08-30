#!/usr/bin/env python3
"""Build Morgentidende from structured content using only the Python stdlib."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://nickzen108.github.io/avisen"
ARTICLE_DIR = ROOT / "content" / "articles"
DOC_ARTICLES = ROOT / "docs" / "artikler"

MONTHS = ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december"]
WEEKDAYS = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp mangler timezone: {value}")
    return dt


def dk_label(value: str) -> str:
    dt = parse_iso(value)
    return f"{dt.day}. {MONTHS[dt.month-1]} {dt.year} kl. {dt:%H.%M}"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_blocks(blocks: list[dict]) -> str:
    out: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind in {"p", "h2", "h3", "blockquote"}:
            text = esc(block.get("text", ""))
            tag = kind
            out.append(f"<{tag}>{text}</{tag}>")
        elif kind in {"ul", "ol"}:
            items = "".join(f"<li>{esc(x)}</li>" for x in block.get("items", []))
            out.append(f"<{kind}>{items}</{kind}>")
        else:
            raise ValueError(f"ukendt body block: {kind}")
    return "\n    ".join(out)


def source_html(article: dict, ledger: dict) -> str:
    wanted = article.get("source_ids_to_display", [])
    sources = {s.get("id"): s for s in ledger.get("sources", [])}
    rows = []
    for sid in wanted:
        source = sources.get(sid)
        if not source:
            continue
        name = esc(source.get("name") or sid)
        url = source.get("url")
        if url:
            rows.append(f'<li><a href="{esc(url)}" rel="nofollow noopener">{name}</a></li>')
        else:
            rows.append(f"<li>{name}</li>")
    if not rows:
        return ""
    return '<section class="article-sources"><h2>Kilder</h2><ul>' + "".join(rows) + "</ul></section>"


def related_html(article: dict) -> tuple[str, str]:
    related = article.get("related") or []
    if not related:
        return "", ""
    rail_items = []
    below_items = []
    for i, item in enumerate(related):
        slug = esc(item["slug"])
        category = esc(item.get("category", "Nyhed"))
        title = esc(item["title"])
        img = item.get("image_src")
        alt = esc(item.get("image_alt", ""))
        image_html = f'<img src="{esc(img)}" alt="{alt}">' if img else ""
        rail = f'<a class="rail-item" href="{slug}.html">{image_html}<span><span>{category}</span> {title}</span></a>'
        if i < 3:
            rail_items.append(rail)
        teaser = esc(item.get("teaser", ""))
        below_items.append(f'<article><a href="{slug}.html">{image_html}</a><p class="section-label">{category}</p><h2><a href="{slug}.html">{title}</a></h2><p>{teaser}</p></article>')
    rail_html = '<aside class="article-rail"><p class="rail-title">Også i avisen</p>' + "".join(rail_items) + "</aside>"
    below_html = '<section class="wrap below">' + "".join(below_items[:4]) + "</section>"
    return rail_html, below_html


def build_article(path: Path) -> None:
    article = load_json(path)
    if path.name.startswith("_") or article.get("status") != "published":
        return
    if not article.get("published_at"):
        raise ValueError(f"published artikel mangler published_at: {path}")

    ledger_path = ROOT / article["ledger"]
    ledger = load_json(ledger_path)
    template = (ROOT / "templates" / "article.html").read_text(encoding="utf-8")

    slug = article["slug"]
    canonical = article.get("seo", {}).get("canonical") or f"{BASE_URL}/artikler/{slug}.html"
    seo_title = article.get("seo", {}).get("title") or article["title"]
    page_title = seo_title if "Morgentidende" in seo_title else f"{seo_title} – Morgentidende"
    description = article.get("seo", {}).get("description") or article["standfirst"]

    category = article["category"]
    schema_type = "NewsArticle" if category in {"Nyhed", "Krimi", "Politik", "Økonomi", "Udland", "Forbruger", "Kultur", "Videnskab", "Sundhed", "Parforhold", "Sport"} else "Article"
    image = article.get("image")
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "headline": article["title"],
        "description": description,
        "datePublished": article["published_at"],
        "author": {"@type": "Organization", "name": article.get("byline", "Morgentidende Redaktion")},
        "publisher": {"@type": "Organization", "name": "Morgentidende"},
        "mainEntityOfPage": canonical,
    }
    if article.get("updated_at"):
        schema["dateModified"] = article["updated_at"]
    if image and image.get("src"):
        schema["image"] = [image["src"]]

    rail_html, below_html = related_html(article)
    updated_label = ""
    if article.get("updated_at"):
        updated_label = f" · Opdateret {esc(dk_label(article['updated_at']))}"
    correction = article.get("correction_note")
    correction_html = ""
    if correction:
        correction_html = f'<aside class="theme-box"><strong>Rettelse:</strong> {esc(correction)}</aside>'

    related_teaser = ""
    if article.get("related_news_slug"):
        related_teaser = f'<aside class="related-teaser"><strong>Relateret:</strong> <a href="{esc(article["related_news_slug"])}.html">Læs den faktuelle nyhedsartikel</a></aside>'

    og_image = ""
    if image and image.get("src"):
        og_image = f'<meta property="og:image" content="{esc(image["src"])}">'

    replacements = {
        "{{SOURCE_PATH}}": esc(path.relative_to(ROOT)),
        "{{PAGE_TITLE}}": esc(page_title),
        "{{META_DESCRIPTION}}": esc(description),
        "{{CANONICAL_URL}}": esc(canonical),
        "{{OG_TITLE}}": esc(article["title"]),
        "{{OG_IMAGE}}": og_image,
        "{{SCHEMA_JSON}}": html.escape(json.dumps(schema, ensure_ascii=False, separators=(",", ":"))),
        "{{CATEGORY}}": esc(category),
        "{{H1}}": esc(article["title"]),
        "{{STANDFIRST}}": esc(article["standfirst"]),
        "{{PUBLISHED_ISO}}": esc(article["published_at"]),
        "{{PUBLISHED_LABEL}}": esc(dk_label(article["published_at"])),
        "{{UPDATED_LABEL}}": updated_label,
        "{{BYLINE}}": esc(article.get("byline", "Morgentidende Redaktion")),
        "{{BODY_HTML}}": render_blocks(article.get("body", [])),
        "{{SOURCES_HTML}}": source_html(article, ledger),
        "{{CORRECTION_HTML}}": correction_html,
        "{{RELATED_TEASER_HTML}}": related_teaser,
        "{{RAIL_HTML}}": rail_html,
        "{{BELOW_HTML}}": below_html,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)

    DOC_ARTICLES.mkdir(parents=True, exist_ok=True)
    (DOC_ARTICLES / f"{slug}.html").write_text(template, encoding="utf-8")


def front_item_url(slug: str) -> str:
    return f"artikler/{esc(slug)}.html"


def build_frontpage() -> None:
    state = load_json(ROOT / "content" / "frontpage.json")
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    date = datetime.fromisoformat(state["date"]).date()
    date_label = f"{WEEKDAYS[date.weekday()]} {date.day}. {MONTHS[date.month-1]} {date.year}"

    ticker = state["ticker"]
    ticker_html = f'<p><a href="{front_item_url(ticker["slug"])}">{esc(ticker["title"])}</a></p>'

    lead = state["lead"]
    lead_html = (
        '<section class="lead">'
        f'<figure class="lead-fig"><img src="{esc(lead["image_src"])}" alt="{esc(lead.get("image_alt", ""))}"></figure>'
        f'<p class="section-label">{esc(lead["category"])}</p>'
        f'<h1><a href="{front_item_url(lead["slug"])}">{esc(lead["title"])}</a></h1>'
        f'<p class="standfirst">{esc(lead["standfirst"])}</p>'
        f'<p class="meta">{esc(lead["published_label"])} · {esc(lead["category"])}</p>'
        '</section>'
    )

    rail_parts = ['<aside class="rail"><p class="rail-title">Også i dag</p>']
    for item in state.get("rail", []):
        rail_parts.append(
            f'<a class="rail-item" href="{front_item_url(item["slug"])}"><img src="{esc(item["image_src"])}" alt="{esc(item.get("image_alt", ""))}"><span><span>{esc(item["category"])}</span> {esc(item["title"])}</span></a>'
        )
    rail_parts.append("</aside>")

    stack_parts = ['<section class="stack">']
    for item in state.get("stack", []):
        stack_parts.append(
            f'<article class="card"><a href="{front_item_url(item["slug"])}"><img src="{esc(item["image_src"])}" alt="{esc(item.get("image_alt", ""))}"></a><p class="section-label">{esc(item["category"])}</p><h2><a href="{front_item_url(item["slug"])}">{esc(item["title"])}</a></h2><p>{esc(item.get("teaser", ""))}</p></article>'
        )
    stack_parts.append("</section>")

    narrow_parts = ['<section class="narrow">']
    for item in state.get("narrow", []):
        narrow_parts.append(
            f'<article><p class="section-label">{esc(item["category"])}</p><h2><a href="{front_item_url(item["slug"])}">{esc(item["title"])}</a></h2><p>{esc(item.get("teaser", ""))}</p></article>'
        )
    narrow_parts.append("</section>")

    replacements = {
        "{{DATE_ISO}}": esc(state["date"]),
        "{{DATE_LABEL}}": esc(date_label),
        "{{EDITION_LABEL}}": esc(state.get("edition_label", "Danmarks nye avis")),
        "{{TICKER_HTML}}": ticker_html,
        "{{LEAD_HTML}}": lead_html,
        "{{RAIL_HTML}}": "".join(rail_parts),
        "{{STACK_HTML}}": "".join(stack_parts),
        "{{NARROW_HTML}}": "".join(narrow_parts),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    (ROOT / "docs" / "index.html").write_text(template, encoding="utf-8")


def build_news_sitemap() -> None:
    now = datetime.now(timezone.utc)
    rows = []
    for path in sorted(ARTICLE_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        article = load_json(path)
        if article.get("status") != "published" or not article.get("published_at"):
            continue
        published = parse_iso(article["published_at"])
        if now - published.astimezone(timezone.utc) > timedelta(days=2):
            continue
        url = f"{BASE_URL}/artikler/{article['slug']}.html"
        rows.append(
            "<url>"
            f"<loc>{esc(url)}</loc>"
            "<news:news>"
            "<news:publication><news:name>Morgentidende</news:name><news:language>da</news:language></news:publication>"
            f"<news:publication_date>{esc(article['published_at'])}</news:publication_date>"
            f"<news:title>{esc(article['title'])}</news:title>"
            "</news:news></url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    (ROOT / "docs" / "news-sitemap.xml").write_text(xml, encoding="utf-8")


def build_sitemap() -> None:
    urls = [f"{BASE_URL}/", f"{BASE_URL}/nyhedsbrev.html", f"{BASE_URL}/om.html", f"{BASE_URL}/rettelser.html", f"{BASE_URL}/ai-politik.html"]
    urls.extend(f"{BASE_URL}/artikler/{p.name}" for p in sorted(DOC_ARTICLES.glob("*.html")))
    rows = [f"  <url><loc>{esc(url)}</loc></url>" for url in urls]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    (ROOT / "docs" / "sitemap.xml").write_text(xml, encoding="utf-8")


def main() -> None:
    for path in sorted(ARTICLE_DIR.glob("*.json")):
        build_article(path)
    build_frontpage()
    build_news_sitemap()
    build_sitemap()
    print("Build OK")


if __name__ == "__main__":
    main()
