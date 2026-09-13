# Draft PR — LangChain Community Tools registry

> Paste into a contribution PR / issue for LangChain community tools (or `langchain-community` toolkit listing). Replace `mig26-design/walletforge-x402` after GitHub publish.

---

## Title

`feat(community): WalletForge x402 paid fetch_markdown and normalize_text tools`

## Summary

Registers LangChain `StructuredTool`s for WalletForge’s production **x402 V2** API on Base. Tools perform pay-per-call HTTP: agents settle **USDC** via EIP-3009; no shared API key.

## Tools

### `fetch_markdown`

- **Description:** Fetch a public URL and return cleaned markdown (SSRF-safe). Costs 0.05 USDC on Base via x402.
- **Args:** `url: str`, `max_chars: int = 50000`
- **Returns:** JSON string / dict with `markdown`, `title`, `url`, `stats`
- **Upstream:** `POST https://api.walletforge.app/v1/fetch-markdown`

### `normalize_text`

- **Description:** Normalize text and extract emails, URLs, phones. Costs 0.01 USDC on Base via x402.
- **Args:** `text: str`
- **Returns:** `normalized`, `emails`, `urls`, `phones`, `stats`
- **Upstream:** `POST https://api.walletforge.app/v1/normalize`

See `docs/TOOL_SPEC.md`.

## Install

```bash
pip install "git+https://github.com/mig26-design/walletforge-x402.git#egg=walletforge-x402[langchain]"
export BUYER_PRIVATE_KEY=0x...
```

```python
from walletforge_x402.langchain_tools import walletforge_tools

tools = walletforge_tools()
# pass to create_agent / bind_tools / AgentExecutor
```

## Reproduction steps

1. `curl -sS https://api.walletforge.app/health` → `endpoints` includes `/v1/fetch-markdown`.
2. Unpaid:
   ```bash
   curl -sS -X POST https://api.walletforge.app/v1/fetch-markdown \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://example.com"}' | head
   ```
   Expect 402 / amount `50000`.
3. `python examples/unpaid_402_smoke.py` from the package.
4. Paid (optional, real USDC):
   ```python
   from walletforge_x402.langchain_tools import fetch_markdown_tool
   print(fetch_markdown_tool().invoke({"url": "https://example.com", "max_chars": 5000}))
   ```

## Proof of live paid settle

- Tx: [`0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc`](https://basescan.org/tx/0x5cebbe810ca7208bc85ab0231c59c03dfee967ad3de30f72ee4a753795677afc)
- 0.05 USDC Base → `0x405b88f183cb9fbb14e20b08a167917aa66e201c`
- Payer: `0x3f6023854de3E58049A352D99D4B5Ec20A761136`
- Client package self-test 2026-09-08 against `https://api.walletforge.app`

## Why community listing

Gives LangChain agent builders a default paid scrape/normalize tool that settles on-chain per call, complementary to free HTTP tools that lack metering or require centralized API keys.

## Checklist

- [ ] Public GitHub (and ideally PyPI) available
- [ ] README + TOOL_SPEC linked
- [ ] Tests: `pytest` mocked 402→200 in package
- [ ] No API keys required beyond buyer wallet for x402
