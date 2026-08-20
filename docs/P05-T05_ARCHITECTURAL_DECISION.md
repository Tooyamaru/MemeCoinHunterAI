# P05-T05 Architectural Decision

## Final Decision

P05-T05 is **Per-Candidate Opportunity Score (Fast Pre-Score)**.

P05-T05 consumes one ELIGIBLE candidate's validated P05-T04 output plus a versioned deterministic scoring ruleset and produces one immutable, auditable Opportunity Score record.

P05-T05 is deterministic, provider-neutral, pure, and has no external I/O.

P05-T05 does not perform feature recalculation, risk re-evaluation, candidate comparison, ranking, trading decision, authorization, execution, LLM judgment, or autonomous behavior.

## Fixed P05 Sequence

P05-T01 Candidate Boundary — COMPLETE
P05-T02 Normalization / Evidence Contract — COMPLETE
P05-T03 Hard-Risk / Disqualification Boundary — COMPLETE / CLOSED / AUDITED PASS
P05-T04 Per-Candidate Feature and Quality Evaluation — CURRENT / implementation pending
P05-T05 Per-Candidate Opportunity Score (Fast Pre-Score) — NEXT

P05 closes after T05.

## Explicit Non-Scope

No ranking task exists in P05.

If ranking is later required because of actual capital contention, it belongs to the Risk/Capital Engine.

Optional Deep Analysis is not built now and is evidence-gated for future architecture.

Final trading decisions remain outside P05 in the Deterministic Decision Engine.

## Required T05 Dependency Check

Before implementing T05, verify that P05-T04 retains the feature values required by the scoring ruleset, rather than only PASS/FAIL flags. If required values were discarded, minimally correct the T04 contract before implementing T05.
