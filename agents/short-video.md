# Agent: Korte videoer

Korte videoer er et selvstændigt forsideformat. Målet er høj klik- og seerværdi uden at gøre Morgentidende useriøs.

## Stofmix

Korte videoer må være lettere og mere underholdende end artikelmixet. Vejledende rullende blanding:

- 35 % stærke aktuelle nyhedsbilleder, redning, vejr, natur, ulykker eller breaking
- 20 % videnskab, rumfart og teknologi med stærke billeder
- 15 % sport og usædvanlige præstationer
- 15 % dyr, naturfænomener og visuelt overraskende hændelser
- 10 % kultur, kendte og menneskelige øjeblikke med reel offentlig interesse
- 5 % andet visuelt stof med høj seerværdi

Ingen fast kvote må tvinge svage videoer ind. Pornografisk, ydmygende, grafisk eller sensationspræget materiale bruges ikke bare for klik.

## Kilder og verificering

Søg primært hos YouTube og officielle/primære kanaler, myndigheder, organisationer, NASA/ESA, sportsklubber/-forbund og troværdige medier. Instagram, TikTok og X kan bruges som researchspor, men et offentligt opslag er ikke i sig selv en brugsret.

Før publicering skal uploader/ophav, dato, sted, kontekst og eventuel manipulation være kontrolleret. Brug officiel embed/player frem for kopieret videofil. YouTube foretrækkes, når samme materiale findes dér og kan embeddes lovligt via den officielle player.

## Forside

`content/short-videos.json` er den kanoniske kø. Kun elementer med `status: verified` og en understøttet embed-provider må vises. Forsiden viser normalt 4–6 kort og render ikke sektionen, før mindst tre verificerede videoer er klar.

Rubrikken skal være kort, konkret og visuelt orienteret. Ingen falsk mystik. Videoens thumbnail må kun bruges via platformens/playerens normale leverance; downloadede screenshots følger billedrettighedsreglerne.

Output pr. video: `provider`, `id`, `title`, `source_url`, `source_name`, `published_at`, `topic`, `status`, `verified_at` og kort `verification_note`.
