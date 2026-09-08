# P08 — Canonical Economic Subject / Lifecycle Identity Authority

**Status:** SPECIFICATION DRAFT — IMPLEMENTATION NOT AUTHORIZED  
**Authority:** Authority A — Canonical Economic Subject / Lifecycle Identity Authority  
**Phase:** P08 — Outcome Learning  
**Scope:** Upstream semantic subject and lifecycle identity governance

This document specifies Authority A, the upstream semantic governance
authority for Canonical Economic Subject Identity and Lifecycle Identity.

It is specification-only. It does not authorize runtime code, persistence,
external access, tests, Authority B, CPA, AEA, Snapshot, P08-T08, or changes
to the closed P08-T07 implementation.

## 1. Purpose and Scope

Authority A answers:

> What canonical economic subject is represented by this lifecycle, and which
> lifecycle identity does it have?

Authority A owns the semantic governance contract for:

1. Canonical Economic Subject Identity;
2. Lifecycle Identity;
3. lifecycle equivalence;
4. lifecycle mapping;
5. Lifecycle Split Facts;
6. lifecycle conflict detection and resolution;
7. identity stability;
8. identity derivation;
9. authoritative identity facts and provenance;
10. deterministic replay;
11. identity correction and change semantics;
12. fail-closed ambiguity;
13. canonicalization and integrity validation; and
14. downstream consumption boundaries.

Authority A is a semantic governance authority. It is not merely:

- a serializer;
- a database lookup;
- an event grouper;
- an administrative identifier generator; or
- an implementation convenience layer.

Authority A does not create economic accounting, realization, classification,
performance, execution, or analytical semantics.

## 2. Approved Governance Baseline

The following decisions are already approved and are normative.

### 2.1 V1 economic subject

The V1 economic subject is a **Trade Lifecycle**.

### 2.2 Lifecycle anchor

A lifecycle is anchored by:

```text
P06 DecisionIntent Identity
+
Canonical Economic Subject Identity
```

### 2.3 Lifecycle identity seed

The lifecycle identity seed remains exactly:

```text
Canonical Economic Subject Identity
+
P06 DecisionIntent Identity
```

The following are not lifecycle identity inputs:

- `split_id`;
- `branch_id`;
- UUIDs;
- timestamps;
- sequences;
- database IDs;
- retrieval order;
- event IDs;
- observation IDs;
- T02 snapshot IDs;
- T06 result IDs; or
- arbitrary generated discriminators.

### 2.4 Cardinality

The normative V1 cardinality is:

```text
one lifecycle → exactly one P06 DecisionIntent

one P06 DecisionIntent → exactly one lifecycle by default

one P06 DecisionIntent → multiple lifecycles only through
an explicit authoritative Lifecycle Split Fact
```

Every resulting lifecycle still has exactly one P06 DecisionIntent.

### 2.5 Split identity rule

A valid Lifecycle Split Fact must authoritatively assert distinct resulting
Canonical Economic Subject Identities.

The resulting identities, together with the same P06 DecisionIntent Identity,
produce distinct Lifecycle Identities.

The Lifecycle Split Fact itself is mapping and provenance authority. It is not
part of the Lifecycle Identity seed and is not an arbitrary identity
discriminator.

If distinct resulting Canonical Economic Subject Identities cannot be
established, the mapping fails closed with:

```text
INVALID_LIFECYCLE_MAPPING
```

### 2.6 Event association

Events may be associated with an existing lifecycle.

Events must not create, split, merge, or redefine lifecycle identity. This
includes:

- executions;
- partial fills;
- accounting events;
- settlement events;
- corrections;
- observations;
- T02 grouping;
- T06 grouping;
- timestamps;
- retrieval order; and
- database ordering.

### 2.7 Identity stability

Lifecycle identity remains stable across:

- T02 snapshots;
- T06 recomputation;
- deterministic replay;
- ordering changes; and
- observation representation changes,

unless an authoritative lifecycle identity fact changes the mapping.

## 3. Canonical Economic Subject Versus Event

### 3.1 Canonical Economic Subject

A Canonical Economic Subject is the provider-neutral semantic economic unit
whose identity determines which economic lifecycle is being represented.

