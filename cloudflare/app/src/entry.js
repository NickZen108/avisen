import app from './index.js';

const PUBLIC_SITE = 'https://morgentidende.nicolaipetersen108.workers.dev';

async function controlRoomResponse() {
  const upstream = await fetch(`${PUBLIC_SITE}/kontrolrum/index.html`, {
    headers: { 'user-agent': 'Morgentidende-Control-Room-Proxy/1.0' },
  });
  if (!upstream.ok) {
    return new Response('Kontrolrummet kunne ikke indlæses.', {
      status: 502,
      headers: {
        'content-type': 'text/plain; charset=utf-8',
        'cache-control': 'no-store',
      },
    });
  }

  let body = await upstream.text();
  body = body
    .replaceAll('href="../"', `href="${PUBLIC_SITE}/"`)
    .replaceAll("href='../'", `href='${PUBLIC_SITE}/'`);

  return new Response(body, {
    status: 200,
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store, private',
      'x-robots-tag': 'noindex, nofollow, noarchive',
      'referrer-policy': 'no-referrer',
      'x-content-type-options': 'nosniff',
      'content-security-policy': "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'GET' && (url.pathname === '/kontrolrum' || url.pathname.startsWith('/kontrolrum/'))) {
      return controlRoomResponse();
    }
    return app.fetch(request, env, ctx);
  },
};
