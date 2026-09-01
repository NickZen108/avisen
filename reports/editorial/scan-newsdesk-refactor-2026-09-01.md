# Scan/Newsdesk-refaktor — 1. september 2026

Implementeret efter redaktionel gennemgang:

- Scan er reduceret til discovery/deduplikering/metadata; kategori, A-D-vægt og researchdom ligger hos Nyhedsdesk.
- Exact-headline-clusters er nedgraderet fra dominerende rankingfaktor til lille bonus.
- AI-shortlist reduceret fra 40 kandidater á 360 tegn til 28 á 220 tegn; Newsdesk-outputloft 900 → 550 tokens.
- Research-outputloft 2200 → 1800; Fact checker 2400 → 2200.
- Deterministisk relateret-historie-ekspansion gør, at Newsdesk kan vælge få seed-signaler og Research stadig kan få op til seks relevante kilder.
- `WATCH` beskytter vigtige enkeltkilde-tip mod tidligt permanent afslag.
- Håndterede signaler får TTL, så samme inventar kan levere flere forskellige historier uden at AI vælger den samme igen.
- Automatisk Cloudflare cron laver kun discovery; editorial AI køres i import-workflowet, så godkendte pakker ikke overskrives før GitHub kan importere dem.
- Import-workflowet kører hvert 15. minut og kan behandle op til tre forskellige kandidater.
- Discovery-nettet er udvidet med flere mainstream-kilder og liberale/konservative/nationalkonservative perspektivkilder i Skandinavien, Tyskland, Frankrig, UK og USA, herunder JihadWatch/FrontPageMag.
- Perspektiv-/advocacy-kilder er `discovery_only`: de kan starte research, men tæller ikke som verifikation. Research følger betroede links til primærkilder/offentlige medier, når de findes.
- Fact-check-reglen er harmoniseret med `SOURCES.md`: ét autoritativt primærdokument ELLER to reelt uafhængige ikke-discovery-kilder kan verificere et claim.

Målet er højere recall af vigtige historier, færre falske afslag og lavere neuron/token-forbrug i første redaktionelle led uden at svække verifikationsgates.
