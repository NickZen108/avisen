#!/usr/bin/env python3
"""Sync Cloudflare Newsdesk runtime output into GitHub source-of-truth files.

Cloudflare performs frequent feed retrieval and keeps runtime state. GitHub keeps
the durable editorial record consumed by the rest of Pipeline v2.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scan" / "latest.md"
QUEUE = ROOT / "queue" / "candidates.json"
DEFAULT_URL = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/candidates"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeGitHubSync/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"Cloudflare Newsdesk returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def validate(payload: dict) -> None:
    if payload.get("runtime") != "cloudflare-workers":
        raise ValueError("Unexpected runtime marker")
    if not isinstance(payload.get("signals"), list):
        raise ValueError("signals must be a list")
    if not payload.get("generated_at") or not payload.get("fingerprint"):
        raise ValueError("generated_at/fingerprint missing")
    for signal in payload["signals"]:
        if not signal.get("source") or not signal.get("headline") or not signal.get("normalized"):
            raise ValueError("Malformed signal")


def render_scan(payload: dict) -> str:
    lines = [
        f"# Scan {payload['generated_at']} (Cloudflare runtime)",
        "",
        "Kildehentning udført af Cloudflare Newsdesk Worker. GitHub er redaktionel source of truth.",
        "",
    ]
    feeds = {x.get("source"): x for x in payload.get("feeds", [])}
    grouped: dict[str, list[dict]] = {}
    for signal in payload["signals"]:
        grouped.setdefault(signal["source"], []).append(signal)

    for source in sorted(set(feeds) | set(grouped)):
        lines.append(f"## {source}")
        status = feeds.get(source, {})
        if status and not status.get("ok"):
            lines.append(f"- (feed ikke nået; status={status.get('status')})")
        else:
            for signal in grouped.get(source, []):
                lines.append(f"- {signal['headline']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    url = os.environ.get("CLOUDFLARE_NEWSDESK_URL", DEFAULT_URL)
    payload = fetch_json(url)
    validate(payload)

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    SCAN.parent.mkdir(parents=True, exist_ok=True)

    existing = None
    if QUEUE.exists():
        try:
            existing = json.loads(QUEUE.read_text(encoding="utf-8"))
        except Exception:
            existing = None

    if existing and existing.get("fingerprint") == payload.get("fingerprint"):
        print("Cloudflare Newsdesk queue uændret")
        return 0

    QUEUE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCAN.write_text(render_scan(payload), encoding="utf-8")
    print(f"Synkroniseret {payload['signal_count']} signaler fra Cloudflare Newsdesk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
