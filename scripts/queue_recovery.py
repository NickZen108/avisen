#!/usr/bin/env python3
"""Maintain deterministic retry/dead-letter state for incomplete pipeline items.

This file is a projection of editorial state. Merely rebuilding QA/health must never
count as a failed recovery attempt; otherwise frequently observed but perfectly
repairable stories can drift into dead-letter without any agent actually trying to
repair them.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / 'reports' / 'editorial' / 'pipeline-health.json'
OUT = ROOT / 'queue' / 'recovery.json'
ARTICLES = ROOT / 'content' / 'articles'


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def article_workflow_state(slug):
    path = ARTICLES / f'{slug}.json'
    article = load(path, {}) if path.exists() else {}
    return article.get('workflow_state') or {}


def main():
    now = datetime.now(timezone.utc)
    health = load(HEALTH, {'articles': []})
    old = load(OUT, {'items': {}})
    old_items = old.get('items') or {}
    items = {}

    for article in health.get('articles') or []:
        slug = str(article.get('slug') or '')
        if not slug or article.get('status') == 'published':
            continue
        reasons = [str(x) for x in article.get('reasons') or []]
        if not reasons:
            continue

        signature = ' | '.join(sorted(reasons))
        ws = article_workflow_state(slug)
        ws_signature = str(ws.get('recovery_reason_signature') or '')
        attempts = int(ws.get('recovery_attempts') or 0)

        # Attempts belong to actual recovery executions, recorded by Recovery Desk.
        # A changed diagnosis starts a new attempt series; passive queue rebuilds do
        # not increment anything.
        if ws_signature and ws_signature != signature:
            attempts = 0

        needs_attention = ws.get('state') == 'needs_attention' or attempts >= 3
        status = 'dead-letter' if needs_attention else 'retry'

        previous = old_items.get(slug) or {}
        if status == 'dead-letter':
            next_retry_at = None
        elif attempts > 0:
            delay = min(360, 15 * (2 ** max(0, attempts - 1)))
            next_retry_at = (now + timedelta(minutes=delay)).isoformat(timespec='seconds')
        elif previous.get('reason_signature') == signature and previous.get('next_retry_at'):
            next_retry_at = previous.get('next_retry_at')
        else:
            # New/never-attempted repair work is immediately eligible for Recovery Desk.
            next_retry_at = now.isoformat(timespec='seconds')

        items[slug] = {
            'status': status,
            'attempts': attempts,
            'resume_from': article.get('resume_from') or article.get('status'),
            'reasons': reasons,
            'reason_signature': signature,
            'last_seen_at': now.isoformat(timespec='seconds'),
            'last_recovery_attempt_at': ws.get('last_recovery_attempt_at'),
            'next_retry_at': next_retry_at,
        }

    payload = {
        'schema_version': 2,
        'generated_at': now.isoformat(timespec='seconds'),
        'retry_count': sum(1 for x in items.values() if x['status'] == 'retry'),
        'dead_letter_count': sum(1 for x in items.values() if x['status'] == 'dead-letter'),
        'items': items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Recovery queue: {payload['retry_count']} retry, {payload['dead_letter_count']} dead-letter")


if __name__ == '__main__':
    main()
