#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTEMPTS = ROOT / "reports" / "editorial" / "publication-attempts.jsonl"
DAILY = ROOT / "reports" / "editorial" / "ai-usage-daily.json"
CACHE = ROOT / "docs" / "img" / "cache"
MANIFEST = CACHE / "manifest.json"

RAW_KEEP_DAYS = 7
RAW_KEEP_MAX = 500
DAILY_KEEP_DAYS = 30


def parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def rotate_attempts() -> dict:
    if not ATTEMPTS.exists():
        return {"kept": 0, "removed": 0, "days": 0}
    rows = []
    for line in ATTEMPTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        rows.append(row)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RAW_KEEP_DAYS)
    recent = [r for r in rows if (parse_time(r.get("at")) or now) >= cutoff]
    recent = recent[-RAW_KEEP_MAX:]
    ATTEMPTS.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in recent), encoding="utf-8")

    by_day = defaultdict(lambda: {
        "attempts": 0, "approved": 0, "holds_or_drops": 0,
        "ai_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
        "total_tokens": 0, "estimated_neurons": 0.0,
        "retries": 0, "evidence_retries": 0,
    })
    daily_cutoff = (now - timedelta(days=DAILY_KEEP_DAYS)).date()
    for r in rows:
        ts = parse_time(r.get("at"))
        if not ts or ts.date() < daily_cutoff:
            continue
        day = ts.date().isoformat()
        d = by_day[day]
        d["attempts"] += 1
        if r.get("status") == "approved":
            d["approved"] += 1
        else:
            d["holds_or_drops"] += 1
        usage = r.get("ai_usage") or {}
        d["ai_calls"] += int(usage.get("calls") or 0)
        d["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        d["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        d["total_tokens"] += int(usage.get("total_tokens") or 0)
        d["estimated_neurons"] += float(usage.get("estimated_neurons") or 0)
        diag = r.get("diagnostics") or {}
        attempts = int(diag.get("article_attempts") or 1)
        if attempts > 1:
            d["retries"] += attempts - 1
        routes = diag.get("retry_routing") or []
        d["evidence_retries"] += sum(1 for x in routes if "evidence" in str(x).lower())

    out = []
    for day in sorted(by_day):
        d = dict(by_day[day])
        d["date"] = day
        d["estimated_neurons"] = round(d["estimated_neurons"], 3)
        d["neurons_per_approved"] = round(d["estimated_neurons"] / d["approved"], 3) if d["approved"] else None
        d["calls_per_approved"] = round(d["ai_calls"] / d["approved"], 2) if d["approved"] else None
        out.append(d)
    DAILY.write_text(json.dumps({"schema_version": 1, "updated_at": now.isoformat(), "days": out}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"kept": len(recent), "removed": max(0, len(rows) - len(recent)), "days": len(out)}


def prune_orphan_cache() -> dict:
    if not MANIFEST.exists() or not CACHE.exists():
        return {"removed_files": 0, "manifest_entries": 0}
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {"removed_files": 0, "manifest_entries": 0}
    if not isinstance(manifest, dict):
        return {"removed_files": 0, "manifest_entries": 0}

    referenced = set()
    cleaned = {}
    for url, record in manifest.items():
        if not isinstance(record, dict):
            continue
        file_path = str(record.get("file") or "")
        if not file_path.startswith("/img/cache/"):
            continue
        target = ROOT / "docs" / file_path.lstrip("/")
        if target.exists():
            referenced.add(target.resolve())
            cleaned[url] = record
    removed = 0
    for p in CACHE.iterdir():
        if p.name == "manifest.json" or not p.is_file():
            continue
        if p.resolve() not in referenced:
            p.unlink()
            removed += 1
    if cleaned != manifest:
        MANIFEST.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"removed_files": removed, "manifest_entries": len(cleaned)}


def main() -> int:
    telemetry = rotate_attempts()
    cache = prune_orphan_cache()
    print(json.dumps({"telemetry": telemetry, "cache": cache}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
