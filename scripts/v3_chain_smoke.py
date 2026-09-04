#!/usr/bin/env python3
"""Tiny budget-accounted smoke for the non-Terra parts of the v3 chain."""
from __future__ import annotations

import v3_safe_runner as s


def main():
    s.install_safety_hooks()

    desk_model = s.p.CONFIG["models"]["desk"]
    desk_text, _ = s.safe_call_ai(
        "integration_desk_smoke", desk_model, "Svar kun OK.", "ping",
        max_output_tokens=32, reasoning="low"
    )
    if not desk_text.strip():
        raise RuntimeError("Qwen Desk smoke returned empty text")

    vectors = s.safe_embed_texts(["Danmark ændrer migrationsregler", "Nye danske regler for migration"])
    if len(vectors) != 2 or not vectors[0]:
        raise RuntimeError("BGE-M3 smoke returned invalid embeddings")

    media_model = s.p.CONFIG["models"]["media_vision"]
    media_text, _ = s.safe_call_ai(
        "integration_media_smoke",
        media_model,
        "Se billedet og svar kun med ordet OK.",
        "Er der et synligt motiv?",
        max_output_tokens=32,
        images=["https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Fronalpstock_big.jpg/320px-Fronalpstock_big.jpg"],
        reasoning="low",
    )
    if not media_text.strip():
        raise RuntimeError("Gemma Media smoke returned empty text")

    generated = s.safe_generate_image(
        "Simple editorial illustration of a newspaper on a desk, no text, landscape composition.",
        "integration-smoke",
    )
    if not generated.get("image"):
        raise RuntimeError("FLUX.1 Schnell smoke returned no image")

    print("V3 chain smoke PASS: Qwen + BGE-M3 + Gemma vision + FLUX.1 Schnell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
