"""The narrow, provider-neutral P04-T09 price-feature boundary.

Only ``price_velocity`` and ``price_acceleration`` are defined here.  Inputs
are accepted P02-T09 observations, not provider payloads.  Calculations are
local and pure: they never mutate an observation, a P02 state entry, or a
caller-owned collection.

Arithmetic uses ``Decimal(str(value))`` for numeric conversion and a fixed
50-digit ``Decimal`` context.  Division uses ROUND_HALF_EVEN under that
context; the resulting finite decimal is serialized as a normalized decimal
string.  No binary floating-point comparison, clamping, interpolation, or
implicit freshness threshold is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import (
    Decimal,
    InvalidOperation,
    localcontext,
    ROUND_HALF_EVEN,
)
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.market_intelligence import (
    AcceptedMarketIntelligenceObservation,
    MarketIntelligenceCategory,
    P02_MARKET_INTELLIGENCE_CONTRACT_VERSION,
)
from core.data.market_state import P02_T08_CONTRACT_VERSION


P04_T09_CONTRACT_VERSION = "p04-t09-v1"
NUMERIC_PRECISION = 50

PRICE_VELOCITY = "price_velocity"
PRICE_ACCELERATION = "price_acceleration"


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


class FeatureCalculationStatus(StrEnum):
    """Observable feature-calculation outcomes."""

    CALCULATED = "CALCULATED"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"


class FeatureReason(StrEnum):
    """Canonical reasons for a non-success feature result."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    UNSUPPORTED_CATEGORY = "UNSUPPORTED_CATEGORY"
    UNSUPPORTED_INPUT_VERSION = "UNSUPPORTED_INPUT_VERSION"
    MISSING_CALCULATION_CONTEXT = "MISSING_CALCULATION_CONTEXT"
    MISSING_PRICE_SEMANTICS = "MISSING_PRICE_SEMANTICS"
    MISSING_SNAPSHOT_LINK = "MISSING_SNAPSHOT_LINK"
    MISSING_PROVENANCE = "MISSING_PROVENANCE"
    INSUFFICIENT_PRICE_OBSERVATIONS = "INSUFFICIENT_PRICE_OBSERVATIONS"
    STALE_INPUT = "STALE_INPUT"
    FUTURE_OBSERVATION = "FUTURE_OBSERVATION"
    NOT_AVAILABLE_AT_REFERENCE_TIME = "NOT_AVAILABLE_AT_REFERENCE_TIME"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    INVALID_TIMESTAMP_ORDER = "INVALID_TIMESTAMP_ORDER"
    ZERO_ELAPSED_TIME = "ZERO_ELAPSED_TIME"
    INVALID_NUMERIC_VALUE = "INVALID_NUMERIC_VALUE"
    INCOMPATIBLE_PRICE_UNIT = "INCOMPATIBLE_PRICE_UNIT"
    INCOMPATIBLE_QUOTE_ASSET = "INCOMPATIBLE_QUOTE_ASSET"
    DUPLICATE_INPUT = "DUPLICATE_INPUT"
    CONTRADICTORY_INPUT = "CONTRADICTORY_INPUT"
    UPSTREAM_NOT_ACCEPTED = "UPSTREAM_NOT_ACCEPTED"
    UPSTREAM_IDENTITY_MISMATCH = "UPSTREAM_IDENTITY_MISMATCH"
    ARITHMETIC_FAILURE = "ARITHMETIC_FAILURE"


@dataclass(frozen=True)
class FeatureDefinition:
    """Explicit identity and version of one authorized feature definition."""

    feature_id: str
    feature_version: str
    input_count: int | None = None
    value_unit_suffix: str | None = None

    def __post_init__(self) -> None:
        if not _text(self.feature_id):
            raise ValueError("feature_id is required")
        if not _text(self.feature_version):
            raise ValueError("feature_version is required")
        if self.input_count is not None and (
            not isinstance(self.input_count, int)
            or isinstance(self.input_count, bool)
            or self.input_count < 1
        ):
            raise ValueError("input_count must be a positive integer")

    @property
    def identifier(self) -> str:
        return self.feature_id


PRICE_VELOCITY_DEFINITION = FeatureDefinition(
    feature_id=PRICE_VELOCITY,
    feature_version="price-velocity-v1",
    input_count=2,
    value_unit_suffix="/second",
)
PRICE_ACCELERATION_DEFINITION = FeatureDefinition(
    feature_id=PRICE_ACCELERATION,
    feature_version="price-acceleration-v1",
    input_count=3,
    value_unit_suffix="/second^2",
)


