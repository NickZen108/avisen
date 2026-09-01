(() => {
  if (!document.body.classList.contains('article-page')) return;
  const match = location.pathname.match(/\/artikler\/([a-z0-9-]+)\.html$/i);
  if (!match) return;
  const payload = JSON.stringify({
    slug: match[1],
    title: (document.querySelector('h1')?.textContent || '').trim(),
    category: (document.querySelector('.section-label')?.textContent || '').trim(),
    referrer: document.referrer || '',
  });
  const endpoint = 'https://morgentidende-app.nicolaipetersen108.workers.dev/api/analytics/pageview';
  try {
    fetch(endpoint, {
      method: 'POST', mode: 'cors', keepalive: true, credentials: 'omit',
      headers: { 'content-type': 'application/json' }, body: payload,
    }).catch(() => {});
  } catch (_) {}
})();
