# Post-Operator Controlled-Paper Dependency Review

**Checkpoint:** `main` `b059c26e4a55bd72897385a19916573e565b99b9` after PR #126.
**Status:** BOUNDED REPOSITORY AUDIT COMPLETE / CONTROLLER AUTHORITY DECISION REQUIRED FOR AUTONOMOUS PAPER.
**Scope:** documentation and owner-path analysis only. No provider request, operational smoke, worker, scheduler, API, wallet or execution.

## What is already closed

The explicit controller-selected path has authenticated readiness and no-I/O payload validation, an approved bounded Solana prepare, exact case review, run once through CIP/OCI/OSC, separate persist once, and durable RTI-03 readback. The single-process launcher and fail-closed smoke harness cover the current controlled-paper scope. `docs/P01-OAF-01-PROVIDER-BACKED-SMOKE-EXECUTION-PACKET.md` describes the separately authorized operational test; PR #126 closes offline preparation, **not** the provider-backed smoke itself. Root `.replit` autoscale is not a qualifying process-local runtime.

## Smallest missing autonomous paper composition

| Stage | Existing owner | Missing decision before autonomous use |
| --- | --- | --- |
| Discovery | P02-T03/T04/T05/T06 admission and universe materialization; bounded Solana JSON-RPC owner validates a **selected** mint for prepare | Approved candidate event/source, event time, ordering/continuity, universe currentness, bounded acquisition cadence and de-duplication. DexScreener latest profiles are NOT_ADMITTED; one selected mint is not autonomous discovery. |
| Selection | Operator currently selects candidate, exact token and pool for OAF/RTI-11 | An explicit paper-only selection policy and accountable authority for selecting one exact candidate/pool. No implicit highest-score selection or client-asserted provenance. |
| Safety and market | P03-T01/T02/T03, RTI-11/P04-LME-03, canonical P04/P05 owner chain | Define when independently admitted observations are usable and their freshness, identity and conflicts for a selected candidate. Existing bounded owners do not authorize repeated source calls. |
| Decision and risk | P06 decision and independent Risk/Capital Authority precede P07 paper admission | Define how a paper-only controller-directed intent can be formed and how the independent Risk Governor can refuse it, without bypass or real capital/execution semantics. |
| Paper run and persistence | Explicit OAF prepare/review/run-once/persist-once, CIP/OCI/OSC, RTI-03 | New authority for any unattended trigger, service identity, scheduling, bounded cycle state and failure/resumption semantics. Browser bearer authentication and process-local opaque handles are not an unattended service credential or durable queue. |

**Recommended next specification gate:** a single **paper-only, one-cycle composition contract** around already owned stages, with a separately selected approved discovery source and exact candidate/pool selection rule. Specify trigger ownership, service authentication, source budgets and clock/freshness, per-candidate stop, Risk Governor veto, exactly which OAF steps are allowed without human confirmation, process-local/durable boundaries, deterministic no-provider fixtures and finite terminal outcomes. Do not implement a scheduler, continuous monitor, retries or unattended OAF mutation until that specification and any source/authority decision receive separate controller authorization. The existing controlled operator path remains usable as documented; this review does not reinterpret its bearer credential as autonomous authority.

## Other bounded workstreams

- **P03 formal closure:** T01–T03 evidence, evaluation and eligibility contracts are implemented, but the phase objective in `docs/MASTER_BLUEPRINT.md` includes broader liquidity, holder, developer, manipulation, tradability and exit-risk coverage. No phase-complete claim follows from those three contract tasks; a scoped phase-exit coverage decision and then an authorized missing domain/source specification are required.
- **P04 formal closure:** T01–T10 and P04-LME-01/02/03 own substantial deterministic evidence and price-direction work. `docs/P04-T09_SPECIFICATION.md` limits current feature calculation to price velocity/acceleration and explicitly defers volume, transactions, liquidity, wallet/social, volatility and regime features. Closing the whole phase requires a coverage decision or explicit scope revision; this audit changes neither contract nor `docs/MASTER_BLUEPRINT.md`.
- **G2:** `docs/P08-G2-REALIZATION-ENDPOINT-BOUNDARY-DISCOVERY.md` requires an owner-approved external settlement fact and endpoint with identity/finality/correction policy. G1/paper finality is not settlement. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.
- **Deployment:** `scripts/operator_single_process_runtime.py` provides explicit APP_ENV matching and one worker/no reload. No proven repository-only blocker remains for a qualifying local/VM *controlled* paper smoke; a stable host, connected database, intentionally provisioned secrets, exact selected payload and separate operational provider-call authorization are still necessary. No paid-host or restart-safe claim is made.

## Controller decision packet

1. **Authorize the narrow paper-only one-cycle composition specification** and select a specific discovery source/event authority and candidate/pool policy. This is the shortest path toward autonomous paper, but does not itself authorize source calls, a worker or automatic action.
2. **Authorize a bounded P03/P04 phase-exit coverage specification first.** This clarifies omitted risk/feature domains before unattended selection, but defers autonomous composition.
3. **Retain the current controlled-paper scope** until the separately authorized provider-backed smoke is performed in a qualifying environment. This validates the existing path but does not close autonomous discovery.

A decision must name the permissible paper trigger and source/selection authority before runtime development. This review selects option 1 as the next *specification* candidate based on reuse of the closed OAF chain, subject to controller authorization. It does not treat generic development authorization as permission for new provider calls, autonomous selection, scheduler, worker, wallet/signing, RPC/DEX execution, settlement, live trading or G2/G3/G4/P09.
