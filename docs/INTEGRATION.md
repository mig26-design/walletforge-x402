# Integration documentation — WalletForge x402

## Prerequisites

- Python 3.10+
- Buyer EOA with **Base USDC** (and optional ETH; settlement is facilitator-sponsored)
- Package: `walletforge-x402` (GitHub / local tarball until PyPI publish)

```bash
pip install -e ".[langchain]"   # or .[agentkit]
export BUYER_PRIVATE_KEY=0x...  # never commit
unset X402_BASE_URL             # use default https://api.walletforge.app
```

## Unpaid smoke (no spend)

```bash
python - <<'PY'
from walletforge_x402 import X402Buyer
r = X402Buyer.unpaid_challenge(
    "/v1/fetch-markdown",
    {"url": "https://example.com"},
    base_url="https://api.walletforge.app",
)
assert r.status_code == 402
assert r.payment_required["accepts"][0]["amount"] == "50000"
print("ok", r.payment_required["accepts"][0]["payTo"])
PY
```

## Paid self-test (spends 0.05 USDC)

```python
from walletforge_x402 import X402Buyer

buyer = X402Buyer(base_url="https://api.walletforge.app")
out = buyer.fetch_markdown("https://example.com", max_chars=5000)
assert out.status_code == 200
print(out.data["title"])
print(out.payment_response["transaction"])
```

### Proven live settle (reference)

| Field | Value |
|-------|-------|
| Date (UTC) | 2026-09-08 |
| Endpoint | `https://api.walletforge.app/v1/fetch-markdown` |
| Amount | 50000 (0.05 USDC) |
| Payer | `0x3f6023854de3E58049A352D99D4B5Ec20A761136` |
| payTo | `0xb5F5a86Df5F78ed78920f74a1D7f26368F708E94` |
| Settle tx | `0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc` |
| Network | Base `eip155:8453` |
| Result | HTTP 200, markdown for `https://example.com/` |

Basescan: https://basescan.org/tx/0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc

## LangChain

```python
from walletforge_x402.langchain_tools import walletforge_tools

tools = walletforge_tools()  # fetch_markdown, normalize_text
# bind to your agent / create_react_agent / etc.
```

## Coinbase AgentKit

```python
from walletforge_x402.agentkit_provider import walletforge_action_provider
# from coinbase_agentkit import AgentKit, AgentKitConfig
# AgentKit(AgentKitConfig(wallet_provider=wp, action_providers=[walletforge_action_provider()]))
```

## Reproduction checklist for reviewers

1. `curl -sS https://api.walletforge.app/health`
2. Unpaid `POST /v1/fetch-markdown` → 402 amount `50000`
3. `pip install` package + set `BUYER_PRIVATE_KEY`
4. `buyer.fetch_markdown("https://example.com")` → 200 + `PAYMENT-RESPONSE.transaction`
5. Confirm tx on Basescan and USDC transfer to `payTo`
