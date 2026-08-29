# Scan-agent

To pulser:
1. GitHub Action »Breaking scan« hvert 15. minut (UTC-cron). Skriver `scan/latest.md`.
2. Grok kører når det workflow slutter. Læs `scan/latest.md` + STYLE.md + EDITORIAL.md.

Breaking = samme sag hos mindst to, eller officiel kilde. Så 1–3 nyheder. Kommentar først efter en nyhed. `.related-teaser` begge veje. `.theme-box` ved ≥2 stykker.

Ikke breaking: ingen fyldartikel.
