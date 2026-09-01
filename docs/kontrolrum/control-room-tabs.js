(() => {
  const main = document.querySelector('main');
  const freshness = main?.querySelector('.freshness');
  if (!main || !freshness) return;

  const style = document.createElement('style');
  style.textContent = `
    .control-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 22px;border-bottom:1px solid var(--rule);padding-bottom:10px}
    .control-tab{border:1px solid var(--rule);background:var(--surface);color:var(--ink);padding:9px 13px;border-radius:999px;cursor:pointer;font-weight:700}
    .control-tab[aria-selected="true"]{background:var(--blue);border-color:#7892ab}
    .control-panel[hidden]{display:none}.control-panel{min-height:240px}
    .tab-note{padding:14px 16px;background:var(--surface);border:1px solid var(--rule);border-radius:9px;margin:12px 0;color:var(--muted)}
    .metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}.metric{padding:16px;border:1px solid var(--rule);border-radius:9px;background:var(--surface)}.metric b{display:block;font-size:26px}.metric small{margin-top:4px}
    .danger-btn{border:1px solid #9a5d63;background:var(--rose);color:var(--ink);padding:8px 11px;border-radius:7px;font-weight:700;cursor:pointer}.danger-btn:disabled{opacity:.5;cursor:wait}
    .kronik-row{display:flex;gap:12px;justify-content:space-between;align-items:flex-start}.kronik-meta{color:var(--muted);font-size:13px}.chronicle-list{margin:8px 0 0;padding-left:20px}.chronicle-list li{margin:7px 0}.recommendations{background:var(--surface);border:1px solid var(--rule);border-radius:9px;padding:16px 20px}.recommendations li{margin:9px 0}
    .flow{display:flex;align-items:stretch;gap:10px;overflow-x:auto;padding:8px 2px 18px;scroll-snap-type:x proximity}.flow-step{min-width:220px;max-width:260px;scroll-snap-align:start;background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:14px;box-shadow:var(--shadow);position:relative}.flow-step:not(:last-child)::after{content:'→';position:absolute;right:-10px;top:50%;transform:translate(50%,-50%);font-size:23px;font-weight:800;color:var(--muted);z-index:2}.flow-step h3{margin:0 0 8px;font:700 19px Georgia,serif}.flow-step .hard{display:inline-block;font-size:11px;font-weight:800;padding:3px 7px;border-radius:999px;background:var(--rose);margin-bottom:7px}.flow-step .soft{display:inline-block;font-size:11px;font-weight:800;padding:3px 7px;border-radius:999px;background:var(--blue);margin-bottom:7px}.req{border-top:1px solid var(--rule);padding:8px 0 0;margin-top:8px}.req b{font-size:20px}.req .tunable{font-size:11px;color:var(--muted);font-weight:700}.adjustment{border-left:5px solid #7892ab;padding:12px 14px;background:var(--surface);border-top:1px solid var(--rule);border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);border-radius:8px;margin:10px 0}.adjustment.experiment{border-left-color:#b99032}.adjustment.fix-system{border-left-color:#8c5960}.adjustment .change{font-weight:800}.review-card{background:var(--surface);border:1px solid var(--rule);border-radius:9px;padding:13px;margin:10px 0}.review-card .reason{color:var(--muted);font-size:13px;margin-top:5px}.policy-lock{background:var(--green);border:1px solid var(--rule);padding:13px 15px;border-radius:9px;margin:12px 0}
    @media(max-width:800px){.metric-grid{grid-template-columns:1fr 1fr}.kronik-row{flex-direction:column}.flow-step{min-width:82vw}}
  `;
  document.head.appendChild(style);

  const existing = [...main.children].filter(el => el !== freshness);
  const nav = document.createElement('nav');
  nav.className = 'control-tabs';
  nav.setAttribute('aria-label', 'Kontrolrum faner');
  freshness.insertAdjacentElement('afterend', nav);

  const panels = {};
  const specs = [
    ['production','Produktion'],['pipeline','Pipeline'],['chroniclers','Kronikører'],['revenue','Indtægter'],['traffic','Mest læste']
  ];
  for (const [id,label] of specs) {
    const btn = document.createElement('button'); btn.type='button'; btn.className='control-tab'; btn.dataset.tab=id; btn.textContent=label; btn.setAttribute('aria-selected','false'); nav.appendChild(btn);
    const panel = document.createElement('section'); panel.className='control-panel'; panel.dataset.panel=id; panel.hidden=true; main.appendChild(panel); panels[id]=panel;
  }
  existing.forEach(el => panels.production.appendChild(el));

  const fmtMoney = ore => new Intl.NumberFormat('da-DK',{style:'currency',currency:'DKK',minimumFractionDigits:2}).format(Number(ore||0)/100);
  const esc = value => String(value ?? '').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const fetchJson = async (url, init) => { const r=await fetch(url,{credentials:'include',cache:'no-store',...init}); const d=await r.json().catch(()=>({})); if(!r.ok){const e=new Error(d.error||`HTTP ${r.status}`);e.status=r.status;e.data=d;throw e;} return d; };
  const errorHtml = e => e.status===401 ? '<div class="tab-note">Administrativ handling kræver, at du også er logget ind på Morgentidendes app-konto.</div>' : e.status===403 ? '<div class="tab-note">Denne handling kræver admin-login med 2-faktor (AAL2). Åbn <a href="/security/mfa">2-faktor-sikkerhed</a> og prøv igen.</div>' : `<div class="tab-note">Kunne ikke hente data: ${esc(e.message)}</div>`;

  async function loadPipeline(){
    const p=panels.pipeline; const d=window.__MT_PIPELINE_FEEDBACK__||{};
    const flow=d.flow||[]; const reviews=d.today?.reviews||[]; const suggestions=d.suggested_adjustments||[];
    const flowHtml=flow.map(s=>`<div class="flow-step"><h3>${esc(s.label)}</h3><span class="${s.hard_gate?'hard':'soft'}">${s.hard_gate?'HARD GATE':'JUSTERBAR/PRODUKTION'}</span>${(s.requirements||[]).map(r=>`<div class="req"><span>${esc(r.label)}</span><br><b>${esc(r.value)} ${esc(r.unit||'')}</b>${r.adjustable?'<div class="tunable">Kan skrues op/ned i eksperiment</div>':'<div class="tunable">Låst sikkerhedskrav</div>'}</div>`).join('')}</div>`).join('');
    const sugHtml=suggestions.length?suggestions.map(x=>`<div class="adjustment ${esc(x.status)}"><strong>${esc(x.stage)}</strong> · ${esc(x.parameter)}<div class="change">${esc(x.current)} → ${esc(x.proposed)}</div><div>${esc(x.why)}</div><small>Status: ${esc(x.status)}</small></div>`).join(''):'<div class="policy-lock"><strong>Ingen pipeline-justering anbefalet i dag.</strong><br>Det betyder ikke, at der ikke var afvisninger; det betyder, at de registrerede afvisninger ikke giver tilstrækkeligt signal til at ændre tærsklerne.</div>';
    const revHtml=reviews.length?reviews.map(x=>`<div class="review-card"><strong>${esc(x.title||x.slug||'Ikke navngivet kandidat')}</strong> · ${esc(x.stage)} · ${esc(x.class)}<div>${esc(x.assessment)}</div><div class="reason">Afvist fordi: ${esc(x.reason)}</div></div>`).join(''):'<div class="tab-note">Ingen afviste publiceringsforsøg registreret i dag.</div>';
    let funnelHtml='<div class="tab-note">Henter live funnel-data…</div>';
    try {
      const f=await fetchJson('/kontrolrum/data/funnel');
      let ai={status:'unknown',available:false,last_successful_ai_call:null,last_quota_error:null,quota_error_count:0,note:''};
      try { ai=await fetchJson('/kontrolrum/data/ai-status'); } catch (_) {}
      const rate=f.post_newsdesk_rejection_rate_pct;
      const rateText=rate==null?'—':`${rate}%`;
      const targetOk=rate!=null && rate < Number(f.long_term_target_pct||10);
      const stages=Object.entries(f.stage_counts||{}).sort((a,b)=>b[1]-a[1]);
      const stageHtml=stages.length?`<table><thead><tr><th>Stop/sluttrin</th><th>Forsøg</th></tr></thead><tbody>${stages.map(([stage,count])=>`<tr><td>${esc(stage)}</td><td>${count}</td></tr>`).join('')}</tbody></table>`:'<div class="tab-note">Ingen post-Newsdesk-forsøg registreret endnu.</div>';
      const reasonHtml=(f.top_stop_reasons||[]).length?`<table><thead><tr><th>Trin</th><th>Årsag</th><th>Antal</th></tr></thead><tbody>${f.top_stop_reasons.map(x=>`<tr><td>${esc(x.stage)}</td><td>${esc(x.reason||'Ingen årsag registreret')}</td><td>${x.count}</td></tr>`).join('')}</tbody></table>`:'<div class="tab-note">Ingen stopårsager registreret endnu.</div>';
      const aiLabel=ai.status==='available'?'Tilgængelig':ai.status==='quota_exhausted'?'Quota opbrugt':'Ukendt';
      const aiTone=ai.status==='available'?'ok':ai.status==='quota_exhausted'?'bad':'warn';
      const aiFmt=(value)=>value?new Intl.DateTimeFormat('da-DK',{timeZone:'Europe/Copenhagen',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value)).replace(',',' kl.'):'—';
      const quota=ai.last_quota_error||null;
      const aiHtml=`<h2>Cloudflare AI-status</h2><div class="metric-grid"><div class="metric"><b><span class="badge ${aiTone}">${esc(aiLabel)}</span></b><span>Cloudflare Workers AI</span><small>${esc(ai.note||'')}</small></div><div class="metric"><b>${esc(aiFmt(ai.last_successful_ai_call))}</b><span>seneste succesfulde AI-kald</span><small>${esc(ai.last_successful_stage||'')}</small></div><div class="metric"><b>${esc(aiFmt(quota?.at))}</b><span>seneste quota-fejl</span><small>${quota?esc(quota.reason||''):'Ingen registreret'}</small></div><div class="metric"><b>${Number(ai.quota_error_count||0)}</b><span>quota-fejl i historikken</span></div></div>`;
      funnelHtml=aiHtml+`<h2>Live funnel efter Newsdesk</h2><p class="intro">Deterministisk måling fra Newsdesk Workers editorial history. Målet er på sigt under ${f.long_term_target_pct||10}% afvisning efter Scanner + Newsdesk.</p><div class="metric-grid"><div class="metric"><b>${f.post_newsdesk_attempts||0}</b><span>post-Newsdesk forsøg</span></div><div class="metric"><b>${f.approved||0}</b><span>godkendt</span></div><div class="metric"><b>${f.parked_watch||0}</b><span>WATCH</span></div><div class="metric"><b>${rateText}</b><span>afvist/holdt</span><small>${targetOk?'under langsigtet mål':'mål < '+(f.long_term_target_pct||10)+'%'}</small></div><div class="metric"><b>${Number(f.total_tokens||0).toLocaleString('da-DK')}</b><span>tokens målt</span></div><div class="metric"><b>≈ ${Number(f.estimated_neurons||0).toLocaleString('da-DK')}</b><span>neurons</span></div><div class="metric"><b>${f.total_ai_calls||0}</b><span>AI-kald</span></div><div class="metric"><b>${f.metered_attempts||0}</b><span>forsøg med usage-data</span></div></div><h3>Hvor historierne ender</h3>${stageHtml}<h3>Hyppigste stopårsager</h3>${reasonHtml}<div class="tab-note">${esc(f.note||'')}</div>`;
    } catch(e) { funnelHtml=errorHtml(e); }
    p.innerHTML=`<h1>Pipeline</h1><p class="intro">Her kan kravene ses som målbare parametre. Hver afvisning udløser en vurdering af, om stoppet var legitimt, reparerbart eller tegn på unødig friktion.</p><div class="policy-lock"><strong>Fast regel:</strong> fact check, etik, forelæggelse og final editor lempes ikke automatisk. Målbare ændringer foreslås som eksperimenter og kan derefter skrues op eller ned.</div>${funnelHtml}<h2>Flow og aktuelle krav</h2><div class="flow">${flowHtml}</div><h2>Dagens pipeline-vurdering</h2><div class="metric-grid"><div class="metric"><b>${d.today?.rejections||0}</b><span>afvisninger vurderet i dag</span></div><div class="metric"><b>${suggestions.length}</b><span>foreslåede justeringer</span></div><div class="metric"><b>${Object.values(d.last7_stage_counts||{}).reduce((a,b)=>a+Number(b||0),0)}</b><span>afvisninger seneste 7 dage</span></div><div class="metric"><b>${(d.current_blockers||[]).length}</b><span>nuværende blokerede artikler</span></div></div>${sugHtml}<h2>Hver afvisning i dag</h2>${revHtml}`;
  }

  async function loadChroniclers(){
    const p=panels.chroniclers; p.innerHTML='<h1>Kronikører</h1><p class="intro">Alle aktive kronikører og deres indsendte kronikker. En fyring fjerner roller/adgang og spærrer login, men sletter ikke allerede publicerede kronikker.</p><div class="tab-note">Henter kronikører…</div>';
    try{
      const d=await fetchJson('/kontrolrum/data/chroniclers');
      if(!d.chroniclers?.length){p.innerHTML+='<div class="tab-note">Ingen aktive kronikører endnu.</div>';return;}
      const wrap=document.createElement('div');
      d.chroniclers.forEach(c=>{
        const det=document.createElement('details');
        const published=(c.chronicles||[]).filter(x=>x.status==='published').length;
        det.innerHTML=`<summary>${esc(c.display_name)} · ${c.chronicles.length} kronikker</summary><div class="kronik-row"><div><p class="kronik-meta">${esc(c.email||'Ingen mail vist')} · ${published} publiceret</p><ul class="chronicle-list">${c.chronicles.length?c.chronicles.map(x=>`<li>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title||'Uden titel')}</a>`:esc(x.title||'Uden titel')} <small>${esc(x.status)}</small></li>`).join(''):'<li>Ingen kronikker endnu</li>'}</ul></div><button class="danger-btn" type="button" data-fire="${esc(c.user_id)}" data-name="${esc(c.display_name)}">Fyr kronikør</button></div>`;
        wrap.appendChild(det);
      });
      p.querySelector('.tab-note')?.remove(); p.appendChild(wrap);
      p.querySelectorAll('[data-fire]').forEach(btn=>btn.addEventListener('click',async()=>{
        const name=btn.dataset.name||'denne kronikør';
        if(!confirm(`Er du sikker? ${name} mister straks sin kronikøradgang og login bliver spærret. Allerede publicerede kronikker slettes ikke.`)) return;
        btn.disabled=true;
        try{await fetchJson('/api/admin/chroniclers/fire',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({user_id:btn.dataset.fire})});alert(`${name} er fyret, rollerne er fjernet og login er spærret.`);await loadChroniclers();}
        catch(e){alert(e.status===403?'Fyring kræver admin-login med 2-faktor (AAL2).':`Kunne ikke fyre kronikøren: ${e.message}`);btn.disabled=false;}
      }));
    }catch(e){p.innerHTML='<h1>Kronikører</h1>'+errorHtml(e);}
  }

  const metric = (value,label,small='') => `<div class="metric"><b>${value}</b><span>${label}</span>${small?`<small>${small}</small>`:''}</div>`;
  async function loadRevenue(){
    const p=panels.revenue;p.innerHTML='<h1>Indtægter</h1><p class="intro">Faktisk registreret omsætning fra abonnementer og reklamer. Der beregnes ikke opdigtede tal.</p><div class="tab-note">Henter økonomidata…</div>';
    try{const d=await fetchJson('/kontrolrum/data/revenue');
      const row=(name,x)=>`<tr><td><strong>${name}</strong></td><td>${fmtMoney(x.subscription_ore)}</td><td>${fmtMoney(x.advertising_ore)}</td><td>${fmtMoney(x.gross_ore)}</td><td>${x.events}</td></tr>`;
      p.innerHTML=`<h1>Indtægter</h1><p class="intro">Faktisk registreret omsætning fra abonnementer og reklamer. Der beregnes ikke opdigtede tal.</p><div class="metric-grid">${metric(d.active_subscriptions,'aktive abonnementer')}${metric(fmtMoney(d.today.gross_ore),'omsætning i dag')}${metric(fmtMoney(d.days7.gross_ore),'seneste 7 dage')}${metric(fmtMoney(d.days30.gross_ore),'seneste 30 dage')}</div><table><thead><tr><th>Periode</th><th>Abonnement</th><th>Reklamer</th><th>I alt</th><th>Posteringer</th></tr></thead><tbody>${row('I dag',d.today)}${row('Seneste 7 dage',d.days7)}${row('Seneste 30 dage',d.days30)}</tbody></table>${d.note?`<div class="tab-note">${esc(d.note)}</div>`:''}`;
    }catch(e){p.innerHTML='<h1>Indtægter</h1>'+errorHtml(e);}
  }

  const storyTable=(title,rows)=>`<details ${title==='I dag'?'open':''}><summary>${title} · ${rows.reduce((a,x)=>a+x.views,0)} visninger</summary>${rows.length?`<table><thead><tr><th>#</th><th>Artikel</th><th>Emne</th><th>Visninger</th></tr></thead><tbody>${rows.map((x,i)=>`<tr><td>${i+1}</td><td><a href="https://morgentidende.nicolaipetersen108.workers.dev/artikler/${esc(x.slug)}.html" target="_blank" rel="noopener"><strong>${esc(x.title)}</strong></a></td><td>${esc(x.category)}</td><td>${x.views}</td></tr>`).join('')}</tbody></table>`:'<div class="tab-note">Ingen målte artikelvisninger i perioden endnu.</div>'}</details>`;
  async function loadTraffic(){
    const p=panels.traffic;p.innerHTML='<h1>Mest læste</h1><div class="tab-note">Henter trafikdata…</div>';
    try{const d=await fetchJson('/kontrolrum/data/traffic'); p.innerHTML=`<h1>Mest læste</h1><p class="intro">Browserbaserede artikelvisninger uden lagring af IP-adresse eller brugeridentitet. Trafik er et sekundært redaktionelt signal.</p>${storyTable('I dag',d.today)}${storyTable('Seneste 7 dage',d.days7)}${storyTable('Seneste 30 dage',d.days30)}<h2>Anbefalinger til udgivelsesstrategien</h2><ul class="recommendations">${(d.recommendations||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${!d.measurement_started?'<div class="tab-note">Trafikmålingen er netop gjort klar. Anbefalingerne bliver mere nyttige, når der er kommet faktiske læsere igennem.</div>':''}`;}
    catch(e){p.innerHTML='<h1>Mest læste</h1>'+errorHtml(e);}
  }

  const loaders={pipeline:loadPipeline,chroniclers:loadChroniclers,revenue:loadRevenue,traffic:loadTraffic}; const loaded=new Set();
  function activate(id){ if(!panels[id]) id='production'; document.querySelectorAll('.control-tab').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===id))); Object.entries(panels).forEach(([k,p])=>p.hidden=k!==id); try{localStorage.setItem('mt-control-tab',id)}catch(_){} if(loaders[id]&&!loaded.has(id)){loaded.add(id);loaders[id]();} }
  nav.addEventListener('click',e=>{const b=e.target.closest('.control-tab');if(b)activate(b.dataset.tab)});
  let start='production';try{start=localStorage.getItem('mt-control-tab')||start}catch(_){}activate(start);
})();