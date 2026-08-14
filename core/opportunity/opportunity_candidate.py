"""Provider-neutral P05-T01 opportunity candidate input boundary.

This module preserves already-created P03/P04 outputs as an immutable
candidate input for later opportunity work.  It does not score, rank, predict,
make decisions, authorize actions, or perform external I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from core.features.feature_snapshot import (
    FeatureCalculationSnapshot,
    FeatureCalculationStatus,
    P04_T10_CONTRACT_VERSION,
)
from core.risk.safety_eligibility import EligibilityStatus
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
)
from core.risk.safety_evaluation import P03_T02_CONTRACT_VERSION
from core.signals.signal_snapshot import (
    P04_T06_CONTRACT_VERSION,
    SignalEvidenceSnapshot,
)
from core.features.price_features import P04_T09_CONTRACT_VERSION


P05_T01_CONTRACT_VERSION = "p05-t01-v1"


class OpportunityCandidateState(StrEnum):
    """Candidate states with no decision or execution meaning."""

    VALID = "VALID"
    ELIGIBLE = "VALID"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


class OpportunityUpstreamKind(StrEnum):
    """Kinds of established upstream references preserved by P05-T01."""

    P03_ELIGIBILITY = "P03_ELIGIBILITY"
    P04_SIGNAL_SNAPSHOT = "P04_SIGNAL_SNAPSHOT"
    P04_FEATURE_SNAPSHOT = "P04_FEATURE_SNAPSHOT"


@dataclass(frozen=True)
class OpportunityUpstreamReference:
    """Immutable digest reference to one preserved upstream contract."""

    kind: OpportunityUpstreamKind
    reference_id: str
    contract_version: str
    representation_digest: str

    def __post_init__(self) -> None:
        kind = _enum_value(self.kind, OpportunityUpstreamKind, "kind")
        object.__setattr__(self, "kind", kind)
        for value, name in (
            (self.reference_id, "reference_id"),
            (self.contract_version, "contract_version"),
            (self.representation_digest, "representation_digest"),
        ):
            _require_text(value, name)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "kind": self.kind.value,
                "reference_id": self.reference_id,
                "contract_version": self.contract_version,
                "representation_digest": self.representation_digest,
            }
        )

@dataclass(frozen=True)
class OpportunityCandidate:
    """Immutable P05-T01 representation of one analytical candidate."""

    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    eligibility: DerivedEligibilityOutput
    signal_snapshot: SignalEvidenceSnapshot
    state: OpportunityCandidateState = OpportunityCandidateState.VALID
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...] = ()
    reason_codes: tuple[str, ...] = ()
    analytical_context: Mapping[str, Any] = field(default_factory=dict)
    upstream_references: tuple[OpportunityUpstreamReference, ...] = ()
    contract_version: str = P05_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)

        state = _enum_value(self.state, OpportunityCandidateState, "state")
        object.__setattr__(self, "state", state)
        if self.contract_version != P05_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T01 contract version")

        reference_time = _to_utc(self.reference_time, "reference_time")
        object.__setattr__(self, "reference_time", reference_time)

        reasons = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(sorted(dict.fromkeys(reasons))),
        )
        if state in {
            OpportunityCandidateState.BLOCKED,
            OpportunityCandidateState.INVALID,
        } and not self.reason_codes:
            raise ValueError("blocked and invalid candidates require reason_codes")

        if not isinstance(self.eligibility, DerivedEligibilityOutput):
            raise ValueError("eligibility must be a DerivedEligibilityOutput")
        if self.eligibility.contract_version != P03_T02_CONTRACT_VERSION:
            raise ValueError("unsupported P03 eligibility contract version")
        if not self.eligibility.evidence_references:
            raise ValueError("eligibility requires upstream evidence references")
        eligibility_time = _to_utc(
            self.eligibility.evaluated_at,
            "eligibility.evaluated_at",
        )
        if eligibility_time > reference_time:
            raise ValueError("eligibility is after candidate reference_time")

        if not isinstance(self.signal_snapshot, SignalEvidenceSnapshot):
            raise ValueError("signal_snapshot must be a SignalEvidenceSnapshot")
        if self.signal_snapshot.contract_version != P04_T06_CONTRACT_VERSION:
            raise ValueError("unsupported P04 signal snapshot contract version")
        if not _is_text(self.signal_snapshot.chain_id) or not _is_text(
            self.signal_snapshot.token_identity
        ):
            raise ValueError("signal snapshot identity is required")
        if (
            self.signal_snapshot.chain_id != self.chain_id
            or self.signal_snapshot.token_identity != self.token_identity
        ):
            raise ValueError("signal snapshot identity does not match candidate")
        signal_times = tuple(
            None
            if value is None
            else _to_utc(value, "signal observation timestamp")
            for value in self.signal_snapshot.observation_timestamps
        )
        if any(value is not None and value > reference_time for value in signal_times):
            raise ValueError("signal snapshot contains future evidence")
        if state is OpportunityCandidateState.VALID and any(
            value is None for value in signal_times
        ):
            raise ValueError("VALID candidates require signal timestamps")

        if self.feature_snapshots is None or not isinstance(
            self.feature_snapshots, (tuple, list)
        ):
            raise ValueError("feature_snapshots must be a tuple or list")
        feature_snapshots = tuple(self.feature_snapshots)
        if not all(
            isinstance(value, FeatureCalculationSnapshot)
            for value in feature_snapshots
        ):
            raise ValueError(
                "feature_snapshots must contain FeatureCalculationSnapshot values"
            )
        for snapshot in feature_snapshots:
            if snapshot.contract_version != P04_T10_CONTRACT_VERSION:
                raise ValueError("unsupported P04 feature snapshot contract version")
            if snapshot.calculation_contract_version != P04_T09_CONTRACT_VERSION:
                raise ValueError("unsupported P04 feature calculation contract version")
            for value, name in (
                (snapshot.chain_id, "feature snapshot chain_id"),
                (snapshot.token_identity, "feature snapshot token_identity"),
            ):
                if value is not None and not _is_text(value):
                    raise ValueError(f"{name} must be non-empty when provided")
            if snapshot.chain_id is not None and snapshot.chain_id != self.chain_id:
                raise ValueError("feature snapshot chain_id does not match candidate")
            if (
                snapshot.token_identity is not None
                and snapshot.token_identity != self.token_identity
            ):
                raise ValueError(
                    "feature snapshot token_identity does not match candidate"
                )
            if snapshot.reference_time is not None and _to_utc(
                snapshot.reference_time,
                "feature snapshot reference_time",
            ) > reference_time:
                raise ValueError("feature snapshot is after candidate reference_time")
            for input_reference in snapshot.inputs:
                for value, name in (
                    (input_reference.observation_time, "feature observation_time"),
                    (input_reference.received_time, "feature received_time"),
                ):
                    if value is not None and _to_utc(value, name) > reference_time:
                        raise ValueError("feature snapshot contains future input")

        feature_snapshots = tuple(
            sorted(feature_snapshots, key=lambda value: value.digest)
        )
        object.__setattr__(self, "feature_snapshots", feature_snapshots)
        if state is OpportunityCandidateState.VALID:
            if self.eligibility.status is not EligibilityStatus.ELIGIBLE:
                raise ValueError("VALID candidates require ELIGIBLE upstream status")
            if any(
                value.status is not FeatureCalculationStatus.CALCULATED
                for value in feature_snapshots
            ):
                raise ValueError(
                    "VALID candidates require calculated feature snapshots"
                )

        context = _canonical_mapping(self.analytical_context)
        object.__setattr__(self, "analytical_context", _freeze(context))

        expected_references = _upstream_references(
            self.eligibility,
            self.signal_snapshot,
            feature_snapshots,
        )
        supplied_references = tuple(self.upstream_references)
        if supplied_references:
            if not all(
                isinstance(value, OpportunityUpstreamReference)
                for value in supplied_references
            ):
                raise ValueError(
                    "upstream_references must contain OpportunityUpstreamReference values"
                )
            if supplied_references != expected_references:
                raise ValueError("upstream_references do not match upstream inputs")
        object.__setattr__(self, "upstream_references", expected_references)

    @classmethod
    def from_upstream(
        cls,
        *,
        candidate_id: str,
        chain_id: str,
        token_identity: str,
        reference_time: datetime,
        eligibility: DerivedEligibilityOutput,
        signal_snapshot: SignalEvidenceSnapshot,
        feature_snapshots: tuple[FeatureCalculationSnapshot, ...]
        | list[FeatureCalculationSnapshot] = (),
        analytical_context: Mapping[str, Any] | None = None,
    ) -> OpportunityCandidate:
        """Build a candidate state from already-created upstream contracts."""

        if not isinstance(eligibility, DerivedEligibilityOutput):
            raise ValueError("eligibility must be a DerivedEligibilityOutput")
        if not isinstance(signal_snapshot, SignalEvidenceSnapshot):
            raise ValueError("signal_snapshot must be a SignalEvidenceSnapshot")
        features = tuple(feature_snapshots)
        if not all(
            isinstance(value, FeatureCalculationSnapshot)
            for value in features
        ):
            raise ValueError(
                "feature_snapshots must contain FeatureCalculationSnapshot values"
            )
        reasons: set[str] = set()
        if eligibility.status is not EligibilityStatus.ELIGIBLE:
            reasons.add("UPSTREAM_NOT_ELIGIBLE")
        if any(
            value.status is not FeatureCalculationStatus.CALCULATED
            for value in features
        ):
            reasons.add("NON_CALCULATED_FEATURE")
        state = (
            OpportunityCandidateState.VALID
            if not reasons
            else OpportunityCandidateState.BLOCKED
        )
        if state is OpportunityCandidateState.BLOCKED:
            reasons.update(eligibility.reason_codes)
        return cls(
            candidate_id=candidate_id,
            chain_id=chain_id,
            token_identity=token_identity,
            reference_time=reference_time,
            state=state,
            eligibility=eligibility,
            signal_snapshot=signal_snapshot,
            feature_snapshots=features,
            reason_codes=tuple(reasons),
            analytical_context={} if analytical_context is None else analytical_context,
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": _timestamp(self.reference_time),
                "state": self.state.value,
                "reason_codes": self.reason_codes,
                "eligibility": _eligibility_material(self.eligibility),
                "signal_snapshot": self.signal_snapshot.canonical_representation,
                "feature_snapshots": tuple(
                    value.canonical_representation for value in self.feature_snapshots
                ),
                "analytical_context": self.analytical_context,
                "upstream_references": tuple(
                    value.canonical_representation
                    for value in self.upstream_references
                ),
                "contract_version": self.contract_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def upstream_contract_versions(self) -> tuple[str, ...]:
        return tuple(value.contract_version for value in self.upstream_references)

    @property
    def upstream_representation_digests(self) -> tuple[str, ...]:
        return tuple(
            value.representation_digest for value in self.upstream_references
        )

    @property
    def is_eligible(self) -> bool:
        return self.state is OpportunityCandidateState.VALID

    @property
    def is_authoritative(self) -> bool:
        return False

    @property
    def is_decision(self) -> bool:
        return False

    @property
    def is_order(self) -> bool:
        return False

    @property
    def is_authorization(self) -> bool:
        return False


@dataclass(frozen=True)
class OpportunityCandidateResult:
    """Explicit valid, blocked, or invalid candidate construction outcome."""

    state: OpportunityCandidateState
    candidate: OpportunityCandidate | None
    reason_codes: tuple[str, ...]
    representation_digest: str | None
    contract_version: str = P05_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        state = _enum_value(self.state, OpportunityCandidateState, "state")
        object.__setattr__(self, "state", state)
        if state is OpportunityCandidateState.INVALID:
            if self.candidate is not None:
                raise ValueError("INVALID result cannot contain a candidate")
        elif not isinstance(self.candidate, OpportunityCandidate):
            raise ValueError("valid or blocked result requires a candidate")
        elif self.candidate.state is not state:
            raise ValueError("result state must match candidate state")
        reasons = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))
        if state is OpportunityCandidateState.INVALID and not self.reason_codes:
            raise ValueError("invalid result requires reason_codes")
        if self.representation_digest is not None:
            _require_text(self.representation_digest, "representation_digest")
        _require_text(self.contract_version, "contract_version")
        if self.contract_version != P05_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T01 contract version")

    @property
    def status(self) -> OpportunityCandidateState:
        return self.state

    @property
    def valid(self) -> bool:
        return self.state is not OpportunityCandidateState.INVALID

    @property
    def blocked(self) -> bool:
        return self.state is OpportunityCandidateState.BLOCKED


def create_opportunity_candidate(
    *,
    candidate_id: str,
    chain_id: str,
    token_identity: str,
    reference_time: datetime,
    eligibility: DerivedEligibilityOutput,
    signal_snapshot: SignalEvidenceSnapshot,
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...]
    | list[FeatureCalculationSnapshot] = (),
    analytical_context: Mapping[str, Any] | None = None,
) -> OpportunityCandidate:
    return OpportunityCandidate.from_upstream(
        candidate_id=candidate_id,
        chain_id=chain_id,
        token_identity=token_identity,
        reference_time=reference_time,
        eligibility=eligibility,
        signal_snapshot=signal_snapshot,
        feature_snapshots=feature_snapshots,
        analytical_context=analytical_context,
    )


def create_opportunity_candidate_result(
    *,
    candidate_id: str,
    chain_id: str,
    token_identity: str,
    reference_time: datetime,
    eligibility: DerivedEligibilityOutput,
    signal_snapshot: SignalEvidenceSnapshot,
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...]
    | list[FeatureCalculationSnapshot] = (),
    analytical_context: Mapping[str, Any] | None = None,
) -> OpportunityCandidateResult:
    try:
        candidate = create_opportunity_candidate(
            candidate_id=candidate_id,
            chain_id=chain_id,
            token_identity=token_identity,
            reference_time=reference_time,
            eligibility=eligibility,
            signal_snapshot=signal_snapshot,
            feature_snapshots=feature_snapshots,
            analytical_context=analytical_context,
        )
    except (AttributeError, TypeError, ValueError):
        return OpportunityCandidateResult(
            state=OpportunityCandidateState.INVALID,
            candidate=None,
            reason_codes=("INVALID_INPUT",),
            representation_digest=None,
        )
    return OpportunityCandidateResult(
        state=candidate.state,
        candidate=candidate,
        reason_codes=candidate.reason_codes,
        representation_digest=candidate.representation_digest,
    )


build_opportunity_candidate = create_opportunity_candidate
build_opportunity_candidate_result = create_opportunity_candidate_result
OpportunityCandidateStatus = OpportunityCandidateState
OpportunityCandidateInput = OpportunityCandidate


def _upstream_references(
    eligibility: DerivedEligibilityOutput,
    signal_snapshot: SignalEvidenceSnapshot,
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...],
) -> tuple[OpportunityUpstreamReference, ...]:
    references = [
        OpportunityUpstreamReference(
            kind=OpportunityUpstreamKind.P03_ELIGIBILITY,
            reference_id=eligibility.evaluator_id,
            contract_version=eligibility.contract_version,
            representation_digest=_digest(_eligibility_material(eligibility)),
        ),
        OpportunityUpstreamReference(
            kind=OpportunityUpstreamKind.P04_SIGNAL_SNAPSHOT,
            reference_id=signal_snapshot.aggregation_digest,
            contract_version=signal_snapshot.contract_version,
            representation_digest=signal_snapshot.digest,
        ),
    ]
    references.extend(
        OpportunityUpstreamReference(
            kind=OpportunityUpstreamKind.P04_FEATURE_SNAPSHOT,
            reference_id=snapshot.calculation_result_id,
            contract_version=snapshot.contract_version,
            representation_digest=snapshot.digest,
        )
        for snapshot in feature_snapshots
    )
    return tuple(references)


def _eligibility_material(value: DerivedEligibilityOutput) -> dict[str, Any]:
    return {
        "status": _enum_value(
            value.status,
            EligibilityStatus,
            "eligibility.status",
        ).value,
        "evaluator_id": value.evaluator_id,
        "evaluated_at": _timestamp(value.evaluated_at),
        "evidence_references": tuple(value.evidence_references),
        "contract_version": value.contract_version,
        "reason_codes": tuple(sorted(dict.fromkeys(value.reason_codes))),
    }


def _canonical_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("analytical_context must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ValueError("analytical_context keys must be strings")
    canonical = _canonicalize(value)
    if not isinstance(canonical, dict):
        raise ValueError("analytical_context must be a mapping")
    return canonical


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite analytical context value")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite analytical context Decimal")
        return format(value.normalize(), "f")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("analytical_context keys must be strings")
        return {
            key: _canonicalize(value[key])
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(
        f"{type(value).__name__} cannot be deterministically serialized"
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _timestamp(value: datetime) -> str:
    return _to_utc(value, "timestamp").isoformat()


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _enum_value(
    value: Any,
    enum_type: type[StrEnum],
    name: str,
) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as error:
            raise ValueError(f"{name} is unsupported") from error
    raise ValueError(f"{name} is unsupported")


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "OpportunityCandidate",
    "OpportunityCandidateInput",
    "OpportunityCandidateResult",
    "OpportunityCandidateState",
    "OpportunityCandidateStatus",
    "OpportunityUpstreamKind",
    "OpportunityUpstreamReference",
    "P05_T01_CONTRACT_VERSION",
    "build_opportunity_candidate",
    "build_opportunity_candidate_result",
    "create_opportunity_candidate",
    "create_opportunity_candidate_result",
]