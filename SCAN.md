# Scan-agent og discovery

Scan er et signalsystem, ikke journalist, fact checker eller publiceringsmotor.

## Arkitektur
1. Cloudflare Worker henter feeds hyppigt og gemmer rå signaler. Dette trin bruger ingen LLM-neurons.
2. GitHub synkroniserer inventaret.
3. En billig 8B-Newsdesk-vurdering får kun en kort deterministisk shortlist. Den vælger `RESEARCH`, `WATCH` eller `DROP`; kategori og A-D-vægt fastsættes her.
4. Research/Fact check kommer først bagefter.

## Shortlist uden blind vinkel
Shortlisten prioriterer aktualitet, placering i feedet, kildeklasse og offentlig/redaktionel relevans. Eksakte overskrifts-clusters giver kun en lille bonus og er aldrig bevis på kildeuafhængighed. Et mindre antal pladser reserveres til seriøse perspektiv-/discovery-kilder, så originale historier ikke drukner i mainstream-volumen.

## Perspektivkilder
Store liberale, konservative og nationalkonservative medier/blogs kan bruges som discovery i Skandinavien, Tyskland, Frankrig, Storbritannien og USA. Eksempler i den aktive scanner er bl.a. Document.no, Achgut, Tichys Einblick, Causeur, Contrepoints, Spiked, CapX, Reason, National Review, City Journal, FrontPageMag og JihadWatch.

Disse er markeret `discovery_only` i scanneren. Det er en sikkerhedsregel om kildebrug, ikke en dom over deres politiske syn: De må starte en historie og pege på oversete dokumenter, men de tæller ikke alene som uafhængig verifikation. Research forsøger automatisk at følge tydeligt betroede links til primærkilder/offentlige medier og kræver derefter den normale dokumentation.

## WATCH i stedet for tidligt afslag
Et vigtigt enkeltkilde-tip skal normalt blive `WATCH`, ikke dø. WATCH får kortere cooldown end en godkendt/publiceret historie, så ny dokumentation kan få sagen genåbnet.

## Flere samtidige historier
Samme scan-inventar må behandles flere gange. Allerede håndterede signaler får midlertidig TTL, så næste redaktionelle cyklus tager næste stærke kandidat i stedet for at vælge den samme igen. Import-workflowet kan behandle op til tre forskellige kandidater pr. 15-minutters runde.

## Ingen fyld
Når de resterende kandidater ikke bærer research, er `DROP`/ingen artikel korrekt. Kapacitet er ikke kvote.