It is defined by the authoritative economic-subject facts supplied through
Authority A. It is not defined by the number, order, or grouping of observed
events.

A Canonical Economic Subject is not inherently:

- a transaction;
- a fill;
- an execution;
- a wallet event;
- an observation;
- a T02 snapshot;
- a T06 result;
- a provider event; or
- a database record.

Those artifacts may provide evidence, linkage, or provenance. They do not
define Lifecycle Identity by themselves.

### 3.1.1 Semantic governance boundary

Authority A governs the semantic question of which economic unit is being
represented. It does not govern the final serialization merely because a
serialization is used to carry the result.

For V1, the semantic boundary is:

1. **Subject-defining facts** are authoritative facts that establish the
   economic unit represented by the Canonical Economic Subject and establish
   whether two such units are the same or distinct.
2. **Lifecycle-anchor facts** establish the relationship between the subject
   and the P06 DecisionIntent Identity. The approved Lifecycle Identity seed
   remains exactly the Canonical Economic Subject Identity plus the P06
   DecisionIntent Identity.
3. **Mapping and correction facts** may establish, split, correct, or leave
   unresolved the relationship between supplied subject claims and lifecycle
   identities, but they do not permit an arbitrary discriminator to become
   subject identity.
4. **Evidence and provenance facts** support the authority, traceability, and
   replay of a semantic claim without defining the subject by themselves.

The first two categories determine semantic identity under the approved
governance baseline. The third category governs how that identity is mapped or
corrected. The fourth category documents the claim. The exact field names,
types, envelopes, and wire encoding for these categories are serialization
governance and remain specification dependencies.

Two representations are semantically the same subject when their validated
authoritative subject-defining facts resolve to the same Canonical Economic
Subject Identity. They are semantically distinct only when Authority A
authoritatively establishes distinct economic units and assigns distinct
subject identities. A representation that differs only in provenance,
observation, event, retrieval, storage, or administrative information is not
thereby a different subject.

### 3.2 Associated events

An event is an occurrence associated with an already-established subject or
lifecycle. Event association can preserve evidence about the subject but
cannot supply lifecycle authority merely because multiple events appear
related.

Event grouping must not be used as a substitute for:

- Canonical Economic Subject Identity;
- Lifecycle Identity;
- lifecycle equivalence;
- a Lifecycle Split Fact; or
- lifecycle conflict resolution.

### 3.3 Same versus distinct subject

Two representations refer to the same Canonical Economic Subject when their
validated authoritative semantic identity facts resolve to the same subject
identity.

Two representations refer to distinct Canonical Economic Subjects when
Authority A authoritatively establishes that their semantic economic units are
distinct and assigns distinct subject identities.

Similarity is not identity. Subject equality must not be inferred from:

- timestamp proximity;
- amount similarity;
- price similarity;
- provider-specific assumptions;
- database ordering;
- caller preference;
- event count; or
- retrieval order;
- event identity;
- observation identity;
- T02 identity;
- T06 identity; or
- administrative identifiers.

## 4. Canonical Economic Subject Identity

### 4.1 Meaning of subject identity

Canonical Economic Subject Identity represents the stable semantic identity of
the economic subject that a lifecycle describes.

It is an identity claim, not merely a record key. It must remain meaningful
across equivalent representations, observations, dataset snapshots, and
replay.

### 4.2 Identity-defining information

Identity-defining information is the authoritative semantic information that
determines whether two representations refer to the same economic subject.

Authority A must distinguish identity-defining information from:

- provenance;
- observation metadata;
- retrieval metadata;
- storage metadata;
- event ordering;
- T02 population membership;
- T06 readiness state; and
- implementation-generated identifiers.

Only information explicitly justified as semantically identity-defining may
participate in Canonical Economic Subject Identity.

### 4.3 Provenance-only information

The following may support or document an identity claim without defining the
identity itself:

- source identity;
- source version;
- observation identity;
- evidence identity;
- collection time;
- T02 snapshot identity;
- T06 result identity;
- provider event identity; and
- storage or retrieval metadata.

Provenance may be preserved in an identity fact or canonical representation.
It does not automatically become part of semantic identity.

### 4.4 Equality

