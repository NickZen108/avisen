#!/usr/bin/env python3
"""Cache external images used by generated public HTML into docs/img/cache.

Editorial source metadata (credit, licence, source_url) stays canonical in content/.
The generated public surface uses local Cloudflare assets so readers are not
subject to third-party hotlink failures or rate limits.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTICLE_DIR = ROOT / "content" / "articles"
CACHE = DOCS / "img" / "cache"
MANIFEST = CACHE / "manifest.json"
PUBLIC_BASE = "https://morgentidende.nicolaipetersen108.workers.dev"
UA = "MorgentidendeImageCache/1.2 (+https://morgentidende.nicolaipetersen108.workers.dev/)"
IMG_RE = re.compile(r'<img\b[^>]*\bsrc=["\'](https?://[^"\']+)["\']', re.I)

LEGACY_REPLACEMENTS = {
    "https://commons.wikimedia.org/wiki/Special:FilePath/Grubenhaus_Warendorf.jpg": "../img/soften.svg",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Nyhavn_from_Kongens_Nytorv.jpg": "https://commons.wikimedia.org/wiki/Special:FilePath/Nyhavn-Copenhagen.jpg",
}

EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
}


def load_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST.exists():
        return {}
    try:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def infer_ext(content_type: str, final_url: str) -> str:
    ctype = content_type.split(";", 1)[0].strip().lower()
    if ctype in EXT_BY_TYPE:
        return EXT_BY_TYPE[ctype]
    suffix = Path(urlparse(final_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(ctype) if ctype else None
    return guessed or ".img"


def plausible_image(content_type: str, body: bytes) -> bool:
    ctype = content_type.lower()
    if ctype.startswith("image/") and len(body) >= 100:
        return True
    head = body[:1024].lstrip().lower()
    return (
        body.startswith(b"\xff\xd8\xff")
        or body.startswith(b"\x89PNG\r\n\x1a\n")
        or body.startswith((b"GIF87a", b"GIF89a"))
        or (body.startswith(b"RIFF") and b"WEBP" in body[:16])
        or head.startswith(b"<svg")
        or b"<svg" in head
    ) and len(body) >= 100


def origin_request_url(url: str) -> str:
    if "commons.wikimedia.org/wiki/Special:FilePath/" in url and "width=" not in url:
        separator = "&" if "?" in url else "?"
        return url + separator + "width=1600"
    return url


def fetch_image(url: str) -> tuple[bytes, str, str]:
    request_url = origin_request_url(url)
    delay = 3
    last_error: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(request_url, headers={"User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                body = response.read(20_000_000)
                ctype = response.headers.get("content-type", "")
                final_url = response.geturl()
                if not plausible_image(ctype, body):
                    raise RuntimeError(f"not an image: {ctype} {final_url}")
                return body, ctype, final_url
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504}:
                raise
        except Exception as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"image fetch failed after retries: {url}: {last_error}")


def public_article_names() -> set[str]:
    names: set[str] = set()
    for p in ARTICLE_DIR.glob("*.json"):
        if p.name.startswith("_"):
            continue
        try:
            article = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if article.get("status") == "published" and article.get("slug"):
            names.add(f"{article['slug']}.html")
    legacy = ROOT / "config" / "legacy-articles.txt"
    if legacy.exists():
        names.update(x.strip() for x in legacy.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#"))
    return names


def html_files() -> list[Path]:
    files = [DOCS / "index.html"]
    allowed = public_article_names()
    files.extend(p for p in sorted((DOCS / "artikler").glob("*.html")) if p.name in allowed)
    return [p for p in files if p.exists()]


def repair_legacy_html(pages: list[Path]) -> None:
    for page in pages:
        text = page.read_text(encoding="utf-8")
        changed = text
        for source, replacement in LEGACY_REPLACEMENTS.items():
            changed = changed.replace(source, replacement)
        if changed != text:
            page.write_text(changed, encoding="utf-8")
            print(f"repaired legacy image reference in {page.relative_to(ROOT)}")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    pages = html_files()
    repair_legacy_html(pages)

    sources: list[str] = []
    seen: set[str] = set()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for url in IMG_RE.findall(text):
            if url.startswith(PUBLIC_BASE + "/"):
                continue
            if url not in seen:
                seen.add(url)
                sources.append(url)

    failures: list[str] = []
    for url in sources:
        record = manifest.get(url) or {}
        cached_file = record.get("file")
        if cached_file and (DOCS / cached_file.lstrip("/")).exists():
            continue
        try:
            body, content_type, final_url = fetch_image(url)
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
            ext = infer_ext(content_type, final_url)
            filename = f"{digest}{ext}"
            target = CACHE / filename
            target.write_bytes(body)
            public_path = f"/img/cache/{filename}"
            manifest[url] = {
                "file": public_path,
                "public_url": PUBLIC_BASE + public_path,
                "content_type": content_type.split(";", 1)[0].strip().lower(),
                "origin_final_url": final_url,
            }
            print(f"cached {url} -> {public_path}")
            time.sleep(1)
        except Exception as exc:
            failures.append(f"{url}: {exc}")
            print(f"WARNING cache miss: {url}: {exc}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        changed = text
        for source, record in manifest.items():
            public_url = record.get("public_url")
            if public_url:
                changed = changed.replace(source, public_url)
        if changed != text:
            page.write_text(changed, encoding="utf-8")

    if failures:
        print("Image cache failures:")
        for failure in failures:
            print("-", failure)
        return 1
    print(f"Image cache OK: {len(sources)} external image URLs, {len(manifest)} cached mappings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
