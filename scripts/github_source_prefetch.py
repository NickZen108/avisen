#!/usr/bin/env python3
"""Best-effort GitHub-side source prefetch for Cloudflare Research.

The output is advisory only. Cloudflare validates the scan fingerprint and exact URL
before using any prefetched text. Missing/failed items simply fall back to Cloudflare fetch.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

UA = "MorgentidendeGitHubPrefetch/1.0"
MAX_TEXT = 12000
MAX_LINKS = 24


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def strip_html(value: str) -> str:
    value = re.sub(r"<script\b[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style\b[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<nav\b[\s\S]*?</nav>", " ", value, flags=re.I)
    value = re.sub(r"<footer\b[\s\S]*?</footer>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def outbound_links(raw_html: str, base_url: str) -> list[dict]:
    base_host = (urlparse(base_url).hostname or "").removeprefix("www.")
    seen, out = set(), []
    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', raw_html, flags=re.I):
        try:
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            host = (parsed.hostname or "").removeprefix("www.")
            if parsed.scheme not in {"http", "https"} or not host or host == base_host or url in seen:
                continue
            seen.add(url)
            out.append({"url": url, "text": strip_html(label)[:180]})
            if len(out) >= MAX_LINKS:
                break
        except Exception:
            continue
    return out


def score(signal: dict, now: datetime) -> tuple:
    published = parse_time(signal.get("published_at"))
    if published is None:
        freshness = 2
    else:
        age = max(0, (now - published).total_seconds() / 3600)
        freshness = 12 if age <= 2 else 9 if age <= 6 else 6 if age <= 24 else 2 if age <= 72 else -6
    feed_rank = signal.get("feed_rank") if isinstance(signal.get("feed_rank"), int) else 99
    feed_score = max(0, 8 - feed_rank // 3)
    source_score = max(0, min(4, int(signal.get("source_priority") or 2)))
    return freshness + feed_score + source_score, published.timestamp() if published else 0


def choose(scan: dict, limit: int) -> list[dict]:
    now = parse_time(scan.get("generated_at")) or datetime.now(timezone.utc)
    rows = [s for s in scan.get("signals") or [] if isinstance(s, dict) and str(s.get("url") or "").startswith(("http://", "https://"))]
    rows.sort(key=lambda s: (-score(s, now)[0], -score(s, now)[1], int(s.get("feed_rank") or 99), str(s.get("source") or "")))
    chosen, per_source = [], {}
    for signal in rows:
        source = str(signal.get("source") or "")
        if per_source.get(source, 0) >= 2:
            continue
        chosen.append(signal)
        per_source[source] = per_source.get(source, 0) + 1
        if len(chosen) >= limit:
            break
    return chosen


def fetch_one(signal: dict) -> dict:
    url = str(signal.get("url") or "")
    base = {"url": url, "ok": False}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.2"})
        with urllib.request.urlopen(req, timeout=10) as response:
            ctype = str(response.headers.get("content-type") or "").lower()
            if "html" not in ctype and "text" not in ctype:
                return {**base, "status": getattr(response, "status", None)}
            raw = response.read(1_500_000).decode("utf-8", errors="replace")
            text = strip_html(raw)[:MAX_TEXT]
            if len(text) < 160:
                return {**base, "status": getattr(response, "status", None)}
            final_url = response.geturl()
            return {
                "url": url,
                "ok": True,
                "status": getattr(response, "status", 200),
                "final_url": final_url,
                "excerpt": text,
                "outbound_links": outbound_links(raw, final_url) if "html" in ctype else [],
            }
    except Exception as exc:
        return {**base, "error": type(exc).__name__}


def build(scan: dict, limit: int = 12) -> dict:
    selected = choose(scan, limit)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        items = list(pool.map(fetch_one, selected))
    return {
        "schema_version": 1,
        "scan_fingerprint": scan.get("fingerprint"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "items": items,
        "attempted": len(items),
        "usable": sum(1 for x in items if x.get("ok")),
    }


def self_test() -> None:
    scan = {
        "fingerprint": "abc",
        "generated_at": "2026-09-01T12:00:00Z",
        "signals": [
            {"url": "https://a.test/1", "source": "A", "source_priority": 4, "feed_rank": 0, "published_at": "2026-09-01T11:30:00Z"},
            {"url": "https://a.test/2", "source": "A", "source_priority": 4, "feed_rank": 1, "published_at": "2026-09-01T11:20:00Z"},
            {"url": "https://a.test/3", "source": "A", "source_priority": 4, "feed_rank": 2, "published_at": "2026-09-01T11:10:00Z"},
            {"url": "https://b.test/1", "source": "B", "source_priority": 3, "feed_rank": 0, "published_at": "2026-09-01T11:00:00Z"},
        ],
    }
    picked = choose(scan, 4)
    assert len(picked) == 3
    assert sum(1 for x in picked if x["source"] == "A") == 2
    assert strip_html("<p>A &amp; B</p>") == "A & B"
    print("github_source_prefetch self-test: PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan")
    ap.add_argument("--output")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    payload = build(scan, max(1, min(20, args.limit)))
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("scan_fingerprint", "attempted", "usable")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
