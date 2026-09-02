#!/usr/bin/env python3
"""Cheap GitHub-side gate that avoids unnecessary Workers AI editorial calls.

This gate is deliberately advisory/fail-open. Cloudflare remains the source of truth
for scanning and editorial state; if inputs are missing or malformed we allow the
normal Cloudflare editorial cycle rather than risk suppressing news.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Temporary feedback burst requested 2026-09-02. It expires automatically after
# three hours; normal cheap dispatch resumes without another code change.
BURST_UNTIL = datetime(2026, 9, 2, 12, 32, tzinfo=timezone.utc)
BURST_MAX_CYCLES = 3


def parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def signal_key(signal: dict) -> str:
    return f"{signal.get('normalized') or ''}|{signal.get('url') or ''}"


def recommended_cycles(scan: dict, history: list[dict], maximum: int = 3) -> tuple[int, str]:
    if not isinstance(scan, dict) or not isinstance(scan.get("signals"), list):
        return maximum, "fail-open: malformed scan"
    if not isinstance(history, list):
        return maximum, "fail-open: malformed editorial history"

    handled: set[str] = set()
    for row in history[:144]:
        if not isinstance(row, dict):
            continue
        for key in row.get("handled_signal_keys") or []:
            if isinstance(key, str) and key:
                handled.add(key)

    now = parse_time(scan.get("generated_at")) or datetime.now(timezone.utc)
    eligible = []
    for signal in scan["signals"]:
        if not isinstance(signal, dict) or not signal.get("url"):
            continue
        key = signal_key(signal)
        if key in handled:
            continue
        published = parse_time(signal.get("published_at"))
        if published is not None and (now - published).total_seconds() > 72 * 3600:
            continue
        eligible.append(signal)

    if not eligible:
        return 0, "no fresh unhandled candidates"

    related = 0
    try:
        from scripts.lead_followup import is_active, load_state, load_article, classify_candidate
        state = load_state()
        if is_active(state, now):
            lead = load_article(state.get("lead_slug"))
            related = sum(1 for signal in eligible if classify_candidate(signal, lead)["related"])
    except Exception:
        related = 0

    burst_active = datetime.now(timezone.utc) < BURST_UNTIL
    if burst_active:
        count = min(BURST_MAX_CYCLES, len(eligible))
        reason = f"burst mode until {BURST_UNTIL.isoformat()}: {len(eligible)} fresh unhandled candidates"
        if related:
            reason += f"; {related} related to active lead"
        return count, reason

    count = min(maximum, len(eligible))
    if related and count == 0:
        count = 1
    reason = f"{len(eligible)} fresh unhandled candidates"
    if related:
        reason += f"; {related} related to active lead"
    return count, reason


def write_output(path: str | None, cycles: int, reason: str) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"cycles={cycles}\n")
        fh.write("reason=" + reason.replace("\n", " ") + "\n")


def self_test() -> None:
    scan = {
        "generated_at": "2026-09-01T12:00:00Z",
        "signals": [
            {"normalized": "a", "url": "https://a.test/1", "published_at": "2026-09-01T11:00:00Z"},
            {"normalized": "b", "url": "https://b.test/2", "published_at": "2026-09-01T10:00:00Z"},
            {"normalized": "old", "url": "https://c.test/3", "published_at": "2026-08-20T10:00:00Z"},
        ],
    }
    n, _ = recommended_cycles(scan, [], 3)
    assert n == 2, n
    history = [{"handled_signal_keys": ["a|https://a.test/1"]}]
    n, _ = recommended_cycles(scan, history, 3)
    assert n == 1, n
    history = [{"handled_signal_keys": ["a|https://a.test/1", "b|https://b.test/2"]}]
    n, _ = recommended_cycles(scan, history, 3)
    assert n == 0, n
    n, reason = recommended_cycles({}, [], 3)
    assert n == 3 and reason.startswith("fail-open")
    print("editorial_dispatch_gate self-test: PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan")
    ap.add_argument("--history")
    ap.add_argument("--max-cycles", type=int, default=3)
    ap.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    maximum = max(1, min(3, args.max_cycles))
    try:
        scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
        history = json.loads(Path(args.history).read_text(encoding="utf-8"))
        cycles, reason = recommended_cycles(scan, history, maximum)
    except Exception as exc:
        cycles, reason = maximum, f"fail-open: {type(exc).__name__}"

    write_output(args.github_output, cycles, reason)
    print(json.dumps({"cycles": cycles, "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
