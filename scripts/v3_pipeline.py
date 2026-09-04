#!/usr/bin/env python3
"""Morgentidende Pipeline v3: one simple, auditable, repair-first newsroom loop.

Flow: Scan inventory -> Desk -> Evidence -> Journalist -> Danish editor ->
Media -> Chief Editor (+ pixels) -> Publish.

Editorial judgment lives in models; deterministic code only handles transport,
source fetching, rights metadata, schemas, retries, and publication integrity.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "editorial_v3.json").read_text(encoding="utf-8"))
QUEUE = ROOT / "queue" / "candidates.json"
STATE = ROOT / "state" / "newsroom-v3.json"
ART_DIR = ROOT / "content" / "articles"
SRC_DIR = ROOT / "sources"
REPORT_ROOT = ROOT / "reports" / "v3-runs"

WORKER_URL = os.environ.get("V3_WORKER_URL", "").rstrip("/")
WORKER_TOKEN = os.environ.get("V3_WORKER_TOKEN", "")
BACKEND_URL = os.environ.get("V3_PRIVATE_BACKEND_URL", "").rstrip("/")
OIDC_TOKEN = os.environ.get("GITHUB_OIDC_TOKEN", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID") or f"local-{int(time.time())}"

USER_AGENT = "MorgentidendeV3/1.0 (+editorial research)"
ALLOWED_LICENSE_HINTS = ("public domain", "cc0", "cc by", "cc-by", "creative commons attribution")

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script","style","noscript","svg"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript","svg"} and self.skip:
            self.skip -= 1
        if tag in {"p","h1","h2","h3","li","article","section"}:
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip:
            s = " ".join(data.split())
            if s:
                self.parts.append(s + " ")

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def dump_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def slugify(value):
    s = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:90] or "historie"

def strip_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(value or "")))).strip()

def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)

def extract_json(text):
    text = str(text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    first, last = text.find("{"), text.rfind("}")
    if first >= 0 and last > first:
        text = text[first:last+1]
    return json.loads(text)

def backend(action, **kwargs):
    if not BACKEND_URL or not OIDC_TOKEN:
        return None
    try:
        r = requests.post(
            BACKEND_URL,
            headers={"authorization": f"Bearer {OIDC_TOKEN}", "content-type": "application/json"},
            json={"action": action, **kwargs},
            timeout=25,
        )
        if not r.ok:
            print(f"private backend {action}: HTTP {r.status_code}: {r.text[:300]}", file=sys.stderr)
            return None
        return r.json()
    except Exception as e:
        print(f"private backend {action}: {e}", file=sys.stderr)
        return None

def estimate_cost(model, usage):
    prices = CONFIG["model_prices_usd_per_million_tokens"].get(model, {})
    inp = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or usage.get("cached_tokens") or 0)
    regular = max(0, inp - cached)
    usd = (
        regular * float(prices.get("input", 0))
        + cached * float(prices.get("cached_input", prices.get("input", 0)))
        + out * float(prices.get("output", 0))
    ) / 1_000_000
    return inp, out, cached, usd, usd * float(CONFIG["cost"]["fx_usd_dkk"])

def call_ai(stage, model, instructions, prompt, *, story_id=None, inbox_id=None,
            max_output_tokens=800, images=None, web_search=False, reasoning="low"):
    if not WORKER_URL or not WORKER_TOKEN:
        raise RuntimeError("V3 Worker URL/token missing")
    payload = {
        "stage": stage,
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "images": images or [],
        "web_search": bool(web_search),
        "reasoning": reasoning,
    }
    started = time.time()
    error = None
    text = ""
    usage = {}
    request_id = None
    try:
        r = requests.post(
            WORKER_URL + "/run",
            headers={"authorization": f"Bearer {WORKER_TOKEN}", "content-type": "application/json"},
            json=payload,
            timeout=240,
        )
        request_id = r.headers.get("cf-ray")
        data = r.json()
        if not r.ok or not data.get("ok"):
            raise RuntimeError(f"AI {stage} HTTP {r.status_code}: {data}")
        text = data.get("text") or ""
        usage = data.get("usage") or {}
        if not text.strip():
            raise RuntimeError(f"AI {stage} returned empty text")
    except Exception as e:
        error = str(e)
    elapsed_ms = int((time.time() - started) * 1000)
    inp, out, cached, usd, dkk = estimate_cost(model, usage)
    backend("log_ai", row={
        "run_id": RUN_ID,
        "story_id": story_id,
        "inbox_id": inbox_id,
        "stage": stage,
        "provider": "cloudflare-ai-gateway",
        "model": model,
        "request_id": request_id,
        "attempt": 1,
        "status": "error" if error else "success",
        "input_tokens": inp,
        "output_tokens": out,
        "cached_input_tokens": cached,
        "estimated_cost_usd": round(usd, 8),
        "estimated_cost_dkk": round(dkk, 6),
        "latency_ms": elapsed_ms,
        "prompt_text": prompt,
        "response_text": text or None,
        "error_message": error,
        "metadata": {"reasoning": reasoning, "web_search": web_search, "image_count": len(images or [])},
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(timespec="seconds"),
    })
    if error:
        raise RuntimeError(error)
    return text, {"input_tokens": inp, "output_tokens": out, "cached_input_tokens": cached, "usd": usd, "dkk": dkk, "latency_ms": elapsed_ms}

def call_json(stage, model, instructions, obj, *, story_id=None, inbox_id=None,
              max_output_tokens=800, images=None, web_search=False, reasoning="low"):
    prompt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    last = None
    for attempt in range(2):
        extra = "" if attempt == 0 else "\nVIGTIGT: Forrige svar kunne ikke parses. Returnér KUN ét gyldigt JSON-objekt uden markdown."
        text, usage = call_ai(
            stage if attempt == 0 else stage + "_format_retry",
            model,
            instructions + extra,
            prompt,
            story_id=story_id,
            inbox_id=inbox_id,
            max_output_tokens=max_output_tokens,
            images=images,
            web_search=web_search,
            reasoning=reasoning,
        )
        try:
            return extract_json(text), usage
        except Exception as e:
            last = e
    raise RuntimeError(f"{stage}: invalid structured output after retry: {last}")

def already_used_urls():
    urls = set()
    for p in SRC_DIR.glob("*.json"):
        d = load_json(p, {}) or {}
        for s in d.get("sources", []):
            if s.get("url"):
                urls.add(str(s["url"]).split("#")[0])
    return urls

def words(s):
    return {x for x in re.findall(r"[a-zA-ZæøåÆØÅ0-9]{4,}", str(s).casefold())}

def candidate_inventory(state):
    q = load_json(QUEUE, {}) or {}
    signals = list(q.get("signals") or [])
    used = already_used_urls()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=42)
    clean = []
    seen = set()
    for s in signals:
        url = str(s.get("url") or "").split("#")[0]
        headline = strip_html(s.get("headline"))
        if not url or not headline or url in used:
            continue
        published = parse_time(s.get("published_at"))
        if published != datetime.min.replace(tzinfo=timezone.utc) and published < cutoff:
            continue
        key = (headline.casefold(), url)
        if key in seen:
            continue
        seen.add(key)
        clean.append({
            "source": s.get("source"),
            "source_class": s.get("source_class"),
            "region": s.get("region"),
            "source_priority": int(s.get("source_priority") or 0),
            "discovery_only": bool(s.get("discovery_only")),
            "headline": headline[:220],
            "description": strip_html(s.get("description"))[:420],
            "url": url,
            "published_at": s.get("published_at"),
        })
    clean.sort(key=lambda s: (parse_time(s.get("published_at")), s.get("source_priority", 0)), reverse=True)
    per_source = {}
    normal, perspective = [], []
    for s in clean:
        src = str(s.get("source"))
        if per_source.get(src, 0) >= 4:
            continue
        per_source[src] = per_source.get(src, 0) + 1
        (perspective if s.get("discovery_only") else normal).append(s)
    maxn = int(CONFIG["limits"]["desk_candidates"])
    maxp = int(CONFIG["limits"]["perspective_candidates"])
    focus_text = " ".join(str(x.get("need") or "") for x in (state.get("scan_brief") or []))
    focus_words = words(focus_text)
    targeted = []
    if focus_words:
        for s in clean:
            if words(s["headline"] + " " + s["description"]) & focus_words:
                targeted.append(s)
    out, keys = [], set()
    for s in targeted[:8] + normal[:maxn-maxp] + perspective[:maxp]:
        k = s["url"]
        if k not in keys:
            keys.add(k); out.append(s)
    return out[:maxn]

def pull_inbox():
    data = backend("pull_inbox", limit=10) or {}
    rows = data.get("rows") or []
    allowed = {"article_idea","followup","research_request","story_tip"}
    return [r for r in rows if str(r.get("kind") or "article_idea") in allowed]

def fetch_source(signal):
    url = str(signal.get("url") or "")
    evidence = {
        "url": url,
        "publisher": signal.get("source"),
        "headline": signal.get("headline"),
        "published_at": signal.get("published_at"),
        "source_class": signal.get("source_class"),
        "region": signal.get("region"),
        "feed_description": signal.get("description"),
        "fetched": False,
        "text": "",
    }
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT, "accept-language": "en,da;q=0.9"}, timeout=20, allow_redirects=True)
        if r.ok and "text/html" in r.headers.get("content-type",""):
            parser = TextExtractor()
            parser.feed(r.text[:1_500_000])
            text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
            evidence["fetched"] = bool(text)
            evidence["resolved_url"] = r.url
            evidence["text"] = text[:14000]
    except Exception as e:
        evidence["fetch_error"] = type(e).__name__
    return evidence

def research_web(query, story_id, inbox_id=None):
    model = CONFIG["models"]["research_web"]
    instructions = """Du er research-assistent for en dansk redaktion. Brug web-søgning til at finde 2-4 konkrete, troværdige kilder til opgaven. Prioritér officielle/primære kilder og veletablerede medier. Returnér KUN JSON:
{"sources":[{"url":"https://...","publisher":"...","why":"..."}],"note":"kort"}.
Opfind aldrig URL'er. Perspektivmedier kan være spor, men ikke alene bære en kontroversiel faktuel påstand."""
    data, _ = call_json("evidence_web_search", model, instructions, {"query": query}, story_id=story_id, inbox_id=inbox_id,
                        max_output_tokens=700, web_search=True, reasoning="low")
    return data.get("sources") or []

