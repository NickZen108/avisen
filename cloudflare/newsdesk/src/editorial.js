const FAST_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast";
const STRONG_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell";
const PUBLIC_BASE = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev";

const CATEGORIES = ["Danmark", "Udland", "Politik", "Penge", "Krimi", "Videnskab & teknologi", "Sundhed", "Kultur & medier", "Sport", "Liv"];

function nowIso() { return new Date().toISOString(); }
function slugify(value) {
  return String(value || "").toLocaleLowerCase("da-DK").normalize("NFKD")
    .replace(/[æ]/g, "ae").replace(/[ø]/g, "oe").replace(/[å]/g, "aa")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 72);
}
function sourceGroup(name) { return slugify(name || "source") + "-reporting"; }
function stripHtml(html) {
  return String(html || "")
    .replace(/<script\b[\s\S]*?<\/script>/gi, " ").replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<nav\b[\s\S]*?<\/nav>/gi, " ").replace(/<footer\b[\s\S]*?<\/footer>/gi, " ")
    .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}

async function fetchExcerpt(signal) {
  if (!signal?.url) return { ...signal, excerpt: signal?.description || "", fetched: false };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 18000);
  try {
    const response = await fetch(signal.url, {
      headers: { "user-agent": "MorgentidendeResearch/1.1 (+https://morgentidende.nicolaipetersen108.workers.dev/)" },
      signal: controller.signal, redirect: "follow",
    });
    if (!response.ok) return { ...signal, excerpt: signal.description || "", fetched: false, fetch_status: response.status };
    const type = response.headers.get("content-type") || "";
    if (!type.includes("html") && !type.includes("text")) return { ...signal, excerpt: signal.description || "", fetched: false, fetch_status: response.status };
    const text = stripHtml(await response.text()).slice(0, 14000);
    return { ...signal, excerpt: text || signal.description || "", fetched: Boolean(text), fetch_status: response.status, final_url: response.url };
  } catch (error) {
    return { ...signal, excerpt: signal.description || "", fetched: false, fetch_error: String(error) };
  } finally { clearTimeout(timer); }
}

function responseObject(raw) {
  if (raw && typeof raw.response === "object" && raw.response !== null) return raw.response;
  if (raw && typeof raw.response === "string") { try { return JSON.parse(raw.response); } catch (_) {} }
  if (raw && Array.isArray(raw.choices)) {
    const content = raw.choices[0]?.message?.content;
    if (typeof content === "object" && content) return content;
    if (typeof content === "string") { try { return JSON.parse(content); } catch (_) {} }
  }
  throw new Error("Workers AI returned no parseable structured response");
}

async function aiJson(env, system, user, schema, maxTokens = 2800, model = STRONG_TEXT_MODEL, fallbackModel = null) {
  const request = {
    messages: [{ role: "system", content: system }, { role: "user", content: user }],
    max_tokens: maxTokens, temperature: 0.15,
    response_format: { type: "json_schema", json_schema: schema },
  };
  try {
    const raw = await env.AI.run(model, request);
    return responseObject(raw);
  } catch (error) {
    if (!fallbackModel || fallbackModel === model) throw error;
    console.warn("Workers AI structured-call fallback", model, "->", fallbackModel, String(error));
    const raw = await env.AI.run(fallbackModel, request);
    return responseObject(raw);
  }
}

const assignmentSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["publish", "hold"] }, title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES }, weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 6 },
    rationale: { type: "string" }, core_question: { type: "string" },
  }, required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question"],
};

const researchSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["continue", "hold"] }, rationale: { type: "string" }, core_question: { type: "string" },
    right_of_reply_required: { type: "boolean" }, contradictions: { type: "array", items: { type: "string" } },
    candidate_claims: { type: "array", minItems: 2, maxItems: 12, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "notes"] } },
  }, required: ["decision", "rationale", "core_question", "right_of_reply_required", "contradictions", "candidate_claims"],
};

