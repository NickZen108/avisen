# Newsdesk internal authentication

Internal Newsdesk JSON endpoints are fail-closed behind the Worker secret `EDITORIAL_RUN_TOKEN`. Do not commit the value.

Before merging/deploying the auth guard, set the Worker secret:

```bash
npx wrangler secret put EDITORIAL_RUN_TOKEN --config cloudflare/newsdesk/wrangler.jsonc
```

Then add the **same value** as the GitHub repository secret `EDITORIAL_RUN_TOKEN`.

Public endpoints remain limited to `GET /health` and retrieval of already-known `/media/<key>` assets. Cloudflare Access for Kontrolrummet is a separate dashboard task and is not configured by this patch.
