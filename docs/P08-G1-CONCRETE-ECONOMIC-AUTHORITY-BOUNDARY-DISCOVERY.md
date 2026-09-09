# P08 — G1 Concrete Economic Authority Boundary Discovery

**Status:** COMPLETE / AWAITING EXPLICIT GOVERNANCE DECISIONS
**Phase:** P08 — Outcome Learning
**Boundary:** G1 — Concrete Economic Authority
**Audit type:** Documentation-only governance discovery
**Implementation status:** NOT AUTHORIZED

## 1. Scope and current governance position

This document records the unresolved governance problem that must be decided
before G1 can be specified. It does not select an economic model, define a
runtime contract, create an evidence authority, or authorize implementation.

The current approved position is:

```text
Authority A = closed identity/lifecycle authority; implementation not authorized
Authority B = closed correction/supersession lineage authority; implemented and audited
P07        = simulation-only; not economic truth
P08-T07    = closed economic interpretation/assembly boundary
G1         = unresolved concrete economic authority
G2         = blocked by G1
G3         = blocked by G1 and G2
G4         = blocked by G3
P09        = NOT AUTHORIZED
```

G1 in this discovery is the unresolved concrete economic authority that must
establish what economic fact or event is authoritative for a lifecycle. It is
not a reopening of Authority A, Authority B, P07, or the closed P08-T07
implementation.

## 2. Exact unresolved G1 problem

The project currently has deterministic identity, lineage, paper-simulation,
non-economic observation, evidence, snapshot, readiness, and T07 assembly
boundaries. It does not yet have an approved authority that answers this
question:

> For one already-identified economic subject and lifecycle, what explicitly
> observed event or state is authoritative enough to establish the concrete
> economic fact that downstream realization, accounting, and classification may
> use?

That question contains several unresolved distinctions:

- whether G1 recognizes an observation, execution/fill, economic cost,
  settlement, valuation, or a governed combination of them;
- whether recognition means that an event occurred, that it is final, that it
  is economically attributable to the lifecycle, or all of those separately;
- whether the authority is simulation-only, external-settlement-aware, or
  another explicitly governed model;
- what source, authority, evidence, and provenance make the fact admissible;
- how the fact is linked to the Authority A subject and lifecycle without
  redefining them;
- how incomplete, contradictory, corrected, superseded, late, reversed, or
  reorg-affected evidence is represented; and
- what exact endpoint permits G2 to evaluate realization eligibility.

No existing boundary can answer these questions without exceeding its approved
authority. G1 must therefore be resolved as a separate governance boundary
before G2, G3, or G4 can be specified.

### 2.1 Why the current boundaries cannot solve G1

| Boundary | What it authoritatively owns | Why it cannot solve concrete G1 |
|---|---|---|
| Authority A | Canonical Economic Subject Identity, Lifecycle Identity, lifecycle mapping, equivalence, split, and mapping conflicts | It identifies what lifecycle is represented. It does not assert that an economic event occurred, that value was realized, that settlement is final, or that evidence is economically admissible. |
| Authority B | Immutable correction and supersession lineage facts for established result identities | It establishes relationships between results. It does not establish execution, settlement, realization, accounting, valuation, or classification. |
| P07 | Provider-neutral paper simulation, fills, paper state, ledger, reconciliation, and finalized non-economic paper result | Paper execution is explicitly not economic truth. It cannot establish external execution, settlement, realized cost, or realized P&L. |
| P08-T07 | Deterministic interpretation and assembly of validated G2/G3/G4 results for one lifecycle | T07 consumes authoritative upstream economic results. It must not collect raw evidence, infer missing facts, repair evidence, or create G1 authority. |
| G2 | Future realization eligibility and the governed endpoint for a realized outcome | G2 is downstream of the decision about which concrete event or evidence G1 recognizes. Without G1's authoritative fact and finality semantics, G2 has no approved realization basis. |
| G3 | Future accounting and canonical economic-result calculation over admissible realized inputs | G3 requires G1/G2-authorized events, quantities, costs, settlement semantics, numeraire, and accounting basis. It cannot decide its own upstream economic truth. |
| G4 | Future performance classification supplied from authoritative G3 results | G4 can classify only after G3 supplies a valid canonical economic result. It cannot decide whether an event was economically real or final. |
| P09 | Separately governed live execution chain | P09 is not authorized and cannot be used to define G1. Execution, wallet, custody, signing, broadcast, and reconciliation remain prohibited here. |

## 3. Current ownership map

### Authority A — canonical subject and lifecycle identity