const factCheckSchema = {
  type: "object", properties: {
    decision: { type: "string", enum: ["publish", "hold"] }, rationale: { type: "string" },
    contradictions: { type: "array", items: { type: "string" } },
    claims: { type: "array", minItems: 2, maxItems: 12, items: { type: "object", properties: {
      id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 },
      status: { type: "string", enum: ["verified", "uncertain", "rejected"] }, notes: { type: "string" },
    }, required: ["id", "claim", "source_indexes", "status", "notes"] } },
  }, required: ["decision", "rationale", "contradictions", "claims"],
};

const deskRecheckSchema = { type: "object", properties: {
  decision: { type: "string", enum: ["publish", "update", "hold", "kill"] }, rationale: { type: "string" },
}, required: ["decision", "rationale"] };

const articleSchema = { type: "object", properties: {
  title: { type: "string" }, standfirst: { type: "string" },
  body: { type: "array", minItems: 3, maxItems: 14, items: { type: "object", properties: {
    type: { type: "string", enum: ["p", "h2", "h3"] }, text: { type: "string" },
  }, required: ["type", "text"] } },
  seo_title: { type: "string" }, seo_description: { type: "string" }, hero_prompt: { type: "string" }, hero_alt: { type: "string" },
}, required: ["title", "standfirst", "body", "seo_title", "seo_description", "hero_prompt", "hero_alt"] };

const finalSchema = { type: "object", properties: {
  blocking_issues: { type: "array", maxItems: 10, items: { type: "object", properties: {
    gate: { type: "string", enum: ["language", "ethics", "image", "seo", "final_editor"] }, issue: { type: "string" },
  }, required: ["gate", "issue"] } },
}, required: ["blocking_issues"] };

function signalSummary(scan) {
  const clusterSizes = new Map((scan.exact_clusters || []).map((c) => [c.normalized, (c.sources || []).length]));
  const ranked = scan.signals.map((s, i) => ({
    s, i,
    cluster: clusterSizes.get(s.normalized) || 1,
    feedRank: Number.isInteger(s.feed_rank) ? s.feed_rank : 99,
    published: Date.parse(s.published_at || "") || 0,
  })).sort((a, b) =>
    b.cluster - a.cluster || a.feedRank - b.feedRank || b.published - a.published ||
    a.s.source.localeCompare(b.s.source, "da") || a.s.headline.localeCompare(b.s.headline, "da")
  );
  const perSource = new Map();
  const chosen = [];
  for (const item of ranked) {
    if (chosen.length >= 40) break;
    const used = perSource.get(item.s.source) || 0;
    if (used >= 6) continue;
    perSource.set(item.s.source, used + 1);
    chosen.push(item);
  }
  return chosen.map(({ s, i }) => ({ i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 360), url: s.url, published_at: s.published_at || null }));
}
async function chooseAssignment(env, scan) {
  const system = `Du er Newsdesk på Morgentidende. Vælg højst én væsentlig, aktuel historie til research. Kræv ikke tre færdige kilder her; Research skal udvide grundlaget. En stærk breaking-historie må sendes videre med én troværdig startkilde. Hold kun ved lav nyhedsværdi, dublet, åbenlys utroværdighed eller konkret risiko, der gør research meningsløs. Returnér kun struktureret output.`;
  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals: signalSummary(scan) }), assignmentSchema, 900, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}
function distinctSources(items) { return [...new Set(items.map((x) => x.source))]; }
function validateAssignment(assignment, scan) {
  if (assignment.decision !== "publish") return { ok: false, reason: assignment.rationale || "Newsdesk hold" };
  const indexes = [...new Set(assignment.signal_indexes.filter((i) => Number.isInteger(i) && i >= 0 && i < scan.signals.length))];
  const selected = indexes.map((i) => ({ ...scan.signals[i], signal_index: i }));
  if (!selected.length) return { ok: false, reason: "Newsdesk valgte ingen brugbare signaler" };
  if (!selected.some((x) => x.url)) return { ok: false, reason: "Ingen kilde-URL til research" };
  return { ok: true, selected };
}

