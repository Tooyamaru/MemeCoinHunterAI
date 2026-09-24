# Post-P01-OSP-01 Controlled Input Path — Dependency Decision

**Status:** BOUNDED DEPENDENCY REVIEW COMPLETE / CONTROLLER DECISION REQUIRED / NO SUCCESSOR SPECIFICATION SELECTED

**Baseline:** GitHub `main` `9d0773a2d0bd82180001c0a8fa1e899fd88e1dd5`; OSC-01 and OSP-01 COMPLETE / CLOSED / CI PASS; implementation PR #50 and closure PR #51 merged. G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 NOT AUTHORIZED.

**Question:** Can an application composition prepare one *complete* `P01Osc01Request` from existing supervised discovery, market, safety, and opportunity capabilities without making up paper fill or lifecycle facts?

## Available bounded owners

| Responsibility | Exact existing owner | What the controller still supplies |
| --- | --- | --- |
| Token universe, point-in-time market predecessor | P02-T04–T09, especially P02-T06 and `P02T07PredecessorContext` | One current candidate and its exact predecessor; no selection from a ticker or autonomous discovery policy |
| Safety and analytical eligibility | P03-T02 `SafetyEvaluationResult` and P03-T03 `DerivedEligibilityOutput` | The *paired*, already evaluated canonical handoff; RTI-11 validates rather than recomputes it |
| Exact pool OHLCV diagnostic and price-direction signal | P04-LME-01 source/policy, LME-02 one bounded transport attempt, LME-03 exact-target orchestration | Exact `ExactPoolDiagnosticTarget`, source reference, cutoff, timeout, size and freshness policy; the provider observation is conditional, not guaranteed |
| Signals/features and P05-T01–T05 opportunity | Existing `produce_canonical_p04_to_p05` invoked by RTI-11 | Candidate ID, explicit processing/evaluation times and optional bounded analytical context |
| RTI-11 canonical result | `MarketToOpportunityCompositionService.compose(P01Rti11CompositionRequest)` | All request facts above; at most one LME-03 diagnostic and, only on success, one P04/P05 producer call |
| OSC-ready request and paper chain | `P01Osc01Request`; `OneShotControlledPaperCaller.run` owns RTI-12–16 delegation | Invocation ID, exact RTI-11 result, ruleset, decision time, policy snapshot, execution observation, simulation configuration, initial state, replay identity, **fill instruction and lifecycle evidence** |

An OSC invocation consumes an **already-produced** RTI-11 result. A preparatory path may delegate to RTI-11 once, but must not also let OSC call RTI-11. RTI-11 is the only owner that invokes LME-03 and the canonical P04/P05 producer; no second market or opportunity evaluation is appropriate. A non-`COMPOSED` RTI-11 outcome cannot be promoted to an OSC-ready successful opportunity by a wrapper. Malformed canonical inputs and identity/version/time mismatches remain validation failures; owner outcomes remain the owners' outcomes. Neither OHLCV's observed close nor its signal provides a fill price, executable liquidity, fee/friction, inventory, or execution-time fact.

## Material missing provenance: fill and lifecycle

`PaperFillInstruction` is a canonical **input type**, not an evidence acquisition owner. It requires caller-owned side, quantity and units, executable liquidity, reference quote price, quote observation time, optional fill time, friction, quote currency, and optional inventory. `evaluate_paper_fill` (P07-T02) evaluates these *supplied hypothetical facts* after P07-T01 input exists; it does not acquire, authorize, or source them. The one-shot P04 OHLCV diagnostic provides historical candles and a price-direction signal, not a quote or fill instruction for this purpose.

`PaperLifecycleEvidence` likewise validates supplied prior exposure state, asset identity, valuation observations, accounting context, lifecycle reference time, ledger stream, sequence and predecessor digest, and independent reconciliation expectation. RTI-02 consumes it to run P07-T02–T07. P07-T05 compares an independently supplied expectation; it does not invent that expectation or establish external settlement truth. No bounded production owner in the reviewed path sources and binds all these facts to the selected candidate/pool and intended paper experiment.

