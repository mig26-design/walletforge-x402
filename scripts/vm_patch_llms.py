#!/usr/bin/env python3
"""Patch x402-server + x402-caller on the VM. No price changes. No secrets printed."""
from pathlib import Path
import re
import subprocess
import sys

SERVER = Path("/opt/x402-server/server.py")
CALLER = Path("/opt/x402-caller/langchain_tools.py")
HELP_CANDIDATES = [
    Path("/opt/x402-caller/telegram_poll.py"),
    Path("/opt/x402-caller/agent_runtime.py"),
]

LLMS = r'''# WalletForge

WalletForge is a non-custodial Base USDC x402 micro-utility API: wallet read tools + scrape/normalize utilities. Agents pay via EIP-3009 (PayAI facilitator). No seller private key on the server.

## Prices (atomic USDC, 6 decimals)
- POST /v1/normalize → 1000 (0.001 USDC)
- POST /v1/fetch-markdown → 3000 (0.003 USDC)
- POST /v1/wallet/balance → 2000 (0.002 USDC)
- POST /v1/wallet/usdc-transfers → 2000 (0.002 USDC)

## Payment
- Network: eip155:8453 (Base mainnet)
- Asset: Base USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- payTo: 0x405b88f183cb9fbb14e20b08a167917aa66e201c
- Flow: unpaid POST → HTTP 402 + PAYMENT-REQUIRED → sign EIP-3009 TransferWithAuthorization → retry with PAYMENT-SIGNATURE → 200 + PAYMENT-RESPONSE

## Examples
POST https://api.walletforge.app/v1/normalize
{"text":"Call Jane at jane@example.com tomorrow"}

POST https://api.walletforge.app/v1/fetch-markdown
{"url":"https://example.com","max_chars":5000}

POST https://api.walletforge.app/v1/wallet/balance
{"address":"0x405b88f183cb9fbb14e20b08a167917aa66e201c"}

POST https://api.walletforge.app/v1/wallet/usdc-transfers
{"address":"0x405b88f183cb9fbb14e20b08a167917aa66e201c","limit":10}

## Discovery
- https://api.walletforge.app/health
- https://api.walletforge.app/agent.json
- https://api.walletforge.app/.well-known/agent.json
- https://api.walletforge.app/.well-known/x402.json
- https://api.walletforge.app/openapi.json
- https://api.walletforge.app/llms.txt
'''

def sh(cmd):
    print("+", cmd)
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if r.stdout:
        print(r.stdout[-2000:])
    if r.returncode != 0 and r.stderr:
        print(r.stderr[-1000:], file=sys.stderr)
    return r.returncode

def patch_server():
    t = SERVER.read_text()
    if "/llms.txt" in t and "LLMS_TXT" in t:
        print("server: llms already present")
        return
    if "PlainTextResponse" not in t:
        t = t.replace(
            "from fastapi.responses import JSONResponse",
            "from fastapi.responses import JSONResponse, PlainTextResponse",
        )
    block = (
        "\nLLMS_TXT = " + repr(LLMS) + "\n\n"
        '@app.get("/llms.txt", response_class=PlainTextResponse)\n'
        '@app.get("/.well-known/llms.txt", response_class=PlainTextResponse)\n'
        "def llms_txt():\n"
        "    return LLMS_TXT\n"
    )
    # insert before first @app.get("/health") or after app = FastAPI
    m = re.search(r'@app\.get\("/health"', t)
    if m:
        t = t[: m.start()] + block + "\n" + t[m.start() :]
    else:
        m2 = re.search(r"app\s*=\s*FastAPI\([^\)]*\)\s*", t)
        if not m2:
            raise SystemExit("cannot find insertion point in server.py")
        t = t[: m2.end()] + "\n" + block + t[m2.end() :]
    SERVER.write_text(t)
    print("server: patched llms.txt routes")

