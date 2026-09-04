#!/usr/bin/env python3
"""Dedicated Danish copy editor for Pipeline v3.

Terra receives only the journalist's finished draft (plus the angle for context)
and returns the polished publication draft. This keeps the expensive model away
from the large evidence bundle while giving it real responsibility for Danish
clarity, rhythm and journalistic prose.
"""
from __future__ import annotations


def install(p):
    def polish_language(draft, desk, story_id):
        model = p.CONFIG["models"]["language_editor"]
        instructions = """Du er Danskredaktør på Morgentidende. Redigér den medsendte artikel direkte til publiceringsklart dansk.

Du er ikke kun korrekturlæser. Forbedr aktivt klarhed, præcision, rytme, flow og journalistisk styrke. Ret svensk/norsk læk, engelske calques, falske venner, ord-for-ord-oversættelse, grammatik, uklare referencer, stift eller maskinagtigt sprog, svage verber, gentagelser, tung syntaks og oppustet embedsmandssprog. Gør rubrik og manchet skarpere når det tydeligt forbedrer teksten.

Bevar dokumenterede fakta, tal, attribution, forbehold, direkte citaters betydning og den redaktionelle vinkel. Indfør ingen nye fakta og gør ikke udsagn mere sikre end de var. Overredigér ikke godt, enkelt dansk.

Returnér KUN JSON i denne form:
{"title":"...","standfirst":"...","body":[{"type":"p","text":"..."},{"type":"h2","text":"..."}],"changes_summary":["kort beskrivelse"]}.
Returnér HELE den redigerede artikel, også når kun få ændringer er nødvendige."""
        data, _ = p.call_json(
            "danish_editor",
            model,
            instructions,
            {"article": {"title": draft.get("title"), "standfirst": draft.get("standfirst"), "body": draft.get("body")},
             "angle": desk.get("angle")},
            story_id=story_id,
            max_output_tokens=1900,
            reasoning="low",
        )
        polished = p.normalize_draft(data)
        # Preserve non-language metadata produced by the journalist.
        draft["title"] = polished["title"]
        draft["standfirst"] = polished["standfirst"]
        draft["body"] = polished["body"]
        # The base orchestrator expects approve/revise. Terra has already performed
        # the edit, so returning approve prevents an unnecessary Qwen rewrite.
        return {
            "status": "approve",
            "issues": [],
            "changes_summary": (data.get("changes_summary") or [])[:8],
        }

    p.language_review = polish_language
