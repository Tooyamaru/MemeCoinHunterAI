# Testing Strategy

## V1.1 verification principles

Every future decision must be reproducible from a point-in-time feature
snapshot containing only information available at decision time. Tests must
guard against look-ahead bias, future-data leakage, survivorship bias, and
feedback loops.

The planned verification progression is:

```text
Unit tests
    ↓
Integration tests
    ↓
Data validation
    ↓
Historical simulation
    ↓
Real-time paper trading
    ↓
Small-capital validation
    ↓
Production
```

A feature is not done merely because code exists, the application starts, or an agent says it works. Each task must define explicit verification criteria and preserve evidence of the checks performed.

Future testing must cover failure paths, stale data, duplicate events,
recovery, PASS/FAIL/UNKNOWN hard-risk states, explicit UNKNOWN-to-NO-TRADE
behavior, governance blocks, correlated/ecosystem/theme exposure, execution
friction, BUY and SELL pre-flight, route validity, sellability, reconciliation
against on-chain state, out-of-band watchdog behavior, Exit Monitor behavior,
signing hard limits, and security boundaries—not only successful flows.

Paper/shadow validation must model slippage, price impact, liquidity, quote
drift, transaction failure, priority fees, MEV effects, and execution latency.
Latency budgets for ingestion, hard filters, pre-score, decision, quote,
pre-flight, submission, and confirmation must be measured against later
benchmarks rather than assumed targets.

Readiness testing must evaluate expectancy, drawdown, slippage, execution
failure rate, latency, infrastructure cost, stale-data events,
duplicate-order incidents, kill-switch behavior, market-regime performance,
and confidence intervals. No fixed trade count or win rate alone authorizes
live trading. Controlled testing must be able to conclude STOP, PAUSE, or
change market when durable risk-adjusted edge is absent.

For this V1.1 documentation revision, verification is limited to intended
document changes, project-state consistency, absence of source/dependency/
database/workflow changes, secret hygiene, and lightweight documentation
checks. No application or integration verification is implied.
