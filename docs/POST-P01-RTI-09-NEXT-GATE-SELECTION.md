# Post-P01-RTI-09 Next-Gate Selection

**Status:** direction approved / superseded by the controlling P01-RTI-10
reconciliation document

**Verified baseline:** `main` and `origin/main` at
`1d10df723757a46684a1ccc229606daf7fafe27c` on 2026-09-23; worktree clean
before this documentation checkpoint; P01-RTI-09 complete / closed / CI pass.

## 1. Selection boundary

This checkpoint selects and outlines one prospective bounded gate. It does not
authorize implementation.

P01-RTI-03 through P01-RTI-09 remain closed. G2 remains blocked / unresolved /
not authorized. G3, G4, P09, provider runtime, worker, scheduler, queue, wallet,
execution, live trading, dashboard, public deployment, and new economic
authority remain outside this selection.

## 2. Current surface assessment

### 2.1 Read-only lifecycle surface

The lifecycle read surface is sufficiently complete for its current governed
purpose:

1. RTI-05 provides exact-digest application lookup through the RTI-03 read
   owner.
2. RTI-06 provides the bounded detail `GET` transport.
3. RTI-07 provides deterministic digest-only keyset paging.
4. RTI-08 provides the bounded collection `GET` transport.
5. RTI-09 locks the combined route, OpenAPI, schema, status, safe-error,
   request-ID, no-store, owner-isolation, and forbidden-operation contract.

No repository evidence establishes a current consumer need for lifecycle
filtering, search, latest/history semantics, richer projection, analytics,
conditional caching, retention, or mutation. Adding those now would create new
semantics rather than close a demonstrated integration gap.

### 2.2 Upstream market-to-opportunity surface

The repository now contains more upstream capability than several older
readiness statements acknowledge:

- P04-LME-01 selects CoinGecko Demo Onchain pool OHLCV as the bounded V1
  historical price-evidence source and defines `price-direction-v1`.
- P04-LME-02 owns one bounded server-side read-only HTTP attempt and diagnostic.
- P04-LME-03 owns caller-directed, one-shot orchestration for one admitted
  candidate and exact pool.
- the canonical evidence producer consumes validated P02/P04 inputs and
  composes the existing P04/P05 chain;
- P05-T08 provides the approved opportunity context consumed by P06.

However, `PROJECT_STATE.md` and `docs/HYBRID_DEVELOPMENT_WORKFLOW.md` still
contain older statements that the historical source and market-to-signal
policy are unresolved. Those statements conflict with the later accepted
P04-LME-01 through P04-LME-03 decisions. Other text correctly says the next
P04 step is separately authorized application/runtime composition. The
repository therefore needs one authoritative reconciliation before that step
can be scoped safely.

The unresolved G2 realization/settlement source is a different authority. It
must not be conflated with the bounded analytical P04 market-evidence source.

## 3. Official candidate assessment

| Candidate | Dependency readiness | Architecture sequencing | Boundedness | Determinism | Observability | Testability | Governance risk | Blast radius | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lifecycle filtering/search | Low: no governed vocabulary or consumer | Low after RTI-09 | Low-medium | Medium | Medium | Medium | High: creates secondary query authority | Medium-high | Defer |
| Lifecycle latest/history semantics | Low: no canonical temporal ordering policy | Low | Medium in code, weak in meaning | Low-medium | Medium | Medium | High: operational time may become domain truth | Medium | Defer |
| Lifecycle projection/analytics | Low: ownership and consumer absent | Low | Medium only if repeatedly narrowed | Medium | Medium | Medium | High: risks parallel integrity or economic interpretation | Medium-high | Defer |
| Lifecycle auth/rate limiting/deployment | Low: caller, quota, topology, and exposure policy absent | Premature before public exposure | Medium-low | Operational/stateful | High required | Medium | Medium-high | Medium-high | Defer; deployment remains ineligible |
| Retention/delete or command API | Low and mutation-bearing | Wrong sequence | Low | Medium | High required | Medium-low | High | High | Ineligible |
| Direct P04 application/runtime composition | Partial: component owners exist, but authoritative cross-document boundary is inconsistent | Potentially high after reconciliation | Low until invocation and side-effect ownership are locked | Medium | Medium-high | Medium | High | High | Blocked pending reconciliation |
| Provider polling, worker, scheduler, automatic pool selection, retry loop | Not authorized | Premature | Low | Low-medium | High required | Medium | High | High | Ineligible |
| Documentation-only lifecycle contract re-audit | High | Low incremental value: RTI-09 already proves it | High | High | High | High | Low | Very small | Available but not recommended |
| Cross-surface governance and upstream readiness reconciliation | High: all evidence is already in the repository | High: removes contradictions before any composition decision | High: documentation and contract inventory only | High | High: explicit authority/blocker matrix | High: evidence and consistency checks | Low | Very small | **Recommended** |
| G2/G3/G4/P09, wallet, execution, live trading, dashboard | Blocked or unauthorized | Outside this selection | Outside scope | Outside scope | Critical | Outside scope | Prohibited | Critical | Ineligible |

