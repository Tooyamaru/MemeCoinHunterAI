# Architecture

## V1.1 strategic position

Meme Coin Hunter AI is a selective, explainable, risk-first crypto decision
system focused initially on Solana meme coins. It is not a launch sniper, MEV
bot, generic LLM trader, or multi-agent autonomous system. Execution is part
of strategy: a theoretical signal is not a valid trade when execution
conditions destroy its expected edge.

## Logical layers

1. **Data layer** — source adapters, raw events, validation, normalization, timestamps, freshness, and persistence.
2. **Intelligence layer** — market state, features, signals, safety evidence, and regime context.
3. **Opportunity layer** — signal fusion, candidate ranking, quality, and phase analysis.
4. **Decision layer** — bounded decisions with evidence, confidence, uncertainty, invalidation, and entry quality.
5. **Governance / risk layer** — independent authorization, exposure controls, circuit breakers, and emergency stop.
6. **Execution layer** — paper execution first; later deterministic interfaces, routers, and venue adapters.
7. **Learning layer** — immutable decision/outcome history, evaluation, and controlled model/strategy versions.
8. **Presentation / dashboard layer** — read-oriented visibility into state, evidence, decisions, risk, and outcomes.
9. **Infrastructure layer** — configuration, logging, health, workers, database, deployment, and recovery.

## V1.1 computation boundary

The project has one modular Decision Engine. “AI” is a category of computation,
not a requirement to use an LLM. Future analysis may contain:

- deterministic rules;
- statistical or classical models;
- optional bounded ML analysis; and
- optional LLM/narrative analysis.

The V1 hot path is:

```text
Data
→ Hard Risk Filter
→ Fast Pre-Score
→ Optional Deep Analysis
→ Deterministic Decision Engine
→ Risk/Capital Engine
→ Pre-Flight
→ Execution
```

LLM/narrative analysis is deferred research. It must not be the primary
trading brain, block the critical path, or independently trigger a BUY. If
introduced later, it requires measurable market/on-chain corroboration and a
benchmark against a control system without narrative analysis. Multi-agent
architecture is deferred until a measured bottleneck, defined hypothesis,
A/B comparison, and evidence of improvement. A generic plugin framework is
also deferred; only clearly valuable boundaries should be modular.

## Required future safety boundaries

Hard Risk Filters are explicit and testable. Contract/token safety checks
include mint authority, freeze authority, LP status, LP concentration,
metadata mutability, top-holder concentration, funding-wallet relationships,
sellability, proxy/control patterns, mutable or dangerous behavior, liquidity
quality, and stale data. Each check returns PASS, FAIL, or UNKNOWN; UNKNOWN
fails closed and never silently becomes PASS.

Pre-Flight Simulation is mandatory before execution and supports BUY and SELL
simulation before an initial BUY whenever technically possible. It evaluates
expected output, price impact, slippage, sellability, fees, route validity,
transaction behavior, relevant contract behavior, and current chain state.
RPC, routing, and MEV infrastructure remain provider-agnostic and may later
support primary, backup, private/premium, and MEV-aware providers without
selecting one in V1.1.

The Decision Engine emits a trade intent. It does not own or expose private
keys, sign, or broadcast:

```text
Decision Intent
→ Risk/Capital Authorization
→ Execution Request
→ Isolated Signing Boundary
→ Broadcast
→ Reconciliation
→ Journal
```

The signing boundary independently enforces hard limits. An independent Exit
Monitor provides a low-latency position-protection path without depending on
LLM, narrative analysis, the slow analysis pipeline, or a new BUY cycle. An
out-of-band watchdog/kill switch can stop new execution if the main
application is stuck, disconnected, malfunctioning, or producing invalid
decisions.

Risk must model maximum position size, total exposure, correlated/ecosystem
and narrative/theme exposure, liquidity-regime concentration, daily loss and
drawdown limits, stale-data protection, emergency stop, and NO-TRADE on
unreliable execution state. Internal position state is not authoritative for
actual positions; it must be reconciled against on-chain state, including
dropped, failed, delayed, partial, duplicated, and unexpected transactions.

