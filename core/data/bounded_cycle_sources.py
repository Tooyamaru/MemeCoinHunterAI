"""One-shot provider-neutral discovery admission and canonical liquidity selection.

Sources are injected; this module imports no concrete network transport.
Each invocation owns fresh P02 state and never resumes a previous cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Protocol

from core.data.contracts import FreshnessPolicy
from core.data.discovery import DiscoveryContext, DiscoveryOutcome, TokenDiscoveryBoundary
from core.data.discovery_orchestration import DiscoveryToOrchestrationBoundary
from core.data.materialization import MaterializationContext, TokenUniverseMaterializer
from core.data.market_observations import P02T07PredecessorContext
from core.data.orchestration import AdapterObservation, IngestionContext, IngestionOrchestrator, ObservationKind
from core.data.coingecko_onchain_orchestration import ExactPoolDiagnosticTarget

MAX_CANDIDATES_PER_CYCLE = 5
MAX_DISCOVERY_OBSERVATIONS = 64
MAX_POOLS_PER_CANDIDATE = 20
SOURCE_CONTRACT_VERSION = "bounded-paper-cycle-source-v1"


class CycleSourceError(ValueError):
    """Invalid source facts; no downstream authority may be inferred."""


class CycleSourceUnavailable(RuntimeError):
    """One-shot source failed; callers must not retry."""


def text(value, name):
    if type(value) is not str or not value or value != value.strip() or len(value) > 256:
        raise CycleSourceError(f"invalid {name}")


def aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CycleSourceError(f"invalid {name}")


def fresh(observed, received, reference, policy):
    for value in (observed, received, reference):
        aware(value, "source clock")
    if not isinstance(policy, FreshnessPolicy) or policy.stale_after is None:
        raise CycleSourceError("explicit freshness required")
    if not observed <= received <= reference or reference - observed > policy.stale_after:
        raise CycleSourceError("stale or inconsistent source clock")


@dataclass(frozen=True)
class DiscoveryBatch:
    source_id: str
    receipt_id: str
    received_at: datetime
    observations: tuple[AdapterObservation, ...]
    contract_version: str = SOURCE_CONTRACT_VERSION

    def __post_init__(self):
        text(self.source_id, "source_id")
        text(self.receipt_id, "receipt_id")
        aware(self.received_at, "received_at")
        if self.contract_version != SOURCE_CONTRACT_VERSION or type(self.observations) is not tuple:
            raise CycleSourceError("invalid discovery contract")
        if len(self.observations) > MAX_DISCOVERY_OBSERVATIONS:
            raise CycleSourceError("discovery response exceeds bound")


class DiscoverySource(Protocol):
    def discover_once(self, *, reference_time: datetime) -> DiscoveryBatch: ...


@dataclass(frozen=True)
class DiscoveredCandidate:
    candidate_id: str
    chain_id: str
    token_mint: str
    source_event_id: str


@dataclass(frozen=True)
class DiscoverySnapshot:
    candidates: tuple[DiscoveredCandidate, ...]
    predecessor: P02T07PredecessorContext
    source_id: str
    receipt_id: str
    received_at: datetime


class BoundedDiscoveryOwner:
    def __init__(self, source: DiscoverySource):
        self.source = source

    def discover(self, *, reference_time, processing_time, freshness_policy, evaluation_id):
        aware(reference_time, "reference_time")
        aware(processing_time, "processing_time")
        batch = self.source.discover_once(reference_time=reference_time)
        if type(batch) is not DiscoveryBatch:
            raise CycleSourceError("noncanonical discovery batch")
        batch.__post_init__()
        if batch.received_at > reference_time:
            raise CycleSourceError("discovery receipt newer than reference")
        # Validate all bounded source entries before deterministic truncation.
        by_token = {}
        events = {}
        for observation in batch.observations:
            if type(observation) is not AdapterObservation or observation.kind is not ObservationKind.EVENT:
                raise CycleSourceError("discovery requires P02-T03 event envelope")
            raw = observation.raw_event
            if raw is None or observation.source_id != batch.source_id or raw.source_id != batch.source_id:
                raise CycleSourceError("discovery source identity mismatch")
            text(raw.source_event_id, "source_event_id")
            fresh(raw.event_time, raw.received_time, reference_time, freshness_policy)
            if raw.received_time != batch.received_at or observation.observed_time != batch.received_at:
                raise CycleSourceError("receipt identity mismatch")
            payload = raw.payload
            try:
                if len(json.dumps(payload, sort_keys=True, allow_nan=False).encode()) > 8192:
                    raise CycleSourceError("discovery payload exceeds bound")
            except (TypeError, ValueError) as exc:
                raise CycleSourceError("noncanonical discovery payload") from exc
            if payload.get("discovery_kind") != "DISCOVERED":
                raise CycleSourceError("only discovery events admitted")
            key = (payload.get("chain_id"), payload.get("token_identity"))
            for value in key:
                text(value, "token identity")
            previous = events.get(raw.source_event_id)
            if previous is not None and previous != observation:
                raise CycleSourceError("contradictory source event")
            events[raw.source_event_id] = observation
            previous = by_token.get(key)
            if previous is not None and previous != observation:
                raise CycleSourceError("contradictory duplicate token")
            by_token[key] = observation

        materializer = TokenUniverseMaterializer(context=MaterializationContext(evaluation_id=evaluation_id))
        candidates = []
        boundary = TokenDiscoveryBoundary(context=DiscoveryContext(
            freshness_policy=freshness_policy, contract_version="p02-t04-v1",
        ))
        forwarding = DiscoveryToOrchestrationBoundary(orchestrator=IngestionOrchestrator(
            context=IngestionContext(freshness_policy=freshness_policy, contract_version="p02-t02-v1"),
        ))
        chosen = sorted(by_token.items())[:MAX_CANDIDATES_PER_CYCLE]
        # Selection is lexical; admission respects original numeric source order.
        # Mixed/non-numeric cursors are retained and validated by canonical P02.
        if all(type(o.cursor) is int for _, o in chosen):
            chosen.sort(key=lambda item: (item[1].cursor, item[0]))
        for (chain, token), observation in chosen:
            discovery = boundary.process(observation, processing_time=processing_time, reference_time=reference_time)
            if discovery.outcome is not DiscoveryOutcome.ACCEPTED:
                raise CycleSourceError("P02-T04 rejected: " + ",".join(discovery.reasons))
            forwarded = forwarding.process(discovery, processing_time=processing_time, reference_time=reference_time)
            if not forwarded.published_as_current:
                raise CycleSourceError("P02-T05 rejected")
            # T06 preserves and enforces source cursor order; process order must be
            # compatible with it. A contradiction stops the entire snapshot.
            materialized = materializer.process(discovery, processing_time=processing_time, reference_time=reference_time)
            if not materialized.current_view_present or materialized.entry is None:
                raise CycleSourceError("P02-T06 rejected: " + ",".join(materialized.reasons))
            identity = hashlib.sha256(json.dumps([chain, token], separators=(",", ":")).encode()).hexdigest()
            candidates.append(DiscoveredCandidate("candidate:" + identity, chain, token, observation.raw_event.source_event_id))
        state = materializer.state
        predecessor = P02T07PredecessorContext(
            snapshot=materializer.snapshot(), state_version=state.state_version,
            state_digest=state.state_digest(), materializer_contract_version="p02-t06-v1",
            evaluation_id=evaluation_id,
        )
        candidates.sort(key=lambda c: (c.chain_id, c.token_mint))
        return DiscoverySnapshot(tuple(candidates), predecessor, batch.source_id, batch.receipt_id, batch.received_at)


@dataclass(frozen=True)
class CanonicalPoolObservation:
    chain_id: str
    token_mint: str
    pool_address: str
    base_mint: str
    quote_mint: str
    liquidity_usd: Decimal
    source_id: str
    reference_id: str
    observed_at: datetime
    received_at: datetime
    contract_version: str = SOURCE_CONTRACT_VERSION

    def validate(self, candidate, reference_time, freshness_policy):
        if self.contract_version != SOURCE_CONTRACT_VERSION:
            raise CycleSourceError("invalid pool contract")
        for name in ("chain_id", "token_mint", "pool_address", "base_mint", "quote_mint", "source_id", "reference_id"):
            text(getattr(self, name), name)
        if (self.chain_id, self.token_mint) != (candidate.chain_id, candidate.token_mint):
            raise CycleSourceError("pool candidate identity mismatch")
        if self.base_mint != self.token_mint or self.quote_mint == self.base_mint:
            raise CycleSourceError("pool base/quote identity mismatch")
        if type(self.liquidity_usd) is not Decimal or not self.liquidity_usd.is_finite() or self.liquidity_usd < 0:
            raise CycleSourceError("invalid canonical USD liquidity")
        fresh(self.observed_at, self.received_at, reference_time, freshness_policy)

    def target(self):
        material = {name: str(getattr(self, name)) for name in self.__dataclass_fields__}
        # Equal facts must retain the same provenance regardless of which
        # duplicate arrived last. Avoid Decimal.normalize's ambient context.
        sign, digits, exponent = self.liquidity_usd.as_tuple()
        coefficient = "".join(map(str, digits))
        trimmed = coefficient.rstrip("0")
        material["liquidity_usd"] = (
            ("-" if sign else "") + trimmed + "e" + str(exponent + len(coefficient) - len(trimmed))
            if trimmed else "0"
        )
        for name in ("observed_at", "received_at"):
            material[name] = getattr(self, name).astimezone(timezone.utc).isoformat()
        digest = hashlib.sha256(json.dumps(
            material, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return ExactPoolDiagnosticTarget(
            chain_id=self.chain_id, token_mint=self.token_mint,
            pool_address=self.pool_address, base_mint=self.base_mint, quote_mint=self.quote_mint,
            target_reference_id=self.reference_id, target_reference_digest=digest,
            target_contract_version=SOURCE_CONTRACT_VERSION,
        )


class PoolCandidateSource(Protocol):
    def pools_once(self, candidate: DiscoveredCandidate, *, reference_time: datetime) -> tuple[CanonicalPoolObservation, ...]: ...


class BoundedPoolCandidateOwner:
    def __init__(self, source: PoolCandidateSource):
        self.source = source

    def select(self, candidate, *, reference_time, freshness_policy):
        pools = self.source.pools_once(candidate, reference_time=reference_time)
        if type(pools) is not tuple or len(pools) > MAX_POOLS_PER_CANDIDATE:
            raise CycleSourceError("pool response exceeds bound or is noncanonical")
        valid = {}
        for pool in pools:
            if type(pool) is not CanonicalPoolObservation:
                raise CycleSourceError("noncanonical pool observation")
            # Invalid metric/identity/time fails closed for this candidate; no
            # alternate metric or implicit first-result selection is permitted.
            pool.validate(candidate, reference_time, freshness_policy)
            previous = valid.get(pool.pool_address)
            if previous is not None and previous != pool:
                raise CycleSourceError("contradictory duplicate pool")
            valid[pool.pool_address] = pool
        # Unary minus rounds Decimal under the ambient context. Sign-copying
        # preserves exact six-place source valuations before the tie-break.
        return min(valid.values(), key=lambda p: (p.liquidity_usd.copy_negate(), p.pool_address)) if valid else None
