# Master Blueprint

This document maps the system. It does not implement future phases.

## Current implementation status

The project is in P02 — Solana / DEX Data Intelligence. P01-T04 — Application
Service & Worker Foundation and P01-T05 — Application Service & Worker
Extensions are complete. P02-T01 through P02-T04 are implemented, and the
P02-T04 corrective patch passed the available verification evidence. At the
audit checkpoint, HEAD and origin/main were both `365f6eb`, and the working
tree was clean. P02-T05 is not started and remains unauthorized pending
verification of this documentation-only correction. Later tasks remain gated
until explicitly authorized.

## V1.1 architectural baseline

V1.1 defines the intended system as a selective, explainable, risk-first crypto
decision system focused initially on Solana meme coins. It is not intended to
be a launch sniper, an MEV bot, a generic LLM trader, or a multi-agent
autonomous system. Execution quality is a first-class source of both edge and
risk.

The system keeps one modular Decision Engine. “AI” is not synonymous with an
LLM: future computation may use deterministic rules, statistical/classical
models, optional bounded ML analysis, and optional narrative/LLM analysis.
V1 hot-path decisions prefer:

```text
DATA
→ HARD RISK FILTER
→ FAST PRE-SCORE
→ OPTIONAL DEEP ANALYSIS
→ DETERMINISTIC DECISION ENGINE
→ RISK/CAPITAL ENGINE
→ PRE-FLIGHT
→ EXECUTION
```

Narrative or LLM analysis is deferred research and must not block the V1
critical path, trigger a BUY by itself, or replace measurable market/on-chain
evidence. Multi-agent architecture is deferred and may only be reconsidered
after a measured bottleneck, a performance hypothesis, an A/B comparison, and
evidence of improvement. Generic plugin architecture is also deferred; only
interfaces with clear architectural value should be modular.

Every future decision must preserve a point-in-time feature snapshot and
provenance sufficient to reproduce what was known at decision time. This is
required to prevent look-ahead bias, future-data leakage, and survivorship
bias. V1 hard risk filters must be explicit, testable, and fail closed:
mint/freeze authority, LP status and concentration, metadata mutability,
top-holder concentration, funding-wallet relationships, sellability,
proxy/control patterns, stale data, and related contract/token safety checks
must support PASS, FAIL, and UNKNOWN states. UNKNOWN is never PASS.

Pre-flight is a mandatory execution gate and should validate both BUY and SELL
simulation whenever technically possible, including expected output, price
impact, slippage, sellability, fees, route validity, transaction behavior,
contract behavior, and current chain state. RPC, routing, and MEV execution
infrastructure remain provider-agnostic and evidence-driven; no provider is
selected by this baseline.

The Decision Engine produces a trade intent and never owns private keys,
signs, or broadcasts. The future boundary is:

```text
Decision Intent
→ Risk/Capital Authorization
→ Execution Request
→ Isolated Signing Boundary
→ Broadcast
→ Reconciliation
→ Journal
```

An independent Exit Monitor protects open positions without depending on an
LLM, narrative analysis, a slow analysis pipeline, or a new BUY cycle. An
independent out-of-band watchdog/kill switch must be able to stop new
execution if the main application is stuck, disconnected, malfunctioning, or
producing invalid decisions.

Capital protection is the highest-priority invariant. Future controls must
include maximum position size, total and correlated/ecosystem/theme exposure,
liquidity-regime concentration, daily loss/drawdown limits, stale-data
protection, emergency stop, and NO-TRADE when safety, risk, state, or
execution information is uncertain. Internal position state must be
reconciled against actual on-chain state before subsequent decisions.

Latency is an explicit future concept with measurable budgets for ingestion,
hard filters, pre-score, decision, quote, pre-flight, submission, and
confirmation. Numerical targets must come from benchmarks rather than being
invented in this baseline.

The progression remains:

```text
BACKTEST
→ PAPER
→ SHADOW
→ MICRO CAPITAL
→ EVIDENCE
→ CONTROLLED LIVE
```

Paper/shadow evaluation must account for slippage, price impact, liquidity,
quote drift, transaction failure, priority fees, MEV effects, and execution
latency rather than assuming infinite liquidity or perfect fills. The
Decision Journal must retain timestamp, market/token, feature snapshot
reference, decision, risk result, execution assumptions, ruleset/model and
configuration versions, outcome, and future provenance/hash references.
Long-term retention prioritizes decision/audit data, associated snapshots,
executed trades, outcomes, and provenance over raw high-frequency data unless
raw data is needed for audit or research.

Learning is read-only in early versions: it may analyze outcomes, expectancy,
drift, and parameters, but may not autonomously change live thresholds or
risk limits. Changes require controlled review and approval. Readiness is
multi-dimensional—expectancy, drawdown, slippage, execution failures,
latency, infrastructure cost, stale data, duplicate orders, kill-switch
behavior, market-regime performance, and confidence intervals—and is never
based on win rate or a fixed trade count alone. If controlled testing fails to
demonstrate durable risk-adjusted edge, governance must allow the project to
STOP, PAUSE, or change market.

