#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

POLICY = r'''#!/usr/bin/env python3
"""Canonical deterministic evidence policy shared by repository gates.

The Cloudflare Worker mirrors these rules and parity fixtures guard drift.
"""
from __future__ import annotations
import re

PRIMARY_TYPES = {"primary", "paper", "interview"}
HIGH_RISK = re.compile(r"\b(sigtet|tiltalt|anklag|mistænkt|voldtægt|seksual|misbrug|selvmord|mindreår|barn|børn|privat helbred|diagnose|terror|drab|korruption|svindel|hvidvask|overgreb|racist|ekstremist)\b", re.I)
ACCUSED = re.compile(r"\b(sigtet|tiltalt|mistænkt|anklaget)\b", re.I)
NAMED = re.compile(r"\b[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\s+[A-ZÆØÅ][a-zæøåéèáàíìóòúù-]+\b")
WIRES = ("reuters", "associated press", "apnews", "agence france-presse", "afp", "ritzau")


def authoritative_primary(source: dict | None) -> bool:
    return bool(source and source.get("type") in PRIMARY_TYPES and str(source.get("authoritative_for") or "").strip())


def original_wire(source: dict | None) -> bool:
    if not source:
        return False
    if str(source.get("wire_origin") or "").strip():
        return True
    group = str(source.get("source_group") or "").lower()
    return group.startswith("wire-")


def evidence_atom(source: dict | None) -> str:
    if not source:
        return ""
    if authoritative_primary(source):
        record = str(source.get("primary_record") or source.get("url") or source.get("source_group") or "primary").strip()
        return "primary:" + record
    wire = str(source.get("wire_origin") or "").strip().lower()
    if wire:
        return "wire:" + wire
    cluster = str(source.get("provenance_cluster") or "").strip()
    if cluster:
        return "cluster:" + cluster
    root = str(source.get("publisher_root") or source.get("source_group") or "").strip().lower()
    return "publisher:" + root if root else ""


def high_risk(article: dict, ledger: dict, claim: dict) -> bool:
    if (ledger.get("right_of_reply") or {}).get("required"):
        return True
    text = " ".join(str(x or "") for x in (article.get("title"), article.get("standfirst"), claim.get("claim")))
    return bool(HIGH_RISK.search(text))


def named_accused(claim: dict) -> bool:
    text = str(claim.get("claim") or "")
    return bool(ACCUSED.search(text) and NAMED.search(text))


def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:
    rows = [sources.get(sid) for sid in claim.get("source_ids", [])]
    rows = [s for s in rows if s]
    primary_ok = any(authoritative_primary(s) for s in rows)
    if named_accused(claim):
        return primary_ok
    atoms = {evidence_atom(s) for s in rows if evidence_atom(s)}
    if high_risk(article, ledger, claim):
        return primary_ok or len(atoms) >= 2
    return primary_ok or any(original_wire(s) for s in rows) or len(atoms) >= 2
'''
(ROOT / 'scripts' / 'evidence_policy.py').write_text(POLICY, encoding='utf-8')

# quality_gate.py: canonical helper + ready enforcement.
p = ROOT / 'scripts' / 'quality_gate.py'
s = p.read_text(encoding='utf-8')
if 'from evidence_policy import claim_has_required_support as evidence_claim_has_required_support' not in s:
    s = s.replace('from pathlib import Path\n', 'from pathlib import Path\nfrom evidence_policy import claim_has_required_support as evidence_claim_has_required_support\n', 1)
start = s.index('def claim_has_required_support(')
end = s.index('\n\ndef validate_article', start)
s = s[:start] + '''def claim_has_required_support(article: dict, ledger: dict, claim: dict, sources: dict[str, dict]) -> bool:\n    return evidence_claim_has_required_support(article, ledger, claim, sources)\n''' + s[end:]
s = s.replace('if article.get("status") in {"scheduled","published"} and claim.get("status")!="verified"', 'if article.get("status") in {"ready","scheduled","published"} and claim.get("status")!="verified"')
s = s.replace('if article.get("status") in {"scheduled","published"}:\n            for sid', 'if article.get("status") in {"ready","scheduled","published"}:\n            for sid')
s = s.replace('if article.get("status") in {"scheduled","published"} and not claim_has_required_support(claim,sources):', 'if article.get("status") in {"ready","scheduled","published"} and not claim_has_required_support(article,ledger,claim,sources):')
p.write_text(s, encoding='utf-8')

