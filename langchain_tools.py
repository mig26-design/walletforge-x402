import os
import json
import base64
import time
import secrets
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data


def b64_encode(data: dict) -> str:
    return base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


class FetchMarkdownInput(BaseModel):
    url: str = Field(description="The public web URL to scrape and convert into cleaned markdown")


class NormalizeTextInput(BaseModel):
    text: str = Field(description="Unstructured text containing contacts, dates, or details to normalize")


class BaseWalletForgeTool(BaseTool):
    private_key: str

    def _execute_paid_call(self, endpoint_url: str, payload: dict) -> str:
        account = Account.from_key(self.private_key)
        with httpx.Client(timeout=30.0) as client:
            # 1. Unpaid request to get 402 challenge
            r = client.post(endpoint_url, json=payload)
            if r.status_code == 200:
                return json.dumps(r.json())
            if r.status_code != 402:
                return f"Error {r.status_code}: {r.text}"

            # 2. Extract payment requirement
            payment_header = r.headers.get("payment-required") or r.headers.get("x-payment-required")
            if not payment_header:
                return "Error: Missing payment-required header"

            challenge = json.loads(base64.b64decode(payment_header))
            accepts = challenge.get("accepts", [{}])[0]

            network = accepts.get("network")
            asset = accepts.get("asset")
            pay_to = accepts.get("payTo")
            amount = str(accepts.get("amount", "50000"))
            extra = accepts.get("extra", {})
            chain_id = int(network.split(":")[1]) if ":" in str(network) else 8453
            max_timeout = int(accepts.get("maxTimeoutSeconds", 60))

            # 3. EIP-712 / EIP-3009 message construction
            now = int(time.time())
            valid_after = 0
            valid_before = now + max_timeout
            nonce = "0x" + secrets.token_hex(32)

            typed_data = {
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
                    "name": extra.get("name", "USD Coin"),
                    "version": extra.get("version", "2"),
                    "chainId": chain_id,
                    "verifyingContract": asset,
                },
                "message": {
                    "from": account.address,
                    "to": pay_to,
                    "value": int(amount),
                    "validAfter": valid_after,
                    "validBefore": valid_before,
                    "nonce": nonce,
                },
            }

            signable_msg = encode_typed_data(full_message=typed_data)
            signed = account.sign_message(signable_msg)

            # 4. Form valid EIP-3009 payment payload
            payment_signature = {
                "x402Version": challenge.get("x402Version", 2),
                "accepted": accepts,
                "payload": {
                    "signature": "0x" + signed.signature.hex(),
                    "authorization": {
                        "from": account.address,
                        "to": pay_to,
                        "value": str(amount),
                        "validAfter": str(valid_after),
                        "validBefore": str(valid_before),
                        "nonce": nonce,
                    },
                },
            }

            # 5. Resubmit request with PAYMENT-SIGNATURE
            headers = {
                "Content-Type": "application/json",
                "PAYMENT-SIGNATURE": b64_encode(payment_signature),
            }
            res = client.post(endpoint_url, json=payload, headers=headers)
            return json.dumps(res.json())


class WalletForgeMarkdownTool(BaseWalletForgeTool):
    name: str = "walletforge_fetch_markdown"
    description: str = "Scrapes a live public webpage and converts the content into clean markdown. Costs 0.05 USDC settled on Base."
    args_schema: Type[BaseModel] = FetchMarkdownInput

    def _run(self, url: str) -> str:
        return self._execute_paid_call("https://api.walletforge.app/v1/fetch-markdown", {"url": url})


class WalletForgeNormalizeTool(BaseWalletForgeTool):
    name: str = "walletforge_normalize_text"
    description: str = "Parses unstructured text and extracts contacts, emails, and entities into JSON. Costs 0.01 USDC settled on Base."
    args_schema: Type[BaseModel] = NormalizeTextInput

    def _run(self, text: str) -> str:
        return self._execute_paid_call("https://api.walletforge.app/v1/normalize", {"text": text})
