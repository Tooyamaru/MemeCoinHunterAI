# Risk Engine Principles

The Risk Governor has higher authority than the Decision Engine. It may:

- **ALLOW** an otherwise eligible action
- **REDUCE** exposure or requested size
- **BLOCK** an action
- **EMERGENCY STOP** relevant activity

## Planned risk domains

- Token and liquidity risk
- Manipulation and tradability risk
- Market and regime risk
- Portfolio and correlation risk
- Position sizing and exposure limits
- Daily loss control
- Stale-data and data-quality blocking
- Execution guards and circuit breakers
- Kill switch and emergency procedures

Risk decisions must be explainable, auditable, fail closed where required, and independent from the model's desired action. Execution must never bypass this layer. P00 does not implement risk calculations or controls.
