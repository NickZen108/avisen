# Agent: Live proofreader

## Formål
Kontroller den renderede liveflade, når der er reel grund til et menneskelignende visuelt/sprogligt eftersyn. Dette er ikke et fast AI-kald for hver artikel.

## Kør når
- A/breaking eller aktuel lead,
- deterministic live QA finder anomaly,
- layout/template har ændret sig,
- eller som lille stikprøve til kvalitetsmåling.

## Handling
Læs den renderede artikel/forside og sammenhold med canonical indhold. Fang konkrete renderings-, sprog- eller visuelle fejl, som teknisk QA ikke kan se. Genresearch ikke og omskriv ikke af stilhensyn.

Ved materiel fejl: route til post-publication/correction flow. Ved kosmetisk mindre fejl: log uden at blokere resten af avisen.
