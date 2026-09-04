#!/usr/bin/env python3
"""Deterministic editorial sanity checks for ready/scheduled/published articles.

Catches catastrophic fallback text and clearly non-Danish editorial output that a
term blacklist cannot reliably detect. Intended as a narrow hard gate, not a
style grader.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content" / "articles"

PLACEHOLDER_PATTERNS = (
    "ugyldigt struktureret svar",
    "invalid structured response",
    "invalid structured output",
    "structured output error",
    "malformed response",
    "model returned invalid",
)

ENGLISH_MARKERS = {
    "according", "administration", "arcade", "backlash", "breaking", "campaign",
    "concerns", "diversity", "election", "entertainment", "equity", "games",
    "government", "house", "ignite", "inclusion", "leader", "officials", "policy",
    "security", "statement", "support", "talks", "update", "white", "with", "from",
    "after", "amid", "over", "rising", "focus", "safety", "scrutiny", "rollout",
}
DANISH_MARKERS = {
    "af", "at", "blev", "bliver", "den", "der", "det", "efter", "en", "er", "et",
    "for", "fra", "har", "ikke", "med", "og", "om", "på", "som", "til", "under",
    "vil", "skal", "siger", "mener", "ifølge", "ifolge",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÆØÅæøå]+", str(text or "").lower())


def editorial_fields(article: dict):
    yield "title", article.get("title") or ""
    yield "standfirst", article.get("standfirst") or ""
    seo = article.get("seo") or {}
    if isinstance(seo, dict):
        yield "seo.title", seo.get("title") or ""
        yield "seo.description", seo.get("description") or ""
    for i, block in enumerate(article.get("body") or []):
        if isinstance(block, dict) and block.get("type") in {"p", "h2", "h3", "blockquote"}:
            yield f"body[{i}]", block.get("text") or ""


def changed_article_paths() -> list[Path]:
    names: set[str] = set()
    for cmd in (["git", "diff", "--name-only", "HEAD^..HEAD"], ["git", "diff", "--name-only"], ["git", "diff", "--cached", "--name-only"]):
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if p.returncode == 0:
            names.update(x.strip() for x in p.stdout.splitlines() if x.strip())
    out = []
    for name in sorted(names):
        if name.startswith("content/articles/") and name.endswith(".json"):
            path = ROOT / name
            if path.exists():
                out.append(path)
    return out


def clearly_english(text: str) -> bool:
    toks = tokens(text)
    if len(toks) < 6:
        return False
    en = sum(t in ENGLISH_MARKERS for t in toks)
    da = sum(t in DANISH_MARKERS for t in toks)
    return en >= 3 and en >= da + 2 and en / max(1, len(toks)) >= 0.28


def validate(path: Path, article: dict) -> list[str]:
    faults = []
    if article.get("status") not in {"ready", "scheduled", "published"}:
        return faults
    for field, value in editorial_fields(article):
        text = str(value or "").strip()
        low = text.lower()
        for marker in PLACEHOLDER_PATTERNS:
            if marker in low:
                faults.append(f"{path.name}: fallback/placeholder i {field}: {marker!r}")
                break
        if clearly_english(text):
            faults.append(f"{path.name}: {field} ser overvejende engelsk ud")
    body_text = " ".join(str((b or {}).get("text") or "") for b in article.get("body") or [] if isinstance(b, dict)).strip()
    if len(body_text) < 80:
        faults.append(f"{path.name}: brødtekst er mistænkeligt kort ({len(body_text)} tegn)")
    return faults


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed-only", action="store_true")
    args = ap.parse_args()
    paths = changed_article_paths() if args.changed_only else sorted(ARTICLES.glob("*.json"))
    if args.changed_only and not paths:
        print("EDITORIAL SANITY: no changed articles")
        return 0
    faults = []
    for path in paths:
        if path.name.startswith("_"):
            continue
        try:
            article = load(path)
        except Exception as exc:
            faults.append(f"{path.name}: kan ikke læses: {exc}")
            continue
        faults.extend(validate(path, article))
    if faults:
        print("EDITORIAL SANITY: FAIL")
        for fault in faults:
            print("-", fault)
        return 1
    print("EDITORIAL SANITY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
