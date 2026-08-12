# Risk Engine Principles

The Risk Governor has higher authority than the Decision Engine. It may:

- **ALLOW** an otherwise eligible action
- **REDUCE** exposure or requested size
- **BLOCK** an action
- **EMERGENCY STOP** relevant activity

## Planned risk domains

- Token and contract safety risk
- Mint/freeze authority and metadata mutability
- LP status, LP concentration, liquidity quality, and sellability
- Top-holder concentration and funding-wallet relationships
- Proxy/control patterns and suspicious mutable behavior
- Manipulation and tradability risk
- Market and regime risk
- Portfolio, correlated, ecosystem, narrative/theme, and liquidity-regime exposure
- Position sizing and exposure limits
- Daily loss and drawdown control
- Stale-data and data-quality blocking
- Execution guards, pre-flight gates, and circuit breakers
- Independent out-of-band watchdog, kill switch, and emergency procedures

## Hard filter contract

Future safety checks are explicit and testable, with states:

```text
PASS | FAIL | UNKNOWN
```

UNKNOWN never silently becomes PASS. Stale data, unknown contract safety,
missing risk information, failed simulation, unavailable RPC, inconsistent
state, or invalid execution state must produce NO-TRADE.

## Capital and state protection

Future controls must enforce maximum position size, total exposure,
correlated/ecosystem/theme exposure, liquidity-regime concentration, daily
loss/drawdown limits, stale-data protection, and an emergency stop. The
watchdog/kill switch must be independent of the Decision Engine and able to
stop new execution if the main application is stuck, disconnected,
malfunctioning, or producing invalid decisions.

On-chain state is authoritative for actual positions. Before subsequent
decisions, future reconciliation must resolve internal versus on-chain
disagreement, including dropped, failed, delayed, partial, duplicated, and
unexpected transactions.

Risk decisions must be explainable, auditable, fail closed where required, and independent from the model's desired action. Execution must never bypass this layer. P00 does not implement risk calculations or controls.