@dataclass(frozen=True)
class FeatureCalculationContext:
    """Explicit point-in-time context supplied by the caller."""

    reference_time: datetime | None
    freshness_policy: FreshnessPolicy | None
    evaluation_id: str | None = None
    processing_time: datetime | None = None


@dataclass(frozen=True)
class FeatureInputReference:
    """Immutable replay reference for one consumed or inspected observation."""

    observation_id: str | None
    observation_time: datetime | None
    received_time: datetime | None
    source_id: str | None
    chain_id: str | None
    token_identity: str | None
    market_subject_id: str | None
    value: str | None
    price_unit: str | None
    quote_asset: str | None
    p02_contract_version: str | None
    upstream_state_version: str | None
    upstream_state_digest: str | None
    upstream_contract_version: str | None

    @property
    def identity(self) -> str | None:
        return self.observation_id


@dataclass(frozen=True)
class FeatureUpstreamReference:
    """Immutable linkage to one P02-T08 state reference."""

    observation_id: str | None
    state_version: str | None
    state_digest: str | None
    contract_version: str | None


@dataclass(frozen=True)
class FeatureSnapshotLinkage:
    """Non-persisting linkage suitable for a later signal snapshot."""

    reference_time: datetime | None
    input_set_digest: str
    observation_ids: tuple[str, ...]
    upstream_references: tuple[FeatureUpstreamReference, ...]
    p02_contract_version: str | None
    feature_representation_digest: str


@dataclass(frozen=True)
class FeatureCalculationResult:
    """Immutable calculated value or explicit fail-closed outcome."""

    result_id: str
    status: FeatureCalculationStatus
    reason_codes: tuple[str, ...]
    feature_id: str
    feature_version: str
    contract_version: str
    value: Decimal | None
    value_unit: str | None
    price_unit: str | None
    quote_asset: str | None
    source_id: str | None
    chain_id: str | None
    token_identity: str | None
    market_subject_id: str | None
    reference_time: datetime | None
    freshness_policy: FreshnessPolicy | None
    evaluation_id: str | None
    inputs: tuple[FeatureInputReference, ...]
    upstream_references: tuple[FeatureUpstreamReference, ...]
    input_set_digest: str
    snapshot_linkage: FeatureSnapshotLinkage
    representation_digest: str

    @property
    def outcome(self) -> FeatureCalculationStatus:
        return self.status

    @property
    def feature_value(self) -> Decimal | None:
        return self.value

    @property
    def value_available(self) -> bool:
        return self.status is FeatureCalculationStatus.CALCULATED

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reason_codes

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(_result_material(self))

    @property
    def digest(self) -> str:
        return self.representation_digest


class FeatureCalculator:
    """Pure calculator for the two authorized P04-T09 price features."""

    def calculate(
        self,
        feature: FeatureDefinition | str,
        observations: Iterable[AcceptedMarketIntelligenceObservation],
        *,
        context: FeatureCalculationContext | None = None,
        reference_time: datetime | None = None,
        freshness_policy: FreshnessPolicy | None = None,
        feature_version: str | None = None,
        evaluation_id: str | None = None,
        processing_time: datetime | None = None,
    ) -> FeatureCalculationResult:
        definition = _definition(feature, feature_version)
        context = _context(
            context,
            reference_time=reference_time,
            freshness_policy=freshness_policy,
            evaluation_id=evaluation_id,
            processing_time=processing_time,
        )
        try:
            values = tuple(observations)
        except (TypeError, ValueError):
            values = ()
            request_reason = FeatureReason.INVALID_REQUEST.value
        else:
            request_reason = None
        return _calculate(definition, values, context, request_reason)


def calculate_feature(
    feature: FeatureDefinition | str,
    observations: Iterable[AcceptedMarketIntelligenceObservation],
    *,
    context: FeatureCalculationContext | None = None,
    reference_time: datetime | None = None,
    freshness_policy: FreshnessPolicy | None = None,
    feature_version: str | None = None,
    evaluation_id: str | None = None,
    processing_time: datetime | None = None,
) -> FeatureCalculationResult:
    return FeatureCalculator().calculate(
        feature,
        observations,
        context=context,
        reference_time=reference_time,
        freshness_policy=freshness_policy,
        feature_version=feature_version,
        evaluation_id=evaluation_id,
        processing_time=processing_time,
    )