def find_related_signals(selected, inventory):
    a = words((selected.get("headline") or "") + " " + (selected.get("description") or ""))
    scored = []
    for s in inventory:
        if s.get("url") == selected.get("url"):
            continue
        b = words((s.get("headline") or "") + " " + (s.get("description") or ""))
        if not a or not b:
            continue
        score = len(a & b) / max(1, min(len(a), len(b)))
        if score >= .33:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:2]]

def build_evidence(desk, inventory, story_id, inbox=None):
    selected_url = desk.get("selected_url")
    selected = next((s for s in inventory if s.get("url") == selected_url), None)
    evidence = []
    if selected:
        evidence.append(fetch_source(selected))
        for s in find_related_signals(selected, inventory):
            evidence.append(fetch_source(s))
    if inbox:
        for u in re.findall(r"https?://[^\s<>)\]]+", str(inbox.get("body") or ""))[:3]:
            evidence.append(fetch_source({"url": u, "source": "Publisher Inbox", "headline": inbox.get("title") or "Publisher input"}))
    need_search = bool(desk.get("research_query")) and (
        not evidence or desk.get("needs_counterparty") or desk.get("needs_primary_source") or inbox
    )
    if need_search:
        for row in research_web(str(desk["research_query"]), story_id, inbox.get("id") if inbox else None)[:3]:
            u = str(row.get("url") or "")
            if u and all(x.get("url") != u for x in evidence):
                evidence.append(fetch_source({"url": u, "source": row.get("publisher") or "Web research", "headline": row.get("why") or ""}))
    evidence = [e for e in evidence if e.get("url")][:int(CONFIG["limits"]["max_source_fetches"])]
    if not evidence:
        raise RuntimeError("No evidence URLs available")
    if not any(e.get("fetched") or len(str(e.get("feed_description") or "")) > 80 for e in evidence):
        raise RuntimeError("Evidence could not be retrieved with enough substance")
    return evidence

