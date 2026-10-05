# A1-HTTP-01 — explicit HTTP adapter, offline conformance

Contract: `a1-explicit-http-adapter-v1`.

## Bounded post-A1-AUD dependency review and selection

Starting main `8b549e599038c8418589baae16fc303b5e8c36ac`; PR #143
MERGED / CLOSED; exact implementation head
`3e371a1c53c28d0bf15585458a4f5ff7940c6f8f`, PR CI #567 /
`37195942557` SUCCESS. Post-merge main CI #568 / `37212294693`
SUCCESS for Python 3.13, TypeScript and whitespace. No competing open PR.

The controller's 2026-10-05 batch authorizes bounded review, specification,
implementation, focused/regression tests and documentation in ONE PR, only
when the selected capability can be completed without provider/runtime access.

| Dependency | Current repository proof | Remaining work |
| --- | --- | --- |
| A1 / P03 / RTI-11 | Complete finite pre-T packet, exact original-owner binding, pure replay and existing Risk/paper composition; offline milestones landed. | Actual source/endpoint qualification remains operational. |
| A1-AUD-01 | Separate durable source audit and exact successful lifecycle attachment; PR/main CI PASS. | Applying revision 0003 and qualifying a real durable database remain separate. No active-case reconstruction. |
| Concrete injected HTTP opener | `A1BoundedTransport` requires a caller-supplied opener; existing fake providers exercise accounting. Common P03 packet admits only a sanitized RPC origin. | No concrete A1 opener translates that origin to a fixed private RPC route or injects Demo authentication outside durable evidence. Offline adapter conformance is explicitly identified by the earlier dependency review. |
| Quota, latency, runtime, smoke | Caps, declarative preflight, single-process launcher and controlled-paper smoke harness exist. | Selected-account/shared-use evidence, real timing, stable process/database, endpoint genesis/LEVEL 1 and provider-backed smoke require separate authority. Fixtures cannot supply them. |

Selected smallest implementable gate: **A1-HTTP-01**. It implements the missing
opener seam without changing the completed collection, replay, Risk, paper,
audit or persistence owners. It adds real transport preparation rather than
another declarative readiness claim. No separate review/specification/closure
PR, provider qualification result or economic authority is implied.

## Explicit construction and routing

`core/data/a1_http_adapter.py:A1HttpAdapter` is explicitly constructed and
passed as the existing collector's `opener`. It has no application default,
CLI, environment lookup, Settings access, background task or probe.
Construction performs no connection.

The frozen configuration requires one safe `rpc_origin`, one private `rpc_url`,
and an explicitly supplied CoinGecko Demo key. Configuration repr is redacted;
errors contain static bounded reason codes. Real values belong only in a
separately authorized runtime secret store, never in repository examples,
manifests, logs, canonical requests or audit payloads. Tests use synthetic values.

RPC `solana`/`safety` requests must be POSTs to exactly the configured public
HTTPS origin. The fixed physical RPC URL may have a private path/query but
must share the exact hostname and HTTPS port 443. Userinfo, fragments, control
characters and arbitrary host aliases are refused. RPC body bytes are passed
unchanged. Duplicate/noncanonical envelopes and mutating RPC methods are refused
before any connection. The ordinary scope reuses the existing read-only method
allowlist; safety reuses the existing finalized P03 parameter validator. There
is no route fallback, host switch or RPC header-auth profile.
Provider authentication needing another profile requires a separate selection.

CoinGecko `valuation`/`diagnostic` requests must be GETs to the canonical Demo
Solana pool/minute OHLCV path at `api.coingecko.com`, with the existing exact
ordered query: aggregate 1, limit 3, USD, canonical mint, include-empty false,
and canonical minute-aligned cutoff. Extra, duplicate, reordered, changed or
credential-bearing query parameters are refused before connection creation.
Only this host/profile receives `x-cg-demo-api-key`. The key never goes to RPC.

The existing `A1HttpRequest` remains the original secret-free object. The
adapter returns its public endpoint as `final_url`, denoting the **sanitized
logical route**, not the private physical RPC path/query. Since the adapter
never follows a redirect and accepts only status 200, this does not disguise
redirected source data. Audit digests attest that logical request and the
returned bytes; they are not hashes of the complete authenticated wire request
or an attestation of a provider account. Keep the physical route/account
selection in protected operational configuration, not durable market evidence.