Two subject identity claims are equal only when their validated,
identity-defining semantic content resolves to the same Canonical Economic
Subject Identity under Authority A.

Equivalent evidence must not create multiple subject identities.

Different representations of the same semantic subject must resolve to the
same identity when their authoritative identity facts are equivalent.

### 4.5 Distinctness

Distinct subject identities require an authoritative semantic basis for
distinctness. A generated branch label, sequence, UUID, timestamp, database
ID, or arbitrary ordinal is insufficient.

For a valid lifecycle split, Authority A must provide distinct resulting
Canonical Economic Subject Identities. The split fact authorizes and records
the mapping; it does not generate those identities.

### 4.6 Identity stability

Once an identity is established from an authoritative fact set, its historical
meaning and identity value are immutable for that fact set.

A later contradictory or corrective identity fact must not silently mutate
the historical identity or rewrite its prior representations.

Any later change is governed by Section 10 and must fail closed when the
applicable identity-correction policy cannot establish a deterministic result.

### 4.7 Unresolved identity

If Authority A cannot establish a single deterministic subject identity, the
subject mapping is unresolved. It must not be resolved using heuristics or
administrative ordering.

An unresolved subject identity cannot produce a valid Lifecycle Identity.

## 5. Lifecycle Identity

### 5.1 Derivation

The semantic derivation chain is:

```text
Canonical Economic Subject
        ↓
Canonical Economic Subject Identity

P06 DecisionIntent
        ↓
P06 DecisionIntent Identity

Both identities
        ↓
Lifecycle Identity
```

Formally:

```text
LifecycleIdentity =
    CanonicalEconomicSubjectIdentity
    +
    P06DecisionIntentIdentity
```

This describes semantic derivation, not a final serialized field layout.

### 5.2 Split derivation

For an authorized split:

```text
Authority A
        ↓
Authoritative Lifecycle Split Fact
        ↓
Distinct resulting Canonical Economic Subject Identities
        ↓
Distinct Lifecycle Identities
        ↓
T07 candidate results
```

The same P06 DecisionIntent Identity may participate in more than one
Lifecycle Identity only under the explicit split exception, and only when
every resulting lifecycle has a distinct authoritative Canonical Economic
Subject Identity.

The split fact itself does not participate in the Lifecycle Identity seed.

### 5.3 Stability

Lifecycle Identity must remain stable across:

- equivalent observation representations;
- T02 dataset snapshots;
- T06 recomputation;
- deterministic replay;
- ordering changes; and
- equivalent authoritative reassembly.

T01, T02, and T06 are linkage or provenance layers only and do not become
identity authorities through their presence in a lifecycle input.

## 6. Lifecycle Equivalence

Authority A must provide deterministic equivalence rules for:

- two observations representing the same lifecycle;
- two event groups associated with the same lifecycle;
- two candidate mappings representing the same lifecycle;
- two candidate mappings that must be distinct;
- insufficient identity evidence;
- contradictory identity evidence; and
- ambiguous identity evidence.

### 6.1 Same lifecycle

Two candidate mappings represent the same lifecycle when:

1. they resolve to the same Canonical Economic Subject Identity;
2. they reference the same P06 DecisionIntent Identity; and
3. no authoritative conflict or split fact establishes distinct subjects.

Equivalent evidence must not create multiple Lifecycle Identities.

### 6.2 Distinct lifecycle

Two candidate mappings are distinct when Authority A establishes either:

- distinct Canonical Economic Subject Identities; or
- an authoritative mapping conflict requiring separate lifecycle treatment.

The second case cannot create a valid lifecycle without a resolved identity
outcome. It must fail closed or be resolved through an explicitly authorized
Authority A identity fact.

### 6.3 Insufficient evidence

Evidence is insufficient when it does not establish the canonical subject,
P06 relationship, or required equivalence facts with deterministic authority.

Insufficient evidence must not be completed with heuristics.

### 6.4 Contradiction

Evidence is contradictory when authoritative identity claims cannot all be
true under the same subject and lifecycle mapping.

Contradictory identity claims fail closed unless an already-authorized
Authority A conflict-resolution rule produces a deterministic resolution.

### 6.5 Ambiguity

