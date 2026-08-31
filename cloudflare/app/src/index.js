const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function missingConfig(env) {
  const required = ['SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY'];
  return required.filter((k) => !env[k]);
}

function bearerToken(req) {
  const auth = req.headers.get('authorization') || '';
  return auth.startsWith('Bearer ') ? auth.slice(7).trim() : null;
}

function jwtClaims(token) {
  try {
    const part = token.split('.')[1];
    if (!part) return {};
    const normalized = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
    return JSON.parse(atob(padded));
  } catch (_) {
    return {};
  }
}

async function supabaseUser(req, env) {
  const token = bearerToken(req);
  if (!token) return null;
  const res = await fetch(`${env.SUPABASE_URL}/auth/v1/user`, {
    headers: { authorization: `Bearer ${token}`, apikey: env.SUPABASE_PUBLISHABLE_KEY },
  });
  if (!res.ok) return null;
  const user = await res.json();
  return { user, claims: jwtClaims(token) };
}

async function serviceQuery(env, path, init = {}) {
  if (!env.SUPABASE_SERVICE_ROLE_KEY) throw new Error('service role secret missing');
  const headers = new Headers(init.headers || {});
  headers.set('apikey', env.SUPABASE_SERVICE_ROLE_KEY);
  headers.set('authorization', `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`);
  if (!headers.has('content-type')) headers.set('content-type', 'application/json');
  return fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, { ...init, headers });
}

