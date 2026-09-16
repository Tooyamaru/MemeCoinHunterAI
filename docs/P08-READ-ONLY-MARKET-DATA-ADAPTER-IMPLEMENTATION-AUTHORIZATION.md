# P08 — Read-Only Market-Data Adapter Limited Implementation Authorization

**Status:** LIMITED IMPLEMENTATION AUTHORIZED
**Basis:** `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION-REAUDIT.md`
**Contract version:** `p08-read-only-market-data-observation-v1`
**Boundary:** Provider-neutral, immutable, read-only market observations

## 1. Authorization

The formal re-audit of the corrected Read-only Market Data Adapter
specification passed all eleven criteria. This document grants one limited
implementation authorization for the exact contract version above.

Authorization is limited strictly to these files:

```text
core/data/read_only_market_data.py
tests/test_read_only_market_data.py
```

These files may be created or modified only for the provider-neutral observation
contract and its focused deterministic tests. No other source, test, package
export, dependency, workflow, environment, project-state, governance,
documentation, database, migration, or deployment file is authorized by this
document.

## 2. Required implementation behavior

The implementation must provide only:

1. recursively immutable observation, metric-envelope, source, provenance, and
   evaluation-context values;
2. the exact canonical fields, null semantics, scalar representations, bounded
   mappings, sequence rules, and hard limits in the formal specification;
3. deterministic identity, compact canonical UTF-8 serialization, and SHA-256
   digest validation;
4. explicit cutoff/freshness validation using caller-supplied UTC values only;
5. the fixed fail-closed reason vocabulary and precedence;
6. explicit replay, duplicate, contradiction, and ordering handling; and
7. an explicit local processing context with no ambient state.

The observation remains evidence-only. It must not infer, default, repair,
truncate, aggregate, reconcile, rank, score, or interpret economic meaning.

## 3. Required focused tests

`tests/test_read_only_market_data.py` must cover at least:

- valid discovery and paper-evaluation observations;
- exact required and optional field behavior, including explicit `null`;
- candidate, chain, token, and market-subject identity;
- source identity, source-event identity, bounded provenance, and predecessor
  links;
- normalized price, liquidity, volume, asset-age, holders, and transaction
  envelopes;
- canonical integer/text/mapping/sequence bounds and rejection behavior;
- missing, unavailable, invalid, stale, future, contradictory, and non-finite
  values;
- inclusive and exclusive freshness boundaries;
- unsupported versions, fields, metrics, and units;
- canonical mapping order, timestamp, decimal, enum, and null behavior;
- field, raw-payload, and observation digest validation and tampering;
- exact replay without mutation;
- duplicate identity/content without replacement;
- same-identity changed-content contradiction;
- explicit ordering, missing sequence, and out-of-order behavior;
- deterministic reason precedence;
- recursive immutability and predecessor non-mutation; and
- absence of scoring, ranking, decision, authorization, execution, settlement,
  accounting, realized P&L, and live-trading behavior.

Tests must use deterministic local fixtures only. They must not contact a
provider, network, API, database, queue, filesystem store, wallet, SDK, or
external service.

## 4. Explicit prohibitions

This authorization does not permit:

- credentials, API keys, access tokens, secrets, private keys, wallets, or
  signing;
- provider-specific integrations, SDKs, endpoints, transports, network calls,
  retries, failover, polling, or source monitoring;
- orders, order construction, execution, broadcast, settlement, or external
  finality;
- fills, positions, ledgers, reconciliation, accounting, valuation, cost
  basis, realized P&L, ROI, or economic-result calculation;
- P05 safety, eligibility, feature calculation, scoring, ranking, or opportunity
  creation;
- P06 decision production or interpretation as authorization;
- Risk/Capital authorization or Risk Governor behavior;
- P07 simulation, paper-state, ledger, or history mutation;
- G1 recognition/finality behavior;
- G2 realization eligibility;
- G3 accounting/economic-result behavior;
- G4 performance classification;
- P09 controlled execution;
- persistence, databases, migrations, queues, caches, APIs, workers, dashboards,
  or deployment behavior; or
- ambient clocks, randomness, environment state, filesystem state, database
  state, network state, hidden registries, or mutable singletons.

## 5. Verification and follow-on gate

The implementation must be verified with focused tests and the repository's
standard static/diff checks under the project-supported runtime. A separate
post-implementation audit is required before the limited implementation can be
considered complete or closed.

This authorization is not permission to begin G2, G3, G4, or P09. Those
boundaries remain separately governed and not authorized.

No commit or push is authorized by this document.