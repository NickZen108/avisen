#!/usr/bin/env python3
"""Runtime entrypoint that keeps auth fresh and transport retries bounded.

GitHub OIDC tokens are intentionally short lived. Worker deployment can take
several minutes, so the safe runner refreshes its token. Fresh workers can also
briefly return Cloudflare's generic HTML 404 while the workers.dev route is
propagating; those transport failures are retried at most twice. Each attempt
still passes through the DB budget reservation and the normal run/story call
ceilings, so this retry cannot become a spending loop.
"""
from __future__ import annotations

import argparse
import os
import time

import requests

import v3_safe_runner as s
import v3_language_editor


def refresh_oidc() -> str:
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL") or ""
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN") or ""
    if not url or not request_token:
        raise s.SafetyLimitExceeded("GitHub OIDC refresh endpoint unavailable")
    sep = "&" if "?" in url else "?"
    r = requests.get(
        f"{url}{sep}audience=morgentidende-v3",
        headers={"Authorization": f"bearer {request_token}"},
        timeout=20,
    )
    r.raise_for_status()
    token = str((r.json() or {}).get("value") or "")
    if not token:
        raise s.SafetyLimitExceeded("GitHub OIDC refresh returned no token")
    os.environ["GITHUB_OIDC_TOKEN"] = token
    s.p.OIDC_TOKEN = token
    return token


def refreshable_backend(action: str, **kwargs):
    if not s.p.BACKEND_URL:
        raise s.SafetyLimitExceeded("Private budget backend unavailable; AI calls fail closed")
    token = s.p.OIDC_TOKEN or os.environ.get("GITHUB_OIDC_TOKEN") or ""
    for attempt in range(2):
        if not token:
            token = refresh_oidc()
        r = requests.post(
            s.p.BACKEND_URL,
            headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
            json={"action": action, **kwargs},
            timeout=20,
        )
        data = {}
        try:
            data = r.json()
        except Exception:
            pass
        if r.status_code == 401 and attempt == 0:
            token = refresh_oidc()
            continue
        if r.status_code == 429:
            return {"ok": False, "status": 429, **(data or {})}
        if not r.ok:
            raise s.SafetyLimitExceeded(
                f"Private backend {action} failed HTTP {r.status_code}: {str(data)[:250]}"
            )
        return data
    raise s.SafetyLimitExceeded(f"Private backend {action} authorization failed after OIDC refresh")


BASE_SAFE_CALL = s.safe_call_ai


def route_resilient_safe_call(*args, **kwargs):
    """Retry only the known zero-inference workers.dev propagation failure.

    The underlying safe call reserves/settles budget for every attempt. There
    are at most three attempts total, and all other errors stop immediately.
    """
    last = None
    for attempt in range(3):
        try:
            return BASE_SAFE_CALL(*args, **kwargs)
        except RuntimeError as exc:
            msg = str(exc)
            transient_route_404 = (
                "HTTP 404" in msg
                and ("Page not found" in msg or "workers.cloudflare" in msg or "workers.dev" in msg)
            )
            if not transient_route_404 or attempt >= 2:
                raise
            last = exc
            time.sleep(3 * (attempt + 1))
    raise last or RuntimeError("bounded route retry failed")


def terra_smoke() -> int:
    """Exercise the critical OpenAI/Cloudflare path and budget guard.

    Success means the configured Terra editor model returned any non-empty text;
    exact wording is deliberately not asserted because wording is not the
    transport contract being tested.
    """
    model = s.p.CONFIG["models"]["language_editor"]
    text, _ = s.safe_call_ai(
        "integration_smoke",
        model,
        "Svar meget kort på dansk.",
        "Skriv ét dansk ord.",
        max_output_tokens=32,
        reasoning="none",
    )
    if not str(text or "").strip():
        raise RuntimeError("Terra smoke returned empty text")
    print(f"V3 Terra smoke PASS: {str(text).strip()[:80]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    s.private_backend = refreshable_backend
    s.safe_call_ai = route_resilient_safe_call
    v3_language_editor.install(s.p)
    # Refresh once proactively; later calls transparently refresh again after 401.
    refresh_oidc()
    return terra_smoke() if args.smoke else s.run_pipeline(args.cycles)


if __name__ == "__main__":
    raise SystemExit(main())
