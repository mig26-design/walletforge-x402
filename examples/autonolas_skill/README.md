# Autonolas / Open Autonomy packing notes

1. Scaffold a skill (`autonomy scaffold skill walletforge_x402` or copy this folder into your AEA packages tree).
2. Copy `skill.yaml`, `behaviours.py`, and use `walletforge_x402.autonolas.tool` helpers.
3. Provide `BUYER_PRIVATE_KEY` via the agent secret store / env — **never** put keys in YAML.
4. Optionally set `X402_BASE_URL` (default `https://api.walletforge.app`).
5. Pack / publish with your usual `autonomy push-all` / registry flow.

The behaviour stub calls the shared EIP-3009 buyer which echoes `extensions` from `PAYMENT-REQUIRED` into `PAYMENT-SIGNATURE`.
