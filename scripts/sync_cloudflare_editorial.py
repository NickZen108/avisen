#!/usr/bin/env python3
"""Import one approved Cloudflare editorial package into GitHub source of truth."""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"
SOURCES = ROOT / "sources"
APPROVALS = ROOT / "reports" / "editorial" / "approvals"
AUTO_IMG = ROOT / "docs" / "img" / "auto"
DEFAULT_URL = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/editorial/latest"
PUBLIC_SITE = "https://morgentidende.nicolaipetersen108.workers.dev"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_policy import claim_has_required_support
from scripts.normalize_categories import target_category

DOCUMENTARY_CONTEXTS = {"event", "place", "person", "object", "archive"}
ALLOWED_AI_PEOPLE_STYLES = {"pencil_hatching", "pencil_sketch", "line_art", "silhouette", "ink_drawing"}


def valid_documentary_image(image: dict) -> bool:
    if image.get("image_type") not in {"photo", "video_still"}:
        return False
    if str(image.get("context_type") or "") not in DOCUMENTARY_CONTEXTS:
        return False
    if not str(image.get("src") or "").startswith("https://"):
        return False
    if not str(image.get("source_url") or "").startswith("https://"):
        return False
    if not str(image.get("alt") or "").strip() or not str(image.get("credit") or "").strip():
        return False
    license_name = str(image.get("license") or "").strip()
    if not license_name or license_name.lower() in {"unknown", "ukendt", "tbd", "n/a"}:
        return False
    if image.get("pending_image") is True or image.get("ai_generated") is True:
        return False
    if image.get("discovery_only_source") is True and image.get("independent_license") is not True:
        return False
    context_type = str(image.get("context_type") or "").strip().lower()
    if context_type != "event" and not str(image.get("caption") or "").strip():
        return False
    try:
        host = (urlparse(str(image.get("source_url") or "")).hostname or "").removeprefix("www.").lower()
    except Exception:
        host = ""
    if image.get("image_type") == "video_still" and (host == "youtube.com" or host.endswith(".youtube.com") or host == "youtu.be"):
        if not str(image.get("rights_basis") or "").strip():
            return False
    return True


def valid_pending_illustration(image: dict) -> bool:
    if image.get("pending_image") is not True:
        return False
    if image.get("ai_generated") is not True:
        return False
    if image.get("image_type") != "illustration" or image.get("context_type") != "illustration":
        return False
    if image.get("photorealistic") is True:
        return False
    if not str(image.get("src") or "").strip():
        return False
    if not str(image.get("source_url") or "").startswith("https://"):
        return False
    if str(image.get("caption") or "").strip().lower() != "illustration":
        return False
    if not str(image.get("credit") or "").strip() or not str(image.get("license") or "").strip() or not str(image.get("alt") or "").strip():
        return False
    contains_people = image.get("contains_people")
    if not isinstance(contains_people, bool):
        return False
    if contains_people and str(image.get("people_style") or "").strip().lower() not in ALLOWED_AI_PEOPLE_STYLES:
        return False
    return True


def fail(message: str) -> None:
    raise ValueError(message)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "MorgentidendeEditorialSync/1.1"})
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
    ids = [sid for sid in coverage.get("editorial_source_ids", []) if sid in source_map and not source_map[sid].get("discovery_only")][:6]
    groups: list[str] = []
    for sid in ids:
        group = str(source_map[sid].get("source_group") or "").strip()
        if group and group not in groups:
            groups.append(group)
    coverage["editorial_source_ids"] = ids
    coverage["independent_source_groups"] = groups
    coverage["status"] = "pass" if len(groups) >= 1 else "limited"
    coverage["limitations"] = None if len(groups) >= 1 else "Ingen reel dokumentationskilde efter import"
    ledger["coverage_sweep"] = coverage


