#!/usr/bin/env python3
import json, os, time
from pathlib import Path
import requests

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
WORKER_URL = os.environ.get("V3_BAKEOFF_WORKER_URL", "").rstrip("/")
WORKER_TOKEN = os.environ.get("V3_BAKEOFF_TOKEN", "")
RUN_ID = os.environ.get("GITHUB_RUN_ID", str(int(time.time())))
OUT_DIR = Path("reports/v3-bakeoff") / RUN_ID
OUT_DIR.mkdir(parents=True, exist_ok=True)

WRITER_MODELS = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/openai/gpt-oss-20b",
    "@cf/zai-org/glm-5.3-flash",
]
EDITOR_MODELS = WRITER_MODELS + ["@cf/qwen/qwen3.8-27b"]
PRICING = {
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast": (0.293, 2.253),
    "@cf/zai-org/glm-4.7-flash": (0.060, 0.400),
    "@cf/qwen/qwen3-30b-a3b-fp8": (0.051, 0.340),
    "@cf/openai/gpt-oss-20b": (0.200, 0.300),
    "@cf/zai-org/glm-5.3-flash": (0.150, 0.500),
    "@cf/qwen/qwen3.8-27b": (0.450, 3.200),
}
WRITER_KEYS = ["fifa-uefa", "bodens-kommun", "sydkorea", "trump-administrationen", "vox-kraever", "reform-uk"]
EDITOR_KEYS = ["fifa-uefa", "bodens-kommun", "sydkorea", "ugyldigt-struktureret-svar", "entertainment-over-policy"]

def model_slug(model): return model.replace("@cf/", "").replace("/", "__")

