#!/usr/bin/env python3
"""Runtime entrypoint that keeps the private budget backend authenticated.

GitHub OIDC tokens are intentionally short lived. Worker deployment can take
several minutes, so the safe runner must be able to refresh its token instead
of either failing mid-run or replacing it with a long-lived secret.
"""
from __future__ import annotations

import argparse
import os

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    s.private_backend = refreshable_backend
    # Refresh once proactively; later calls transparently refresh again after 401.
    refresh_oidc()
    return s.smoke() if args.smoke else s.run_pipeline(args.cycles)


if __name__ == "__main__":
    raise SystemExit(main())