async function rolesFor(userId, env) {
  const r = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(userId)}&select=role`);
  if (!r.ok) throw new Error(`role lookup failed: ${r.status}`);
  return (await r.json()).map((x) => x.role);
}

async function requireUser(req, env, accepted = [], options = {}) {
  const session = await supabaseUser(req, env);
  if (!session) return { error: json({ error: 'unauthorized' }, 401) };
  const roles = await rolesFor(session.user.id, env);
  if (accepted.length && !accepted.some((r) => roles.includes(r))) {
    return { error: json({ error: 'forbidden' }, 403) };
  }
  if (options.requireAal2 && session.claims?.aal !== 'aal2') {
    return { error: json({ error: 'mfa_required', required_aal: 'aal2' }, 403) };
  }
  return { user: session.user, roles, claims: session.claims };
}

async function audit(env, actorId, action, objectType, objectId = null, metadata = {}) {
  await serviceQuery(env, 'audit_log', {
    method: 'POST',
    headers: { Prefer: 'return=minimal' },
    body: JSON.stringify({ actor_id: actorId, action, object_type: objectType, object_id: objectId, metadata }),
  });
}

async function kronikCheck(req, env, user) {
  const body = await req.json();
  const { submission_id, revision_no, content_hash, title, standfirst, text, category } = body;
  if (!submission_id || !revision_no || !content_hash || !title || !text) return json({ error: 'invalid_request' }, 400);

  const prompt = `Du er Kronik-agent på Morgentidende. Kronikører er inviterede gæsteskribenter og skal have stor frihed. Afvis ikke en tekst fordi den er skarp, politisk, personlig, provokerende eller uenig med avisen. Vurder kun publiceringshygiejne: forståeligt dansk, basal kvalitet, åbenlys spam/sabotage, grove personangreb/chikane, doxxing, alvorlige udokumenterede beskyldninger, åbenlys ulovlighed samt klart misvisende form. Returnér JSON med decision PASS, REVISE eller ESCALATE; reasons som korte konkrete danske forklaringer; risk_type. REVISE skal foreslå mindst indgribende rettelse. ESCALATE bruges kun når menneskelig vurdering reelt er nødvendig.`;
  const result = await env.AI.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', {
    messages: [
      { role: 'system', content: prompt },
      { role: 'user', content: JSON.stringify({ title, standfirst, body: text, category }) },
    ],
    temperature: 0.1,
    max_tokens: 1200,
    response_format: { type: 'json_object' },
  });
  let review = result?.response ?? result;
  if (typeof review === 'string') review = JSON.parse(review);
  const decision = String(review.decision || '').toLowerCase();
  if (!['pass', 'revise', 'escalate'].includes(decision)) return json({ error: 'agent_invalid_response' }, 502);

  const save = await serviceQuery(env, 'agent_reviews', {
    method: 'POST', headers: { Prefer: 'return=representation' },
    body: JSON.stringify({ submission_id, revision_no, content_hash, decision, reasons: review.reasons || [], risk_type: review.risk_type || null, model: '@cf/meta/llama-3.3-70b-instruct-fp8-fast' }),
  });
  if (!save.ok) return json({ error: 'review_save_failed' }, 502);
  await audit(env, user.id, `chronicler_agent_${decision}`, 'submission', submission_id, { revision_no, content_hash, reasons: review.reasons || [] });
  return json({ decision: decision.toUpperCase(), reasons: review.reasons || [], risk_type: review.risk_type || null, content_hash });
}

async function createPublishRequest(req, env, user) {
  const body = await req.json();
  const { submission_id, revision_no, content_hash, requested_for } = body;
  if (!submission_id || !revision_no || !content_hash || !requested_for) return json({ error: 'invalid_request' }, 400);

  const reviewRes = await serviceQuery(env, `agent_reviews?submission_id=eq.${encodeURIComponent(submission_id)}&revision_no=eq.${Number(revision_no)}&content_hash=eq.${encodeURIComponent(content_hash)}&decision=eq.pass&select=id&order=created_at.desc&limit=1`);
  if (!reviewRes.ok || !(await reviewRes.json()).length) return json({ error: 'fresh_agent_pass_required' }, 409);

  const idempotency_key = `${submission_id}:${revision_no}:${content_hash}:${requested_for}`;
  const r = await serviceQuery(env, 'publish_requests', {
    method: 'POST', headers: { Prefer: 'resolution=ignore-duplicates,return=representation' },
    body: JSON.stringify({ submission_id, requested_by: user.id, requested_for, revision_no, content_hash, idempotency_key }),
  });
  if (!r.ok) return json({ error: 'publish_request_failed' }, 502);
  await audit(env, user.id, 'publish_requested', 'submission', submission_id, { requested_for, revision_no, content_hash });
  return json({ ok: true, request: (await r.json())[0] || null }, 202);
}

async function uploadHero(req, env, user) {
  const type = req.headers.get('content-type') || '';
  const allowed = new Set(['image/jpeg', 'image/png', 'image/webp']);
  if (!allowed.has(type)) return json({ error: 'unsupported_media_type' }, 415);
  const bytes = await req.arrayBuffer();
  if (!bytes.byteLength || bytes.byteLength > 10 * 1024 * 1024) return json({ error: 'file_too_large' }, 413);
  const ext = type === 'image/jpeg' ? 'jpg' : type === 'image/png' ? 'png' : 'webp';
  const key = `uploads/${user.id}/${crypto.randomUUID()}.${ext}`;
  await env.MEDIA.put(key, bytes, { httpMetadata: { contentType: type } });
  await audit(env, user.id, 'media_uploaded', 'r2_object', key, { byte_size: bytes.byteLength, mime_type: type });
  return json({ key, mime_type: type, byte_size: bytes.byteLength }, 201);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const missing = missingConfig(env);
    if (url.pathname === '/health') return json({ ok: missing.length === 0, missing_config: missing });
    if (missing.length) return json({ error: 'not_configured', missing }, 503);

    try {
      if (url.pathname === '/api/me' && req.method === 'GET') {
        const auth = await requireUser(req, env);
        if (auth.error) return auth.error;
        return json({ user: { id: auth.user.id, email: auth.user.email }, roles: auth.roles, aal: auth.claims?.aal || 'aal1' });
      }
      if (url.pathname === '/api/kronik/check' && req.method === 'POST') {
        const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']);
        if (auth.error) return auth.error;
        return kronikCheck(req, env, auth.user);
      }
      if (url.pathname === '/api/kronik/publish-request' && req.method === 'POST') {
        const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']);
        if (auth.error) return auth.error;
        return createPublishRequest(req, env, auth.user);
      }
      if (url.pathname === '/api/media/hero' && req.method === 'PUT') {
        const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']);
        if (auth.error) return auth.error;
        return uploadHero(req, env, auth.user);
      }
      if (url.pathname.startsWith('/api/admin/')) {
        const auth = await requireUser(req, env, ['admin'], { requireAal2: true });
        if (auth.error) return auth.error;
        return json({ ok: true, aal: auth.claims?.aal, note: 'Admin route requires app admin role + MFA (AAL2); Cloudflare Access must also protect the control-room hostname.' });
      }
      return json({ error: 'not_found' }, 404);
    } catch (error) {
      console.error(error);
      return json({ error: 'internal_error' }, 500);
    }
  },
};
