#!/usr/bin/env python3
"""Test exact changed and recent articles in addition to legacy live_qa."""
from __future__ import annotations
import argparse,json,subprocess,urllib.parse,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEFAULT_BASE="https://nickzen108.github.io/avisen/"
def parse(v):return datetime.fromisoformat(v.replace("Z","+00:00")).astimezone(timezone.utc)
def check(u):
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"MorgentidendeLiveQA/3.1"}),timeout=20) as r:b=r.read(2000000);s=r.status
  if s>=400:return f"HTTP {s} {u}"
  t=b.decode("utf-8",errors="replace")
  return f"template-marker {u}" if "{{" in t or "}}" in t else None
 except Exception as e:return f"FETCH {u}: {e}"
def live_url(base,path):
 rel=str(path).replace("\\","/")
 if rel.startswith("docs/"):rel=rel[len("docs/"):]
 return urllib.parse.urljoin(base,rel)
def main():
 p=argparse.ArgumentParser();p.add_argument("--target-sha");p.add_argument("--recent-hours",type=int,default=24);p.add_argument("--report",default="reports/qa/live-recent.md");p.add_argument("--base-url",default=DEFAULT_BASE);a=p.parse_args();base=a.base_url.rstrip("/")+"/";base_run=subprocess.run(["python","scripts/live_qa.py","--base-url",base,"--strict-internal","--report","/tmp/base-live.md"],cwd=ROOT);cut=datetime.now(timezone.utc)-timedelta(hours=a.recent_hours);urls=[]
 for f in (ROOT/"content"/"articles").glob("*.json"):
  if f.name.startswith("_"):continue
  try:
   x=json.loads(f.read_text(encoding="utf-8"))
   if x.get("status")=="published" and x.get("published_at") and parse(x["published_at"])>=cut:urls.append(live_url(base,f"artikler/{x['slug']}.html"))
  except Exception:pass
 if a.target_sha:
  out=subprocess.check_output(["git","diff-tree","--no-commit-id","--name-only","-r",a.target_sha,"--","docs/artikler"],cwd=ROOT,text=True)
  urls += [live_url(base,x) for x in out.splitlines() if x.endswith(".html")]
 faults=[e for u in dict.fromkeys(urls) if (e:=check(u))];rp=Path(a.report);rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text("# Recent/exact live QA\n\n"+("\n".join("- "+x for x in faults) if faults else "PASS")+"\n",encoding="utf-8");return 1 if base_run.returncode or faults else 0
if __name__=="__main__":raise SystemExit(main())