def normalize_draft(draft):
    title = strip_html(draft.get("title") or draft.get("rubrik") or "")
    standfirst = strip_html(draft.get("standfirst") or draft.get("manchet") or "")
    body = draft.get("body") or []
    if isinstance(body, str):
        body = [{"type": "p", "text": x.strip()} for x in re.split(r"\n\s*\n", body) if x.strip()]
    norm = []
    for b in body:
        if not isinstance(b, dict):
            continue
        kind = b.get("type") if b.get("type") in {"p","h2","h3","blockquote","ul","ol"} else "p"
        if kind in {"ul","ol"}:
            items = [strip_html(x) for x in (b.get("items") or []) if strip_html(x)]
            if items:
                norm.append({"type": kind, "items": items})
        else:
            text = strip_html(b.get("text") or "")
            if text:
                norm.append({"type": kind, "text": text})
    if not title or not standfirst or len(norm) < 3:
        raise RuntimeError("Journalist returned incomplete article")
    return {"title": title, "standfirst": standfirst, "body": norm}

def journalist(desk, evidence, story_id, issues=None):
    instructions = """Du er journalist på Morgentidende. Skriv en færdig dansk netavisartikel fra den dokumenterede evidens og Desk-bestillingen.
HÅRD FAGLIG REGEL: Skriv frisk, naturligt, idiomatisk dansk ud fra betydningen. Kopiér ikke svensk/norsk/engelsk syntaks, falske venner eller maskinoversættelser fra kilderne.
Opfind ingen fakta, citater eller motiver. Bevar attribution og forbehold. Gør tydeligt hvem der påstår hvad. Hvis evidensen ikke understøtter noget, udelad det.
Morgentidendes vinkel må bestemme spørgsmål og prioritering, aldrig fakta.
Returnér KUN JSON:
{"title":"...","standfirst":"...","body":[{"type":"p","text":"..."},{"type":"h2","text":"..."},{"type":"p","text":"..."}],"topics":["..."],"source_refs":["S1"],"hero_search_terms":["konkret person/event/sted", "..."]}.
Sigt efter ca. 450-800 ord for en almindelig nyhed; kortere hvis materialet ikke bærer mere."""
    payload = {"commission": desk, "evidence": evidence}
    if issues:
        payload["revision_instruction"] = issues
        instructions += "\nDu reparerer nu den eksisterende artikel. Ret præcis de påpegede problemer uden at ændre dokumenterede fakta."
    model = CONFIG["models"]["journalist"]
    data, _ = call_json("journalist" if not issues else "journalist_repair", model, instructions, payload,
                        story_id=story_id, max_output_tokens=1800, reasoning="low")
    out = normalize_draft(data)
    out["topics"] = [strip_html(x) for x in (data.get("topics") or []) if strip_html(x)][:8]
    out["hero_search_terms"] = [strip_html(x) for x in (data.get("hero_search_terms") or []) if strip_html(x)][:4]
    return out

