#!/usr/bin/env python3
"""Deterministic quality gates for Morgentidende."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from evidence_policy import claim_has_required_support as evidence_claim_has_required_support

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def err(message: str) -> None:
    ERRORS.append(message)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"JSON-fejl {path.relative_to(ROOT)}: {exc}")
        return None


def parse_iso(value: str, label: str):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timezone mangler")
        return dt
    except Exception as exc:
        err(f"ugyldigt timestamp {label}: {value!r} ({exc})")
        return None


def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    return evidence_claim_has_required_support(article, ledger, claim, sources)


def validate_article(path: Path, categories: set[str], prebuild: bool) -> None:
    article = read_json(path)
    if article is None or path.name.startswith("_"):
        return
    status = article.get("status")
    valid_statuses = {"draft", "researching", "checking", "editing", "ready", "scheduled", "published"}
    if status not in valid_statuses:
        err(f"{path.name}: ugyldig status")
        return

    if status in {"draft", "researching", "checking", "editing"}:
        return

    required = ["status", "story_id", "slug", "category", "weight", "title", "standfirst", "byline", "ledger", "claim_ids", "seo", "body"]
    for field in required:
        if field not in article:
            err(f"{path.name}: mangler felt {field}")
    if article.get("category") not in categories:
        err(f"{path.name}: ugyldig kategori {article.get('category')!r}")
    if article.get("weight") not in {"A", "B", "C", "D"}:
        err(f"{path.name}: ugyldig weight")
    slug = article.get("slug", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+", slug):
        err(f"{path.name}: slug skal være YYYY-MM-DD-lowercase-slug")
    if not str(article.get("title", "")).strip() or len(str(article.get("title", ""))) > 180:
        err(f"{path.name}: ugyldig title")
    if not str(article.get("standfirst", "")).strip():
        err(f"{path.name}: standfirst mangler")
    body = article.get("body") or []
    if not body:
        err(f"{path.name}: body er tom")
    allowed_blocks = {"p", "h2", "h3", "ul", "ol", "blockquote", "figure"}
    for i, block in enumerate(body):
        if not isinstance(block, dict) or block.get("type") not in allowed_blocks:
            err(f"{path.name}: body[{i}] har ugyldig type")
            continue
        if block.get("type") == "figure":
            src = str(block.get("src", "")).strip()
            alt = str(block.get("alt", "")).strip()
            if not src:
                err(f"{path.name}: body[{i}] figure mangler src")
            if not alt:
                err(f"{path.name}: body[{i}] figure mangler alt")
            if src and not (src.startswith("../img/") or re.match(r"^https?://", src)):
                err(f"{path.name}: body[{i}] figure src skal være ../img/... eller http(s)-URL")
            if src.startswith("../img/"):
                local = (ROOT / "docs" / "artikler" / src).resolve()
                docs_root = (ROOT / "docs").resolve()
                if docs_root not in local.parents or not local.exists():
                    err(f"{path.name}: body[{i}] lokal figure findes ikke: {src}")
            if "wide" in block and not isinstance(block.get("wide"), bool):
                err(f"{path.name}: body[{i}] figure wide skal være bool")
    seo = article.get("seo") or {}
    if not seo.get("title") or not seo.get("description"):
        print(f"QUALITY NOTE {path.name}: SEO title/description mangler; SEO fallback må reparere det")
    image = article.get("image")
    if image is not None:
        for field in ["src", "alt", "credit", "license", "source_url", "image_type"]:
            if not str(image.get(field, "")).strip():
                err(f"{path.name}: image mangler udfyldt {field}")
        if image.get("image_type") not in {"photo", "video_still", "illustration", "graphic"}:
            err(f"{path.name}: ugyldig image_type")
        if image.get("image_type") == "illustration" and article.get("automation_origin") == "cloudflare-workers-ai":
            if image.get("pending_image") is not True or image.get("ai_generated") is not True:
                err(f"{path.name}: autonom nyhedsillustration skal være pending og AI-genereret")
            if image.get("context_type") != "illustration":
                err(f"{path.name}: autonom nyhedsillustration skal have context_type=illustration")
            if str(image.get("caption") or "").strip().lower() != "illustration":
                err(f"{path.name}: autonom nyhedsillustration skal have synlig caption Illustration")
        if image.get("image_type") in {"photo", "video_still"} and image.get("pending_image") is True:
            err(f"{path.name}: dokumentarisk hero må ikke have pending_image=true")
        if image.get("placement", "lead") not in {"lead", "inline", "none"}:
            err(f"{path.name}: image placement skal være lead, inline eller none")
        for field in ["src", "source_url"]:
            value = str(image.get(field, "")).strip()
            if value and not re.match(r"^https?://", value):
                err(f"{path.name}: image {field} skal være http(s)-URL")
    ledger_path = ROOT / str(article.get("ledger", ""))
    if not ledger_path.exists():
        err(f"{path.name}: ledger findes ikke: {article.get('ledger')}")
        return
    ledger = read_json(ledger_path)
    if ledger is None:
        return
    sources = {s.get("id"): s for s in ledger.get("sources", []) if s.get("id")}
    claims = {c.get("id"): c for c in ledger.get("claims", []) if c.get("id")}
    for claim_id in article.get("claim_ids", []):
        claim = claims.get(claim_id)
        if not claim:
            err(f"{path.name}: claim {claim_id} findes ikke i ledger")
            continue
        if article.get("status") in {"ready", "scheduled", "published"} and claim.get("status") != "verified":
            err(f"{path.name}: klar/publiceret claim {claim_id} er ikke verified")
        if article.get("status") in {"ready", "scheduled", "published"}:
            for sid in claim.get("source_ids", []):
                src = sources.get(sid)
                if not src:
                    err(f"{path.name}: claim {claim_id} peger på ukendt source_id {sid}")
                elif not str(src.get("source_group", "")).strip():
                    err(f"{path.name}: source {sid} mangler source_group")
        if article.get("status") in {"ready", "scheduled", "published"} and not claim_has_required_support(article, ledger, claim, sources):
            err(f"{path.name}: claim {claim_id} mangler gyldig autoritativ eller anden tilladt støtte")
    if article.get("category") == "Kommentar" and not article.get("related_news_slug"):
        err(f"{path.name}: Kommentar mangler related_news_slug")
    if article.get("status") == "scheduled":
        scheduled_for = article.get("scheduled_for")
        if not scheduled_for:
            err(f"{path.name}: scheduled_for mangler")
        else:
            parse_iso(scheduled_for, f"{path.name}.scheduled_for")
        if article.get("published_at"):
            err(f"{path.name}: scheduled artikel må ikke have published_at")
        if (ledger.get("fact_check") or {}).get("status") != "pass":
            err(f"{path.name}: fact_check.status skal være pass før scheduling")
    if article.get("status") == "published":
        if (ledger.get("fact_check") or {}).get("status") != "pass":
            err(f"{path.name}: fact_check.status skal være pass før publicering")
        published = article.get("published_at")
        if not published:
            err(f"{path.name}: published_at mangler")
        else:
            dt = parse_iso(published, f"{path.name}.published_at")
            if dt and dt.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
                err(f"{path.name}: published_at ligger i fremtiden")
        if article.get("updated_at"):
            parse_iso(article["updated_at"], f"{path.name}.updated_at")
        if not prebuild:
            output = ROOT / "docs" / "artikler" / f"{slug}.html"
            if not output.exists():
                err(f"{path.name}: genereret HTML mangler")
            else:
                text = output.read_text(encoding="utf-8")
                if not text.startswith("<!-- GENERATED FROM content/articles/"):
                    err(f"{path.name}: HTML mangler generated-marker")
                if len(re.findall(r"<h1(?:\s|>)", text, flags=re.I)) != 1:
                    err(f"{path.name}: genereret HTML skal have præcis én H1")


def validate_no_new_handwritten_html(prebuild: bool) -> None:
    legacy = set()
    legacy_file = ROOT / "config" / "legacy-articles.txt"
    if legacy_file.exists():
        legacy = {x.strip() for x in legacy_file.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")}
    structured = set()
    for path in (ROOT / "content" / "articles").glob("*.json"):
        if path.name.startswith("_"):
            continue
        data = read_json(path)
        if data and data.get("slug"):
            structured.add(f"{data['slug']}.html")
    for html_path in (ROOT / "docs" / "artikler").glob("*.html"):
        if html_path.name not in legacy and html_path.name not in structured:
            err(f"ny håndskrevet HTML er forbudt: docs/artikler/{html_path.name}")
        if html_path.name in structured and not prebuild:
            text = html_path.read_text(encoding="utf-8")
            if not text.startswith("<!-- GENERATED FROM content/articles/"):
                err(f"struktureret artikel er ikke generator-output: {html_path.name}")


def validate_public_text() -> None:
    banned = ["intern note", "ingen frit foto", "ikke avisens"]
    for path in [ROOT / "docs" / "index.html", *sorted((ROOT / "docs" / "artikler").glob("*.html"))]:
        if not path.exists():
            continue
        low = path.read_text(encoding="utf-8").lower()
        for phrase in banned:
            if phrase in low:
                err(f"offentlig intern formulering i {path.relative_to(ROOT)}: {phrase}")


def validate_frontpage() -> None:
    state = read_json(ROOT / "content" / "frontpage.json")
    if state is None:
        return
    for field in ["date", "ticker", "lead", "rail", "stack", "narrow", "lead_rationale"]:
        if field not in state:
            err(f"frontpage mangler {field}")
    slugs = []
    for item in [state.get("ticker", {}), state.get("lead", {}), *state.get("rail", []), *state.get("stack", []), *state.get("narrow", [])]:
        if item.get("slug"):
            slugs.append(item["slug"])
    known = {p.stem for p in (ROOT / "docs" / "artikler").glob("*.html")}
    for article_path in (ROOT / "content" / "articles").glob("*.json"):
        if article_path.name.startswith("_"):
            continue
        data = read_json(article_path)
        if data and data.get("status") == "published" and data.get("slug"):
            known.add(data["slug"])
    for slug in slugs:
        if slug not in known:
            err(f"frontpage peger på ukendt slug: {slug}")


def changed_article_paths() -> list[Path]:
    names: set[str] = set()
    commands = [
        ["git", "diff", "--name-only", "HEAD^..HEAD"],
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        except OSError:
            continue
        if result.returncode == 0:
            names.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    paths = []
    for name in sorted(names):
        if name.startswith("content/articles/") and name.endswith(".json"):
            path = ROOT / name
            if path.exists() and not path.name.startswith("_"):
                paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prebuild", action="store_true")
    parser.add_argument("--changed-only", action="store_true", help="prebuild: validate only changed article JSON files when detectable")
    args = parser.parse_args()
    categories = {x.strip() for x in (ROOT / "config" / "categories.txt").read_text(encoding="utf-8").splitlines() if x.strip()}

    article_paths = sorted((ROOT / "content" / "articles").glob("*.json"))
    if args.prebuild and args.changed_only:
        changed = changed_article_paths()
        if changed:
            article_paths = changed
            print(f"QUALITY: changed-only prebuild ({len(article_paths)} article(s))")
        else:
            print("QUALITY: no changed article detected; falling back to full article validation")

    for path in article_paths:
        validate_article(path, categories, args.prebuild)

    # Prebuild stays focused on source-of-truth article/frontpage state. Expensive
    # archive/output scans belong after the canonical build, where they can actually
    # validate generated HTML and the whole public surface once.
    validate_frontpage()
    if not args.prebuild:
        validate_no_new_handwritten_html(False)
        validate_public_text()
        if not (ROOT / "docs" / "news-sitemap.xml").exists():
            err("docs/news-sitemap.xml mangler efter build")

    if ERRORS:
        print("QUALITY GATE: FAIL")
        for e in ERRORS:
            print(f"- {e}")
        return 1
    print("QUALITY GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
