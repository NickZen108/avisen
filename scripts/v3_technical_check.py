#!/usr/bin/env python3
"""Narrow machine-integrity checks for v3. No editorial taste gates."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "content" / "articles"
ALLOWED_ROLES = {"lead","top_story","important_followup","normal","magazine","section_only"}

def die(msg):
    raise SystemExit(f"V3 TECHNICAL CHECK FAILED: {msg}")

def main():
    checked = 0
    for p in sorted(ART.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            a = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            die(f"{p}: invalid JSON: {e}")
        if a.get("pipeline_version") != 3:
            continue
        checked += 1
        for key in ("story_id","slug","category","title","standfirst","body","ledger","status"):
            if key not in a:
                die(f"{p}: missing {key}")
        if a["status"] == "published":
            if not a.get("published_at"):
                die(f"{p}: published without published_at")
            image = a.get("image") or {}
            for key in ("src","alt","credit","license","source_url"):
                if not image.get(key):
                    die(f"{p}: published Hero missing {key}")
            if image.get("pending_image"):
                die(f"{p}: published Hero still pending")
            ledger = ROOT / str(a["ledger"])
            if not ledger.exists():
                die(f"{p}: ledger does not exist: {ledger}")
            role = a.get("frontpage_role") or "normal"
            if role not in ALLOWED_ROLES:
                die(f"{p}: bad frontpage_role {role}")
        if not isinstance(a.get("body"), list) or not a["body"]:
            die(f"{p}: body must be non-empty block list")
    fp = ROOT / "content" / "frontpage-v2.json"
    if fp.exists():
        f = json.loads(fp.read_text(encoding="utf-8"))
        lead = (f.get("lead") or {}).get("slug")
        if lead:
            ap = ART / f"{lead}.json"
            if not ap.exists():
                die(f"frontpage lead missing article {lead}")
            a = json.loads(ap.read_text(encoding="utf-8"))
            if a.get("status") != "published":
                die(f"frontpage lead is not published: {lead}")
    print(f"V3 technical check PASS ({checked} v3 articles)")
if __name__ == "__main__":
    main()
