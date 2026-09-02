# Agenter og processer — Morgentidende

Alle roller følger `HUSREGLER.md`. Hver beslutning har én ejer. En senere rolle må ikke rutinemæssigt gentage tidligere arbejde.

## Kernepipeline

1. **Scan** — billig bred radar. Finder, normaliserer og grupperer signaler. Ingen endelig nyhedsværdi eller verifikation.
2. **Nyhedsdesk** — vælger research-frø, story-id, kategori og foreløbig A-D-vægt. Åben ved indgangen; tynd dokumentation er Researchs problem.
3. **Research** — finder og strukturerer nødvendig evidens til 1–6 bærende kandidat-claims. Ingen nyhedsvurdering og ingen endelig sandhedsdom.
4. **Fact checker** — uafhængig verifier. Ét claim kan verificeres af én relevant autoritativ kilde, når kilden faktisk dokumenterer claimet inden for sit kompetence- eller vidensområde. Autoritative kilder omfatter store redaktionelle medier, myndigheder/officielle kilder, virksomheder eller personer om egne forhold, relevante forskere/fageksperter samt forskningspapirer/original forskning. Ét verificeret bærende claim kan være nok til en kort artikel.
5. **Nyhedsdesk recheck** — B-D går normalt deterministisk videre efter Fact checker PASS. Kun A/breaking får et ultrakort aktualitetsrecheck.
6. **Journalist** — skriver titel, manchet og artikel direkte fra verificerede claims og ejer normalt lægmandssprog/rubrik.
7. **Etik/fairness — betinget** — kører kun ved konkret risikoflag om fx forelæggelse, alvorlige beskyldninger, privatliv, børn, identifikation eller skade.
8. **Medieredaktør — betinget** — kører kun når eksternt dokumentarisk foto/video faktisk skal findes eller verificeres. Standardillustration kræver ikke et særskilt medie-AI-kald.
9. **Slutredaktør** — ét kompakt uafhængigt slutcheck mod verificerede claims; fanger kun materielle blockers og opretter final approval snapshot.
10. **Forsideredaktør** — vælger lead og placering blandt allerede publicerbare historier.

## Deterministisk maskinrum — ikke AI-agenter

- **SEO/metadata:** afledes normalt af titel/manchet og kontrolleres maskinelt; ingen fast SEO-agent.
- **Teknisk QA:** schema, links, canonical refs, build, sitemaps, assets og design lock.
- **Udgiver:** sætter kun publiceringsmetadata/PR-status; beslutter ikke journalistik.
- **Live technical QA:** tester live output, links/assets, embeds og template-markers.
- **Recovery:** router et blokeret stykke tilbage til præcis det manglende trin; ingen omgåelse af gates.

## Efter publicering

- **Live proofreader — betinget:** bruges til A/lead, konkrete anomalier eller stikprøver; ikke som fast AI-kald på hver artikel.
- **Update-monitor:** leder efter materielle nye oplysninger og kan sende UPDATE tilbage til Newsdesk/Research. Ved lead kan den samtidig åbne spor for nye fakta og bedre dokumentarisk foto/video; en særskilt lead-followup-agent er ikke nødvendig.
- **Correction editor — hændelsesstyret:** bruges kun ved materiel rettelse efter publicering.

Separate produktflows som `commentator.md`, `kronik-agent.md` og `short-video.md` er ikke trin i den almindelige nyhedspipeline. Daglig/ugentlig rapportering er driftsanalyse, ikke artikelbehandling.

## Effektivitetsprincipper

- **Én ejer pr. beslutning:** nyhedsværdi = Nyhedsdesk; evidensindsamling = Research; faktuel verifikation = Fact checker; fairness/forelæggelse = Etik; tekst = Journalist; slutkontrol = Slutredaktør; placering = Forsideredaktør; teknik = deterministic QA.
- **Billigt først:** kode/metadata/simple regler før AI.
- **Progressiv strenghed:** Scan og Newsdesk er åbne; strenghed stiger tættere på publicering og med reel risiko.
- **Risiko frem for kvoter:** ingen universelle minimumskrav på to claims, to eller tre kilder eller tre source-groups.
- **Normal kildegrundregel:** én relevant autoritativ kilde kan verificere et claim. Store medier er autoritative redaktionelle kilder; myndigheder er autoritative om deres officielle område; virksomheder/personer er autoritative om egne forhold; relevante forskere/fageksperter og forskningspapirer er autoritative inden for deres faglige/resultatmæssige område. Flere kilder bruges for pluralisme, mod-evidens og ekstra sikkerhed, ikke som mekanisk minimum.
- **Soft flags er ikke hard gates:** tvivl og risici routes til rette ejer.
- **Kompakte payloads:** claims + kildeindeks + korte relevante uddrag sendes videre; samme lange kildekontekst genbruges ikke blindt.
- **8B som standard:** stærk model bruges kun, når kompleksitet/risiko eller kvalitetsbehov reelt kræver det.
- **Ingen fyld:** korte historier må være korte.

## Pipeline v2

Alle nye autopublicerbare artikler har `pipeline_version: 2`. Research skriver coverage/evidens-overblik; Fact checker skriver `fact_check`; desk-recheck kan være deterministisk for B-D; Slutredaktør opretter `reports/editorial/approvals/<slug>.json`.

Approval snapshot beskytter redaktionelt indhold efter sidste kontrol. Udgiver må bagefter kun ændre tekniske/publiceringsfelter.

## Hard stops

Hard stops skal være få og konkrete: ingen verificerede bærende claims; et claim uden mindst én relevant autoritativ dokumentationskilde; uafsluttet konkret etik/manual-review; manglende final approval; teknisk korrupt artikel; højrisiko autopublicering; ugyldigt/opdigtet publiceringstidspunkt. Et bestemt antal kilder eller claims er ikke i sig selv et hard stop.
