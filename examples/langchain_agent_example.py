"""Minimal LangChain tool wiring (does not spend unless you invoke tools)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    from walletforge_x402 import DEFAULT_BASE_URL, X402Buyer

    challenge = X402Buyer.unpaid_challenge(
        "/v1/fetch-markdown",
        {"url": "https://example.com"},
        base_url=DEFAULT_BASE_URL,
    )
    print(f"unpaid fetch-markdown status={challenge.status_code}")
    if challenge.payment_required:
        accepts = challenge.payment_required.get("accepts") or []
        if accepts:
            print(
                f"amount={accepts[0].get('amount')} network={accepts[0].get('network')} "
                f"extensions={list((challenge.payment_required.get('extensions') or {}).keys())}"
            )

    if not os.getenv("BUYER_PRIVATE_KEY"):
        print("Set BUYER_PRIVATE_KEY to bind paid LangChain tools (will spend real Base USDC).")
        return 0

    from walletforge_x402.langchain_tools import walletforge_tools

    tools = walletforge_tools()
    print("tools:", [t.name for t in tools])
    return 0


if __name__ == "__main__":
    sys.exit(main())
