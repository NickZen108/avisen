#!/usr/bin/env python3
"""Post-publication visual QA for recent Morgentidende articles.

This is the deterministic companion to the Live proofreader agent. It verifies
that canonical hero images are actually present on the live page and that image
assets return plausible image responses instead of HTML/error payloads.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://morgentidende.nicolaipetersen108.workers.dev/"


class ImgParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "img":
            return
        item = {k.lower(): (v or "") for k, v in attrs}
        if item.get("src"):
            self.images.append(item)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def get(url: str, limit: int = 5_000_000) -> tuple[int, str, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeVisualQA/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        body = response.read(limit)
        return response.status, response.headers.get("content-type", ""), body, response.geturl()


def plausible_image(content_type: str, body: bytes) -> bool:
    ctype = content_type.lower()
    if ctype.startswith("image/"):
        return len(body) >= 100
    head = body[:512].lstrip().lower()
    return (
        body.startswith(b"\xff\xd8\xff")
        or body.startswith(b"\x89PNG\r\n\x1a\n")
        or body.startswith((b"GIF87a", b"GIF89a"))
        or body.startswith(b"RIFF") and b"WEBP" in body[:16]
        or head.startswith(b"<svg")
        or b"<svg" in head
    ) and len(body) >= 100


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--recent-hours", type=int, default=24)
    parser.add_argument("--report", default="reports/qa/live-visual-latest.md")
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.recent_hours)
    faults: list[str] = []
    checked_pages = 0
    checked_images = 0

    for path in sorted((ROOT / "content" / "articles").glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
            if article.get("status") != "published" or not article.get("published_at"):
                continue
            if parse_time(article["published_at"]) < cutoff:
                continue
        except Exception as exc:
            faults.append(f"canonical parse {path.name}: {exc}")
            continue

        slug = article.get("slug")
        if not slug:
            faults.append(f"canonical slug mangler: {path.name}")
            continue
        page_url = urllib.parse.urljoin(base, f"artikler/{slug}.html")
        try:
            status, content_type, body, final_url = get(page_url, limit=3_000_000)
            checked_pages += 1
            if status >= 400 or "html" not in content_type.lower():
                faults.append(f"side {slug}: HTTP/content-type {status} {content_type}")
                continue
            html = body.decode("utf-8", errors="replace")
        except Exception as exc:
            faults.append(f"side {slug}: {exc}")
            continue

        hp = ImgParser()
        hp.feed(html)
        if not hp.images:
            faults.append(f"side {slug}: ingen <img>-elementer på live-siden")
            continue

        canonical_image = (article.get("image") or {}).get("src")
        resolved_live = {urllib.parse.urljoin(final_url, img["src"]) for img in hp.images}
        if canonical_image:
            resolved_canonical = urllib.parse.urljoin(base, canonical_image)
            if resolved_canonical not in resolved_live and canonical_image not in {img["src"] for img in hp.images}:
                faults.append(f"side {slug}: canonical hero findes ikke i live HTML: {canonical_image}")

        for img in hp.images:
            src = urllib.parse.urljoin(final_url, img["src"])
            alt = img.get("alt", "").strip()
            if not alt:
                faults.append(f"side {slug}: billede mangler alt-tekst: {src}")
            try:
                img_status, img_type, img_body, img_final = get(src)
                checked_images += 1
                if img_status >= 400:
                    faults.append(f"side {slug}: billede HTTP {img_status}: {src}")
                elif not plausible_image(img_type, img_body):
                    faults.append(f"side {slug}: ugyldig billedrespons {img_type}: {img_final}")
            except Exception as exc:
                faults.append(f"side {slug}: billede kunne ikke hentes {src}: {exc}")

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Live visual QA",
        "",
        f"Pages checked: {checked_pages}",
        f"Images checked: {checked_images}",
        "",
    ]
    if faults:
        lines.append("FAIL")
        lines.extend(f"- {fault}" for fault in faults)
    else:
        lines.append("PASS")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
