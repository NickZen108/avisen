# Agenter og processer — Morgentidende

Alle roller følger `HUSREGLER.md`. Hver beslutning har én ejer. En senere rolle må ikke rutinemæssigt gentage tidligere arbejde.

## Kernepipeline

1. **Scan** — finder, normaliserer og grupperer signaler. Ingen endelig verifikation.
2. **Nyhedsdesk** — vælger research-frø, story-id, kategori og foreløbig A-D-vægt.
3. **Research** — finder og strukturerer nødvendig evidens. Kildekrav følger `SOURCES.md`.
4. **Fact checker** — afgør hvilke claims der er tilstrækkeligt dokumenterede.
5. **Journalist** — skriver titel, manchet og artikel fra verificerede claims.
6. **Sprog** — forbedrer dansk, klarhed og læsbarhed uden at ændre mening.
7. **Etik/fairness** — vurderer konkrete risici om bl.a. alvorlige beskyldninger, privatliv, børn, identifikation og skade.
8. **Medieredaktør** — vælger og verificerer foto/video/illustration efter gældende medieregler.
9. **SEO/discovery** — metadata og discovery-optimering; må ikke ændre journalistikken og må ikke blokere publicering alene.
10. **Slutredaktør** — foretager det samlede uafhængige slutcheck, herunder korrekt kategori, og opretter final approval snapshot.
11. **Forsideredaktør** — vælger lead og placering blandt allerede publicerbare historier.

## Deterministisk maskinrum

- **Udgiver/release:** ændrer kun publiceringsmetadata og afgør ikke journalistik.
- **Builder:** genererer offentlig HTML fra canonical data.
- **Teknisk QA:** kontrollerer relevante kode-/buildforhold, ikke redaktionelle beslutninger.
- **Live QA:** kontrollerer den publicerede overflade efter deploy.
- **Recovery:** sender et fejlende stykke tilbage til den ansvarlige eksisterende rolle i stedet for at omgå problemet.

## Efter publicering

- **Update-monitor:** følger materielle nye oplysninger og kan sende en historie tilbage til Newsdesk/Research.
- **Correction editor:** bruges ved materielle rettelser efter publicering.

Separate produktflows som `commentator.md`, `kronik-agent.md` og `short-video.md` er ikke trin i den almindelige nyhedspipeline. Rapportering og analytics er driftsanalyse, ikke artikelbehandling.

## Ansvarsprincipper

- Én ejer pr. beslutning.
- Research indsamler; Fact checker verificerer; Journalist skriver; Sprog forbedrer formulering; Etik vurderer skade/fairness; Medieredaktør ejer billeder; Slutredaktør ejer samlet approval og kategori; Forsideredaktør ejer placering.
- Kilde- og evidensregler findes kun i `SOURCES.md` og overordnede stopregler i `HUSREGLER.md`.
- Ingen agent må skabe egne skjulte kvoter eller ekstra gates.
- En fejl routes til den rolle, der ejer fejlen, frem for at blive kontrolleret igen af flere efterfølgende roller.
