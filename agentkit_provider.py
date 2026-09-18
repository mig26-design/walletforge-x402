from typing import Any, Dict
import sys
sys.path.insert(0, "/opt/x402-caller")

from langchain_tools import (
    WalletForgeMarkdownTool,
    WalletForgeNormalizeTool,
    WalletForgeWalletBalanceTool,
    WalletForgeUsdcTransfersTool,
)


class WalletForgeActionProvider:
    """Action provider exposing x402 paid micro-utilities on Base."""

    def __init__(self, private_key: str):
        self.markdown_tool = WalletForgeMarkdownTool(private_key=private_key)
        self.normalize_tool = WalletForgeNormalizeTool(private_key=private_key)
        self.balance_tool = WalletForgeWalletBalanceTool(private_key=private_key)
        self.transfers_tool = WalletForgeUsdcTransfersTool(private_key=private_key)

    def get_actions(self) -> list:
        return [
            {
                "name": "walletforge_fetch_markdown",
                "description": self.markdown_tool.description,
                "parameters": self.markdown_tool.args_schema.schema(),
                "handler": self.execute_fetch_markdown,
            },
            {
                "name": "walletforge_normalize_text",
                "description": self.normalize_tool.description,
                "parameters": self.normalize_tool.args_schema.schema(),
                "handler": self.execute_normalize,
            },
            {
                "name": "walletforge_wallet_balance",
                "description": self.balance_tool.description,
                "parameters": self.balance_tool.args_schema.schema(),
                "handler": self.execute_wallet_balance,
            },
            {
                "name": "walletforge_usdc_transfers",
                "description": self.transfers_tool.description,
                "parameters": self.transfers_tool.args_schema.schema(),
                "handler": self.execute_usdc_transfers,
            },
        ]

    def execute_fetch_markdown(self, args: Dict[str, Any]) -> str:
        return self.markdown_tool._run(url=args["url"])

    def execute_normalize(self, args: Dict[str, Any]) -> str:
        return self.normalize_tool._run(text=args["text"])
