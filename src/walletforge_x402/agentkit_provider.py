"""Coinbase AgentKit ActionProvider adapter for WalletForge x402 tools.

Uses coinbase_agentkit when installed (extra [agentkit]). If the package is
absent, exposes a lightweight compatible stub so examples/docs stay importable.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from walletforge_x402.buyer import X402Buyer, load_buyer_from_env

try:
    from coinbase_agentkit import ActionProvider, Network, create_action

    _HAS_AGENTKIT = True
except ImportError:  # pragma: no cover
    _HAS_AGENTKIT = False

    class Network:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    def create_action(**_decorator_kwargs: Any):  # type: ignore[misc]
        def deco(fn):
            return fn

        return deco

    class ActionProvider:  # type: ignore[no-redef]
        def __init__(self, name: str, action_providers: list | None = None) -> None:
            self.name = name
            self.action_providers = action_providers or []


class FetchMarkdownSchema(BaseModel):
    url: str = Field(..., description="Public URL to fetch as markdown")
    max_chars: Optional[int] = Field(
        default=None,
        description="Optional max markdown characters (500..200000)",
    )


class NormalizeTextSchema(BaseModel):
    text: str = Field(..., description="Text to normalize / extract entities from")


class WalletForgeX402Provider(ActionProvider):
    """AgentKit action provider wrapping X402Buyer."""

    def __init__(self, buyer: X402Buyer | None = None) -> None:
        super().__init__("walletforge-x402", [])
        self._buyer = buyer

    def _get_buyer(self) -> X402Buyer:
        if self._buyer is None:
            self._buyer = load_buyer_from_env()
        return self._buyer

    @create_action(
        name="fetch_markdown",
        description=(
            "Fetch a public URL as cleaned markdown via WalletForge x402 V2 "
            "(Base eip155:8453 USDC, 0.05 USDC)."
        ),
        schema=FetchMarkdownSchema,
    )
    def fetch_markdown(self, args: dict[str, Any]) -> str:
        url = args["url"]
        max_chars = args.get("max_chars")
        resp = self._get_buyer().fetch_markdown(url, max_chars=max_chars)
        return json.dumps(resp.data, ensure_ascii=False)

    @create_action(
        name="normalize_text",
        description=(
            "Normalize text and extract emails/URLs/phones via WalletForge x402 V2 "
            "(0.01 USDC)."
        ),
        schema=NormalizeTextSchema,
    )
    def normalize_text(self, args: dict[str, Any]) -> str:
        resp = self._get_buyer().normalize(args["text"])
        return json.dumps(resp.data, ensure_ascii=False)

    def supports_network(self, network: Network) -> bool:
        # WalletForge settles on Base mainnet; allow broadly so agents can call
        # regardless of CDP wallet network selection.
        protocol = getattr(network, "protocol_family", None) or getattr(
            network, "network_id", ""
        )
        if protocol in (None, "", "evm", "eip155:8453", "base-mainnet", "base"):
            return True
        net_id = str(getattr(network, "network_id", "") or "")
        chain = str(getattr(network, "chain_id", "") or "")
        return "8453" in net_id or chain in ("8453", "base-mainnet") or True


def walletforge_x402_provider(buyer: X402Buyer | None = None) -> WalletForgeX402Provider:
    """Factory matching AgentKit `*_action_provider()` naming."""
    return WalletForgeX402Provider(buyer=buyer)


# Alias used in README / examples
walletforge_action_provider = walletforge_x402_provider
