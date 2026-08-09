# Master Blueprint

This document maps the system. It does not implement future phases.

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
- **Objective:** Produce bounded, evidence-backed decisions.
- **Major components:** BUY, WATCH, HOLD, TAKE PROFIT, REDUCE, EXIT, AVOID, confidence, evidence, risk, invalidation, expected edge, uncertainty, entry quality, phase, NO TRADE.
- **Dependencies:** P03, P05.
- **Entry criteria:** Opportunity records and risk context are available.
- **Exit criteria:** Decisions preserve time-of-decision evidence and separate decision from entry.
- **Major risks:** Overconfidence, hallucinated evidence, treating confidence as profit probability.
- **Deliverables:** Versioned decision records and evaluation criteria.

### P07 — PAPER TRADING ENGINE
- **Objective:** Test decisions with realistic simulated execution.
- **Major components:** Fees, spread, slippage, latency, liquidity, entry/exit realism, failed execution, partial fills, positions, exposure.
- **Dependencies:** P05, P06.
- **Entry criteria:** Decisions are auditable and execution assumptions are explicit.
- **Exit criteria:** Paper results include frictions and support reproducible simulation.
- **Major risks:** Perfect-fill assumptions, simulation mismatch, misleading performance.
- **Deliverables:** Paper ledger, simulator, reconciliation, performance reports.

### P08 — OUTCOME LEARNING
- **Objective:** Learn from decisions and outcomes without uncontrolled strategy changes.
- **Major components:** Wins/losses, missed opportunities, avoided losses, regime/strategy/feature/decision/entry/exit performance, immutable snapshots, production/challenger models, walk-forward validation.
- **Dependencies:** P06, P07.
- **Entry criteria:** Sufficient historical decision and outcome records exist.
- **Exit criteria:** Learning is validated against bias and cannot self-modify production uncontrolled.
- **Major risks:** Overfitting, look-ahead, regime/survivorship bias, feedback loops.
- **Deliverables:** Outcome dataset, evaluation reports, controlled model versioning.

### P09 — DEX / JUPITER EXECUTION
- **Objective:** Add controlled execution only after prior validation.
- **Major components:** Decision → Risk Governor → Execution Interface → Router → venue adapter, quote/route validation, slippage/price guards, submission, confirmation, failure handling, wallet state, reconciliation, stale-decision rejection, emergency stop.
- **Dependencies:** P01–P08 and explicit go-live approval.
- **Entry criteria:** Paper evidence demonstrates measurable executable edge after frictions.
- **Exit criteria:** Controlled execution is auditable and all safety gates pass.
- **Major risks:** Real-money loss, stale quotes, failed transactions, key compromise.
- **Deliverables:** Execution interfaces, venue adapters, controls, audit trail.

### P10 — LIVE SMALL-CAPITAL VALIDATION
- **Objective:** Validate under tightly bounded real conditions.
- **Major components:** Hard capital/position/loss limits, emergency stop, logging, manual oversight, reconciliation.
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
