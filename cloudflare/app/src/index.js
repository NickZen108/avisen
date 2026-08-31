const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' };
const PUBLIC_SITE = 'https://morgentidende.nicolaipetersen108.workers.dev';

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...extraHeaders } });
}

function htmlPage(title, body, status = 200, extraHeaders = {}) {
  return new Response(`<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)} – Morgentidende</title><style>body{font-family:system-ui,sans-serif;background:#f8f5ef;color:#171717;margin:0}.wrap{max-width:720px;margin:8vh auto;padding:28px;background:white;border:1px solid #d8d2c8}h1{font-family:Georgia,serif}a{color:#1b2430}.roles{color:#666}.actions{display:flex;gap:14px;flex-wrap:wrap;margin-top:24px}</style></head><body><main class="wrap">${body}</main></body></html>`, { status, headers: { 'content-type': 'text/html; charset=utf-8', ...extraHeaders } });
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
}

function missingConfig(env) {
  const required = ['SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY'];
  return required.filter((k) => !env[k]);
}

function cookieValue(req, name) {
  const raw = req.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key === name) return decodeURIComponent(rest.join('='));
  }
  return null;
}

function bearerToken(req) {
  const auth = req.headers.get('authorization') || '';
  if (auth.startsWith('Bearer ')) return auth.slice(7).trim();
  return cookieValue(req, 'mt_access');
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
  return { user, claims: jwtClaims(token), token };
}

async function serviceQuery(env, path, init = {}) {
  if (!env.SUPABASE_SECRET_KEY) throw new Error('supabase secret key missing');
  const headers = new Headers(init.headers || {});
  headers.set('apikey', env.SUPABASE_SECRET_KEY);
  if (!headers.has('content-type')) headers.set('content-type', 'application/json');
  return fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, { ...init, headers });
}

function expandRoles(roles) {
  const out = new Set(roles || []);
  if (out.has('admin')) ['reader', 'chronicler', 'editor'].forEach((r) => out.add(r));
  if (out.has('editor')) ['reader', 'chronicler'].forEach((r) => out.add(r));
  if (out.has('chronicler')) out.add('reader');
  return [...out];
}

async function bootstrapGrantedRoles(user, env) {
  if (!user?.id || !user?.email || !user?.email_confirmed_at) return;
  const email = user.email.trim().toLowerCase();
  const grantRes = await serviceQuery(env, `access_grants?email=eq.${encodeURIComponent(email)}&select=roles&limit=1`);
  if (!grantRes.ok) throw new Error(`access grant lookup failed: ${grantRes.status}`);
  const grants = await grantRes.json();
  if (!grants.length) return;
  const desired = expandRoles(grants[0].roles || []);
  const currentRes = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(user.id)}&select=role`);
  if (!currentRes.ok) throw new Error(`role lookup failed: ${currentRes.status}`);
  const current = new Set((await currentRes.json()).map((x) => x.role));
  const missing = desired.filter((role) => !current.has(role));
  if (!missing.length) return;
  const insert = await serviceQuery(env, 'user_roles', {
    method: 'POST',
    headers: { Prefer: 'resolution=ignore-duplicates,return=minimal' },
    body: JSON.stringify(missing.map((role) => ({ user_id: user.id, role, granted_by: user.id }))),
  });
  if (!insert.ok) throw new Error(`role bootstrap failed: ${insert.status}`);
  await audit(env, user.id, 'roles_bootstrapped', 'user', user.id, { roles: missing });
}

async function rolesFor(userId, env) {
  const r = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(userId)}&select=role`);
  if (!r.ok) throw new Error(`role lookup failed: ${r.status}`);
  return expandRoles((await r.json()).map((x) => x.role));
}

async function requireUser(req, env, accepted = [], options = {}) {
  const session = await supabaseUser(req, env);
  if (!session) return { error: json({ error: 'unauthorized' }, 401) };
  await bootstrapGrantedRoles(session.user, env);
  const roles = await rolesFor(session.user.id, env);
  if (accepted.length && !accepted.some((r) => roles.includes(r))) {
    return { error: json({ error: 'forbidden' }, 403) };
  }
  if (options.requireAal2 && session.claims?.aal !== 'aal2') {
    return { error: json({ error: 'mfa_required', required_aal: 'aal2' }, 403) };
  }
  return { user: session.user, roles, claims: session.claims, token: session.token };
}

