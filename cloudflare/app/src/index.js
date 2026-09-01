const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' };
const PUBLIC_SITE = 'https://morgentidende.nicolaipetersen108.workers.dev';

function json(data, status = 200, extraHeaders = {}) { return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...extraHeaders } }); }
function htmlPage(title, body, status = 200, extraHeaders = {}) { return new Response(`<!doctype html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${escapeHtml(title)} – Morgentidende</title><style>body{font-family:system-ui,sans-serif;background:#f8f5ef;color:#171717;margin:0}.wrap{max-width:720px;margin:6vh auto;padding:28px;background:white;border:1px solid #d8d2c8}h1{font-family:Georgia,serif}a{color:#1b2430}.roles{color:#666}.actions{display:flex;gap:14px;flex-wrap:wrap;margin-top:24px}form{margin:18px 0}input{padding:10px;margin:5px 0;max-width:100%}button{padding:10px 14px}.qr{max-width:260px;width:100%;height:auto}.secret{word-break:break-all;font-family:monospace;background:#eee;padding:8px}</style></head><body><main class="wrap">${body}</main></body></html>`, { status, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', ...extraHeaders } }); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch])); }
function missingConfig(env) { return ['SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY'].filter((k) => !env[k]); }
function cookieValue(req, name) { const raw = req.headers.get('cookie') || ''; for (const part of raw.split(';')) { const [key, ...rest] = part.trim().split('='); if (key === name) return decodeURIComponent(rest.join('=')); } return null; }
function bearerToken(req) { const auth = req.headers.get('authorization') || ''; return auth.startsWith('Bearer ') ? auth.slice(7).trim() : cookieValue(req, 'mt_access'); }
function jwtClaims(token) { try { const part = token.split('.')[1]; if (!part) return {}; const normalized = part.replace(/-/g, '+').replace(/_/g, '/'); const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4); return JSON.parse(atob(padded)); } catch (_) { return {}; } }

function authCookies(session) {
  const ttl = Math.max(60, Number(session.expires_in || 3600));
  return [
    `mt_access=${encodeURIComponent(session.access_token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${ttl}`,
    `mt_refresh=${encodeURIComponent(session.refresh_token || '')}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`,
  ];
}
function withCookies(response, cookies = []) { if (!cookies.length) return response; const headers = new Headers(response.headers); for (const c of cookies) headers.append('set-cookie', c); return new Response(response.body, { status: response.status, statusText: response.statusText, headers }); }
async function authFetch(env, path, token, init = {}) { const headers = new Headers(init.headers || {}); headers.set('apikey', env.SUPABASE_PUBLISHABLE_KEY); if (token) headers.set('authorization', `Bearer ${token}`); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); return fetch(`${env.SUPABASE_URL}/auth/v1/${path}`, { ...init, headers }); }
async function userForToken(token, env) { if (!token) return null; const res = await authFetch(env, 'user', token, { method: 'GET' }); if (!res.ok) return null; return res.json(); }
async function refreshedSession(req, env) { const refresh = cookieValue(req, 'mt_refresh'); if (!refresh) return null; const res = await authFetch(env, 'token?grant_type=refresh_token', null, { method: 'POST', body: JSON.stringify({ refresh_token: refresh }) }); if (!res.ok) return null; const data = await res.json(); if (!data.access_token) return null; const user = data.user || await userForToken(data.access_token, env); if (!user) return null; return { user, claims: jwtClaims(data.access_token), token: data.access_token, cookies: authCookies(data) }; }
async function supabaseSession(req, env) { const token = bearerToken(req); const user = await userForToken(token, env); if (user) return { user, claims: jwtClaims(token), token, cookies: [] }; return refreshedSession(req, env); }

async function serviceQuery(env, path, init = {}) { if (!env.SUPABASE_SECRET_KEY) throw new Error('supabase secret key missing'); const headers = new Headers(init.headers || {}); headers.set('apikey', env.SUPABASE_SECRET_KEY); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); return fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, { ...init, headers }); }
async function adminAuthFetch(env, path, init = {}) { if (!env.SUPABASE_SECRET_KEY) throw new Error('supabase secret key missing'); const headers = new Headers(init.headers || {}); headers.set('apikey', env.SUPABASE_SECRET_KEY); headers.set('authorization', `Bearer ${env.SUPABASE_SECRET_KEY}`); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); return fetch(`${env.SUPABASE_URL}/auth/v1/${path}`, { ...init, headers }); }
async function rowsOrThrow(response, label) { if (!response.ok) throw new Error(`${label} failed: ${response.status}`); return response.json(); }
function dkDay(value = new Date()) { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Copenhagen', year: 'numeric', month: '2-digit', day: '2-digit' }).format(value); }
function safeHost(value) { try { return value ? new URL(value).hostname.slice(0, 180) : null; } catch (_) { return null; } }
function allowedAnalyticsOrigin(origin) { if (!origin) return false; if (origin === PUBLIC_SITE || origin === 'https://morgentidende.hostingersite.com') return true; return /^https:\/\/(?:www\.)?morgentidende\.dk$/i.test(origin); }
async function pageview(req, env) {
  const origin = req.headers.get('origin') || '';
  const cors = allowedAnalyticsOrigin(origin) ? { 'access-control-allow-origin': origin, 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'content-type', 'vary': 'Origin' } : {};
  if (req.method === 'OPTIONS') return new Response(null, { status: allowedAnalyticsOrigin(origin) ? 204 : 403, headers: cors });
  if (!allowedAnalyticsOrigin(origin)) return json({ error: 'forbidden_origin' }, 403);
  const data = await req.json().catch(() => ({}));
  const slug = String(data.slug || '').trim().slice(0, 160);
  if (!/^[a-z0-9][a-z0-9-]{4,159}$/i.test(slug)) return json({ error: 'invalid_slug' }, 400, cors);
  const row = { article_slug: slug, title: String(data.title || '').trim().slice(0, 240), category: String(data.category || '').trim().slice(0, 80), referrer_host: safeHost(data.referrer || '') };
  const inserted = await serviceQuery(env, 'traffic_events', { method: 'POST', headers: { Prefer: 'return=minimal' }, body: JSON.stringify(row) });
  if (!inserted.ok) return json({ error: 'analytics_insert_failed' }, 503, cors);
  return new Response(null, { status: 204, headers: cors });
}
async function controlChroniclers(env) {
  const roles = await rowsOrThrow(await serviceQuery(env, 'user_roles?role=in.(chronicler,editor,admin)&select=user_id,role'), 'role list');
  const byUser = new Map(); for (const row of roles) { const set = byUser.get(row.user_id) || new Set(); set.add(row.role); byUser.set(row.user_id, set); }
  const ids = [...byUser.entries()].filter(([, rs]) => rs.has('chronicler') && !rs.has('editor') && !rs.has('admin')).map(([id]) => id);
  if (!ids.length) return json({ chroniclers: [] });
  const inIds = `(${ids.join(',')})`;
  const [profiles, submissions, authResult] = await Promise.all([
    rowsOrThrow(await serviceQuery(env, `profiles?user_id=in.${encodeURIComponent(inIds)}&select=user_id,display_name,created_at`), 'profiles'),
    rowsOrThrow(await serviceQuery(env, `submissions?author_id=in.${encodeURIComponent(inIds)}&select=id,author_id,title,status,published_at,github_slug,created_at&order=created_at.desc`), 'submissions'),
    adminAuthFetch(env, 'admin/users?page=1&per_page=1000', { method: 'GET' }).then(async r => r.ok ? r.json() : ({ users: [] })),
  ]);
  const emails = new Map((authResult.users || []).map(u => [u.id, u.email || null]));
  const profileMap = new Map(profiles.map(p => [p.user_id, p]));
  const chroniclers = ids.map(id => ({ user_id: id, display_name: profileMap.get(id)?.display_name || emails.get(id) || 'Ukendt kronikør', email: emails.get(id) || null, created_at: profileMap.get(id)?.created_at || null, chronicles: submissions.filter(s => s.author_id === id).map(s => ({ id: s.id, title: s.title, status: s.status, published_at: s.published_at, created_at: s.created_at, url: s.github_slug ? `${PUBLIC_SITE}/artikler/${s.github_slug}.html` : null })) }));
  return json({ chroniclers });
}
function revenueSummary(rows, days) { const now = Date.now(), cutoff = now - days * 86400000, today = dkDay(); const use = rows.filter(r => { const t = Date.parse(r.occurred_at); return Number.isFinite(t) && (days === 0 ? dkDay(new Date(t)) === today : t >= cutoff); }); const sum = source => use.filter(r => r.source === source).reduce((a, r) => a + Number(r.gross_amount_ore || 0), 0); return { gross_ore: sum('subscription') + sum('advertising'), subscription_ore: sum('subscription'), advertising_ore: sum('advertising'), events: use.length }; }
async function controlRevenue(env) {
  const cutoff = new Date(Date.now() - 31 * 86400000).toISOString();
  const [events, subscriptions] = await Promise.all([
    rowsOrThrow(await serviceQuery(env, `revenue_events?occurred_at=gte.${encodeURIComponent(cutoff)}&select=occurred_at,source,gross_amount_ore,currency&order=occurred_at.desc&limit=10000`), 'revenue events'),
    rowsOrThrow(await serviceQuery(env, 'subscriptions?select=tier,status,current_period_end,updated_at'), 'subscriptions'),
  ]);
  const active = subscriptions.filter(s => ['active','trialing'].includes(String(s.status || '').toLowerCase()));
  return json({ currency: 'DKK', today: revenueSummary(events, 0), days7: revenueSummary(events, 7), days30: revenueSummary(events, 30), active_subscriptions: active.length, by_tier: active.reduce((a, s) => (a[s.tier || 'ukendt'] = (a[s.tier || 'ukendt'] || 0) + 1, a), {}), data_connected: events.length > 0, note: events.length ? null : 'Ingen betalings- eller reklameindtægter er registreret endnu. Fanen viser kun faktiske revenue-events; der opfindes ikke omsætning.' });
}
function topStories(rows, days) { const today = dkDay(), cutoff = Date.now() - days * 86400000; const use = rows.filter(r => { const t = Date.parse(r.occurred_at); return Number.isFinite(t) && (days === 0 ? dkDay(new Date(t)) === today : t >= cutoff); }); const map = new Map(); for (const r of use) { const key = r.article_slug; const x = map.get(key) || { slug: key, title: r.title || key, category: r.category || 'Ukendt', views: 0 }; x.views++; if (r.title) x.title = r.title; if (r.category) x.category = r.category; map.set(key, x); } return [...map.values()].sort((a,b) => b.views - a.views).slice(0, 30); }
function trafficRecommendations(rows) { if (rows.length < 20) return ['Der er endnu for lidt trafik til stærke anbefalinger. Vent til mindst cirka 20 registrerede artikelvisninger.']; const cats = new Map(); const refs = new Map(); for (const r of rows) { cats.set(r.category || 'Ukendt', (cats.get(r.category || 'Ukendt') || 0) + 1); refs.set(r.referrer_host || 'Direkte/ukendt', (refs.get(r.referrer_host || 'Direkte/ukendt') || 0) + 1); } const topCat = [...cats].sort((a,b)=>b[1]-a[1])[0]; const topRef = [...refs].sort((a,b)=>b[1]-a[1])[0]; const rec = []; if (topCat) rec.push(`${topCat[0]} står for ${Math.round(topCat[1]*100/rows.length)}% af de målte artikelvisninger. Overvej lidt mere kapacitet til emnet, men behold redaktionel bredde.`); if (topRef) rec.push(`${topRef[0]} er største målte trafikkilde med ${Math.round(topRef[1]*100/rows.length)}%. Brug det som distributionssignal, ikke som automatisk lead-kriterium.`); rec.push('Brug trafik som sekundært signal: gentag stærke emner og formater, men lad nyhedsværdi, fakta og pluralisme styre publiceringen.'); return rec; }
async function controlTraffic(env) {
  const cutoff = new Date(Date.now() - 31 * 86400000).toISOString();
  const rows = await rowsOrThrow(await serviceQuery(env, `traffic_events?occurred_at=gte.${encodeURIComponent(cutoff)}&select=occurred_at,article_slug,title,category,referrer_host&order=occurred_at.desc&limit=50000`), 'traffic events');
  const days30rows = rows.filter(r => Date.parse(r.occurred_at) >= Date.now() - 30 * 86400000);
  return json({ today: topStories(rows, 0), days7: topStories(rows, 7), days30: topStories(rows, 30), total_views_30d: days30rows.length, recommendations: trafficRecommendations(days30rows), measurement_started: rows.length > 0 });
}
async function controlFunnel() {
  const endpoint = 'https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/editorial/history';
  const response = await fetch(endpoint, { headers: { 'user-agent': 'MorgentidendeControlRoom/1.0' }, cf: { cacheTtl: 0 } });
  if (!response.ok) return json({ error: 'funnel_source_unavailable', status: response.status }, 503);
  const rows = await response.json();
  const downstream = (Array.isArray(rows) ? rows : []).filter(r => (r.stage || 'approved') !== 'newsdesk');
  const approved = downstream.filter(r => r.status === 'approved');
  const parked = downstream.filter(r => r.status === 'watch');
  const rejected = downstream.filter(r => !['approved', 'watch'].includes(r.status));
  const stageCounts = {};
  const reasonCounts = new Map();
  let metered = 0, calls = 0, tokens = 0, neurons = 0;
  for (const r of downstream) {
    const stage = r.stage || 'approved'; stageCounts[stage] = (stageCounts[stage] || 0) + 1;
    if (r.status !== 'approved') {
      const key = `${stage}|||${r.reason || ''}`; reasonCounts.set(key, (reasonCounts.get(key) || 0) + 1);
    }
    const u = r.ai_usage || null;
    if (u) { metered++; calls += Number(u.calls || 0); tokens += Number(u.total_tokens || 0); neurons += Number(u.estimated_neurons || 0); }
  }
  const denominator = downstream.length;
  const rate = denominator ? rejected.length * 100 / denominator : null;
  const topStopReasons = [...reasonCounts.entries()].sort((a,b) => b[1]-a[1]).slice(0,12).map(([key,count]) => { const [stage, reason] = key.split('|||'); return { stage, reason, count }; });
  return json({
    history_rows: Array.isArray(rows) ? rows.length : 0,
    post_newsdesk_attempts: denominator,
    approved: approved.length,
    parked_watch: parked.length,
    rejected_or_held: rejected.length,
    post_newsdesk_rejection_rate_pct: rate == null ? null : Math.round(rate * 100) / 100,
    long_term_target_pct: 10,
    stage_counts: stageCounts,
    top_stop_reasons: topStopReasons,
    metered_attempts: metered,
    total_ai_calls: Math.round(calls),
    total_tokens: Math.round(tokens),
    estimated_neurons: Math.round(neurons * 1000) / 1000,
    avg_tokens_per_metered_attempt: metered ? Math.round(tokens / metered * 10) / 10 : null,
    avg_neurons_per_metered_attempt: metered ? Math.round(neurons / metered * 1000) / 1000 : null,
    note: 'Forsøg tælles, så retries af samme historie kan optræde flere gange.'
  });
}
async function fireChronicler(req, env, actor) {
  const data = await req.json().catch(() => ({})); const userId = String(data.user_id || '').trim();
  if (!/^[0-9a-f-]{36}$/i.test(userId)) return json({ error: 'invalid_user_id' }, 400);
  if (userId === actor.id) return json({ error: 'cannot_fire_self' }, 400);
  const roles = await rowsOrThrow(await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(userId)}&select=role`), 'target roles');
  const roleSet = new Set(roles.map(r => r.role));
  if (!roleSet.has('chronicler') || roleSet.has('admin') || roleSet.has('editor')) return json({ error: 'target_is_not_fireable_chronicler' }, 409);
  const userRes = await adminAuthFetch(env, `admin/users/${encodeURIComponent(userId)}`, { method: 'GET' }); const user = userRes.ok ? await userRes.json() : null;
  if (user?.email) await serviceQuery(env, `access_grants?email=eq.${encodeURIComponent(String(user.email).toLowerCase())}`, { method: 'DELETE', headers: { Prefer: 'return=minimal' } });
  const delRoles = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(userId)}`, { method: 'DELETE', headers: { Prefer: 'return=minimal' } }); if (!delRoles.ok) throw new Error(`role revoke failed: ${delRoles.status}`);
  const ban = await adminAuthFetch(env, `admin/users/${encodeURIComponent(userId)}`, { method: 'PUT', body: JSON.stringify({ ban_duration: '876000h' }) }); if (!ban.ok) throw new Error(`login ban failed: ${ban.status}`);
  await audit(env, actor.id, 'chronicler_fired', 'user', userId, { email: user?.email || null, login_banned: true, roles_removed: true });
  return json({ ok: true, user_id: userId, login_removed: true });
}
function expandRoles(roles) { const out = new Set(roles || []); if (out.has('admin')) ['reader', 'chronicler', 'editor'].forEach((r) => out.add(r)); if (out.has('editor')) ['reader', 'chronicler'].forEach((r) => out.add(r)); if (out.has('chronicler')) out.add('reader'); return [...out]; }
async function audit(env, actorId, action, objectType, objectId = null, metadata = {}) { await serviceQuery(env, 'audit_log', { method: 'POST', headers: { Prefer: 'return=minimal' }, body: JSON.stringify({ actor_id: actorId, action, object_type: objectType, object_id: objectId, metadata }) }); }
async function bootstrapGrantedRoles(user, env) { if (!user?.id || !user?.email || !user?.email_confirmed_at) return; const email = user.email.trim().toLowerCase(); const grantRes = await serviceQuery(env, `access_grants?email=eq.${encodeURIComponent(email)}&select=roles&limit=1`); if (!grantRes.ok) throw new Error(`access grant lookup failed: ${grantRes.status}`); const grants = await grantRes.json(); if (!grants.length) return; const desired = expandRoles(grants[0].roles || []); const currentRes = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(user.id)}&select=role`); if (!currentRes.ok) throw new Error(`role lookup failed: ${currentRes.status}`); const current = new Set((await currentRes.json()).map((x) => x.role)); const missing = desired.filter((role) => !current.has(role)); if (!missing.length) return; const insert = await serviceQuery(env, 'user_roles', { method: 'POST', headers: { Prefer: 'resolution=ignore-duplicates,return=minimal' }, body: JSON.stringify(missing.map((role) => ({ user_id: user.id, role, granted_by: user.id }))) }); if (!insert.ok) throw new Error(`role bootstrap failed: ${insert.status}`); await audit(env, user.id, 'roles_bootstrapped', 'user', user.id, { roles: missing }); }
async function rolesFor(userId, env) { const r = await serviceQuery(env, `user_roles?user_id=eq.${encodeURIComponent(userId)}&select=role`); if (!r.ok) throw new Error(`role lookup failed: ${r.status}`); return expandRoles((await r.json()).map((x) => x.role)); }
async function requireUser(req, env, accepted = [], options = {}) { const session = await supabaseSession(req, env); if (!session) return { error: json({ error: 'unauthorized' }, 401) }; await bootstrapGrantedRoles(session.user, env); const roles = await rolesFor(session.user.id, env); if (accepted.length && !accepted.some((r) => roles.includes(r))) return { error: json({ error: 'forbidden' }, 403) }; if (options.requireAal2 && session.claims?.aal !== 'aal2') return { error: json({ error: 'mfa_required', required_aal: 'aal2' }, 403) }; return { user: session.user, roles, claims: session.claims, token: session.token, cookies: session.cookies || [] }; }
async function requestFields(req) { const type = req.headers.get('content-type') || ''; if (type.includes('application/json')) return req.json(); const form = await req.formData(); return Object.fromEntries(form.entries()); }

async function listFactors(token, env) { const r = await authFetch(env, 'factors', token, { method: 'GET' }); if (!r.ok) return []; const data = await r.json(); const rows = Array.isArray(data) ? data : [...(data.totp || []), ...(data.phone || [])]; return rows; }
async function authSession(req, env) {
  const fields = await requestFields(req); const email = String(fields.email || '').trim().toLowerCase(); const password = String(fields.password || ''); const mode = fields.mode === 'signup' ? 'signup' : 'login';
  if (!email || password.length < 8) return htmlPage('Login', '<h1>Kunne ikke fortsætte</h1><p>Indtast en gyldig e-mail og en adgangskode på mindst 8 tegn.</p><p><a href="'+PUBLIC_SITE+'/login.html">Tilbage til login</a></p>', 400);
  const endpoint = mode === 'signup' ? 'signup' : 'token?grant_type=password'; const res = await authFetch(env, endpoint, null, { method: 'POST', body: JSON.stringify({ email, password }) }); const data = await res.json().catch(() => ({}));
  if (!res.ok) return htmlPage('Login', `<h1>Login mislykkedes</h1><p>${escapeHtml(data.msg || data.message || data.error_description || 'Kontrollér e-mail og adgangskode.')}</p><p><a href="${PUBLIC_SITE}/login.html">Prøv igen</a></p>`, 401);
  if (mode === 'signup' && !data.access_token) return htmlPage('Bekræft e-mail', `<h1>Tjek din indbakke</h1><p>Vi har sendt en bekræftelse til <strong>${escapeHtml(email)}</strong>.</p><p><a href="${PUBLIC_SITE}/login.html">Til login</a></p>`);
  const user = data.user; if (user) await bootstrapGrantedRoles(user, env); const roles = user ? await rolesFor(user.id, env) : []; if (user) await audit(env, user.id, 'login', 'user', user.id, { roles });
  let location = '/account'; if (roles.includes('admin')) { const factors = await listFactors(data.access_token, env); if (factors.some((f) => f.status === 'verified')) location = '/security/mfa'; }
  const headers = new Headers({ location }); for (const cookie of authCookies(data)) headers.append('set-cookie', cookie); return new Response(null, { status: 303, headers });
}
async function refreshRoute(req, env) { const s = await refreshedSession(req, env); if (!s) return Response.redirect(`${PUBLIC_SITE}/login.html`, 303); const next = new URL(req.url).searchParams.get('next') || '/account'; return withCookies(new Response(null, { status: 303, headers: { location: next.startsWith('/') ? next : '/account' } }), s.cookies); }
async function accountPage(req, env) { const auth = await requireUser(req, env); if (auth.error) return Response.redirect(`${PUBLIC_SITE}/login.html`, 303); const isAdmin = auth.roles.includes('admin'); const isChronicler = auth.roles.includes('chronicler'); const mfaNote = isAdmin && auth.claims?.aal !== 'aal2' ? '<p><strong>Admin:</strong> Gennemfør 2-faktor-login før administrative handlinger.</p>' : ''; const actions = [`<a href="${PUBLIC_SITE}/">Til avisen</a>`, `<a href="${PUBLIC_SITE}/abonnement.html">Abonnement</a>`, '<a href="/security/mfa">2-faktor-sikkerhed</a>']; if (isChronicler) actions.push(`<a href="${PUBLIC_SITE}/kronikoer/">Kronikørdesk</a>`); if (isAdmin) actions.push(`<a href="${PUBLIC_SITE}/kontrolrum/">Kontrolrum</a>`); return withCookies(htmlPage('Konto', `<h1>Velkommen</h1><p>${escapeHtml(auth.user.email || '')}</p>${mfaNote}<p class="roles">Adgang: ${escapeHtml(auth.roles.join(', '))} · ${escapeHtml(auth.claims?.aal || 'aal1')}</p><div class="actions">${actions.join('')}</div><form method="post" action="/auth/logout"><button type="submit">Log ud</button></form>`), auth.cookies); }
function logout() { const headers = new Headers({ location: `${PUBLIC_SITE}/` }); headers.append('set-cookie', 'mt_access=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0'); headers.append('set-cookie', 'mt_refresh=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0'); return new Response(null, { status: 303, headers }); }

async function mfaPage(req, env) { const auth = await requireUser(req, env); if (auth.error) return Response.redirect(`${PUBLIC_SITE}/login.html`, 303); const factors = await listFactors(auth.token, env); const verified = factors.filter((f) => f.status === 'verified'); let body = `<h1>2-faktor-sikkerhed</h1><p>Aktuelt sikkerhedsniveau: <strong>${escapeHtml(auth.claims?.aal || 'aal1')}</strong>.</p>`; if (!factors.length) body += '<p>Tilføj en authenticator-app. Det er gratis og anbefales især til admin-konti.</p><form method="post" action="/security/mfa/enroll"><button type="submit">Start opsætning</button></form>'; else if (verified.length && auth.claims?.aal !== 'aal2') { const f = verified[0]; body += `<p>Din authenticator er allerede tilmeldt. Indtast den sekscifrede kode for at løfte sessionen til AAL2.</p><form method="post" action="/security/mfa/verify"><input type="hidden" name="factor_id" value="${escapeHtml(f.id)}"><label>Kode<br><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6,8}" required></label><br><button type="submit">Bekræft</button></form>`; } else { body += `<p>${verified.length ? '2-faktor er aktiv.' : 'En faktor er under opsætning.'}</p>`; for (const f of factors) body += `<p>${escapeHtml(f.friendly_name || f.factor_type || 'Faktor')} · ${escapeHtml(f.status || '')}</p>`; } body += '<p><a href="/account">Tilbage til konto</a></p>'; return withCookies(htmlPage('2-faktor-sikkerhed', body), auth.cookies); }
async function mfaEnroll(req, env) { const auth = await requireUser(req, env); if (auth.error) return auth.error; const r = await authFetch(env, 'factors', auth.token, { method: 'POST', body: JSON.stringify({ factor_type: 'totp', friendly_name: 'Morgentidende' }) }); const data = await r.json().catch(() => ({})); if (!r.ok) return withCookies(htmlPage('2-faktor', `<h1>Kunne ikke starte 2-faktor</h1><p>${escapeHtml(data.msg || data.message || 'Prøv igen.')}</p>`, r.status), auth.cookies); await audit(env, auth.user.id, 'mfa_enrollment_started', 'user', auth.user.id, { factor_id: data.id }); const qr = data?.totp?.qr_code || ''; const secret = data?.totp?.secret || ''; return withCookies(htmlPage('Opsæt 2-faktor', `<h1>Scan QR-koden</h1><p>Scan koden med din authenticator-app og indtast derefter koden nedenfor.</p>${qr ? `<img class="qr" src="${escapeHtml(qr)}" alt="QR-kode til authenticator">` : ''}${secret ? `<p>Alternativ nøgle:</p><p class="secret">${escapeHtml(secret)}</p>` : ''}<form method="post" action="/security/mfa/verify"><input type="hidden" name="factor_id" value="${escapeHtml(data.id)}"><label>Kode<br><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6,8}" required></label><br><button type="submit">Aktivér 2-faktor</button></form>`), auth.cookies); }
async function mfaVerify(req, env) { const auth = await requireUser(req, env); if (auth.error) return auth.error; const fields = await requestFields(req); const factorId = String(fields.factor_id || ''); const code = String(fields.code || '').trim(); if (!factorId || !/^\d{6,8}$/.test(code)) return htmlPage('2-faktor', '<h1>Ugyldig kode</h1><p>Prøv igen.</p>', 400); const challengeRes = await authFetch(env, `factors/${encodeURIComponent(factorId)}/challenge`, auth.token, { method: 'POST', body: '{}' }); const challenge = await challengeRes.json().catch(() => ({})); if (!challengeRes.ok || !challenge.id) return htmlPage('2-faktor', '<h1>Kunne ikke starte udfordringen</h1><p>Prøv igen om lidt.</p>', 400); const verifyRes = await authFetch(env, `factors/${encodeURIComponent(factorId)}/verify`, auth.token, { method: 'POST', body: JSON.stringify({ challenge_id: challenge.id, code }) }); const verified = await verifyRes.json().catch(() => ({})); if (!verifyRes.ok) return htmlPage('2-faktor', `<h1>Koden blev ikke godkendt</h1><p>${escapeHtml(verified.msg || verified.message || 'Prøv igen.')}</p>`, 401); await audit(env, auth.user.id, 'mfa_verified', 'user', auth.user.id, { factor_id: factorId }); const cookies = verified.access_token ? authCookies(verified) : auth.cookies; return withCookies(new Response(null, { status: 303, headers: { location: '/account' } }), cookies); }