Evidence is ambiguous when more than one identity or mapping remains
consistent with the authoritative facts and no authorized rule selects one.

Ambiguity fails closed. Authority A must not select by timestamp, amount,
provider, insertion order, caller preference, majority vote, or result
magnitude.

## 7. Lifecycle Split Authority

### 7.1 Split fact purpose

A Lifecycle Split Fact establishes that one originating P06 DecisionIntent
maps to multiple resulting lifecycles because each resulting lifecycle
corresponds to a distinct authoritative Canonical Economic Subject Identity.

It does not:

- generate a subject;
- generate a branch identifier;
- add a split identifier to the lifecycle identity seed;
- convert event grouping into lifecycle authority; or
- authorize a split without distinct resulting subject identities.

### 7.2 Required semantic assertions

A valid Lifecycle Split Fact must establish:

1. the originating P06 DecisionIntent;
2. each distinct resulting Canonical Economic Subject Identity;
3. the mapping from the originating P06 to those subjects and lifecycles;
4. the authoritative reason or basis;
5. lifecycle mapping, equivalence, and conflict information;
6. fact identity; and
7. provenance.

The exact serialized fields and types remain a specification dependency. The
semantic obligations are fixed by this section.

### 7.3 Valid split

A split is valid only when:

- Authority A is the authoritative source;
- the originating P06 is identified;
- at least two resulting canonical subject identities are established;
- the resulting subject identities are distinct;
- each resulting lifecycle has exactly one P06;
- the mapping is internally consistent;
- the reason or basis is authoritative; and
- provenance is complete and verifiable.

### 7.4 Invalid split

A split is invalid when:

- the split fact is missing;
- the originating P06 is missing or inconsistent;
- resulting subject identities are absent;
- resulting subject identities are not distinct;
- the mapping is ambiguous or contradictory;
- the fact authority is not valid;
- provenance is missing or contradictory; or
- the split is inferred only from events or administrative metadata.

An invalid split fails closed with `INVALID_LIFECYCLE_MAPPING` or another
explicitly locked public failure category that preserves that semantic result.

### 7.5 Split stability and replay

An authorized split must replay to the same resulting subject identities and
Lifecycle Identities from equivalent authoritative inputs.

T02 snapshots, T06 recomputation, retrieval order, event grouping, or
implementation-generated discriminators must not change the split result.

## 8. Merge and Equivalence Boundary

Authority A may assert that two candidate mappings represent:

1. the same canonical economic subject;
2. distinct canonical economic subjects; or
3. an unresolved or ambiguous subject relationship.

Authority A must not introduce an unrestricted merge operation.

### 8.1 Same-subject resolution

When authoritative facts establish that two mappings represent the same
subject, **unestablished candidate mappings** resolve to one Canonical Economic
Subject Identity and, when the P06 identity is also the same, one Lifecycle
Identity.

Event grouping does not perform this semantic merge.

An equivalence assertion must not automatically perform a retroactive merge of
already-established Lifecycle Identities. If two established lifecycle
identities later appear equivalent, the assertion is an identity-correction or
identity-change case governed by Section 10. Authority A must preserve the
historical identities and topology while the authorized correction outcome is
determined. There is no unrestricted merge operation and no silent historical
rewrite.

### 8.2 Distinct-subject resolution

When authoritative facts establish distinct subjects, Authority A supplies
distinct Canonical Economic Subject Identities. The resulting lifecycles are
distinct when their P06 identity and subject identity combination is distinct.

### 8.3 Existing identity conflict

If a later authoritative fact would change an already-established lifecycle
identity, Authority A must not silently mutate the historical identity.

The result must be one of the explicitly authorized identity-correction
outcomes in Section 10. If no such outcome is authorized, the state fails
closed.

## 9. Conflict and Fail-Closed Semantics

Authority A must fail closed for:

- missing subject identity;
- conflicting subject identity;
- ambiguous mapping;
- non-distinct split subjects;
- invalid split fact;
- inconsistent P06 relationship;
- duplicate identity claims;
- contradictory authoritative facts;
- unresolved equivalence;
- invalid identity representation;
- digest mismatch; and
- provenance failure.

The semantic rule is:

> If identity cannot be established deterministically, fail closed.

