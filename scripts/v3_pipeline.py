#!/usr/bin/env python3
"""Morgentidende Pipeline v3 — lean editorial chain.

Flow:
Scan (retrieval + BGE-M3 semantic clustering) -> Desk (Qwen3-30B) ->
Journalist (Terra, may order targeted Scan) -> Media (Gemma + one lawful
photo at a time, FLUX.1 Schnell only if no photo works) ->
Chefredaktør (Terra, edits/researches itself) -> Publish (code).

There is deliberately no separate Research or Danish-editor stage. Code owns
transport, source retrieval, rights metadata, state, retries and publication
integrity. Models own editorial judgment.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
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
GENERATED_MEDIA_DIR = ROOT / "docs" / "media" / "generated"

WORKER_URL = os.environ.get("V3_WORKER_URL", "").rstrip("/")
WORKER_TOKEN = os.environ.get("V3_WORKER_TOKEN", "")
BACKEND_URL = os.environ.get("V3_PRIVATE_BACKEND_URL", "").rstrip("/")
OIDC_TOKEN = os.environ.get("GITHUB_OIDC_TOKEN", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID") or f"local-{int(time.time())}"

USER_AGENT = "MorgentidendeV3/2.0 (+editorial retrieval)"
ALLOWED_LICENSE_HINTS = ("public domain", "cc0", "cc by", "cc-by", "creative commons attribution")
BGE_THRESHOLD = float(CONFIG.get("scan", {}).get("semantic_cluster_threshold", 0.76))
_EMBED_CACHE: dict[str, list[float]] = {}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
        if tag in {"p", "h1", "h2", "h3", "li", "article", "section"}:
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
        text = text[first:last + 1]
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


def log_scan_request(*, story_id, requested_by, kind, query, purpose, result_count, metadata=None):
    backend(
        "log_scan_request",
        row={
            "run_id": RUN_ID,
            "story_id": story_id,
            "requested_by": requested_by,
            "kind": kind,
            "query": str(query)[:1000],
            "purpose": str(purpose or "")[:1000],
            "result_count": int(result_count or 0),
            "metadata": metadata or {},
        },
    )


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
    """Normal model call. v3_safe_runner replaces this at runtime with budget guard."""
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
    if not text.strip():
        raise RuntimeError(f"AI {stage} returned empty text")
    usage = data.get("usage") or {}
    inp, out, cached, usd, dkk = estimate_cost(model, usage)
    elapsed_ms = int((time.time() - started) * 1000)
    backend("log_ai", row={
        "run_id": RUN_ID, "story_id": story_id, "inbox_id": inbox_id, "stage": stage,
        "provider": "workers-ai-native" if str(model).startswith("@cf/") else "cloudflare-ai-gateway",
        "model": model, "request_id": request_id, "attempt": 1, "status": "success",
        "input_tokens": inp, "output_tokens": out, "cached_input_tokens": cached,
        "estimated_cost_usd": round(usd, 8), "estimated_cost_dkk": round(dkk, 6),
        "latency_ms": elapsed_ms, "prompt_text": prompt, "response_text": text,
        "metadata": {"reasoning": reasoning, "web_search": web_search, "image_count": len(images or [])},
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(timespec="seconds"),
    })
    return text, {"input_tokens": inp, "output_tokens": out, "cached_input_tokens": cached,
                  "usd": usd, "dkk": dkk, "latency_ms": elapsed_ms}


def call_json(stage, model, instructions, obj, *, story_id=None, inbox_id=None,
              max_output_tokens=800, images=None, web_search=False, reasoning="low"):
    prompt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    last = None
    for attempt in range(int(CONFIG["limits"].get("max_format_attempts", 2))):
        extra = "" if attempt == 0 else "\nVIGTIGT: Returnér KUN ét gyldigt JSON-objekt uden markdown."
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


# ---------- Scan ----------

def embed_texts(texts: list[str], story_id=None):
    """BGE-M3 embeddings. v3_safe_runner replaces this with budget-accounted call."""
    if not texts:
        return []
    if not WORKER_URL or not WORKER_TOKEN:
        raise RuntimeError("V3 Worker URL/token missing")
    model = CONFIG["models"]["scan_embedding"]
    r = requests.post(
        WORKER_URL + "/embed",
        headers={"authorization": f"Bearer {WORKER_TOKEN}", "content-type": "application/json"},
        json={"model": model, "texts": texts[:128]},
        timeout=120,
    )
    data = r.json()
    if not r.ok or not data.get("ok"):
        raise RuntimeError(f"Scan embedding HTTP {r.status_code}: {data}")
    return data.get("data") or []


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_cluster(signals: list[dict], story_id=None):
    if len(signals) < 2:
        return signals
    texts = [strip_html((s.get("headline") or "") + ". " + (s.get("description") or ""))[:900] for s in signals]
    missing_idx, missing_text = [], []
    vectors: list[list[float] | None] = [None] * len(texts)
    for i, text in enumerate(texts):
        key = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if key in _EMBED_CACHE:
            vectors[i] = _EMBED_CACHE[key]
        else:
            missing_idx.append(i)
            missing_text.append(text)
    if missing_text:
        new_vecs = embed_texts(missing_text, story_id=story_id)
        if len(new_vecs) != len(missing_text):
            return signals
        for i, vec in zip(missing_idx, new_vecs):
            vectors[i] = vec
            _EMBED_CACHE[hashlib.sha1(texts[i].encode("utf-8")).hexdigest()] = vec
    kept: list[dict] = []
    kept_vecs: list[list[float]] = []
    for s, vec in zip(signals, vectors):
        if not vec:
            kept.append(s)
            kept_vecs.append([])
            continue
        duplicate_of = None
        for j, kv in enumerate(kept_vecs):
            if kv and _cosine(vec, kv) >= BGE_THRESHOLD:
                duplicate_of = j
                break
        if duplicate_of is None:
            row = dict(s)
            row["cluster_variants"] = 1
            kept.append(row)
            kept_vecs.append(vec)
        else:
            kept[duplicate_of]["cluster_variants"] = int(kept[duplicate_of].get("cluster_variants") or 1) + 1
    return kept


def already_used_urls():
    urls = set()
    for p in SRC_DIR.glob("*.json"):
        d = load_json(p, {}) or {}
        for s in d.get("sources", []):
            if s.get("url"):
                urls.add(str(s["url"]).split("#")[0])
    return urls


def targeted_scan(query: str, *, limit=5, story_id=None, requested_by="journalist", kind="source", purpose=""):
    """Targeted Scan retrieval using Google News RSS; no generative model."""
    q = strip_html(query)[:500]
    if not q:
        return []
    params = {"q": q, "hl": "da", "gl": "DK", "ceid": "DK:da"}
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
    out = []
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for item in root.findall(".//item"):
            title = strip_html(item.findtext("title") or "")
            link = strip_html(item.findtext("link") or "")
            desc = strip_html(item.findtext("description") or "")
            pub = strip_html(item.findtext("pubDate") or "")
            source = item.find("source")
            publisher = strip_html(source.text if source is not None else "Google News")
            if not title or not link:
                continue
            out.append({
                "source": publisher or "Google News",
                "source_class": "targeted_scan",
                "region": "TARGETED",
                "source_priority": 5,
                "discovery_only": False,
                "headline": title[:220],
                "description": desc[:420],
                "url": link,
                "published_at": pub or None,
                "targeted_query": q,
            })
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"targeted Scan failed: {type(e).__name__}: {e}", file=sys.stderr)
    log_scan_request(story_id=story_id, requested_by=requested_by, kind=kind, query=q,
                     purpose=purpose, result_count=len(out))
    return out


def candidate_inventory(state):
    q = load_json(QUEUE, {}) or {}
    signals = list(q.get("signals") or [])
    for req in (state.get("scan_brief") or [])[:3]:
        query = req.get("query") or req.get("need")
        if query:
            signals.extend(targeted_scan(str(query), limit=4, requested_by="chief", kind="next_story",
                                         purpose=req.get("purpose") or req.get("type") or "frontpage need"))
    used = already_used_urls()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=42)
    clean, seen = [], set()
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
            "source": s.get("source"), "source_class": s.get("source_class"), "region": s.get("region"),
            "source_priority": int(s.get("source_priority") or 0), "discovery_only": bool(s.get("discovery_only")),
            "headline": headline[:220], "description": strip_html(s.get("description"))[:420],
            "url": url, "published_at": s.get("published_at"), "targeted_query": s.get("targeted_query"),
        })
    clean.sort(key=lambda s: (parse_time(s.get("published_at")), s.get("source_priority", 0)), reverse=True)
    per_source, pre = {}, []
    for s in clean:
        src = str(s.get("source"))
        if per_source.get(src, 0) >= 4:
            continue
        per_source[src] = per_source.get(src, 0) + 1
        pre.append(s)
        if len(pre) >= int(CONFIG["limits"]["desk_candidates"]) * 2:
            break
    clustered = semantic_cluster(pre)
    return clustered[:int(CONFIG["limits"]["desk_candidates"])]


def pull_inbox():
    data = backend("pull_inbox", limit=10) or {}
    rows = data.get("rows") or []
    allowed = {"article_idea", "followup", "story_tip"}
    return [r for r in rows if str(r.get("kind") or "article_idea") in allowed]


def fetch_source(signal):
    url = str(signal.get("url") or "")
    evidence = {
        "url": url, "publisher": signal.get("source"), "headline": signal.get("headline"),
        "published_at": signal.get("published_at"), "source_class": signal.get("source_class"),
        "region": signal.get("region"), "feed_description": signal.get("description"),
        "fetched": False, "text": "",
    }
    try:
        r = requests.get(url, headers={"user-agent": USER_AGENT, "accept-language": "da,en;q=0.9"},
                         timeout=20, allow_redirects=True)
        if r.ok and "text/html" in r.headers.get("content-type", ""):
            parser = TextExtractor()
            parser.feed(r.text[:1_500_000])
            text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
            evidence["fetched"] = bool(text)
            evidence["resolved_url"] = r.url
            evidence["text"] = text[:16000]
    except Exception as e:
        evidence["fetch_error"] = type(e).__name__
    return evidence


def main_sources(desk, inventory, inbox=None):
    rows = []
    selected = next((s for s in inventory if s.get("url") == desk.get("selected_url")), None)
    if selected:
        rows.append(fetch_source(selected))
    if inbox:
        urls = re.findall(r"https?://[^\s<>)\]]+", str(inbox.get("body") or ""))
        for u in urls[:1]:
            rows.append(fetch_source({"url": u, "source": "Publisher Inbox", "headline": inbox.get("title") or "Publisher input"}))
    rows = [r for r in rows if r.get("url")]
    if not rows:
        raise RuntimeError("Desk commission has no main source")
    if not any(r.get("fetched") or len(str(r.get("feed_description") or "")) > 80 for r in rows):
        raise RuntimeError("Main source could not be retrieved with enough substance")
    return rows[:2]


def scan_for_requests(requests_, *, story_id, requested_by, kind="source", max_requests=2):
    found = []
    for req in (requests_ or [])[:max_requests]:
        if isinstance(req, str):
            query, purpose = req, ""
        else:
            query, purpose = req.get("query"), req.get("purpose")
        if not query:
            continue
        candidates = targeted_scan(str(query), limit=3, story_id=story_id, requested_by=requested_by,
                                   kind=kind, purpose=str(purpose or ""))
        for c in candidates[:2]:
            e = fetch_source(c)
            if e.get("url") and all(x.get("url") != e.get("url") for x in found):
                found.append(e)
    return found[:int(CONFIG["limits"]["max_source_fetches"])]


# ---------- Journalist ----------

def normalize_draft(draft):
    if not isinstance(draft, dict):
        raise RuntimeError("Article is not an object")
    title = strip_html(draft.get("title") or draft.get("rubrik") or "")
    standfirst = strip_html(draft.get("standfirst") or draft.get("manchet") or "")
    body = draft.get("body") or []
    if isinstance(body, str):
        body = [{"type": "p", "text": x.strip()} for x in re.split(r"\n\s*\n", body) if x.strip()]
    norm = []
    for b in body:
        if not isinstance(b, dict):
            continue
        kind = b.get("type") if b.get("type") in {"p", "h2", "h3", "blockquote", "ul", "ol"} else "p"
        if kind in {"ul", "ol"}:
            items = [strip_html(x) for x in (b.get("items") or []) if strip_html(x)]
            if items:
                norm.append({"type": kind, "items": items})
        else:
            text = strip_html(b.get("text") or "")
            if text:
                norm.append({"type": kind, "text": text})
    if not title or not standfirst or len(norm) < 3:
        raise RuntimeError("Article is incomplete")
    out = {"title": title, "standfirst": standfirst, "body": norm}
    out["topics"] = [strip_html(x) for x in (draft.get("topics") or []) if strip_html(x)][:8]
    out["hero_search_terms"] = [strip_html(x) for x in (draft.get("hero_search_terms") or []) if strip_html(x)][:5]
    return out


def journalist_pass(desk, evidence, story_id, *, current_article=None, search_context=None):
    model = CONFIG["models"]["journalist"]
    instructions = """Du er Journalist på Morgentidende. Du er GPT-5.6 Terra og ejer research-behovet for din artikel.