## 4. Recommended next bounded gate

### P01-RTI-10 — Cross-Surface Governance and Upstream Readiness Reconciliation

P01-RTI-10 should be a documentation-only reconciliation gate. It should
establish one current, non-contradictory authority and dependency map from the
accepted P04-LME boundaries through the canonical P04/P05 composition and
P05-T08 opportunity context, while recording that the lifecycle read surface
is complete enough and frozen at RTI-09.

This gate has the best sequencing value because it:

- corrects materially stale governance before code is authorized;
- distinguishes P04 analytical market evidence from blocked G2 economic
  realization/settlement evidence;
- makes the exact remaining application-composition gap reviewable;
- uses repository evidence only and adds no runtime behavior;
- prevents an implementation gate from inventing ownership across otherwise
  complete components; and
- preserves every prohibited boundary.

## 5. Specification outline for controller review

### 5.1 Purpose

Produce the authoritative post-RTI-09 readiness record for the next bounded
integration decision. Reconcile current documentation without changing code,
tests, contracts, or runtime behavior.

### 5.2 Inputs to reconcile

The gate should inspect and cross-reference only the current authoritative
materials for:

1. RTI-05 through RTI-09 lifecycle read ownership and closure;
2. P02-T06/P02-T09 candidate and market-intelligence identity;
3. P04-LME-01 source, temporal, identity, and signal-policy decisions;
4. P04-LME-02 one-shot transport ownership;
5. P04-LME-03 caller-directed orchestration ownership;
6. canonical P04-to-P05 evidence production;
7. P05-T08 opportunity-context handoff;
8. the separately blocked G2 realization/settlement authority; and
9. master governance exclusions for operational and economic boundaries.

### 5.3 Required outputs

The prospective gate should produce:

- one authority matrix naming the owner of source identity, candidate/pool
  identity, timestamps, transport, signal classification, P04/P05 composition,
  opportunity context, lifecycle reads, and G2 realization;
- one dependency/readiness matrix marking each link `CLOSED`, `READY FOR
  SEPARATE SPECIFICATION`, `BLOCKED`, or `NOT AUTHORIZED`;
- an explicit reconciliation of stale source/policy statements with the later
  accepted P04-LME decisions;
- a definitive statement that RTI-05 through RTI-09 need no immediate feature
  extension;
- an exact residual-gap statement for any later application composition;
- explicit stop conditions preventing provider runtime, polling, automatic
  selection, background processing, mutation, or economic authority; and
- one recommendation for the subsequent controller-reviewed gate, without
  authorizing or implementing it.

### 5.4 Determinism and evidence rules

- Every conclusion must cite repository-owned contracts or governed state.
- Later accepted decisions supersede stale descriptive text only where the
  ownership and scope match exactly.
- P04 analytical source authority must never be generalized into G2
  realization or settlement authority.
- An absent owner remains an explicit blocker; it must not be inferred.
- No live request or provider correctness claim is part of this gate.

### 5.5 Permitted file shape

Only governance/documentation files may change, expected to be limited to:

- the final P01-RTI-10 reconciliation specification or audit;
- `PROJECT_STATE.md`;
- directly contradictory current-governance text such as
  `docs/HYBRID_DEVELOPMENT_WORKFLOW.md`;
- `docs/CHANGELOG.md`; and
- `docs/MASTER_BLUEPRINT.md` only if its current status wording requires
  alignment.

No production code, test behavior, dependency, schema, migration, route,
provider adapter, worker, scheduler, queue, dashboard, wallet, execution, or
economic module may change.

### 5.6 Verification

The gate should require:

1. targeted cross-document consistency checks;
2. repository searches proving obsolete blocker wording is removed or
   explicitly historical;
3. link/path checks for every cited owner;
4. `git diff --check`;
5. review that no non-documentation file changed; and
6. no full runtime regression unless CI policy requires it for the resulting
   documentation-only pull request.

### 5.7 Stop conditions

Stop and return to controller review if reconciliation would require:

- a live provider call or provider-runtime correctness claim;
- a new application service, route, model, migration, or dependency;
- automatic token/pool discovery or selection;
- worker, scheduler, queue, retry, or polling behavior;
- mutation of paper lifecycle state;
- redefinition of RTI-03 through RTI-09 behavior;
- G2/G3/G4/P09, wallet, execution, settlement, or live-trading authority; or
- treating P04 price evidence as authoritative economic realization.

## 6. Controller decision required

This selection document did not itself authorize implementation. The
controller subsequently approved the documentation-only P01-RTI-10
reconciliation. Its controlling result is recorded in
`docs/P01-RTI-10-CROSS-SURFACE-GOVERNANCE-UPSTREAM-READINESS-RECONCILIATION.md`.
No subsequent gate starts automatically.
