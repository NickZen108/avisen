#!/usr/bin/env python3
from pathlib import Path

path = Path('cloudflare/app/src/index.js')
text = path.read_text(encoding='utf-8')

helper_anchor = "async function serviceQuery(env, path, init = {}) { if (!env.SUPABASE_SECRET_KEY) throw new Error('supabase secret key missing'); const headers = new Headers(init.headers || {}); headers.set('apikey', env.SUPABASE_SECRET_KEY); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); return fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, { ...init, headers }); }\n"
helper_code = r'''async function adminAuthFetch(env, path, init = {}) { if (!env.SUPABASE_SECRET_KEY) throw new Error('supabase secret key missing'); const headers = new Headers(init.headers || {}); headers.set('apikey', env.SUPABASE_SECRET_KEY); headers.set('authorization', `Bearer ${env.SUPABASE_SECRET_KEY}`); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); return fetch(`${env.SUPABASE_URL}/auth/v1/${path}`, { ...init, headers }); }
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
'''

if 'async function adminAuthFetch' not in text:
    if helper_anchor not in text:
        raise RuntimeError('serviceQuery anchor missing')
    text = text.replace(helper_anchor, helper_anchor + helper_code, 1)

route_anchor = "      if (url.pathname === '/api/me' && req.method === 'GET') { const auth = await requireUser(req, env); if (auth.error) return auth.error; return withCookies(json({ user: { id: auth.user.id, email: auth.user.email }, roles: auth.roles, aal: auth.claims?.aal || 'aal1' }), auth.cookies); }\n"
route_code = "      if (url.pathname === '/api/analytics/pageview' && ['POST','OPTIONS'].includes(req.method)) return pageview(req, env);\n      if (url.pathname === '/kontrolrum/data/chroniclers' && req.method === 'GET') return controlChroniclers(env);\n      if (url.pathname === '/kontrolrum/data/revenue' && req.method === 'GET') return controlRevenue(env);\n      if (url.pathname === '/kontrolrum/data/traffic' && req.method === 'GET') return controlTraffic(env);\n"
if "'/kontrolrum/data/chroniclers'" not in text:
    if route_anchor not in text:
        raise RuntimeError('api/me route anchor missing')
    text = text.replace(route_anchor, route_code + route_anchor, 1)

admin_anchor = "      if (url.pathname.startsWith('/api/admin/')) { const auth = await requireUser(req, env, ['admin'], { requireAal2: true }); if (auth.error) return auth.error; return withCookies(json({ ok: true, aal: auth.claims?.aal, note: 'Admin route requires app admin role + MFA (AAL2); Cloudflare Access should additionally protect the control-room hostname.' }), auth.cookies); }"
admin_new = "      if (url.pathname === '/api/admin/chroniclers/fire' && req.method === 'POST') { const auth = await requireUser(req, env, ['admin'], { requireAal2: true }); if (auth.error) return auth.error; return withCookies(await fireChronicler(req, env, auth.user), auth.cookies); }\n" + admin_anchor
if "'/api/admin/chroniclers/fire'" not in text:
    if admin_anchor not in text:
        raise RuntimeError('admin route anchor missing')
    text = text.replace(admin_anchor, admin_new, 1)

path.write_text(text, encoding='utf-8')
print('Control-room data APIs applied or already present')