Skriv fra KILDERNES BETYDNING på naturligt idiomatisk dansk; oversæt aldrig ord-for-ord. Opfind aldrig fakta, citater eller motiver. Attribution og forbehold skal være præcise.
Én autoritativ hovedkilde kan være nok til en enkel faktuel historie. Bestil kun en målrettet Scan-søgning, når du faktisk mangler noget. Ved politiske historier i Indland/Udland skal du aktivt overveje den reelle modpart/pluralisme; hvis modpartens dokumenterede synspunkt mangler og er relevant, bestil Scan efter det.
Scan kan bestilles til fx modpartens holdning, myndighedssvar eller en konkret primærkilde. Højst to søgninger. Du vurderer selv uenighed mellem kilderne.
Returnér KUN JSON med denne form:
{"status":"ready"|"needs_scan"|"drop","reason":"kort","scan_requests":[{"query":"meget konkret søgning","purpose":"hvad mangler"}],"article":{"title":"...","standfirst":"...","body":[{"type":"p","text":"..."}],"topics":["..."],"hero_search_terms":["1 selve begivenheden","2 central person","3 præcist sted eller objekt"]}}.
Ved ready skal article være en færdig netavisartikel. Sigt ca. 450-800 ord, kortere hvis materialet ikke bærer mere. hero_search_terms skal stå i Media-prioritet: konkret begivenhed først, derefter person, derefter sted/objekt."""
    payload = {
        "commission": desk,
        "sources": [{k: v for k, v in e.items() if k != "text"} | {"text_excerpt": str(e.get("text") or e.get("feed_description") or "")[:9000]} for e in evidence],
    }
    if current_article:
        payload["current_article"] = current_article
        payload["instruction"] = "Opdatér selv artiklen med de nye kilder; behold korrekte dele og ret alt nødvendigt."
    if search_context:
        payload["scan_results_note"] = search_context
    data, usage = call_json("journalist" if not current_article else "journalist_after_scan", model, instructions, payload,
                            story_id=story_id, max_output_tokens=2200, reasoning="medium")
    status = data.get("status")
    if status not in {"ready", "needs_scan", "drop"}:
        raise RuntimeError("Journalist returned invalid status")
    article = None
    if data.get("article"):
        article = normalize_draft(data["article"])
    return {"status": status, "reason": data.get("reason") or "", "scan_requests": data.get("scan_requests") or [],
            "article": article, "usage": usage}


def run_journalist(desk, evidence, story_id):
    first = journalist_pass(desk, evidence, story_id)
    if first["status"] == "drop":
        return None, evidence, "drop"
    if first["status"] == "ready":
        if not first["article"]:
            raise RuntimeError("Journalist ready without article")
        return first["article"], evidence, "ready"
    extra = scan_for_requests(first["scan_requests"], story_id=story_id, requested_by="journalist",
                              max_requests=int(CONFIG["limits"].get("max_journalist_scan_requests", 2)))
    if not extra:
        return None, evidence, "needs_scan_no_results"
    all_sources = (evidence + extra)[:int(CONFIG["limits"]["max_source_fetches"])]
    second = journalist_pass(desk, all_sources, story_id, current_article=first.get("article"),
                             search_context="Scan-søgninger er udført; brug kun de medsendte kilder, der faktisk støtter teksten.")
    if second["status"] != "ready" or not second["article"]:
        return None, all_sources, second["status"]
    return second["article"], all_sources, "ready"


# ---------- Media ----------

def commons_search_one(term):
    query = strip_html(term)
    if not query:
        return None
    try:
        params = {
            "action": "query", "format": "json", "formatversion": "2", "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6", "gsrlimit": "12",
            "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "1280", "origin": "*",
        }
        r = requests.get("https://commons.wikimedia.org/w/api.php", params=params,
                         headers={"user-agent": USER_AGENT}, timeout=25)
        for page in (r.json().get("query", {}).get("pages") or []):
            ii = (page.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value") or
                             (meta.get("UsageTerms") or {}).get("value"))
            if not lic or not any(h in lic.casefold() for h in ALLOWED_LICENSE_HINTS):
                continue
            url = ii.get("thumburl") or ii.get("url")
            if not url:
                continue
            artist = strip_html((meta.get("Artist") or {}).get("value")) or "Wikimedia Commons"
            desc = strip_html((meta.get("ImageDescription") or {}).get("value"))
            return {
                "src": url, "original_url": ii.get("url") or url,
                "source_url": ii.get("descriptionurl") or ii.get("url"),
                "license": lic, "credit": artist[:300], "description": desc[:500],
                "alt": desc[:240] or query, "search_term": query,
                "image_type": "photo", "ai_generated": False,
            }
    except Exception as e:
        print(f"Commons search failed: {type(e).__name__}", file=sys.stderr)
    return None


def media_review(draft, candidate, story_id, attempt_label):
    model = CONFIG["models"]["media_vision"]
    instructions = """Du er Media/billedredaktør på Morgentidende. Du får præcis ÉT billede ad gangen. Se pixlerne og afgør om det er et stærkt, semantisk relevant Hero til netop artiklen.