def calculate_price_velocity(
    observations: Iterable[AcceptedMarketIntelligenceObservation],
    *,
    context: FeatureCalculationContext | None = None,
    reference_time: datetime | None = None,
    freshness_policy: FreshnessPolicy | None = None,
    feature_version: str | None = None,
    evaluation_id: str | None = None,
    processing_time: datetime | None = None,
) -> FeatureCalculationResult:
    return calculate_feature(
        PRICE_VELOCITY_DEFINITION,
        observations,
        context=context,
        reference_time=reference_time,
        freshness_policy=freshness_policy,
        feature_version=feature_version,
        evaluation_id=evaluation_id,
        processing_time=processing_time,
    )


def calculate_price_acceleration(
    observations: Iterable[AcceptedMarketIntelligenceObservation],
    *,
    context: FeatureCalculationContext | None = None,
    reference_time: datetime | None = None,
    freshness_policy: FreshnessPolicy | None = None,
    feature_version: str | None = None,
    evaluation_id: str | None = None,
    processing_time: datetime | None = None,
) -> FeatureCalculationResult:
    return calculate_feature(
        PRICE_ACCELERATION_DEFINITION,
        observations,
        context=context,
        reference_time=reference_time,
        freshness_policy=freshness_policy,
        feature_version=feature_version,
        evaluation_id=evaluation_id,
        processing_time=processing_time,
    )


def _calculate(
    definition: FeatureDefinition,
    values: tuple[object, ...],
    context: FeatureCalculationContext | None,
    request_reason: str | None,
) -> FeatureCalculationResult:
    refs = tuple(_input_reference(value) for value in values)
    refs = tuple(sorted(refs, key=_reference_sort_key))
    input_digest = _digest({"inputs": [_reference_material(item) for item in refs]})
    upstream_refs = _upstream_references(values)

    if request_reason is not None:
        return _result(
            definition, context, FeatureCalculationStatus.INVALID,
            (request_reason,), refs, upstream_refs, input_digest,
        )
    if definition.feature_id not in (PRICE_VELOCITY, PRICE_ACCELERATION):
        return _result(
            definition, context, FeatureCalculationStatus.UNSUPPORTED,
            (FeatureReason.UNSUPPORTED_FEATURE.value,), refs, upstream_refs, input_digest,
        )
    if definition.feature_version != _definition_for(definition.feature_id).feature_version:
        return _result(
            definition, context, FeatureCalculationStatus.UNSUPPORTED,
            (FeatureReason.UNSUPPORTED_FEATURE.value,), refs, upstream_refs, input_digest,
        )
    if context is None or context.reference_time is None or context.freshness_policy is None:
        return _result(
            definition, context, FeatureCalculationStatus.UNKNOWN,
            (FeatureReason.MISSING_CALCULATION_CONTEXT.value,), refs, upstream_refs, input_digest,
        )
    if not _aware(context.reference_time) or not _valid_policy(context.freshness_policy):
        return _result(
            definition, context, FeatureCalculationStatus.INVALID,
            (FeatureReason.INVALID_REQUEST.value,), refs, upstream_refs, input_digest,
        )

    observations = values
    if not observations:
        return _result(
            definition, context, FeatureCalculationStatus.UNKNOWN,
            (FeatureReason.INSUFFICIENT_PRICE_OBSERVATIONS.value,), refs,
            upstream_refs, input_digest,
        )

    reasons: set[str] = set()
    normalized: list[tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]] = []
    for item in observations:
        item_reasons = _validate_input(item, context.reference_time)
        reasons.update(item_reasons)
        if item_reasons:
            continue
        assert isinstance(item, AcceptedMarketIntelligenceObservation)
        value, numeric_reason = _numeric_value(item.value)
        metadata = item.provenance.observation_metadata
        unit = _semantic(metadata, "unit")
        quote = _semantic(metadata, "quote_asset")
        if numeric_reason is not None:
            reasons.add(numeric_reason)
        if unit is None or quote is None or _semantic(metadata, "measurement") != "price":
            reasons.add(FeatureReason.MISSING_PRICE_SEMANTICS.value)
        if numeric_reason is None and unit is not None and quote is not None and (
            _semantic(metadata, "measurement") == "price"
        ):
            normalized.append((item, value, unit, quote))

    if reasons:
        # Future/unavailable information must never be hidden by selecting a
        # subset.  Structural input failures also fail the complete request.
        return _result(
            definition, context, _status_for_reasons(reasons),
            tuple(reasons), refs, upstream_refs, input_digest,
            normalized=normalized,
        )

    identity_reasons = _identity_and_duplicate_reasons(normalized)
    if identity_reasons:
        return _result(
            definition, context, FeatureCalculationStatus.UNKNOWN,
            tuple(identity_reasons), refs, upstream_refs, input_digest,
            normalized=normalized,
        )

    common = normalized[0]
    for item, _, unit, quote in normalized[1:]:
        if unit != common[2]:
            reasons.add(FeatureReason.INCOMPATIBLE_PRICE_UNIT.value)
        if quote != common[3]:
            reasons.add(FeatureReason.INCOMPATIBLE_QUOTE_ASSET.value)
        if _subject(item) != _subject(common[0]):
            reasons.add(FeatureReason.CONTRADICTORY_INPUT.value)
    if reasons:
        return _result(
            definition, context, FeatureCalculationStatus.UNKNOWN,
            tuple(reasons), refs, upstream_refs, input_digest, normalized=normalized,
        )

    ordered = sorted(normalized, key=_observation_sort_key)
    needed = _definition_for(definition.feature_id).input_count
    assert needed is not None
    selected = ordered[-needed:]
    if len(selected) < needed:
        return _result(
            definition, context, FeatureCalculationStatus.UNKNOWN,
            (FeatureReason.INSUFFICIENT_PRICE_OBSERVATIONS.value,), refs,
            upstream_refs, input_digest, normalized=normalized,
        )

    stale_after = context.freshness_policy.stale_after
    if stale_after is not None:
        stale = any(
            context.reference_time - item.observation_time > stale_after
            for item, *_ in selected
        )
        if stale:
            return _result(
                definition, context, FeatureCalculationStatus.UNKNOWN,
                (FeatureReason.STALE_INPUT.value,), refs, upstream_refs,
                input_digest, normalized=normalized,
            )

    selected_times = [item.observation_time for item, *_ in selected]
    if any(not _aware(value) for value in selected_times):
        return _result(
            definition, context, FeatureCalculationStatus.INVALID,
            (FeatureReason.INVALID_TIMESTAMP.value,), refs, upstream_refs, input_digest,
            normalized=normalized,
        )
    if len(set(selected_times)) != len(selected_times):
        return _result(
            definition, context, FeatureCalculationStatus.INVALID,
            (FeatureReason.ZERO_ELAPSED_TIME.value,), refs, upstream_refs, input_digest,
            normalized=normalized,
        )
    try:
        numeric = _calculate_numeric(definition.feature_id, selected)
    except (ArithmeticError, InvalidOperation, ValueError, OverflowError):
        return _result(
            definition, context, FeatureCalculationStatus.INVALID,
            (FeatureReason.ARITHMETIC_FAILURE.value,), refs, upstream_refs, input_digest,
            normalized=normalized,
        )
    return _result(
        definition, context, FeatureCalculationStatus.CALCULATED, (), refs,
        upstream_refs, input_digest, numeric=numeric, normalized=normalized,
    )


