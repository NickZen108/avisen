# Pipeline v2 — QUARANTINED

Pipeline v2 was quarantined on 2026-09-04 after repeated editorial-quality and workflow-audit failures during controlled Burst 3 experiments.

## Status

- Do not use Pipeline v2 for article production.
- The old source code remains in Git history and in the existing `cloudflare/newsdesk` tree as a reference only.
- `cloudflare-editorial-sync.yml`, `burst-3-once.yml`, `dispatch-burst-3-once.yml`, and `cloudflare-newsdesk-deploy.yml` are deliberately inert quarantine stubs.
- The currently deployed v2 Newsdesk Worker may continue to expose discovery/scan data, but no repository workflow is allowed to call its v2 editorial production endpoint.
- Ordinary site build/deploy remains separate from the quarantined editorial chain so existing published content can still be served and manually corrected.

## Why it was quarantined

Observed classes of failure included:

1. malformed structured model output becoming publishable fallback text;
2. broken Danish / literal machine-translation language passing final review;
3. semantically wrong documentary hero images despite valid rights metadata;
4. inconsistent story geography/entity metadata;
5. validation/audit stages disagreeing about whether a candidate had actually passed publication;
6. accumulated retries, gates and special-case logic making responsibility unclear.

## Boundary for Pipeline v3

Pipeline v3 must be built separately and must not reactivate v2 workflows. Reuse only components that are independently useful (for example source discovery, static site rendering or image caching) and only after explicitly reviewing their contract.

The v3 design goal is a small number of intelligent editorial decisions, typed hand-offs, explicit failure states, cheap models for routine work, and one strong independent final review before publication.