## HTTP, TLS, deadline and resource contract

The production backend is stdlib `HTTPSConnection` with default verified TLS,
hostname verification and port 443. It has no environment proxy, redirect or
authentication handler. Exactly one `request` and one `getresponse` occur per
accepted invocation. No HTTP retry, redirect, pagination, fallback, decompression
or extra source request occurs. Each invocation uses a fresh connection.

The timeout argument must exactly equal the canonical request's timeout.
An independent monotonic deadline starts before connection construction;
remaining time is checked and applied to connection/send, response-header and
body socket operations. Body reads use stdlib `read1` to avoid an internal
body-filling receive loop under one unchanged timeout. Backward/nonfinite clocks
and exhausted deadlines fail closed. The existing aware source/receipt clocks,
aggregate ledger, source freshness and immutable T remain independently owned
by the collector/transport.

This is **not** a hard real-time watchdog or an operational latency guarantee.
DNS, TLS, platform scheduling and HTTP framing must be qualified in the actual
runtime. Deadline overruns are rejected when blocking operations return; no
packet is published from an overrun. Offline timing proves enforcement paths,
not worst-case provider latency or successful same-minute completion.

Only HTTP 200 is accepted. Redirects, authentication failures, rate limits and
server errors close the response/connection without reading/retrying. Body reads
are bounded to at most 64 KiB and the canonical remaining body cap plus one
sentinel byte. Over-cap, invalid bytes, Content-Length truncation, framing/read
errors or timeout close resources and return no receipt. Backend exception text
never enters returned errors. The outer ledger reserves the full cap before the
opener; failure remains charged and terminal, without refunds or a second call.

Successful responses are closed by the existing transport; adapter close is
idempotent. A supplied connection factory/clock is a trusted injection seam,
not protection against malicious code that logs secrets or performs hidden I/O.
The default backend behavior is also exercised offline through actual stdlib
HTTP framing/send with fake sockets; no DNS/TLS/provider connection is made.

## Acceptance, completed scope and remaining operational gates

Focused cases cover no-contact/redacted construction, frozen configuration,
four scopes, exact routing/auth isolation, malformed route/query rejection,
timeout equality/decreasing timeouts, deadline/clock failure, HTTP failures,
sanitized exceptions/cleanup, cap/sentinel boundaries, verified TLS configuration,
actual stdlib fixed/chunked/truncated HTTP framing and no redirected second send.
Integration retains 21 physical fake calls and original common packet lineage,
then runs existing owners with either exact durable lifecycle/audit readback or
independent Risk veto with zero persisted rows. Authentication/physical routing
values are absent from the audit. All real networking is blocked in these tests.

No operational DB migration, runtime launch, real credential lookup, provider
request, quota/latency measurement, LEVEL 2 verification, automatic cycle/API
wiring or Hunter Room change. This milestone closes **offline adapter
implementation/conformance**, not operational adapter or provider qualification.

Next operational packet must select a stable single process, connected durable
database with intentional revision 0003 migration, exact environment/operator
readiness, this fixed RPC route and Demo profile, protected runtime credentials,
actual account quota/shared-use/latency evidence and an explicit acceptance of
LEVEL 1-only paper verification. Any authorized attempt is finite, no-retry,
pre-T collection and pure post-T replay, at most one simulation-only lifecycle,
explicit audit attachment/readback and terminal STOP. Do not silently wire this
adapter into the older selected-mint OAF smoke or claim it verifies A1.

Risk Governor remains INDEPENDENT / MANDATORY / HIGHER AUTHORITY. G2 remains
BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.
Wallet/signing/broadcast/DEX/settlement/live trading and MASTER_BLUEPRINT changes
remain excluded.

## Local verification checkpoint

Python 3.13.15: **69 focused tests PASS** (67 adapter conformance and two
full-owner integration/Risk cases). **275 relevant regressions / 44 subtests
PASS** across two bounded runs: existing transport/budget/A1/P03/RTI-11 and
lifecycle persistence/query/catalog/foundation; independent paper Risk,
declarative preflight and additive audit migration. Locked environment check,
module compilation, exact scope and whitespace PASS. No full local repository
suite. PR/head/run/merge evidence remains pending publication; full Python and
TypeScript suites belong to GitHub CI. Existing Starlette/Alembic deprecation
warnings do not change the test outcomes.