Authority A owns the semantic identity of the canonical economic subject and its
lifecycle. It owns lifecycle equivalence, mapping, authorized split facts, and
lifecycle mapping conflict resolution. It must remain independent from
realization, settlement, accounting, classification, lineage, custody, and
execution.

Authority A answers **which subject and lifecycle are being represented**. It
does not answer **which economic fact occurred or became final**.

### Authority B — correction and supersession lineage

Authority B owns explicit immutable correction and supersession facts between
already-established result identities. It preserves lineage provenance and
fails closed on invalid, contradictory, branching, cyclic, or ambiguous
lineage. It consumes Authority A lifecycle identity and must not redefine it.

Authority B answers **how authoritative result records relate**. It does not
answer **whether the underlying economic event or settlement is real**.

### G1 — unresolved concrete economic authority

G1 must be the separately governed authority that answers what concrete
economic event, state, or finality condition is recognized for a lifecycle. Its
scope, evidence, source authority, temporal semantics, output states, and
prohibitions are unresolved and require explicit owner decisions below.

G1 must not be assumed to be a provider integration, wallet boundary, ledger,
accounting engine, classifier, or execution system. Those are separate choices
that require explicit authorization.

### G2 — realization eligibility

G2 is a downstream authority that determines whether the G1-governed economic
facts satisfy the conditions for a realized outcome. It must distinguish
non-final, pending, unavailable, invalid, and realized states according to its
own approved contract. G2 cannot invent the G1 event, source, finality rule, or
economic subject.

### G3 — accounting and economic result

G3 is a downstream authority for canonical economic accounting and result
construction. It must receive admissible G1/G2 facts and an approved
accounting basis. G3 cannot silently choose settlement authority, cost basis,
fee treatment, conversion, precision, rounding, or missing-evidence recovery
on behalf of G1.

### G4 — performance classification

G4 is a downstream authority for the approved classification vocabulary and
deterministic classification rule over valid G3 results. G4 cannot turn
simulation status, readiness, an observation, or an unresolved result into
`WIN`, `LOSS`, or `BREAKEVEN`.

### T07 — economic interpretation and assembly

T07 validates and assembles supplied G2, G3, and G4 results for one lifecycle.
It preserves their identities, policy versions, digests, provenance, and
Authority B lineage. T07 does not collect raw economic evidence or establish
the G1 fact. Its authority effect remains `NONE` with respect to execution and
capital.

### P09 — unauthorized execution chain

P09 remains a separate future chain:

```text
Decision Intent
→ Risk / Capital Authorization
→ Execution Request
→ isolated Signing
→ Broadcast
→ Reconciliation
→ Journal
```

P09 is not a source of G1 authority and remains **NOT AUTHORIZED**.

## 4. Minimum governance decisions required from the project owner

The following questions must be answered before an implementation-ready G1
specification can be drafted. They are decision questions, not defaults. This
document intentionally does not answer them.

### 4.1 Economic subject and recognized event

**G1-01 — What exact economic subject does G1 recognize?**

Is it the already-established Authority A canonical economic subject, a
decision/trade lifecycle, an externally settled position, an account-level
economic claim, or another explicitly named subject?

**G1-02 — What exact event or state does G1 authoritatively recognize?**

Must G1 recognize an observation, an external execution/fill, an economic cost,
a settlement, a valuation, a completed lifecycle, or a defined combination
with separate event types?

**G1-03 — What does “recognized” mean?**

Does recognition assert that an event was observed, that it occurred, that it
is attributable to the lifecycle, that it is final, or that it is admissible
for downstream economic interpretation? Must these meanings be separate
states?

**G1-04 — What is the lifecycle cardinality?**

Can one lifecycle contain multiple observations, fills, costs, settlements,
partial fills, reversals, and valuations? Can one event belong to multiple
lifecycles, and if so, what explicit authority and allocation rule permits it?

### 4.2 Finality and authoritative observation conditions

**G1-05 — What conditions make a lifecycle or event final?**

Is finality based on settlement, an external confirmation state, a fixed
observation condition, a governed close event, a manual attestation, or
another rule?

**G1-06 — Can an open, partially filled, cancelled, failed, reversed, or
otherwise incomplete lifecycle be G1-authoritative?**

If yes, what state is emitted and what downstream authority may consume it? If
no, which explicit fail-closed state is required?

**G1-07 — How are chain reorganizations, transaction replacement, reversals,
chargebacks, or other external invalidations handled, if relevant?**

What event or authority can change finality, and does that create a correction,
supersession, invalidation, or new lifecycle fact?

### 4.3 G1 operating model

**G1-08 — Is G1 simulation-only, external-settlement-aware, or another
explicitly governed model?**

