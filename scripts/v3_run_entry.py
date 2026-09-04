#!/usr/bin/env python3
"""Runtime entrypoint with fresh GitHub OIDC auth and bounded transport retry."""
from __future__ import annotations

import argparse
import os
import time

import requests

import v3_safe_runner as s


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
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code == 401 and attempt == 0:
            token = refresh_oidc()
            continue
        if r.status_code == 429:
            return {"ok": False, "status": 429, **data}
        if not r.ok:
            raise s.SafetyLimitExceeded(
                f"Private backend {action} failed HTTP {r.status_code}: {str(data)[:250]}"
            )
        return data
    raise s.SafetyLimitExceeded(f"Private backend {action} authorization failed after OIDC refresh")


BASE_SAFE_CALL = s.safe_call_ai


def route_resilient_safe_call(*args, **kwargs):
    """Retry only the known zero-inference workers.dev propagation 404."""
    last = None
    for attempt in range(3):
        try:
            return BASE_SAFE_CALL(*args, **kwargs)
        except RuntimeError as exc:
            msg = str(exc)
            transient = "HTTP 404" in msg and ("Page not found" in msg or "workers.cloudflare" in msg or "workers.dev" in msg)
            if not transient or attempt >= 2:
                raise
            last = exc
            time.sleep(3 * (attempt + 1))
    raise last or RuntimeError("bounded route retry failed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    s.private_backend = refreshable_backend
    s.safe_call_ai = route_resilient_safe_call
    refresh_oidc()
    return s.smoke() if args.smoke else s.run_pipeline(args.cycles)


if __name__ == "__main__":
    raise SystemExit(main())