def read_json(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception: return None

def find_by_key(folder, key):
    matches = sorted(Path(folder).glob(f"*{key}*.json"))
    return matches[-1] if matches else None

def build_writer_fixture(key):
    p = find_by_key("sources", key)
    if not p: return None
    d = read_json(p)
    if not d: return None
    sources = []
    for s in d.get("sources", [])[:3]:
        sources.append({"id":s.get("id"),"name":s.get("name"),"url":s.get("url"),"headline_or_scope":s.get("authoritative_for") or s.get("headline"),"publisher":s.get("publisher_name")})
    claims = [c for c in d.get("claims", []) if c.get("status") == "verified"][:10]
    return {"fixture":key,"source_file":str(p),"assignment":d.get("assignment", {}),"sources":sources,"verified_claims":[{"id":c.get("id"),"claim":c.get("claim"),"source_ids":c.get("source_ids", [])} for c in claims]}

def build_editor_fixture(key):
    p = find_by_key("content/articles", key)
    if not p: return None
    d = read_json(p)
    if not d: return None
    return {"fixture":key,"article_file":str(p),"title":d.get("title"),"standfirst":d.get("standfirst"),"body":d.get("body", []),"image":d.get("image"),"story_location":d.get("story_location"),"category":d.get("category")}

def extract_text(payload):
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        if isinstance(result.get("response"), str): return result["response"]
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            if isinstance(msg.get("content"), str): return msg["content"]
    if isinstance(result, str): return result
    return ""

def extract_usage(payload):
    result = payload.get("result") if isinstance(payload, dict) else None
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    inp = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
    out = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
    return int(inp), int(out)

def call(model, system, user, max_tokens=700):
    messages = [{"role":"system","content":system},{"role":"user","content":user}]
    started = time.time()
    try:
        if WORKER_URL:
            url = WORKER_URL + "/run"
            body = {"model":model,"messages":messages,"max_tokens":max_tokens,"temperature":0.2}
            headers = {"Authorization":f"Bearer {WORKER_TOKEN}","Content-Type":"application/json"}
        else:
            url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{model}"
            body = {"messages":messages,"max_tokens":max_tokens,"temperature":0.2}
            headers = {"Authorization":f"Bearer {API_TOKEN}","Content-Type":"application/json"}
        r = requests.post(url, headers=headers, json=body, timeout=180)
        elapsed = round(time.time()-started, 3)
        try: payload = r.json()
        except Exception: payload = {"raw":r.text[:5000]}
        text = extract_text(payload)
        inp, out = extract_usage(payload)
        pin, pout = PRICING.get(model, (0,0))
        cost = (inp/1_000_000)*pin + (out/1_000_000)*pout
        return {"ok":r.ok and bool(text),"http_status":r.status_code,"text":text,"usage":{"input_tokens":inp,"output_tokens":out,"estimated_usd":cost},"elapsed_s":elapsed,"raw":payload if not text else None}
    except Exception as e:
        return {"ok":False,"http_status":None,"text":"","usage":{"input_tokens":0,"output_tokens":0,"estimated_usd":0},"elapsed_s":round(time.time()-started,3),"error":str(e)}

writer_system = """Du er journalist på en seriøs dansk netavis. Skriv en kort nyhedsartikel på naturligt, idiomatisk dansk ud fra det dokumenterede materiale. Materialet kan indeholde dårligt oversatte danske formuleringer fra en tidligere pipeline; forstå betydningen og skriv den om på korrekt dansk i stedet for at kopiere sproglige fejl. Opfind ingen fakta. Bevar forbehold og attribution. Returnér kun: RUBRIK, MANCHET og BRØDTEKST."""
editor_system = """Du er en kræsen dansk chefredaktør. Vurder teksten som om den stod klar til publicering på en seriøs dansk avis. Find konkret: 1) ikke-naturligt eller forkert dansk, svensk/norsk/engelsk læk og ordrette maskinoversættelser, 2) uklare eller faktuelt risikable formuleringer/attribution, 3) om hero-billedet faktisk er relevant for historien og ikke bare lovligt, 4) øvrige alvorlige redaktionelle fejl. Små stilpræferencer er ikke blockers. Afslut med præcis én beslutning: PUBLISH, REVISE eller DROP. Ved REVISE skal du citere de konkrete problemsteder og foreslå naturlig dansk rettelse."""
desk_system = """Du er vagthavende Desk Editor på Morgentidende. Vælg den næste historie ud fra nyhedsværdi, aktualitet, betydning, dokumentation, eksisterende dækning og åbne opfølgningsbehov. Undgå mekanisk kategori-fyld. Det er tilladt at vælge INGEN. Returnér VALG og en kort BEGRUNDELSE."""

writer_fixtures = [x for x in (build_writer_fixture(k) for k in WRITER_KEYS) if x]
editor_fixtures = [x for x in (build_editor_fixture(k) for k in EDITOR_KEYS) if x]
results = {"schema_version":1,"run_id":RUN_ID,"writer_fixtures":[x["fixture"] for x in writer_fixtures],"editor_fixtures":[x["fixture"] for x in editor_fixtures],"writer":[],"editor":[],"desk":[]}

for model in WRITER_MODELS:
    for fx in writer_fixtures:
        res = call(model, writer_system, json.dumps(fx, ensure_ascii=False), 750)
        row = {"model":model,"fixture":fx["fixture"],**res}; results["writer"].append(row)
        (OUT_DIR/f"writer__{model_slug(model)}__{fx['fixture']}.json").write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("WRITER",model,fx["fixture"],res["ok"],res["http_status"],res["usage"])

for model in EDITOR_MODELS:
    for fx in editor_fixtures:
        res = call(model, editor_system, json.dumps(fx, ensure_ascii=False), 700)
        row = {"model":model,"fixture":fx["fixture"],**res}; results["editor"].append(row)
        (OUT_DIR/f"editor__{model_slug(model)}__{fx['fixture']}.json").write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("EDITOR",model,fx["fixture"],res["ok"],res["http_status"],res["usage"])

desk_payload = {"current_frontpage_note":"Antag at ingen af disse historier allerede er dækket. Vælg kun efter redaktionel værdi.","candidates":writer_fixtures}
for model in WRITER_MODELS:
    res = call(model, desk_system, json.dumps(desk_payload, ensure_ascii=False), 350)
    row = {"model":model,**res}; results["desk"].append(row)
    (OUT_DIR/f"desk__{model_slug(model)}.json").write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DESK",model,res["ok"],res["http_status"],res["usage"])

summary = {}
for section in ("writer","editor","desk"):
    by = {}
    for r in results[section]:
        b = by.setdefault(r["model"],{"calls":0,"success":0,"input_tokens":0,"output_tokens":0,"estimated_usd":0.0,"elapsed_s":0.0})
        b["calls"] += 1; b["success"] += int(bool(r.get("ok"))); b["input_tokens"] += r.get("usage",{}).get("input_tokens",0); b["output_tokens"] += r.get("usage",{}).get("output_tokens",0); b["estimated_usd"] += r.get("usage",{}).get("estimated_usd",0.0); b["elapsed_s"] += r.get("elapsed_s",0.0)
    for b in by.values(): b["estimated_usd"] = round(b["estimated_usd"],6); b["elapsed_s"] = round(b["elapsed_s"],2)
    summary[section] = by
results["summary"] = summary
(OUT_DIR/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(OUT_DIR/"summary.json").write_text(json.dumps({"run_id":RUN_ID,"fixtures":{"writer":results["writer_fixtures"],"editor":results["editor_fixtures"]},"summary":summary},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