# source_independence_gate.py: use exactly the canonical helper.
p = ROOT / 'scripts' / 'source_independence_gate.py'
p.write_text(r'''#!/usr/bin/env python3
"""Hard gate against fake source plurality using the canonical evidence policy."""
from __future__ import annotations
import json, sys
from pathlib import Path
from evidence_policy import claim_has_required_support
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'content'/'articles'; ERR=[]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 for p in sorted(ART.glob('*.json')):
  if p.name.startswith('_'): continue
  try: a=load(p)
  except Exception: continue
  if a.get('pipeline_version')!=2 or a.get('status') not in {'ready','scheduled','published'}: continue
  if str(a.get('category')) in {'Guide','Kommentar'}: continue
  lp=ROOT/str(a.get('ledger') or '')
  if not lp.exists(): continue
  l=load(lp); sources={s.get('id'):s for s in l.get('sources') or [] if s.get('id')}
  sweep=l.get('coverage_sweep') or {}; ids=sweep.get('editorial_source_ids') or []
  groups={str(sources.get(i,{}).get('source_group') or '') for i in ids}; groups.discard('')
  if sweep.get('status')=='pass' and not groups: ERR.append(f'{p.name}: coverage PASS kræver mindst én reel dokumentationskilde')
  claims={c.get('id'):c for c in l.get('claims') or [] if c.get('id')}
  for cid in a.get('claim_ids') or []:
   c=claims.get(cid)
   if c and not claim_has_required_support(a,l,c,sources): ERR.append(f'{p.name}: claim {cid} mangler gyldig støtte efter canonical evidence policy')
 if ERR:
  print('SOURCE INDEPENDENCE: FAIL'); [print('-',x) for x in ERR]; return 1
 print('SOURCE INDEPENDENCE: PASS'); return 0
if __name__=='__main__': sys.exit(main())
''', encoding='utf-8')

# Worker policy alignment.
p = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
s = p.read_text(encoding='utf-8')
# wire provenance must be structural, never body substring.
s = re.sub(r'''function wireOrigin\(item\) \{[\s\S]*?\n\}\nfunction evidenceSourceGroup\(item\) \{[\s\S]*?\n\}''', r'''function wireOrigin(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const source = String(item?.source || "").toLowerCase().trim();
  if (host === "reuters.com" || host.endsWith(".reuters.com") || source === "reuters" || source === "thomson reuters") return "reuters";
  if (host === "apnews.com" || host.endsWith(".apnews.com") || ["ap", "associated press", "ap news"].includes(source)) return "ap";
  if (["afp", "agence france-presse"].includes(source)) return "afp";
  if (["ritzau", "ritzau bureau"].includes(source)) return "ritzau";
  return null;
}
function evidenceSourceGroup(item) {
  return sourceGroup(item?.source, item?.final_url || item?.url);
}
function provenanceClusters(items) {
  const clusters = [];
  for (let i = 0; i < items.length; i++) {
    let cluster = null;
    for (let j = 0; j < i; j++) {
      const a = `${items[i]?.headline || ""} ${items[i]?.excerpt || items[i]?.description || ""}`;
      const b = `${items[j]?.headline || ""} ${items[j]?.excerpt || items[j]?.description || ""}`;
      if (lexicalSimilarity(a, b) >= 0.90) { cluster = clusters[j]; break; }
    }
    clusters[i] = cluster || `pc-${i + 1}`;
  }
  return clusters;
}
function evidenceAtom(item) {
  if (authoritativePrimary(item)) return `primary:${item?.final_url || item?.url || evidenceSourceGroup(item)}`;
  const wire = wireOrigin(item); if (wire) return `wire:${wire}`;
  if (item?.provenance_cluster) return `cluster:${item.provenance_cluster}`;
  return `publisher:${evidenceSourceGroup(item)}`;
}''', s, count=1)

old = '''function evidenceRulePass(assignment, research, claim, evidence) {
  const primaryOk = evidence.some(authoritativePrimary);
  if (namedAccusedCrimeClaim(assignment, claim)) return primaryOk;
  const wireOk = evidence.some(authoritativeEditorial);
  const independent = new Set(evidence.map(evidenceSourceGroup));
  // Keep runtime approval aligned with repository quality gates: one ordinary
  // editorial publication is not independent corroboration. A competent primary
  // source or original wire may stand alone; otherwise require two publisher groups.
  if (primaryOk || wireOk || independent.size >= 2) return true;
  return false;
}'''
new = '''function evidenceRulePass(assignment, research, claim, evidence) {
  const primaryOk = evidence.some(authoritativePrimary);
  if (namedAccusedCrimeClaim(assignment, claim)) return primaryOk;
  const wireOk = evidence.some(authoritativeEditorial);
  const atoms = new Set(evidence.map(evidenceAtom).filter(Boolean));
  if (highRiskFactClaim(assignment, research, claim)) return primaryOk || atoms.size >= 2;
  return primaryOk || wireOk || atoms.size >= 2;
}'''
if old not in s: raise SystemExit('Worker evidenceRulePass anchor missing')
s = s.replace(old, new, 1)

