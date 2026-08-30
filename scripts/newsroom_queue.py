#!/usr/bin/env python3
"""Turn scan/latest.md into a deterministic, machine-readable newsroom queue.

This script does no editorial judgement and calls no AI/API. It only inventories
signals found by the free GitHub Actions scan so the AI newsdesk can consume a
stable queue later.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scan" / "latest.md"
OUT = ROOT / "queue" / "candidates.json"


def normalize_title(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9æøåäöüéèáàíìóòúùß ]+", " ", value)
    return " ".join(value.split())


def parse_scan(text: str) -> tuple[str | None, list[dict]]:
    scan_label = None
    signals: list[dict] = []
    source = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# Scan "):
            scan_label = line.removeprefix("# Scan ").strip()
        elif line.startswith("## "):
            source = line[3:].strip()
        elif line.startswith("- ") and source:
            headline = line[2:].strip()
            if not headline or headline.startswith("("):
                continue
            signals.append(
                {
                    "source": source,
                    "headline": headline,
                    "normalized": normalize_title(headline),
                }
            )
    signals.sort(key=lambda x: (x["normalized"], x["source"], x["headline"]))
    return scan_label, signals


def main() -> int:
    if not SCAN.exists():
        raise SystemExit("scan/latest.md mangler")

    scan_label, signals = parse_scan(SCAN.read_text(encoding="utf-8"))
    stable = [{"source": x["source"], "headline": x["headline"], "normalized": x["normalized"]} for x in signals]
    fingerprint = hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            if old.get("fingerprint") == fingerprint:
                print("Newsroom queue uændret")
                return 0
        except Exception:
            pass

    grouped: dict[str, list[dict]] = {}
    for signal in signals:
        grouped.setdefault(signal["normalized"], []).append(signal)

    exact_clusters = []
    for normalized, items in grouped.items():
        distinct_sources = sorted({x["source"] for x in items})
        if len(distinct_sources) >= 2:
            exact_clusters.append(
                {
                    "normalized": normalized,
                    "sources": distinct_sources,
                    "headlines": [x["headline"] for x in items],
                    "note": "Exact normalized headline match only; not proof of independent sourcing.",
                }
            )

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scan_label": scan_label,
        "fingerprint": fingerprint,
        "signal_count": len(signals),
        "signals": signals,
        "exact_clusters": exact_clusters,
        "editorial_status": "UNRANKED",
        "warning": "This queue is an inventory, not a news-value or verification decision.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Newsroom queue opdateret: {len(signals)} signaler")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