Prioriteten er: selve begivenheden > central person > præcist sted/objekt. Et generisk, historisk forkert eller geografisk forkert foto skal afvises. Metadata/licens må ikke opfindes. En redaktionel illustration må ikke ligne et dokumentarisk foto af en begivenhed, der ikke er fotograferet.
Returnér KUN JSON: {"decision":"approve"|"reject","reason":"kort","better_search_term":"kun ved reject eller null"}."""
    payload = {
        "article": {"title": draft["title"], "standfirst": draft["standfirst"], "topics": draft.get("topics") or []},
        "candidate": {k: v for k, v in candidate.items() if k not in {"_vision_src", "image_b64"}},
        "attempt": attempt_label,
    }
    vision_src = candidate.get("_vision_src") or candidate.get("src")
    data, _ = call_json("media_vision", model, instructions, payload, story_id=story_id,
                        max_output_tokens=220, images=[vision_src] if vision_src else [], reasoning="low")
    if data.get("decision") not in {"approve", "reject"}:
        raise RuntimeError("Media returned invalid decision")
    return data


def generate_image(prompt: str, story_id: str):
    """FLUX.1 Schnell generation. v3_safe_runner replaces this with budget guard."""
    if not WORKER_URL or not WORKER_TOKEN:
        raise RuntimeError("V3 Worker URL/token missing")
    r = requests.post(
        WORKER_URL + "/image",
        headers={"authorization": f"Bearer {WORKER_TOKEN}", "content-type": "application/json"},
        json={"model": CONFIG["models"]["media_generator"], "prompt": prompt, "steps": 4},
        timeout=180,
    )
    data = r.json()
    if not r.ok or not data.get("ok") or not data.get("image"):
        raise RuntimeError(f"Image generation failed HTTP {r.status_code}: {data}")
    return data


def _save_generated_image(story_id, image_b64):
    raw = base64.b64decode(image_b64)
    GENERATED_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(story_id)}.jpg"
    path = GENERATED_MEDIA_DIR / filename
    path.write_bytes(raw)
    return f"https://nickzen108.github.io/avisen/media/generated/{filename}", path


def media_choose(draft, desk, story_id, extra_terms=None):
    terms = []
    for t in list(extra_terms or []) + list(draft.get("hero_search_terms") or []) + list(desk.get("hero_search_terms") or []):
        t = strip_html(t)
        if t and t.casefold() not in {x.casefold() for x in terms}:
            terms.append(t)
    if not terms:
        terms = [draft["title"]]
    attempts = int(CONFIG["limits"].get("max_media_photo_attempts", 3))
    for idx, term in enumerate(terms[:attempts], 1):
        candidate = commons_search_one(term)
        log_scan_request(story_id=story_id, requested_by="media", kind="photo", query=term,
                         purpose=f"Hero photo priority {idx}", result_count=1 if candidate else 0)
        if not candidate:
            continue
        verdict = media_review(draft, candidate, story_id, f"lawful-photo-{idx}")
        if verdict.get("decision") == "approve":
            return candidate, {"source": "lawful_photo", "attempts": idx, "reason": verdict.get("reason")}
        better = strip_html(verdict.get("better_search_term") or "")
        if better and better.casefold() not in {x.casefold() for x in terms}:
            terms.append(better)

    prompt = (
        "Editorial newspaper illustration, clearly illustrative and not a documentary photograph. "
        "No text, no logos, no invented quotation marks, no fake screenshot, no depiction claiming to be the real event. "
        f"Story: {draft['title']}. {draft['standfirst']}. Clean professional news illustration, landscape 4:3 composition."
    )[:2000]
    generated = generate_image(prompt, story_id)
    public_src, _ = _save_generated_image(story_id, generated["image"])
    candidate = {
        "src": public_src,
        "_vision_src": f"data:image/jpeg;base64,{generated['image']}",
        "source_url": None,
        "license": "Redaktionel illustration",
        "credit": "Morgentidende",
        "description": f"Redaktionel illustration til: {draft['title']}",
        "alt": draft["title"],
        "search_term": "generated editorial illustration",
        "image_type": "illustration",
        "ai_generated": True,
    }
    verdict = media_review(draft, candidate, story_id, "flux-1-schnell")
    if verdict.get("decision") != "approve":
        return None, {"source": "generated", "reason": verdict.get("reason") or "Generated illustration rejected"}
    return candidate, {"source": "generated", "reason": verdict.get("reason")}


# ---------- Chefredaktør ----------

def chief_review(draft, desk, evidence, hero, state, story_id, *, high_risk=False, after_scan=False):
    model = CONFIG["models"]["chief_high_risk"] if high_risk else CONFIG["models"]["chief_normal"]
    instructions = """Du er Chefredaktør på Morgentidende med endelig publiceringsmyndighed. Du skal minimere unødige AI-kald ved SELV at rette artiklen, også ved væsentlig omskrivning. Send ikke arbejdet tilbage til Journalisten.
