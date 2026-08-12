"""Provider-neutral market-intelligence representation for the P02 boundary.

This module accepts already materialized P02-T08 state references and bounded,
provider-neutral values.  It does not collect data, calculate measurements,
aggregate sources, or mutate upstream state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias

from core.data.contracts import DataQuality, OrderingStatus, SequenceValue
from core.data.market_state import (
    MarketStateEntry,
    MarketStateKey,
    P02_T08_CONTRACT_VERSION,
)


P02_MARKET_INTELLIGENCE_CONTRACT_VERSION = "p02-market-intelligence-v1"
MAX_METADATA_DEPTH = 8
MAX_METADATA_ITEMS = 64
MAX_METADATA_BYTES = 8192

MarketIntelligenceSubjectKey: TypeAlias = tuple[str, str, str, str, str]
MarketIntelligenceObservationKey: TypeAlias = tuple[str, str, str, str, str, str]


class MarketIntelligenceCategory(StrEnum):
    """Reserved representation categories; none define measurement semantics."""

    PRICE = "PRICE"
    VOLUME = "VOLUME"
    LIQUIDITY = "LIQUIDITY"
    POOL_STATE = "POOL_STATE"
    SWAP_FLOW = "SWAP_FLOW"
    TRANSACTION_FLOW = "TRANSACTION_FLOW"
    FRESHNESS = "FRESHNESS"
    STREAM_HEALTH = "STREAM_HEALTH"


class MarketIntelligenceValueKind(StrEnum):
    """The explicit shape approved for a provider-neutral category value."""

    ANY = "ANY"
    SCALAR = "SCALAR"
    MAPPING = "MAPPING"
    SEQUENCE = "SEQUENCE"


class MarketIntelligenceOutcome(StrEnum):
    REPRESENTED = "REPRESENTED"
    UPDATED = "UPDATED"
    DUPLICATE = "DUPLICATE"
    CONTRADICTORY = "CONTRADICTORY"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED = "REJECTED"


class MarketIntelligenceReason(StrEnum):
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    INCOMPLETE_OBSERVATION = "INCOMPLETE_OBSERVATION"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    OBSERVATION_ID_MISMATCH = "OBSERVATION_ID_MISMATCH"
    INVALID_UPSTREAM_REFERENCE = "INVALID_UPSTREAM_REFERENCE"
    UPSTREAM_IDENTITY_MISMATCH = "UPSTREAM_IDENTITY_MISMATCH"
    UNSUPPORTED_CATEGORY = "UNSUPPORTED_CATEGORY"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    VALUE_KIND_MISMATCH = "VALUE_KIND_MISMATCH"
    UNSUPPORTED_METADATA = "UNSUPPORTED_METADATA"
    METADATA_BOUNDS_EXCEEDED = "METADATA_BOUNDS_EXCEEDED"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    INVALID_TIMESTAMP_RELATIONSHIP = "INVALID_TIMESTAMP_RELATIONSHIP"
    INVALID_DATA_AGE = "INVALID_DATA_AGE"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    CONTRADICTORY_OBSERVATION = "CONTRADICTORY_OBSERVATION"
    OUT_OF_ORDER_SEQUENCE = "OUT_OF_ORDER_SEQUENCE"
    UNCOMPUTABLE_DIGEST = "UNCOMPUTABLE_DIGEST"


P02_T09_CONTRACT_VERSION = "p02-t09-v1"


class DecisionReadyAssessmentStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    KNOWN = "KNOWN"
    PASS = "PASS"
    FAIL = "FAIL"


class DecisionReadyEligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


class DecisionReadyOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    INVALID = "INVALID"
    REJECTED = "REJECTED"


class DecisionReadyReason(StrEnum):
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    INCOMPLETE_IDENTITY = "INCOMPLETE_IDENTITY"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    MISSING_MARKET_SNAPSHOT = "MISSING_MARKET_SNAPSHOT"
    INVALID_MARKET_SNAPSHOT = "INVALID_MARKET_SNAPSHOT"
    INCOMPLETE_MARKET_DATA = "INCOMPLETE_MARKET_DATA"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    TIMESTAMP_MISMATCH = "TIMESTAMP_MISMATCH"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"
    EVIDENCE_SOURCE_MISMATCH = "EVIDENCE_SOURCE_MISMATCH"
    INVALID_QUALITY = "INVALID_QUALITY"
    QUALITY_INCONSISTENT = "QUALITY_INCONSISTENT"
    STALE_DATA = "STALE_DATA"
    INVALID_SAFETY_STATUS = "INVALID_SAFETY_STATUS"
    INVALID_SELLABILITY_STATUS = "INVALID_SELLABILITY_STATUS"
    INVALID_ELIGIBILITY_STATUS = "INVALID_ELIGIBILITY_STATUS"
    ELIGIBILITY_REASON_REQUIRED = "ELIGIBILITY_REASON_REQUIRED"
    INVALID_UPSTREAM_REFERENCE = "INVALID_UPSTREAM_REFERENCE"


@dataclass(frozen=True)
class DecisionReadyIdentity:
    """Explicit asset identity; optional display fields are never inferred."""

    chain_id: str | None
    token_identity: str | None
    source_id: str | None
    symbol: str | None = None
    decimals: int | None = None
    market_subject_id: str | None = None
    market_group_id: str | None = None
    exposure_identity: str | None = None


@dataclass(frozen=True)
class DecisionReadyEvidence:
    """One auditable field observation with bounded provenance."""

    source_id: str | None
    observed_at: datetime | None
    field: str | None
    value: Any
    provenance: Mapping[str, Any]
    observation_id: str | None = None
    upstream_state_version: str | None = None
    upstream_state_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _freeze(_canonical_value(self.value)))
        object.__setattr__(
            self,
            "provenance",
            _freeze(_canonical_mapping(self.provenance)),
        )


@dataclass(frozen=True)
class DecisionReadyMarketSnapshot:
    """Point-in-time values carried forward from the P02 market layers."""

    observed_at: datetime | None
    values: Mapping[str, Any]
    source_id: str | None = None
    upstream: MarketIntelligenceStateReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _freeze(_canonical_mapping(self.values)))


@dataclass(frozen=True)
class DecisionReadyLiquidity:
    status: DecisionReadyAssessmentStatus | str = DecisionReadyAssessmentStatus.UNKNOWN
    observed_at: datetime | None = None
    values: Mapping[str, Any] = field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _freeze(_canonical_mapping(self.values)))


@dataclass(frozen=True)
class DecisionReadyMarketActivity:
    observed_at: datetime | None = None
    values: Mapping[str, Any] = field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _freeze(_canonical_mapping(self.values)))


@dataclass(frozen=True)
class DecisionReadySafety:
    """Safety boundary only; unknown remains unknown until evidence exists."""

    safety_status: DecisionReadyAssessmentStatus | str = DecisionReadyAssessmentStatus.UNKNOWN
    liquidity_status: DecisionReadyAssessmentStatus | str = DecisionReadyAssessmentStatus.UNKNOWN
    contract_status: DecisionReadyAssessmentStatus | str = DecisionReadyAssessmentStatus.UNKNOWN
    holder_concentration_status: DecisionReadyAssessmentStatus | str = (
        DecisionReadyAssessmentStatus.UNKNOWN
    )
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionReadySellability:
    """Exit evidence boundary; this does not simulate or execute a sale."""

    sellability_status: DecisionReadyAssessmentStatus | str = (
        DecisionReadyAssessmentStatus.UNKNOWN
    )
    exit_evidence_status: DecisionReadyAssessmentStatus | str = (
        DecisionReadyAssessmentStatus.UNKNOWN
    )
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionReadyDataQuality:
    overall_status: DataQuality | str
    completeness: bool
    freshness_status: DataQuality | str
    source_count: int
    latest_observed_at: datetime | None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionReadyEligibility:
    status: DecisionReadyEligibilityStatus | str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionReadyCandidate:
    """Validated evidence container, not a signal or trading decision."""

    identity: DecisionReadyIdentity | None
    market_snapshot: DecisionReadyMarketSnapshot | None
    liquidity: DecisionReadyLiquidity
    market_activity: DecisionReadyMarketActivity
    safety: DecisionReadySafety
    sellability: DecisionReadySellability
    data_quality: DecisionReadyDataQuality
    evidence: tuple[DecisionReadyEvidence, ...]
    observed_at: datetime | None
    eligibility: DecisionReadyEligibility
    contract_version: str = P02_T09_CONTRACT_VERSION


@dataclass(frozen=True)
class DecisionReadyValidationResult:
    candidate: DecisionReadyCandidate | None
    outcome: DecisionReadyOutcome
    quality: DataQuality
    reason_codes: tuple[str, ...]
    accepted: bool

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reason_codes


def validate_decision_ready_candidate(
    candidate: DecisionReadyCandidate | object,
) -> DecisionReadyValidationResult:
    """Validate the P02-T09 boundary without deriving a trading decision."""

    if not isinstance(candidate, DecisionReadyCandidate):
        return _decision_ready_rejection(
            None,
            DecisionReadyOutcome.INVALID,
            DataQuality.INVALID,
            DecisionReadyReason.INVALID_CANDIDATE.value,
        )

    reasons: list[str] = []
    identity = candidate.identity
    liquidity = candidate.liquidity
    market_activity = candidate.market_activity
    safety = candidate.safety
    sellability = candidate.sellability
    if not isinstance(liquidity, DecisionReadyLiquidity):
        reasons.append(DecisionReadyReason.INVALID_CANDIDATE.value)
        liquidity = DecisionReadyLiquidity()
    if not isinstance(market_activity, DecisionReadyMarketActivity):
        reasons.append(DecisionReadyReason.INVALID_CANDIDATE.value)
        market_activity = DecisionReadyMarketActivity()
    if not isinstance(safety, DecisionReadySafety):
        reasons.append(DecisionReadyReason.INVALID_SAFETY_STATUS.value)
        safety = DecisionReadySafety()
    if not isinstance(sellability, DecisionReadySellability):
        reasons.append(DecisionReadyReason.INVALID_SELLABILITY_STATUS.value)
        sellability = DecisionReadySellability()
    if not isinstance(identity, DecisionReadyIdentity):
        reasons.append(DecisionReadyReason.INCOMPLETE_IDENTITY.value)
    else:
        required = (identity.chain_id, identity.token_identity, identity.source_id)
        if any(value is None for value in required):
            reasons.append(DecisionReadyReason.INCOMPLETE_IDENTITY.value)
        elif any(not _non_empty(value) for value in required):
            reasons.append(DecisionReadyReason.INVALID_IDENTITY.value)
        if identity.symbol is not None and not _non_empty(identity.symbol):
            reasons.append(DecisionReadyReason.INVALID_IDENTITY.value)
        if identity.decimals is not None and (
            not isinstance(identity.decimals, int)
            or isinstance(identity.decimals, bool)
            or identity.decimals < 0
        ):
            reasons.append(DecisionReadyReason.INVALID_IDENTITY.value)
        for optional_identity in (
            identity.market_subject_id,
            identity.market_group_id,
            identity.exposure_identity,
        ):
            if optional_identity is not None and not _non_empty(optional_identity):
                reasons.append(DecisionReadyReason.INVALID_IDENTITY.value)

    if not _aware(candidate.observed_at):
        reasons.append(
            DecisionReadyReason.INVALID_TIMESTAMP.value
            if candidate.observed_at is not None
            else DecisionReadyReason.INCOMPLETE_MARKET_DATA.value
        )

    snapshot = candidate.market_snapshot
    if not isinstance(snapshot, DecisionReadyMarketSnapshot):
        reasons.append(DecisionReadyReason.MISSING_MARKET_SNAPSHOT.value)
    else:
        if not _aware(snapshot.observed_at):
            reasons.append(
                DecisionReadyReason.INVALID_TIMESTAMP.value
                if snapshot.observed_at is not None
                else DecisionReadyReason.INVALID_MARKET_SNAPSHOT.value
            )
        elif _aware(candidate.observed_at) and snapshot.observed_at != candidate.observed_at:
            reasons.append(DecisionReadyReason.TIMESTAMP_MISMATCH.value)
        if not snapshot.values and not liquidity.values and not market_activity.values:
            reasons.append(DecisionReadyReason.INCOMPLETE_MARKET_DATA.value)
        if snapshot.upstream is None:
            reasons.append(DecisionReadyReason.INVALID_UPSTREAM_REFERENCE.value)
        elif isinstance(identity, DecisionReadyIdentity):
            if (
                snapshot.upstream.source_id != identity.source_id
                or snapshot.upstream.chain_id != identity.chain_id
                or snapshot.upstream.token_identity != identity.token_identity
            ):
                reasons.append(DecisionReadyReason.INVALID_UPSTREAM_REFERENCE.value)
            if snapshot.source_id is not None and snapshot.source_id != identity.source_id:
                reasons.append(DecisionReadyReason.INVALID_UPSTREAM_REFERENCE.value)

    if not isinstance(candidate.evidence, tuple) or not candidate.evidence:
        reasons.append(DecisionReadyReason.INCOMPLETE_EVIDENCE.value)
        evidence_sources: set[str] = set()
        latest_evidence_time: datetime | None = None
    else:
        evidence_sources = set()
        latest_evidence_time = None
        for evidence in candidate.evidence:
            if not isinstance(evidence, DecisionReadyEvidence):
                reasons.append(DecisionReadyReason.INVALID_EVIDENCE.value)
                continue
            if not _non_empty(evidence.source_id):
                reasons.append(DecisionReadyReason.INCOMPLETE_EVIDENCE.value)
            else:
                evidence_sources.add(evidence.source_id)
            if not _aware(evidence.observed_at):
                reasons.append(DecisionReadyReason.INVALID_TIMESTAMP.value)
            elif _aware(candidate.observed_at) and evidence.observed_at > candidate.observed_at:
                reasons.append(DecisionReadyReason.TIMESTAMP_MISMATCH.value)
            if not _non_empty(evidence.field):
                reasons.append(DecisionReadyReason.INCOMPLETE_EVIDENCE.value)
            if not evidence.provenance:
                reasons.append(DecisionReadyReason.INCOMPLETE_EVIDENCE.value)
            if (
                isinstance(identity, DecisionReadyIdentity)
                and _non_empty(evidence.source_id)
                and evidence.source_id != identity.source_id
            ):
                reasons.append(DecisionReadyReason.EVIDENCE_SOURCE_MISMATCH.value)
            if _aware(evidence.observed_at) and (
                latest_evidence_time is None or evidence.observed_at > latest_evidence_time
            ):
                latest_evidence_time = evidence.observed_at

    quality = candidate.data_quality
    if not isinstance(quality, DecisionReadyDataQuality):
        reasons.append(DecisionReadyReason.INVALID_QUALITY.value)
        quality_status = None
        freshness_status = None
    else:
        quality_status = _data_quality(quality.overall_status)
        freshness_status = _data_quality(quality.freshness_status)
        allowed_quality = {
            DataQuality.VALID,
            DataQuality.STALE,
            DataQuality.INCOMPLETE,
            DataQuality.INVALID,
        }
        if quality_status not in allowed_quality or freshness_status not in allowed_quality:
            reasons.append(DecisionReadyReason.INVALID_QUALITY.value)
        if not isinstance(quality.completeness, bool):
            reasons.append(DecisionReadyReason.INVALID_QUALITY.value)
        if not isinstance(quality.source_count, int) or isinstance(quality.source_count, bool) or quality.source_count < 0:
            reasons.append(DecisionReadyReason.INVALID_QUALITY.value)
        elif evidence_sources and quality.source_count != len(evidence_sources):
            reasons.append(DecisionReadyReason.QUALITY_INCONSISTENT.value)
        if not _aware(quality.latest_observed_at):
            reasons.append(DecisionReadyReason.INVALID_TIMESTAMP.value)
        elif latest_evidence_time is not None and quality.latest_observed_at != latest_evidence_time:
            reasons.append(DecisionReadyReason.QUALITY_INCONSISTENT.value)
        if quality_status is DataQuality.VALID and not quality.completeness:
            reasons.append(DecisionReadyReason.QUALITY_INCONSISTENT.value)
        if quality_status is DataQuality.INCOMPLETE and quality.completeness:
            reasons.append(DecisionReadyReason.QUALITY_INCONSISTENT.value)
        if DataQuality.STALE in {quality_status, freshness_status}:
            reasons.append(DecisionReadyReason.STALE_DATA.value)

    if _assessment_status(safety.safety_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SAFETY_STATUS.value)
    if _assessment_status(safety.liquidity_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SAFETY_STATUS.value)
    if _assessment_status(safety.contract_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SAFETY_STATUS.value)
    if _assessment_status(safety.holder_concentration_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SAFETY_STATUS.value)
    if _assessment_status(sellability.sellability_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SELLABILITY_STATUS.value)
    if _assessment_status(sellability.exit_evidence_status) is None:
        reasons.append(DecisionReadyReason.INVALID_SELLABILITY_STATUS.value)

    eligibility = candidate.eligibility
    eligibility_status = (
        eligibility.status
        if isinstance(eligibility, DecisionReadyEligibility)
        else None
    )
    if _eligibility_status(eligibility_status) is None:
        reasons.append(DecisionReadyReason.INVALID_ELIGIBILITY_STATUS.value)
    elif (
        _eligibility_status(eligibility_status)
        in {DecisionReadyEligibilityStatus.UNKNOWN, DecisionReadyEligibilityStatus.INELIGIBLE}
        and not eligibility.reasons
    ):
        reasons.append(DecisionReadyReason.ELIGIBILITY_REASON_REQUIRED.value)

    if reasons:
        unique_reasons = tuple(dict.fromkeys(reasons))
        if DataQuality.STALE in {quality_status, freshness_status}:
            return _decision_ready_rejection(
                candidate,
                DecisionReadyOutcome.STALE,
                DataQuality.STALE,
                *unique_reasons,
            )
        outcome = (
            DecisionReadyOutcome.INCOMPLETE
            if any(
                reason
                in {
                    DecisionReadyReason.INCOMPLETE_IDENTITY.value,
                    DecisionReadyReason.MISSING_MARKET_SNAPSHOT.value,
                    DecisionReadyReason.INCOMPLETE_MARKET_DATA.value,
                    DecisionReadyReason.INCOMPLETE_EVIDENCE.value,
                }
                for reason in unique_reasons
            )
            else DecisionReadyOutcome.INVALID
        )
        return _decision_ready_rejection(
            candidate,
            outcome,
            DataQuality.INCOMPLETE if outcome is DecisionReadyOutcome.INCOMPLETE else DataQuality.INVALID,
            *unique_reasons,
        )

    assert quality_status is not None
    return DecisionReadyValidationResult(
        candidate=candidate,
        outcome=DecisionReadyOutcome.ACCEPTED,
        quality=quality_status,
        reason_codes=(),
        accepted=True,
    )


def _decision_ready_rejection(
    candidate: DecisionReadyCandidate | None,
    outcome: DecisionReadyOutcome,
    quality: DataQuality,
    *reasons: str,
) -> DecisionReadyValidationResult:
    return DecisionReadyValidationResult(
        candidate=candidate,
        outcome=outcome,
        quality=quality,
        reason_codes=tuple(dict.fromkeys(reasons)),
        accepted=False,
    )


def _data_quality(value: Any) -> DataQuality | None:
    if isinstance(value, DataQuality):
        return value
    if isinstance(value, str):
        try:
            return DataQuality(value)
        except ValueError:
            return None
    return None


def _assessment_status(value: Any) -> DecisionReadyAssessmentStatus | None:
    if isinstance(value, DecisionReadyAssessmentStatus):
        return value
    if isinstance(value, str):
        try:
            return DecisionReadyAssessmentStatus(value)
        except ValueError:
            return None
    return None


def _eligibility_status(value: Any) -> DecisionReadyEligibilityStatus | None:
    if isinstance(value, DecisionReadyEligibilityStatus):
        return value
    if isinstance(value, str):
        try:
            return DecisionReadyEligibilityStatus(value)
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class MarketIntelligenceCategoryContract:
    """An explicit representation-shape contract, not a measurement schema."""

    category: MarketIntelligenceCategory | str
    value_kind: MarketIntelligenceValueKind | str = MarketIntelligenceValueKind.ANY
    contract_version: str = P02_MARKET_INTELLIGENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        category = _category(self.category)
        kind = _value_kind(self.value_kind)
        if category is None:
            raise ValueError("category must be supported")
        if kind is None:
            raise ValueError("value_kind must be supported")
        if not _non_empty(self.contract_version):
            raise ValueError("contract_version is required")
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "value_kind", kind)


@dataclass(frozen=True)
class MarketIntelligenceStateReference:
    """Read-only point-in-time reference to one P02-T08 state entry."""

    state_entry: MarketStateEntry
    state_version: str
    state_digest: str
    evaluation_id: str | None = None
    contract_version: str = P02_T08_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.state_entry, MarketStateEntry):
            raise ValueError("state_entry must be a P02-T08 MarketStateEntry")
        for name, value in (
            ("state_version", self.state_version),
            ("state_digest", self.state_digest),
            ("contract_version", self.contract_version),
        ):
            if not _non_empty(value):
                raise ValueError(f"{name} is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")

    @property
    def key(self) -> MarketStateKey:
        return self.state_entry.key

    @property
    def source_id(self) -> str:
        return self.state_entry.source_id

    @property
    def chain_id(self) -> str:
        return self.state_entry.chain_id

    @property
    def token_identity(self) -> str:
        return self.state_entry.token_identity

    @property
    def market_subject_id(self) -> str:
        return self.state_entry.market_subject_id


@dataclass(frozen=True)
class MarketIntelligenceObservation:
    """A bounded, provider-neutral observation candidate."""

    source_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    intelligence_category: MarketIntelligenceCategory | str
    value: Any
    observation_time: datetime
    received_time: datetime
    reference_time: datetime | None
    data_age: timedelta | None
    upstream: MarketIntelligenceStateReference
    observation_id: str | None = None
    source_event_id: str | None = None
    sequence: SequenceValue = None
    ordering_status: OrderingStatus | str = OrderingStatus.NOT_PROVIDED
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    observation_metadata: Mapping[str, Any] = field(default_factory=dict)
    quality: DataQuality | str = DataQuality.VALID
    source_unavailable: bool = False

    def __post_init__(self) -> None:
        category = _category(self.intelligence_category)
        if category is not None:
            object.__setattr__(self, "intelligence_category", category)
        if isinstance(self.ordering_status, str):
            try:
                object.__setattr__(
                    self, "ordering_status", OrderingStatus(self.ordering_status)
                )
            except ValueError:
                pass
        if isinstance(self.quality, str):
            try:
                object.__setattr__(self, "quality", DataQuality(self.quality))
            except ValueError:
                pass

    @property
    def subject_key(self) -> MarketIntelligenceSubjectKey:
        return (
            self.source_id,
            self.chain_id,
            self.token_identity,
            self.market_subject_id,
            _enum_value(self.intelligence_category),
        )


@dataclass(frozen=True)
class MarketIntelligenceProvenance:
    source_id: str
    source_event_id: str | None
    observation_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    intelligence_category: MarketIntelligenceCategory
    observation_time: datetime
    received_time: datetime
    reference_time: datetime
    data_age: timedelta
    sequence: SequenceValue
    ordering_status: OrderingStatus
    source_metadata: Mapping[str, Any]
    observation_metadata: Mapping[str, Any]
    upstream_state_version: str
    upstream_state_digest: str
    upstream_contract_version: str
    evaluation_id: str | None


@dataclass(frozen=True)
class AcceptedMarketIntelligenceObservation:
    """Immutable observation admitted by this boundary."""

    observation_result_id: str
    observation_id: str
    source_id: str
    chain_id: str
    token_identity: str
    market_subject_id: str
    intelligence_category: MarketIntelligenceCategory
    value: Any
    observation_time: datetime
    received_time: datetime
    reference_time: datetime
    data_age: timedelta
    sequence: SequenceValue
    ordering_status: OrderingStatus
    quality: DataQuality
    provenance: MarketIntelligenceProvenance
    upstream: MarketIntelligenceStateReference
    category_contract_version: str
    contract_version: str
    fingerprint: str
    accepted: bool = True

    @property
    def key(self) -> MarketIntelligenceObservationKey:
        return (
            self.source_id,
            self.chain_id,
            self.token_identity,
            self.market_subject_id,
            self.intelligence_category.value,
            self.observation_id,
        )

    @property
    def subject_key(self) -> MarketIntelligenceSubjectKey:
        return self.key[:-1]


MarketIntelligenceEvidence = AcceptedMarketIntelligenceObservation


@dataclass(frozen=True)
class MarketIntelligenceResult:
    """Observable immutable result for accepted and rejected input."""

    result_id: str
    observation_id: str | None
    key: MarketIntelligenceObservationKey | None
    outcome: MarketIntelligenceOutcome
    quality: DataQuality
    reason_codes: tuple[str, ...]
    predecessor_state_version: str
    predecessor_state_digest: str
    local_state_version: str
    local_state_digest: str
    observation: AcceptedMarketIntelligenceObservation | None
    accepted: bool
    state_changed: bool

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reason_codes


@dataclass
class MarketIntelligenceContext:
    """The only mutable state owned by one local processor."""

    contract_version: str = P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
    evaluation_id: str | None = None
    represented: dict[
        MarketIntelligenceObservationKey, AcceptedMarketIntelligenceObservation
    ] = field(default_factory=dict)
    current: dict[
        MarketIntelligenceSubjectKey, AcceptedMarketIntelligenceObservation
    ] = field(default_factory=dict)
    accepted_fingerprints: dict[MarketIntelligenceObservationKey, str] = field(
        default_factory=dict
    )
    latest_sequence_by_subject: dict[MarketIntelligenceSubjectKey, int] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not _non_empty(self.contract_version):
            raise ValueError("contract_version is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")
        if not isinstance(self.represented, dict) or not isinstance(self.current, dict):
            raise ValueError("local state must use dictionaries")
        for key, observation in self.represented.items():
            if not _valid_observation_key(key) or not isinstance(
                observation, AcceptedMarketIntelligenceObservation
            ):
                raise ValueError("represented contains an invalid observation")
        for key, observation in self.current.items():
            if not _valid_subject_key(key) or observation.subject_key != key:
                raise ValueError("current contains an invalid observation")

    @property
    def state_version(self) -> str:
        return self.state_digest()

    def state_digest(self) -> str:
        return _digest(
            {
                "contract_version": self.contract_version,
                "evaluation_id": self.evaluation_id,
                "represented": [
                    {"key": list(key), "observation": _observation_material(value)}
                    for key, value in sorted(self.represented.items())
                ],
                "current": [
                    {"key": list(key), "observation": _observation_material(value)}
                    for key, value in sorted(self.current.items())
                ],
                "accepted_fingerprints": [
                    {"key": list(key), "fingerprint": value}
                    for key, value in sorted(self.accepted_fingerprints.items())
                ],
                "latest_sequence_by_subject": [
                    {"key": list(key), "sequence": value}
                    for key, value in sorted(self.latest_sequence_by_subject.items())
                ],
            }
        )

    def snapshot(self) -> tuple[AcceptedMarketIntelligenceObservation, ...]:
        return tuple(self.current[key] for key in sorted(self.current))


MarketIntelligenceProcessingContext = MarketIntelligenceContext


class MarketIntelligenceProcessor:
    """Represent observations against an explicit P02-T08 state reference."""

    def __init__(
        self,
        *,
        category_contracts: Mapping[
            MarketIntelligenceCategory | str, MarketIntelligenceCategoryContract
        ]
        | None = None,
        context: MarketIntelligenceContext | None = None,
    ) -> None:
        if context is not None and not isinstance(context, MarketIntelligenceContext):
            raise ValueError("context must be a MarketIntelligenceContext")
        self.context = context or MarketIntelligenceContext()
        self.category_contracts = _contracts(category_contracts)

    def process(self, observation: object) -> MarketIntelligenceResult:
        before = self.context.state_digest()
        identity = _safe_observation_id(observation)
        key = _safe_observation_key(observation, identity)
        invalid = self._validate(observation)
        if invalid is not None:
            outcome, quality, reason = invalid
            return self._rejected(
                observation,
                identity=identity,
                key=key,
                outcome=outcome,
                quality=quality,
                reason=reason,
                before=before,
            )

        assert isinstance(observation, MarketIntelligenceObservation)
        category = _category(observation.intelligence_category)
        assert category is not None
        normalized_value = _canonical_value(observation.value)
        normalized_source_metadata = _canonical_mapping(observation.source_metadata)
        normalized_observation_metadata = _canonical_mapping(
            observation.observation_metadata
        )
        category_contract = self.category_contracts[category]
        canonical_identity = _canonical_observation_id(
            observation, normalized_value, normalized_observation_metadata
        )
        identity = observation.observation_id or canonical_identity
        key = _observation_key(observation, category, identity)
        fingerprint = _fingerprint(
            observation,
            category,
            identity,
            normalized_value,
            normalized_source_metadata,
            normalized_observation_metadata,
        )
        prior_fingerprint = self.context.accepted_fingerprints.get(key)
        if prior_fingerprint is not None:
            outcome = (
                MarketIntelligenceOutcome.DUPLICATE
                if prior_fingerprint == fingerprint
                else MarketIntelligenceOutcome.CONTRADICTORY
            )
            quality = (
                DataQuality.DUPLICATE
                if outcome is MarketIntelligenceOutcome.DUPLICATE
                else DataQuality.CONTRADICTORY
            )
            reason = (
                MarketIntelligenceReason.DUPLICATE_OBSERVATION
                if outcome is MarketIntelligenceOutcome.DUPLICATE
                else MarketIntelligenceReason.CONTRADICTORY_OBSERVATION
            )
            return self._rejected(
                observation, identity=identity, key=key, outcome=outcome,
                quality=quality, reason=reason.value, before=before
            )

        subject_key = key[:-1]
        current = self.context.current.get(subject_key)
        ordering = _ordering_status(observation.ordering_status)
        if _integer_sequence(observation.sequence):
            prior_sequence = self.context.latest_sequence_by_subject.get(subject_key)
            if prior_sequence is None:
                ordering = OrderingStatus.FIRST
            elif observation.sequence <= prior_sequence:
                return self._rejected(
                    observation, identity=identity, key=key,
                    outcome=MarketIntelligenceOutcome.OUT_OF_ORDER,
                    quality=DataQuality.OUT_OF_ORDER,
                    reason=MarketIntelligenceReason.OUT_OF_ORDER_SEQUENCE.value,
                    before=before,
                )
            else:
                ordering = OrderingStatus.IN_ORDER
        elif ordering is None:
            return self._rejected(
                observation, identity=identity, key=key,
                outcome=MarketIntelligenceOutcome.INVALID,
                quality=DataQuality.INVALID,
                reason=MarketIntelligenceReason.INVALID_OBSERVATION.value,
                before=before,
            )

        accepted = _accepted_observation(
            observation=observation,
            identity=identity,
            category=category,
            value=_freeze(normalized_value),
            source_metadata=_freeze(normalized_source_metadata),
            observation_metadata=_freeze(normalized_observation_metadata),
            ordering=ordering,
            fingerprint=fingerprint,
            category_contract_version=category_contract.contract_version,
        )
        self.context.represented[key] = accepted
        self.context.accepted_fingerprints[key] = fingerprint
        self.context.current[subject_key] = accepted
        if _integer_sequence(observation.sequence):
            self.context.latest_sequence_by_subject[subject_key] = observation.sequence
        after = self.context.state_digest()
        outcome = (
            MarketIntelligenceOutcome.REPRESENTED
            if current is None
            else MarketIntelligenceOutcome.UPDATED
        )
        result_id = _digest(
            {
                "evaluation_id": self.context.evaluation_id,
                "key": list(key),
                "outcome": outcome.value,
                "before": before,
                "after": after,
            }
        )
        return MarketIntelligenceResult(
            result_id=result_id,
            observation_id=identity,
            key=key,
            outcome=outcome,
            quality=DataQuality.VALID,
            reason_codes=(),
            predecessor_state_version=before,
            predecessor_state_digest=before,
            local_state_version=after,
            local_state_digest=after,
            observation=accepted,
            accepted=True,
            state_changed=True,
        )

    def snapshot(self) -> tuple[AcceptedMarketIntelligenceObservation, ...]:
        return self.context.snapshot()

    def _validate(
        self, value: object
    ) -> tuple[MarketIntelligenceOutcome, DataQuality, str] | None:
        if not isinstance(value, MarketIntelligenceObservation):
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_OBSERVATION.value,
            )
        category = _category(value.intelligence_category)
        if category is None or category not in self.category_contracts:
            return (
                MarketIntelligenceOutcome.UNSUPPORTED,
                DataQuality.INVALID,
                MarketIntelligenceReason.UNSUPPORTED_CATEGORY.value,
            )
        if value.source_unavailable or value.quality is DataQuality.SOURCE_UNAVAILABLE:
            return (
                MarketIntelligenceOutcome.UNAVAILABLE,
                DataQuality.SOURCE_UNAVAILABLE,
                MarketIntelligenceReason.SOURCE_UNAVAILABLE.value,
            )
        if value.quality is DataQuality.STALE:
            return (
                MarketIntelligenceOutcome.STALE,
                DataQuality.STALE,
                MarketIntelligenceReason.STALE_OBSERVATION.value,
            )
        if not isinstance(value.quality, DataQuality) or value.quality is not DataQuality.VALID:
            return (
                MarketIntelligenceOutcome.REJECTED,
                value.quality if isinstance(value.quality, DataQuality) else DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_OBSERVATION.value,
            )
        if not all(
            _non_empty(getattr(value, name))
            for name in ("source_id", "chain_id", "token_identity", "market_subject_id")
        ):
            return (
                MarketIntelligenceOutcome.INCOMPLETE,
                DataQuality.INCOMPLETE,
                MarketIntelligenceReason.INCOMPLETE_OBSERVATION.value,
            )
        if not isinstance(value.upstream, MarketIntelligenceStateReference):
            return (
                MarketIntelligenceOutcome.INCOMPLETE,
                DataQuality.INCOMPLETE,
                MarketIntelligenceReason.INVALID_UPSTREAM_REFERENCE.value,
            )
        if (
            value.upstream.source_id != value.source_id
            or value.upstream.chain_id != value.chain_id
            or value.upstream.token_identity != value.token_identity
            or value.upstream.market_subject_id != value.market_subject_id
        ):
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.UPSTREAM_IDENTITY_MISMATCH.value,
            )
        if not _aware(value.observation_time) or not _aware(value.received_time):
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_TIMESTAMP.value,
            )
        if value.reference_time is None or not _aware(value.reference_time):
            return (
                MarketIntelligenceOutcome.INCOMPLETE,
                DataQuality.INCOMPLETE,
                MarketIntelligenceReason.INCOMPLETE_OBSERVATION.value,
            )
        if value.observation_time > value.received_time or value.observation_time > value.reference_time:
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_TIMESTAMP_RELATIONSHIP.value,
            )
        if not isinstance(value.data_age, timedelta) or value.data_age < timedelta(0):
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_DATA_AGE.value,
            )
        if value.reference_time - value.observation_time != value.data_age:
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_DATA_AGE.value,
            )
        if not _valid_sequence(value.sequence) or _ordering_status(value.ordering_status) is None:
            return (
                MarketIntelligenceOutcome.INVALID,
                DataQuality.INVALID,
                MarketIntelligenceReason.INVALID_OBSERVATION.value,
            )
        try:
            normalized_value = _canonical_value(value.value)
            normalized_source = _canonical_mapping(value.source_metadata)
            normalized_observation = _canonical_mapping(value.observation_metadata)
            contract = self.category_contracts[category]
            if not _value_matches_kind(normalized_value, contract.value_kind):
                return (
                    MarketIntelligenceOutcome.UNSUPPORTED,
                    DataQuality.INVALID,
                    MarketIntelligenceReason.VALUE_KIND_MISMATCH.value,
                )
            identity = _canonical_observation_id(
                value, normalized_value, normalized_observation
            )
            if value.observation_id is not None and value.observation_id != identity:
                return (
                    MarketIntelligenceOutcome.INVALID,
                    DataQuality.INVALID,
                    MarketIntelligenceReason.OBSERVATION_ID_MISMATCH.value,
                )
            return None
        except ValueError as exc:
            reason = (
                MarketIntelligenceReason.METADATA_BOUNDS_EXCEEDED.value
                if "bound" in str(exc).lower()
                else MarketIntelligenceReason.UNSUPPORTED_METADATA.value
            )
            return MarketIntelligenceOutcome.INVALID, DataQuality.INVALID, reason

    def _rejected(
        self,
        value: object,
        *,
        identity: str | None,
        key: MarketIntelligenceObservationKey | None,
        outcome: MarketIntelligenceOutcome,
        quality: DataQuality,
        reason: str,
        before: str,
    ) -> MarketIntelligenceResult:
        result_id = _digest(
            {
                "evaluation_id": self.context.evaluation_id,
                "identity": identity,
                "key": list(key) if key else None,
                "outcome": outcome.value,
                "reason": reason,
                "before": before,
            }
        )
        return MarketIntelligenceResult(
            result_id=result_id,
            observation_id=identity,
            key=key,
            outcome=outcome,
            quality=quality,
            reason_codes=(reason,),
            predecessor_state_version=before,
            predecessor_state_digest=before,
            local_state_version=before,
            local_state_digest=before,
            observation=None,
            accepted=False,
            state_changed=False,
        )


MarketIntelligenceMaterializer = MarketIntelligenceProcessor
MarketIntelligenceProcessorContext = MarketIntelligenceContext


def represent_market_intelligence(
    observation: MarketIntelligenceObservation,
    *,
    category_contracts: Mapping[
        MarketIntelligenceCategory | str, MarketIntelligenceCategoryContract
    ]
    | None = None,
    context: MarketIntelligenceContext | None = None,
) -> MarketIntelligenceResult:
    return MarketIntelligenceProcessor(
        category_contracts=category_contracts, context=context
    ).process(observation)


def _contracts(
    value: Mapping[
        MarketIntelligenceCategory | str, MarketIntelligenceCategoryContract
    ]
    | None,
) -> dict[MarketIntelligenceCategory, MarketIntelligenceCategoryContract]:
    if value is None:
        return {
            category: MarketIntelligenceCategoryContract(category)
            for category in MarketIntelligenceCategory
        }
    result: dict[MarketIntelligenceCategory, MarketIntelligenceCategoryContract] = {}
    for key, contract in value.items():
        if not isinstance(contract, MarketIntelligenceCategoryContract):
            raise ValueError("category_contracts must contain category contracts")
        category = _category(key)
        if category is None or contract.category is not category:
            raise ValueError("category contract key does not match its category")
        result[category] = contract
    return result


def _accepted_observation(
    *,
    observation: MarketIntelligenceObservation,
    identity: str,
    category: MarketIntelligenceCategory,
    value: Any,
    source_metadata: Mapping[str, Any],
    observation_metadata: Mapping[str, Any],
    ordering: OrderingStatus,
    fingerprint: str,
    category_contract_version: str,
) -> AcceptedMarketIntelligenceObservation:
    assert observation.reference_time is not None
    assert observation.data_age is not None
    provenance = MarketIntelligenceProvenance(
        source_id=observation.source_id,
        source_event_id=observation.source_event_id,
        observation_id=identity,
        chain_id=observation.chain_id,
        token_identity=observation.token_identity,
        market_subject_id=observation.market_subject_id,
        intelligence_category=category,
        observation_time=observation.observation_time,
        received_time=observation.received_time,
        reference_time=observation.reference_time,
        data_age=observation.data_age,
        sequence=observation.sequence,
        ordering_status=ordering,
        source_metadata=source_metadata,
        observation_metadata=observation_metadata,
        upstream_state_version=observation.upstream.state_version,
        upstream_state_digest=observation.upstream.state_digest,
        upstream_contract_version=observation.upstream.contract_version,
        evaluation_id=observation.upstream.evaluation_id,
    )
    return AcceptedMarketIntelligenceObservation(
        observation_result_id=_digest(
            {
                "identity": identity,
                "fingerprint": fingerprint,
                "evaluation_id": observation.upstream.evaluation_id,
            }
        ),
        observation_id=identity,
        source_id=observation.source_id,
        chain_id=observation.chain_id,
        token_identity=observation.token_identity,
        market_subject_id=observation.market_subject_id,
        intelligence_category=category,
        value=value,
        observation_time=observation.observation_time,
        received_time=observation.received_time,
        reference_time=observation.reference_time,
        data_age=observation.data_age,
        sequence=observation.sequence,
        ordering_status=ordering,
        quality=DataQuality.VALID,
        provenance=provenance,
        upstream=observation.upstream,
        category_contract_version=category_contract_version,
        contract_version=P02_MARKET_INTELLIGENCE_CONTRACT_VERSION,
        fingerprint=fingerprint,
    )


def _observation_id(
    observation: MarketIntelligenceObservation,
    value: Any,
    metadata: Mapping[str, Any],
) -> str:
    return _canonical_observation_id(observation, value, metadata)


def _canonical_observation_id(
    observation: MarketIntelligenceObservation,
    value: Any,
    metadata: Mapping[str, Any],
) -> str:
    return "mi:" + _digest(
        {
            "source_id": observation.source_id,
            "source_event_id": observation.source_event_id,
            "chain_id": observation.chain_id,
            "token_identity": observation.token_identity,
            "market_subject_id": observation.market_subject_id,
            "intelligence_category": _enum_value(observation.intelligence_category),
            "value": value,
            "observation_time": _timestamp(observation.observation_time),
            "sequence": observation.sequence,
            "observation_metadata": metadata,
        }
    )


def _safe_observation_id(value: object) -> str | None:
    if not isinstance(value, MarketIntelligenceObservation):
        return None
    try:
        canonical = _canonical_observation_id(
            value,
            _canonical_value(value.value),
            _canonical_mapping(value.observation_metadata),
        )
        return value.observation_id or canonical
    except (TypeError, ValueError):
        return value.observation_id if _non_empty(value.observation_id) else None


def _observation_key(
    observation: MarketIntelligenceObservation,
    category: MarketIntelligenceCategory,
    identity: str,
) -> MarketIntelligenceObservationKey:
    return (
        observation.source_id,
        observation.chain_id,
        observation.token_identity,
        observation.market_subject_id,
        category.value,
        identity,
    )


def _safe_observation_key(
    value: object, identity: str | None
) -> MarketIntelligenceObservationKey | None:
    if not isinstance(value, MarketIntelligenceObservation) or identity is None:
        return None
    category = _category(value.intelligence_category)
    if category is None:
        return None
    return _observation_key(value, category, identity)


def _fingerprint(
    observation: MarketIntelligenceObservation,
    category: MarketIntelligenceCategory,
    identity: str,
    value: Any,
    source_metadata: Mapping[str, Any],
    observation_metadata: Mapping[str, Any],
) -> str:
    return _digest(
        {
            "key": list(_observation_key(observation, category, identity)),
            "value": value,
            "observation_time": _timestamp(observation.observation_time),
            "received_time": _timestamp(observation.received_time),
            "reference_time": _timestamp(observation.reference_time),
            "data_age": observation.data_age.total_seconds() if observation.data_age else None,
            "sequence": observation.sequence,
            "source_event_id": observation.source_event_id,
            "ordering_status": _enum_value(observation.ordering_status),
            "source_metadata": source_metadata,
            "observation_metadata": observation_metadata,
            "upstream": {
                "state_version": observation.upstream.state_version,
                "state_digest": observation.upstream.state_digest,
                "contract_version": observation.upstream.contract_version,
                "evaluation_id": observation.upstream.evaluation_id,
            },
        }
    )


def _observation_material(
    observation: AcceptedMarketIntelligenceObservation,
) -> dict[str, Any]:
    return {
        "key": list(observation.key),
        "value": observation.value,
        "observation_time": _timestamp(observation.observation_time),
        "received_time": _timestamp(observation.received_time),
        "reference_time": _timestamp(observation.reference_time),
        "data_age": observation.data_age.total_seconds(),
        "sequence": observation.sequence,
        "ordering_status": observation.ordering_status.value,
        "quality": observation.quality.value,
        "provenance": observation.provenance,
        "upstream": observation.upstream,
        "category_contract_version": observation.category_contract_version,
        "contract_version": observation.contract_version,
        "fingerprint": observation.fingerprint,
        "accepted": observation.accepted,
    }


def _canonical_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a mapping")
    result = _canonicalize(value, depth=0, counter=[0])
    if not isinstance(result, dict):
        raise ValueError("metadata must be a mapping")
    _bounded_json(result)
    return result


def _canonical_value(value: Any) -> Any:
    result = _canonicalize(value, depth=0, counter=[0])
    _bounded_json(result)
    return result


def _canonicalize(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata bound exceeded")
    counter[0] += 1
    if counter[0] > MAX_METADATA_ITEMS:
        raise ValueError("metadata bound exceeded")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("unsupported metadata")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("unsupported metadata")
        if any(_sensitive_key(key) for key in value):
            raise ValueError("unsupported metadata")
        return {
            key: _canonicalize(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item, depth=depth + 1, counter=counter) for item in value]
    raise ValueError("unsupported metadata")


def _bounded_json(value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("metadata bound exceeded")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _general_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _general_canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Mapping):
        return {str(key): _general_canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_general_canonical(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _general_canonical(getattr(value, name))
            for name in sorted(value.__dataclass_fields__)
        }
    raise ValueError("value cannot be deterministically serialized")


def _timestamp(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if isinstance(value, datetime) else None


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _category(value: Any) -> MarketIntelligenceCategory | None:
    if isinstance(value, MarketIntelligenceCategory):
        return value
    if isinstance(value, str):
        try:
            return MarketIntelligenceCategory(value)
        except ValueError:
            return None
    return None


def _value_kind(value: Any) -> MarketIntelligenceValueKind | None:
    if isinstance(value, MarketIntelligenceValueKind):
        return value
    if isinstance(value, str):
        try:
            return MarketIntelligenceValueKind(value)
        except ValueError:
            return None
    return None


def _ordering_status(value: Any) -> OrderingStatus | None:
    if isinstance(value, OrderingStatus):
        return value
    if isinstance(value, str):
        try:
            return OrderingStatus(value)
        except ValueError:
            return None
    return None


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, StrEnum) else value


def _integer_sequence(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_sequence(value: Any) -> bool:
    return value is None or _integer_sequence(value) or isinstance(value, str)


def _value_matches_kind(value: Any, kind: MarketIntelligenceValueKind) -> bool:
    if kind is MarketIntelligenceValueKind.ANY:
        return True
    if kind is MarketIntelligenceValueKind.SCALAR:
        return value is None or isinstance(value, (bool, int, float, str))
    if kind is MarketIntelligenceValueKind.MAPPING:
        return isinstance(value, dict)
    return isinstance(value, list)


def _valid_subject_key(value: Any) -> bool:
    return isinstance(value, tuple) and len(value) == 5 and all(_non_empty(item) for item in value)


def _valid_observation_key(value: Any) -> bool:
    return isinstance(value, tuple) and len(value) == 6 and all(_non_empty(item) for item in value)


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        term in normalized
        for term in (
            "secret",
            "password",
            "credential",
            "api_key",
            "access_token",
            "private_key",
            "seed_phrase",
            "signing",
        )
    )


__all__ = [
    "AcceptedMarketIntelligenceObservation",
    "DecisionReadyAssessmentStatus",
    "DecisionReadyCandidate",
    "DecisionReadyDataQuality",
    "DecisionReadyEligibility",
    "DecisionReadyEligibilityStatus",
    "DecisionReadyEvidence",
    "DecisionReadyIdentity",
    "DecisionReadyLiquidity",
    "DecisionReadyMarketActivity",
    "DecisionReadyMarketSnapshot",
    "DecisionReadyOutcome",
    "DecisionReadyReason",
    "DecisionReadySafety",
    "DecisionReadySellability",
    "DecisionReadyValidationResult",
    "MarketIntelligenceCategory",
    "MarketIntelligenceCategoryContract",
    "MarketIntelligenceContext",
    "MarketIntelligenceEvidence",
    "MarketIntelligenceOutcome",
    "MarketIntelligenceObservation",
    "MarketIntelligenceObservationKey",
    "MarketIntelligenceProcessingContext",
    "MarketIntelligenceProcessor",
    "MarketIntelligenceProvenance",
    "MarketIntelligenceReason",
    "MarketIntelligenceResult",
    "MarketIntelligenceStateReference",
    "MarketIntelligenceSubjectKey",
    "MarketIntelligenceValueKind",
    "P02_T09_CONTRACT_VERSION",
    "P02_MARKET_INTELLIGENCE_CONTRACT_VERSION",
    "MarketIntelligenceMaterializer",
    "represent_market_intelligence",
    "validate_decision_ready_candidate",
]