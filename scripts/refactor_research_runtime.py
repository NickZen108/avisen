#!/usr/bin/env python3
from pathlib import Path
import re

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')

# Research should be able to represent a genuinely simple one-claim story without inventing filler.
s = s.replace('decision: { type: "string", enum: ["continue", "watch", "hold"] }', 'decision: { type: "string", enum: ["continue", "watch"] }', 1)
s = s.replace('candidate_claims: { type: "array", minItems: 2, maxItems: 12, items:', 'candidate_claims: { type: "array", minItems: 1, maxItems: 8, items:', 1)
# Keep the next gate schema compatible with a one-claim research packet; Fact checker policy is optimized separately.
s = s.replace('claims: { type: "array", minItems: 2, maxItems: 12, items:', 'claims: { type: "array", minItems: 1, maxItems: 12, items:', 1)
s = s.replace('if (selected.length >= 6) break;', 'if (selected.length >= 5) break;', 1)

new_research = r'''async function runResearch(env, assignment, selected) {
  let researched = await Promise.all(selected.map(fetchExcerpt));
  let usable = researched.filter((x) => (x.excerpt || "").length >= 160);

  // Cheap deterministic expansion before spending AI: when the seed set lacks strong
  // corroboration, follow a few clearly trusted primary/public-media links already found
  // on the fetched pages. Discovery sources remain leads only, never evidence.
  let evidenceUsable = usable.filter(isEvidenceSource);
  if (!evidenceUsable.some(authoritativePrimary) || evidenceGroups(evidenceUsable).length < 2) {
    const seen = new Set(usable.map((x) => x.final_url || x.url).filter(Boolean));
    const links = [];
    for (const item of usable) {
      for (const link of item.outbound_links || []) {
        const kind = trustedExpansionKind(link.url);
        if (!kind || seen.has(link.url)) continue;
        seen.add(link.url);
        links.push({
          url: link.url,
          headline: link.text || item.headline || "Original source",
          description: "",
          source: hostOf(link.url) || "linked-source",
          source_kind: kind === "primary" ? "primary" : "news",
          source_class: kind,
          discovery_only: false,
        });
      }
    }
    links.sort((a, b) => Number(b.source_kind === "primary") - Number(a.source_kind === "primary"));
    if (links.length) {
      const expanded = await Promise.all(links.slice(0, 4).map(fetchExcerpt));
      usable = usable.concat(expanded.filter((x) => (x.excerpt || "").length >= 160));
      evidenceUsable = usable.filter(isEvidenceSource);
    }
  }

  // Research no longer rejects a promising story merely because corroboration is not
  // already present. Fact checker owns the evidence verdict. We stop only if there is
  // literally no usable evidence source after the cheap expansion attempt.
  if (!evidenceUsable.length) {
    return { decision: "watch", rationale: "Ingen brugbar dokumentationskilde kunne hentes endnu", researched: [] };
  }

  const unique = [];
  const seenUrls = new Set();
  const prioritized = [...evidenceUsable].sort((a, b) => Number(authoritativePrimary(b)) - Number(authoritativePrimary(a)));
  for (const item of prioritized) {
    const url = item.final_url || item.url;
    if (!url || seenUrls.has(url)) continue;
    seenUrls.add(url);
    unique.push(item);
    if (unique.length >= 5) break;
  }

  const sources = unique.map((item, i) => ({
    source_index: i,
    name: item.source,
    headline: item.headline,
    url: item.final_url || item.url,
    excerpt: item.excerpt.slice(0, 5000),
    discovery_only: false,
    source_kind: item.source_kind || "news",
  }));
  const system = `Du er Research på Morgentidende. Lav et kompakt evidens-kort til Fact checker; vurder ikke nyhedsværdi igen og fæld ikke den endelige sandhedsdom. Kortlæg 1-6 bærende kandidat-claims med præcise source_indexes. Notér kun reelle modsigelser, væsentlige forbehold og nødvendig kontekst. En primærkilde er værdifuld, men du skal ikke kræve et bestemt antal medier. Hvis mindst ét brugbart claim kan kildebelægges, vælg continue; watch kun hvis materialet reelt ikke giver noget kontrollerbart. Flag alvorlige belastende påstande via right_of_reply_required, men brug ikke flaget som stopregel. Opfind intet.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 850, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  research.researched = unique;
  research.source_payload = sources;
  return research;
}
'''

pattern = re.compile(r'async function runResearch\(env, assignment, selected\) \{.*?\n\}\n\nasync function runFactCheck', re.S)
if not pattern.search(s):
    raise SystemExit('runResearch block not found')
s = pattern.sub(new_research + '\nasync function runFactCheck', s, count=1)

old_recheck = '''async function deskRecheck(env, assignment, dossier) {
  const system = `Du er Nyhedsdesk ved et ultrakort recheck efter bestået Fact check. Genresearch ikke. Udgangspunktet er publish/update. Hold/kill kun ved en ny konkret redaktionel grund: historien er ikke længere aktuel/væsentlig eller dokumentationen ændrer selve nyhedskernen. Svar kort.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions }), deskRecheckSchema, 180, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}'''
new_recheck = '''async function deskRecheck(env, assignment, dossier) {
  // B-D stories were just accepted by Newsdesk and Fact checker; repeating that judgement
  // costs an extra model call without new information. Keep only a tiny A/breaking staleness check.
  if (assignment.weight !== "A") {
    return { decision: "publish", rationale: "Fact check bestået; intet særskilt A-recheck nødvendigt" };
  }
  const system = `Du er Nyhedsdesk ved et ultrakort A/breaking-recheck efter bestået Fact check. Genresearch ikke. Hold/kill kun hvis materialet viser, at nyhedskernen siden assignment er blevet materielt forældet eller har skiftet karakter. Ellers publish. Svar kort.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions }), deskRecheckSchema, 140, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}'''
if old_recheck not in s:
    raise SystemExit('deskRecheck block not found')
s = s.replace(old_recheck, new_recheck, 1)

p.write_text(s, encoding='utf-8')
print('Research runtime optimization applied')