def language_review(draft, desk, story_id):
    model = CONFIG["models"]["language_editor"]
    instructions = """Du er en kræsen dansk sprogredaktør. Du skal IKKE genvurdere historiens politik eller nyhedsværdi. Find kun reelle sprogproblemer:
svensk/norsk læk, engelske calques, falske venner, ord-for-ord-oversættelse, forkert grammatik, unaturlige danske formuleringer og uklare sætninger.
Små stilpræferencer er ikke fejl. Returnér KUN JSON:
{"status":"approve"|"revise","issues":[{"quote":"konkret problem","fix":"naturligt dansk forslag","reason":"kort"}]}.
Brug revise kun når teksten faktisk bør repareres før publicering."""
    data, _ = call_json("danish_editor", model, instructions, {"article": draft, "angle": desk.get("angle")},
                        story_id=story_id, max_output_tokens=550, reasoning="low")
    if data.get("status") not in {"approve","revise"}:
        raise RuntimeError("Danish editor returned invalid status")
    return data

def commons_search(terms, limit=4):
    queries = [x for x in terms if x][:3]
    results, seen = [], set()
    for query in queries:
        try:
            params = {
                "action":"query","format":"json","formatversion":"2","generator":"search",
                "gsrsearch": f"{query} filetype:bitmap","gsrnamespace":"6","gsrlimit":"10",
                "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":"1400",
                "origin":"*",
            }
            r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers={"user-agent":USER_AGENT}, timeout=25)
            for page in (r.json().get("query",{}).get("pages") or []):
                ii = (page.get("imageinfo") or [{}])[0]
                meta = ii.get("extmetadata") or {}
                lic = strip_html((meta.get("LicenseShortName") or {}).get("value") or (meta.get("UsageTerms") or {}).get("value"))
                if not lic or not any(h in lic.casefold() for h in ALLOWED_LICENSE_HINTS):
                    continue
                url = ii.get("thumburl") or ii.get("url")
                original = ii.get("descriptionurl") or ii.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                artist = strip_html((meta.get("Artist") or {}).get("value")) or "Wikimedia Commons"
                desc = strip_html((meta.get("ImageDescription") or {}).get("value"))
                results.append({
                    "src": url,
                    "original_url": ii.get("url") or url,
                    "source_url": original,
                    "license": lic,
                    "credit": artist[:300],
                    "description": desc[:500],
                    "alt": desc[:240] or query,
                    "search_term": query,
                    "image_type": "photo",
                    "ai_generated": False,
                })
                if len(results) >= limit:
                    return results
        except Exception:
            continue
    return results