async function runResearch(env, assignment, selected) {
  const researched = await Promise.all(selected.map(fetchExcerpt));
  const usable = researched.filter((x) => (x.excerpt || "").length >= 160);
  if (distinctSources(usable).length < 2) return { decision: "hold", rationale: "Research kunne kun hente læsbart materiale fra én kilde", researched: usable };
  const sources = usable.map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url, excerpt: s.excerpt.slice(0, 12000) }));
  const system = `Du er Research på Morgentidende. Du må IKKE fact-checke som slutdommer. Kortlæg historien ud fra de vedlagte kildetekster: bærende faktapåstande, relevante modpositioner, konsekvenser for læseren, uenigheder og usikkerhed. AI er aldrig en kilde. Peg på præcis hvilke kilder der understøtter hvert kandidat-claim. Forelæggelse skal markeres, hvis alvorlige belastende påstande om en identificerbar part kræver svar. Opfind ikke ekstra claims for at nå et antal. Returnér kun struktureret output.`;
  const research = await aiJson(env, system, JSON.stringify({ assignment, sources }), researchSchema, 2200, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
  research.researched = usable;
  research.source_payload = sources;
  if (research.right_of_reply_required) research.decision = "hold";
  return research;
}

async function runFactCheck(env, assignment, research) {
  const system = `Du er en UAFHÆNGIG Fact checker på Morgentidende. Research-agentens konklusioner er ikke autoritative. Forsøg aktivt at falsificere hvert kandidat-claim ved at kontrollere det mod de vedlagte originale kildetekster. Du må ikke tilføje nye kilder eller nye fakta. Markér verified kun når mindst to reelt uafhængige kilder understøtter et materielt claim. Enkeltkilde-oplysninger er normalt uncertain. Rejected bruges, når kilderne modsiger claimet. To solide verificerede bærende claims er nok til en kort artikel; opfind ikke claims. Hold kun hvis færre end to bærende claims kan verificeres, eller hvis en væsentlig modsigelse gør historiens kerne usikker. Returnér kun struktureret output.`;
  const fact = await aiJson(env, system, JSON.stringify({
    assignment,
    research: { core_question: research.core_question, rationale: research.rationale, contradictions: research.contradictions, candidate_claims: research.candidate_claims },
    sources: research.source_payload,
  }), factCheckSchema, 2400);
  fact.researched = research.researched;
  fact.core_question = research.core_question || assignment.core_question;
  fact.right_of_reply_required = research.right_of_reply_required;
  for (const claim of fact.claims) {
    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < fact.researched.length))];
    claim.source_indexes = indexes;
    const independent = new Set(indexes.map((i) => fact.researched[i]?.source).filter(Boolean));
    if (claim.status === "verified" && independent.size < 2) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministic gate: mindre end to uafhængige kilder.`.trim();
    }
  }
  const verified = fact.claims.filter((c) => c.status === "verified");
  if (verified.length < 2) {
    fact.decision = "hold";
    fact.rationale = `${fact.rationale || ""} Deterministic gate: færre end to bærende claims er verificeret.`.trim();
  }
  return fact;
}

async function deskRecheck(env, assignment, dossier) {
  const system = `Du er Newsdesk ved et kort recheck EFTER uafhængig Fact checker. Du må ikke genresearche eller gentage fact check. Vurder kun om den dokumenterede historie stadig er aktuel og væsentlig nok, og om kernen stadig svarer til assignment. Hold/kill kræver en konkret redaktionel grund.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), contradictions: dossier.contradictions, rationale: dossier.rationale }), deskRecheckSchema, 450, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}

