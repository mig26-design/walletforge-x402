# Draft PR — Coinbase AgentKit community action provider catalog

> Paste into a PR against the AgentKit community / examples / action-providers catalog once the GitHub repo URL is final. Replace `mig26-design/walletforge-x402` and link the live package.

---

## Title

`feat: add WalletForge x402 fetch_markdown / normalize_text action provider`

## Summary

Adds a community **ActionProvider** for [WalletForge](https://api.walletforge.app), a non-custodial **x402 V2** paid API on **Base mainnet**. Agents pay **0.05 USDC** per URL→markdown scrape and **0.01 USDC** per text normalize/extract call via EIP-3009 + public facilitator — no seller API keys and no seller private key on the server.

## Motivation

- Autonomous agents need pay-per-call web utilities without shared API keys.
- x402 is the HTTP-native payment rail; WalletForge exposes production Base USDC endpoints already listed on PayAI Bazaar and x402scan.
- Packaging as an AgentKit action provider lets CDP AgentKit apps register tools with one provider factory.

## Tools / actions

| Action | Endpoint | Price |
|--------|----------|-------|
| `fetch_markdown` | `POST https://api.walletforge.app/v1/fetch-markdown` | 0.05 USDC |
| `normalize_text` | `POST https://api.walletforge.app/v1/normalize` | 0.01 USDC |

Full schemas: see `docs/TOOL_SPEC.md` in this package.

## Integration

```bash
pip install "git+https://github.com/mig26-design/walletforge-x402.git#egg=walletforge-x402[agentkit]"
export BUYER_PRIVATE_KEY=0x...   # EOA with Base USDC
```

```python
from walletforge_x402.agentkit_provider import walletforge_action_provider
from coinbase_agentkit import AgentKit, AgentKitConfig

agent_kit = AgentKit(
    AgentKitConfig(
        wallet_provider=wallet_provider,
        action_providers=[walletforge_action_provider()],
    )
)
```

Buyer implementation: `walletforge_x402.buyer.X402Buyer` (echoes x402 `extensions` for Bazaar compatibility).

## Reproduction steps (reviewers)

1. Health: `curl -sS https://api.walletforge.app/health`
2. Unpaid challenge:
   ```bash
   curl -sS -i -X POST https://api.walletforge.app/v1/fetch-markdown \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://example.com"}'
   ```
   Expect **402**, `accepts[0].amount == "50000"`, `payTo == 0xb5F5a86Df5F78ed78920f74a1D7f26368F708E94`.
3. Install package + set `BUYER_PRIVATE_KEY` with ~0.10 Base USDC.
4. Run:
   ```python
   from walletforge_x402 import X402Buyer
   out = X402Buyer(base_url="https://api.walletforge.app").fetch_markdown("https://example.com")
   print(out.status_code, out.payment_response)
   ```
5. Confirm settle tx on Basescan.

## Proof of live paid settle (Base)

| | |
|--|--|
| Date | 2026-09-08 |
| Amount | **0.05 USDC** (`50000`) |
| From | `0x3f6023854de3E58049A352D99D4B5Ec20A761136` |
| To | `0xb5F5a86Df5F78ed78920f74a1D7f26368F708E94` |
| Tx | [`0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc`](https://basescan.org/tx/0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc) |
| Client | `walletforge-x402` → `api.walletforge.app` |
| HTTP | 200, Example Domain markdown |

## Security / custody notes

- Server never holds a seller key; settlement via PayAI facilitator.
- SSRF protections on fetch-markdown (public URLs only).
- Reviewers should use a dedicated funded test EOA; never paste keys into the PR.

## Checklist

- [ ] Package published (GitHub and/or PyPI)
- [ ] Unpaid 402 verified by reviewer
- [ ] Optional paid settle verified
- [ ] Docs link to TOOL_SPEC + INTEGRATION
- [ ] No secrets in repo

## Links

- API: https://api.walletforge.app
- agent.json: https://api.walletforge.app/.well-known/agent.json
- Package: `https://github.com/mig26-design/walletforge-x402` (pending publish)
