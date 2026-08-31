# Gratis automationsarkitektur — eksperimentfase

## Princip

Redaktionel intelligens = ChatGPT/redaktion. GitHub Actions = deterministisk maskinrum.

Grok, Grok Bot og xAI-automatiseringer er ikke en del af avisen. De må ikke skrive, scanne, korrekturlæse eller committe her. Se `AI-POLICY.md`.

## Pipeline v2

1. Scan/queue finder kandidater.
2. Nyhedsdesk assignment.
3. Research coverage sweep + ledger.
4. Fact checker falsificerer claims.
5. Nyhedsdesk recheck `publish|update|hold|kill`.
6. Journalist → Sprog → Etik → Billede → SEO.
7. Slutredaktør opretter `reports/editorial/approvals/<slug>.json` med snapshot.
8. Forsideredaktør bruger canonical slug-reference for v2.
9. Teknisk QA.
10. Udgiver gør artiklen `ready` + `release_requested: true`, men sætter ikke `published_at`.
11. `[AUTO]` PR testes; merge accepterer kun pipeline-v2-artikler og allowlisten.
12. Efter merge sætter `release_ready.py` faktisk `published_at` ved build/release.
13. Generatoren bygger public-output og offentlig rettelseslog.
14. Post-deploy guard tester forside + netop ændrede/recent artikel-URL'er.
15. Live proofreader og redaktionel update-monitor er redaktionelle ChatGPT-opgaver, ikke GitHub-heuristikker og ikke Grok.

Final approval sammenlignes maskinelt med artikelens redaktionelle snapshot. Udgiver må bagefter kun ændre publiceringsmetadata.