The only convenient construction helpers found for both types are `_instruction` and `_evidence` in `tests/test_controlled_paper_lifecycle.py`. They use fixed simulated quantity/price/liquidity and test-built valuation, accounting, ledger, and reconciliation material. The test computes a ledger to construct an expectation; promoting this fixture pattern into production would manufacture provenance and compromise the independence of reconciliation. These helpers are evidence of test feasibility, **not** an authorized input source.

Other explicit OSC inputs also remain controller responsibilities: `DecisionEvaluationRuleset`, `decision_time`, scoped `PaperRiskCapitalPolicySnapshot`, `ExecutionObservation`, `SimulationConfigurationIdentity`, `InitialPaperStateIdentity`, and `ReplayIdentity`. An input-preparation service could verify their exact identity and time linkage, but it cannot silently derive policy, capital, fill, or lifecycle facts from market candles.

## Time, identity, failure and STOP constraints for a later specification

- Controller chooses/approves the exact P02 candidate and exact pool target before any LME-02 credential or HTTP access. P02 current membership, P03 chain/token pair, RTI-11 target, policy scope, execution subject, paper asset and replay identities must remain linked using existing owner invariants. A symbol or matching digest alone is not source authority.
- Reference time is the pre-request closed-minute cutoff. P04-LME-02 owns request/receipt clocks; RTI-11 requires explicit processing and evaluation times and a freshness policy. OSC decision time must respect its RTI-11 opportunity reference. Quote observation/fill time and lifecycle reference/valuation/accounting times belong to independently supplied paper facts; no wall-clock default may fill them.
- A later composition, if authorized, must prevalidate all exact canonical supplied objects before side effects, preserve the exact RTI-11 result and provenance, and bind any new invocation identity without altering owner digests. RTI-11, LME-03, its producer, and each OSC owner may execute at most once in the relevant single invocation. No RTI-04 or OSP-01 call belongs to this input-preparation boundary.
- The successful preparation STOP would be an exact validated `P01Osc01Request` containing an exact RTI-11 result and **explicitly supplied canonical** fill/evidence. Non-composed market outcomes stop earlier with exact owner reasons; malformed input is a validation failure. Whether a preparation owner should itself invoke OSC is a separate operational-caller decision. No new ordinary outcomes are selected in this review.

## Controller decision required

The present repository supports a narrow, honest *thin assembly* **only if** the controller or another independently governed source already provides canonical `PaperFillInstruction`, `PaperLifecycleEvidence`, and all other explicit OSC inputs. That option reduces constructor wiring but leaves the hardest manual fact sourcing unresolved; it cannot claim complete supervised paper hunting from discovery/market/safety data alone.

Before writing a formal complete-input-path specification, the controller must choose one of these boundaries:

1. **Explicit-facts-only composition:** the controller supplies both complete canonical paper objects with documented source/provenance and approves one candidate/pool. Specify only validation and bounded RTI-11-to-OSC-request assembly; no auto-generated paper facts. This is a smaller usability improvement.
2. **Separate paper-fact sourcing capability:** first decide authoritative *simulation-only* owners and policies for quote/liquidity/friction/fill time, prior state, valuation/accounting, ledger sequencing, and an independently grounded reconciliation expectation. This requires additional domain design and explicit approval; OHLCV cannot stand in for these facts.
3. **Upstream-only preparation:** stop at a canonical RTI-11 result with supervised candidate/pool and P03 handoff. Defer the claim of a complete OSC-ready experiment until paper-fact sourcing is decided.

No option is selected here, no identifier or formal successor specification is assigned, and no implementation authority is granted. No autonomous selection/ranking, polling, loop/retry, scheduler/worker/queue, persistence or replay archive, P08 wiring, wallet/signing/RPC/DEX, economic realization, execution, or live trading follows. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.
