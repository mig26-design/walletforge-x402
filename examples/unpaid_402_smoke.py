"""Unpaid live 402 smoke against api.walletforge.app (no spend)."""

from __future__ import annotations

import json
import sys

from walletforge_x402 import DEFAULT_BASE_URL, X402Buyer


def main() -> int:
    # Explicit production base so a leftover local X402_BASE_URL does not hijack smoke.
    base = DEFAULT_BASE_URL
    r = X402Buyer.unpaid_challenge(
        "/v1/normalize",
        {"text": "smoke"},
        base_url=base,
    )
    print(f"base={base} status={r.status_code}")
    if r.payment_required:
        print(
            json.dumps(
                {
                    "x402Version": r.payment_required.get("x402Version"),
                    "accepts": r.payment_required.get("accepts"),
                    "extension_keys": list(
                        (r.payment_required.get("extensions") or {}).keys()
                    ),
                },
                indent=2,
            )
        )
    return 0 if r.status_code == 402 else 1


if __name__ == "__main__":
    sys.exit(main())
