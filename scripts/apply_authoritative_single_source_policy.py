#!/usr/bin/env python3
"""Remove legacy support-passage gating and enforce the single-authoritative-source rule."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one regex match, found {count}")
    return out


def patch_editorial() -> None:
    path = ROOT / "cloudflare/newsdesk/src/editorial.js"
    s = path.read_text(encoding="utf-8")

    # Fact-check output no longer has a quote/passage sub-contract. Source indexes are
    # the evidence references; the deterministic gate decides whether one of them is authoritative.
    s = replace_once(
        s,
        '''      evidence: { type: "array", minItems: 1, maxItems: 8, items: { type: "object", properties: {\n        source_index: { type: "integer" }, quote: { type: "string" },\n      }, required: ["source_index", "quote"] } },\n      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },\n    }, required: ["id", "claim", "source_indexes", "evidence", "status", "notes"] } },''',
        '''      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },\n    }, required: ["id", "claim", "source_indexes", "status", "notes"] } },''',
        "factCheckSchema evidence",
    )

    # Remove the legacy passage-verification helper block entirely.
    s = regex_once(
        s,
        r'''function normalizedPassageText\(value\) \{.*?\n\}\nfunction verifiedSupportPassages\(claim, researched\) \{.*?\n\}\n\nasync function runResearch''',
        'async function runResearch',
        "legacy passage helper block",
    )

    old_system = '''  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. For HVER source_index du bruger som støtte skal evidence indeholde samme source_index og en KORT, ORDRET passage kopieret direkte fra den vedlagte excerpt, som faktisk dokumenterer netop claimet. Brug aldrig en kilde som støtte blot fordi den handler om samme historie. Hvis du ikke kan citere en konkret støttepassage, må source_index ikke bruges som evidens. Et claim kan få Verified på baggrund af én relevant autoritativ kilde, når en kort ordret støttepassage faktisk dokumenterer claimet. Autoritative kilder er: (1) store etablerede redaktionelle medier, (2) myndigheder/officielle kilder, (3) virksomheder, organisationer eller personer om egne forhold, (4) relevante forskere/fageksperter inden for deres fagområde og (5) forskningspapirer/original forskning. Originale bureaukilder som Reuters/AP/AFP/Ritzau er også autoritative. Kræv ikke automatisk kilde nr. 2 blot fordi kilden er et medie. Ved høj risiko, alvorlige beskyldninger eller fairness kan ekstra kontrol, attribution, forelæggelse eller Etik-review være nødvendig, men høj risiko skaber ikke i sig selv en mekanisk to-kilde-regel. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;'''
    new_system = '''  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Forsøg aktivt at falsificere hvert kandidat-claim mod de vedlagte kildetekster. Discovery-blogs og perspektiv/advocacy-feeds er fjernet før dette trin og må aldrig bruges som kilder. Angiv kun source_indexes for kilder, der faktisk dokumenterer claimet; brug aldrig en kilde som støtte blot fordi den handler om samme historie. Et claim kan få Verified på baggrund af én relevant autoritativ kilde. Autoritative kilder er: (1) store etablerede redaktionelle medier som BBC, Reuters, AP, Financial Times m.fl., (2) myndigheder/officielle kilder, (3) virksomheder, organisationer eller personer om egne forhold, (4) relevante forskere/fageksperter inden for deres fagområde og (5) forskningspapirer/original forskning. Originale bureaukilder som Reuters/AP/AFP/Ritzau er også autoritative. Kræv ikke automatisk kilde nr. 2, ekstra støttepassager eller andre sekundære evidensartefakter, når én relevant autoritativ kilde dokumenterer claimet. Ved høj risiko, alvorlige beskyldninger eller fairness kan ekstra kontrol, attribution, forelæggelse eller Etik-review være nødvendig, men høj risiko skaber ikke i sig selv en mekanisk to-kilde-regel. For alle materielle tal (døde, penge, procent, antal osv.) skal du aktivt sammenligne/falsificere tallet mod alle vedlagte relevante kilder; ved mismatch skal claimet være uncertain eller formuleres forsigtigt/attribueret, aldrig vælg automatisk det højeste tal. Rejected når evidensen modsiger claimet; ellers uncertain. Ét verificeret bærende claim er nok til en kort one-claim-artikel; usikre sekundære detaljer skal blot udelades. Opfind ingen nye kilder, fakta eller citater. Din overordnede publish/hold-vurdering er rådgivende; en deterministisk gate beregner den endelige beslutning efter claim-kontrollen.`;'''
    s = replace_once(s, old_system, new_system, "fact-check system prompt")

    s = regex_once(
        s,
        r'''  for \(const claim of fact\.claims\) \{\n    const requestedIndexes = .*?\n  \}\n  const verified = fact\.claims\.filter''',
        '''  for (const claim of fact.claims) {\n    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];\n    claim.source_indexes = indexes;\n    const evidence = indexes.map((i) => fact.researched[i]).filter(isEvidenceSource);\n    claim.numeric_material = numericMaterialClaim(claim);\n    claim.named_accused_primary_required = namedAccusedCrimeClaim(assignment, claim);\n    if (claim.status === "verified" && (!indexes.length || !evidenceRulePass(assignment, research, claim, evidence))) {\n      claim.status = "uncertain";\n      claim.notes = `${claim.notes || ""} Nedgraderet af deterministisk gate: claimet mangler en relevant autoritativ kilde.`.trim();\n    }\n  }\n  const verified = fact.claims.filter''',
        "fact-check deterministic gate",
    )

    s = replace_once(
        s,
        '''    const support_passages = (c.support_passages || []).map((x) => ({ source_id: sources[x.source_index]?.id, quote: x.quote, match_verified: x.match_verified === true })).filter((x) => x.source_id && ids.includes(x.source_id));\n    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, support_passages, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };''',
        '''    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id && !s.discovery_only)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };''',
        "ledger support_passages",
    )
    s = replace_once(
        s,
        '''    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; hvert publiceret claim har mindst én maskinverificeret støttepassage, og discovery-only-kilder kan ikke verificere claims."] },''',
        '''    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; hvert publiceret claim har mindst én relevant autoritativ kilde, og discovery-only-kilder kan ikke verificere claims."] },''',
        "ledger fact_check note",
    )
    path.write_text(s, encoding="utf-8")


def patch_evidence_policy() -> None:
    path = ROOT / "scripts/evidence_policy.py"
    s = path.read_text(encoding="utf-8")
    s = regex_once(
        s,
        r'''def supporting_source_ids\(ledger: dict, claim: dict\) -> list\[str\]:\n.*?\n\n\ndef claim_has_required_support''',
        '''def supporting_source_ids(ledger: dict, claim: dict) -> list[str]:\n    # Canonical rule: source_ids are the evidence references. No separate passage\n    # object may veto an otherwise relevant authoritative source.\n    return list(claim.get("source_ids", []))\n\n\ndef claim_has_required_support''',
        "supporting_source_ids",
    )
    path.write_text(s, encoding="utf-8")


def patch_source_gate() -> None:
    path = ROOT / "scripts/source_independence_gate.py"
    s = path.read_text(encoding="utf-8")
    s = s.replace(
        "It applies the locked house rule: one relevant authoritative source plus a\nverified support passage. Discovery-only cannot verify a claim.",
        "It applies the locked house rule: one relevant authoritative source is enough.\nDiscovery-only cannot verify a claim.",
    )
    path.write_text(s, encoding="utf-8")


def remove_legacy_test() -> None:
    path = ROOT / "scripts/claim_passage_contract_test.py"
    if path.exists():
        path.unlink()


def remove_support_passages_from_json() -> None:
    # Existing ledgers must not preserve a field whose semantics no longer exist.
    for path in ROOT.rglob("*.json"):
        if ".git" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        changed = False
        def walk(value):
            nonlocal changed
            if isinstance(value, dict):
                if "support_passages" in value:
                    del value["support_passages"]
                    changed = True
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(data)
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_clean() -> None:
    checks = ["support_passages", "support passage", "støttepassage", "støttepassager"]
    for needle in checks:
        proc = subprocess.run(
            ["git", "grep", "-n", "-i", needle, "--", ":(exclude)scripts/apply_authoritative_single_source_policy.py"],
            cwd=ROOT, text=True, capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            raise SystemExit(f"Legacy passage requirement remains for {needle!r}:\n{proc.stdout}")


if __name__ == "__main__":
    patch_editorial()
    patch_evidence_policy()
    patch_source_gate()
    remove_legacy_test()
    remove_support_passages_from_json()
    assert_clean()
    print("AUTHORITATIVE SINGLE-SOURCE POLICY: APPLIED")
