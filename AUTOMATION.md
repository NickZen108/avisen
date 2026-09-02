# Gratis automationsarkitektur — eksperimentfase

## Princip

Redaktionel intelligens = få tydeligt ejede AI-beslutninger. GitHub Actions = deterministisk maskinrum. En rolle må ikke være et AI-kald bare fordi en klassisk avis ville have en medarbejder med den titel.

## Pipeline v2

1. Scan/queue finder kandidater billigt.
2. Nyhedsdesk vælger research-frø.
3. Research bygger kompakt evidenskort.
4. Fact checker verificerer/falsificerer claims.
5. B-D går normalt deterministisk videre; A/breaking får ultrakort desk-recheck.
6. Journalist skriver titel, manchet og artikel fra verified claims.
7. Etik kører kun ved konkret risikoflag. Medieredaktør kører kun ved eksternt dokumentarisk foto/video; ellers bruges standardillustration.
8. Slutredaktør laver ét kompakt slutcheck og approval snapshot.
9. Forsideredaktør placerer publicerbare historier.
10. Teknisk QA, metadata/SEO, build og publiceringskontrol er deterministiske.
11. Udgiver gør artiklen `ready` + `release_requested: true`; faktisk `published_at` sættes ved release.
12. Efter merge bygger generatoren output og post-deploy guard tester liveflader.
13. Live proofreader er kun nødvendig ved A/lead, konkret anomaly eller stikprøve. Update-monitor følger materielle ændringer.

## Forbrugsregel

Llama 3.1 8B er standard til desk, research, fact-check, journalistik og slutkontrol. Llama 3.3 70B er kun fallback ved struktureret output-fejl på A- og B-artikler. Flux Schnell bruges kun som sidste hero-udvej på A; B–D får statisk skitse, hvis intet lovligt foto findes. Send korte kildeuddrag og strukturerede claims. Editorial-sync kører én cyklus pr. cron som standard.

## Ingen skjulte kvoter

Deterministiske scripts må ikke genindføre strengere redaktionelle krav end husreglen. Der er ingen universel hard gate på tre kilder, tre source-groups eller to claims. **Én relevant autoritativ kilde er nok** til et almindeligt bærende faktum. Navngiven sigtet/tiltalt/mistænkt kræver primærkilde eller original bureaukilde. Højrisiko kan kræve etik/forelæggelse — ikke en skjult to-kilde-kvote. Discovery-only er aldrig evidens.