def _validate_input(
    item: object, reference_time: datetime
) -> set[str]:
    reasons: set[str] = set()
    if not isinstance(item, AcceptedMarketIntelligenceObservation):
        return {FeatureReason.INVALID_REQUEST.value}
    if item.intelligence_category is not MarketIntelligenceCategory.PRICE:
        return {FeatureReason.UNSUPPORTED_CATEGORY.value}
    if item.quality is not DataQuality.VALID or item.accepted is not True:
        reasons.add(
            FeatureReason.STALE_INPUT.value
            if item.quality is DataQuality.STALE
            else FeatureReason.UPSTREAM_NOT_ACCEPTED.value
        )
    if item.contract_version != P02_MARKET_INTELLIGENCE_CONTRACT_VERSION or (
        item.category_contract_version != P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
    ):
        reasons.add(FeatureReason.UNSUPPORTED_INPUT_VERSION.value)
    required = (
        item.observation_id,
        item.source_id,
        item.chain_id,
        item.token_identity,
        item.market_subject_id,
    )
    if any(not _text(value) for value in required):
        reasons.add(FeatureReason.MISSING_PROVENANCE.value)
    if not isinstance(item.provenance, object) or item.provenance is None:
        reasons.add(FeatureReason.MISSING_PROVENANCE.value)
    upstream = item.upstream
    if upstream is None:
        reasons.add(FeatureReason.MISSING_SNAPSHOT_LINK.value)
    else:
        for value in (
            getattr(upstream, "state_version", None),
            getattr(upstream, "state_digest", None),
            getattr(upstream, "contract_version", None),
        ):
            if not _text(value):
                reasons.add(FeatureReason.MISSING_SNAPSHOT_LINK.value)
        if getattr(upstream, "contract_version", None) != P02_T08_CONTRACT_VERSION:
            reasons.add(FeatureReason.UNSUPPORTED_INPUT_VERSION.value)
        if any(
            getattr(upstream, name, None) != getattr(item, name, None)
            for name in ("source_id", "chain_id", "token_identity", "market_subject_id")
        ):
            reasons.add(FeatureReason.UPSTREAM_IDENTITY_MISMATCH.value)
    for value in (item.observation_time, item.received_time, item.reference_time):
        if not _aware(value):
            reasons.add(FeatureReason.INVALID_TIMESTAMP.value)
    if _aware(item.observation_time) and _aware(item.received_time):
        if item.observation_time > item.received_time:
            reasons.add(FeatureReason.INVALID_TIMESTAMP_ORDER.value)
        if item.observation_time > reference_time:
            reasons.add(FeatureReason.FUTURE_OBSERVATION.value)
        if item.received_time > reference_time:
            reasons.add(FeatureReason.NOT_AVAILABLE_AT_REFERENCE_TIME.value)
    if _aware(item.observation_time) and _aware(item.reference_time):
        if item.observation_time > item.reference_time:
            reasons.add(FeatureReason.INVALID_TIMESTAMP_ORDER.value)
    if not isinstance(item.data_age, timedelta) or item.data_age < timedelta(0):
        reasons.add(FeatureReason.INVALID_TIMESTAMP.value)
    elif _aware(item.observation_time):
        age = reference_time - item.observation_time
        if age < timedelta(0):
            reasons.add(FeatureReason.FUTURE_OBSERVATION.value)
        elif item.data_age != item.reference_time - item.observation_time:
            reasons.add(FeatureReason.INVALID_TIMESTAMP_ORDER.value)
    if not _provenance_matches(item):
        reasons.add(FeatureReason.UPSTREAM_IDENTITY_MISMATCH.value)
    return reasons


