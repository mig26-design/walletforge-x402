"""Mocked x402 V2 buyer tests — no live paid settle."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
from eth_account import Account

from walletforge_x402.buyer import (
    AMOUNT_FETCH_MARKDOWN,
    AMOUNT_NORMALIZE,
    DEFAULT_ASSET,
    DEFAULT_NETWORK,
    DEFAULT_PAY_TO,
    X402Buyer,
    b64d,
    b64e,
    build_payment_payload,
    echo_extensions,
)


def _b64(obj: Any) -> str:
    return base64.b64encode(
        json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    ).decode()


def _payment_required(
    *,
    amount: str = AMOUNT_NORMALIZE,
    with_bazaar: bool = True,
    resource_url: str = "https://api.walletforge.app/v1/normalize",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "x402Version": 2,
        "error": "PAYMENT-SIGNATURE header is required",
        "resource": {
            "url": resource_url,
            "description": "Normalize text",
            "mimeType": "application/json",
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": DEFAULT_NETWORK,
                "amount": amount,
                "asset": DEFAULT_ASSET,
                "payTo": DEFAULT_PAY_TO,
                "maxTimeoutSeconds": 60,
                "extra": {"name": "USD Coin", "version": "2"},
            }
        ],
        "extensions": {},
    }
    if with_bazaar:
        body["extensions"] = {
            "bazaar": {
                "info": {
                    "serviceName": "WalletForge",
                    "tags": ["web-scraping", "markdown"],
                    "input": {"method": "POST", "type": "json"},
                    "output": {"example": {"normalized": "..."}},
                },
                "schema": {"type": "object"},
            }
        }
    return body


@pytest.fixture
def ephemeral_key() -> str:
    # Deterministic-enough for tests: fresh each session, never printed
    return "0x" + "11" * 32


@pytest.fixture
def buyer(ephemeral_key: str) -> X402Buyer:
    return X402Buyer(private_key=ephemeral_key, base_url="https://api.walletforge.app")


def test_echo_extensions_preserves_server_and_adds_client_only():
    required = {
        "bazaar": {"info": {"serviceName": "WalletForge", "tags": ["a"]}},
        "other": {"info": {"x": 1}},
    }
    out = echo_extensions(
        required,
        client_extras={
            "bazaar": {"info": {"serviceName": "HACKED", "clientNote": "ok"}},
            "clientOnly": {"info": {"y": 2}},
        },
    )
    # Must not overwrite serviceName
    assert out["bazaar"]["info"]["serviceName"] == "WalletForge"
    # May append new keys under info
    assert out["bazaar"]["info"]["clientNote"] == "ok"
    assert out["clientOnly"]["info"]["y"] == 2
    assert out["other"]["info"]["x"] == 1
    # Deep copy — mutating out must not touch required
    out["bazaar"]["info"]["tags"].append("mut")
    assert required["bazaar"]["info"]["tags"] == ["a"]


def test_build_payment_payload_echoes_extensions_and_resource(ephemeral_key: str):
    account = Account.from_key(ephemeral_key)
    required = _payment_required()
    payload = build_payment_payload(required, account=account, now=1_700_000_000)

    assert payload["x402Version"] == 2
    assert payload["resource"] == required["resource"]
    assert payload["extensions"] == required["extensions"]
    assert "bazaar" in payload["extensions"]
    assert payload["accepted"]["amount"] == AMOUNT_NORMALIZE
    assert payload["accepted"]["extra"]["name"] == "USD Coin"
    assert payload["accepted"]["payTo"] == DEFAULT_PAY_TO
    assert payload["payload"]["signature"].startswith("0x")
    assert payload["payload"]["authorization"]["from"] == account.address
    assert len(payload["payload"]["authorization"]["nonce"]) == 66  # 0x + 64 hex


def test_b64_roundtrip():
    obj = {"a": 1, "b": "ü"}
    assert b64d(b64e(obj)) == obj


def test_pay_post_402_then_200_mock(buyer: X402Buyer):
    required = _payment_required()
    success_body = {
        "normalized": "hello",
        "emails": [],
        "urls": [],
        "phones": [],
        "stats": {"chars": 5, "emails": 0, "urls": 0, "phones": 0},
    }
    settlement = {"success": True, "transaction": "0xabc"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("PAYMENT-SIGNATURE") or request.headers.get(
            "payment-signature"
        ):
            # Verify extension echo in signature payload
            sig_hdr = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get(
                "payment-signature"
            )
            decoded = b64d(sig_hdr)
            assert decoded["extensions"]["bazaar"]["info"]["serviceName"] == "WalletForge"
            assert decoded["resource"]["url"].endswith("/v1/normalize")
            assert decoded["accepted"]["asset"].lower() == DEFAULT_ASSET.lower()
            return httpx.Response(
                200,
                json=success_body,
                headers={"PAYMENT-RESPONSE": _b64(settlement)},
            )
        return httpx.Response(
            402,
            json=required,
            headers={"PAYMENT-REQUIRED": _b64(required)},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://api.walletforge.app") as client:
        # Patch buyer to use mock via shared client: call pay_post with client
        # Our buyer builds absolute URLs; MockTransport matches any host.
        resp = buyer.pay_post("/v1/normalize", {"text": "hello"}, client=client)

    assert resp.status_code == 200
    assert resp.data["normalized"] == "hello"
    assert resp.payment_response == settlement
    assert resp.payment_required is not None
    assert "bazaar" in resp.payment_required["extensions"]


def test_fetch_markdown_mock(buyer: X402Buyer):
    required = _payment_required(
        amount=AMOUNT_FETCH_MARKDOWN,
        resource_url="https://api.walletforge.app/v1/fetch-markdown",
    )
    md_body = {"url": "https://example.com", "markdown": "# Hi", "chars": 4}

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/v1/fetch-markdown")
        body = json.loads(request.content.decode())
        assert body["url"] == "https://example.com"
        assert body.get("max_chars") == 2000
        if request.headers.get("PAYMENT-SIGNATURE"):
            decoded = b64d(request.headers["PAYMENT-SIGNATURE"])
            assert decoded["accepted"]["amount"] == AMOUNT_FETCH_MARKDOWN
            assert decoded["extensions"]["bazaar"]["info"]["serviceName"] == "WalletForge"
            return httpx.Response(200, json=md_body)
        return httpx.Response(
            402, json=required, headers={"PAYMENT-REQUIRED": _b64(required)}
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        resp = buyer.fetch_markdown("https://example.com", max_chars=2000, client=client)

    assert resp.status_code == 200
    assert resp.data["markdown"] == "# Hi"


def test_buyer_drops_private_key_from_instance(ephemeral_key: str):
    b = X402Buyer(private_key=ephemeral_key)
    assert b.private_key is None
    assert b.address.startswith("0x")
    # repr must not contain key material
    assert ephemeral_key not in repr(b)
    assert ephemeral_key[2:] not in repr(b)


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BUYER_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("X402_BUYER_PRIVATE_KEY", raising=False)
    with pytest.raises(Exception):
        X402Buyer(private_key=None)


def test_settlement_error_on_paid_failure(buyer: X402Buyer):
    required = _payment_required()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("PAYMENT-SIGNATURE"):
            return httpx.Response(402, json={"error": "still required"})
        return httpx.Response(
            402, json=required, headers={"PAYMENT-REQUIRED": _b64(required)}
        )

    from walletforge_x402.buyer import SettlementError

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(SettlementError):
            buyer.pay_post("/v1/normalize", {"text": "x"}, client=client)


def test_constants():
    assert AMOUNT_NORMALIZE == "10000"
    assert AMOUNT_FETCH_MARKDOWN == "50000"
    assert DEFAULT_NETWORK == "eip155:8453"
