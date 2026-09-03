#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
SYNC = ROOT / 'scripts' / 'sync_cloudflare_editorial.py'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing fragment: {label}')
    return text.replace(old, new, 1)

text = EDITORIAL.read_text(encoding='utf-8')

# A short one-claim story must not be forced to invent/repeat material just to fill three blocks.
text = replace_once(text, 'body: { type: "array", minItems: 3, maxItems: 14, items:', 'body: { type: "array", minItems: 1, maxItems: 14, items:', 'article body minimum')

# Journalist owns first-pass publishable copy. Explicitly prevent source-name manchets and unsupported generic filler.
old = 'En kort one-claim-nyhed med tre meningsfulde tekstblokke er fuldt acceptabel; fyld aldrig ud. Media ejer heroen; skriv ingen billedprompt eller billedmetadata.`;'
new = 'En one-claim-nyhed skal være kort: brug kun så mange tekstblokke som de verificerede claims faktisk bærer, helt ned til én blok. Gentag aldrig samme claim for at skabe længde, og tilføj aldrig generelle perspektiver, konsekvenser, fremtidsforudsigelser eller baggrund, medmindre de selv findes som verified claims. Standfirst skal være en rigtig kort manchet på normalt 1-2 sætninger og højst 35 ord, der opsummerer nyheden; den må aldrig blot være et kildenavn som “Euronews”. Media ejer heroen; skriv ingen billedprompt eller billedmetadata.`;'
text = replace_once(text, old, new, 'journalist no-filler rule')

# A/B gets one strong, short final-editor pass. This replaces duplicated checks; it does not add a gate.
old = 'const raw = await aiJson(env, system, JSON.stringify({ categories: CATEGORIES, assignment, claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, article }), finalSchema, 360, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);'
new = 'const reviewModel = ["A", "B"].includes(assignment?.weight) ? STRONG_TEXT_MODEL : FAST_TEXT_MODEL;\n  const reviewFallback = reviewModel === FAST_TEXT_MODEL ? STRONG_TEXT_MODEL : null;\n  const raw = await aiJson(env, system, JSON.stringify({ categories: CATEGORIES, assignment, claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, article }), finalSchema, 360, reviewModel, reviewFallback);'
text = replace_once(text, old, new, 'tiered final editor model')

# Commons relevance: when a search query contains subject words beyond place/institution terms,
# an archive photo must match at least one subject word. This prevents e.g. a pope photo winning a robot story.
old = '''        const minOverlap = queryTerms.size <= 1 ? 1 : 2;
        if (queryTerms.size && overlap < minOverlap) continue;

        const visualText = `${title} ${desc}`.toLocaleLowerCase();'''
new = '''        const minOverlap = queryTerms.size <= 1 ? 1 : 2;
        if (queryTerms.size && overlap < minOverlap) continue;
        const subjectTerms = [...queryTerms].filter((term) => !locationTerms.has(term));
        if (subjectTerms.length && !subjectTerms.some((term) => candidateWords.has(term))) continue;

        const visualText = `${title} ${desc}`.toLocaleLowerCase();'''
text = replace_once(text, old, new, 'Commons subject relevance')

EDITORIAL.write_text(text, encoding='utf-8')

# Importer must accept a genuinely short one-claim article.
text = SYNC.read_text(encoding='utf-8')
text = replace_once(text, 'if not isinstance(article.get("body"), list) or len(article["body"]) < 3:\n        fail("artikeltekst mangler eller har færre end tre meningsfulde tekstblokke")', 'if not isinstance(article.get("body"), list) or len(article["body"]) < 1:\n        fail("artikeltekst mangler")', 'sync body minimum')
SYNC.write_text(text, encoding='utf-8')

print('cost-quality balance patch: PASS')