def _provenance_matches(item: AcceptedMarketIntelligenceObservation) -> bool:
    provenance = item.provenance
    if provenance is None:
        return False
    return all(
        getattr(provenance, left, None) == getattr(item, right, None)
        for left, right in (
            ("source_id", "source_id"),
            ("observation_id", "observation_id"),
            ("chain_id", "chain_id"),
            ("token_identity", "token_identity"),
            ("market_subject_id", "market_subject_id"),
            ("observation_time", "observation_time"),
            ("received_time", "received_time"),
            ("reference_time", "reference_time"),
        )
    ) and getattr(provenance, "intelligence_category", None) is item.intelligence_category


def _identity_and_duplicate_reasons(
    normalized: list[tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]]
) -> tuple[str, ...]:
    reasons: set[str] = set()
    by_id: dict[str, tuple[Any, ...]] = {}
    by_fact: dict[tuple[Any, ...], str] = {}
    for item, value, unit, quote in normalized:
        content = _content_key(item, value, unit, quote)
        prior = by_id.get(item.observation_id)
        if prior is not None:
            if prior == content:
                reasons.add(FeatureReason.DUPLICATE_INPUT.value)
            elif prior[2] != content[2]:
                reasons.add(FeatureReason.CONTRADICTORY_INPUT.value)
        by_id[item.observation_id] = content
        fact = (
            _subject(item),
            _timestamp(item.observation_time),
            unit,
            quote,
        )
        prior_id = by_fact.get(fact)
        if prior_id is not None and prior_id != item.observation_id:
            reasons.add(FeatureReason.CONTRADICTORY_INPUT.value)
        by_fact[fact] = item.observation_id
    return tuple(sorted(reasons))


def _calculate_numeric(
    feature_id: str,
    selected: list[tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]],
) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = NUMERIC_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        if feature_id == PRICE_VELOCITY:
            first, second = selected[-2], selected[-1]
            elapsed = _seconds(second[0].observation_time - first[0].observation_time)
            if elapsed <= 0:
                raise ValueError("elapsed time must be positive")
            return _canonical_decimal((second[1] - first[1]) / elapsed)
        first, middle, last = selected[-3], selected[-2], selected[-1]
        elapsed_01 = _seconds(middle[0].observation_time - first[0].observation_time)
        elapsed_12 = _seconds(last[0].observation_time - middle[0].observation_time)
        elapsed_02 = _seconds(last[0].observation_time - first[0].observation_time)
        if min(elapsed_01, elapsed_12, elapsed_02) <= 0:
            raise ValueError("elapsed time must be positive")
        velocity_01 = (middle[1] - first[1]) / elapsed_01
        velocity_12 = (last[1] - middle[1]) / elapsed_12
        return _canonical_decimal(Decimal(2) * (velocity_12 - velocity_01) / elapsed_02)


