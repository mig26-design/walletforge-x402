"""Open Autonomy / Open AEA style behaviour stub.

Copy this module into a scaffolded skill package and adjust imports to the
skill package path. It intentionally avoids importing `aea` at module import
time so unit tests and pip installs without Open Autonomy still succeed.
"""

from __future__ import annotations

from typing import Any, Optional


class FetchMarkdownBehaviour:
    """Periodic fetch-markdown via walletforge_x402 buyer.

    When used inside Open AEA, subclass `aea.skills.behaviours.TickerBehaviour`
    instead and call `act()` from the framework tick.
    """

    def __init__(
        self,
        target_url: str = "https://example.com",
        max_chars: Optional[int] = 50_000,
        tick_interval: float = 30.0,
        **kwargs: Any,
    ) -> None:
        self.target_url = target_url
        self.max_chars = max_chars
        self.tick_interval = tick_interval
        self.kwargs = kwargs
        self.last_result: dict[str, Any] | None = None

    def act(self) -> dict[str, Any]:
        from walletforge_x402.autonolas.tool import fetch_markdown_via_buyer

        self.last_result = fetch_markdown_via_buyer(
            self.target_url, max_chars=self.max_chars
        )
        return self.last_result


class WalletForgeParams:
    """Skill model stub for base URL / knobs (key stays in env)."""

    def __init__(self, base_url: str = "https://api.walletforge.app", **kwargs: Any) -> None:
        self.base_url = base_url.rstrip("/")
        self.kwargs = kwargs
