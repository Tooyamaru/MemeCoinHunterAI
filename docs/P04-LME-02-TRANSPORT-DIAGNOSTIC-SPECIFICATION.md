# P04-LME-02 — Server-Side OHLCV Transport and Diagnostic Specification

**Status:** LIMITED IMPLEMENTATION COMPLETE / LOCAL CHECKS PASS / CI PENDING

**Phase:** P04 — Market & Signal Intelligence

**Scope:** one bounded read-only request and one-shot diagnostic composition

**Updated:** 2026-09-21

## 1. Authorization and purpose

The owner authorized continuation on 2026-09-21 after reviewing P04-LME-01 and
the proposed next step. P04-LME-02 connects the accepted CoinGecko Demo Onchain
request contract to one bounded server-side HTTP GET and then to the existing
P04-LME-01 mapper and price-direction policy.

This is a diagnostic transport boundary. It does not schedule polling, select a
token or pool, publish application state, persist evidence, place paper trades,
connect a wallet, sign, broadcast, or execute a transaction.

## 2. Components

The limited implementation may add:

- `core/data/coingecko_onchain_transport.py`;
- `core/data/coingecko_onchain_diagnostic.py`;
- `tests/test_coingecko_onchain_transport.py`;
- `tests/test_coingecko_onchain_diagnostic.py`;
- the `COINGECKO_DEMO_API_KEY` setting name in `.env.example`;
- minimal changes to P04-LME-01 timing inputs, tests, and project documentation.

No new dependency is authorized. The transport uses the Python standard
library and remains replaceable through an injected opener in tests.

## 3. Request and secret boundary

The transport accepts only an already-validated `OhlcvRequest` and a server-side
API key. The key is supplied through the `COINGECKO_DEMO_API_KEY` environment
variable at the diagnostic boundary. It must not enter:

- the URL or query string;
- response/result objects;
- exception text;
- logs;
- attempt metadata;
- canonical provenance or digests; or
- test fixtures and committed environment files.

The key is sent only as the `x-cg-demo-api-key` request header. Normal object
representations redact headers.

## 4. Timing correction

P04-LME-01 used one injected time for both the closed-minute request cutoff and
downstream evaluation. A real response necessarily arrives after its request is
built, so P04-LME-02 separates these meanings:

- `OhlcvRequest.reference_time` remains the pre-request time used solely to
  calculate and bind `before_timestamp`;
- `evaluation_time` is supplied to mapping after receipt and must be at or
  after `received_at`;
- the default remains the request reference time for existing offline replay;
- P02 data age and freshness use the explicit evaluation time;
- candle closure is still checked against actual receipt time.

No wall clock enters the pure mapping or signal policy. Only the transport and
diagnostic orchestration receive an injected clock.

## 5. HTTP limits

- Method: `GET` only.
- Scheme and host: fixed by the validated P04-LME-01 request.
- Redirects: disabled.
- Timeout: exact positive value carried by `OhlcvRequest`.
- Response limit: exact bounded value carried by `OhlcvRequest`, enforced while
  streaming rather than after retaining an unbounded body.
- Attempts: exactly one. Retry remains orchestration-owned.
- Success body: returned only for a 2xx status.
- HTTP error body: discarded and never logged or preserved.
- Response objects: always closed.

Expected transport failures map into the existing P04-LME-01 outcomes:

- timeout -> `TIMEOUT`;
- oversized response -> `RESPONSE_TOO_LARGE`;
- connection/DNS/TLS/unsupported response -> `SOURCE_UNAVAILABLE`;
- HTTP status remains explicit so the mapper owns 401/403/429/non-2xx policy.

## 6. One-shot diagnostic

The diagnostic function receives an exact request, admitted P02-T06
predecessor, explicit freshness policy, optional environment mapping, injected
transport, and injected clock. It:

1. reads the API key by exact environment name;
2. prepares the redacted authenticated request;
3. performs one bounded fetch;
4. captures an explicit evaluation time after receipt; and
5. invokes the existing price-direction policy from original request/response
   inputs.

Missing credentials return the existing `AUTHENTICATION_FAILED` outcome with
no signal. The diagnostic never constructs accepted P02 or P04 evidence itself.

## 7. Verification gate

Offline tests must prove:

1. exact URL, method, header, timeout, and single-attempt behavior;
2. redirects are rejected;
3. streaming size enforcement and response closure;
4. 2xx, 401/403, 429, generic HTTP, timeout, connection, invalid response, and
   oversized response behavior;
5. secrets cannot appear in output, repr, error text, provenance, or logs;
6. injected clocks produce deterministic timestamps;
7. missing credentials fail closed;
8. a mocked diagnostic produces real P02-T07/T08/T09 evidence and P04 signal;
9. evaluation time after receipt is used for freshness;
10. no retry, scheduler, persistence, wallet, execution, or application wiring
    is reachable.

An actual request to CoinGecko is optional operational verification. It may run
only when a real API key and exact real Solana pool composition are supplied
through the server-side environment. CI must remain credential-free and offline.

## 8. Exit state

P04-LME-02 is complete only after focused/regression tests and CI pass. Actual
provider verification is recorded separately as `NOT RUN`, `PASS`, or `FAIL`;
absence of credentials must never be represented as a successful live check.

Completion of this task does not authorize continuous polling, runtime wiring,
paper automation, wallet integration, G2, G3, G4, P09, or live execution.