def _result(
    definition: FeatureDefinition,
    context: FeatureCalculationContext | None,
    status: FeatureCalculationStatus,
    reasons: Iterable[str],
    refs: tuple[FeatureInputReference, ...],
    upstream_refs: tuple[FeatureUpstreamReference, ...],
    input_digest: str,
    *,
    numeric: Decimal | None = None,
    normalized: list[tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]] | None = None,
) -> FeatureCalculationResult:
    normalized = normalized or []
    reason_codes = tuple(sorted(set(str(value) for value in reasons if _text(value))))
    reference_time = context.reference_time if context else None
    policy = context.freshness_policy if context else None
    evaluation_id = context.evaluation_id if context else None
    subject = _common_subject(normalized)
    unit = normalized[0][2] if normalized and all(item[2] == normalized[0][2] for item in normalized) else None
    quote = normalized[0][3] if normalized and all(item[3] == normalized[0][3] for item in normalized) else None
    value_unit = None
    if status is FeatureCalculationStatus.CALCULATED and unit is not None:
        value_unit = unit + ("/second" if definition.feature_id == PRICE_VELOCITY else "/second^2")
    material = {
        "calculation_contract_version": P04_T09_CONTRACT_VERSION,
        "feature_id": definition.feature_id,
        "feature_version": definition.feature_version,
        "status": status.value,
        "reason_codes": reason_codes,
        "value": _decimal_text(numeric) if status is FeatureCalculationStatus.CALCULATED else None,
        "value_unit": value_unit,
        "price_unit": unit,
        "quote_asset": quote,
        "subject": _subject_material(subject),
        "reference_time": _timestamp(reference_time),
        "freshness_policy": _policy_material(policy),
        "evaluation_id": evaluation_id,
        "inputs": tuple(_reference_material(item) for item in refs),
        "upstream_references": tuple(_upstream_material(item) for item in upstream_refs),
        "input_set_digest": input_digest,
    }
    representation_digest = _digest(material)
    result_id = _digest({"representation_digest": representation_digest})
    linkage = FeatureSnapshotLinkage(
        reference_time=reference_time,
        input_set_digest=input_digest,
        observation_ids=tuple(item.observation_id for item in refs if item.observation_id is not None),
        upstream_references=upstream_refs,
        p02_contract_version=(
            P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
            if any(
                item.p02_contract_version == P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
                for item in refs
            )
            else None
        ),
        feature_representation_digest=representation_digest,
    )
    return FeatureCalculationResult(
        result_id=result_id,
        status=status,
        reason_codes=reason_codes,
        feature_id=definition.feature_id,
        feature_version=definition.feature_version,
        contract_version=P04_T09_CONTRACT_VERSION,
        value=numeric if status is FeatureCalculationStatus.CALCULATED else None,
        value_unit=value_unit,
        price_unit=unit,
        quote_asset=quote,
        source_id=subject[0] if subject else None,
        chain_id=subject[1] if subject else None,
        token_identity=subject[2] if subject else None,
        market_subject_id=subject[3] if subject else None,
        reference_time=reference_time,
        freshness_policy=policy,
        evaluation_id=evaluation_id,
        inputs=refs,
        upstream_references=upstream_refs,
        input_set_digest=input_digest,
        snapshot_linkage=linkage,
        representation_digest=representation_digest,
    )


def _input_reference(value: object) -> FeatureInputReference:
    if not isinstance(value, AcceptedMarketIntelligenceObservation):
        return FeatureInputReference(None, None, None, None, None, None, None, None, None, None, None, None, None, None)
    metadata = value.provenance.observation_metadata
    numeric, _ = _numeric_value(value.value)
    return FeatureInputReference(
        observation_id=value.observation_id if _text(value.observation_id) else None,
        observation_time=_utc_or_none(value.observation_time),
        received_time=_utc_or_none(value.received_time),
        source_id=value.source_id if _text(value.source_id) else None,
        chain_id=value.chain_id if _text(value.chain_id) else None,
        token_identity=value.token_identity if _text(value.token_identity) else None,
        market_subject_id=value.market_subject_id if _text(value.market_subject_id) else None,
        value=_decimal_text(numeric) if numeric is not None else None,
        price_unit=_semantic(metadata, "unit"),
        quote_asset=_semantic(metadata, "quote_asset"),
        p02_contract_version=value.contract_version if _text(value.contract_version) else None,
        upstream_state_version=getattr(value.upstream, "state_version", None),
        upstream_state_digest=getattr(value.upstream, "state_digest", None),
        upstream_contract_version=getattr(value.upstream, "contract_version", None),
    )


