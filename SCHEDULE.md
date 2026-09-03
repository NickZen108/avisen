# Udgivelsesstrategi

Målet er høj nyhedsværdi og stabil kvalitet, ikke et bestemt antal filer pr. døgn.

## Ingen tvungen timeartikel

En stille periode uden en artikel er ikke en fejl. En svag, gammel eller dårligt dokumenteret artikel er en fejl. Breaking kommer oveni den normale rytme. Volumen må aldrig være årsag til publicering.

## Døgnrytme — dansk tid

- **23.00–05.30:** overvågning; kun tung breaking prioriteres automatisk.
- **05.45–06.15:** morgenudgave og ny vurdering af lead/forside.
- **06.15–09.00:** høj beredskab for morgenudviklinger.
- **09.00–15.00:** kontinuerlig publicering efter vægt og readiness, med frokost-refresh omkring middag.
- **15.00–19.00:** tung eftermiddags-/aftennyhedsperiode.
- **19.00–22.00:** færre, stærkere stykker; forklaring, feature, guide og udvalgt kommentar kan fylde mere.
- **22.00–23.00:** oprydning, rettelser og næste morgens research.

Rytmen er en planlægningsmodel, ikke en kvote.

## Planlagt kø

Evergreen, feature, guide, historie, videnskab og datastof kan færdiggøres i batches og få `status: scheduled` samt et timezone-aware `scheduled_for`. De følger samme redaktionelle approval-flow som øvrige artikler. `published_at` sættes først, når artiklen faktisk frigives.

Aktuelle nyheder vurderes løbende. Breaking kan tilsidesætte den planlagte rytme. Planlagt stof er en distributionsmekanisme, ikke en produktionskvote.

## Nyhedsvægt

Nyhedsdesk klassificerer kandidater:

- **A — breaking/tung:** stor pågående hændelse eller beslutning med høj offentlig betydning og høj aktualitet
- **B — væsentlig:** klar national/regional eller sektorbetydning
- **C — normal:** relevant, verificeret daglig nyhed
- **D — evergreen/dybde:** guide, feature, historie, baggrund

Vægt afgøres af betydning og aktualitet, ikke af mekaniske kildekvoter.

## Breaking

Breaking kan publiceres uden at vente på næste planlagte refresh, når det bærende faktum er dokumenteret efter `SOURCES.md`, rubrikken holder sig til det sikkert kendte, og de almindelige redaktionelle approval-led er bestået.

Breaking overtager kun lead, hvis `FRONTPAGE.md` vurderer, at historien faktisk er vigtigst.

## Story clusters og opdateringer

Ved en fortsættende hændelse opdateres den kanoniske artikel med `updated_at`, så længe kernehistorien er den samme. Nyt URL kræver ny hændelse, ny selvstændig vinkel eller andet format.

En gammel artikel må aldrig få nyt publiceringstidspunkt bare for at se frisk ud. Substantielle opdateringer får tydelig `Opdateret`-tid.

## Kommentar

Kommentar om en aktuel nyhed publiceres først efter en faktuel artikel om samme story. Kommentar er sjældnere end nyhed og normalt ikke første format under ufuldstændig breaking-information.
