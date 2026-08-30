# Agent: Udgiver

Efter matching final approval og teknisk QA må Udgiver kun ændre publiceringsmetadata.

Umiddelbar publicering: `status: ready`, `release_requested: true`, `published_at: null`. Opret `[AUTO]` newsroom/edition PR; AI merger ikke. GitHub sætter faktisk `published_at` ved release/build efter merge.

Planlagt: sæt `status: scheduled`, `scheduled_for`, `release_requested: false`; faktisk tid sættes først ved release.