Authority A must not resolve semantic conflict using:

- latest timestamp;
- insertion order;
- database order;
- provider preference;
- caller preference;
- majority vote;
- result magnitude; or
- event grouping.

The exact public enum names, error payload fields, and precedence among
multiple failure categories are specification dependencies unless already
locked by an upstream contract.

## 10. Identity Correction and Change Semantics

Authority A identity facts are distinct from Authority B correction and
supersession lineage for T07 results.

### 10.1 Correction of identity representation

A representation correction is a correction to how an already-established
semantic identity is encoded or transported, with no change to the
authoritative subject-defining facts.

For this case:

- the existing Canonical Economic Subject Identity and Lifecycle Identity
  remain valid;
- no new Lifecycle Identity is required;
- the historical identity and its prior representations are preserved; and
- the corrected representation may replace or supersede the representation
  only under the applicable canonicalization rule.

The corrected representation must not silently rewrite historical identity
facts or make a different subject appear equivalent.

### 10.2 Correction of an authoritative identity fact

A correction of an authoritative identity fact is a claim that the prior fact
was wrong, incomplete, or misapplied. It must be represented as a new
authoritative Authority A fact with explicit provenance and a reference to the
fact being corrected.

It must not mutate the historical fact in place.

For this case:

- the historical Canonical Economic Subject Identity and Lifecycle Identity
  remain valid for the historical fact set and historical representations;
- a new Lifecycle Identity is required only if the authorized correction
  establishes a distinct semantic subject or otherwise establishes a distinct
  lifecycle mapping;
- the historical identity and topology are preserved; and
- until an explicit authorized correction outcome determines the result, the
  affected mapping is unresolved and fails closed.

### 10.3 Correction of lifecycle mapping

If the underlying lifecycle mapping is later proven wrong, Authority A must
not silently change the historical Lifecycle Identity. The corrected mapping
must be evaluated under an explicitly authorized identity-correction rule.

For this case:

- the historical Lifecycle Identity remains valid for the historical mapping
  and is never silently mutated;
- a new Lifecycle Identity is required when the corrected authoritative
  mapping establishes a distinct subject/P06 combination;
- the historical identity, historical mapping, and historical topology are
  preserved;
- the corrected mapping is unresolved and fails closed until an authorized
  outcome is selected; and
- a vague future or later mapping is not an implicit identity mutation
  mechanism.

Until that rule establishes a deterministic outcome, the mapping is unresolved
and fails closed.

### 10.4 Replacement or supersession of an identity fact

Authority A may require a new identity fact to replace a prior fact only under
an explicitly authorized identity-fact change rule.

The replacement or supersession of a fact does not by itself merge or mutate
established lifecycle identities. The rule must explicitly state whether the
replacement preserves the existing semantic identity, establishes a distinct
identity, or leaves the mapping unresolved.

This is not T07 result correction or supersession lineage. Authority B owns
correction and supersession facts for T07 result lineage and remains separate.

### 10.5 Actual semantic change of economic subject

An actual semantic change in the economic subject is not an identity mutation.
It establishes a distinct subject identity and, when paired with a P06
DecisionIntent Identity, a distinct Lifecycle Identity.

For this case:

- the existing Lifecycle Identity remains valid for the historical subject
  and historical fact set;
- a new Lifecycle Identity is required for the changed semantic subject when
  it is paired with a P06 DecisionIntent Identity;
- the historical identity, results, and lineage representations are preserved;
  and
- no historical result, identity, or lineage representation is retroactively
  mutated.

### 10.6 Identity change boundary

An established historical Lifecycle Identity is immutable. A later
authoritative fact may establish a corrected or distinct future mapping only
through an explicitly authorized Authority A identity-change outcome.

No future-mapping label, pending mapping, equivalence assertion, or
administrative replacement may silently mutate an established identity. If the
authorized outcome cannot be determined, Authority A must preserve the
historical identity and fail the affected current mapping closed.

This specification does not become Authority B's result-lineage authority.

## 11. Deterministic Replay

For equivalent authoritative inputs, Authority A must produce equivalent:

