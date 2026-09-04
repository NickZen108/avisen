#!/usr/bin/env python3
"""Dedicated Danish language editor policy for Pipeline v3.

The language editor is allowed to improve prose, not only detect translation
artifacts. It must preserve documented facts, attribution, quotations and the
editorial angle while making the article read like professional Danish news.
"""
from __future__ import annotations


def install(p):
    def enhanced_language_review(draft, desk, story_id):
        model = p.CONFIG["models"]["language_editor"]
        instructions = """Du er Danskredaktør på Morgentidende. Din opgave er at løfte teksten til professionelt, naturligt og præcist dansk nyhedssprog.

Du skal både finde egentlige fejl OG forbedre sproget, når en formulering er tung, stiv, uklar, gentagende, maskinagtig eller mindre idiomatisk end den bør være. Se især efter svensk/norsk læk, engelske calques, falske venner, ord-for-ord-oversættelse, grammatik, uklare referencer, dårligt flow, unødige gentagelser, svage verber, tung syntaks, oppustet embedsmandssprog og rubrik/manchet der kan gøres skarpere.

Bevar altid dokumenterede fakta, tal, attribution, forbehold, direkte citater og historiens betydning. Du må ikke indføre nye fakta, ændre politisk substans eller gøre teksten mere kategorisk end evidensen tillader. Godt, enkelt dansk skal ikke pyntes unødigt.

Returnér KUN JSON:
{"status":"approve"|"revise","issues":[{"quote":"konkret passage","fix":"bedre naturlig dansk formulering","reason":"kort forklaring"}]}.

Vælg revise hvis konkrete ændringer mærkbart vil forbedre korrekthed, klarhed, rytme, præcision eller journalistisk kvalitet. Vælg approve når teksten allerede er publiceringsklar."""
        data, _ = p.call_json(
            "danish_editor",
            model,
            instructions,
            {"article": draft, "angle": desk.get("angle")},
            story_id=story_id,
            max_output_tokens=850,
            reasoning="low",
        )
        if data.get("status") not in {"approve", "revise"}:
            raise RuntimeError("Danish editor returned invalid status")
        issues = data.get("issues") or []
        if not isinstance(issues, list):
            raise RuntimeError("Danish editor returned invalid issues")
        data["issues"] = issues[:12]
        return data

    p.language_review = enhanced_language_review
