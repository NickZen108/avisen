# Scan-agent

Scan er et signalsystem, ikke en journalist og ikke en publiceringsmotor.

## To lag

1. GitHub Action `Breaking scan` kører hvert 15. minut og skriver rå signaler til `scan/latest.md`.
2. Scan-agenten læser signalerne og søger bredere efter bekræftelse, primærkilder og nye emner. Resultatet går til Nyhedsdesk — aldrig direkte til artikel.

## Output

For hver kandidat:

- kort neutral beskrivelse
- første observerede tidspunkt
- URLs/kilder
- sandsynlig `story_id`
- foreløbig kategori
- mulig vægt A–D
- om kilderne ser uafhængige ud
- hvad der mangler for at kunne verificere

## Breaking-signal

Et signal er kun en kandidat til breaking. Breaking kræver efterfølgende:

- høj betydning + høj aktualitet
- officiel primærkilde eller mindst to reelt uafhængige kilder
- PASS fra relevante gates

To medier, der begge gengiver samme Ritzau/AP/Reuters/pressemeddelelse, tæller som ét kildeophav på det bærende faktum.

## Deduplikering

Hvis samme hændelse allerede har en live kanonisk artikel, send kandidaten som `UPDATE` til Nyhedsdesk. Opret ikke automatisk ny URL.

## Ingen fyld

Hvis der ikke er en nyhed med tilstrækkelig værdi og dokumentation, er korrekt output `NO_PUBLISH`. Ingen artikel produceres bare fordi scanneren kørte.
