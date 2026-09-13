# WalletForge x402 — Tool Specification

## Service

| Field | Value |
|-------|-------|
| Service name | WalletForge x402 |
| Public base URL | `https://api.walletforge.app` |
| Protocol | x402 V2 (`exact`) |
| Network | Base mainnet `eip155:8453` |
| Settlement asset | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Recipient (`payTo`) | `0x405b88f183cb9fbb14e20b08a167917aa66e201c` |
| Facilitator | `https://facilitator.payai.network` |
| Seller custody | None (non-custodial; no seller private key) |

Discovery:

- https://api.walletforge.app/.well-known/agent.json
- https://api.walletforge.app/.well-known/x402.json
- PayAI Bazaar: `GET https://facilitator.payai.network/discovery/resources` (search `walletforge`)
- x402scan registrations: fetch-markdown `2a3ab5b6-ba4f-4bef-87de-7f62cf4a5e43`, normalize `d8f51e9f-4082-4022-9590-6f5e321109da`

---

## Tool: `fetch_markdown`

| Field | Value |
|-------|-------|
| HTTP | `POST https://api.walletforge.app/v1/fetch-markdown` |
| Price | **50000** atomic USDC (**0.05 USDC**) |
| Content-Type | `application/json` |
| Auth | x402 payment headers (not API keys) |

### Input schema

```json
{
  "type": "object",
  "required": ["url"],
  "properties": {
    "url": { "type": "string", "format": "uri", "description": "Public http(s) URL to fetch" },
    "max_chars": {
      "type": "integer",
      "minimum": 500,
      "maximum": 200000,
      "default": 50000,
      "description": "Truncate returned markdown after this many characters"
    }
  }
}
```

### Output schema (success 200)

```json
{
  "type": "object",
  "properties": {
    "url": { "type": "string" },
    "title": { "type": "string" },
    "content_type": { "type": "string" },
    "markdown": { "type": "string" },
    "stats": {
      "type": "object",
      "properties": {
        "chars": { "type": "integer" },
        "bytes_fetched": { "type": "integer" },
        "truncated": { "type": "boolean" }
      }
    }
  }
}
```

### Safety

- SSRF-hardened: public HTTP(S) only; blocks private/link-local/metadata hosts.
- Response size / timeout capped server-side.

### LangChain tool name

`fetch_markdown`

### AgentKit action name

`fetch_markdown`

---

## Tool: `normalize_text`

| Field | Value |
|-------|-------|
| HTTP | `POST https://api.walletforge.app/v1/normalize` |
| Price | **10000** atomic USDC (**0.01 USDC**) |

### Input schema

```json
{
  "type": "object",
  "required": ["text"],
  "properties": {
    "text": { "type": "string", "minLength": 1, "maxLength": 200000 }
  }
}
```

### Output schema (success 200)

```json
{
  "type": "object",
  "properties": {
    "normalized": { "type": "string" },
    "emails": { "type": "array", "items": { "type": "string" } },
    "urls": { "type": "array", "items": { "type": "string" } },
    "phones": { "type": "array", "items": { "type": "string" } },
    "stats": { "type": "object" }
  }
}
```

### LangChain / AgentKit names

`normalize_text`

---

## Payment flow (buyer)

1. `POST` without payment → **HTTP 402** + `PAYMENT-REQUIRED` (base64 JSON).
2. Decode `accepts[0]`; sign EIP-3009 `TransferWithAuthorization`.
3. Retry with `PAYMENT-SIGNATURE` (base64). **Echo `extensions` from the 402 body** (required for Bazaar).
4. Success → **200** + `PAYMENT-RESPONSE` (includes settle tx hash).

Python buyer: package `walletforge-x402` (`X402Buyer`, LangChain tools, AgentKit provider).
