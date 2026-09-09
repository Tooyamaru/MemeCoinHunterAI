---
name: G1 predecessor contracts
description: Durable cross-phase validation rules for the simulation-only G1 boundary.
---

G1 must validate P06, P07, and P08 artifacts through each predecessor's own
canonical constructor/digest contract rather than recomputing every digest with
a G1 serializer. P07-T05's successful reconciliation status is `MATCH`;
P07-T06 owns a separate non-economic status vocabulary in which the corresponding
successful result status is `RECONCILED`.

**Why:** The predecessor boundaries intentionally use different canonical
representations and status vocabularies. A generic G1 hash or status assumption
can reject a valid, fully materialized lifecycle or silently misclassify its
finality.

**How to apply:** When extending G1 verification, preserve predecessor-owned
validation and map only explicitly supplied P07-T06 fields into G1's
simulation-finality predicate. Keep P08-T02 `as_of_time` as a timezone-aware
datetime in the result object while canonicalizing it only for serialization.