## Phase map

### P00 — PROJECT GOVERNANCE & ARCHITECTURE
- **Objective:** Establish project rules, boundaries, continuation state, and architecture.
- **Major components:** Governance docs, phase map, portability script, safety rules, testing strategy.
- **Dependencies:** None.
- **Entry criteria:** Project vision and safety constraints are agreed.
- **Exit criteria:** P00-T01 is verified; next task awaits explicit approval.
- **Major risks:** Scope creep, undocumented decisions, unsafe assumptions.
- **Deliverables:** Governance foundation and concise continuation checkpoint.

### P01 — APPLICATION FOUNDATION
- **Objective:** Create the maintainable application and service foundation.
- **Major components:** Backend, configuration, environment management, logging, errors, health, database abstraction/schema, dashboard shell, tests, lifecycle, module boundaries.
- **Dependencies:** P00.
- **Entry criteria:** Governance is verified and implementation scope is approved.
- **Exit criteria:** A minimal observable application foundation passes targeted checks.
- **Major risks:** Leaky boundaries, unsafe configuration, premature complexity.
- **Deliverables:** Foundation services, initial schema, health checks, test harness.

### P02 — SOLANA / DEX DATA INTELLIGENCE
- **Objective:** Collect reliable, normalized market data.
- **Major components:** Solana connectivity, token universe/discovery, emerging-token detection, DEX pools, liquidity, swaps, transaction flow, price/volume state, freshness, stream health, deduplication, recovery.
- **Dependencies:** P01.
- **Entry criteria:** Foundation can securely run and persist validated data.
- **Exit criteria:** Reproducible normalized market state with freshness and recovery evidence.
- **Major risks:** Provider outages, stale/duplicated data, incomplete coverage, rate limits.
- **Deliverables:** Data adapters, normalized events/state, health and recovery controls.

### P03 — TOKEN SAFETY & RISK INTELLIGENCE
- **Objective:** Reject dangerous or untradable tokens before expensive analysis.
- **Major components:** Eligibility, liquidity safety, holder concentration, developer/wallet risk, suspicious behavior, manipulation, scam/rug indicators, tradability, exit risk.
- **Dependencies:** P01, P02.
- **Entry criteria:** Validated market data is available.
- **Exit criteria:** Safety decisions are explainable, testable, and fail closed.
- **Major risks:** False negatives, adversarial behavior, misleading third-party data.
- **Deliverables:** Safety rules, risk evidence, eligibility outcomes.

### P04 — MARKET & SIGNAL INTELLIGENCE
- **Objective:** Derive robust market features and signals.
- **Major components:** Price velocity/acceleration, volume acceleration/relative volume, transaction frequency, buy/sell pressure, flow, liquidity behavior, momentum, volatility, regime, wallet/on-chain signals, justified social signals, feature snapshots.
- **Dependencies:** P02, P03.
- **Entry criteria:** Safe eligible data has known timestamps and quality.
- **Exit criteria:** Features/signals are reproducible without blind dependence on traditional indicators.
- **Major risks:** Look-ahead bias, noisy features, regime instability, data leakage.
- **Deliverables:** Feature definitions, signal outputs, snapshot history.

### P05 — OPPORTUNITY ENGINE
- **Objective:** Fuse signals and rank candidate opportunities.
- **Major components:** Dynamic weighting, candidate ranking/reduction, opportunity score/quality, market phase detection.
- **Dependencies:** P03, P04.
- **Entry criteria:** Safety and signal outputs are versioned and testable.
- **Exit criteria:** Ranked opportunities and phases are explainable; score is not treated as an automatic buy.
- **Major risks:** Overweighting one signal, score gaming, unstable rankings.
- **Deliverables:** Opportunity records, phase states, ranking evaluation.

### P06 — AI DECISION ENGINE
- **Objective:** Produce bounded, evidence-backed trade intents with deterministic hot-path decisions.
- **Major components:** Deterministic rules, optional statistical/classical or bounded ML analysis, BUY, WATCH, HOLD, TAKE PROFIT, REDUCE, EXIT, AVOID, confidence, evidence, risk, invalidation, expected edge, uncertainty, entry quality, phase, NO TRADE, and point-in-time feature snapshots.
- **Dependencies:** P03, P05.
- **Entry criteria:** Opportunity records and risk context are available.
- **Exit criteria:** Decisions preserve time-of-decision evidence, separate intent from authorization and entry, and do not depend on an LLM.
- **Major risks:** Overconfidence, data leakage, hallucinated evidence, treating confidence as profit probability, and analysis latency.
- **Deliverables:** Versioned decision records and evaluation criteria.

