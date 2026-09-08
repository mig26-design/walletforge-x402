"""WalletForge x402 V2 buyer: 402 → EIP-3009 sign → retry with PAYMENT-SIGNATURE.

Improvements over the reference client:
- Deep-copy and echo *all* PaymentRequired.extensions into PAYMENT-SIGNATURE
  (spec: client must include at least the info received; may append, never
  delete/overwrite).
- Preserve accepted.extra verbatim (token EIP-712 name/version, ATM hints).
- Echo full resource object, not a truncated dict.
- Never log or print private keys.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data

DEFAULT_BASE_URL = "https://api.walletforge.app"
DEFAULT_NETWORK = "eip155:8453"
DEFAULT_ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DEFAULT_PAY_TO = "0xb5F5a86Df5F78ed78920f74a1D7f26368F708E94"
DEFAULT_FACILITATOR = "https://facilitator.payai.network"

# Atomic USDC amounts (6 decimals)
AMOUNT_NORMALIZE = "10000"  # 0.01 USDC
AMOUNT_FETCH_MARKDOWN = "50000"  # 0.05 USDC


class X402Error(Exception):
    """Base error for x402 buyer failures."""


class PaymentRequiredError(X402Error):
    """Server returned 402 but PAYMENT-REQUIRED could not be used."""


class SettlementError(X402Error):
    """Paid retry did not succeed."""


def b64e(obj: Any) -> str:
    return base64.b64encode(
        json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    ).decode()


def b64d(value: str) -> dict[str, Any]:
    pad = "=" * (-len(value) % 4)
    return json.loads(base64.b64decode(value + pad))


def chain_id(network: str) -> int:
    if ":" not in network:
        raise ValueError(f"bad network: {network}")
    ns, ref = network.split(":", 1)
    if ns != "eip155":
        raise ValueError(f"unsupported network namespace: {ns}")
    return int(ref)


def echo_extensions(
    required_extensions: Mapping[str, Any] | None,
    *,
    client_extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Echo server extensions into PaymentPayload.extensions.

    Spec rule: include at least the info received; may append additional
    keys/info but must not delete or overwrite existing extension info.
    """
    out: dict[str, Any] = copy.deepcopy(dict(required_extensions or {}))
    if not client_extras:
        return out
    for ext_id, extra_val in client_extras.items():
        if ext_id not in out:
            out[ext_id] = copy.deepcopy(extra_val)
            continue
        # Merge only additive keys under the extension object
        existing = out[ext_id]
        if isinstance(existing, dict) and isinstance(extra_val, Mapping):
            for k, v in extra_val.items():
                if k not in existing:
                    existing[k] = copy.deepcopy(v)
                elif (
                    isinstance(existing[k], dict)
                    and isinstance(v, Mapping)
                ):
                    for sk, sv in v.items():
                        if sk not in existing[k]:
                            existing[k][sk] = copy.deepcopy(sv)
        # else: keep server value (never overwrite)
    return out


def sign_eip3009(
    account: Account,
    *,
    asset: str,
    token_name: str,
    token_version: str,
    network: str,
    to: str,
    value: str,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
) -> tuple[str, dict[str, str]]:
    authorization = {
        "from": account.address,
        "to": to,
        "value": int(value),
        "validAfter": valid_after,
        "validBefore": valid_before,
        "nonce": nonce,
    }
    full_message = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": token_name,
            "version": token_version,
            "chainId": chain_id(network),
            "verifyingContract": asset,
        },
        "message": authorization,
    }
    signable = encode_typed_data(full_message=full_message)
    signed = account.sign_message(signable)
    auth_out = {
        "from": account.address,
        "to": to,
        "value": str(value),
        "validAfter": str(valid_after),
        "validBefore": str(valid_before),
        "nonce": "0x" + nonce.hex(),
    }
    return "0x" + signed.signature.hex(), auth_out