def chief_review(draft, desk, evidence, images, state, story_id, high_risk=False):
    model = CONFIG["models"]["chief_high_risk"] if high_risk else CONFIG["models"]["chief_normal"]
    instructions = """Du er Chefredaktør på Morgentidende og har reel publiceringsmyndighed.
Vurder samlet: (1) faktuel støtte og korrekt attribution i den medsendte evidens, (2) relevant pluralisme/modpart, (3) naturligt professionelt dansk som sidste sikkerhedsnet, (4) rubrik/manchet, (5) om Hero-kandidaten faktisk viser noget relevant for netop historien og har brugbar licens/credit, og (6) passende forside-rolle set i forhold til den aktuelle forside.
Du ser de faktiske Hero-billedpixels i samme rækkefølge som image_candidates. Et lovligt men irrelevant billede er ikke acceptabelt.
REPAIR-FIRST: Sprogfejl, manglende modpart, manglende research eller dårligt billede skal normalt give revise/research_more/media_retry, ikke drop. DROP er kun til en historie der reelt ikke holder, er dublet, ikke kan dokumenteres eller er blevet irrelevant.
Returnér KUN JSON:
{"decision":"publish"|"revise"|"research_more"|"media_retry"|"drop",
 "issues":["konkret..."],
 "hero_choice":0,
 "frontpage_role":"lead"|"top_story"|"important_followup"|"normal"|"magazine"|"section_only",
 "followup_needs":["authority_response"|"counterparty_response"|"new_development"],
 "reason":"kort",
 "media_search_terms":["..."]}.
Ved publish skal hero_choice pege på et faktisk relevant billede."""
    payload = {
        "commission": desk,
        "article": draft,
        "evidence": [{k:v for k,v in e.items() if k != "text"} | {"text_excerpt": str(e.get("text") or e.get("feed_description") or "")[:5000]} for e in evidence],
        "image_candidates": [{k:v for k,v in im.items() if k not in {"original_url"}} for im in images],
        "frontpage_state": {
            "active_lead": state.get("active_lead"),
            "top_stories": state.get("top_stories"),
            "coverage_last_24h": state.get("coverage_last_24h"),
            "active_packages": state.get("active_packages"),
        },
    }
    data, _ = call_json("chief_editor_high_risk" if high_risk else "chief_editor", model, instructions, payload,
                        story_id=story_id, max_output_tokens=700, images=[x["src"] for x in images], reasoning="medium" if high_risk else "low")
    if data.get("decision") not in {"publish","revise","research_more","media_retry","drop"}:
        raise RuntimeError("Chief returned invalid decision")
    return data