### P07 — PAPER TRADING ENGINE
- **Objective:** Test decisions with realistic simulated execution.
- **Major components:** BUY and SELL simulation, fees, spread, slippage, price impact, latency, liquidity, quote drift, priority fees, MEV effects, failed execution, partial fills, positions, exposure, and reconciliation.
- **Dependencies:** P05, P06.
- **Entry criteria:** Decisions are auditable and execution assumptions are explicit.
- **Exit criteria:** Paper results include frictions and support reproducible simulation.
- **Major risks:** Perfect-fill assumptions, simulation mismatch, misleading performance.
- **Deliverables:** Paper ledger, simulator, reconciliation, performance reports.

### P08 — OUTCOME LEARNING
- **Objective:** Learn from decisions and outcomes without uncontrolled strategy changes.
- **Major components:** Read-only analysis of wins/losses, missed opportunities, avoided losses, expectancy, drift, regime/strategy/feature/decision/entry/exit performance, immutable point-in-time snapshots, production/challenger models, walk-forward validation, and controlled promotion.
- **Dependencies:** P06, P07.
- **Entry criteria:** Sufficient historical decision and outcome records exist.
- **Exit criteria:** Learning is validated against bias and cannot self-modify production uncontrolled.
- **Major risks:** Overfitting, look-ahead, regime/survivorship bias, feedback loops.
- **Deliverables:** Outcome dataset, evaluation reports, controlled model versioning.

### P09 — DEX / JUPITER EXECUTION
- **Objective:** Add provider-agnostic controlled execution only after prior validation and explicit go-live approval.
- **Major components:** Decision intent → Risk/Capital Authorization → Execution Request → isolated signing boundary → broadcast, provider-agnostic RPC/routing/MEV interfaces, BUY and SELL pre-flight, quote/route validation, slippage/price guards, latency budgets, submission, confirmation, failure handling, wallet state, reconciliation, stale-decision rejection, independent Exit Monitor, watchdog, and emergency stop.
- **Dependencies:** P01–P08 and explicit go-live approval.
- **Entry criteria:** Paper evidence demonstrates measurable executable edge after frictions.
- **Exit criteria:** Controlled execution is auditable and all safety gates pass.
- **Major risks:** Real-money loss, stale quotes, failed transactions, key compromise.
- **Deliverables:** Execution interfaces, venue adapters, controls, audit trail.

### P10 — LIVE SMALL-CAPITAL VALIDATION
- **Objective:** Validate under tightly bounded real conditions.
- **Major components:** Hard capital/position/correlated-exposure/loss limits, emergency stop, independent watchdog, logging, manual oversight, reconciliation, and multi-dimensional readiness evidence.
- **Dependencies:** P09.
- **Entry criteria:** Execution controls and paper evidence meet explicit thresholds.
- **Exit criteria:** Small-capital results and operational evidence support or reject scaling.
- **Major risks:** Losses, operational drift, liquidity/latency surprises.
- **Deliverables:** Controlled validation report and go/no-go decision.

### P11 — RAILWAY / 24x7 PRODUCTION
- **Objective:** Provide stable production runtime only when 24/7 operation is justified.
- **Major components:** Dashboard/API, scanner, market-data, signal, decision, risk, execution, learning workers, PostgreSQL, optional justified Redis.
- **Dependencies:** P10, operational runbooks, security review.
- **Entry criteria:** Stable validated system and genuine 24/7 need.
- **Exit criteria:** Monitored, recoverable, secure production operation.
- **Major risks:** Worker drift, outages, unsafe deployment, cost/scale issues.
- **Deliverables:** Production services, monitoring, recovery, deployment runbooks.

### P12 — OPTIMIZATION & EXPANSION
- **Objective:** Expand only after the core system is proven.
- **Major components:** Other chains/DEX venues, improved ML, wallet/social intelligence, latency, scaling, redundancy.
- **Dependencies:** P11 evidence and explicit prioritization.
- **Entry criteria:** Core reliability and edge are established.
- **Exit criteria:** Each expansion has isolated evidence and rollback.
- **Major risks:** Complexity, correlation of failures, diluted focus, new attack surface.
- **Deliverables:** Individually validated expansions.

## Global gates

- Opportunity score never automatically means BUY.
- Decision confidence is not a guaranteed probability of profit.
- Real-money autonomous trading is disabled until the validation gates are met.
- The Risk Governor may ALLOW, REDUCE, BLOCK, or EMERGENCY STOP.
- Hard risk checks support PASS, FAIL, and UNKNOWN; UNKNOWN never becomes PASS.
- Every decision must be reproducible from point-in-time information available at decision time.
- Pre-flight BUY and SELL simulation is required before an initial BUY whenever technically possible; failure means NO TRADE.
- The Decision Engine produces intent only and never owns keys, signs, or broadcasts.
- On-chain state must be reconciled with internal state before subsequent decisions.
- Learning is read-only until controlled review approves a versioned change.
- No fixed trade count or win-rate target authorizes live trading.
- Failure to demonstrate durable risk-adjusted edge permits STOP, PAUSE, or a market change.