def build_payment_payload(
    required: Mapping[str, Any],
    *,
    account: Account,
    accept_index: int = 0,
    client_extension_extras: Mapping[str, Any] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    """Build a V2 PaymentPayload from a decoded PAYMENT-REQUIRED object."""
    accepts = required.get("accepts") or []
    if not accepts:
        raise PaymentRequiredError("PAYMENT-REQUIRED has empty accepts[]")
    if accept_index >= len(accepts):
        raise PaymentRequiredError(f"accept_index {accept_index} out of range")

    accepted = copy.deepcopy(accepts[accept_index])
    extra = dict(accepted.get("extra") or {})
    token_name = extra.get("name") or "USD Coin"
    token_version = str(extra.get("version") or "2")
    # Keep full extra (name/version + any assetTransferMethod) on accepted
    accepted["extra"] = extra

    ts = int(time.time() if now is None else now)
    valid_after = 0
    valid_before = ts + int(accepted.get("maxTimeoutSeconds") or 60)
    nonce = secrets.token_bytes(32)

    signature, authorization = sign_eip3009(
        account,
        asset=accepted["asset"],
        token_name=token_name,
        token_version=token_version,
        network=accepted["network"],
        to=accepted["payTo"],
        value=str(accepted["amount"]),
        valid_after=valid_after,
        valid_before=valid_before,
        nonce=nonce,
    )

    resource = required.get("resource")
    # Echo resource as-is (object or omit); never invent fields
    payload: dict[str, Any] = {
        "x402Version": int(required.get("x402Version") or 2),
        "accepted": {
            "scheme": accepted["scheme"],
            "network": accepted["network"],
            "amount": str(accepted["amount"]),
            "asset": accepted["asset"],
            "payTo": accepted["payTo"],
            "maxTimeoutSeconds": accepted.get("maxTimeoutSeconds", 60),
            "extra": accepted["extra"],
        },
        "payload": {"signature": signature, "authorization": authorization},
        "extensions": echo_extensions(
            required.get("extensions"),
            client_extras=client_extension_extras,
        ),
    }
    if resource is not None:
        payload["resource"] = copy.deepcopy(resource)
    return payload


def _header_get(headers: Mapping[str, str], name: str) -> str | None:
    lower = name.lower()
    for k, v in headers.items():
        if k.lower() == lower:
            return v
    return None


@dataclass
class PaidResponse:
    status_code: int
    data: Any
    headers: dict[str, str]
    payment_response: dict[str, Any] | None = None
    payment_required: dict[str, Any] | None = None


@dataclass
class X402Buyer:
    """Non-custodial x402 V2 buyer for WalletForge endpoints."""

    private_key: str | None = None
    base_url: str = field(default_factory=lambda: os.getenv("X402_BASE_URL", DEFAULT_BASE_URL).rstrip("/"))
    timeout: float = 60.0
    client_extension_extras: dict[str, Any] = field(default_factory=dict)
    _account: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        key = self.private_key or os.getenv("BUYER_PRIVATE_KEY") or os.getenv("X402_BUYER_PRIVATE_KEY")
        if not key:
            raise X402Error(
                "BUYER_PRIVATE_KEY (or X402_BUYER_PRIVATE_KEY) is required for paid calls"
            )
        if not key.startswith("0x"):
            key = "0x" + key
        # Never store or print the raw key beyond Account.from_key
        self._account = Account.from_key(key)
        self.private_key = None  # drop reference; never print

    @property
    def address(self) -> str:
        return self._account.address

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        payment_signature: str | None = None,
        client: httpx.Client | None = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "walletforge-x402/0.1",
        }
        if payment_signature:
            headers["PAYMENT-SIGNATURE"] = payment_signature

        owns = client is None
        http = client or httpx.Client(timeout=self.timeout)
        try:
            return http.post(url, json=body, headers=headers)
        finally:
            if owns:
                http.close()

    def pay_post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        client: httpx.Client | None = None,
        accept_index: int = 0,
    ) -> PaidResponse:
        """POST unpaid; on 402 sign EIP-3009 and retry with PAYMENT-SIGNATURE."""
        owns = client is None
        http = client or httpx.Client(timeout=self.timeout)
        try:
            r1 = self._post(path, body, client=http)
            if r1.status_code != 402:
                data: Any
                try:
                    data = r1.json()
                except Exception:
                    data = r1.text
                return PaidResponse(
                    status_code=r1.status_code,
                    data=data,
                    headers=dict(r1.headers),
                )

            hdr = _header_get(r1.headers, "PAYMENT-REQUIRED")
            if not hdr:
                raise PaymentRequiredError("402 without PAYMENT-REQUIRED header")
            required = b64d(hdr)
            # Prefer header envelope; fall back to JSON body if header decode fails shape
            if not required.get("accepts") and isinstance(r1.json() if r1.content else None, dict):
                try:
                    body_req = r1.json()
                    if body_req.get("accepts"):
                        required = body_req
                except Exception:
                    pass

            payment_payload = build_payment_payload(
                required,
                account=self._account,
                accept_index=accept_index,
                client_extension_extras=self.client_extension_extras or None,
            )
            payment_sig = b64e(payment_payload)

            r2 = self._post(path, body, payment_signature=payment_sig, client=http)
            try:
                data2 = r2.json()
            except Exception:
                data2 = r2.text

            resp_hdr = _header_get(r2.headers, "PAYMENT-RESPONSE")
            payment_response = b64d(resp_hdr) if resp_hdr else None

            if r2.status_code >= 400:
                raise SettlementError(
                    f"paid request failed status={r2.status_code} body={data2!r}"
                )

            return PaidResponse(
                status_code=r2.status_code,
                data=data2,
                headers=dict(r2.headers),
                payment_response=payment_response,
                payment_required=required,
            )
        finally:
            if owns:
                http.close()

    def fetch_markdown(
        self,
        url: str,
        *,
        max_chars: int | None = None,
        client: httpx.Client | None = None,
    ) -> PaidResponse:
        body: dict[str, Any] = {"url": url}
        if max_chars is not None:
            body["max_chars"] = max_chars
        return self.pay_post("/v1/fetch-markdown", body, client=client)

    def normalize(
        self,
        text: str,
        *,
        client: httpx.Client | None = None,
    ) -> PaidResponse:
        return self.pay_post("/v1/normalize", {"text": text}, client=client)

    @staticmethod
    def unpaid_challenge(
        path: str = "/v1/normalize",
        body: dict[str, Any] | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> PaidResponse:
        """Smoke an unpaid POST (expects 402). No private key needed."""
        base = (base_url or os.getenv("X402_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        url = f"{base}{path}"
        payload = body if body is not None else {"text": "smoke"}
        with httpx.Client(timeout=timeout) as http:
            r = http.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "walletforge-x402/0.1",
                },
            )
        hdr = _header_get(r.headers, "PAYMENT-REQUIRED")
        required = b64d(hdr) if hdr else None
        try:
            data = r.json()
        except Exception:
            data = r.text
        return PaidResponse(
            status_code=r.status_code,
            data=data,
            headers=dict(r.headers),
            payment_required=required,
        )


def load_buyer_from_env(**kwargs: Any) -> X402Buyer:
    return X402Buyer(**kwargs)
