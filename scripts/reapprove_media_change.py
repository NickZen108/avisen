#!/usr/bin/env python3
"""Targeted re-approval for image-only changes to a published Pipeline V2 article.

This does NOT weaken the immutable final-approval gate. It proves that the only
editorial delta since the previous approval is the article.image object, validates
the replacement's basic provenance metadata, and then writes a new approval snapshot
with an audit record of the previous approval.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = {
    "status", "published_at", "updated_at", "scheduled_for",
    "released_from_schedule_at", "release_requested", "publication",
    "manual_review_completed", "workflow_state",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot(article: dict) -> dict:
    out = copy.deepcopy(article)
    for key in PUB:
        out.pop(key, None)
    return out


def digest(obj: dict) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def without_image(obj: dict) -> dict:
    out = copy.deepcopy(obj)
    out.pop("image", None)
    return out


def validate_image(image: dict):
    required = ("src", "alt", "credit", "license", "source_url", "image_type", "placement")
    missing = [key for key in required if not str(image.get(key) or "").strip()]
    if missing:
        raise SystemExit("Media re-approval blocked: image metadata missing: " + ", ".join(missing))
    if image.get("image_type") not in {"photo", "video_still", "document", "graphic", "illustration"}:
        raise SystemExit(f"Media re-approval blocked: unsupported image_type {image.get('image_type')!r}")
    if not str(image.get("src")).startswith(("https://", "/")):
        raise SystemExit("Media re-approval blocked: image src must be https:// or site-relative")
    if not str(image.get("source_url")).startswith("https://"):
        raise SystemExit("Media re-approval blocked: source_url must be https://")
    context_type = str(image.get("context_type") or "context").strip().lower()
    if context_type != "event" and not str(image.get("caption") or "").strip():
        raise SystemExit("Media re-approval blocked: non-event photo requires visible archive/context caption")


def reapprove(slug: str, checked_at: str | None = None, dry_run: bool = False):
    article_path = ROOT / "content" / "articles" / f"{slug}.json"
    approval_path = ROOT / "reports" / "editorial" / "approvals" / f"{slug}.json"
    if not article_path.exists() or not approval_path.exists():
        raise SystemExit("Media re-approval blocked: article or approval missing")

    article = load(article_path)
    approval = load(approval_path)
    if article.get("pipeline_version") != 2:
        raise SystemExit("Media re-approval blocked: only Pipeline V2 articles are supported")
    if article.get("status") != "published":
        raise SystemExit("Media re-approval blocked: targeted media replacement is for published articles")
    if approval.get("status") != "pass" or approval.get("article_slug") != slug:
        raise SystemExit("Media re-approval blocked: previous valid final approval missing")

    current = snapshot(article)
    previous = approval.get("editorial_snapshot")
    if not isinstance(previous, dict):
        raise SystemExit("Media re-approval blocked: previous editorial snapshot missing")
    if without_image(current) != without_image(previous):
        raise SystemExit(
            "Media re-approval blocked: changes beyond image metadata detected; "
            "use the correction/editorial re-approval workflow instead"
        )
    if current.get("image") == previous.get("image"):
        raise SystemExit("Media re-approval blocked: image has not changed")

    validate_image(current.get("image") or {})
    old_hash = digest(previous)
    new_hash = digest(current)
    when = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    new_approval = copy.deepcopy(approval)
    new_approval["checked_at"] = when
    new_approval["gates"] = {
        **(new_approval.get("gates") or {}),
        "image": "pass",
        "final_editor": "pass",
    }
    new_approval["media_reapproval"] = {
        "mode": "targeted-image-only",
        "checked_at": when,
        "previous_snapshot_sha256": old_hash,
        "new_snapshot_sha256": new_hash,
        "changed_fields": ["image"],
        "checks": [
            "only image differs from previous final approval",
            "replacement image provenance metadata complete",
            "article text, claims, SEO, category and byline unchanged",
        ],
    }
    new_approval["editorial_snapshot"] = current

    if not dry_run:
        dump(approval_path, new_approval)
    print(json.dumps({
        "ok": True,
        "slug": slug,
        "mode": "targeted-image-only",
        "previous_snapshot_sha256": old_hash,
        "new_snapshot_sha256": new_hash,
        "written": not dry_run,
    }, ensure_ascii=False))
    return new_approval


def self_test():
    good = {
        "src": "https://example.test/image.jpg",
        "alt": "Dokumentarisk foto",
        "credit": "Example",
        "license": "CC BY 4.0",
        "source_url": "https://example.test/source",
        "image_type": "photo",
        "placement": "lead",
        "context_type": "event",
    }
    validate_image(good)
    try:
        validate_image({**good, "source_url": None})
    except SystemExit:
        pass
    else:
        raise AssertionError("missing source_url should fail")
    base = {"title": "A", "image": {"src": "old"}, "status": "published"}
    changed = {"title": "A", "image": {"src": "new"}, "status": "published"}
    assert without_image(snapshot(base)) == without_image(snapshot(changed))
    changed["title"] = "B"
    assert without_image(snapshot(base)) != without_image(snapshot(changed))
    print("media_reapproval self-test: PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--checked-at")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.slug:
        ap.error("--slug is required unless --self-test is used")
    reapprove(args.slug, args.checked_at, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
