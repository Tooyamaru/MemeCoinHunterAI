# Security

## Permanent rules

Never commit:

- Private keys
- Wallet seed phrases
- API secrets
- Credentials
- `.env` files containing secrets

Use environment secrets. Documentation may contain secret variable names only, never values.

## V1.1 security boundaries

Capital protection is the highest-priority invariant. When uncertainty exists,
the result is **NO-TRADE**. This includes stale data, unknown contract safety,
failed simulation, unavailable RPC, inconsistent internal/on-chain state,
missing risk information, or invalid execution state.

The Decision Engine produces intent only. It must never own or expose private
keys, sign, broadcast, or bypass the Risk/Capital boundary. Future execution
must use an isolated signing boundary that independently enforces hard limits.
An independent out-of-band watchdog/kill switch must be able to stop new
execution even if the main application is stuck, disconnected, malfunctioning,
or producing invalid decisions. An independent Exit Monitor protects open
positions without relying on LLM, narrative, slow analysis, or a new BUY
cycle.

Future contract/scam safety checks must be explicit, testable, and represented
as PASS, FAIL, or UNKNOWN. UNKNOWN is never PASS. Future reconciliation must
treat on-chain state as authoritative and prevent subsequent decisions while
internal and on-chain position state disagrees.

## Future trading controls

- Any future trading wallet must be isolated from personal or primary holdings.
- Development must not use unrestricted real-money wallet permissions.
- Withdrawal or transfer automation must not be enabled casually.
- Real-money autonomous trading remains disabled until the documented validation gates pass.
- Secrets must not appear in logs, fixtures, screenshots, generated artifacts, or project state.

Readiness must consider expectancy, drawdown, slippage, execution failures,
latency, infrastructure cost, stale-data events, duplicate orders,
kill-switch behavior, market-regime performance, and confidence intervals.
Win rate or a fixed trade count cannot authorize live trading. If durable
risk-adjusted edge is not demonstrated after controlled testing, governance
may STOP, PAUSE, or change market.

This V1.1 revision creates no integrations, wallet, secret configuration, or
fund-access code.
