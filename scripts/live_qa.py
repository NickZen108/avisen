#!/usr/bin/env python3
"""Hourly live smoke test for the public Morgentidende site."""
from __future__ import annotations

import argparse
import html.parser
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "MorgentidendeLiveQA/1.0"


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
        if tag == "img" and data.get("src"):
            self.images.append(data["src"])


def fetch(url: str, timeout: int = 20) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read(2_000_000)


def check_url(url: str) -> str | None:
    try:
        status, _ = fetch(url)
        if status >= 400:
            return f"HTTP {status} {url}"
        return None
    except Exception as exc:
        return f"FETCH {url}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://nickzen108.github.io/avisen/")
    parser.add_argument("--report", default="reports/qa/live-latest.md")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    failures: list[str] = []
    checked: set[str] = set()

    try:
        status, body = fetch(base)
        if status >= 400:
            failures.append(f"Forside HTTP {status}")
            body = b""
    except Exception as exc:
        failures.append(f"Forside kunne ikke hentes: {exc}")
        body = b""

    parser_html = LinkParser()
    if body:
        parser_html.feed(body.decode("utf-8", errors="replace"))

    article_urls = []
    for href in parser_html.links:
        url = urllib.parse.urljoin(base, href)
        if "/artikler/" in url and url.endswith(".html") and url not in article_urls:
            article_urls.append(url)

    image_urls = {urllib.parse.urljoin(base, src) for src in parser_html.images}

    for url in article_urls[:30]:
        try:
            status, article_body = fetch(url)
            checked.add(url)
            if status >= 400:
                failures.append(f"Artikel HTTP {status}: {url}")
                continue
            p = LinkParser()
            p.feed(article_body.decode("utf-8", errors="replace"))
            for src in p.images:
                image_urls.add(urllib.parse.urljoin(url, src))
        except Exception as exc:
            failures.append(f"Artikel kunne ikke hentes: {url}: {exc}")

    for url in sorted(image_urls):
        if url in checked:
            continue
        failure = check_url(url)
        checked.add(url)
        if failure:
            failures.append(failure)
        time.sleep(0.05)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Live QA {stamp}", "", f"Base: {base}", f"Artikler testet: {len(article_urls[:30])}", f"URLs/assets testet: {len(checked)}", ""]
    if failures:
        lines += ["## FAIL", ""] + [f"- {x}" for x in failures]
    else:
        lines += ["## PASS", "", "Ingen døde forside-/artikel-/billed-URLs fundet i denne smoke test."]

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Live QA: {'FAIL' if failures else 'PASS'} ({len(failures)} fejl)")
    return 1 if failures and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
