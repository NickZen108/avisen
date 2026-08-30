#!/usr/bin/env python3
"""Release due scheduled Morgentidende articles into canonical published state."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "content" / "articles"


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp mangler timezone: {value}")
    return dt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", help="ISO timestamp override for deterministic testing")
    args = parser.parse_args()

    now = parse_iso(args.now).astimezone(timezone.utc) if args.now else datetime.now(timezone.utc)
    published_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    changed = 0

    for path in sorted(ARTICLE_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        article = json.loads(path.read_text(encoding="utf-8"))
        if article.get("status") != "scheduled":
            continue

        scheduled_for = article.get("scheduled_for")
        if not scheduled_for:
            raise SystemExit(f"{path.name}: scheduled artikel mangler scheduled_for")

        due = parse_iso(scheduled_for).astimezone(timezone.utc) <= now
        if not due:
            continue

        if article.get("manual_review"):
            raise SystemExit(f"{path.name}: manual_review=true må aldrig frigives automatisk")

        article["status"] = "published"
        article["published_at"] = published_at
        article["released_from_schedule_at"] = published_at
        path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"RELEASED {path.name} scheduled_for={scheduled_for} published_at={published_at}")
        changed += 1

    print(f"Scheduled release: {changed} article(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
