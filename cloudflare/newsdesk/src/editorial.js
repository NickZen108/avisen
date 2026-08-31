const TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell";
const PUBLIC_BASE = "https://morgentidende-newsdesk.nicolaipetersen108.workers.dev";

const CATEGORIES = ["Nyhed", "Krimi", "Politik", "Økonomi", "Udland", "Forbruger", "Kultur", "Videnskab", "Sundhed", "Parforhold", "Sport"];

function nowIso() { return new Date().toISOString(); }
function slugify(value) {
  return String(value || "")
    .toLocaleLowerCase("da-DK")
    .normalize("NFKD")
    .replace(/[æ]/g, "ae").replace(/[ø]/g, "oe").replace(/[å]/g, "aa")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 72);
}
function sourceGroup(name) { return slugify(name || "source") + "-reporting"; }
function stripHtml(html) {
  return String(html || "")
    .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<nav\b[\s\S]*?<\/nav>/gi, " ")
    .replace(/<footer\b[\s\S]*?<\/footer>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/\s+/g, " ").trim();
}

async function fetchExcerpt(signal) {
  if (!signal?.url) return { ...signal, excerpt: signal?.description || "", fetched: false };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 18000);
  try {
    const response = await fetch(signal.url, {
      headers: { "user-agent": "MorgentidendeResearch/1.0 (+https://morgentidende.nicolaipetersen108.workers.dev/)" },
      signal: controller.signal,
      redirect: "follow",
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
  if (raw && typeof raw.response === "string") {
    try { return JSON.parse(raw.response); } catch (_) {}
  }
  if (raw && Array.isArray(raw.choices)) {
    const content = raw.choices[0]?.message?.content;
    if (typeof content === "object" && content) return content;
    if (typeof content === "string") {
      try { return JSON.parse(content); } catch (_) {}
    }
  }
  throw new Error("Workers AI returned no parseable structured response");
}

async function aiJson(env, system, user, schema, maxTokens = 2800) {
  const raw = await env.AI.run(TEXT_MODEL, {
    messages: [{ role: "system", content: system }, { role: "user", content: user }],
    max_tokens: maxTokens,
    temperature: 0.15,
    response_format: { type: "json_schema", json_schema: schema },
  });
  return responseObject(raw);
}

const assignmentSchema = {
  type: "object",
  properties: {
    decision: { type: "string", enum: ["publish", "hold"] },
    title_hint: { type: "string" },
    category: { type: "string", enum: CATEGORIES },
    weight: { type: "string", enum: ["A", "B", "C", "D"] },
    signal_indexes: { type: "array", items: { type: "integer" }, minItems: 0, maxItems: 8 },
    rationale: { type: "string" },
    core_question: { type: "string" },
  },
  required: ["decision", "title_hint", "category", "weight", "signal_indexes", "rationale", "core_question"],
};

const dossierSchema = {
  type: "object",
  properties: {
    decision: { type: "string", enum: ["publish", "hold"] },
    rationale: { type: "string" },
    core_question: { type: "string" },
    right_of_reply_required: { type: "boolean" },
    contradictions: { type: "array", items: { type: "string" } },
    claims: {
      type: "array",
      minItems: 3,
      maxItems: 12,
      items: {
        type: "object",
        properties: {
          id: { type: "string" }, claim: { type: "string" }, source_indexes: { type: "array", items: { type: "integer" }, minItems: 1 }, status: { type: "string", enum: ["verified", "uncertain"] }, notes: { type: "string" },
        },
        required: ["id", "claim", "source_indexes", "status", "notes"],
      },
    },
  },
  required: ["decision", "rationale", "core_question", "right_of_reply_required", "contradictions", "claims"],
};

const articleSchema = {
  type: "object",
  properties: {
    title: { type: "string" }, standfirst: { type: "string" },
    body: { type: "array", minItems: 5, maxItems: 14, items: { type: "object", properties: { type: { type: "string", enum: ["p", "h2", "h3"] }, text: { type: "string" } }, required: ["type", "text"] } },
    seo_title: { type: "string" }, seo_description: { type: "string" }, hero_prompt: { type: "string" }, hero_alt: { type: "string" },
  },
  required: ["title", "standfirst", "body", "seo_title", "seo_description", "hero_prompt", "hero_alt"],
};

const finalSchema = {
  type: "object",
  properties: {
    decision: { type: "string", enum: ["pass", "hold"] },
    language: { type: "string", enum: ["pass", "hold"] }, ethics: { type: "string", enum: ["pass", "hold"] }, image: { type: "string", enum: ["pass", "hold"] }, seo: { type: "string", enum: ["pass", "hold"] }, final_editor: { type: "string", enum: ["pass", "hold"] }, notes: { type: "array", items: { type: "string" } },
  },
  required: ["decision", "language", "ethics", "image", "seo", "final_editor", "notes"],
};

function signalSummary(scan) {
  return scan.signals.slice(0, 100).map((s, i) => ({ i, source: s.source, headline: s.headline, description: (s.description || "").slice(0, 500), url: s.url }));
}

async function chooseAssignment(env, scan) {
  const system = `Du er Newsdesk på Morgentidende, en dansk generalistisk netavis med både danske og store internationale nyheder. Vælg højst én aktuel historie til behandling. Kvalitet slår volumen. En historie opfylder Newsdesk-kriteriet, når mindst tre forskellige redaktionelle kilder i input tydeligt dækker samme væsentlige, aktuelle begivenhed eller samme bærende nye oplysning. Samme wire genudgivet flere steder tæller ikke som flere uafhængige kilder, hvis det er åbenlyst. En direkte dansk vinkel er et plus, men IKKE et krav for store internationale begivenheder, katastrofer, krige, økonomiske chok, videnskabelige gennembrud eller andre historier med klar almen nyhedsværdi. Hvis du selv i rationale konstaterer, at mindst tre forskellige redaktionelle kilder dækker samme store aktuelle historie, og du ikke samtidig identificerer et konkret dokumentations-, etik- eller uafhængighedsproblem, SKAL decision være publish og signal_indexes skal pege på mindst tre af de relevante kilder. Brug kun hold når kriteriet faktisk ikke er opfyldt eller du kan beskrive den konkrete grund. Dokumenterbarhed er altid et krav. Returnér kun struktureret output.`;
  return aiJson(env, system, JSON.stringify({ generated_at: scan.generated_at, signals: signalSummary(scan) }), assignmentSchema, 1600);
}

function distinctSources(items) { return [...new Set(items.map((x) => x.source))]; }
function validateAssignment(assignment, scan) {
  if (assignment.decision !== "publish") return { ok: false, reason: assignment.rationale || "Newsdesk hold" };
  const indexes = [...new Set(assignment.signal_indexes.filter((i) => Number.isInteger(i) && i >= 0 && i < scan.signals.length))];
  const selected = indexes.map((i) => ({ ...scan.signals[i], signal_index: i }));
  if (distinctSources(selected).length < 3) return { ok: false, reason: "Mindre end tre forskellige kilder efter deterministic recheck" };
  if (selected.filter((x) => x.url).length < 3) return { ok: false, reason: "Mindre end tre kilde-URL'er" };
  return { ok: true, selected };
}

async function buildDossier(env, assignment, selected) {
  const researched = await Promise.all(selected.map(fetchExcerpt));
  const usable = researched.filter((x) => (x.excerpt || "").length >= 160);
  if (distinctSources(usable).length < 3) return { decision: "hold", rationale: "Kunne ikke hente læsbart materiale fra tre forskellige kilder", researched: usable };
  const sourcePayload = usable.map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url, excerpt: s.excerpt.slice(0, 12000) }));
  const system = `Du er Morgentidendes research- og fact-check-desk. Arbejd kun ud fra de vedlagte kildetekster; AI er aldrig en kilde. For hver bærende faktuel påstand skal du angive de kilder, der faktisk støtter den. Materielle claims skal have støtte fra mindst to uafhængige kilder. En oplysning, der kun støttes af én kilde, skal markeres uncertain og må ikke bruges som verificeret claim. Hvis mindst tre materielle claims hver støttes af mindst to uafhængige kilder, right_of_reply_required er false, og der ikke er en konkret bærende modsigelse eller anden dokumentationsblokering, SKAL decision være publish. Brug kun hold når rationale beskriver det konkrete dokumentations-, modsigelses- eller forelæggelsesproblem. Skeln klart mellem verificerede fakta og påstande/udsagn. Returnér kun struktureret output.`;
  const dossier = await aiJson(env, system, JSON.stringify({ assignment, sources: sourcePayload }), dossierSchema, 3600);
  dossier.researched = usable;
  if (dossier.right_of_reply_required) dossier.decision = "hold";

  for (const claim of dossier.claims) {
    const indexes = [...new Set((claim.source_indexes || []).filter((i) => Number.isInteger(i) && i >= 0 && i < usable.length))];
    claim.source_indexes = indexes;
    const independentSources = new Set(indexes.map((i) => usable[i]?.source).filter(Boolean));
    if (claim.status === "verified" && independentSources.size < 2) {
      claim.status = "uncertain";
      claim.notes = `${claim.notes || ""} Nedgraderet af deterministic gate: mindre end to uafhængige kilder.`.trim();
    }
  }

  const verified = dossier.claims.filter((c) => c.status === "verified");
  if (verified.length < 3) {
    dossier.decision = "hold";
    dossier.rationale = `${dossier.rationale || ""} Deterministic gate: færre end tre bærende claims har støtte fra mindst to uafhængige kilder.`.trim();
  }
  return dossier;
}

