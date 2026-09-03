from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')
anchor = 'async function runResearch(env, assignment, selected) {'

helper = r'''
function decodeSearchText(value) {
  return stripHtml(String(value || "").replace(/<!\[CDATA\[|\]\]>/g, " ")).trim();
}
function targetedResearchQueries(assignment) {
  const clean = (value, limit = 10) => [...new Set(words(value))].slice(0, limit).join(" ");
  const title = clean(assignment?.title_hint || "", 10);
  const question = clean(assignment?.core_question || "", 10);
  return [...new Set([title, question, clean(`${assignment?.title_hint || ""} ${assignment?.core_question || ""}`, 12)].filter((x) => x.length >= 4))].slice(0, 2);
}
function unwrapDuckDuckGoUrl(value) {
  try {
    const u = new URL(value, "https://duckduckgo.com");
    const encoded = u.searchParams.get("uddg");
    if (encoded) return decodeURIComponent(encoded);
    return u.href;
  } catch (_) { return null; }
}
async function googleNewsSearch(query) {
  const out = [];
  try {
    const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en&gl=US&ceid=US:en`;
    const res = await fetch(url, { headers: { "user-agent": "MorgentidendeResearch/1.3" }, cf: { cacheTtl: 300, cacheEverything: true } });
    if (!res.ok) return out;
    const xml = await res.text();
    for (const match of xml.matchAll(/<item>[\s\S]*?<title>([\s\S]*?)<\/title>[\s\S]*?<link>([\s\S]*?)<\/link>[\s\S]*?<\/item>/gi)) {
      const headline = decodeSearchText(match[1]);
      const link = decodeSearchText(match[2]);
      if (!/^https?:\/\//i.test(link)) continue;
      out.push({ url: link, headline, description: "", source: "Google News search", source_class: "targeted_web", discovery_only: false });
      if (out.length >= 6) break;
    }
  } catch (_) {}
  return out;
}
async function duckDuckGoSearch(query) {
  const out = [];
  try {
    const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0 MorgentidendeResearch/1.3" } });
    if (!res.ok) return out;
    const html = await res.text();
    const re = /<a[^>]+class=["'][^"']*result__a[^"']*["'][^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
    for (const match of html.matchAll(re)) {
      const link = unwrapDuckDuckGoUrl(match[1]);
      if (!link || !/^https?:\/\//i.test(link) || isUtilityOrAccountUrl(link)) continue;
      out.push({ url: link, headline: decodeSearchText(match[2]), description: "", source: hostOf(link) || "web-search", source_class: "targeted_web", discovery_only: false });
      if (out.length >= 6) break;
    }
  } catch (_) {}
  return out;
}
async function targetedResearchWebSearch(assignment) {
  const queries = targetedResearchQueries(assignment);
  if (!queries.length) return [];
  const batches = [];
  for (const query of queries) batches.push(googleNewsSearch(query), duckDuckGoSearch(query));
  const results = (await Promise.all(batches)).flat();
  const seen = new Set();
  const out = [];
  for (const item of results) {
    const key = item.url?.replace(/[?#].*$/, "");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    const kind = trustedExpansionKind(item.url);
    out.push({
      ...item,
      source_kind: kind === "primary" ? "primary" : kind === "public_media" ? "strong_editorial" : "news",
      targeted_search: true,
    });
    if (out.length >= 8) break;
  }
  return out;
}

'''

if 'async function targetedResearchWebSearch(' not in s:
    if anchor not in s:
        raise SystemExit('runResearch anchor missing')
    s = s.replace(anchor, helper + anchor, 1)

old = '''  if (!evidenceUsable.length) {
    return { decision: "watch", rationale: "Ingen brugbar dokumentationskilde kunne hentes endnu", researched, candidate_claims: [], contradictions: [], right_of_reply_required: false, conflict_present: false };
  }
'''
new = '''  // Research always supplements the start source/link expansion with a fresh,
  // independent targeted web search. Search results still have to be fetched and
  // pass the existing evidence-source rules; this is discovery, not a new gate.
  const searchedCandidates = await targetedResearchWebSearch(assignment);
  if (searchedCandidates.length) {
    const alreadySeen = new Set(usable.map((x) => (x.final_url || x.url || "").replace(/[?#].*$/, "")).filter(Boolean));
    const freshCandidates = searchedCandidates.filter((x) => {
      const key = (x.url || "").replace(/[?#].*$/, "");
      return key && !alreadySeen.has(key);
    }).slice(0, 4);
    if (freshCandidates.length) {
      const searched = await Promise.all(freshCandidates.map(fetchExcerpt));
      const normalized = searched.map((x) => ({ ...x, source_kind: normalizedSourceKind(x), targeted_search: true })).filter((x) => {
        const minChars = (authoritativePrimary(x) || strongEditorialSource(x)) ? 80 : 120;
        return (x.excerpt || "").length >= minChars;
      });
      usable = usable.concat(normalized);
      evidenceUsable = usable.filter(isEvidenceSource);
    }
  }

  if (!evidenceUsable.length) {
    return { decision: "watch", rationale: "Startkilde, relevante links og målrettet websøgning gav endnu ingen brugbar dokumentationskilde", researched, candidate_claims: [], contradictions: [], right_of_reply_required: false, conflict_present: false };
  }
'''

if old not in s:
    if 'Startkilde, relevante links og målrettet websøgning' not in s:
        raise SystemExit('watch anchor missing')
else:
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