async function audit(env, actorId, action, objectType, objectId = null, metadata = {}) {
  await serviceQuery(env, 'audit_log', {
    method: 'POST',
    headers: { Prefer: 'return=minimal' },
    body: JSON.stringify({ actor_id: actorId, action, object_type: objectType, object_id: objectId, metadata }),
  });
}

async function requestFields(req) {
  const type = req.headers.get('content-type') || '';
  if (type.includes('application/json')) return req.json();
  const form = await req.formData();
  return Object.fromEntries(form.entries());
}

function authCookies(session) {
  const ttl = Math.max(60, Number(session.expires_in || 3600));
  return [
    `mt_access=${encodeURIComponent(session.access_token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${ttl}`,
    `mt_refresh=${encodeURIComponent(session.refresh_token || '')}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`,
  ];
}

async function authSession(req, env) {
  const fields = await requestFields(req);
  const email = String(fields.email || '').trim().toLowerCase();
  const password = String(fields.password || '');
  const mode = fields.mode === 'signup' ? 'signup' : 'login';
  if (!email || password.length < 8) return htmlPage('Login', '<h1>Kunne ikke fortsætte</h1><p>Indtast en gyldig e-mail og en adgangskode på mindst 8 tegn.</p><p><a href="'+PUBLIC_SITE+'/login.html">Tilbage til login</a></p>', 400);
  const endpoint = mode === 'signup' ? `${env.SUPABASE_URL}/auth/v1/signup` : `${env.SUPABASE_URL}/auth/v1/token?grant_type=password`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json', apikey: env.SUPABASE_PUBLISHABLE_KEY },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return htmlPage('Login', `<h1>Login mislykkedes</h1><p>${escapeHtml(data.msg || data.message || data.error_description || 'Kontrollér e-mail og adgangskode.')}</p><p><a href="${PUBLIC_SITE}/login.html">Prøv igen</a></p>`, 401);
  }
  if (mode === 'signup' && !data.access_token) {
    return htmlPage('Bekræft e-mail', `<h1>Tjek din indbakke</h1><p>Vi har sendt en bekræftelse til <strong>${escapeHtml(email)}</strong>. Når e-mailen er bekræftet, kan du logge ind.</p><p><a href="${PUBLIC_SITE}/login.html">Til login</a></p>`);
  }
  const user = data.user;
  if (user) await bootstrapGrantedRoles(user, env);
  const roles = user ? await rolesFor(user.id, env) : [];
  if (user) await audit(env, user.id, 'login', 'user', user.id, { roles });
  const headers = new Headers({ location: '/account' });
  for (const cookie of authCookies(data)) headers.append('set-cookie', cookie);
  return new Response(null, { status: 303, headers });
}

async function accountPage(req, env) {
  const auth = await requireUser(req, env);
  if (auth.error) return Response.redirect(`${PUBLIC_SITE}/login.html`, 303);
  const isAdmin = auth.roles.includes('admin');
  const isChronicler = auth.roles.includes('chronicler');
  const mfaNote = isAdmin && auth.claims?.aal !== 'aal2' ? '<p><strong>Admin:</strong> 2-faktor-login skal aktiveres, før Kontrolrummet kan udføre adminhandlinger.</p>' : '';
  const actions = [`<a href="${PUBLIC_SITE}/">Til avisen</a>`, `<a href="${PUBLIC_SITE}/abonnement.html">Abonnement</a>`];
  if (isChronicler) actions.push(`<a href="${PUBLIC_SITE}/kronikoer/">Kronikørdesk</a>`);
  if (isAdmin) actions.push(`<a href="${PUBLIC_SITE}/kontrolrum/">Kontrolrum</a>`);
  return htmlPage('Konto', `<h1>Velkommen</h1><p>${escapeHtml(auth.user.email || '')}</p>${mfaNote}<p class="roles">Adgang: ${escapeHtml(auth.roles.join(', '))}</p><div class="actions">${actions.join('')}</div><form method="post" action="/auth/logout" style="margin-top:28px"><button type="submit">Log ud</button></form>`);
}

function logout() {
  const headers = new Headers({ location: `${PUBLIC_SITE}/` });
  headers.append('set-cookie', 'mt_access=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0');
  headers.append('set-cookie', 'mt_refresh=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0');
  return new Response(null, { status: 303, headers });
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
      if (url.pathname === '/auth/session' && req.method === 'POST') return authSession(req, env);
      if (url.pathname === '/auth/logout' && req.method === 'POST') return logout();
      if (url.pathname === '/account' && req.method === 'GET') return accountPage(req, env);
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
