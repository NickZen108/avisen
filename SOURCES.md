# Kilder og faktaledger

Morgentidende skriver ikke direkte fra en løs bunke links. Research omsætter kilder til en struktureret faktaledger; Journalisten må kun bruge godkendte claims.

## Kildehierarki

1. primærdokument: lov, dom, myndighedsafgørelse, officiel statistik, regnskab, paper, original tale/interview, direkte partsvar
2. troværdig nyhedsorganisation med egen reporting
3. fagmedie/sekundær analyse med tydelig kilde
4. blog, social post, YouTube, anonym kanal eller aggregator

## Discovery-/perspektivkilder

Ideologiske, aktivistiske eller stærkt kommenterende medier kan være fremragende til at opdage oversete sager. De kan derfor stå i scannerens feednet som `discovery_only`. Det betyder:

- de kan udløse `RESEARCH` eller `WATCH`
- de kan pege på primærdokumenter og andre kilder
- deres politiske retning er ikke i sig selv et argument for eller imod historien
- de tæller ikke alene som uafhængig verifikation af et bærende claim
- hvis de linker til en autoritativ primærkilde, skal Research åbne og kontrollere primærkilden direkte

En autoritativ primærkilde kan fortsat bære et faktum efter reglerne nedenfor; ellers kræves reelt uafhængig dokumentation.

## Uafhængighed

To URLs er ikke nødvendigvis to kilder. `source_group` registrerer det oprindelige ophav.

## Coverage sweep før skrivning

Når Nyhedsdesk har valgt en nyhed til research med henblik på publicering, skal Research:

- finde relevant primærkilde, når den findes
- normalt gennemgå mindst **3 reelt uafhængige redaktionelle kilder** om samme historie, når sådanne findes
- søge på tværs af relevante internationale/nationale medier, fagmedier og lokale/specialiserede kilder
- sammenligne centrale fakta, konsekvenser, citater, forbehold, modpositioner og kontekst
- registrere hvilke væsentlige pointer kun enkelte dækninger havde
- undgå at bruge én artikel som skjult skabelon

Ledgeren har et maskinlæsbart `coverage_sweep` med `status`, `editorial_source_ids`, `independent_source_groups`, `limitations` og `notes`.

`pass` kræver normalt mindst tre reelt uafhængige coverage-source-groups. `limited` bruges fx tidligt i breaking og kræver en konkret begrundelse. `not_required` er kun til genrer, hvor et nyheds-coverage sweep reelt ikke giver mening, og kræver begrundelse.

Coverage-bredde er ikke kunstig 50/50. Evidens og relevans afgør vægten.

## Minimum for bærende faktum

Et bærende faktum kan godkendes ved én autoritativ primærkilde eller to reelt uafhængige navngivne kilder. Coverage sweep erstatter ikke dette krav og omvendt.

## Fact check og desk recheck

Fact checker udfylder `fact_check.status = pass|fail`, tidspunkt og noter. Efter Fact checker ser Nyhedsdesk det dokumenterede resultat igen og udfylder `desk_recheck.status = publish|update|hold|kill` med tidspunkt og begrundelse.

Fact check PASS betyder “dokumenteret”, ikke automatisk “værd at publicere”.

## Forelæggelse/modpart

`right_of_reply.required: true` er en hard gate. Uden dokumenteret undtagelse kræves `party`, `contacted_at`, `deadline` og enten et registreret svar eller en udløbet svarfrist.

## AI

AI-genereret tekst, opsummeringer eller søgesvar er aldrig source-id. Oprindelige kilder skal åbnes og kontrolleres.