s = s.replace('For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én original bureaukilde (Reuters/AP/AFP/Ritzau), én stærk original redaktionel kilde som BBC, DR, TV 2, SVT, NRK, Financial Times eller Politico ved tydelig attribution, eller to uafhængige troværdige kilder.', 'For almindelige lavrisiko-fakta kan Verified bæres af én autoritativ primærkilde inden for dens kompetenceområde, én dokumenteret original bureaukilde (Reuters/AP/AFP/Ritzau), eller to provenance-uafhængige troværdige evidenskilder. Ét almindeligt redaktionelt medie kan ikke stå alene. Ved højrisiko kræves primærkilde eller mindst to provenance-uafhængige evidenskilder.')

# Add provenance fields to publication ledger and align note.
old = '''  const sources = dossier.researched.filter(isEvidenceSource).map((s, i) => {
    const url = s.final_url || s.url;
    const primary = s.source_kind === "primary" && !s.discovery_only;
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: evidenceSourceGroup(s), authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };
  });'''
new = '''  const evidenceRows = dossier.researched.filter(isEvidenceSource);
  const clusters = provenanceClusters(evidenceRows);
  const sources = evidenceRows.map((s, i) => {
    const url = s.final_url || s.url;
    const primary = s.source_kind === "primary" && !s.discovery_only;
    const publisher = evidenceSourceGroup(s);
    const wire = wireOrigin(s);
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: publisher, publisher_root: publisher.replace(/^host-/, ""), wire_origin: wire, provenance_type: primary ? "primary_record" : wire ? "wire_original" : "reporting", provenance_cluster: clusters[i], primary_record: primary ? url : null, authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };
  });'''
if old not in s: raise SystemExit('makeLedger source anchor missing')
s = s.replace(old, new, 1)
s = s.replace('For lavrisiko-fakta kan en autoritativ primærkilde, original bureaukilde eller stærk original redaktionel kilde være nok; ellers bruges to uafhængige kilder. Højrisiko/fairness behandles strengere.', 'Lavrisiko kræver autoritativ primærkilde, dokumenteret original bureaukilde eller to provenance-uafhængige evidenskilder. Højrisiko kræver primærkilde eller to provenance-uafhængige evidenskilder.')
p.write_text(s, encoding='utf-8')

# Golden self-test for canonical Python policy.
(ROOT / 'scripts' / 'evidence_policy_selftest.py').write_text(r'''#!/usr/bin/env python3
from evidence_policy import claim_has_required_support

def src(id, group, **kw):
 d={'id':id,'source_group':group,'publisher_root':group.replace('host-',''),'type':'news','authoritative_for':'x'}; d.update(kw); return d

def check(label, want, article, ledger, claim, rows):
 got=claim_has_required_support(article, ledger, claim, {x['id']:x for x in rows})
 if got != want: raise SystemExit(f'{label}: expected {want}, got {got}')

a={'title':'Lav risiko','standfirst':''}; l={'right_of_reply':{'required':False}}
check('one ordinary outlet fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1']},[src('S1','host-theguardian-com')])
check('two publishers pass',True,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-theguardian-com'),src('S2','host-bbc-com')])
check('same provenance cluster fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-theguardian-com',provenance_cluster='pc-x'),src('S2','host-bbc-com',provenance_cluster='pc-x')])
check('wire low risk passes',True,a,l,{'claim':'En almindelig oplysning','source_ids':['S1']},[src('S1','host-reuters-com',wire_origin='reuters')])
h={'title':'Mistænkt for drab','standfirst':''}
check('wire high risk alone fails',False,h,l,{'claim':'En person er mistænkt for drab','source_ids':['S1']},[src('S1','host-reuters-com',wire_origin='reuters')])
check('primary high risk passes',True,h,l,{'claim':'En person er mistænkt for drab','source_ids':['S1']},[src('S1','host-politi-dk',type='primary',primary_record='https://politi.dk/x')])
print('EVIDENCE POLICY SELFTEST: PASS')
''', encoding='utf-8')

print('Evidence architecture migration applied')