def _upstream_references(values: Iterable[object]) -> tuple[FeatureUpstreamReference, ...]:
    result = {
        (
            getattr(value, "observation_id", None),
            getattr(getattr(value, "upstream", None), "state_version", None),
            getattr(getattr(value, "upstream", None), "state_digest", None),
            getattr(getattr(value, "upstream", None), "contract_version", None),
        )
        for value in values
        if isinstance(value, AcceptedMarketIntelligenceObservation)
    }
    return tuple(FeatureUpstreamReference(*item) for item in sorted(result, key=lambda x: tuple("" if v is None else str(v) for v in x)))


def _definition(feature: FeatureDefinition | str, version: str | None) -> FeatureDefinition:
    if isinstance(feature, FeatureDefinition):
        if version is None:
            return feature
        return FeatureDefinition(feature.feature_id, version, feature.input_count, feature.value_unit_suffix)
    if isinstance(feature, str):
        known = _definition_for(feature)
        return FeatureDefinition(feature, version or known.feature_version, known.input_count, known.value_unit_suffix)
    return FeatureDefinition("invalid", version or "invalid")


def _definition_for(feature_id: str) -> FeatureDefinition:
    return {
        PRICE_VELOCITY: PRICE_VELOCITY_DEFINITION,
        PRICE_ACCELERATION: PRICE_ACCELERATION_DEFINITION,
    }.get(feature_id, FeatureDefinition(feature_id or "invalid", "unknown"))


def _context(
    context: FeatureCalculationContext | None,
    *,
    reference_time: datetime | None,
    freshness_policy: FreshnessPolicy | None,
    evaluation_id: str | None,
    processing_time: datetime | None,
) -> FeatureCalculationContext | None:
    if context is not None:
        return context
    if reference_time is None and freshness_policy is None and evaluation_id is None and processing_time is None:
        return None
    return FeatureCalculationContext(reference_time, freshness_policy, evaluation_id, processing_time)


def _numeric_value(value: object) -> tuple[Decimal | None, str | None]:
    if isinstance(value, bool) or value is None:
        return None, FeatureReason.INVALID_NUMERIC_VALUE.value
    if not isinstance(value, (int, float, str, Decimal)):
        return None, FeatureReason.INVALID_NUMERIC_VALUE.value
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, FeatureReason.INVALID_NUMERIC_VALUE.value
    if not result.is_finite():
        return None, FeatureReason.INVALID_NUMERIC_VALUE.value
    return _canonical_decimal(result), None


def _canonical_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    if value == 0:
        return Decimal(0)
    return value.normalize()


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    value = _canonical_decimal(value)
    return format(value, "f")


def _seconds(value: timedelta) -> Decimal:
    return Decimal(value.days * 86400 + value.seconds) + (Decimal(value.microseconds) / Decimal(1_000_000))


def _semantic(metadata: object, key: str) -> str | None:
    if not isinstance(metadata, Mapping):
        return None
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return None
    return value


def _subject(item: AcceptedMarketIntelligenceObservation) -> tuple[str, str, str, str]:
    return item.source_id, item.chain_id, item.token_identity, item.market_subject_id


def _common_subject(
    normalized: list[tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]]
) -> tuple[str, str, str, str] | None:
    if not normalized:
        return None
    subjects = {_subject(item) for item, *_ in normalized}
    return next(iter(subjects)) if len(subjects) == 1 else None


def _content_key(item: AcceptedMarketIntelligenceObservation, value: Decimal, unit: str, quote: str) -> tuple[Any, ...]:
    return (
        _subject(item), item.observation_id, _timestamp(item.observation_time),
        _timestamp(item.received_time), _timestamp(item.reference_time),
        _decimal_text(value), unit, quote, item.contract_version,
        getattr(item.upstream, "state_version", None),
        getattr(item.upstream, "state_digest", None),
        getattr(item.upstream, "contract_version", None),
    )


def _observation_sort_key(item: tuple[AcceptedMarketIntelligenceObservation, Decimal, str, str]) -> tuple[Any, ...]:
    observation, value, *_ = item
    return (_timestamp(observation.observation_time) or "", observation.observation_id, *_subject(observation), _decimal_text(value) or "")


def _reference_sort_key(item: FeatureInputReference) -> tuple[Any, ...]:
    return (
        _timestamp(item.observation_time) or "",
        item.observation_id or "",
        item.source_id or "",
        item.chain_id or "",
        item.token_identity or "",
        item.market_subject_id or "",
        item.value or "",
    )


def _reference_material(item: FeatureInputReference) -> dict[str, Any]:
    return {
        "observation_id": item.observation_id,
        "observation_time": _timestamp(item.observation_time),
        "received_time": _timestamp(item.received_time),
        "source_id": item.source_id,
        "chain_id": item.chain_id,
        "token_identity": item.token_identity,
        "market_subject_id": item.market_subject_id,
        "value": item.value,
        "price_unit": item.price_unit,
        "quote_asset": item.quote_asset,
        "p02_contract_version": item.p02_contract_version,
        "upstream_state_version": item.upstream_state_version,
        "upstream_state_digest": item.upstream_state_digest,
        "upstream_contract_version": item.upstream_contract_version,
    }


