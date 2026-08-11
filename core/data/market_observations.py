"""Provider-neutral token-scoped market observation evidence for P02-T07.

This module is deliberately an evidence-admission boundary.  It does not
interpret market measurements, contact a provider, persist state, or mutate
the P02-T06 snapshot supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.data.contracts import DataQuality, FreshnessPolicy, OrderingStatus, SequenceValue
from core.data.materialization import TokenUniverseEntry


P02_T07_CONTRACT_VERSION = "p02-t07-v1"
MAX_METADATA_DEPTH = 8
MAX_METADATA_ITEMS = 64
MAX_METADATA_BYTES = 8192


class MarketObservationKind(StrEnum):
    OBSERVED = "OBSERVED"
    UPDATED = "UPDATED"


class MarketObservationOutcome(StrEnum):
    OBSERVED = "OBSERVED"
    UPDATED = "UPDATED"
    DUPLICATE = "DUPLICATE"
    CONTRADICTORY = "CONTRADICTORY"
    STALE = "STALE"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    TOKEN_NOT_CURRENT = "TOKEN_NOT_CURRENT"
    RESYNCHRONIZATION_REQUIRED = "RESYNCHRONIZATION_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED = "REJECTED"


class MarketObservationReason(StrEnum):
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    INCOMPLETE_CANDIDATE = "INCOMPLETE_CANDIDATE"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    INVALID_TIMESTAMP_RELATIONSHIP = "INVALID_TIMESTAMP_RELATIONSHIP"
    NEGATIVE_DATA_AGE = "NEGATIVE_DATA_AGE"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    TOKEN_NOT_CURRENT = "TOKEN_NOT_CURRENT"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    OBSERVATION_ID_MISMATCH = "OBSERVATION_ID_MISMATCH"
    UNSUPPORTED_OBSERVATION_KIND = "UNSUPPORTED_OBSERVATION_KIND"
    UNSUPPORTED_MEASUREMENT = "UNSUPPORTED_MEASUREMENT"
    UNSUPPORTED_METADATA = "UNSUPPORTED_METADATA"
    METADATA_BOUNDS_EXCEEDED = "METADATA_BOUNDS_EXCEEDED"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    CONTRADICTORY_OBSERVATION = "CONTRADICTORY_OBSERVATION"
    OUT_OF_ORDER_SEQUENCE = "OUT_OF_ORDER_SEQUENCE"
    UPDATE_REQUIRES_PRIOR_OBSERVATION = "UPDATE_REQUIRES_PRIOR_OBSERVATION"
    OBSERVED_REQUIRES_NEW_SUBJECT = "OBSERVED_REQUIRES_NEW_SUBJECT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    RESYNCHRONIZATION_REQUIRED = "RESYNCHRONIZATION_REQUIRED"
    CANDIDATE_QUALITY_NOT_VALID = "CANDIDATE_QUALITY_NOT_VALID"


@dataclass(frozen=True)
class P02T07PredecessorContext:
    """Read-only point-in-time context from the actual P02-T06 snapshot."""

    snapshot: tuple[TokenUniverseEntry, ...]
    state_version: str
    state_digest: str
    materializer_contract_version: str
    evaluation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, tuple):
            raise ValueError("snapshot must be the tuple returned by snapshot()")
        if not all(isinstance(entry, TokenUniverseEntry) for entry in self.snapshot):
            raise ValueError("snapshot must contain TokenUniverseEntry values")
        for name, value in (
            ("state_version", self.state_version),
            ("state_digest", self.state_digest),
            ("materializer_contract_version", self.materializer_contract_version),
        ):
            if not _non_empty(value):
                raise ValueError(f"{name} is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")

    @property
    def snapshot_state_version(self) -> str:
        return self.state_version

    @property
    def snapshot_state_digest(self) -> str:
        return self.state_digest

    def contains(self, chain_id: str, token_identity: str) -> bool:
        return any(
            entry.chain_id == chain_id and entry.token_identity == token_identity
            for entry in self.snapshot
        )


@dataclass(frozen=True)
class MarketObservationCandidate:
    """Bounded provider-neutral candidate received after upstream adaptation."""

    source_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    observation_kind: MarketObservationKind | str
    observation_time: datetime
    received_time: datetime
    observation_metadata: Mapping[str, Any] = field(default_factory=dict)
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = P02_T07_CONTRACT_VERSION
    quality: DataQuality = DataQuality.VALID
    observation_id: str | None = None
    source_event_id: str | None = None
    sequence: SequenceValue = None
    source_unavailable: bool = False
    resynchronization_required: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.observation_kind, str):
            try:
                object.__setattr__(
                    self,
                    "observation_kind",
                    MarketObservationKind(self.observation_kind),
                )
            except ValueError:
                pass
        if isinstance(self.quality, str):
            try:
                object.__setattr__(self, "quality", DataQuality(self.quality))
            except ValueError:
                pass

    @property
    def token_subject(self) -> tuple[str, str]:
        return self.chain_id, self.token_identity

    @property
    def market_subject(self) -> tuple[str, str, str]:
        return self.chain_id, self.token_identity, self.market_subject_id

    @property
    def source_subject(self) -> tuple[str, str, str, str]:
        return (self.source_id, self.chain_id, self.token_identity, self.market_subject_id)


@dataclass(frozen=True)
class MarketObservationProvenance:
    source_id: str
    source_event_id: str | None
    observation_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    observation_kind: MarketObservationKind
    observation_time: datetime
    received_time: datetime
    sequence: SequenceValue
    observation_metadata: Mapping[str, Any]
    source_metadata: Mapping[str, Any]


@dataclass(frozen=True)
class AcceptedMarketObservationEvidence:
    """Immutable evidence produced only after successful admission."""

    observation_result_id: str
    observation_id: str
    source_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    observation_kind: MarketObservationKind
    quality: DataQuality
    quality_status: DataQuality
    sequence: SequenceValue
    ordering_status: OrderingStatus
    observation_time: datetime
    received_time: datetime
    processing_time: datetime
    reference_time: datetime
    data_age: timedelta
    observation_metadata: Mapping[str, Any]
    source_metadata: Mapping[str, Any]
    provenance: MarketObservationProvenance
    candidate_contract_version: str
    materializer_contract_version: str
    predecessor_state_version: str
    predecessor_state_digest: str
    local_state_version: str
    local_state_digest: str
    accepted: bool = True


@dataclass(frozen=True)
class MarketObservationResult:
    """Observable result for both accepted and rejected candidates."""

    observation_result_id: str
    observation_id: str | None
    source_id: str | None
    chain_id: str | None
    token_identity: str | None
    market_subject_id: str | None
    outcome: MarketObservationOutcome
    quality: DataQuality
    quality_status: DataQuality
    reason_codes: tuple[str, ...]
    processing_time: datetime | None
    reference_time: datetime | None
    data_age: timedelta | None
    predecessor_state_version: str | None
    predecessor_state_digest: str | None
    local_state_version: str
    local_state_digest: str
    evidence: AcceptedMarketObservationEvidence | None
    accepted: bool
    state_changed: bool

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reason_codes


@dataclass
class MarketObservationContext:
    """The only mutable state owned by P02-T07."""

    contract_version: str = P02_T07_CONTRACT_VERSION
    evaluation_id: str | None = None
    accepted_evidence: dict[tuple[str, str, str, str], AcceptedMarketObservationEvidence] = field(
        default_factory=dict
    )
    accepted_observation_fingerprints: dict[str, str] = field(default_factory=dict)
    latest_sequence_by_subject: dict[tuple[str, str, str, str], int] = field(default_factory=dict)
    resynchronization_required: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not _non_empty(self.contract_version):
            raise ValueError("contract_version is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")

    @property
    def state_version(self) -> str:
        return self.state_digest()

    def state_digest(self) -> str:
        return _digest(
            {
                "contract_version": self.contract_version,
                "evaluation_id": self.evaluation_id,
                "accepted_evidence": [
                    {
                        "key": list(key),
                        "evidence": _evidence_material(value),
                    }
                    for key, value in sorted(self.accepted_evidence.items())
                ],
                "accepted_observation_fingerprints": dict(
                    sorted(self.accepted_observation_fingerprints.items())
                ),
                "latest_sequence_by_subject": [
                    {"key": list(key), "sequence": value}
                    for key, value in sorted(self.latest_sequence_by_subject.items())
                ],
                "resynchronization_required": sorted(self.resynchronization_required),
            }
        )


# Clear aliases make the narrow public boundary easy to discover without
# creating a second implementation vocabulary.
MarketObservationProcessingContext = MarketObservationContext
MarketObservationEvidence = AcceptedMarketObservationEvidence
ObservationProcessingResult = MarketObservationResult


class MarketObservationProcessor:
    """Deterministically admit candidates against an explicit predecessor view."""

    def __init__(
        self,
        *,
        predecessor: P02T07PredecessorContext,
        context: MarketObservationContext | None = None,
        freshness_policy: FreshnessPolicy | None = None,
    ) -> None:
        if not isinstance(predecessor, P02T07PredecessorContext):
            raise ValueError("predecessor is required")
        if context is not None and not isinstance(context, MarketObservationContext):
            raise ValueError("context must be a MarketObservationContext")
        if freshness_policy is not None and not isinstance(freshness_policy, FreshnessPolicy):
            raise ValueError("freshness_policy must be a FreshnessPolicy")
        self.predecessor = predecessor
        self.context = context or MarketObservationContext()
        self.freshness_policy = freshness_policy or FreshnessPolicy()

    def process(
        self,
        candidate: MarketObservationCandidate,
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> MarketObservationResult:
        """Process one candidate using only explicit times and local state."""

        before = self.context.state_digest()
        extracted = _extract_candidate(candidate)
        if extracted is None:
            return self._rejected(
                None,
                outcome=MarketObservationOutcome.INVALID,
                quality=DataQuality.INVALID,
                reasons=(MarketObservationReason.INVALID_CANDIDATE.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        candidate, safe, extraction_reason = extracted
        normalized_kind = _observation_kind(candidate.observation_kind)
        if normalized_kind is not None and normalized_kind is not candidate.observation_kind:
            candidate = replace(candidate, observation_kind=normalized_kind)
        identity = _safe_observation_id(candidate)
        source_id = _safe_text(candidate.source_id)
        chain_id = _safe_text(candidate.chain_id)
        token_identity = _safe_text(candidate.token_identity)
        subject_id = _safe_text(candidate.market_subject_id)

        if not _aware(processing_time) or not _aware(reference_time):
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.INVALID,
                quality=DataQuality.INVALID,
                reasons=(MarketObservationReason.INVALID_TIMESTAMP.value,),
                processing_time=None,
                reference_time=None,
                before=before,
            )

        if safe is None:
            extraction_outcome = (
                MarketObservationOutcome.UNSUPPORTED
                if extraction_reason == MarketObservationReason.UNSUPPORTED_MEASUREMENT.value
                else MarketObservationOutcome.INVALID
            )
            return self._rejected(
                candidate,
                identity=identity,
                outcome=extraction_outcome,
                quality=DataQuality.INVALID,
                reasons=(extraction_reason or MarketObservationReason.INVALID_CANDIDATE.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        normalized_metadata, normalized_source_metadata, canonical_identity = safe

        if candidate.source_unavailable or candidate.quality is DataQuality.SOURCE_UNAVAILABLE:
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.SOURCE_UNAVAILABLE,
                quality=DataQuality.SOURCE_UNAVAILABLE,
                reasons=(MarketObservationReason.SOURCE_UNAVAILABLE.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        if candidate.resynchronization_required:
            self.context.resynchronization_required.add(source_id or "<invalid-source>")
            # The local condition is intentionally observable but is not
            # cleared or otherwise used as an automatic recovery protocol.
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.RESYNCHRONIZATION_REQUIRED,
                quality=DataQuality.INVALID,
                reasons=(MarketObservationReason.RESYNCHRONIZATION_REQUIRED.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        if not isinstance(candidate.quality, DataQuality) or candidate.quality is not DataQuality.VALID:
            quality = candidate.quality if isinstance(candidate.quality, DataQuality) else DataQuality.INVALID
            outcome = _quality_outcome(quality)
            return self._rejected(
                candidate,
                identity=identity,
                outcome=outcome,
                quality=quality,
                reasons=(MarketObservationReason.CANDIDATE_QUALITY_NOT_VALID.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )

        validation = _validate_candidate(
            candidate,
            normalized_metadata,
            normalized_source_metadata,
            canonical_identity,
            self.freshness_policy,
            reference_time,
        )
        if validation is not None:
            outcome, quality, reason = validation
            return self._rejected(
                candidate,
                identity=identity,
                outcome=outcome,
                quality=quality,
                reasons=(reason,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )

        assert identity is not None
        if not self.predecessor.contains(candidate.chain_id, candidate.token_identity):
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.TOKEN_NOT_CURRENT,
                quality=DataQuality.INCOMPLETE,
                reasons=(MarketObservationReason.TOKEN_NOT_CURRENT.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        fingerprint = _candidate_fingerprint(candidate, normalized_metadata, normalized_source_metadata)
        prior_fingerprint = self.context.accepted_observation_fingerprints.get(identity)
        if prior_fingerprint is not None:
            if prior_fingerprint == fingerprint:
                return self._rejected(
                    candidate,
                    identity=identity,
                    outcome=MarketObservationOutcome.DUPLICATE,
                    quality=DataQuality.DUPLICATE,
                    reasons=(MarketObservationReason.DUPLICATE_OBSERVATION.value,),
                    processing_time=processing_time,
                    reference_time=reference_time,
                    before=before,
                )
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.CONTRADICTORY,
                quality=DataQuality.CONTRADICTORY,
                reasons=(MarketObservationReason.CONTRADICTORY_OBSERVATION.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )

        subject_key = candidate.source_subject
        previous = self.context.accepted_evidence.get(subject_key)
        if candidate.observation_kind is MarketObservationKind.UPDATED and previous is None:
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.REJECTED,
                quality=DataQuality.INCOMPLETE,
                reasons=(MarketObservationReason.UPDATE_REQUIRES_PRIOR_OBSERVATION.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )
        if candidate.observation_kind is MarketObservationKind.OBSERVED and previous is not None:
            return self._rejected(
                candidate,
                identity=identity,
                outcome=MarketObservationOutcome.REJECTED,
                quality=DataQuality.INCOMPLETE,
                reasons=(MarketObservationReason.OBSERVED_REQUIRES_NEW_SUBJECT.value,),
                processing_time=processing_time,
                reference_time=reference_time,
                before=before,
            )

        ordering = OrderingStatus.NOT_PROVIDED
        if isinstance(candidate.sequence, int) and not isinstance(candidate.sequence, bool):
            old_sequence = self.context.latest_sequence_by_subject.get(subject_key)
            if old_sequence is None:
                ordering = OrderingStatus.FIRST
            elif candidate.sequence <= old_sequence:
                return self._rejected(
                    candidate,
                    identity=identity,
                    outcome=MarketObservationOutcome.OUT_OF_ORDER,
                    quality=DataQuality.OUT_OF_ORDER,
                    reasons=(MarketObservationReason.OUT_OF_ORDER_SEQUENCE.value,),
                    processing_time=processing_time,
                    reference_time=reference_time,
                    before=before,
                )
            else:
                ordering = OrderingStatus.IN_ORDER

        data_age = reference_time - candidate.observation_time
        provenance = MarketObservationProvenance(
            source_id=candidate.source_id,
            source_event_id=candidate.source_event_id,
            observation_id=identity,
            chain_id=candidate.chain_id,
            token_identity=candidate.token_identity,
            market_subject_id=candidate.market_subject_id,
            observation_kind=candidate.observation_kind,
            observation_time=candidate.observation_time,
            received_time=candidate.received_time,
            sequence=candidate.sequence,
            observation_metadata=_freeze(normalized_metadata),
            source_metadata=_freeze(normalized_source_metadata),
        )
        # Build the evidence after the state transition so its local version
        # describes the accepted state it belongs to.
        result_outcome = (
            MarketObservationOutcome.OBSERVED
            if previous is None
            else MarketObservationOutcome.UPDATED
        )
        provisional = _evidence_material_without_local(
            candidate,
            identity,
            ordering,
            data_age,
            provenance,
            self.predecessor,
            self.context,
            processing_time,
            reference_time,
        )
        provisional_id = _digest(
            {
                "evaluation_id": self.context.evaluation_id,
                "observation_id": identity,
                "outcome": result_outcome.value,
                "processing_time": _timestamp(processing_time),
                "reference_time": _timestamp(reference_time),
                "predecessor_state_version": self.predecessor.state_version,
            }
        )
        self.context.accepted_observation_fingerprints[identity] = fingerprint
        if isinstance(candidate.sequence, int) and not isinstance(candidate.sequence, bool):
            self.context.latest_sequence_by_subject[subject_key] = candidate.sequence
        local_after = self.context.state_digest()
        evidence = AcceptedMarketObservationEvidence(
            **provisional,
            observation_result_id=provisional_id,
            local_state_version=local_after,
            local_state_digest=local_after,
        )
        self.context.accepted_evidence[subject_key] = evidence
        final_local = self.context.state_digest()
        if final_local != local_after:
            evidence = AcceptedMarketObservationEvidence(
                **{
                    **provisional,
                    "observation_result_id": provisional_id,
                    "local_state_version": final_local,
                    "local_state_digest": final_local,
                }
            )
            self.context.accepted_evidence[subject_key] = evidence
        return MarketObservationResult(
            observation_result_id=provisional_id,
            observation_id=identity,
            source_id=candidate.source_id,
            chain_id=candidate.chain_id,
            token_identity=candidate.token_identity,
            market_subject_id=candidate.market_subject_id,
            outcome=result_outcome,
            quality=DataQuality.VALID,
            quality_status=DataQuality.VALID,
            reason_codes=(),
            processing_time=processing_time,
            reference_time=reference_time,
            data_age=data_age,
            predecessor_state_version=self.predecessor.state_version,
            predecessor_state_digest=self.predecessor.state_digest,
            local_state_version=final_local,
            local_state_digest=final_local,
            evidence=evidence,
            accepted=True,
            state_changed=True,
        )

    def _rejected(
        self,
        candidate: MarketObservationCandidate | None,
        *,
        identity: str | None = None,
        outcome: MarketObservationOutcome,
        quality: DataQuality,
        reasons: tuple[str, ...],
        processing_time: datetime | None,
        reference_time: datetime | None,
        before: str,
    ) -> MarketObservationResult:
        identity = identity or (_safe_observation_id(candidate) if candidate is not None else None)
        result_id = _digest(
            {
                "evaluation_id": self.context.evaluation_id,
                "observation_id": identity,
                "source_id": _safe_text(getattr(candidate, "source_id", None)),
                "outcome": outcome.value,
                "processing_time": _timestamp(processing_time),
                "reference_time": _timestamp(reference_time),
                "predecessor_state_version": self.predecessor.state_version,
            }
        )
        return MarketObservationResult(
            observation_result_id=result_id,
            observation_id=identity,
            source_id=_safe_text(getattr(candidate, "source_id", None)),
            chain_id=_safe_text(getattr(candidate, "chain_id", None)),
            token_identity=_safe_text(getattr(candidate, "token_identity", None)),
            market_subject_id=_safe_text(getattr(candidate, "market_subject_id", None)),
            outcome=outcome,
            quality=quality,
            quality_status=quality,
            reason_codes=reasons,
            processing_time=processing_time if _aware(processing_time) else None,
            reference_time=reference_time if _aware(reference_time) else None,
            data_age=_data_age(candidate, reference_time),
            predecessor_state_version=self.predecessor.state_version,
            predecessor_state_digest=self.predecessor.state_digest,
            local_state_version=before,
            local_state_digest=before,
            evidence=None,
            accepted=False,
            state_changed=False,
        )


def process_market_observation(
    candidate: MarketObservationCandidate,
    *,
    predecessor: P02T07PredecessorContext,
    context: MarketObservationContext | None = None,
    processing_time: datetime,
    reference_time: datetime,
    freshness_policy: FreshnessPolicy | None = None,
) -> MarketObservationResult:
    """Small functional entry point for one-shot processing."""

    return MarketObservationProcessor(
        predecessor=predecessor,
        context=context,
        freshness_policy=freshness_policy,
    ).process(candidate, processing_time=processing_time, reference_time=reference_time)


def derive_observation_id(candidate: MarketObservationCandidate) -> str:
    """Return the deterministic identity required by P02-T07."""

    if not isinstance(candidate, MarketObservationCandidate):
        raise ValueError("candidate is required")
    return _observation_id(candidate)


def _validate_candidate(
    candidate: MarketObservationCandidate,
    metadata: dict[str, Any] | None,
    source_metadata: dict[str, Any] | None,
    identity: str | None,
    policy: FreshnessPolicy,
    reference_time: datetime,
) -> tuple[MarketObservationOutcome, DataQuality, str] | None:
    if not _non_empty(candidate.source_id) or not _non_empty(candidate.chain_id) or not _non_empty(
        candidate.token_identity
    ) or not _non_empty(candidate.market_subject_id) or not _non_empty(candidate.contract_version):
        return (
            MarketObservationOutcome.INCOMPLETE,
            DataQuality.INCOMPLETE,
            MarketObservationReason.INCOMPLETE_CANDIDATE.value,
        )
    if not _aware(candidate.observation_time) or not _aware(candidate.received_time):
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.INVALID_TIMESTAMP.value,
        )
    if candidate.observation_time > candidate.received_time or candidate.observation_time > reference_time:
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.INVALID_TIMESTAMP_RELATIONSHIP.value,
        )
    data_age = reference_time - candidate.observation_time
    if data_age < timedelta(0):
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.NEGATIVE_DATA_AGE.value,
        )
    if policy.stale_after is not None and data_age > policy.stale_after:
        return (
            MarketObservationOutcome.STALE,
            DataQuality.STALE,
            MarketObservationReason.STALE_OBSERVATION.value,
        )
    if candidate.observation_kind not in (MarketObservationKind.OBSERVED, MarketObservationKind.UPDATED):
        return (
            MarketObservationOutcome.UNSUPPORTED,
            DataQuality.INVALID,
            MarketObservationReason.UNSUPPORTED_OBSERVATION_KIND.value,
        )
    if not _valid_sequence(candidate.sequence):
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.INVALID_CANDIDATE.value,
        )
    if not _non_empty(candidate.source_event_id) and candidate.source_event_id is not None:
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.INVALID_IDENTITY.value,
        )
    if identity is None or (
        candidate.observation_id is not None and candidate.observation_id != identity
    ):
        return (
            MarketObservationOutcome.INVALID,
            DataQuality.INVALID,
            MarketObservationReason.OBSERVATION_ID_MISMATCH.value,
        )
    return None


def _extract_candidate(
    value: Any,
) -> tuple[
    MarketObservationCandidate,
    tuple[dict[str, Any], dict[str, Any], str] | None,
    str | None,
] | None:
    if not isinstance(value, MarketObservationCandidate):
        return None
    try:
        metadata = _bounded_canonical_mapping(value.observation_metadata)
        source_metadata = _bounded_canonical_mapping(value.source_metadata)
        try:
            _reject_measurements(metadata)
            _reject_measurements(source_metadata)
        except ValueError:
            return value, None, MarketObservationReason.UNSUPPORTED_MEASUREMENT.value
        identity = _observation_id(value)
        if value.observation_id is not None and value.observation_id != identity:
            return value, None, MarketObservationReason.OBSERVATION_ID_MISMATCH.value
        return value, (metadata, source_metadata, identity), None
    except ValueError as exc:
        reason = (
            MarketObservationReason.METADATA_BOUNDS_EXCEEDED.value
            if "bounded" in str(exc)
            else MarketObservationReason.UNSUPPORTED_METADATA.value
        )
        return value, None, reason


def _safe_observation_id(candidate: MarketObservationCandidate | None) -> str | None:
    if candidate is None:
        return None
    try:
        return _observation_id(candidate)
    except ValueError:
        safe = {
            "source_id": _safe_text(candidate.source_id),
            "source_event_id": _safe_text(candidate.source_event_id),
            "chain_id": _safe_text(candidate.chain_id),
            "token_identity": _safe_text(candidate.token_identity),
            "market_subject_id": _safe_text(candidate.market_subject_id),
        }
        return f"invalid:{_digest(safe)}"


def _observation_id(candidate: MarketObservationCandidate) -> str:
    if not _non_empty(candidate.source_id):
        raise ValueError("source_id is required")
    if _non_empty(candidate.source_event_id):
        material = {"source_id": candidate.source_id, "source_event_id": candidate.source_event_id}
    else:
        metadata = _bounded_canonical_mapping(candidate.observation_metadata)
        material = {
            "source_id": candidate.source_id,
            "chain_id": candidate.chain_id,
            "token_identity": candidate.token_identity,
            "market_subject_id": candidate.market_subject_id,
            "observation_time": _timestamp(candidate.observation_time),
            "sequence": candidate.sequence,
            "observation_metadata": metadata,
        }
    return _digest(material)


def _candidate_fingerprint(
    candidate: MarketObservationCandidate,
    metadata: dict[str, Any],
    source_metadata: dict[str, Any],
) -> str:
    return _digest(
        {
            "observation_id": _observation_id(candidate),
            "source_id": candidate.source_id,
            "chain_id": candidate.chain_id,
            "token_identity": candidate.token_identity,
            "market_subject_id": candidate.market_subject_id,
            "observation_kind": _enum_value(candidate.observation_kind),
            "observation_time": _timestamp(candidate.observation_time),
            "received_time": _timestamp(candidate.received_time),
            "sequence": candidate.sequence,
            "observation_metadata": metadata,
            "source_metadata": source_metadata,
            "contract_version": candidate.contract_version,
            "quality": candidate.quality.value,
            "source_event_id": candidate.source_event_id,
        }
    )


def _evidence_material_without_local(
    candidate: MarketObservationCandidate,
    identity: str,
    ordering: OrderingStatus,
    data_age: timedelta,
    provenance: MarketObservationProvenance,
    predecessor: P02T07PredecessorContext,
    context: MarketObservationContext,
    processing_time: datetime,
    reference_time: datetime,
) -> dict[str, Any]:
    return {
        "observation_id": identity,
        "source_id": candidate.source_id,
        "chain_id": candidate.chain_id,
        "token_identity": candidate.token_identity,
        "market_subject_id": candidate.market_subject_id,
        "observation_kind": candidate.observation_kind,
        "quality": DataQuality.VALID,
        "quality_status": DataQuality.VALID,
        "sequence": candidate.sequence,
        "ordering_status": ordering,
        "observation_time": candidate.observation_time,
        "received_time": candidate.received_time,
        "processing_time": processing_time,
        "reference_time": reference_time,
        "data_age": data_age,
        "observation_metadata": provenance.observation_metadata,
        "source_metadata": provenance.source_metadata,
        "provenance": provenance,
        "candidate_contract_version": candidate.contract_version,
        "materializer_contract_version": predecessor.materializer_contract_version,
        "predecessor_state_version": predecessor.state_version,
        "predecessor_state_digest": predecessor.state_digest,
        "accepted": True,
    }


def _evidence_material(evidence: AcceptedMarketObservationEvidence) -> dict[str, Any]:
    """Canonical state material; local digest fields are attestations, not inputs."""

    return {
        "observation_result_id": evidence.observation_result_id,
        "observation_id": evidence.observation_id,
        "source_id": evidence.source_id,
        "chain_id": evidence.chain_id,
        "token_identity": evidence.token_identity,
        "market_subject_id": evidence.market_subject_id,
        "observation_kind": evidence.observation_kind,
        "quality": evidence.quality,
        "quality_status": evidence.quality_status,
        "sequence": evidence.sequence,
        "ordering_status": evidence.ordering_status,
        "observation_time": evidence.observation_time,
        "received_time": evidence.received_time,
        "processing_time": evidence.processing_time,
        "reference_time": evidence.reference_time,
        "data_age": evidence.data_age,
        "observation_metadata": evidence.observation_metadata,
        "source_metadata": evidence.source_metadata,
        "provenance": evidence.provenance,
        "candidate_contract_version": evidence.candidate_contract_version,
        "materializer_contract_version": evidence.materializer_contract_version,
        "predecessor_state_version": evidence.predecessor_state_version,
        "predecessor_state_digest": evidence.predecessor_state_digest,
        "accepted": evidence.accepted,
    }


def _bounded_canonical_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a mapping")
    result = _canonicalize(value, depth=0, counter=[0])
    if not isinstance(result, dict):
        raise ValueError("metadata must be a mapping")
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds the bounded size")
    return result


def _reject_measurements(value: Any) -> None:
    unsupported = {
        "price",
        "volume",
        "liquidity",
        "reserves",
        "reserve",
        "transaction_count",
        "swap_amount",
        "buy_sell_pressure",
        "buy_pressure",
        "sell_pressure",
        "order_book",
        "pool_state",
        "transaction_flow",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower().replace("-", "_") in unsupported:
                raise ValueError("unsupported market measurement")
            _reject_measurements(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_measurements(child)


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    sensitive_terms = (
        "secret",
        "password",
        "credential",
        "api_key",
        "access_token",
        "private_key",
        "seed_phrase",
        "signing",
    )
    return any(term in normalized for term in sensitive_terms)


def _canonicalize(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata depth exceeds the bounded limit")
    counter[0] += 1
    if counter[0] > MAX_METADATA_ITEMS:
        raise ValueError("metadata item count exceeds the bounded limit")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("metadata keys must be strings")
        if any(_sensitive_key(key) for key in value):
            raise ValueError("sensitive metadata is not accepted")
        return {
            key: _canonicalize(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item, depth=depth + 1, counter=counter) for item in value]
    raise ValueError("opaque metadata is not accepted")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_canonicalize_general(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _canonicalize_general(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return value // timedelta(microseconds=1)
    if isinstance(value, Mapping):
        return {str(key): _canonicalize_general(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_canonicalize_general(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _canonicalize_general(getattr(value, name))
            for name in sorted(value.__dataclass_fields__)
        }
    raise ValueError("value cannot be deterministically serialized")


def _quality_outcome(quality: DataQuality) -> MarketObservationOutcome:
    try:
        return MarketObservationOutcome(quality.value)
    except ValueError:
        return MarketObservationOutcome.REJECTED


def _observation_kind(value: Any) -> MarketObservationKind | None:
    if isinstance(value, MarketObservationKind):
        return value
    if isinstance(value, str):
        try:
            return MarketObservationKind(value)
        except ValueError:
            return None
    return None


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, StrEnum) else value


def _data_age(candidate: Any, reference_time: Any) -> timedelta | None:
    observation_time = getattr(candidate, "observation_time", None)
    if _aware(observation_time) and _aware(reference_time):
        return reference_time - observation_time
    return None


def _timestamp(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if _aware(value) else None


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_text(value: Any) -> str | None:
    return value if _non_empty(value) else None


def _valid_sequence(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, str)


__all__ = [
    "AcceptedMarketObservationEvidence",
    "MarketObservationCandidate",
    "MarketObservationContext",
    "MarketObservationEvidence",
    "MarketObservationKind",
    "MarketObservationOutcome",
    "MarketObservationProcessingContext",
    "MarketObservationProcessor",
    "MarketObservationProvenance",
    "MarketObservationReason",
    "MarketObservationResult",
    "ObservationProcessingResult",
    "P02T07PredecessorContext",
    "derive_observation_id",
    "process_market_observation",
]