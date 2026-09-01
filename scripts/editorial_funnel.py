#!/usr/bin/env python3
"""Cheap operational funnel report for the Cloudflare editorial pipeline.

Counts editorial attempts that got past Newsdesk and shows where they stopped.
This is an operational metric, not a quality score: repeated attempts at the same
story can appear more than once.
"""
from __future__ import annotations
import argparse, collections, json, urllib.request

DEFAULT_URL = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/editorial/history"


def load(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeFunnel/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    rows = load(args.url)

    # Newsdesk-stage WATCH/DROP never entered the downstream publishing funnel.
    downstream = [r for r in rows if (r.get("stage") or "approved") != "newsdesk"]
    approved = [r for r in downstream if r.get("status") == "approved"]
    rejected = [r for r in downstream if r.get("status") not in {"approved", "watch"}]
    parked = [r for r in downstream if r.get("status") == "watch"]
    denominator = len(downstream)
    reject_rate = (len(rejected) / denominator * 100) if denominator else None

    stages = collections.Counter((r.get("stage") or "approved") for r in downstream)
    reasons = collections.Counter((r.get("stage") or "approved", r.get("reason") or "") for r in downstream if r.get("status") != "approved")
    tokens = neurons = calls = 0.0
    metered = 0
    for r in downstream:
        u = r.get("ai_usage") or {}
        if u:
            metered += 1
            tokens += float(u.get("total_tokens") or 0)
            neurons += float(u.get("estimated_neurons") or 0)
            calls += float(u.get("calls") or 0)

    report = {
        "history_rows": len(rows),
        "post_newsdesk_attempts": denominator,
        "approved": len(approved),
        "parked_watch": len(parked),
        "rejected_or_held": len(rejected),
        "post_newsdesk_rejection_rate_pct": round(reject_rate, 2) if reject_rate is not None else None,
        "long_term_target_pct": 10,
        "stage_counts": dict(stages),
        "top_stop_reasons": [
            {"stage": stage, "reason": reason, "count": count}
            for (stage, reason), count in reasons.most_common(12)
        ],
        "metered_attempts": metered,
        "total_ai_calls": int(calls),
        "total_tokens": int(tokens),
        "estimated_neurons": round(neurons, 3),
        "avg_tokens_per_metered_attempt": round(tokens / metered, 1) if metered else None,
        "avg_neurons_per_metered_attempt": round(neurons / metered, 3) if metered else None,
        "note": "Rows are editorial attempts, so retries of one story can count separately.",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Post-Newsdesk attempts: {denominator}; approved={len(approved)}; watch={len(parked)}; rejected/held={len(rejected)}")
        print(f"Post-Newsdesk rejection rate: {report['post_newsdesk_rejection_rate_pct']}% (long-term target <10%)")
        print(f"Metered attempts: {metered}; tokens={int(tokens)}; estimated neurons={neurons:.3f}")
        print("Stages:", dict(stages))
        for item in report["top_stop_reasons"]:
            print(f"- {item['count']}x {item['stage']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
