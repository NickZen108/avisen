# Morgentidende automation

## Grundprincip

GitHub er sandheden for redaktionelt indhold og publiceringsstatus. Cloudflare Newsdesk producerer og vurderer historier, mens deterministiske gates håndhæver de fælles minimumskrav uden at opfinde strengere redaktionelle kvoter.

## Standardflow

1. Newsdesk opdager kandidathistorier.
2. Desk vælger og prioriterer historier efter nyhedsværdi, aktualitet og relevans.
3. Research henter relevante kilder og udleder kandidat-claims.
4. Fact checker forsøger aktivt at falsificere kandidat-claims og markerer kun dokumenterede claims som verified.
5. Desk recheck vurderer, om den verificerede kerne stadig er en publicerbar historie.
6. Journalist skriver udelukkende på baggrund af verificerede claims.
7. Sprog, etik/fairness, billede, SEO og slutredaktør gennemgår artiklen.
8. Deterministiske quality gates kontrollerer kontrakterne.
9. Godkendt indhold lander i GitHub og kan publiceres.
10. Cloudflare bygger og serverer den aktuelle version.
11. Post-publication checks kontrollerer live-output og materielle ændringer.
12. Efter merge bygger generatoren output og post-deploy guard tester liveflader.
13. Live proofreader er kun nødvendig ved A/lead, konkret anomaly eller stikprøve. Update-monitor følger materielle ændringer.

## Forbrugsregel

Llama 3.1 8B er standard til desk, research, fact-check, journalistik og slutkontrol. Llama 3.3 70B er kun fallback ved struktureret output-fejl på A- og B-artikler. Flux Schnell bruges kun som sidste hero-udvej på A; B–D får statisk skitse, hvis intet lovligt foto findes. Send korte kildeuddrag og strukturerede claims. Editorial-sync kører én cyklus pr. cron som standard.

## Ingen skjulte kvoter

Deterministiske scripts må ikke genindføre strengere redaktionelle krav end husreglen. Der er ingen universel hard gate på tre kilder, tre source-groups eller to claims. **Én relevant autoritativ kilde er nok** til et almindeligt bærende faktum. Navngiven sigtet/tiltalt/mistænkt kræver primærkilde eller original bureaukilde. Højrisiko kan kræve etik/forelæggelse — ikke en skjult to-kilde-kvote. Discovery-only er aldrig evidens.
