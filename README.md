# walletforge-x402

Python **x402 V2 buyer** and adapters for [LangChain](https://python.langchain.com/), [Coinbase AgentKit](https://docs.cdp.coinbase.com/agentkit/docs/welcome), and Autonolas / Open Autonomy — wired to the live WalletForge API.

**API:** [https://api.walletforge.app](https://api.walletforge.app)

| Endpoint | Price | Request body |
|----------|-------|----------------|
| `POST /v1/fetch-markdown` | **0.05 USDC** (`50000`) | `{"url": "https://...", "max_chars": 5000}` |
| `POST /v1/normalize` | **0.01 USDC** (`10000`) | `{"text": "..."}` |

| | |
|--|--|
| Network | Base mainnet `eip155:8453` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| payTo | `0xb5F5a86Df5F78ed78920f74a1D7f26368F708E94` |
| Facilitator | `https://facilitator.payai.network` |
| Discovery | [`/.well-known/agent.json`](https://api.walletforge.app/.well-known/agent.json) · [`/.well-known/x402.json`](https://api.walletforge.app/.well-known/x402.json) |

Unpaid calls return **HTTP 402** with `PAYMENT-REQUIRED` (base64 JSON) and `extensions.bazaar`. The buyer **must echo** those extensions into `PAYMENT-SIGNATURE` (append-only; never strip server fields).

> **Paid calls spend real Base USDC.** Unit tests are mocked. Unpaid 402 smoke does not spend.

---

## Install from GitHub

Replace `mig26-design/walletforge-x402` with your fork or upstream once published.

```bash
# clone
git clone https://github.com/mig26-design/walletforge-x402.git walletforge-x402
cd walletforge-x402

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# core buyer
pip install -e .

# optional runtimes
pip install -e ".[langchain]"
pip install -e ".[agentkit]"
pip install -e ".[dev]"        # pytest
```

### One-liner (pip from Git)

```bash
pip install "git+https://github.com/mig26-design/walletforge-x402.git"
pip install "git+https://github.com/mig26-design/walletforge-x402.git#egg=walletforge-x402[langchain]"
```

### Install from release tarball

```bash
tar -xzf walletforge-x402.tgz
cd walletforge-x402
python -m venv .venv && source .venv/bin/activate
pip install -e ".[langchain]"
```

---

## Publish this repo on GitHub (maintainers)

```bash
cd walletforge-x402
git init
git add .
git commit -m "Initial walletforge-x402 adapters"
# create empty public repo on GitHub, then:
git branch -M main
git remote add origin https://github.com/mig26-design/walletforge-x402.git
git push -u origin main
```

Suggested repo settings:

1. Add `LICENSE` (MIT already declared in `pyproject.toml`).
2. Protect `main`; require CI green before merge.
3. Never commit `.env`, buyer keys, or `*.pem`.
4. Optional GitHub Actions: `pip install -e ".[dev]"` + `pytest -q` on PR.
5. Tag releases: `git tag v0.1.0 && git push --tags`.

`.gitignore` already excludes `.venv/`, `__pycache__/`, `.env`, and key files.

---

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `BUYER_PRIVATE_KEY` | paid calls only | Hex EOA for EIP-3009 `TransferWithAuthorization` |
| `X402_BASE_URL` | no | Defaults to `https://api.walletforge.app` |

```bash
export BUYER_PRIVATE_KEY=0xYOUR_FUNDED_BASE_EOA_KEY
# unset X402_BASE_URL unless you intentionally point at another host
unset X402_BASE_URL
```

**Never commit or print private keys.** Fund the buyer with Base USDC (and a little ETH for unrelated txs if needed; x402 settle is facilitator-sponsored).

---

## Quick start

### Unpaid 402 smoke (safe — no key, no spend)

```bash
python examples/unpaid_402_smoke.py
```

```python
from walletforge_x402 import X402Buyer

r = X402Buyer.unpaid_challenge(
    "/v1/fetch-markdown",
    {"url": "https://example.com"},
)
assert r.status_code == 402
print(r.payment_required["accepts"][0]["amount"])  # 50000
```

### Paid call (spends 0.05 USDC)

```python
from walletforge_x402 import X402Buyer

buyer = X402Buyer()  # reads BUYER_PRIVATE_KEY
result = buyer.fetch_markdown("https://example.com", max_chars=5000)
print(result.data["markdown"][:400])
print(result.payment_response)  # settle tx hash, etc.
```

---

## LangChain

```bash
pip install -e ".[langchain]"
```

```python
from walletforge_x402.langchain_tools import walletforge_tools

tools = walletforge_tools()  # fetch_markdown, normalize_text
# bind tools to your agent / LLM as usual
```

See `examples/langchain_agent_example.py`.

---

## Coinbase AgentKit

```bash
pip install -e ".[agentkit]"
```

```python
from walletforge_x402.agentkit_provider import walletforge_action_provider

provider = walletforge_action_provider()
# AgentKit(AgentKitConfig(wallet_provider=..., action_providers=[provider]))
```

Actions: `fetch_markdown`, `normalize_text`. See `examples/agentkit_example.py`.

---

## Autonolas / Open Autonomy

```python
from walletforge_x402.autonolas import fetch_markdown_via_buyer

data = fetch_markdown_via_buyer("https://example.com", max_chars=8000)
```

Skill stubs: `src/walletforge_x402/autonolas/` and `examples/autonolas_skill/`.  
Inject `BUYER_PRIVATE_KEY` via the agent secret store — never YAML.

---

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

Mocked `httpx` only — CI must not run live paid settles.

---

## Protocol notes for agent builders

1. `POST` unpaid → expect **402** + `PAYMENT-REQUIRED`.
2. Decode challenge; build EIP-3009 authorization for `accepted.amount` / `payTo` / `asset` / `network`.
3. Retry same path with header `PAYMENT-SIGNATURE` (base64 payment payload).
4. **Echo `extensions`** from the 402 body into the payment payload (required for PayAI Bazaar refresh).
5. Success → **200** + `PAYMENT-RESPONSE` (settle metadata).

---

## License

MIT