def patch_caller():
    t = CALLER.read_text()
    if "walletforge_wallet_balance" in t:
        print("caller: wallet tools already present")
        return
    # Detect paid_client style vs BaseWalletForgeTool style
    if "execute_paid_call" in t or "from paid_client" in t or "paid_client" in t:
        # Append tools using paid_client.execute_paid_call pattern matching existing
        addition = '''

class WalletBalanceInput(BaseModel):
    address: str = Field(description="Base address (0x...) for ETH + USDC balances")


class UsdcTransfersInput(BaseModel):
    address: str = Field(description="Base address (0x...) for recent USDC transfers")
    limit: int = Field(default=10, description="Max transfers (1-25)")


class WalletForgeWalletBalanceTool(BaseTool):
    name: str = "walletforge_wallet_balance"
    description: str = "Returns Base ETH and USDC balances for an address via WalletForge x402 (0.002 USDC)."
    args_schema: type[BaseModel] = WalletBalanceInput

    def _run(self, address: str) -> str:
        from paid_client import execute_paid_call
        return execute_paid_call(
            "https://api.walletforge.app/v1/wallet/balance",
            {"address": address},
        )


class WalletForgeUsdcTransfersTool(BaseTool):
    name: str = "walletforge_usdc_transfers"
    description: str = "Lists recent Base USDC transfers for an address via WalletForge x402 (0.002 USDC)."
    args_schema: type[BaseModel] = UsdcTransfersInput

    def _run(self, address: str, limit: int = 10) -> str:
        from paid_client import execute_paid_call
        lim = max(1, min(int(limit or 10), 25))
        return execute_paid_call(
            "https://api.walletforge.app/v1/wallet/usdc-transfers",
            {"address": address, "limit": lim},
        )
'''
        # If BaseTool already imported and paid_client used differently, adapt:
        if "BaseWalletForgeTool" in t:
            addition = '''

class WalletBalanceInput(BaseModel):
    address: str = Field(description="Base address (0x...) for ETH + USDC balances")


class UsdcTransfersInput(BaseModel):
    address: str = Field(description="Base address (0x...) for recent USDC transfers")
    limit: int = Field(default=10, description="Max transfers (1-25)")


class WalletForgeWalletBalanceTool(BaseWalletForgeTool):
    name: str = "walletforge_wallet_balance"
    description: str = "Returns Base ETH and USDC balances for an address via WalletForge x402 (0.002 USDC)."
    args_schema: type[BaseModel] = WalletBalanceInput

    def _run(self, address: str) -> str:
        return self._execute_paid_call(
            "https://api.walletforge.app/v1/wallet/balance",
            {"address": address},
        )


class WalletForgeUsdcTransfersTool(BaseWalletForgeTool):
    name: str = "walletforge_usdc_transfers"
    description: str = "Lists recent Base USDC transfers for an address via WalletForge x402 (0.002 USDC)."
    args_schema: type[BaseModel] = UsdcTransfersInput

    def _run(self, address: str, limit: int = 10) -> str:
        lim = max(1, min(int(limit or 10), 25))
        return self._execute_paid_call(
            "https://api.walletforge.app/v1/wallet/usdc-transfers",
            {"address": address, "limit": lim},
        )
'''
        CALLER.write_text(t.rstrip() + "\n" + addition + "\n")
        print("caller: appended wallet tools")
    else:
        raise SystemExit("unrecognized langchain_tools.py shape")

    # /help mention
    for hp in HELP_CANDIDATES:
        if not hp.exists():
            continue
        h = hp.read_text()
        if "walletforge_wallet_balance" in h:
            continue
        if "/help" in h or "fetch_markdown" in h or "normalize" in h:
            # light touch: append note near help text if a HELP string exists
            if "walletforge_fetch_markdown" in h and "walletforge_wallet_balance" not in h:
                h = h.replace(
                    "walletforge_fetch_markdown",
                    "walletforge_fetch_markdown, walletforge_wallet_balance, walletforge_usdc_transfers",
                    1,
                )
                hp.write_text(h)
                print(f"help: touched {hp}")
                break

def main():
    patch_server()
    patch_caller()
    sh("sudo systemctl restart x402-server")
    sh("sudo systemctl restart x402-agent x402-telegram")
    sh("curl -sS -o /tmp/llms.out -w 'llms:%{http_code}\\n' https://api.walletforge.app/llms.txt")
    sh("curl -sS -o /dev/null -w 'wk:%{http_code}\\n' https://api.walletforge.app/.well-known/llms.txt")
    sh("curl -sS -o /dev/null -w 'wallet402:%{http_code}\\n' -X POST https://api.walletforge.app/v1/wallet/balance -H 'Content-Type: application/json' -d '{\"address\":\"0x405b88f183cb9fbb14e20b08a167917aa66e201c\"}'")
    sh("systemctl is-active x402-server x402-agent x402-telegram x402-wallet-alert.timer; systemctl is-active x402-daily-job.timer || true")
    sh("python3 - <<'P'\nfrom web3 import Web3\nrpc='https://mainnet.base.org'\nw=Web3(Web3.HTTPProvider(rpc))\naddr=Web3.to_checksum_address('0xae162A1A777080F16e650e298De537dfFe256121')\nusdc=Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')\nabi=[{'constant':True,'inputs':[{'name':'_owner','type':'address'}],'name':'balanceOf','outputs':[{'name':'balance','type':'uint256'}],'type':'function'}]\nc=w.eth.contract(address=usdc, abi=abi)\nprint('buyer_usdc', c.functions.balanceOf(addr).call()/1e6)\nP")
    print("DONE")

if __name__ == "__main__":
    main()
