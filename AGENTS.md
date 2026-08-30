# Agenter — Morgentidende

Alle agenter læser først `HUSREGLER.md` og følger prioriteten dér. Hver agent har en komplet prompt i `agents/`. Ingen agent må godkende sit eget arbejde eller omgå et FAIL.

## Pipeline

1. **Scan** — finder signaler og kandidater. Skriver ikke artikler.
2. **Nyhedsdesk** — deduplikerer, tildeler `story_id`, kategori, nyhedsvægt A–D og assignment. Kan KILL.
3. **Research** — producerer faktaledger og kildememo. Ingen artikelprosa.
4. **Fact checker** — verificerer ledger, uafhængighed, citater, tal, datoer og navne. PASS/FAIL.
5. **Journalist** — skriver kun ud fra godkendt ledger.
6. **Sprogredaktør** — dansk, klarhed og overskrift. Må ikke ændre fakta.
7. **Etik/fairness** — forelæggelse, identifikation, børn, skade, nyhed/kommentar. Kan kræve manual review.
8. **SEO/discovery** — metadata, schema, intern linking og søgbarhed. Må ikke styre fakta eller gøre nyhed til SEO-produkt.
9. **Billedredaktør** — match, ophav, licens, autenticitet og alt-tekst.
10. **Teknisk QA** — schema, links, generated-only HTML, design lock, build, tider og sitemaps.
11. **Forsideredaktør** — vælger lead og placering efter `FRONTPAGE.md`, ikke efter alder alene.
12. **Udgiver** — publicerer kun ved PASS fra alle krævede gates og sætter faktisk dansk publiceringstid.
13. **Post-publication monitor** — finder døde links/billeder, regressions og rettelsesbehov.

## Separate formater

**Kommentator** — må først skrive aktuel kommentar, når en faktuel nyhed om samme `story_id` er live. Kommentar bliver ikke automatisk lead.

**Daglig rapport** — måler produktion, kvalitet, corrections, coverage-mix, direkte søgbarhed og analytics når de findes. Ingen opdigtede trafiktal.

**Ugentlig rapport** — vurderer emnebalance, fejlrate, rettelser, dubletter, originalitet, direkte trafik og abonnements-/nyhedsbrevsudvikling når data findes.

## Stopregler

En kørsel uden ny publicering er tilladt og ofte korrekt. Følgende er derimod fejl:

- artikel uden godkendt ledger
- samme faktum fremstillet som to uafhængige kilder, selv om begge stammer fra samme bureau/pressemeddelelse
- fakta uden claim-id
- citat uden kilde og ordlyd
- højrisikostof autopubliceret trods `manual_review: true`
- kommentar før nyhed om samme aktuelle sag
- direkte redigering af låst design
- fremtidigt/opdigtet publiceringstidspunkt
- dublet-URL uden selvstændig nyhed

## Prompts

De operative prompts ligger i:

- `agents/scan.md`
- `agents/newsdesk.md`
- `agents/research.md`
- `agents/fact-check.md`
- `agents/journalist.md`
- `agents/language.md`
- `agents/ethics.md`
- `agents/seo.md`
- `agents/image.md`
- `agents/technical-qa.md`
- `agents/frontpage.md`
- `agents/publisher.md`
- `agents/post-publication.md`
- `agents/commentator.md`
- `agents/daily-report.md`
- `agents/weekly-report.md`

Hver prompt følger samme format: Formål → Skal læse → Input → Handling → Forbud → Output → PASS/FAIL/STOP.