def normalize_incoming_category(article: dict, ledger: dict, approval: dict) -> None:
    old = str(article.get("category") or "").strip()
    new = target_category(article)
    if not new or new == old:
        return
    article["category"] = new
    assignment = ledger.get("assignment")
    if isinstance(assignment, dict) and str(assignment.get("category") or "").strip() == old:
        assignment["category"] = new
    approval["category_normalization"] = {
        "mode": "deterministic-taxonomy-boundary",
        "from": old,
        "to": new,
        "changed_fields": ["article.category", "ledger.assignment.category"],
    }


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
    if not isinstance(article.get("body"), list) or len(article["body"]) < 3:
        fail("artikeltekst mangler eller har færre end tre meningsfulde tekstblokke")
    image = article.get("image") or {}
    if image.get("placement") != "lead":
        fail("automatisk artikel mangler godkendt lead-hero")
    documentary_ok = valid_documentary_image(image)
    pending_ok = valid_pending_illustration(image)
    if not documentary_ok and not pending_ok:
        fail("hero skal være enten gyldigt dokumentarisk media eller en tydeligt mærket pending blyantsskitse")
    if not str(image.get("alt") or "").strip() or not str(image.get("credit") or "").strip():
        fail("hero mangler alt/kredit")
    if approval.get("status") != "pass" or approval.get("story_id") != article.get("story_id"):
        fail("final approval mangler eller matcher ikke")
    normalize_coverage(ledger)

    source_map = {s.get("id"): s for s in ledger.get("sources", []) if s.get("id")}
    source_ids = set(source_map)
    claims = ledger.get("claims") or []
    if len(claims) < 1:
        fail("ingen verificerede bærende claims")
    for claim in claims:
        ids = [x for x in claim.get("source_ids", []) if x in source_ids]
        if claim.get("status") != "verified" or not ids:
            fail(f"claim mangler verificeret dokumentation: {claim.get('id')}")
        if not claim_has_required_support(article, ledger, claim, source_map):
            fail(f"claim mangler tilstrækkelig dokumentation efter canonical evidence policy: {claim.get('id')}")
    if (ledger.get("fact_check") or {}).get("status") != "pass":
        fail("fact-check er ikke pass")
    media_url = str(media.get("url") or "")
    if documentary_ok:
        if media.get("kind") != "documentary" or media_url != str(image.get("src") or "") or not media_url.startswith("https://"):
            fail("dokumentarisk hero-pakke matcher ikke artikelbilledet")
    else:
        if media.get("kind") != "generated" or not media_url.startswith("https://"):
            fail("pending illustration mangler genereret media-pakke")
        if media.get("image_type") != "illustration":
            fail("pending illustration er fejlmærket i media-pakken")
    return article, ledger, approval, media


def save_hero(media: dict) -> Path:
    key = Path(str(media["key"])).name
    if not key.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        fail("ukendt hero-filtype")
    req = urllib.request.Request(media["url"], headers={"User-Agent": "MorgentidendeEditorialSync/1.1"})
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
    normalize_incoming_category(article, ledger, approval)
    slug = article["slug"]
    article_path = ARTICLES / f"{slug}.json"
    if article_path.exists():
        print(f"Allerede importeret: {slug}")
        return 0

    # Editorial destination is immutable from first GitHub ingestion onward.
    # An explicit destination from Newsdesk wins; otherwise deterministic subject
    # rules provide the transition while the runtime rolls out the same field.
    destination = str(article.get("editorial_destination") or "main")
    article["editorial_destination"] = destination
    ledger["editorial_destination"] = destination
    approval["editorial_destination"] = destination

    hero_path = save_hero(media)
    original_source_url = article["image"].get("source_url")
    article["image"]["src"] = f"{PUBLIC_SITE}/img/auto/{hero_path.name}"
    article["image"]["source_url"] = media.get("url") if media.get("kind") == "generated" else original_source_url
    article["automation_origin"] = "cloudflare-workers-ai"

    snapshot = json.loads(json.dumps(article))
    for key in ("status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "workflow_state"):
        snapshot.pop(key, None)
    approval["editorial_snapshot"] = snapshot

    ARTICLES.mkdir(parents=True, exist_ok=True); SOURCES.mkdir(parents=True, exist_ok=True); APPROVALS.mkdir(parents=True, exist_ok=True)
    article_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SOURCES / f"{slug}.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (APPROVALS / f"{slug}.json").write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported Cloudflare editorial package: {slug}; destination={destination}; hero={hero_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EDITORIAL SYNC FAIL: {exc}", file=sys.stderr)
        raise
