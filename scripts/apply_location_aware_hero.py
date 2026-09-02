#!/usr/bin/env python3
"""One-shot canonical Newsdesk migration: resolve story location before hero search.

New contract:
- first Newsdesk assignment identifies country/place/language before research/hero
- local-language, transliterated/alternate and English hero queries are generated there
- Commons searches all query languages and ranks all lawful candidates together
- documentary photo/context/map/satellite still outranks Flux pencil fallback
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / "cloudflare" / "newsdesk" / "src" / "editorial.js"


def replace_once(old: str, new: str, label: str) -> None:
    text = EDITORIAL.read_text(encoding="utf-8")
    if new in text:
        print(f"{label}: already applied")
        return
    if old not in text:
        raise SystemExit(f"{label}: expected anchor not found")
    EDITORIAL.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"{label}: applied")


# 1) Make location/language a required part of the birth assignment.
replace_once(
'''const assignmentSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["research", "watch", "drop"] }, title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES }, weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 3 },
    rationale: { type: "string" }, core_question: { type: "string" },
  }, required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question"],
};
''',
'''const assignmentSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["research", "watch", "drop"] }, title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES }, weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 3 },
    rationale: { type: "string" }, core_question: { type: "string" },
    story_location: { type: "object", properties: {
      country: { type: "string" }, country_code: { type: "string" },
      primary_language: { type: "string" }, primary_language_code: { type: "string" },
      place_names_local: { type: "array", maxItems: 6, items: { type: "string" } },
      place_names_english: { type: "array", maxItems: 6, items: { type: "string" } },
      transliterations: { type: "array", maxItems: 6, items: { type: "string" } },
      hero_queries_local: { type: "array", maxItems: 3, items: { type: "string" } },
      hero_queries_english: { type: "array", maxItems: 3, items: { type: "string" } },
      hero_queries_transliterated: { type: "array", maxItems: 3, items: { type: "string" } },
    }, required: ["country", "country_code", "primary_language", "primary_language_code", "place_names_local", "place_names_english", "transliterations", "hero_queries_local", "hero_queries_english", "hero_queries_transliterated"] },
  }, required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question", "story_location"],
};
''',
"assignment story_location schema",
)

# 2) Ask the first Newsdesk to determine location and multilingual media terms once,
# before downstream research and hero resolution.
replace_once(
'''  const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Svar ultrakort.`;
''',
'''  const system = `Du er Morgentidendes første Nyhedsdesk. Vælg ét konkret research-frø. RESEARCH er standard ved reel nyhedsværdi, originalitet, offentlig betydning eller tydelig redaktionel relevans; tynd dokumentation er Researchs problem, ikke en afvisningsgrund. WATCH kun hvis nyhedskrogen/aktualiteten endnu er uklar. DROP kun ved klar dublet, gammel/triviel sag, rent holdningsstof uden nyhedskrog eller åbenlys spam. discovery_only må udløse Research, men er aldrig dokumentation. Sæt kategori og A-D-vægt. Fastslå samtidig story_location FØR research og hero: primært land, ISO-landekode, vigtigste lokale sprog, lokale og engelske stednavne samt evt. translitterationer. Lav 1-3 korte hero-søgefraser på lokalt sprog og 1-3 på engelsk; ved andet alfabet også translittererede varianter. Brug hændelsestype + sted + år når det er kendt. Oversæt ikke egennavne forkert. Hvis landet reelt er uklart eller sagen ikke har ét primært land, brug country='unknown', country_code='', primary_language='unknown' og tomme lokale arrays, men lav stadig engelske hero-termer hvis muligt. Svar ultrakort.`;
''',
"Newsdesk multilingual location instruction",
)

# 3) Unicode-aware multilingual Commons queries. Search all languages first, then
# choose the best result globally instead of returning the first query's winner.
old_queries = '''function commonsSearchQueries(assignment, article, research = null) {
  const stop = new Set(["mener","siger","efter","over","under","vil","kan","skal","med","fra","til","for","the","and","with","from","says","after","over"]);
  const clean = (value, limit = 7) => words(value).filter((x) => x.length >= 4 && !stop.has(x)).slice(0, limit).join(" ");
  const claims = (research?.candidate_claims || []).map((x) => x.claim).join(" ");
  const raw = [
    clean(`${assignment?.title_hint || ""} ${article?.title || ""}`, 7),
    clean(assignment?.title_hint || article?.title || "", 5),
    clean(assignment?.core_question || "", 5),
    clean(claims, 5),
    clean(article?.standfirst || "", 5),
  ].filter((x) => x && x.length >= 4);
  return [...new Set(raw)].slice(0, 5);
}
'''
new_queries = '''function mediaWords(value) {
  return (String(value || "").normalize("NFKC").match(/[\\p{L}\\p{N}]{2,}/gu) || [])
    .map((x) => x.toLocaleLowerCase()).filter(Boolean);
}
function commonsSearchQueries(assignment, article, research = null) {
  const loc = assignment?.story_location || {};
  const supplied = [
    ...(Array.isArray(loc.hero_queries_local) ? loc.hero_queries_local : []),
    ...(Array.isArray(loc.hero_queries_transliterated) ? loc.hero_queries_transliterated : []),
    ...(Array.isArray(loc.hero_queries_english) ? loc.hero_queries_english : []),
  ].map((x) => String(x || "").trim()).filter((x) => x.length >= 2);
  const stop = new Set(["mener","siger","efter","over","under","vil","kan","skal","med","fra","til","for","the","and","with","from","says","after"]);
  const clean = (value, limit = 7) => mediaWords(value).filter((x) => !stop.has(x)).slice(0, limit).join(" ");
  const claims = (research?.candidate_claims || []).map((x) => x.claim).join(" ");
  const fallback = [
    clean(`${assignment?.title_hint || ""} ${article?.title || ""}`, 7),
    clean(assignment?.core_question || "", 5),
    clean(claims, 5),
    clean(article?.standfirst || "", 5),
  ].filter((x) => x && x.length >= 2);
  return [...new Set([...supplied, ...fallback])].slice(0, 8);
}
'''
replace_once(old_queries, new_queries, "multilingual Commons query builder")

old_finder = '''async function findCommonsDocumentaryHero(assignment, article, research = null) {
  const queries = commonsSearchQueries(assignment, article, research);
  if (!queries.length) return null;
  for (const q of queries) {
  const params = new URLSearchParams({
    action: "query",
    format: "json",
    origin: "*",
    generator: "search",
    gsrnamespace: "6",
    gsrsearch: q,
    gsrlimit: "8",
    prop: "imageinfo",
    iiprop: "url|mime|size|extmetadata",
  });
  try {
    const res = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`, {
      headers: { "user-agent": "MorgentidendeMediaDesk/1.0" },
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!res.ok) continue;
    const payload = await res.json();
    const pages = Object.values(payload?.query?.pages || {});
    const queryTerms = new Set(words(q));
    const ranked = [];
    for (const page of pages) {
      const info = page?.imageinfo?.[0];
      const meta = info?.extmetadata || {};
      const license = meta.LicenseShortName?.value || meta.UsageTerms?.value || "";
      if (!info?.url || info?.mime !== "image/jpeg" || !commonsLicenseAllowed(license)) continue;
      if ((info.width || 0) < 800 || (info.height || 0) < 450) continue;
      const desc = stripCommonsHtml(meta.ImageDescription?.value || "");
      const title = String(page?.title || "").replace(/^File:/i, "");
      const candidateWords = new Set(words(`${title} ${desc}`));
      let overlap = 0;
      for (const term of queryTerms) if (candidateWords.has(term)) overlap += 1;
      const minOverlap = queryTerms.size <= 1 ? 1 : 2;
      if (overlap < minOverlap) continue;
      const credit = stripCommonsHtml(meta.Artist?.value || meta.Credit?.value || "Wikimedia Commons");
      ranked.push({
        score: overlap,
        hero: {
          src: info.thumburl || info.url,
          alt: desc || title,
          credit: credit || "Wikimedia Commons",
          license: stripCommonsHtml(license),
          source_url: info.descriptionurl || `https://commons.wikimedia.org/wiki/${encodeURIComponent(page.title)}`,
          image_type: "photo",
          context_type: "archive",
          caption: "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.",
          pending_image: false,
          ai_generated: false,
          placement: "lead",
        },
      });
    }
    ranked.sort((a, b) => b.score - a.score);
    if (ranked[0]?.hero) return ranked[0].hero;
  } catch (_) {}
  }
  return null;
}
'''
new_finder = '''async function findCommonsDocumentaryHero(assignment, article, research = null) {
  const queries = commonsSearchQueries(assignment, article, research);
  if (!queries.length) return null;
  const allowedMime = new Set(["image/jpeg", "image/png", "image/webp", "image/svg+xml", "image/tiff", "image/gif", "image/avif"]);
  const loc = assignment?.story_location || {};
  const locationTerms = new Set([
    ...(Array.isArray(loc.place_names_local) ? loc.place_names_local : []),
    ...(Array.isArray(loc.place_names_english) ? loc.place_names_english : []),
    ...(Array.isArray(loc.transliterations) ? loc.transliterations : []),
    loc.country || "",
  ].flatMap(mediaWords));
  const year = String(new Date().getUTCFullYear());
  const winners = new Map();

  for (let qIndex = 0; qIndex < queries.length; qIndex++) {
    const q = queries[qIndex];
    const params = new URLSearchParams({
      action: "query", format: "json", origin: "*", generator: "search",
      gsrnamespace: "6", gsrsearch: q, gsrlimit: "10",
      prop: "imageinfo", iiprop: "url|mime|size|extmetadata", iiurlwidth: "1600",
    });
    try {
      const res = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`, {
        headers: { "user-agent": "MorgentidendeMediaDesk/2.0" },
        cf: { cacheTtl: 300, cacheEverything: true },
      });
      if (!res.ok) continue;
      const payload = await res.json();
      const pages = Object.values(payload?.query?.pages || {});
      const queryTerms = new Set(mediaWords(q));
      for (const page of pages) {
        const info = page?.imageinfo?.[0];
        const meta = info?.extmetadata || {};
        const license = meta.LicenseShortName?.value || meta.UsageTerms?.value || "";
        const mime = String(info?.mime || "").toLowerCase();
        if (!info?.url || !allowedMime.has(mime) || !commonsLicenseAllowed(license)) continue;
        if ((info.width || 0) < 800 || (info.height || 0) < 450) continue;
        // Formats such as SVG/TIFF/GIF should use Wikimedia's rasterized thumbnail.
        const requiresThumb = ["image/svg+xml", "image/tiff", "image/gif"].includes(mime);
        const src = info.thumburl || (!requiresThumb ? info.url : null);
        if (!src) continue;

        const desc = stripCommonsHtml(meta.ImageDescription?.value || "");
        const title = String(page?.title || "").replace(/^File:/i, "");
        const candidateWords = new Set(mediaWords(`${title} ${desc}`));
        let overlap = 0;
        for (const term of queryTerms) if (candidateWords.has(term)) overlap += 1;
        const minOverlap = queryTerms.size <= 1 ? 1 : 2;
        if (queryTerms.size && overlap < minOverlap) continue;

        const visualText = `${title} ${desc}`.toLocaleLowerCase();
        const isMap = /(^|\\s)(map|kort|karte)(\\s|$)/iu.test(visualText);
        const isSatellite = ["satellite", "landsat", "sentinel", "earth observ", "satellit"].some((x) => visualText.includes(x));
        const graphic = isMap || isSatellite || mime === "image/svg+xml";
        const contextType = isMap ? "map" : isSatellite ? "satellite" : "archive";
        const caption = isMap ? "Kort over sagen eller det berørte område." : isSatellite ? "Satellitbillede relateret til hændelsen eller det berørte område." : "Arkivfoto – billedet viser ikke nødvendigvis selve hændelsen.";
        let placeOverlap = 0;
        for (const term of locationTerms) if (candidateWords.has(term)) placeOverlap += 1;
        const eventBonus = visualText.includes(year) ? 5 : 0;
        const queryPriorityBonus = Math.max(0, 1 - qIndex * 0.1);
        const score = overlap * 3 + Math.min(4, placeOverlap * 2) + eventBonus + queryPriorityBonus;
        const sourceUrl = info.descriptionurl || `https://commons.wikimedia.org/wiki/${encodeURIComponent(page.title)}`;
        const credit = stripCommonsHtml(meta.Artist?.value || meta.Credit?.value || "Wikimedia Commons");
        const candidate = {
          score,
          hero: {
            src, alt: desc || title, credit: credit || "Wikimedia Commons", license: stripCommonsHtml(license),
            source_url: sourceUrl, image_type: graphic ? "graphic" : "photo", context_type: contextType, caption,
            pending_image: false, ai_generated: false, placement: "lead",
          },
        };
        const old = winners.get(sourceUrl);
        if (!old || candidate.score > old.score) winners.set(sourceUrl, candidate);
      }
    } catch (_) {}
  }
  const ranked = [...winners.values()].sort((a, b) => b.score - a.score);
  return ranked[0]?.hero || null;
}
'''
replace_once(old_finder, new_finder, "global multilingual Commons ranking")

# 4) Preserve location contract in the canonical article and evidence ledger.
replace_once(
'''    assignment: { category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", core_question: dossier.core_question || assignment.core_question, manual_review: false },
''',
'''    assignment: { category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, core_question: dossier.core_question || assignment.core_question, manual_review: false },
''',
"ledger story_location",
)
replace_once(
'''    category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", title: article.title, standfirst: article.standfirst,
''',
'''    category: assignment.category, weight: assignment.weight, editorial_destination: assignment.editorial_destination || "main", story_location: assignment.story_location || null, title: article.title, standfirst: article.standfirst,
''',
"article story_location",
)
replace_once(
'''media_policy: { documentary_first: true, pending_image: Boolean(hero.pending_image), temporary_sketch_allowed_after_scout: true, static_sketch_fallback: true, late_hold_for_no_photo: false }''',
'''media_policy: { documentary_first: true, multilingual_location_search: true, pending_image: Boolean(hero.pending_image), temporary_sketch_allowed_after_scout: true, static_sketch_fallback: false, late_hold_for_no_photo: false }''',
"media policy audit",
)

print("location-aware hero migration complete")
