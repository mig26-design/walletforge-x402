"""Register WalletForge x402 as a Coinbase AgentKit ActionProvider."""

from __future__ import annotations

import os
import sys


def main() -> int:
    from walletforge_x402.agentkit_provider import walletforge_action_provider

    provider = walletforge_action_provider()
    print(f"provider={provider.name} supports_network(base)={provider.supports_network(type('N', (), {'protocol_family': 'evm', 'network_id': 'base-mainnet', 'chain_id': '8453'})())}")

    # With coinbase-agentkit installed:
    #   from coinbase_agentkit import AgentKit, AgentKitConfig
    #   agent_kit = AgentKit(AgentKitConfig(
    #       wallet_provider=wallet_provider,
    #       action_providers=[walletforge_action_provider()],
    #   ))
    if not os.getenv("BUYER_PRIVATE_KEY"):
        print("Set BUYER_PRIVATE_KEY before invoking paid actions (real Base USDC).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
