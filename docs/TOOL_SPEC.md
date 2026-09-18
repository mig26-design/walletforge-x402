# WalletForge x402 — Tool Spec

## Service

| | |
|--|--|
| Public base URL | `https://api.walletforge.app` |
| Protocol | x402 V2 (`exact`) |
| Network | Base mainnet `eip155:8453` |
| Asset | Base USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Recipient (`payTo`) | `0x405b88f183cb9fbb14e20b08a167917aa66e201c` |

Discovery:
- https://api.walletforge.app/llms.txt
- https://api.walletforge.app/.well-known/agent.json
- https://api.walletforge.app/.well-known/x402.json
- https://api.walletforge.app/health
- https://api.walletforge.app/openapi.json

## Actions

| Action | HTTP | Price |
|--------|------|-------|
| `normalize_text` | `POST /v1/normalize` | **1000** (0.001 USDC) |
| `fetch_markdown` | `POST /v1/fetch-markdown` | **3000** (0.003 USDC) |
| `wallet_balance` | `POST /v1/wallet/balance` | **2000** (0.002 USDC) |
| `usdc_transfers` | `POST /v1/wallet/usdc-transfers` | **2000** (0.002 USDC) |

### normalize_text
Body: `{"text":"..."}`

### fetch_markdown
Body: `{"url":"https://example.com","max_chars":5000}`

### wallet_balance
Body: `{"address":"0x..."}` → Base ETH + USDC (6 decimals)

### usdc_transfers
Body: `{"address":"0x...","limit":10}` → recent USDC transfers (`limit` ≤ 25)

## Payment flow
1. Unpaid POST → **HTTP 402** + `PAYMENT-REQUIRED` / `accepts[]`
2. Buyer signs EIP-3009 `TransferWithAuthorization` for `amount` / `payTo` / `asset` / `network`
3. Retry with `PAYMENT-SIGNATURE` (echo server `extensions` append-only)
4. **200** + `PAYMENT-RESPONSE` settle metadata

## Client
Python package `walletforge-x402`: `X402Buyer`, LangChain tools, AgentKit provider.
