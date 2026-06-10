# Copilot Instructions

- Treat this repository as demo/paper trading software unless the user explicitly requests otherwise.
- Never add live order execution without a separate risk review and an explicit live-mode gate.
- Keep strategy research, risk controls, and broker execution in separate modules.
- Backtests must include costs, slippage, drawdown, and out-of-sample validation.
- Do not print broker secrets, API keys, tokens, or account credentials.