Dine opgaver er: faktuel støtte; præcis attribution; relevant pluralisme; stærkt naturligt dansk; rubrik/manchet; Hero-relevans og rettighedsmetadata; kategori og artikeltype; endelig publiceringsbeslutning; forsideplacering i forhold til det kompakte Frontpage Snapshot; forsidebalance; næste redaktionelle behov; opfølgende artikler; story-package/Læs også-relationer; prioritering af åbne opfølgninger; undgå dubletter/overproduktion.
Hvis noget kan rettes ud fra de kilder du allerede har, RET DET SELV og returnér den komplette rettede artikel. Hvis der reelt mangler dokumentation/pluralisme, bestil højst to meget konkrete Scan-søgninger. Efter nye Scan-kilder skal du selv færdigskrive artiklen. DROP kun hvis historien ikke holder, er dublet, ikke kan dokumenteres eller er blevet irrelevant.
Media har allerede vurderet Hero-pixlerne; du får også Hero-billedet som sidste sikkerhedsnet.
Returnér KUN JSON:
{"decision":"publish"|"publish_with_edits"|"needs_scan"|"media_retry"|"drop","reason":"kort","article":null eller KOMPLET rettet article,"scan_requests":[{"query":"...","purpose":"..."}],"frontpage_role":"lead"|"top_story"|"important_followup"|"normal"|"magazine"|"section_only","followup_needs":["kort behov"],"next_scan_requests":[{"query":"konkret søgning til næste artikel","purpose":"hvorfor forsiden/redaktionen mangler den"}],"media_search_terms":["kun hvis media_retry"]}.
Ved publish_with_edits SKAL article indeholde hele den rettede artikel. next_scan_requests er redaktionelle behov EFTER denne artikel og må gerne være tom."""
    payload = {
        "commission": desk,
        "article": draft,
        "sources": [{k: v for k, v in e.items() if k != "text"} | {"text_excerpt": str(e.get("text") or e.get("feed_description") or "")[:7000]} for e in evidence],
        "hero": {k: v for k, v in hero.items() if k not in {"_vision_src", "image_b64"}},
        "frontpage_snapshot": state.get("chief_snapshot") or {
            "active_lead": state.get("active_lead"), "top_stories": state.get("top_stories"),
            "coverage_last_24h": state.get("coverage_last_24h"), "active_packages": state.get("active_packages"),
        },
        "after_targeted_scan": bool(after_scan),
    }
    vision_src = hero.get("_vision_src") or hero.get("src")
    data, usage = call_json("chief_editor_after_scan" if after_scan else "chief_editor", model, instructions, payload,
                            story_id=story_id, max_output_tokens=2300, images=[vision_src] if vision_src else [],
                            reasoning="medium" if high_risk else "low")
    if data.get("decision") not in {"publish", "publish_with_edits", "needs_scan", "media_retry", "drop"}:
        raise RuntimeError("Chief returned invalid decision")
    if data.get("article"):
        data["article"] = normalize_draft(data["article"])
    data["usage"] = usage
    return data


def run_chief(draft, desk, evidence, hero, state, story_id, *, high_risk=False):
    first = chief_review(draft, desk, evidence, hero, state, story_id, high_risk=high_risk)
    if first["decision"] in {"publish", "publish_with_edits", "drop", "media_retry"}:
        return first, evidence
    extra = scan_for_requests(first.get("scan_requests"), story_id=story_id, requested_by="chief",
                              max_requests=int(CONFIG["limits"].get("max_chief_scan_requests", 2)))
    if not extra:
        return {**first, "decision": "drop", "reason": "Chefredaktør manglede dokumentation, og Scan fandt ingen brugbar kilde"}, evidence
    all_sources = (evidence + extra)[:int(CONFIG["limits"]["max_source_fetches"])]
    second = chief_review(first.get("article") or draft, desk, all_sources, hero, state, story_id,
                          high_risk=high_risk, after_scan=True)
    return second, all_sources


# ---------- Publish ----------

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
        path = ART_DIR / f"{slug}.json"
        n += 1
    source_path = SRC_DIR / f"{slug}.json"
    source_rows = []
    for i, e in enumerate(evidence, 1):
        source_rows.append({
            "id": f"S{i}", "name": e.get("publisher") or urllib.parse.urlparse(e.get("url", "")).netloc,
            "url": e.get("resolved_url") or e.get("url"), "discovery_url": e.get("url"),
            "headline": e.get("headline"), "published_at": e.get("published_at"), "fetched": bool(e.get("fetched")),
        })
    ledger = {
        "schema_version": 3, "story_id": story_id, "package_id": package_id, "generated_at": now_iso(),
        "sources": source_rows,
        "evidence_note": "Pipeline v3 stores provenance. One authoritative source can be enough; source sufficiency is editorial judgment, not a count gate.",
    }
    dump_json(source_path, ledger)
    related_rows = article_related(package_id)
    related = []
    for a in related_rows[:4]:
        im = a.get("image") or {}
        related.append({"slug": a["slug"], "category": a.get("category", "Nyhed"), "title": a.get("title", ""),
                        "teaser": a.get("standfirst", ""), "image_src": im.get("src"), "image_alt": im.get("alt", "")})
    related_news_slug = related_rows[0]["slug"] if related_rows else None
    clean_hero = {k: v for k, v in hero.items() if k not in {"_vision_src", "image_b64", "original_url"}}
    article = {
        "pipeline_version": 3, "status": "published", "release_requested": False,
        "story_id": story_id, "package_id": package_id, "slug": slug,
        "category": desk.get("category") if desk.get("category") in CONFIG["editorial"]["categories"] else "Nyhed",
        "weight": desk.get("weight") if desk.get("weight") in {"A", "B", "C", "D"} else "C",
        "article_type": desk.get("article_type") or "news",
        "frontpage_role": chief.get("frontpage_role") or desk.get("frontpage_intent") or "normal",
        "title": draft["title"], "standfirst": draft["standfirst"], "byline": "Morgentidende Redaktion",
        "published_at": now_iso(), "updated_at": None, "ledger": str(source_path.relative_to(ROOT)),
        "seo": {"title": draft["title"], "description": draft["standfirst"], "canonical": None},
        "image": {
            **clean_hero,
            "src": clean_hero.get("src"), "alt": clean_hero.get("alt") or draft["title"],
            "credit": clean_hero.get("credit") or "Morgentidende",
            "license": clean_hero.get("license") or ("Redaktionel illustration" if clean_hero.get("ai_generated") else ""),
            "source_url": clean_hero.get("source_url"),
            "image_type": clean_hero.get("image_type") or ("illustration" if clean_hero.get("ai_generated") else "photo"),
            "context_type": "editorial_illustration" if clean_hero.get("ai_generated") else "documentary",
            "caption": clean_hero.get("description") or "", "pending_image": False,
            "ai_generated": bool(clean_hero.get("ai_generated")), "placement": "lead",
        },
        "body": draft["body"], "topics": draft.get("topics") or [],
        "followup_needs": chief.get("followup_needs") or [],
        "next_scan_requests": chief.get("next_scan_requests") or [],
        "related_news_slug": related_news_slug, "related": related,
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
        backend("set_inbox_status", id=inbox["id"], status="completed", story_id=story_id,
                package_id=package_id, pipeline_run_id=RUN_ID)
    return article


# ---------- Cycle ----------

def cycle(cycle_no, report):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "v3_newsroom_state.py")], check=True)
    state = load_json(STATE, {}) or {}
    inventory = candidate_inventory(state)
    inbox_rows = pull_inbox()
    desk_model = CONFIG["models"]["desk"]
    desk_instructions = """Du er Desk på Morgentidende. Vælg højst ÉN konkret historie til næste artikel eller none. Du ser semantisk deduplikerede Scan-kandidater, Frontpage Snapshot og Publisher Inbox.
