#!/usr/bin/env python3
"""Import one approved Cloudflare editorial package into GitHub source of truth.

Cloudflare may research, draft and approve. GitHub remains canonical: this script
validates the package, writes structured source files, stores the generated hero
locally, and lets the existing Pipeline v2 gates/release/build chain decide
whether it can become public.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
SOURCES = ROOT / "sources"
APPROVALS = ROOT / "reports" / "editorial" / "approvals"
AUTO_IMG = ROOT / "docs" / "img" / "auto"
FRONTPAGE = ROOT / "content" / "frontpage.json"
DEFAULT_URL = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/editorial/latest"


def fail(message: str) -> None:
    raise ValueError(message)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeEditorialSync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200:
            fail(f"Cloudflare editorial endpoint HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def load_payload(path: str | None, url: str) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return fetch_json(url)


def normalize_coverage(ledger: dict) -> None:
    source_map = {s.get("id"): s for s in ledger.get("sources", []) if s.get("id")}
    coverage = ledger.get("coverage_sweep") or {}
    ids = [sid for sid in coverage.get("editorial_source_ids", []) if sid in source_map][:6]
    groups: list[str] = []
    for sid in ids:
        group = str(source_map[sid].get("source_group") or "").strip()
        if group and group not in groups:
            groups.append(group)
    coverage["editorial_source_ids"] = ids
    coverage["independent_source_groups"] = groups
    coverage["status"] = "pass" if len(groups) >= 3 else "limited"
    coverage["limitations"] = None if len(groups) >= 3 else "Færre end tre uafhængige kildegrupper efter import"
    ledger["coverage_sweep"] = coverage


def validate(payload: dict) -> tuple[dict, dict, dict, dict]:
    if payload.get("status") != "approved":
        fail(f"pakken er ikke approved (status={payload.get('status')!r})")
    if payload.get("runtime") != "cloudflare-workers-ai":
        fail("ukendt editorial runtime")
    article = payload.get("article") or {}
    ledger = payload.get("ledger") or {}
    approval = payload.get("approval") or {}
    media = payload.get("media") or {}
    slug = str(payload.get("slug") or article.get("slug") or "").strip()
    if not slug or article.get("slug") != slug or ledger.get("article_slug") != slug or approval.get("article_slug") != slug:
        fail("slug mismatch i editorial package")
    if article.get("pipeline_version") != 2 or article.get("status") != "ready" or article.get("release_requested") is not True:
        fail("artikel er ikke Pipeline v2 ready+release_requested")
    if not isinstance(article.get("body"), list) or len(article["body"]) < 5:
        fail("artikeltekst mangler")
    image = article.get("image") or {}
    if image.get("placement") != "lead" or image.get("image_type") != "illustration":
        fail("automatisk artikel mangler godkendt lead-illustration")
    if not str(image.get("alt") or "").strip() or not str(image.get("credit") or "").strip():
        fail("hero mangler alt/kredit")
    if approval.get("status") != "pass" or approval.get("story_id") != article.get("story_id"):
        fail("final approval mangler eller matcher ikke")
    for gate in ("language", "ethics", "image", "seo", "final_editor"):
        if (approval.get("gates") or {}).get(gate) != "pass":
            fail(f"approval gate {gate} er ikke pass")
    normalize_coverage(ledger)
    coverage = ledger.get("coverage_sweep") or {}
    if coverage.get("status") != "pass" or len(set(coverage.get("independent_source_groups") or [])) < 3:
        fail("mindre end tre uafhængige redaktionelle kildegrupper")
    source_ids = {s.get("id") for s in ledger.get("sources", [])}
    claims = ledger.get("claims") or []
    if len(claims) < 3:
        fail("for få verificerede claims")
    for claim in claims:
        ids = [x for x in claim.get("source_ids", []) if x in source_ids]
        if claim.get("status") != "verified" or len(set(ids)) < 2:
            fail(f"claim uden to kilder: {claim.get('id')}")
    if (ledger.get("fact_check") or {}).get("status") != "pass":
        fail("fact-check er ikke pass")
    if (ledger.get("desk_recheck") or {}).get("status") not in {"publish", "update"}:
        fail("desk recheck er ikke publish/update")
    media_url = str(media.get("url") or "")
    if not media_url.startswith("https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/media/"):
        fail("generated hero media URL mangler")
    return article, ledger, approval, media


def save_hero(media: dict) -> Path:
    key = Path(str(media["key"])).name
    if not key.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        fail("ukendt hero-filtype")
    req = urllib.request.Request(media["url"], headers={"User-Agent": "MorgentidendeEditorialSync/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read(15_000_000)
        ctype = response.headers.get("content-type", "").lower()
    if len(data) < 1000 or not ctype.startswith("image/"):
        fail(f"hero er ikke plausibelt billede ({ctype}, {len(data)} bytes)")

    AUTO_IMG.mkdir(parents=True, exist_ok=True)
    target = AUTO_IMG / (Path(key).stem + ".jpg")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            w, h = im.size
            if w < 512 or h < 512:
                fail(f"hero for lille: {w}x{h}")
            target_ratio = 16 / 9
            ratio = w / h
            if ratio > target_ratio:
                nw = round(h * target_ratio); left = (w - nw) // 2
                im = im.crop((left, 0, left + nw, h))
            elif ratio < target_ratio:
                nh = round(w / target_ratio); top = (h - nh) // 2
                im = im.crop((0, top, w, top + nh))
            if im.width > 1600:
                im = im.resize((1600, 900), Image.Resampling.LANCZOS)
            im.save(target, "JPEG", quality=88, optimize=True, progressive=True)
    except ImportError as exc:
        fail(f"Pillow mangler til 16:9 hero-normalisering: {exc}")
    return target


def update_frontpage(slug: str) -> None:
    state = json.loads(FRONTPAGE.read_text(encoding="utf-8"))
    state["ticker"] = {"slug": slug}
    for key, limit in (("rail", 5), ("narrow", 8)):
        items = [x for x in state.get(key, []) if x.get("slug") != slug]
        items.insert(0, {"slug": slug})
        state[key] = items[:limit]
    FRONTPAGE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON package already fetched from Cloudflare")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    payload = load_payload(args.input, args.url)
    if payload.get("status") != "approved":
        print(f"Cloudflare editorial: {payload.get('status', 'none')} – {payload.get('reason', 'ingen godkendt artikel')}")
        return 0

    article, ledger, approval, media = validate(payload)
    slug = article["slug"]
    article_path = ARTICLES / f"{slug}.json"
    if article_path.exists():
        print(f"Allerede importeret: {slug}")
        return 0

    hero_path = save_hero(media)
    article["image"]["src"] = f"/img/auto/{hero_path.name}"
    article["image"]["source_url"] = None
    article["automation_origin"] = "cloudflare-workers-ai"

    # Approval snapshot must match canonical article after all editorial mutations.
    snapshot = json.loads(json.dumps(article))
    for key in ("status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed"):
        snapshot.pop(key, None)
    approval["editorial_snapshot"] = snapshot

    ARTICLES.mkdir(parents=True, exist_ok=True); SOURCES.mkdir(parents=True, exist_ok=True); APPROVALS.mkdir(parents=True, exist_ok=True)
    article_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SOURCES / f"{slug}.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (APPROVALS / f"{slug}.json").write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_frontpage(slug)
    print(f"Imported Cloudflare editorial package: {slug}; hero={hero_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EDITORIAL SYNC FAIL: {exc}", file=sys.stderr)
        raise