async function writeArticle(env, assignment, dossier) {
  const sources = dossier.researched.map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const system = `Du er journalist på Morgentidende. Skriv præcist og levende dansk, men brug KUN verificerede claims. Gør attribution tydelig. Ingen opdigtede citater. Skriv til almindelige læsere: erstat fagord og engelske brancheord med almindeligt dansk, forklar nødvendige tekniske begreber første gang med 1-2 korte sætninger, og omsæt uvante mål til fx kilometer, meter, Celsius og kilogram. En kort nyhed må gerne nøjes med tre meningsfulde tekstblokke; fyld aldrig teksten ud bare for at nå en længde. Hero-prompten skal beskrive en bred redaktionel illustration og må ikke foregive at være dokumentarfoto. Ingen tekst i billedet.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3000);
}

async function finalReview(env, assignment, dossier, article) {
  const system = `Du er uafhængig slutredaktør. Kontrollér den færdige artikel mod de verificerede claims uden at genresearche. Returnér kun konkrete publiceringsblokerende problemer: materielt forkert/uklart sprog, uforklaret nødvendigt fagsprog, påstande ud over dokumentationen, utilstrækkelig attribution/pluralisme, etisk problem, misvisende SEO eller falsk-dokumentarisk hero-prompt. Små stilpræferencer er ikke blockers.`;
  const raw = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 900);
  const issues = Array.isArray(raw.blocking_issues) ? raw.blocking_issues.filter((x) => x?.gate && x?.issue) : [];
  const failed = new Set(issues.map((x) => x.gate));
  return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", image: failed.has("image") ? "hold" : "pass", seo: failed.has("seo") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };
}
async function reviseFixableIssues(env, assignment, dossier, article, review) {
  const fixable = (review.issues || []).filter((x) => ["language", "seo", "image"].includes(x.gate));
  const hard = (review.issues || []).filter((x) => !["language", "seo", "image"].includes(x.gate));
  if (!fixable.length || hard.length) return article;
  const system = `Ret KUN de konkrete language/seo/image-prompt-problemer. Bevar verificerede fakta, vinkel og betydning. Tilføj ingen nye claims. Lægmandssprog og metriske enheder er obligatoriske.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues: fixable }), articleSchema, 2400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}
async function generateHero(env, article) {
  const prompt = `${article.hero_prompt}. Wide 16:9 editorial illustration for a serious Danish newspaper, visually strong, elegant, realistic lighting but clearly illustrative rather than documentary evidence, no words, no logos, no watermarks.`;
  const raw = await env.AI.run(IMAGE_MODEL, { prompt });
  if (!raw?.image || typeof raw.image !== "string") throw new Error("Image model returned no base64 image");
  return raw.image;
}

function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {
  const sources = dossier.researched.map((s, i) => ({ id: `S${i + 1}`, name: s.source, url: s.final_url || s.url, published_at: null, accessed_at: accessedAt, type: "news", source_group: sourceGroup(s.source), authoritative_for: s.headline || "Independent coverage" }));
  const groups = [...new Set(sources.map((s) => s.source_group))];
  const claims = dossier.claims.filter((c) => c.status === "verified").map((c, i) => {
    const ids = [...new Set(c.source_indexes)].map((n) => sources[n]?.id).filter(Boolean);
    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };
  });
  return {
    schema_version: 2, story_id: storyId, article_slug: slug,
    assignment: { category: assignment.category, weight: assignment.weight, core_question: dossier.core_question || assignment.core_question, manual_review: false },
    sources,
    coverage_sweep: { status: groups.length >= 3 ? "pass" : "limited", editorial_source_ids: sources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 3 ? null : "Færre end tre uafhængige kildegrupper; bærende claims er stadig krydstjekket", notes: ["Research hentede og sammenlignede kilder; Fact checker kørte som separat AI-call bagefter."] },
    claims, numbers: [], quotes: [], right_of_reply: { required: false, party: null, contacted_at: null, deadline: null, response: null, exception: null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Uafhængigt Fact checker-call bestået; deterministisk gate kræver mindst to uafhængige kilder for verificerede materielle claims."] },
    desk_recheck: { status: desk.decision, checked_at: accessedAt, rationale: desk.rationale },
  };
}

