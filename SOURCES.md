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

## Minimum for bærende faktum

Godkend når mindst én af disse er opfyldt:

- én primærkilde, som selv er autoritativ for netop faktummet, **eller**
- to reelt uafhængige navngivne kilder

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
