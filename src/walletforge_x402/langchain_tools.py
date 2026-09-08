"""LangChain StructuredTool wrappers around the WalletForge x402 buyer."""

from __future__ import annotations

import json
from typing import Any, Optional

from walletforge_x402.buyer import X402Buyer, load_buyer_from_env

try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Install walletforge-x402[langchain] to use LangChain tools"
    ) from exc


class FetchMarkdownInput(BaseModel):
    url: str = Field(..., description="Public http(s) URL to fetch as cleaned markdown")
    max_chars: Optional[int] = Field(
        default=None,
        ge=500,
        le=200_000,
        description="Optional markdown length cap (500..200000)",
    )


class NormalizeTextInput(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text to normalize and extract entities from")


def _buyer_or_default(buyer: X402Buyer | None) -> X402Buyer:
    return buyer if buyer is not None else load_buyer_from_env()


def fetch_markdown_tool(buyer: X402Buyer | None = None) -> StructuredTool:
    """LangChain tool: paid POST /v1/fetch-markdown (0.05 USDC)."""

    b = _buyer_or_default(buyer)

    def _run(url: str, max_chars: Optional[int] = None) -> str:
        resp = b.fetch_markdown(url, max_chars=max_chars)
        return json.dumps(resp.data, ensure_ascii=False)

    return StructuredTool.from_function(
        name="fetch_markdown",
        description=(
            "Fetch a public URL and return cleaned markdown via WalletForge x402 "
            "(Base mainnet USDC, ~0.05 USDC per call)."
        ),
        func=_run,
        args_schema=FetchMarkdownInput,
    )


def normalize_text_tool(buyer: X402Buyer | None = None) -> StructuredTool:
    """LangChain tool: paid POST /v1/normalize (0.01 USDC)."""

    b = _buyer_or_default(buyer)

    def _run(text: str) -> str:
        resp = b.normalize(text)
        return json.dumps(resp.data, ensure_ascii=False)

    return StructuredTool.from_function(
        name="normalize_text",
        description=(
            "Normalize text and extract emails, URLs, and phones via WalletForge x402 "
            "(Base mainnet USDC, ~0.01 USDC per call)."
        ),
        func=_run,
        args_schema=NormalizeTextInput,
    )


def walletforge_tools(buyer: X402Buyer | None = None) -> list[Any]:
    """Return both StructuredTools bound to the same buyer."""
    b = _buyer_or_default(buyer)
    return [fetch_markdown_tool(b), normalize_text_tool(b)]
