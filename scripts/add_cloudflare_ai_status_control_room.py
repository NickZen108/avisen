#!/usr/bin/env python3
from pathlib import Path

app = Path('cloudflare/app/src/index.js')
s = app.read_text(encoding='utf-8')

if 'async function controlAiStatus()' not in s:
    marker = 'async function controlFunnel() {'
    block = r'''async function controlAiStatus() {
  const endpoint = 'https://morgentidende-newsdesk.nicolaipetersen108.workers.dev/editorial/history';
  const response = await fetch(endpoint, { headers: { 'user-agent': 'MorgentidendeControlRoom/1.0' }, cf: { cacheTtl: 0 } });
  if (!response.ok) return json({ status: 'unknown', error: 'ai_status_source_unavailable', source_status: response.status }, 503);
  const rows = await response.json();
  const events = Array.isArray(rows) ? rows : [];
  const eventAt = (r) => r?.at || r?.created_at || r?.timestamp || r?.occurred_at || r?.updated_at || null;
  const toMs = (r) => { const t = Date.parse(eventAt(r) || ''); return Number.isFinite(t) ? t : -1; };
  const isQuotaError = (r) => {
    const text = String(r?.reason || r?.error || '');
    return /(?:AiError:\s*)?4006\b|used up your daily free allocation|quota(?:_| )?(?:exhausted|exceeded)/i.test(text);
  };
  const quota = events.filter(isQuotaError).sort((a,b) => toMs(b) - toMs(a))[0] || null;
  const successes = events.filter(r => !isQuotaError(r) && Number(r?.ai_usage?.calls || 0) > 0).sort((a,b) => toMs(b) - toMs(a));
  const success = successes[0] || null;
  const quotaMs = quota ? toMs(quota) : -1;
  const successMs = success ? toMs(success) : -1;
  let status = 'unknown';
  if (success && successMs > quotaMs) status = 'available';
  else if (quota) status = 'quota_exhausted';
  return json({
    status,
    available: status === 'available',
    last_successful_ai_call: success ? eventAt(success) : null,
    last_successful_stage: success?.stage || (success?.status === 'approved' ? 'release' : null),
    last_quota_error: quota ? { at: eventAt(quota), stage: quota?.stage || null, reason: String(quota?.reason || quota?.error || '') } : null,
    quota_error_count: events.filter(isQuotaError).length,
    source: 'editorial/history',
    note: status === 'available' ? 'Der er registreret et succesfuldt AI-kald efter den seneste quota-fejl.' : status === 'quota_exhausted' ? 'Den seneste relevante kapacitetshændelse er en quota-fejl.' : 'Der er endnu ikke nok historik til at afgøre AI-status sikkert.'
  });
}
'''
    if marker not in s:
        raise SystemExit('controlFunnel marker missing')
    s = s.replace(marker, block + marker, 1)

route = "if (url.pathname === '/kontrolrum/data/funnel' && req.method === 'GET') return controlFunnel();"
new_route = route + "\n      if (url.pathname === '/kontrolrum/data/ai-status' && req.method === 'GET') return controlAiStatus();"
if '/kontrolrum/data/ai-status' not in s:
    if route not in s:
        raise SystemExit('funnel route marker missing')
    s = s.replace(route, new_route, 1)
app.write_text(s, encoding='utf-8')

ui = Path('docs/kontrolrum/control-room-tabs.js')
u = ui.read_text(encoding='utf-8')

fetch_marker = "      const f=await fetchJson('/kontrolrum/data/funnel');"
fetch_repl = fetch_marker + "\n      let ai={status:'unknown',available:false,last_successful_ai_call:null,last_quota_error:null,quota_error_count:0,note:''};\n      try { ai=await fetchJson('/kontrolrum/data/ai-status'); } catch (_) {}"
if "fetchJson('/kontrolrum/data/ai-status')" not in u:
    if fetch_marker not in u:
        raise SystemExit('funnel fetch marker missing')
    u = u.replace(fetch_marker, fetch_repl, 1)

html_marker = "      funnelHtml=`<h2>Live funnel efter Newsdesk</h2>"
if 'Cloudflare AI-status' not in u:
    if html_marker not in u:
        raise SystemExit('funnel html marker missing')
    ai_prefix = r'''      const aiLabel=ai.status==='available'?'Tilgængelig':ai.status==='quota_exhausted'?'Quota opbrugt':'Ukendt';
      const aiTone=ai.status==='available'?'ok':ai.status==='quota_exhausted'?'bad':'warn';
      const aiFmt=(value)=>value?new Intl.DateTimeFormat('da-DK',{timeZone:'Europe/Copenhagen',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value)).replace(',',' kl.'):'—';
      const quota=ai.last_quota_error||null;
      const aiHtml=`<h2>Cloudflare AI-status</h2><div class="metric-grid"><div class="metric"><b><span class="badge ${aiTone}">${esc(aiLabel)}</span></b><span>Cloudflare Workers AI</span><small>${esc(ai.note||'')}</small></div><div class="metric"><b>${esc(aiFmt(ai.last_successful_ai_call))}</b><span>seneste succesfulde AI-kald</span><small>${esc(ai.last_successful_stage||'')}</small></div><div class="metric"><b>${esc(aiFmt(quota?.at))}</b><span>seneste quota-fejl</span><small>${quota?esc(quota.reason||''):'Ingen registreret'}</small></div><div class="metric"><b>${Number(ai.quota_error_count||0)}</b><span>quota-fejl i historikken</span></div></div>`;
'''
    u = u.replace(html_marker, ai_prefix + "      funnelHtml=aiHtml+`<h2>Live funnel efter Newsdesk</h2>", 1)

ui.write_text(u, encoding='utf-8')
print('Cloudflare AI status added to control room')
