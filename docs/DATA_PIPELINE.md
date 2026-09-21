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

## P04-LME-01 limited offline analytical source boundary

The owner-approved V1 historical price-evidence source is the CoinGecko Demo
Onchain pool-OHLCV endpoint. It is limited to exact-pool, exact-token,
closed one-minute candles mapped through the existing P02 admission boundary.
Missing intervals are not interpolated, and invalid identity, temporal, or
content evidence fails closed.

The implemented `PRICE_DIRECTION_1M` policy classifies only whether the latest
validated close rose, fell, or remained flat relative to the previous close.
It is observational evidence, not a prediction or trading instruction. The
complete decision, mapping, test requirements, and excluded scope are recorded
in `docs/P04-LME-01-LIVE-MARKET-EVIDENCE-SPECIFICATION.md`. The pure mapper and
policy are implemented and tested through the existing P02/P04/P05 chain using
synthetic fixtures.

P04-LME-02 adds one bounded server-side HTTP GET and one-shot diagnostic
composition. It reads the API credential from the exact environment name,
disables redirects, performs no retry, enforces the request-owned timeout and
streaming response-size limit, and supplies a distinct post-receipt evaluation
time to the pure mapper. Continuous polling, live provider verification,
application wiring, and paper automation remain outside the completed local
verification. The transport does not select a token or pool.

P04-LME-03 is an owner-accepted limited orchestration boundary. It binds one
current P02-T06 token candidate and one exact caller-directed pool
target to the existing one-shot diagnostic, while validating admission before
credential lookup or network access. It does not discover, rank, or select a
token or pool and adds no polling or application wiring. The limited
implementation, offline verification, and locked CI are complete.

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