async function writeArticle(env, assignment, dossier) {
  const sources = dossier.researched.map((s, i) => ({ source_index: i, name: s.source, headline: s.headline, url: s.final_url || s.url }));
  const system = `Du er journalist og derefter sprogagent på en nøgtern dansk netavis. Skriv præcist dansk uden sensationssprog. Brug KUN de verificerede claims i dossieret. Gør attribution tydelig, når noget er et udsagn og ikke et fastslået faktum. Ingen opdigtede citater. Kort nyhedsformat med logisk struktur. Hero-prompten skal beskrive en flot, bred redaktionel illustration, som symboliserer emnet uden at foregive at være et dokumentarfoto af den konkrete virkelige hændelse eller konkrete personer. Ingen tekst i billedet.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), sources }), articleSchema, 3800);
}

async function finalReview(env, assignment, dossier, article) {
  const system = `Du er uafhængig slutredaktør på Morgentidende. Kontrollér artikel mod verificerede claims. PASS kun hvis: dansk sprog er klart og korrekt; ingen påstand går videre end dokumentationen; pluralisme/attribution er rimelig; etik er forsvarlig; SEO er nøgtern; hero-prompten er relevant og ikke udformet som falsk dokumentarfoto. Hvis noget materielt mangler eller er usikkert: hold. Returnér kun struktureret output.`;
  const review = await aiJson(env, system, JSON.stringify({ assignment, claims: dossier.claims, contradictions: dossier.contradictions, article }), finalSchema, 1400);
  const componentGates = [review.language, review.ethics, review.image, review.seo, review.final_editor];
  review.decision = componentGates.every((gate) => gate === "pass") ? "pass" : "hold";
  return review;
}

async function generateHero(env, article) {
  const prompt = `${article.hero_prompt}. Wide 16:9 editorial illustration for a serious Danish newspaper, visually strong, elegant, realistic lighting but clearly illustrative rather than documentary evidence, no words, no logos, no watermarks.`;
  const raw = await env.AI.run(IMAGE_MODEL, { prompt, seed: Math.floor(Math.random() * 100000) });
  if (!raw?.image || typeof raw.image !== "string") throw new Error("Image model returned no base64 image");
  return raw.image;
}

function makeLedger(storyId, slug, assignment, dossier, accessedAt) {
  const sources = dossier.researched.map((s, i) => ({
    id: `S${i + 1}`, name: s.source, url: s.final_url || s.url, published_at: null, accessed_at: accessedAt,
    type: "news", source_group: sourceGroup(s.source), authoritative_for: s.headline || "Independent coverage",
  }));
  const groups = [...new Set(sources.map((s) => s.source_group))];
  const claims = dossier.claims.filter((c) => c.status === "verified").map((c, i) => {
    const ids = [...new Set(c.source_indexes)].map((n) => sources[n]?.id).filter(Boolean);
    return { id: `F${String(i + 1).padStart(2, "0")}`, claim: c.claim, status: "verified", source_ids: ids, independent_groups: ids.map((id) => sources.find((s) => s.id === id)?.source_group).filter(Boolean), checked_at: accessedAt, notes: c.notes || "" };
  });
  return {
    schema_version: 2, story_id: storyId, article_slug: slug,
    assignment: { category: assignment.category, weight: assignment.weight, core_question: dossier.core_question || assignment.core_question, manual_review: false },
    sources,
    coverage_sweep: { status: groups.length >= 3 ? "pass" : "limited", editorial_source_ids: sources.slice(0, 6).map((s) => s.id), independent_source_groups: groups.slice(0, 6), limitations: groups.length >= 3 ? null : "Færre end tre uafhængige kildegrupper", notes: ["Cloudflare editorial runtime fetched and compared the source texts before drafting."] },
    claims, numbers: [], quotes: [],
    right_of_reply: { required: false, party: null, contacted_at: null, deadline: null, response: null, exception: null },
    fact_check: { status: "pass", checked_at: accessedAt, notes: ["Independent Cloudflare fact-check stage passed; deterministic claim-support gate required at least two source indexes for each published material claim."] },
    desk_recheck: { status: "publish", checked_at: accessedAt, rationale: assignment.rationale || "Newsdesk selected the story after multi-source comparison." },
  };
}

export async function runEditorialCycle(env, scan) {
  const startedAt = nowIso();
  const assignment = await chooseAssignment(env, scan);
  const check = validateAssignment(assignment, scan);
  if (!check.ok) return { status: "hold", stage: "newsdesk", checked_at: startedAt, reason: check.reason, scan_fingerprint: scan.fingerprint };

  const dossier = await buildDossier(env, assignment, check.selected);
  if (dossier.decision !== "publish") return { status: "hold", stage: "fact-check", checked_at: startedAt, reason: dossier.rationale || "Fact check hold", scan_fingerprint: scan.fingerprint };

  const article = await writeArticle(env, assignment, dossier);
  const review = await finalReview(env, assignment, dossier, article);
  if (review.decision !== "pass" || [review.language, review.ethics, review.image, review.seo, review.final_editor].some((x) => x !== "pass")) {
    return { status: "hold", stage: "final-editor", checked_at: startedAt, reason: (review.notes || []).join("; ") || "Final editor hold", scan_fingerprint: scan.fingerprint };
  }

  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const imageKey = `${slug}.jpg`;
  const imageBase64 = await generateHero(env, article);
  const ledger = makeLedger(storyId, slug, assignment, dossier, startedAt);
  const claimIds = ledger.claims.map((c) => c.id);
  const canonical = {
    pipeline_version: 2, status: "ready", release_requested: true, story_id: storyId, slug,
    category: assignment.category, weight: assignment.weight, title: article.title, standfirst: article.standfirst,
    byline: "Morgentidende Redaktion", published_at: null, updated_at: null, manual_review: false,
    ledger: `sources/${slug}.json`, claim_ids: claimIds,
    seo: { title: article.seo_title, description: article.seo_description, canonical: null },
    image: { src: `/img/auto/${imageKey}`, alt: article.hero_alt, credit: "Morgentidende", license: "Morgentidende", source_url: null, image_type: "illustration", placement: "lead" },
    body: article.body, source_ids_to_display: ledger.sources.slice(0, 6).map((s) => s.id), related_news_slug: null, related: [], correction_note: null, scheduled_for: null, released_from_schedule_at: null,
  };
  const approvalSnapshot = JSON.parse(JSON.stringify(canonical));
  for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed"]) delete approvalSnapshot[key];
  const approval = { schema_version: 1, status: "pass", story_id: storyId, article_slug: slug, checked_at: startedAt, gates: { language: "pass", ethics: "pass", image: "pass", seo: "pass", final_editor: "pass" }, editorial_snapshot: approvalSnapshot };

  return {
    status: "approved", schema_version: 1, generated_at: startedAt, scan_fingerprint: scan.fingerprint,
    runtime: "cloudflare-workers-ai", model: TEXT_MODEL, story_id: storyId, slug, article: canonical, ledger, approval,
    media: { key: imageKey, content_type: "image/jpeg", base64: imageBase64 },
    audit: { assignment, final_review: review, source_count: ledger.sources.length, independent_source_groups: ledger.coverage_sweep.independent_source_groups },
  };
}

export function editorialDue(lastRunAt) {
  if (!lastRunAt) return true;
  const then = Date.parse(lastRunAt);
  return !Number.isFinite(then) || Date.now() - then >= 27 * 60 * 1000;
}

export function publicMediaUrl(key) { return `${PUBLIC_BASE}/media/${encodeURIComponent(key)}`; }
