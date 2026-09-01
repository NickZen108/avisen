#!/usr/bin/env python3
from pathlib import Path

app = Path('cloudflare/app/src/index.js')
s = app.read_text(encoding='utf-8')
traffic_fn = '''async function controlTraffic(env) {
  const cutoff = new Date(Date.now() - 31 * 86400000).toISOString();
  const rows = await rowsOrThrow(await serviceQuery(env, `traffic_events?occurred_at=gte.${encodeURIComponent(cutoff)}&select=occurred_at,article_slug,title,category,referrer_host&order=occurred_at.desc&limit=50000`), 'traffic events');
  const days30rows = rows.filter(r => Date.parse(r.occurred_at) >= Date.now() - 30 * 86400000);
  return json({ today: topStories(rows, 0), days7: topStories(rows, 7), days30: topStories(rows, 30), total_views_30d: days30rows.length, recommendations: trafficRecommendations(days30rows), measurement_started: rows.length > 0 });
}
'''
funnel_fn = traffic_fn + '''async function controlFunnel() {
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
'''
if traffic_fn not in s: raise SystemExit('controlTraffic marker missing')
s = s.replace(traffic_fn, funnel_fn, 1)
route = "      if (url.pathname === '/kontrolrum/data/traffic' && req.method === 'GET') return controlTraffic(env);\n"
if route not in s: raise SystemExit('traffic route missing')
s = s.replace(route, route + "      if (url.pathname === '/kontrolrum/data/funnel' && req.method === 'GET') return controlFunnel();\n", 1)
app.write_text(s, encoding='utf-8')

tabs = Path('docs/kontrolrum/control-room-tabs.js')
t = tabs.read_text(encoding='utf-8')
old = '''  function loadPipeline(){
    const p=panels.pipeline; const d=window.__MT_PIPELINE_FEEDBACK__||{};
'''
new = '''  async function loadPipeline(){
    const p=panels.pipeline; const d=window.__MT_PIPELINE_FEEDBACK__||{};
'''
if old not in t: raise SystemExit('loadPipeline marker missing')
t = t.replace(old, new, 1)
old_end = '''    p.innerHTML=`<h1>Pipeline</h1><p class="intro">Her kan kravene ses som målbare parametre. Hver afvisning udløser en vurdering af, om stoppet var legitimt, reparerbart eller tegn på unødig friktion.</p><div class="policy-lock"><strong>Fast regel:</strong> fact check, etik, forelæggelse og final editor lempes ikke automatisk. Målbare ændringer foreslås som eksperimenter og kan derefter skrues op eller ned.</div><h2>Flow og aktuelle krav</h2><div class="flow">${flowHtml}</div><h2>Dagens pipeline-vurdering</h2><div class="metric-grid"><div class="metric"><b>${d.today?.rejections||0}</b><span>afvisninger vurderet i dag</span></div><div class="metric"><b>${suggestions.length}</b><span>foreslåede justeringer</span></div><div class="metric"><b>${Object.values(d.last7_stage_counts||{}).reduce((a,b)=>a+Number(b||0),0)}</b><span>afvisninger seneste 7 dage</span></div><div class="metric"><b>${(d.current_blockers||[]).length}</b><span>nuværende blokerede artikler</span></div></div>${sugHtml}<h2>Hver afvisning i dag</h2>${revHtml}`;
  }
'''
new_end = '''    let funnelHtml='<div class="tab-note">Henter live funnel-data…</div>';
    try {
      const f=await fetchJson('/kontrolrum/data/funnel');
      const rate=f.post_newsdesk_rejection_rate_pct;
      const rateText=rate==null?'—':`${rate}%`;
      const targetOk=rate!=null && rate < Number(f.long_term_target_pct||10);
      const stages=Object.entries(f.stage_counts||{}).sort((a,b)=>b[1]-a[1]);
      const stageHtml=stages.length?`<table><thead><tr><th>Stop/sluttrin</th><th>Forsøg</th></tr></thead><tbody>${stages.map(([stage,count])=>`<tr><td>${esc(stage)}</td><td>${count}</td></tr>`).join('')}</tbody></table>`:'<div class="tab-note">Ingen post-Newsdesk-forsøg registreret endnu.</div>';
      const reasonHtml=(f.top_stop_reasons||[]).length?`<table><thead><tr><th>Trin</th><th>Årsag</th><th>Antal</th></tr></thead><tbody>${f.top_stop_reasons.map(x=>`<tr><td>${esc(x.stage)}</td><td>${esc(x.reason||'Ingen årsag registreret')}</td><td>${x.count}</td></tr>`).join('')}</tbody></table>`:'<div class="tab-note">Ingen stopårsager registreret endnu.</div>';
      funnelHtml=`<h2>Live funnel efter Newsdesk</h2><p class="intro">Deterministisk måling fra Newsdesk Workers editorial history. Målet er på sigt under ${f.long_term_target_pct||10}% afvisning efter Scanner + Newsdesk.</p><div class="metric-grid"><div class="metric"><b>${f.post_newsdesk_attempts||0}</b><span>post-Newsdesk forsøg</span></div><div class="metric"><b>${f.approved||0}</b><span>godkendt</span></div><div class="metric"><b>${f.parked_watch||0}</b><span>WATCH</span></div><div class="metric"><b>${rateText}</b><span>afvist/holdt</span><small>${targetOk?'under langsigtet mål':'mål < '+(f.long_term_target_pct||10)+'%'}</small></div><div class="metric"><b>${Number(f.total_tokens||0).toLocaleString('da-DK')}</b><span>tokens målt</span></div><div class="metric"><b>≈ ${Number(f.estimated_neurons||0).toLocaleString('da-DK')}</b><span>neurons</span></div><div class="metric"><b>${f.total_ai_calls||0}</b><span>AI-kald</span></div><div class="metric"><b>${f.metered_attempts||0}</b><span>forsøg med usage-data</span></div></div><h3>Hvor historierne ender</h3>${stageHtml}<h3>Hyppigste stopårsager</h3>${reasonHtml}<div class="tab-note">${esc(f.note||'')}</div>`;
    } catch(e) { funnelHtml=errorHtml(e); }
    p.innerHTML=`<h1>Pipeline</h1><p class="intro">Her kan kravene ses som målbare parametre. Hver afvisning udløser en vurdering af, om stoppet var legitimt, reparerbart eller tegn på unødig friktion.</p><div class="policy-lock"><strong>Fast regel:</strong> fact check, etik, forelæggelse og final editor lempes ikke automatisk. Målbare ændringer foreslås som eksperimenter og kan derefter skrues op eller ned.</div>${funnelHtml}<h2>Flow og aktuelle krav</h2><div class="flow">${flowHtml}</div><h2>Dagens pipeline-vurdering</h2><div class="metric-grid"><div class="metric"><b>${d.today?.rejections||0}</b><span>afvisninger vurderet i dag</span></div><div class="metric"><b>${suggestions.length}</b><span>foreslåede justeringer</span></div><div class="metric"><b>${Object.values(d.last7_stage_counts||{}).reduce((a,b)=>a+Number(b||0),0)}</b><span>afvisninger seneste 7 dage</span></div><div class="metric"><b>${(d.current_blockers||[]).length}</b><span>nuværende blokerede artikler</span></div></div>${sugHtml}<h2>Hver afvisning i dag</h2>${revHtml}`;
  }
'''
if old_end not in t: raise SystemExit('pipeline render marker missing')
t = t.replace(old_end, new_end, 1)
tabs.write_text(t, encoding='utf-8')
print('funnel integrated into control room')