May G1 recognize paper simulation as a distinct non-economic observation only,
or may it consume external execution/settlement evidence? If multiple modes
exist, are they separate contracts and authorities?

**G1-09 — If external-settlement-aware, what exact external authority is
allowed?**

May the authority be a provider, chain/RPC observation, venue record, wallet
record, custodian, account ledger, manual attestation, or a future
provider-neutral evidence adapter? Which authority is authoritative when they
disagree?

**G1-10 — Is valuation in G1?**

If valuation is allowed, is it explicitly distinct from execution, settlement,
realized economic result, and classification? What authority, timestamp,
horizon, price basis, and stale-data rule govern it?

### 4.4 Identity, lifecycle, and lineage relationship

**G1-11 — How must G1 link its fact to Authority A?**

Which Authority A canonical subject and lifecycle identities are required, and
which fields are linkage-only rather than part of G1 semantic identity?

**G1-12 — Can G1 create, split, merge, or redefine a lifecycle?**

If no, how must G1 fail when event grouping disagrees with Authority A? If a
split or merge is ever allowed, which explicit authority owns that fact and
how does it remain separate from event grouping?

**G1-13 — How must G1 relate to Authority B lineage?**

Does a corrected or superseded G1 fact create a new G1 result, an Authority B
lineage fact, both, or another governed record? Which authority owns the
correction assertion, and how is historical identity preserved?

**G1-14 — Can G1 facts refer to T07 results?**

If so, are result references linkage-only, and how is circularity prevented so
that a G1 fact does not derive its own identity from a T07 result that already
depends on that fact?

### 4.5 Relationship to G2 realization eligibility

**G1-15 — What exact G1 output does G2 consume?**

Does G2 consume an event, a finality assertion, a lifecycle state, an
evidence packet, a canonical G1 result, or several explicitly separated
records?

**G1-16 — What is G1's responsibility versus G2's responsibility?**

Which boundary determines that an event is authentic and attributable, and
which boundary determines that the lifecycle satisfies realization
eligibility? Where does settlement finality stop and realization eligibility
begin?

**G1-17 — Can G2 use G1 observations without settlement?**

If yes, under what non-realized state and with what prohibition against
producing realized P&L or classification? If no, what evidence is mandatory?

### 4.6 Evidence, authority, and provenance

**G1-18 — What evidence is authoritative for each event type?**

Which evidence is required for observation, execution/fill, cost, settlement,
valuation, cancellation, reversal, and finality?

**G1-19 — What source and authority metadata are mandatory?**

Which source identity, source version, authority identity, policy version,
observation timestamp, event timestamp, finality timestamp, and integrity
digest must be preserved?

**G1-20 — What is the conflict rule for multiple sources?**

Is there an approved source hierarchy, quorum, corroboration rule, or explicit
unresolved-conflict state? May G1 ever prefer one source by freshness,
insertion order, magnitude, or caller preference?

**G1-21 — What provenance chain must G1 preserve?**

Which P06, P07, P08-T01 through P08-T06, Authority A, Authority B, external
evidence, and downstream references are required, optional, or prohibited?

**G1-22 — What evidence is missing versus invalid versus unavailable?**

Must these be distinct public states, and which states may be consumed by G2,
G3, G4, or T07?

### 4.7 Correction, supersession, contradiction, and finality

**G1-23 — What is the correction rule?**

When an authoritative G1 fact is wrong or incomplete, is it immutable and
replaced by a new fact, and does Authority B carry the correction lineage?

**G1-24 — What is the supersession rule?**

Can a later fact replace the current G1 representative without asserting that
the predecessor was erroneous? How is that distinct from correction?

**G1-25 — What is the contradiction rule?**

Which conflicts fail closed immediately, which can remain unresolved, and
which authority may resolve them? Is there any permitted source precedence?

**G1-26 — Can a final fact be reopened?**

If finality can be withdrawn, is that represented as correction,
supersession, invalidation, reversal, or a new lifecycle? What remains
immutable?

### 4.8 Temporal, cutoff, and replay semantics

**G1-27 — What timestamps and temporal roles exist?**

Which of event time, observation time, source time, settlement time, finality
time, reference time, cutoff time, and ingestion time are allowed, and which
may affect identity or validity?

**G1-28 — What is the authoritative cutoff or outcome horizon?**

Is G1 current-state based, event-time based, settlement-time based,
as-of-cutoff based, or governed by another horizon? How does this remain
separate from future AEA analytical as-of selection?

**G1-29 — How are late, corrected, superseded, and future-dated facts handled?**