- Canonical Economic Subject Identities;
- Lifecycle Identities;
- equivalence outcomes;
- split outcomes;
- conflict outcomes;
- identity-correction outcomes;
- canonical representations; and
- identity digests.

Replay must not depend on:

- wall-clock time;
- randomness;
- local timezone;
- database state;
- insertion order;
- retrieval order;
- filesystem state;
- provider state;
- process identity;
- memory address; or
- hidden configuration.

Equivalent authoritative inputs must produce equivalent resulting subject
identities for an authorized split. A different ordering of equivalent
observations must not create a new identity.

## 12. Provenance and Evidence

Authority A may consume authoritative identity facts and supporting evidence
needed to establish:

- the P06 DecisionIntent relationship;
- canonical economic subject identity;
- lifecycle mapping;
- a Lifecycle Split Fact;
- equivalence;
- conflict resolution;
- identity correction or change;
- authoritative source and version; and
- relevant upstream observations or events.

Authority A must preserve provenance for:

- P06 DecisionIntent;
- canonical economic subject;
- lifecycle mapping;
- split fact;
- equivalence fact;
- conflict fact;
- identity fact;
- authoritative source/version; and
- relevant upstream observations/events.

Supporting evidence does not become identity authority merely by being
preserved.

P07 and P08 artifacts must not be elevated into lifecycle identity authority
unless an already-approved contract explicitly grants that authority.

T01, T02, and T06 remain linkage/provenance layers only under the approved
baseline.

## 13. Canonicalization and Identity Digests

Authority A must define deterministic representations for:

- Canonical Economic Subject Identity;
- Lifecycle Identity;
- Lifecycle Split Fact; and
- lifecycle mapping and equivalence facts.

The representation must preserve the established canonicalization principles:

- UTF-8;
- deterministic JSON or the existing canonical format;
- sorted keys;
- explicit nulls where allowed;
- canonical enum values;
- UTC timestamps;
- deterministic decimal representation;
- no binary floating point for semantic numeric values;
- no NaN or infinity;
- negative-zero normalization; and
- deterministic collection ordering.

### 13.1 Normative semantic dependency sequence

The dependency sequence is:

```text
Semantic Identity Definition
          ↓
Semantic Identity Value
          ↓
Canonical Representation
          ↓
Integrity Digest
```

The Semantic Identity Definition establishes which authoritative semantic facts
define the subject or lifecycle. The Semantic Identity Value is the resulting
identity claim before serialization. The Canonical Representation is the
deterministic encoding of that already-defined value. The Integrity Digest
protects that representation.

The digest is not semantic identity. Semantic identity must not be defined by
hashing a representation that itself depends on that digest. No identity or
digest circular dependency is permitted.

### 13.2 Semantic identity

Semantic identity is the stable meaning of the subject or lifecycle.

### 13.3 Canonical representation

Canonical representation is the deterministic encoding of an already-defined
semantic identity fact.

### 13.4 Integrity digest

An integrity digest protects the canonical representation. It does not become
semantic identity merely because it is convenient.

The exact digest construction, digest field placement, and serialized field
names remain specification dependencies unless already locked by an upstream
contract.

Authority A must not create circular identity dependencies. A digest must not
become an input to the semantic identity whose representation it hashes.

## 14. Authority Boundaries

### 14.1 Authority A owns

Authority A owns:

- Canonical Economic Subject Identity;
- Lifecycle Identity;
- lifecycle equivalence;
- lifecycle mapping;
- Lifecycle Split Facts; and
- lifecycle mapping conflict resolution.

### 14.2 Authority A does not own

Authority A does not own:

- G2 realization semantics;
- G3 accounting or economic result semantics;
- G4 classification semantics;
- T07 canonical result selection;
- Authority B T07 result lineage;
- CPA analytical cohort selection;
- AEA analytical cutoff;
- economic metrics;
- P&L;
- valuation;
- execution;
- capital authorization;
- wallet, signing, or broadcast;
- external provider or network control; or
- future Snapshot semantics.

### 14.3 T07

T07 consumes and validates Authority A outputs.

T07 must not redefine Canonical Economic Subject Identity, Lifecycle Identity,
equivalence, mapping, or split semantics.

T07 remains responsible for assembling supplied economic semantics and
selecting the current canonical T07 result per lifecycle.

