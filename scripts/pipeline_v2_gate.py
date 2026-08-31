#!/usr/bin/env python3
"""Additional machine-enforced gates for Morgentidende pipeline v2."""
from __future__ import annotations
import argparse,copy,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ERRORS=[]
PUB={"status","published_at","updated_at","scheduled_for","released_from_schedule_at","release_requested","publication","manual_review_completed","workflow_state"}
def err(x): ERRORS.append(x)
def load(p):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as e:err(f"{p}: JSON-fejl {e}");return None
def time(v,l):
 try:
  d=datetime.fromisoformat(v.replace("Z","+00:00"));
  if d.tzinfo is None:raise ValueError("timezone mangler")
  return d.astimezone(timezone.utc)
 except Exception as e:err(f"{l}: ugyldigt timestamp {v!r}: {e}");return None
def snap(a):
 x=copy.deepcopy(a)
 for k in PUB:x.pop(k,None)
 return x
def coverage(name,a,l,s):
 c=l.get("coverage_sweep") or {};st=c.get("status")
 if st not in {"pass","limited","not_required"}:err(f"{name}: coverage_sweep.status ugyldig");return
 groups=set()
 for sid in c.get("editorial_source_ids") or []:
  src=s.get(sid)
  if not src:err(f"{name}: ukendt coverage source {sid}");continue
  g=str(src.get("source_group") or "").strip()
  if not g:err(f"{name}: coverage source {sid} mangler source_group")
  else:groups.add(g)
 declared={str(x).strip() for x in c.get("independent_source_groups",[]) if str(x).strip()}
 if declared and declared!=groups:err(f"{name}: coverage source-groups matcher ikke sources")
 if st=="pass" and len(groups)<3:err(f"{name}: coverage PASS kræver mindst 3 uafhængige source-groups")
 if st=="limited" and not str(c.get("limitations") or "").strip():err(f"{name}: limited coverage kræver begrundelse")
 if st=="not_required":
  article_type=str(a.get("format") or a.get("genre") or a.get("category") or "")
  if article_type not in {"Guide","Kommentar"}:err(f"{name}: not_required coverage kun tilladt for Guide/Kommentar")
  if not str(c.get("limitations") or "").strip():err(f"{name}: not_required kræver begrundelse")
def ror(name,l):
 r=l.get("right_of_reply") or {}
 if not r.get("required"):return
 if not str(r.get("party") or "").strip():err(f"{name}: right_of_reply party mangler")
 if str(r.get("exception") or "").strip():return
 if not r.get("contacted_at"):err(f"{name}: forelæggelse contacted_at mangler")
 else:time(r["contacted_at"],f"{name}.contacted_at")
 if not r.get("deadline"):err(f"{name}: forelæggelse deadline mangler");return
 d=time(r["deadline"],f"{name}.deadline")
 if d and not r.get("response") and d>datetime.now(timezone.utc):err(f"{name}: forelæggelsesfrist ikke udløbet og svar mangler")
def approval(path,a):
 ap=ROOT/"reports"/"editorial"/"approvals"/f"{a['slug']}.json"
 if not ap.exists():err(f"{path.name}: final approval mangler");return
 x=load(ap)
 if not x:return
 if x.get("schema_version")!=1 or x.get("status")!="pass":err(f"{path.name}: final approval schema/status ugyldig")
 if x.get("story_id")!=a.get("story_id") or x.get("article_slug")!=a.get("slug"):err(f"{path.name}: approval story/slug mismatch")
 for g in ["language","ethics","image","seo","final_editor"]:
  if (x.get("gates") or {}).get(g)!="pass":err(f"{path.name}: approval gate {g} ikke pass")
 if not x.get("checked_at"):err(f"{path.name}: approval checked_at mangler")
 else:time(x["checked_at"],f"{path.name}.approval.checked_at")
 if x.get("editorial_snapshot")!=snap(a):err(f"{path.name}: redaktionelt indhold ændret efter final approval")
def article(path):
 a=load(path)
 if not a or path.name.startswith("_") or a.get("pipeline_version")!=2 or a.get("status") not in {"ready","scheduled","published"}:return
 if a.get("manual_review") and not a.get("manual_review_completed"):err(f"{path.name}: manual_review er ikke afsluttet")
 lp=ROOT/str(a.get("ledger",""))
 if not lp.exists():err(f"{path.name}: ledger mangler");return
 l=load(lp)
 if not l:return
 sm={s.get("id"):s for s in l.get("sources",[]) if s.get("id")};coverage(path.name,a,l,sm);ror(path.name,l)
 f=l.get("fact_check") or {};d=l.get("desk_recheck") or {}
 if f.get("status")!="pass" or not f.get("checked_at"):err(f"{path.name}: fact_check pass+checked_at kræves")
 if d.get("status") not in {"publish","update"} or not d.get("checked_at") or not str(d.get("rationale") or "").strip():err(f"{path.name}: desk_recheck publish|update + tidspunkt + rationale kræves")
 approval(path,a)
 if a.get("status")=="ready" and not isinstance(a.get("release_requested"),bool):err(f"{path.name}: release_requested skal være bool")
def frontpage():
 s=load(ROOT/"content"/"frontpage.json")
 if not s:return
 arts={}
 for p in (ROOT/"content"/"articles").glob("*.json"):
  if p.name.startswith("_"):continue
  a=load(p)
  if a and a.get("slug"):arts[a["slug"]]=a
 for i in [s.get("ticker",{}),s.get("lead",{}),*s.get("rail",[]),*s.get("stack",[]),*s.get("narrow",[])]:
  slug=i.get("slug")
  if not slug:err("frontpage item mangler slug");continue
  a=arts.get(slug)
  if a and a.get("pipeline_version")==2:
   if a.get("status")!="published":err(f"frontpage v2-artikel er ikke published: {slug}")
   if set(i)-{"slug"}:err(f"frontpage v2-item {slug} må kun indeholde slug")
def corrections():
 p=ROOT/"content"/"corrections.json"
 if not p.exists():err("content/corrections.json mangler");return
 x=load(p)
 if not x:return
 if x.get("schema_version")!=1 or not isinstance(x.get("entries"),list):err("corrections schema ugyldigt");return
 for n,e in enumerate(x["entries"]):
  if e.get("type") not in {"clarification","correction","retraction"}:err(f"corrections[{n}] type ugyldig")
  for k in ["article_slug","timestamp","summary"]:
   if not str(e.get(k) or "").strip():err(f"corrections[{n}] mangler {k}")
  if e.get("timestamp"):time(e["timestamp"],f"corrections[{n}].timestamp")
def main():
 argparse.ArgumentParser().parse_args()
 for p in sorted((ROOT/"content"/"articles").glob("*.json")):article(p)
 frontpage();corrections()
 if ERRORS:
  print("PIPELINE V2 GATE: FAIL")
  for x in ERRORS:print("-",x)
  return 1
 print("PIPELINE V2 GATE: PASS");return 0
if __name__=="__main__":sys.exit(main())