export async function runEditorialCycle(env, scan) {
  const startedAt = nowIso();
  const assignment = await chooseAssignment(env, scan);
  const check = validateAssignment(assignment, scan);
  if (!check.ok) return { status: "hold", stage: "newsdesk", checked_at: startedAt, reason: check.reason, scan_fingerprint: scan.fingerprint };

  const research = await runResearch(env, assignment, check.selected);
  if (research.decision !== "continue") return { status: "hold", stage: research.right_of_reply_required ? "ethics" : "research", checked_at: startedAt, reason: research.rationale || "Research hold", scan_fingerprint: scan.fingerprint };

  const dossier = await runFactCheck(env, assignment, research);
  if (dossier.decision !== "publish") return { status: "hold", stage: "fact-check", checked_at: startedAt, reason: dossier.rationale || "Fact check hold", scan_fingerprint: scan.fingerprint };

  const desk = await deskRecheck(env, assignment, dossier);
  if (!["publish", "update"].includes(desk.decision)) return { status: "hold", stage: "desk-recheck", checked_at: startedAt, reason: desk.rationale || "Newsdesk recheck hold", scan_fingerprint: scan.fingerprint };

  let article = await writeArticle(env, assignment, dossier);
  let review = await finalReview(env, assignment, dossier, article);
  if (review.decision !== "pass") {
    const revised = await reviseFixableIssues(env, assignment, dossier, article, review);
    if (JSON.stringify(revised) !== JSON.stringify(article)) { article = revised; review = await finalReview(env, assignment, dossier, article); }
  }
  if (review.decision !== "pass" || [review.language, review.ethics, review.image, review.seo, review.final_editor].some((x) => x !== "pass")) {
    return { status: "hold", stage: "final-editor", checked_at: startedAt, reason: (review.notes || []).join("; ") || "Final editor hold", scan_fingerprint: scan.fingerprint };
  }

  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const imageKey = `${slug}.jpg`;
  const imageBase64 = await generateHero(env, article);
  const ledger = makeLedger(storyId, slug, assignment, dossier, desk, startedAt);
  const canonical = {
    pipeline_version: 2, status: "ready", release_requested: true, story_id: storyId, slug,
    category: assignment.category, weight: assignment.weight, title: article.title, standfirst: article.standfirst,
    byline: "Morgentidende Redaktion", published_at: null, updated_at: null, manual_review: false,
    ledger: `sources/${slug}.json`, claim_ids: ledger.claims.map((c) => c.id),
    seo: { title: article.seo_title, description: article.seo_description, canonical: null },
    image: { src: `/img/auto/${imageKey}`, alt: article.hero_alt, credit: "Morgentidende", license: "Morgentidende", source_url: null, image_type: "illustration", placement: "lead" },
    body: article.body, source_ids_to_display: ledger.sources.slice(0, 6).map((s) => s.id), related_news_slug: null, related: [], correction_note: null, scheduled_for: null, released_from_schedule_at: null,
  };
  const approvalSnapshot = JSON.parse(JSON.stringify(canonical));
  for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed", "workflow_state"]) delete approvalSnapshot[key];
  const approval = { schema_version: 1, status: "pass", story_id: storyId, article_slug: slug, checked_at: startedAt, gates: { language: "pass", ethics: "pass", image: "pass", seo: "pass", final_editor: "pass" }, editorial_snapshot: approvalSnapshot };

  return {
    status: "approved", schema_version: 1, generated_at: startedAt, scan_fingerprint: scan.fingerprint,
    runtime: "cloudflare-workers-ai", model: STRONG_TEXT_MODEL, models: { fast: FAST_TEXT_MODEL, strong: STRONG_TEXT_MODEL, image: IMAGE_MODEL }, story_id: storyId, slug, article: canonical, ledger, approval,
    media: { key: imageKey, content_type: "image/jpeg", base64: imageBase64 },
    audit: { assignment, research: { rationale: research.rationale, candidate_claims: research.candidate_claims, contradictions: research.contradictions }, fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, desk_recheck: desk, final_review: review, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
  };
}

export function editorialDue(lastRunAt) {
  if (!lastRunAt) return true;
  const then = Date.parse(lastRunAt);
  return !Number.isFinite(then) || Date.now() - then >= 27 * 60 * 1000;
}
export function publicMediaUrl(key) { return `${PUBLIC_BASE}/media/${encodeURIComponent(key)}`; }
