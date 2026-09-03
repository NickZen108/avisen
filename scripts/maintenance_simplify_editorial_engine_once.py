#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
RELEASE = ROOT / 'scripts' / 'release_ready.py'
SYNC = ROOT / 'scripts' / 'sync_cloudflare_editorial.py'
QUALITY = ROOT / 'scripts' / 'quality_gate.py'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing expected fragment: {label}')
    return text.replace(old, new, 1)


# --- editorial.js: one fact owner, no compatibility desk gate, max three article attempts ---
text = EDITORIAL.read_text(encoding='utf-8')
text, n = re.subn(r'\nconst semanticFactCheckSchema = \{.*?\n\};\n\nconst articleSchema', '\nconst articleSchema', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('semanticFactCheckSchema removal failed')
text, n = re.subn(r'\nasync function finalSemanticFactCheck\(.*?\nasync function writeArticle', '\nasync function writeArticle', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('semantic fact-check functions removal failed')
text = replace_once(
    text,
    'gate: { type: "string", enum: ["language", "ethics", "image", "seo", "final_editor"] }, issue: { type: "string" },',
    'gate: { type: "string", enum: ["language", "ethics", "final_editor"] }, issue: { type: "string" },',
    'final schema gate enum',
)
old_final_return = 'return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", image: failed.has("image") ? "hold" : "pass", seo: failed.has("seo") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };'
new_final_return = 'return { decision: issues.length ? "hold" : "pass", language: failed.has("language") ? "hold" : "pass", ethics: failed.has("ethics") ? "hold" : "pass", final_editor: failed.has("final_editor") ? "hold" : "pass", issues, notes: issues.map((x) => `${x.gate}: ${x.issue}`) };'
text = replace_once(text, old_final_return, new_final_return, 'final review return')
old_revise = '''async function reviseFixableIssues(env, assignment, dossier, article, review) {
  const fixable = (review.issues || []).filter((x) => ["language", "seo"].includes(x.gate));
  const hard = (review.issues || []).filter((x) => !["language", "seo"].includes(x.gate));
  if (!fixable.length || hard.length) return article;
  const system = `Ret KUN de konkrete language/seo-problemer. Bevar verificerede fakta, vinkel og betydning. Tilføj ingen nye claims. Lægmandssprog og metriske enheder er obligatoriske.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues: fixable }), articleSchema, 2400, FAST_TEXT_MODEL, STRONG_TEXT_MODEL);
}'''
new_revise = '''async function reviseArticleIssues(env, assignment, dossier, article, review) {
  const issues = (review.issues || []).filter((x) => ["language", "ethics", "final_editor"].includes(x.gate));
  if (!issues.length) return article;
  const system = `Du reparerer en allerede fact-checket artikel. Ret KUN de konkrete problemer fra Slutredaktøren og returnér hele artiklen i samme schema. Brug kun de verificerede claims. Ved language: ret kun sprog og klarhed. Ved final_editor: fjern eller omskriv tekst, der går ud over de verificerede claims; opfind aldrig nye fakta. Ved ethics: tilføj kun fairness/attribution, hvis den nødvendige information allerede findes i de verificerede claims; ellers kan problemet ikke repareres automatisk. SEO må aldrig være blocker. Bevar vinkel og betydning så langt det er forsvarligt.`;
  return aiJson(env, system, JSON.stringify({ assignment, verified_claims: dossier.claims.filter((c) => c.status === "verified"), article, issues }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2200 : 1400, FAST_TEXT_MODEL, null);
}'''
text = replace_once(text, old_revise, new_revise, 'targeted repair function')
old_det = '''  return {
    decision: issues.length ? "hold" : "pass",
    language: failed.has("language") ? "hold" : "pass",
    ethics: "pass",
    image: failed.has("image") ? "hold" : "pass",
    seo: failed.has("seo") ? "hold" : "pass",
    final_editor: failed.has("final_editor") ? "hold" : "pass",
    issues,
    notes: issues.map((x) => `${x.gate}: ${x.issue}`),
    mode: "deterministic-low-risk",
  };'''
new_det = '''  return {
    decision: issues.length ? "hold" : "pass",
    language: failed.has("language") ? "hold" : "pass",
    ethics: "pass",
    final_editor: failed.has("final_editor") ? "hold" : "pass",
    issues,
    notes: issues.map((x) => `${x.gate}: ${x.issue}`),
    mode: "deterministic-low-risk",
  };'''
text = replace_once(text, old_det, new_det, 'deterministic review return')
text = replace_once(text, 'function makeLedger(storyId, slug, assignment, dossier, desk, accessedAt) {', 'function makeLedger(storyId, slug, assignment, dossier, accessedAt) {', 'ledger signature')
text = replace_once(text, 'core_question: dossier.core_question || assignment.core_question, manual_review: false },', 'core_question: dossier.core_question || assignment.core_question },', 'ledger manual_review')
text = replace_once(text, '    desk_recheck: { status: desk.decision, checked_at: accessedAt, rationale: desk.rationale },\n', '', 'ledger desk recheck')

start = text.find('  // Desk recheck gate removed. Fact check + final editor own publication decisions.')
end_marker = '  const ledger = makeLedger(storyId, slug, assignment, dossier, desk, startedAt);'
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('runEditorialCycle replacement anchors missing')
end += len(end_marker)
new_cycle = '''  let article = await writeArticle(env, assignment, dossier);
  article = await polishArticleLanguage(env, assignment, dossier, article);

  const date = startedAt.slice(0, 10);
  const slug = `${date}-${slugify(article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const storyId = `${date}-${slugify(assignment.title_hint || article.title)}`.slice(0, 96).replace(/-+$/g, "");
  const imageKey = `${slug}.jpg`;
  let hero;
  let media;
  if (mediaScout) {
    hero = { ...mediaScout, pending_image: false, ai_generated: false };
    media = {
      kind: "documentary",
      key: imageKey,
      content_type: "image/external",
      url: mediaScout.src,
      source_url: mediaScout.source_url,
      credit: mediaScout.credit,
      license: mediaScout.license,
      image_type: mediaScout.image_type,
    };
  } else {
    const sketch = await generateTemporarySketch(env, assignment, article);
    hero = pendingSketchHero(imageKey, article, sketch);
    media = {
      kind: "generated",
      key: imageKey,
      content_type: sketch.content_type,
      base64: sketch.base64,
      pending_image: true,
      image_type: "illustration",
    };
  }

  const MAX_ARTICLE_ATTEMPTS = 3;
  let articleAttempts = 1;
  const aiFinalRequired = requiresAiFinalReview(assignment, dossier, article);
  let review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);
  while (review.decision !== "pass" && articleAttempts < MAX_ARTICLE_ATTEMPTS) {
    const revised = await reviseArticleIssues(env, assignment, dossier, article, review);
    if (JSON.stringify(revised) === JSON.stringify(article)) break;
    article = revised;
    articleAttempts += 1;
    review = aiFinalRequired ? await finalReview(env, assignment, dossier, article) : deterministicFinalReview(assignment, dossier, article);
  }
  if (review.decision !== "pass") {
    return { status: "drop", stage: "final-editor", checked_at: startedAt, generated_at: startedAt, title: article.title || assignment.title_hint, reason: `Droppet efter ${articleAttempts} artikel-forsøg: ${(review.notes || []).join("; ") || "Slutredaktør godkendte ikke artiklen"}`, scan_fingerprint: scan.fingerprint, handled_signal_keys: handledSignalKeys, audit: { assignment, article_title: article.title, article_attempts: articleAttempts, fact_check: { claims: dossier.claims, rationale: dossier.rationale }, final_review: review } };
  }

  const ledger = makeLedger(storyId, slug, assignment, dossier, startedAt);'''
text = text[:start] + new_cycle + text[end:]
text = replace_once(text, '    byline: "Morgentidende Redaktion", published_at: null, updated_at: null, manual_review: false,', '    byline: "Morgentidende Redaktion", published_at: null, updated_at: null,', 'canonical manual_review')
text = replace_once(text, 'for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "manual_review_completed", "workflow_state"]) delete approvalSnapshot[key];', 'for (const key of ["status", "published_at", "updated_at", "scheduled_for", "released_from_schedule_at", "release_requested", "publication", "workflow_state"]) delete approvalSnapshot[key];', 'approval snapshot legacy key')
text = replace_once(text, 'gates: { language: "pass", ethics: "pass", image: "pass", seo: "pass", final_editor: "pass" }', 'gates: { language: "pass", ethics: "pass", image: "pass", final_editor: "pass" }', 'approval SEO gate')
text = text.replace('fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions, semantic: semanticFactCheck }, desk_recheck: desk, final_review: review,', 'fact_check: { rationale: dossier.rationale, claims: dossier.claims, contradictions: dossier.contradictions }, article_attempts: articleAttempts, final_review: review,')
EDITORIAL.write_text(text, encoding='utf-8')

# --- release_ready.py: release verifies the final ticket; it does not re-run specialist gates ---
text = RELEASE.read_text(encoding='utf-8')
text = text.replace(" 'status','published_at','updated_at','scheduled_for','released_from_schedule_at','release_requested','publication','manual_review','manual_review_completed','workflow_state',\n", " 'status','published_at','updated_at','scheduled_for','released_from_schedule_at','release_requested','publication','workflow_state',\n")
text = text.replace("RETRYABLE={'language','image'}; MAX_RETRIES=3\n", "")
old_diag = ''' else:\n  a=load(ap); gates=a.get('gates') or {}\n  if a.get('status')!='pass': reasons.append('final approval status er ikke PASS'); missing.append('final_editor')\n  for g in ['language','ethics','image']:\n   if gates.get(g)!='pass': reasons.append(f'approval gate {g} er ikke PASS'); missing.append(g)\n  if gates.get('final_editor')!='pass': reasons.append('approval gate final_editor er ikke PASS'); missing.append('final_editor')\n  if snap(a.get('editorial_snapshot'))!=snap(x): reasons.append('artiklens redaktionelle indhold er ændret efter final approval'); missing.append('final_editor')\n priority=['fact_check','language','ethics','image','final_editor']\n return reasons,next((step for step in priority if step in missing),None)'''
new_diag = ''' else:\n  a=load(ap)\n  if a.get('status')!='pass': reasons.append('final approval status er ikke PASS'); missing.append('final_editor')\n  if snap(a.get('editorial_snapshot'))!=snap(x): reasons.append('artiklens redaktionelle indhold er ændret efter final approval'); missing.append('final_editor')\n priority=['fact_check','final_editor']\n return reasons,next((step for step in priority if step in missing),None)'''
text = replace_once(text, old_diag, new_diag, 'release diagnose')
old_route = '''def route_failure(x,resume,reasons,stamp):\n ws=x.get('workflow_state') or {}; retries=ws.get('retry_counts') or {}\n if resume in RETRYABLE:\n  retries[resume]=int(retries.get(resume,0))+1\n  if retries[resume]>=MAX_RETRIES:\n   x['status']='draft'; x['release_requested']=False\n   x['workflow_state']={'state':'dropped','dropped_at':stamp,'dropped_after':MAX_RETRIES,'failed_stage':resume,'reasons':reasons,'retry_counts':retries}\n   return 'dropped'\n x['status']='checking'; x['release_requested']=False\n x['workflow_state']={'state':'blocked','blocked_at':stamp,'resume_from':resume,'reasons':reasons,'retry_counts':retries}\n return 'routed'\n'''
new_route = '''def route_failure(x,resume,reasons,stamp):\n x['status']='checking'; x['release_requested']=False\n x['workflow_state']={'state':'blocked','blocked_at':stamp,'resume_from':resume,'reasons':reasons}\n return 'routed'\n'''
text = replace_once(text, old_route, new_route, 'release routing')
text = text.replace(" stamp=now.replace(microsecond=0).isoformat().replace('+00:00','Z'); released=0; recovered=0; dropped=0; rows=[]", " stamp=now.replace(microsecond=0).isoformat().replace('+00:00','Z'); released=0; recovered=0; rows=[]")
text = text.replace("   outcome=route_failure(x,resume,reasons,stamp); path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8'); repair_frontpage(x.get('slug')); recovered+=1; dropped+=outcome=='dropped'", "   route_failure(x,resume,reasons,stamp); path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8'); repair_frontpage(x.get('slug')); recovered+=1")
text = text.replace(" write_health(rows,stamp); print(f'Ready release: {released}; recovered/parked: {recovered}; dropped after retries: {dropped}'); return 0", " write_health(rows,stamp); print(f'Ready release: {released}; parked invalid tickets: {recovered}'); return 0")
RELEASE.write_text(text, encoding='utf-8')

# --- sync importer: remove references to deleted/retired process layers ---
text = SYNC.read_text(encoding='utf-8')
text = text.replace('from scripts.magazine_policy import infer_new_destination\n', '')
old_gates = '''    for gate in ("language", "ethics", "image", "seo", "final_editor"):\n        if (approval.get("gates") or {}).get(gate) != "pass":\n            fail(f"approval gate {gate} er ikke pass")\n\n'''
text = replace_once(text, old_gates, '', 'sync duplicate approval gates')
text = replace_once(text, '    if (ledger.get("desk_recheck") or {}).get("status") not in {"publish", "update"}:\n        fail("desk recheck er ikke publish/update")\n', '', 'sync desk recheck')
text = replace_once(text, '    destination = infer_new_destination(article)\n', '    destination = str(article.get("editorial_destination") or "main")\n', 'destination fallback')
text = text.replace(', "manual_review_completed"', '')
SYNC.write_text(text, encoding='utf-8')

# --- remove stale category branch that can never be reached ---
text = QUALITY.read_text(encoding='utf-8')
text = text.replace('    if article.get("category") == "Kommentar" and not article.get("related_news_slug"):\n        err(f"{path.name}: Kommentar mangler related_news_slug")\n', '')
QUALITY.write_text(text, encoding='utf-8')

# Sanity: retired process names must no longer exist in active engine/import/release files.
for path in (EDITORIAL, RELEASE, SYNC):
    body = path.read_text(encoding='utf-8')
    for retired in ('desk_recheck', 'manual_review', 'semanticFactCheck'):
        if retired in body:
            raise SystemExit(f'{retired} still present in {path.relative_to(ROOT)}')
print('one-shot editorial engine simplification patch: PASS')