async function kronikCheck(req, env, user) { const body = await req.json(); const { submission_id, revision_no, content_hash, title, standfirst, text, category } = body; if (!submission_id || !revision_no || !content_hash || !title || !text) return json({ error: 'invalid_request' }, 400); const prompt = `Du er Kronik-agent på Morgentidende. Kronikører er inviterede gæsteskribenter og skal have stor frihed. Afvis ikke en tekst fordi den er skarp, politisk, personlig, provokerende eller uenig med avisen. Vurder kun publiceringshygiejne: forståeligt dansk, basal kvalitet, åbenlys spam/sabotage, grove personangreb/chikane, doxxing, alvorlige udokumenterede beskyldninger, åbenlys ulovlighed samt klart misvisende form. Returnér JSON med decision PASS, REVISE eller ESCALATE; reasons som korte konkrete danske forklaringer; risk_type. REVISE skal foreslå mindst indgribende rettelse. ESCALATE bruges kun når menneskelig vurdering reelt er nødvendig.`; const result = await env.AI.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', { messages: [{ role: 'system', content: prompt }, { role: 'user', content: JSON.stringify({ title, standfirst, body: text, category }) }], temperature: 0.1, max_tokens: 1200, response_format: { type: 'json_object' } }); let review = result?.response ?? result; if (typeof review === 'string') review = JSON.parse(review); const decision = String(review.decision || '').toLowerCase(); if (!['pass', 'revise', 'escalate'].includes(decision)) return json({ error: 'agent_invalid_response' }, 502); const save = await serviceQuery(env, 'agent_reviews', { method: 'POST', headers: { Prefer: 'return=representation' }, body: JSON.stringify({ submission_id, revision_no, content_hash, decision, reasons: review.reasons || [], risk_type: review.risk_type || null, model: '@cf/meta/llama-3.3-70b-instruct-fp8-fast' }) }); if (!save.ok) return json({ error: 'review_save_failed' }, 502); await audit(env, user.id, `chronicler_agent_${decision}`, 'submission', submission_id, { revision_no, content_hash, reasons: review.reasons || [] }); return json({ decision: decision.toUpperCase(), reasons: review.reasons || [], risk_type: review.risk_type || null, content_hash }); }
async function createPublishRequest(req, env, user) { const body = await req.json(); const { submission_id, revision_no, content_hash, requested_for } = body; if (!submission_id || !revision_no || !content_hash || !requested_for) return json({ error: 'invalid_request' }, 400); const reviewRes = await serviceQuery(env, `agent_reviews?submission_id=eq.${encodeURIComponent(submission_id)}&revision_no=eq.${Number(revision_no)}&content_hash=eq.${encodeURIComponent(content_hash)}&decision=eq.pass&select=id&order=created_at.desc&limit=1`); if (!reviewRes.ok || !(await reviewRes.json()).length) return json({ error: 'fresh_agent_pass_required' }, 409); const idempotency_key = `${submission_id}:${revision_no}:${content_hash}:${requested_for}`; const r = await serviceQuery(env, 'publish_requests', { method: 'POST', headers: { Prefer: 'resolution=ignore-duplicates,return=representation' }, body: JSON.stringify({ submission_id, requested_by: user.id, requested_for, revision_no, content_hash, idempotency_key }) }); if (!r.ok) return json({ error: 'publish_request_failed' }, 502); await audit(env, user.id, 'publish_requested', 'submission', submission_id, { requested_for, revision_no, content_hash }); return json({ ok: true, request: (await r.json())[0] || null }, 202); }
async function uploadHero(req, env, user) { const type = req.headers.get('content-type') || ''; const allowed = new Set(['image/jpeg', 'image/png', 'image/webp']); if (!allowed.has(type)) return json({ error: 'unsupported_media_type' }, 415); const bytes = await req.arrayBuffer(); if (!bytes.byteLength || bytes.byteLength > 10 * 1024 * 1024) return json({ error: 'file_too_large' }, 413); const ext = type === 'image/jpeg' ? 'jpg' : type === 'image/png' ? 'png' : 'webp'; const key = `uploads/${user.id}/${crypto.randomUUID()}.${ext}`; await env.MEDIA.put(key, bytes, { httpMetadata: { contentType: type } }); await audit(env, user.id, 'media_uploaded', 'r2_object', key, { byte_size: bytes.byteLength, mime_type: type }); return json({ key, mime_type: type, byte_size: bytes.byteLength }, 201); }

export default {
  async fetch(req, env) {
    const url = new URL(req.url); const missing = missingConfig(env); if (url.pathname === '/health') return json({ ok: missing.length === 0, missing_config: missing }); if (missing.length) return json({ error: 'not_configured', missing }, 503);
    try {
      if (url.pathname === '/auth/session' && req.method === 'POST') return authSession(req, env);
      if (url.pathname === '/auth/refresh' && req.method === 'POST') return refreshRoute(req, env);
      if (url.pathname === '/auth/logout' && req.method === 'POST') return logout();
      if (url.pathname === '/account' && req.method === 'GET') return accountPage(req, env);
      if (url.pathname === '/security/mfa' && req.method === 'GET') return mfaPage(req, env);
      if (url.pathname === '/security/mfa/enroll' && req.method === 'POST') return mfaEnroll(req, env);
      if (url.pathname === '/security/mfa/verify' && req.method === 'POST') return mfaVerify(req, env);
      if (url.pathname === '/api/analytics/pageview' && ['POST','OPTIONS'].includes(req.method)) return pageview(req, env);
      if (url.pathname === '/kontrolrum/data/chroniclers' && req.method === 'GET') return controlChroniclers(env);
      if (url.pathname === '/kontrolrum/data/revenue' && req.method === 'GET') return controlRevenue(env);
      if (url.pathname === '/kontrolrum/data/traffic' && req.method === 'GET') return controlTraffic(env);
      if (url.pathname === '/kontrolrum/data/funnel' && req.method === 'GET') return controlFunnel();
      if (url.pathname === '/api/me' && req.method === 'GET') { const auth = await requireUser(req, env); if (auth.error) return auth.error; return withCookies(json({ user: { id: auth.user.id, email: auth.user.email }, roles: auth.roles, aal: auth.claims?.aal || 'aal1' }), auth.cookies); }
      if (url.pathname === '/api/kronik/check' && req.method === 'POST') { const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']); if (auth.error) return auth.error; return withCookies(await kronikCheck(req, env, auth.user), auth.cookies); }
      if (url.pathname === '/api/kronik/publish-request' && req.method === 'POST') { const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']); if (auth.error) return auth.error; return withCookies(await createPublishRequest(req, env, auth.user), auth.cookies); }
      if (url.pathname === '/api/media/hero' && req.method === 'PUT') { const auth = await requireUser(req, env, ['chronicler', 'editor', 'admin']); if (auth.error) return auth.error; return withCookies(await uploadHero(req, env, auth.user), auth.cookies); }
      if (url.pathname === '/api/admin/chroniclers/fire' && req.method === 'POST') { const auth = await requireUser(req, env, ['admin'], { requireAal2: true }); if (auth.error) return auth.error; return withCookies(await fireChronicler(req, env, auth.user), auth.cookies); }
      if (url.pathname.startsWith('/api/admin/')) { const auth = await requireUser(req, env, ['admin'], { requireAal2: true }); if (auth.error) return auth.error; return withCookies(json({ ok: true, aal: auth.claims?.aal, note: 'Admin route requires app admin role + MFA (AAL2); Cloudflare Access should additionally protect the control-room hostname.' }), auth.cookies); }
      return json({ error: 'not_found' }, 404);
    } catch (error) { console.error(error); return json({ error: 'internal_error' }, 500); }
  },
};
