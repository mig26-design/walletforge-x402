"""Pure helpers an Open Autonomy behaviour can call (no AEA runtime required)."""

from __future__ import annotations

import json
from typing import Any, Optional

from walletforge_x402.buyer import X402Buyer, load_buyer_from_env


def fetch_markdown_via_buyer(
    url: str,
    *,
    max_chars: Optional[int] = None,
    buyer: X402Buyer | None = None,
) -> dict[str, Any]:
    b = buyer or load_buyer_from_env()
    resp = b.fetch_markdown(url, max_chars=max_chars)
    data = resp.data
    return data if isinstance(data, dict) else {"raw": data, "status_code": resp.status_code}


def normalize_via_buyer(
    text: str,
    *,
    buyer: X402Buyer | None = None,
) -> dict[str, Any]:
    b = buyer or load_buyer_from_env()
    resp = b.normalize(text)
    data = resp.data
    return data if isinstance(data, dict) else {"raw": data, "status_code": resp.status_code}


def result_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
