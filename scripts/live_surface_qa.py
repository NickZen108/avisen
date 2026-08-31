#!/usr/bin/env python3
"""Live proof for responsive shell, dark mode and rendered hero assets."""
from __future__ import annotations

import argparse
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://morgentidende.nicolaipetersen108.workers.dev/"


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def fetch(url: str, limit: int = 8_000_000) -> tuple[str, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeSurfaceQA/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.headers.get("content-type", ""), response.read(limit), response.geturl()


def html(url: str) -> tuple[str, str]:
    ctype, body, final = fetch(url, 4_000_000)
    if "html" not in ctype.lower():
        raise ValueError(f"ikke HTML: {ctype}")
    return body.decode("utf-8", errors="replace"), final


def hero_src(page: str) -> str | None:
    match = re.search(r'<figure\b[^>]*class=["\'][^"\']*\blead-fig\b[^"\']*["\'][^>]*>[\s\S]*?<img\b[^>]*src=["\']([^"\']+)["\']', page, re.I)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--recent-hours", type=int, default=24)
    parser.add_argument("--report", default="reports/qa/live-surface-latest.md")
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.recent_hours)
    faults: list[str] = []
    pages_checked = 0
    heroes_checked = 0

    try:
        front, _ = html(base)
        pages_checked += 1
        for needle, label in (
            ('name="viewport"', "responsive viewport"),
            ("theme.css", "theme.css"),
            ("theme.js", "theme.js"),
            ('class="theme-toggle"', "dark-mode switch"),
            ('role="switch"', "accessible dark-mode switch"),
        ):
            if needle not in front:
                faults.append(f"forside mangler {label}")
        for asset in ("theme.css", "theme.js", "style.css"):
            try:
                ctype, body, _ = fetch(urllib.parse.urljoin(base, asset), 2_000_000)
                if len(body) < 100:
                    faults.append(f"{asset} er tom/for lille")
                if asset.endswith(".css") and "css" not in ctype.lower():
                    faults.append(f"{asset} forkert content-type {ctype}")
                if asset.endswith(".js") and not any(x in ctype.lower() for x in ("javascript", "text/plain")):
                    faults.append(f"{asset} forkert content-type {ctype}")
            except Exception as exc:
                faults.append(f"{asset} kunne ikke hentes: {exc}")
    except Exception as exc:
        faults.append(f"forside kunne ikke kontrolleres: {exc}")

    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Pillow required for live_surface_qa.py")

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
            faults.append(f"{path.name}: canonical parse {exc}")
            continue
        slug = article.get("slug")
        url = urllib.parse.urljoin(base, f"artikler/{slug}.html")
        try:
            page, final = html(url); pages_checked += 1
        except Exception as exc:
            faults.append(f"{slug}: live side {exc}")
            continue
        if 'name="viewport"' not in page:
            faults.append(f"{slug}: mangler viewport")
        if "theme.css" not in page or "theme.js" not in page or 'class="theme-toggle"' not in page:
            faults.append(f"{slug}: dark-mode shell mangler")

        image = article.get("image") or {}
        if image.get("src") and image.get("placement", "lead") == "lead":
            src = hero_src(page)
            if not src:
                faults.append(f"{slug}: canonical lead-hero er ikke renderet som lead-fig")
                continue
            hero_url = urllib.parse.urljoin(final, src)
            ctype = ""
            try:
                ctype, body, _ = fetch(hero_url)
                if "svg" in ctype.lower() or hero_url.lower().split("?", 1)[0].endswith(".svg"):
                    continue
                with Image.open(io.BytesIO(body)) as im:
                    w, h = im.size
                    heroes_checked += 1
                    if w < 600 or h < 300:
                        faults.append(f"{slug}: hero-kilde for lille {w}x{h}")
                    if w <= 0 or h <= 0:
                        faults.append(f"{slug}: ugyldige hero-dimensioner")
            except Exception as exc:
                is_svg = "svg" in ctype.lower() or hero_url.lower().split("?", 1)[0].endswith(".svg")
                if not is_svg:
                    faults.append(f"{slug}: hero kan ikke dimensionskontrolleres: {exc}")

    report = Path(args.report); report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Live surface QA", "", f"Pages checked: {pages_checked}", f"Raster heroes checked: {heroes_checked}", ""]
    if faults:
        lines += ["FAIL", *[f"- {x}" for x in faults]]
    else:
        lines.append("PASS")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
