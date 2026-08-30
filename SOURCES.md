# Kilder og faktaledger

Morgentidende skriver ikke direkte fra en løs bunke links. Research skal først omsætte kilder til en struktureret faktaledger. Journalisten må kun bruge faktuelle påstande, der er godkendt i ledgeren.

## Kildehierarki

Stærkest som udgangspunkt:

1. primærdokument: lov, dom, myndighedsafgørelse, officiel statistik, regnskab, paper, original tale/interview, direkte partsvar
2. troværdig nyhedsorganisation med egen reporting
3. fagmedie/sekundær analyse med tydelig kilde
4. blog, social post, YouTube, anonym kanal eller aggregator

Niveau 4 kan være kilde til, **at afsenderen har sagt/postet noget**, men er normalt ikke tilstrækkelig dokumentation for det underliggende faktum.

## Uafhængighed

To URLs er ikke nødvendigvis to kilder. Research registrerer `source_group` for det oprindelige ophav.

Eksempler:

- DR og TV 2 citerer samme Ritzau-telegram → ét source-group på telegrammets faktum
- tre medier citerer samme pressemeddelelse → ét source-group på selskabets påstand
- dom + selvstændigt medieinterview → to uafhængige ophav

## Coverage sweep før skrivning

Når Nyhedsdesk har valgt en nyhed til research med henblik på publicering, skal Research ikke nøjes med den kilde, der gjorde redaktionen opmærksom på historien.

Før en nyhedsartikel må gå til Journalist, skal Research:

- finde relevant primærkilde, når den findes
- normalt gennemgå mindst **3 reelt uafhængige redaktionelle kilder**, der dækker samme historie, når sådanne findes
- søge efter kilder med forskellig relevant adgang til historien, fx internationalt nyhedsmedie, dansk/national dækning, fagmedie, lokal dækning eller selvstændig reporting
- sammenligne hvilke væsentlige fakta, konsekvenser, citater, forbehold, modpositioner og kontekst de forskellige kilder bidrager med
- registrere væsentlige uenigheder eller forskelle i faktaledger/memo
- undgå at bruge én artikel som skjult skabelon for Morgentidendes tekst

Formålet er både **fuldstændighed og pluralisme**: forskellige redaktioner opdager og prioriterer ofte forskellige væsentlige dele af samme historie. Coverage sweep er derfor ikke kun et fact-check, men en systematisk søgning efter manglende relevante pointer.

Tre URLs er ikke nok. Bureaukopier, syndikering, omskrivninger af samme artikel eller medier der alle bygger på samme pressemeddelelse tæller ikke som tre uafhængige coverage-kilder.

Hvis færre end 3 reelt uafhængige redaktionelle kilder findes — fx meget tidligt i breaking news — dokumenterer Research søgningen og begrænsningen. Historien kan fortsætte, hvis kravene til bærende fakta nedenfor er opfyldt, men Fact checker skal tage eksplicit stilling til den manglende bredde, og historien bør genundersøges ved senere UPDATE når flere kilder bliver tilgængelige.

Coverage-bredde er ikke det samme som kunstig balance. En svag eller udokumenteret modposition får ikke samme vægt som stærk evidens alene for at skabe 50/50-symmetri.

## Minimum for bærende faktum

Godkend når mindst én af disse er opfyldt:

- én primærkilde, som selv er autoritativ for netop faktummet, **eller**
- to reelt uafhængige navngivne kilder

Dette minimum afgør, om et faktum kan bæres. Det erstatter ikke coverage sweep for en hel nyhedsartikel.

En pressemeddelelse er primær dokumentation for, hvad afsenderen meddeler, men ikke automatisk sandhedsbevis for en omstridt ekstern påstand.

Alvorlige anklager, store ukendte tal eller påstande med høj skade kræver skærpet dokumentation og kan udløse manuel review.

## Faktaledger

Én ledger pr. story/article under `sources/`. JSON er canonical for nye artikler.

Hver claim indeholder mindst:

- `id`: stabilt claim-id, fx `F01`
- `claim`: kort neutral faktasætning
- `status`: `verified`, `disputed`, `uncertain`, `rejected`
- `source_ids`: kilder der understøtter
- `independent_groups`: ophavsgrupper
- `checked_at`: tidspunkt
- `notes`: forbehold/konflikter

Hver source indeholder mindst:

- `id`
- `name`
- `url`
- `published_at` eller `accessed_at`
- `type`: `primary`, `news`, `paper`, `interview`, `other`
- `source_group`
- `authoritative_for`: hvad kilden faktisk kan bevise

Coverage-memoet skal desuden gøre det muligt for Fact checker at se, hvilke kilder der blev gennemgået, hvilke der er reelt uafhængige, og hvilke væsentlige pointer der kom fra forskellige dækninger.

## Tal

For hvert centralt tal skal ledgeren registrere:

- værdi
- enhed
- periode/dato
- population/nævner når relevant
- evt. beregningsformel
- kilde

Procenter og procentpoint skelnes. Tal fra forskellige datoer eller populationer må ikke lægges sammen uden dokumenteret metode.

## Citater

Direkte citat kræver:

- ordret originaltekst eller lyd/transkript
- speaker
- kilde-URL/dokument
- kontekst nok til at sikre mening
- oversættelsesstatus

Hvis ordlyden ikke kan genfindes: parafrasér eller drop citatet. Citat i H1 kræver ekstra fact-check.

## Egennavne og titler

Navn, titel, embede, organisation, geografi og juridisk status verificeres særskilt. Ingen automatisk udfyldning fra modelhukommelse.

## Dato og freshness

Ledgeren registrerer, hvornår hændelsen skete, og hvornår kilden blev publiceret. Evergreen må gerne være ældre. Nyhed må ikke sælges som ny, hvis den bærende udvikling er gammel.

## Modpart

I en konkret strid registreres:

- hvem kritikken retter sig mod
- om parten er kontaktet eller allerede har et relevant offentligt svar
- svar/fravær af svar
- deadline

Manglende svar er ikke tilladelse til at gætte partens holdning.

## AI

AI-genereret tekst, opsummeringer eller søgesvar er aldrig source-id. AI kan hjælpe med at finde kilder, men fact checker skal åbne og kontrollere den oprindelige kilde.
