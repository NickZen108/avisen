# Korrekturvagt

Se AGENTS.md, afsnittet Korrekturvagt. Første pligt: slet interne noter på alle sider.

## Døde billeder (obligatorisk)

Tematisk match er ikke nok. Hvert `<img>` på forside, artikelside, rail og `.below` skal hentes.

Dødt foto, hvis én af delene gælder:

- HTTP 404, 5xx, timeout eller tomt svar
- src peger på en wikiside, ikke en rå billedfil
- alt-teksten vises i en grå kasse på den live side
- filen i `docs/img/` findes, men src peger et andet sted hen og det andet sted er dødt

Handling: erstat src med lokal fil i `docs/img/` hvis den findes; ellers med en verificeret rå billed-URL. Commit. Skriv fil og årsag i `reports/qa/`.

Et foto der matcher emnet, men ikke loader, er veto — samme regel som foto-mismatch i EDITORIAL.md.