def _upstream_material(item: FeatureUpstreamReference) -> dict[str, Any]:
    return {
        "observation_id": item.observation_id,
        "state_version": item.state_version,
        "state_digest": item.state_digest,
        "contract_version": item.contract_version,
    }


def _subject_material(subject: tuple[str, str, str, str] | None) -> dict[str, str] | None:
    if subject is None:
        return None
    return {
        "source_id": subject[0],
        "chain_id": subject[1],
        "token_identity": subject[2],
        "market_subject_id": subject[3],
    }


def _result_material(result: FeatureCalculationResult) -> dict[str, Any]:
    return {
        "calculation_contract_version": result.contract_version,
        "feature_id": result.feature_id,
        "feature_version": result.feature_version,
        "status": result.status.value,
        "reason_codes": result.reason_codes,
        "value": _decimal_text(result.value),
        "value_unit": result.value_unit,
        "price_unit": result.price_unit,
        "quote_asset": result.quote_asset,
        "subject": _subject_material(
            (result.source_id, result.chain_id, result.token_identity, result.market_subject_id)
            if result.source_id and result.chain_id and result.token_identity and result.market_subject_id
            else None
        ),
        "reference_time": _timestamp(result.reference_time),
        "freshness_policy": _policy_material(result.freshness_policy),
        "evaluation_id": result.evaluation_id,
        "inputs": tuple(_reference_material(item) for item in result.inputs),
        "upstream_references": tuple(_upstream_material(item) for item in result.upstream_references),
        "input_set_digest": result.input_set_digest,
    }


def _policy_material(policy: FreshnessPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    return {"stale_after_seconds": _timedelta_seconds(policy.stale_after)}


def _valid_policy(policy: object) -> bool:
    return isinstance(policy, FreshnessPolicy) and (
        policy.stale_after is None
        or isinstance(policy.stale_after, timedelta)
        and policy.stale_after >= timedelta(0)
    )


def _status_for_reasons(reasons: set[str]) -> FeatureCalculationStatus:
    if FeatureReason.UNSUPPORTED_CATEGORY.value in reasons or FeatureReason.UNSUPPORTED_INPUT_VERSION.value in reasons:
        return FeatureCalculationStatus.UNSUPPORTED
    if any(reason in reasons for reason in (
        FeatureReason.INVALID_REQUEST.value,
        FeatureReason.INVALID_TIMESTAMP.value,
        FeatureReason.INVALID_TIMESTAMP_ORDER.value,
        FeatureReason.ZERO_ELAPSED_TIME.value,
        FeatureReason.INVALID_NUMERIC_VALUE.value,
        FeatureReason.FUTURE_OBSERVATION.value,
        FeatureReason.NOT_AVAILABLE_AT_REFERENCE_TIME.value,
        FeatureReason.UPSTREAM_IDENTITY_MISMATCH.value,
    )):
        return FeatureCalculationStatus.INVALID
    return FeatureCalculationStatus.UNKNOWN


def _timedelta_seconds(value: timedelta | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(_seconds(value))


def _timestamp(value: datetime | None) -> str | None:
    if not isinstance(value, datetime) or not _aware(value):
        return None
    return value.astimezone(timezone.utc).isoformat()


def _utc_or_none(value: object) -> datetime | None:
    return value.astimezone(timezone.utc) if isinstance(value, datetime) and _aware(value) else None


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite canonical value")
        return value
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return _timedelta_seconds(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, FeatureInputReference):
        return _reference_material(value)
    if isinstance(value, FeatureUpstreamReference):
        return _upstream_material(value)
    raise ValueError("value cannot be deterministically serialized")


__all__ = [
    "FeatureCalculationContext",
    "FeatureCalculationResult",
    "FeatureCalculationStatus",
    "FeatureDefinition",
    "FeatureInputReference",
    "FeatureReason",
    "FeatureSnapshotLinkage",
    "FeatureUpstreamReference",
    "FeatureCalculator",
    "P04_T09_CONTRACT_VERSION",
    "PRICE_ACCELERATION",
    "PRICE_ACCELERATION_DEFINITION",
    "PRICE_VELOCITY",
    "PRICE_VELOCITY_DEFINITION",
    "calculate_feature",
    "calculate_price_acceleration",
    "calculate_price_velocity",
]