### 14.4 CPA

CPA later consumes the authoritative lifecycle projection and expected
population.

CPA must not:

- create lifecycles;
- split lifecycles;
- merge lifecycles;
- redefine identity;
- infer identity from P06 alone; or
- select canonical T07 results.

### 14.5 AEA

AEA later handles analytical admissibility and as-of selection.

AEA must not redefine Canonical Economic Subject Identity, Lifecycle Identity,
equivalence, mapping, or split semantics.

### 14.6 T02 and T06

T02 owns observation population and dataset cutoff.

T06 owns its approved non-economic readiness predicate.

Neither becomes lifecycle identity authority.

## 15. Required Invariants

The following invariants are normative.

### A-01 — One lifecycle, one P06

Every Lifecycle Identity maps to exactly one P06 DecisionIntent Identity.

### A-02 — Default P06 cardinality

One P06 DecisionIntent Identity maps to exactly one Lifecycle Identity by
default.

### A-03 — Split exception

A P06 may map to multiple Lifecycle Identities only through an authoritative
Lifecycle Split Fact.

### A-04 — Distinct resulting subjects

Every valid split must authoritatively assert distinct resulting Canonical
Economic Subject Identities.

### A-05 — Split fact exclusion

The Lifecycle Split Fact is not part of the Lifecycle Identity seed.

### A-06 — Event association

Event association cannot create, split, merge, or redefine a subject or
lifecycle identity.

### A-07 — Identity stability

Equivalent representations, snapshots, recomputation, and replay cannot
change an established identity.

### A-08 — Deterministic equivalence

Equivalent authoritative subject evidence resolves to one identity and must
not produce duplicate identities.

### A-09 — Fail-closed ambiguity

Insufficient, contradictory, or ambiguous identity evidence fails closed.

### A-10 — No heuristic identity

Similarity, ordering, timing, provider preference, or caller preference cannot
establish identity.

### A-11 — No arbitrary discriminator

No administrative or generated discriminator may be added to the identity
seed to avoid a collision.

### A-12 — No T02/T06 identity authority

T02 and T06 identities are linkage/provenance only.

### A-13 — No circular identity dependency

Identity and integrity digest construction must not depend circularly on
representations or facts that depend on the identity being constructed.

### A-14 — Deterministic replay

Equivalent authoritative inputs produce equivalent identities, equivalence,
split, conflict, correction, representation, and digest outcomes.

### A-15 — Provenance integrity

Identity facts and mappings must preserve verifiable authority and provenance.

### A-16 — Authority separation

Authority A owns subject and lifecycle identity. Authority B owns T07 result
correction and supersession lineage. Neither may silently assume the other's
authority.

### A-17 — Semantic boundary

Only authoritative subject-defining and lifecycle-anchor facts may determine
semantic identity. Provenance, evidence, observations, events, T02, T06,
timestamps, retrieval order, provider identifiers, and administrative
identifiers cannot independently define it.

### A-18 — No silent identity mutation

An established historical Lifecycle Identity must not be silently mutated.
Every correction, replacement, or semantic change requires an explicit
authorized Authority A outcome; otherwise the affected state fails closed.

### A-19 — No retroactive equivalence merge

An equivalence assertion must not retroactively merge established Lifecycle
Identities or silently rewrite historical lifecycle topology.

### A-20 — Explicit correction outcome

An identity correction must deterministically preserve the historical identity,
establish a new identity, or fail closed as unresolved. A vague future mapping
cannot select implicitly among those outcomes.

### A-21 — Digest is not identity

The integrity digest protects the canonical representation after semantic
identity has been defined. It cannot define semantic identity or participate in
a circular identity/digest dependency.

### A-22 — Semantic replay chain

Equivalent authoritative inputs must produce equivalent semantic identity
values before canonical representation and digest construction. Serialization
or digest differences must not create semantic identity differences.

## 16. Dependency Graph

Base identity path:

```text
Authority A
        ↓
Canonical Economic Subject Identity
        ↓
Lifecycle Identity
        ↓
T07 / CPA Consumers
```

Split path:

