const SECURITY_HEADERS = {
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'permissions-policy': 'camera=(), microphone=(), geolocation=(), payment=()',
  'cross-origin-opener-policy': 'same-origin',
  'content-security-policy': "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline'; frame-src https://www.youtube-nocookie.com; connect-src 'self'; form-action 'self' https://formsubmit.co; upgrade-insecure-requests",
};

export default {
  async fetch(request, env) {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
      return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, HEAD, OPTIONS' } });
    }
    if (request.method === 'OPTIONS') return new Response(null, { status: 204 });
    const response = await env.ASSETS.fetch(request);
    const headers = new Headers(response.headers);
    for (const [key, value] of Object.entries(SECURITY_HEADERS)) headers.set(key, value);
    if (new URL(request.url).pathname.startsWith('/kontrolrum')) {
      headers.set('cache-control', 'private, no-store');
      headers.set('x-robots-tag', 'noindex, nofollow');
    }
    return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
  },
};