Vurder nyhedsværdi, aktualitet, konsekvens, dokumenterbarhed, originalitet, hvad forsiden allerede har og Chefredaktørens scan-brief. Dit job er at VÆLGE, ikke at researche eller skrive artiklen. selected_url er hovedkilden, som går direkte til Journalisten.
Morgentidendes særlige interesseområder kan påvirke spørgsmål og prioritering, aldrig fakta. Undgå dubletter og mekanisk kategorifyld.
Returnér KUN JSON: {"decision":"commission"|"none","selected_url":"https://..."|null,"inbox_id":"uuid"|null,"angle":"...","why_now":"...","category":"Nyhed|Indland|Krimi|Økonomi|Udland|Forbruger|Kultur|Videnskab|Sundhed|Parforhold|Sport|Guide|Feature|Historie|Kommentar|Penge|Videnskab & teknologi|Kultur & medier|Liv","weight":"A"|"B"|"C"|"D","article_type":"news"|"followup"|"background"|"analysis"|"feature","frontpage_intent":"lead"|"top_story"|"important_followup"|"normal"|"magazine"|"section_only","package_id":"eksisterende-id eller null","hero_search_terms":["..."],"risk_level":"normal"|"high"}."""
    desk_payload = {
        "editorial_line": CONFIG["editorial"],
        "frontpage_snapshot": state.get("chief_snapshot") or state,
        "scan_candidates": inventory,
        "publisher_inbox": inbox_rows,
    }
    desk, desk_usage = call_json("desk", desk_model, desk_instructions, desk_payload,
                                 max_output_tokens=700, reasoning="medium")
    report["stages"].append({"cycle": cycle_no, "stage": "desk", "model": desk_model,
                             "cost_dkk": round(desk_usage["dkk"], 4), "decision": desk.get("decision")})
    if desk.get("decision") != "commission":
        return {"status": "no_article", "reason": "desk_none"}

    inbox = next((r for r in inbox_rows if r.get("id") == desk.get("inbox_id")), None)
    seed = desk.get("selected_url") or (inbox.get("title") if inbox else desk.get("angle")) or f"cycle-{cycle_no}"
    story_id = f"v3-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{hashlib.sha1(str(seed).encode()).hexdigest()[:8]}"
    if inbox:
        backend("set_inbox_status", id=inbox["id"], status="commissioned", story_id=story_id, pipeline_run_id=RUN_ID)

    evidence = main_sources(desk, inventory, inbox)
    draft, evidence, journalist_status = run_journalist(desk, evidence, story_id)
    report["stages"].append({"cycle": cycle_no, "story_id": story_id, "stage": "journalist",
                             "model": CONFIG["models"]["journalist"], "status": journalist_status})
    if not draft:
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="parked", story_id=story_id, pipeline_run_id=RUN_ID)
        return {"status": "parked", "story_id": story_id, "reason": f"journalist:{journalist_status}"}

    hero, media_meta = media_choose(draft, desk, story_id)
    report["stages"].append({"cycle": cycle_no, "story_id": story_id, "stage": "media",
                             "model": CONFIG["models"]["media_vision"], "status": "approved" if hero else "rejected",
                             "source": media_meta.get("source"), "reason": media_meta.get("reason")})
    if not hero:
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="parked", story_id=story_id, pipeline_run_id=RUN_ID)
        return {"status": "parked", "story_id": story_id, "reason": "Media found no acceptable Hero"}

    high_risk = desk.get("risk_level") == "high" or desk.get("weight") == "A"
    chief, evidence = run_chief(draft, desk, evidence, hero, state, story_id, high_risk=high_risk)
    if chief.get("decision") == "media_retry":
        hero2, media_meta2 = media_choose(draft, desk, story_id, extra_terms=chief.get("media_search_terms") or [])
        if hero2:
            hero = hero2
            chief, evidence = run_chief(draft, desk, evidence, hero, state, story_id, high_risk=high_risk)
        else:
            chief = {**chief, "decision": "drop", "reason": media_meta2.get("reason") or "Media retry failed"}

    decision = chief.get("decision")
    if decision not in {"publish", "publish_with_edits"}:
        status = "dropped" if decision == "drop" else "parked"
        if inbox:
            backend("set_inbox_status", id=inbox["id"], status="rejected" if status == "dropped" else "parked",
                    story_id=story_id, pipeline_run_id=RUN_ID)
        report["stages"].append({"cycle": cycle_no, "story_id": story_id, "stage": "chief",
                                 "status": status, "decision": decision, "reason": str(chief.get("reason") or "")[:250]})
        return {"status": status, "story_id": story_id, "decision": decision}

    final_draft = chief.get("article") if decision == "publish_with_edits" and chief.get("article") else draft
    package_id = str(desk.get("package_id") or f"pkg-{slugify(desk.get('angle') or final_draft['title'])[:60]}")
    article = publish_article(desk, final_draft, evidence, hero, chief, story_id, package_id, inbox)
    report["stages"].append({"cycle": cycle_no, "story_id": story_id, "stage": "publish",
                             "status": "published", "slug": article["slug"], "frontpage_role": article["frontpage_role"]})
    subprocess.run([sys.executable, str(ROOT / "scripts" / "v3_newsroom_state.py")], check=True)
    return {"status": "published", "story_id": story_id, "slug": article["slug"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    args = ap.parse_args()
    cycles = max(1, min(int(CONFIG["limits"].get("max_cycles_per_run", 3)), args.cycles))
    report = {"schema_version": 3, "run_id": RUN_ID, "started_at": now_iso(),
              "cycles_requested": cycles, "results": [], "stages": []}
    report["cost_before"] = backend("cost_summary")
    for i in range(1, cycles + 1):
        try:
            result = cycle(i, report)
        except Exception as e:
            result = {"status": "error", "reason": str(e)[:500]}
        report["results"].append({"cycle": i, **result})
    report["finished_at"] = now_iso()
    report["cost_after"] = backend("cost_summary")
    dump_json(REPORT_ROOT / RUN_ID / "summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
