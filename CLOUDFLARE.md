# Cloudflare distribution

Morgentidende uses GitHub as source of truth. Cloudflare Workers Static Assets is a distribution layer for the already generated `docs/` tree; Cloudflare must not become an independent content source.

## Worker configuration

The repository root contains `wrangler.jsonc` with:

- Worker name: `morgentidende`
- Assets directory: `./docs`
- HTML handling: `none` (preserves existing `.html` URLs)
- No Worker script/runtime code
- `workers.dev` enabled for staging/verification

## Workers Builds settings

When connecting this repository in Cloudflare Workers & Pages:

- Repository: `NickZen108/avisen`
- Production branch: `main`
- Root directory: repository root
- Build command: leave blank
- Deploy command: `npx wrangler deploy`
- Non-production deploy command: `npx wrangler versions upload`
- Build watch include paths: `docs/*`, `wrangler.jsonc`
- Do not trigger production deploys for content/source-only commits; the GitHub publisher first renders approved content into `docs/`.

The `docs/_headers` rules prevent `workers.dev` staging and preview URLs from being indexed. Do not remove those noindex rules until a deliberate decision is made to use a workers.dev hostname as the canonical production hostname.

## Cutover rule

Do not change canonical URLs, sitemap base URLs, or the GitHub post-deploy guard until the Cloudflare staging deployment passes both:

```bash
python scripts/live_qa.py --base-url https://<worker>.workers.dev/ --strict-internal
python scripts/live_recent_qa.py --base-url https://<worker>.workers.dev/ --recent-hours 24
```

After staging passes, attach the final production domain, verify it, then change canonical/sitemap/live-QA targets in one atomic repository change. Keep the previous distribution path available as rollback until the new production path has passed live proof.