Must they be rejected, retained as non-final, represented as new immutable
facts, or handled by another explicit state machine?

**G1-30 — What replay invariant is required?**

Which explicit inputs must reproduce the same G1 identity, canonical bytes,
digest, validity, finality, and failure state regardless of retrieval order,
provider timing, timezone, or later evidence?

### 4.9 Custody, account, wallet, and provider boundary

**G1-31 — Does G1 require account, custody, wallet, or provider state?**

If yes, which state is merely evidence and which authority asserts it? If no,
must all such state remain explicitly prohibited?

**G1-32 — Is wallet ownership or account ownership part of G1?**

If yes, which separately governed authority establishes it? If no, how must G1
represent events whose attribution depends on ownership?

**G1-33 — Is provider/RPC/DEX/network access allowed in G1?**

If yes, is access limited to a provider-neutral evidence adapter, and what
exact external truth and finality semantics are accepted? If no, what
explicitly supplied evidence replaces live access?

### 4.10 G1 output, canonicalization, and prohibitions

**G1-34 — What exact G1 result states and failure vocabulary are required?**

Which states distinguish observed, executed, settled, final, non-final,
unavailable, contradictory, invalid, corrected, and superseded facts?

**G1-35 — What exact fields, identity seed, canonical serialization, and digest
rules are required?**

Which fields define semantic identity, which are provenance-only, which are
nullable, how are collections ordered, and how are timestamps and economic
values represented without circularity?

**G1-36 — What must G1 explicitly prohibit?**

Must G1 prohibit paper simulation as economic truth, accounting, P&L, ROI,
classification, risk authorization, capital authorization, execution, wallet
access, signing, broadcast, provider access, persistence, learning, and P09?
Are any exceptions intended, and which separately authorized boundary owns
them?

## 5. Safe next governance sequence

No implementation or downstream phase should begin before the owner answers
the decision questions above and the answers are recorded as approved
governance.

The safe sequence is:

1. **G1 specification** — convert the explicit owner decisions into a bounded,
   immutable, deterministic, provider-neutral G1 contract with exact ownership,
   evidence, finality, identity linkage, temporal, canonicalization, failure,
   and prohibition rules.
2. **G1 specification audit** — audit the completed specification against
   Authority A, Authority B, P07, P08-T07, the security boundary, and the
   future G2/G3/G4 separation. Resolve every remaining ambiguity before
   implementation readiness.
3. **Separate G1 implementation authorization** — authorize only the exact
   approved G1 files and tests, with no implicit G2, G3, G4, P09, provider,
   wallet, persistence, or execution scope.
4. **G1 implementation and audit** — implement the authorized contract only,
   run focused and repository checks, and perform a separate implementation
   audit with explicit PASS/FAIL/BLOCKED findings.
5. **Only then G2 specification work** — specify realization eligibility over
   the audited G1 outputs. G2 must not be started merely because this
   discovery document is complete.

G3 accounting/economic-result specification remains downstream of audited G1
and G2 contracts. G4 classification remains downstream of audited G3.

## 6. Explicit prohibitions

Until the owner decisions, G1 specification, G1 specification audit, separate
implementation authorization, implementation, and implementation audit are
complete, this discovery authorizes none of the following:

- real-money behavior or live trading;
- wallet, custody, private-key, signer, signing, or broadcast behavior;
- provider, RPC, DEX, exchange, network, or external API behavior;
- settlement or external-finality integration;
- accounting, economic-result calculation, P&L, ROI, valuation, or
  performance metrics;
- `WIN`, `LOSS`, `BREAKEVEN`, or any other economic classification;
- Risk Governor decisions or capital authorization;
- execution requests or execution behavior;
- persistence, migrations, caches, queues, or database authority;
- AI/ML, strategy updates, model updates, or learning behavior;
- implementation or modification of Authority A;
- implementation or modification of Authority B;
- modification or redesign of P08-T07; or
- G2, G3, G4, G5, P08-T08, or P09 behavior.

No paper result, readiness result, identity, lineage fact, or documentation
status grants any prohibited authority implicitly.

## 7. Discovery conclusion

The unresolved G1 problem is now explicitly bounded: the project needs an
owner-approved authority for the concrete economic fact, event attribution,
admissibility, and finality conditions that downstream G2 may use. Existing
identity, lineage, simulation, interpretation, and downstream economic
boundaries cannot fill that gap without violating their approved ownership.

This discovery is complete, but G1 remains **AWAITING EXPLICIT GOVERNANCE
DECISIONS**. No implementation or economic authority was started.

P09 remains **NOT AUTHORIZED**.