def article_related(package_id):
    if not package_id:
        return []
    rows = []
    for p in ART_DIR.glob("*.json"):
        a = load_json(p, {}) or {}
        if a.get("status") == "published" and a.get("package_id") == package_id:
            rows.append(a)
    rows.sort(key=lambda a: parse_time(a.get("published_at")), reverse=True)
    return rows

def publish_article(desk, draft, evidence, hero, chief, story_id, package_id, inbox=None):
    date_prefix = datetime.now(timezone.utc).date().isoformat()
    slug = f"{date_prefix}-{slugify(draft['title'])}"
    path = ART_DIR / f"{slug}.json"
    n = 2
    while path.exists():
        slug = f"{date_prefix}-{slugify(draft['title'])}-{n}"
        path = ART_DIR / f"{slug}.json"; n += 1
    source_path = SRC_DIR / f"{slug}.json"
    source_rows = []
    for i, e in enumerate(evidence, 1):
        source_rows.append({
            "id": f"S{i}",
            "name": e.get("publisher") or urllib.parse.urlparse(e.get("url","")).netloc,
            "url": e.get("url"),
            "headline": e.get("headline"),
            "published_at": e.get("published_at"),
            "fetched": bool(e.get("fetched")),
        })
    ledger = {
        "schema_version": 3,
        "story_id": story_id,
        "package_id": package_id,
        "generated_at": now_iso(),
        "sources": source_rows,
        "evidence_note": "Pipeline v3 stores source provenance; source sufficiency is an editorial judgment, not a source-count gate.",
    }
    dump_json(source_path, ledger)
    related_rows = article_related(package_id)
    related = []
    for a in related_rows[:4]:
        im = a.get("image") or {}
        related.append({"slug":a["slug"],"category":a.get("category","Nyhed"),"title":a.get("title",""),"teaser":a.get("standfirst",""),"image_src":im.get("src"),"image_alt":im.get("alt","")})
    related_news_slug = related_rows[0]["slug"] if related_rows else None
    article = {
        "pipeline_version": 3,
        "status": "published",
        "release_requested": False,
        "story_id": story_id,
        "package_id": package_id,
        "slug": slug,
        "category": desk.get("category") if desk.get("category") in CONFIG["editorial"]["categories"] else "Nyhed",
        "weight": desk.get("weight") if desk.get("weight") in {"A","B","C","D"} else "C",
        "article_type": desk.get("article_type") or "news",
        "frontpage_role": chief.get("frontpage_role") or "normal",
        "title": draft["title"],
        "standfirst": draft["standfirst"],
        "byline": "Morgentidende Redaktion",
        "published_at": now_iso(),
        "updated_at": None,
        "ledger": str(source_path.relative_to(ROOT)),
        "seo": {"title": draft["title"], "description": draft["standfirst"], "canonical": None},
        "image": {
            "src": hero["src"],
            "alt": hero.get("alt") or draft["title"],
            "credit": hero.get("credit") or "Wikimedia Commons",
            "license": hero.get("license") or "Public domain",
            "source_url": hero.get("source_url") or hero.get("original_url"),
            "image_type": hero.get("image_type") or "photo",
            "context_type": "documentary" if not hero.get("ai_generated") else "editorial_illustration",
            "caption": hero.get("description") or "",
            "pending_image": False,
            "ai_generated": bool(hero.get("ai_generated")),
            "placement": "lead",
        },
        "body": draft["body"],
        "topics": draft.get("topics") or [],
        "followup_needs": chief.get("followup_needs") or [],
        "related_news_slug": related_news_slug,
        "related": related,
        "automation_origin": "pipeline-v3",
        "editorial_decision": {"chief": chief.get("decision"), "reason": chief.get("reason"), "run_id": RUN_ID},
    }
    dump_json(path, article)
    backend("log_ai", row={
        "run_id": RUN_ID, "story_id": story_id, "stage": "publish", "provider": "system", "model": "none",
        "status": "success", "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
        "estimated_cost_usd": 0, "estimated_cost_dkk": 0, "latency_ms": 0,
        "metadata": {"slug": slug, "frontpage_role": article["frontpage_role"]},
    })
    if inbox:
        backend("set_inbox_status", id=inbox["id"], status="completed", story_id=story_id, package_id=package_id, pipeline_run_id=RUN_ID)
    return article