## Reproducibility, latency, and retention

Every decision requires a point-in-time feature snapshot reference so the
decision can be reproduced from information available at that time. This
prevents look-ahead bias, future-data leakage, and survivorship bias.

Latency is a measurable architectural budget for data ingestion, hard
filters, pre-score, decision, quote, pre-flight, submission, and confirmation.
Numerical limits must be established by later benchmarks, not invented here.

The Decision Journal preserves timestamp, market/token, feature snapshot
reference, decision output, risk result, execution assumptions,
ruleset/model/configuration versions, outcome, and future cryptographic/hash
provenance references. Long-term retention prioritizes audit/decision data,
associated snapshots, executed trades, outcomes, and provenance; raw
high-frequency data may have shorter retention unless needed for research or
audit.

## Dependency direction

Data flows toward intelligence, opportunity, decision, governance, execution, and learning. Presentation observes published state; it does not bypass governance. Modules should communicate through explicit contracts and remain replaceable.

## Mandatory control boundary

```text
Decision Intent
      ↓
Risk / Capital Authorization
      ↓
Execution Request
      ↓
Isolated Signing Boundary
      ↓
Broadcast
       ↓
Reconciliation
       ↓
Journal
```

The Decision Engine must never hold unrestricted fund control, own private
keys, sign, broadcast, or call a venue directly. The Risk Governor has higher
authority and can ALLOW, REDUCE, BLOCK, or EMERGENCY STOP. P01-T05 preserves
these boundaries. Later services remain gated until explicitly authorized.

## Future portability

The P01 runtime baseline is Python/FastAPI in `backend/api` with shared infrastructure in `backend/core`. The initial Replit environment is for development and preview. GitHub is the source of truth. A future stable 24/7 runtime may use Railway, but Railway remains out of scope until its planned production phase.


## P05 Current Boundary
P05-T03 is the deterministic hard-risk/disqualification boundary and remains
the mandatory ELIGIBLE gate. P05-T04 is COMPLETE / CLOSED / AUDITED PASS WITH
NON-BLOCKING OBSERVATIONS as the per-candidate feature and quality evaluation
boundary. It preserves existing P04-T10 snapshots and provenance, applies the
P05-T03 eligibility gate, and performs no recalculation, scoring, ranking,
decision, execution, authorization, AI, or external I/O. P05-T05 is COMPLETE /
CLOSED / AUDITED PASS as the deterministic, provider-neutral, pure per-candidate
opportunity pre-score boundary. P05-T06 is COMPLETE / CLOSED / AUDITED PASS. P05 remains deterministic, provider-neutral,
and fail-closed.

## P06 Architecture Gate

P05-T01 through P05-T08 are complete and closed. The P06 architecture gate is
IN PROGRESS; no P06 runtime is authorized yet. The approved P06 boundary
consumes one validated P05-T08 evidence-first opportunity context and produces
one deterministic, versioned analytical decision intent.

Optional bounded deep analysis, including statistical, classical, bounded ML,
or narrative/LLM analysis, is non-authoritative and separately versioned. It
must not invent evidence, overwrite risk state, independently trigger an
action, or block the deterministic hot path. The deterministic Decision Engine
remains the decision authority.

P06 preserves all P05 provenance, risk and uncertainty/invalidation context,
timestamps, contract/evaluator versions, and T05/T06/T07/T08 digests. It may
emit only an analytical action from the approved vocabulary or `NO_TRADE`;
confidence is not profit probability and action is not authorization.

P06 does not rank candidates, compare candidate sets, authorize capital, own
private keys or wallets, sign, broadcast, call RPC/DEX/provider execution
infrastructure, construct transactions, or submit orders. The separate
Risk/Capital Authorization, Execution Request, isolated Signing Boundary,
Broadcast, Reconciliation, and Journal boundaries remain mandatory.
