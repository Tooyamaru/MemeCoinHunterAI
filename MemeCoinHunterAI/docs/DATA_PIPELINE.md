# Data Pipeline

```text
Raw market / chain data
        ↓
Validation
        ↓
Normalization
        ↓
Market state
        ↓
Features
        ↓
Point-in-time feature snapshot
        ↓
Signals
        ↓
Opportunity
        ↓
Fast pre-score
        ↓
Optional deep analysis
        ↓
Deterministic decision intent
        ↓
Hard risk / capital
        ↓
BUY + SELL pre-flight
        ↓
Provider-agnostic execution
        ↓
Reconciliation
        ↓
Decision journal / outcome
```

## V1.1 data contracts

- Preserve event timestamp, received timestamp, decision timestamp, and source
  identity.
- Compute data age and expose freshness explicitly.
- Stale or contradictory data is a quality state and may force NO-TRADE.
- Every decision preserves the feature values and evidence available at that
  time; later updates must not overwrite the historical snapshot.
- Point-in-time snapshots are required to prevent look-ahead bias, future-data
  leakage, and survivorship bias.
- Separate raw high-frequency records, normalized state, derived features,
  audit/decision data, and outcomes.
- Long-term retention prioritizes decision journal records, decision-linked
  snapshots, executed trade records, P&L/outcomes, and
  model/ruleset/configuration provenance. Raw tick/orderbook data may have
  shorter retention unless needed for research or audit.
- Detect duplicates, preserve sequence integrity where available, and track
  source health, failure, retry, recovery, and resynchronization.

## Hard safety evidence

The future hard-risk contract must expose explicit PASS, FAIL, or UNKNOWN
states for token/contract and liquidity checks, including mint authority,
freeze authority, LP status and concentration, metadata mutability,
top-holder concentration, funding-wallet relationships, sellability, and
proxy/control patterns. UNKNOWN fails closed and never becomes PASS.

## Execution-aware data

Execution feasibility is part of the decision. Before an initial BUY, the
future pre-flight layer must support BUY and SELL simulation whenever
technically possible and capture expected output, price impact, slippage,
sellability, fees, route validity, chain state, transaction behavior, and
relevant contract behavior. Future paper/shadow records must model liquidity,
quote drift, transaction failure, priority fees, MEV effects, and latency
instead of infinite liquidity or perfect fills.

Latency budgets are explicit future fields for ingestion, hard filters,
pre-score, decision, quote, pre-flight, submission, and confirmation. Exact
targets require benchmarking.

## Failure handling

Bad, missing, duplicated, delayed, or contradictory input must produce an explicit quality state. Downstream consumers must fail closed when required data is stale or unavailable. Recovery must be observable and replayable before a stream is considered healthy again.

Blockchain state is authoritative for actual position state. Future
reconciliation must handle dropped, failed, delayed, partial, duplicate, and
unexpected transactions, and must block subsequent decisions while internal
and on-chain state disagree.

## P00/P01 boundary

No blockchain or DEX connection, scanner, signal calculation, trading
simulator, execution implementation, or retention policy belongs in the
current foundation revision.