def cycle(cycle_no, report):
    subprocess.run([sys.executable, str(ROOT/"scripts"/"v3_newsroom_state.py")], check=True)
    state = load_json(STATE, {}) or {}
    inventory = candidate_inventory(state)
    inbox_rows = pull_inbox()
    desk_model = CONFIG["models"]["desk"]
    desk_instructions = """Du er vagthavende Desk Editor på Morgentidende. Vælg højst én historie til næste artikel, eller vælg ingen.
Vurder NYHEDSVÆRDI, aktualitet, konsekvens, dokumenterbarhed, originalitet, hvad forsiden allerede har, aktive opfølgningsbehov og Publisher Inbox.
Find gerne en lidt anderledes og skarp vinkel i tråd med den redaktionelle linje, men vinklen må aldrig forudbestemme fakta.
Perspektiv-/advocacy-kilder er gode til at opdage spor, men kontroversielle fakta skal research'es fra passende kilder.
Undgå dubletter og mekanisk kategorifyld. Publisher Inbox har høj prioritet når den indeholder en konkret artikelidé, men skal stadig behandles journalistisk.
Returnér KUN JSON:
{"decision":"commission"|"none","selected_url":"https://..."|null,"inbox_id":"uuid"|null,
"angle":"...","why_now":"...","why_this_angle":"...","category":"...","weight":"A"|"B"|"C"|"D",
"article_type":"news"|"followup"|"background"|"analysis"|"feature",
"frontpage_intent":"lead"|"top_story"|"important_followup"|"normal"|"magazine"|"section_only",
"package_id":"eksisterende-id eller null","needs_counterparty":true|false,"needs_primary_source":true|false,
"research_query":"konkret søgeopgave eller null","hero_search_terms":["..."],"risk_level":"normal"|"high"}."""
    desk_payload = {
        "editorial_line": CONFIG["editorial"],
        "frontpage_state": state,
        "scan_candidates": inventory,
        "publisher_inbox": inbox_rows,
    }
    desk, desk_usage = call_json("desk", desk_model, desk_instructions, desk_payload, max_output_tokens=750, reasoning="medium")
    report["stages"].append({"cycle":cycle_no,"stage":"desk","model":desk_model,"cost_dkk":round(desk_usage["dkk"],4),"decision":desk.get("decision")})
    if desk.get("decision") != "commission":
        return {"status":"no_article","reason":"desk_none"}

    inbox = next((r for r in inbox_rows if r.get("id") == desk.get("inbox_id")), None)
    seed = desk.get("selected_url") or (inbox.get("title") if inbox else desk.get("angle")) or f"cycle-{cycle_no}"
    story_id = f"v3-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{hashlib.sha1(str(seed).encode()).hexdigest()[:8]}"
    if inbox:
        backend("set_inbox_status", id=inbox["id"], status="commissioned", story_id=story_id, pipeline_run_id=RUN_ID)

    try:
        evidence = build_evidence(desk, inventory, story_id, inbox)
    except Exception as e:
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="parked", story_id=story_id, pipeline_run_id=RUN_ID)
        report["stages"].append({"cycle":cycle_no,"story_id":story_id,"stage":"evidence","status":"parked","reason":str(e)[:200]})
        return {"status":"parked","story_id":story_id,"reason":str(e)}

    draft = journalist(desk, evidence, story_id)
    lang = language_review(draft, desk, story_id)
    if lang.get("status") == "revise":
        draft = journalist(desk, evidence, story_id, issues={"language_issues": lang.get("issues") or [], "current_article": draft})

    terms = list(draft.get("hero_search_terms") or []) + list(desk.get("hero_search_terms") or [])
    if not terms:
        terms = [draft["title"]]
    images = commons_search(terms, int(CONFIG["limits"]["hero_candidates"]))
    if not images:
        report["stages"].append({"cycle":cycle_no,"story_id":story_id,"stage":"media","status":"parked","reason":"no lawful Commons candidate"})
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="parked", story_id=story_id, pipeline_run_id=RUN_ID)
        return {"status":"parked","story_id":story_id,"reason":"no lawful Hero candidate"}

    high_risk = desk.get("risk_level") == "high" or desk.get("weight") == "A" or bool(desk.get("needs_counterparty"))
    chief = chief_review(draft, desk, evidence, images, state, story_id, high_risk=high_risk)

    decision = chief.get("decision")
    if decision == "revise":
        draft = journalist(desk, evidence, story_id, issues={"chief_issues": chief.get("issues") or [], "current_article": draft})
        chief = chief_review(draft, desk, evidence, images, state, story_id, high_risk=high_risk)
        decision = chief.get("decision")
    elif decision == "research_more" and desk.get("research_query"):
        extra = research_web(str(desk.get("research_query")), story_id, inbox.get("id") if inbox else None)
        for row in extra[:2]:
            if row.get("url") and all(e.get("url") != row.get("url") for e in evidence):
                evidence.append(fetch_source({"url":row["url"],"source":row.get("publisher") or "Web research","headline":row.get("why") or ""}))
        draft = journalist(desk, evidence, story_id, issues={"chief_issues": chief.get("issues") or [], "current_article": draft})
        chief = chief_review(draft, desk, evidence, images, state, story_id, high_risk=high_risk)
        decision = chief.get("decision")
    elif decision == "media_retry":
        more_terms = chief.get("media_search_terms") or terms[1:] or [draft["title"]]
        images = commons_search(more_terms, int(CONFIG["limits"]["hero_candidates"]))
        if images:
            chief = chief_review(draft, desk, evidence, images, state, story_id, high_risk=high_risk)
            decision = chief.get("decision")

    if decision != "publish":
        status = "dropped" if decision == "drop" else "parked"
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="rejected" if status=="dropped" else "parked", story_id=story_id, pipeline_run_id=RUN_ID)
        report["stages"].append({"cycle":cycle_no,"story_id":story_id,"stage":"chief","status":status,"decision":decision,"reason":str(chief.get("reason") or "")[:200]})
        return {"status":status,"story_id":story_id,"decision":decision}

    choice = chief.get("hero_choice")
    if not isinstance(choice, int) or choice < 0 or choice >= len(images):
        return {"status":"parked","story_id":story_id,"reason":"Chief publish lacked valid Hero choice"}
    hero = images[choice]
    package_id = str(desk.get("package_id") or f"pkg-{slugify(desk.get('angle') or draft['title'])[:60]}")
    article = publish_article(desk, draft, evidence, hero, chief, story_id, package_id, inbox)
    report["stages"].append({"cycle":cycle_no,"story_id":story_id,"stage":"publish","status":"published","slug":article["slug"],"frontpage_role":article["frontpage_role"]})
    subprocess.run([sys.executable, str(ROOT/"scripts"/"v3_newsroom_state.py")], check=True)
    return {"status":"published","story_id":story_id,"slug":article["slug"]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    args = ap.parse_args()
    cycles = max(1, min(3, args.cycles))
    report = {"schema_version":1,"run_id":RUN_ID,"started_at":now_iso(),"cycles_requested":cycles,"results":[],"stages":[]}
    report["cost_before"] = backend("cost_summary")
    for i in range(1, cycles+1):
        try:
            result = cycle(i, report)
        except Exception as e:
            result = {"status":"error","reason":str(e)[:500]}
        report["results"].append({"cycle":i, **result})
    report["finished_at"] = now_iso()
    report["cost_after"] = backend("cost_summary")
    out = REPORT_ROOT / RUN_ID / "summary.json"
    dump_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