```text
Authority A
        ↓
Lifecycle Split Fact
        ↓
Distinct Resulting Canonical Economic Subject Identities
        ↓
Distinct Lifecycle Identities
```

Population and analytical relationships:

```text
T02 Observation Population
        +
Authoritative Lifecycle Projection
        ↓
CPA
```

```text
T07 Current Canonical Result per Lifecycle
        ↓
AEA Analytical Admissibility / As-Of Selection
```

Dependency constraints:

```text
T07 consumes and validates Authority A outputs.
CPA consumes the authoritative lifecycle projection.
CPA MUST NOT create, split, merge, or redefine lifecycle identity.
AEA MUST NOT redefine lifecycle identity or lineage.
No downstream component may feed identity authority backward.
```

Semantic identity and integrity dependency:

```text
Semantic Identity Definition
        ↓
Semantic Identity Value
        ↓
Canonical Representation
        ↓
Integrity Digest
```

The digest protects the canonical representation and cannot define the
semantic identity or feed back into its definition.

Authority B remains a parallel downstream authority for T07 result lineage:

```text
Authority B
        ↓
Validated Correction / Supersession Lineage
        ↓
T07 Result Canonical-Head Selection per Lifecycle
```

Authority B does not define Canonical Economic Subject Identity or Lifecycle
Identity.

## 17. Governance Dependencies

### 17.1 Already approved semantics

The following are approved and must not be reopened:

- V1 economic subject is Trade Lifecycle;
- P06 DecisionIntent Identity plus Canonical Economic Subject Identity anchor
  lifecycle;
- the exact lifecycle identity seed;
- one lifecycle → exactly one P06;
- one P06 → one lifecycle by default;
- explicit split exception;
- distinct resulting subject requirement;
- split fact exclusion from the identity seed;
- event-grouping prohibition;
- Authority A ownership;
- T07 consumer/validator boundary;
- CPA consumer boundary;
- AEA analytical-only boundary; and
- T01/T02/T06 linkage/provenance boundary.

### 17.2 Unresolved specification dependencies

The following remain specification dependencies:

1. exact serialized fields and types of Canonical Economic Subject Identity;
2. exact serialized fields and types of Lifecycle Identity;
3. exact serialized fields and types of Lifecycle Split Fact;
4. exact encoding of the semantic identity seed;
5. exact identity digest construction;
6. exact equivalence-fact representation;
7. exact conflict-fact representation;
8. exact identity correction/change-fact representation;
9. exact public failure enum spellings;
10. exact provenance envelope and authority-version representation; and
11. exact adapter mapping to T07.

Each dependency must state the semantic decision that remains and why it is
needed. “Governance parameter required” is not sufficient analysis.

No unresolved item authorizes arbitrary identity fields, implementation
discriminators, or heuristic equivalence.

## 18. Required Auditability

This specification must allow a later architect to independently determine:

- whether identity is semantic or administrative;
- whether a split produces distinct subjects;
- whether Lifecycle Identity is stable;
- whether identity can change;
- whether equivalence is deterministic;
- whether conflicts fail closed;
- whether CPA and T07 remain consumers rather than authorities;
- whether replay produces identical identities; and
- whether provenance can be independently verified;
- whether semantic identity is separated from serialization governance;
- whether identity corrections have deterministic outcomes;
- whether equivalence avoids retroactive lifecycle merges; and
- whether the identity-to-representation-to-digest chain is non-circular.

The formal audit must verify the requirements of this document against the
approved P08-T07 Canonical Result Authority Extension specification.

## 19. Document Status and Next Action

### Specification status

**SPECIFICATION DRAFT — IMPLEMENTATION NOT AUTHORIZED**

This document defines the proposed Authority A semantic governance contract.
It does not claim PASS or implementation readiness.

### Implementation status

No source code, runtime behavior, or tests are authorized or changed by this
document.

Authority B, CPA, AEA, Snapshot, and P08-T08 are not started.

### Exact next action

**FORMAL AUDIT REQUIRED**

P08 CANONICAL ECONOMIC SUBJECT / LIFECYCLE IDENTITY AUTHORITY SPECIFICATION DRAFT COMPLETE — FORMAL AUDIT REQUIRED — IMPLEMENTATION NOT AUTHORIZED