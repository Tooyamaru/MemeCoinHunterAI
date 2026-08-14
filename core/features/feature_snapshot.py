"""Immutable, deterministic P04-T10 feature-calculation snapshots.

This module captures an already-created P04-T09 result.  It revalidates the
result and its provenance without recalculating the feature or performing I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.data.contracts import FreshnessPolicy
from core.features.price_features import (
    FeatureCalculationResult,
    FeatureCalculationStatus,
    FeatureInputReference,
    FeatureSnapshotLinkage,
    FeatureUpstreamReference,
    P04_T09_CONTRACT_VERSION,
    _digest as _feature_digest,
    _reference_material,
)


P04_T10_CONTRACT_VERSION = "p04-t10-v1"


class FeatureSnapshotStatus(StrEnum):
    """Observable outcomes of the feature snapshot boundary."""

    SNAPSHOTTED = "SNAPSHOTTED"
    INVALID_INPUT = "INVALID_INPUT"

    CREATED = "SNAPSHOTTED"
    INVALID = "INVALID_INPUT"


FeatureCalculationSnapshotStatus = FeatureSnapshotStatus


@dataclass(frozen=True)
class FeatureCalculationSnapshot:
    """A point-in-time immutable representation of one T09 result."""

    calculation_result_id: str
    status: FeatureCalculationStatus
    reason_codes: tuple[str, ...]
    feature_id: str
    feature_version: str
    calculation_contract_version: str
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
    result_representation_digest: str
    contract_version: str = P04_T10_CONTRACT_VERSION

    @classmethod
    def from_result(
        cls,
        result: FeatureCalculationResult,
    ) -> FeatureCalculationSnapshot:
        return _require_snapshot(FeatureCalculationSnapshotResult.from_result(result))

    @classmethod
    def _from_valid_result(
        cls,
        result: FeatureCalculationResult,
    ) -> FeatureCalculationSnapshot:
        _validate_result(result)
        linkage = FeatureSnapshotLinkage(
            reference_time=(
                None
                if result.snapshot_linkage.reference_time is None
                else _to_utc(
                    result.snapshot_linkage.reference_time,
                    "snapshot_linkage.reference_time",
                )
            ),
            input_set_digest=result.snapshot_linkage.input_set_digest,
            observation_ids=result.snapshot_linkage.observation_ids,
            upstream_references=result.snapshot_linkage.upstream_references,
            p02_contract_version=result.snapshot_linkage.p02_contract_version,
            feature_representation_digest=(
                result.snapshot_linkage.feature_representation_digest
            ),
        )
        return cls(
            calculation_result_id=result.result_id,
            status=result.status,
            reason_codes=result.reason_codes,
            feature_id=result.feature_id,
            feature_version=result.feature_version,
            calculation_contract_version=result.contract_version,
            value=result.value,
            value_unit=result.value_unit,
            price_unit=result.price_unit,
            quote_asset=result.quote_asset,
            source_id=result.source_id,
            chain_id=result.chain_id,
            token_identity=result.token_identity,
            market_subject_id=result.market_subject_id,
            reference_time=result.reference_time,
            freshness_policy=result.freshness_policy,
            evaluation_id=result.evaluation_id,
            inputs=result.inputs,
            upstream_references=result.upstream_references,
            input_set_digest=result.input_set_digest,
            snapshot_linkage=linkage,
            result_representation_digest=result.representation_digest,
        )

    def __post_init__(self) -> None:
        try:
            status = FeatureCalculationStatus(self.status)
        except (TypeError, ValueError) as error:
            raise ValueError("status must be a FeatureCalculationStatus") from error
        object.__setattr__(self, "status", status)

        for value, name in (
            (self.calculation_result_id, "calculation_result_id"),
            (self.feature_id, "feature_id"),
            (self.feature_version, "feature_version"),
            (self.calculation_contract_version, "calculation_contract_version"),
            (self.input_set_digest, "input_set_digest"),
            (self.result_representation_digest, "result_representation_digest"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)

        if self.calculation_contract_version != P04_T09_CONTRACT_VERSION:
            raise ValueError("snapshot requires the P04-T09 result contract")
        if self.status is FeatureCalculationStatus.CALCULATED:
            if not isinstance(self.value, Decimal) or not self.value.is_finite():
                raise ValueError("CALCULATED snapshots require a finite Decimal value")
            _require_text(self.value_unit, "value_unit")
        elif self.value is not None or self.value_unit is not None:
            raise ValueError("non-calculated snapshots cannot contain a value")

        reason_codes = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reason_codes):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reason_codes))))

        if self.reference_time is not None:
            object.__setattr__(
                self,
                "reference_time",
                _to_utc(self.reference_time, "reference_time"),
            )
        if self.freshness_policy is not None and not isinstance(
            self.freshness_policy, FreshnessPolicy
        ):
            raise ValueError("freshness_policy must be a FreshnessPolicy")
        for value, name in (
            (self.source_id, "source_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.market_subject_id, "market_subject_id"),
            (self.evaluation_id, "evaluation_id"),
            (self.price_unit, "price_unit"),
            (self.quote_asset, "quote_asset"),
        ):
            if value is not None:
                _require_text(value, name)

        inputs = tuple(self.inputs)
        if not all(isinstance(value, FeatureInputReference) for value in inputs):
            raise ValueError("inputs must contain FeatureInputReference values")
        object.__setattr__(self, "inputs", inputs)

        upstream = tuple(self.upstream_references)
        if not all(isinstance(value, FeatureUpstreamReference) for value in upstream):
            raise ValueError(
                "upstream_references must contain FeatureUpstreamReference values"
            )
        object.__setattr__(self, "upstream_references", upstream)
        if not isinstance(self.snapshot_linkage, FeatureSnapshotLinkage):
            raise ValueError("snapshot_linkage must be a FeatureSnapshotLinkage")
        _validate_snapshot_linkage(self)

    @property
    def result_id(self) -> str:
        return self.calculation_result_id

    @property
    def source_result_id(self) -> str:
        return self.calculation_result_id

    @property
    def source_contract_version(self) -> str:
        return self.calculation_contract_version

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "calculation_result_id": self.calculation_result_id,
                "status": self.status.value,
                "reason_codes": self.reason_codes,
                "feature_id": self.feature_id,
                "feature_version": self.feature_version,
                "calculation_contract_version": self.calculation_contract_version,
                "value": _decimal_text(self.value),
                "value_unit": self.value_unit,
                "price_unit": self.price_unit,
                "quote_asset": self.quote_asset,
                "source_id": self.source_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "market_subject_id": self.market_subject_id,
                "reference_time": _timestamp(self.reference_time),
                "freshness_policy": _policy_material(self.freshness_policy),
                "evaluation_id": self.evaluation_id,
                "inputs": tuple(_reference_material(value) for value in self.inputs),
                "upstream_references": tuple(
                    _upstream_material(value) for value in self.upstream_references
                ),
                "input_set_digest": self.input_set_digest,
                "snapshot_linkage": _linkage_material(self.snapshot_linkage),
                "result_representation_digest": self.result_representation_digest,
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


@dataclass(frozen=True)
class FeatureCalculationSnapshotResult:
    """Explicit fail-closed outcome for snapshot creation."""

    snapshot_status: FeatureSnapshotStatus
    snapshotted: bool
    snapshot: FeatureCalculationSnapshot | None
    reason_codes: tuple[str, ...]
    calculation_result_id: str | None
    result_representation_digest: str | None
    contract_version: str = P04_T10_CONTRACT_VERSION

    @classmethod
    def from_result(
        cls,
        result: FeatureCalculationResult | object,
    ) -> FeatureCalculationSnapshotResult:
        if not isinstance(result, FeatureCalculationResult):
            return cls._invalid(("INVALID_CALCULATION_RESULT",))
        try:
            snapshot = FeatureCalculationSnapshot._from_valid_result(result)
        except (AttributeError, TypeError, ValueError):
            return cls._invalid(
                ("INVALID_CALCULATION_RESULT",),
                result=result,
            )
        return cls(
            snapshot_status=FeatureSnapshotStatus.SNAPSHOTTED,
            snapshotted=True,
            snapshot=snapshot,
            reason_codes=(),
            calculation_result_id=result.result_id,
            result_representation_digest=result.representation_digest,
        )

    @classmethod
    def _invalid(
        cls,
        reason_codes: tuple[str, ...],
        *,
        result: FeatureCalculationResult | None = None,
    ) -> FeatureCalculationSnapshotResult:
        result_id = _safe_result_text(result, "result_id")
        representation_digest = _safe_result_text(
            result,
            "representation_digest",
        )
        return cls(
            snapshot_status=FeatureSnapshotStatus.INVALID_INPUT,
            snapshotted=False,
            snapshot=None,
            reason_codes=reason_codes,
            calculation_result_id=result_id,
            result_representation_digest=representation_digest,
        )

    def __post_init__(self) -> None:
        try:
            status = FeatureSnapshotStatus(self.snapshot_status)
        except (TypeError, ValueError) as error:
            raise ValueError("snapshot_status must be a FeatureSnapshotStatus") from error
        object.__setattr__(self, "snapshot_status", status)
        if self.snapshotted is not (status is FeatureSnapshotStatus.SNAPSHOTTED):
            raise ValueError("snapshotted must match snapshot_status")
        if self.snapshotted and self.snapshot is None:
            raise ValueError("a SNAPSHOTTED result requires a snapshot")
        if not self.snapshotted and self.snapshot is not None:
            raise ValueError("an invalid result cannot contain a snapshot")
        reasons = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))
        for value, name in (
            (self.calculation_result_id, "calculation_result_id"),
            (self.result_representation_digest, "result_representation_digest"),
            (self.contract_version, "contract_version"),
        ):
            if value is not None:
                _require_text(value, name)

    @property
    def status(self) -> FeatureSnapshotStatus:
        return self.snapshot_status

    @property
    def valid(self) -> bool:
        return self.snapshotted

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "snapshot_status": self.snapshot_status.value,
                "snapshotted": self.snapshotted,
                "snapshot": (
                    None
                    if self.snapshot is None
                    else self.snapshot.canonical_representation
                ),
                "reason_codes": self.reason_codes,
                "calculation_result_id": self.calculation_result_id,
                "result_representation_digest": self.result_representation_digest,
                "contract_version": self.contract_version,
            }
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.representation_digest


def snapshot_feature_calculation(
    result: FeatureCalculationResult,
) -> FeatureCalculationSnapshot:
    return FeatureCalculationSnapshot.from_result(result)


create_feature_calculation_snapshot = snapshot_feature_calculation


def snapshot_feature_calculation_result(
    result: FeatureCalculationResult | object,
) -> FeatureCalculationSnapshotResult:
    return FeatureCalculationSnapshotResult.from_result(result)


create_feature_calculation_snapshot_result = snapshot_feature_calculation_result


def _require_snapshot(
    result: FeatureCalculationSnapshotResult,
) -> FeatureCalculationSnapshot:
    if not result.valid or result.snapshot is None:
        reason = ", ".join(result.reason_codes) or "UNSPECIFIED"
        raise ValueError(
            f"cannot create a FeatureCalculationSnapshot: "
            f"{result.snapshot_status.value} ({reason})"
        )
    return result.snapshot


def _validate_result(result: FeatureCalculationResult) -> None:
    try:
        status = FeatureCalculationStatus(result.status)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid calculation status") from error
    if status is not result.status:
        raise ValueError("calculation status is not normalized")
    if result.contract_version != P04_T09_CONTRACT_VERSION:
        raise ValueError("unsupported calculation contract")
    if not _is_text(result.feature_id) or not _is_text(result.feature_version):
        raise ValueError("feature identity is incomplete")
    if not isinstance(result.reason_codes, tuple) or any(
        not _is_text(value) for value in result.reason_codes
    ):
        raise ValueError("reason_codes are invalid")
    if tuple(sorted(dict.fromkeys(result.reason_codes))) != result.reason_codes:
        raise ValueError("reason_codes are not normalized")
    if status is FeatureCalculationStatus.CALCULATED:
        if not isinstance(result.value, Decimal) or not result.value.is_finite():
            raise ValueError("calculated value is invalid")
        if not _is_text(result.value_unit):
            raise ValueError("calculated value unit is missing")
    elif result.value is not None or result.value_unit is not None:
        raise ValueError("non-calculated result contains a value")

    if result.reference_time is not None:
        reference_time = _to_utc(result.reference_time, "reference_time")
    else:
        reference_time = None
    if result.freshness_policy is not None and not isinstance(
        result.freshness_policy, FreshnessPolicy
    ):
        raise ValueError("freshness policy is invalid")
    if not isinstance(result.inputs, tuple) or not all(
        isinstance(value, FeatureInputReference) for value in result.inputs
    ):
        raise ValueError("inputs are invalid")
    if not isinstance(result.upstream_references, tuple) or not all(
        isinstance(value, FeatureUpstreamReference)
        for value in result.upstream_references
    ):
        raise ValueError("upstream references are invalid")
    if not isinstance(result.snapshot_linkage, FeatureSnapshotLinkage):
        raise ValueError("snapshot linkage is invalid")
    for item in result.inputs:
        observation_time = (
            None
            if item.observation_time is None
            else _to_utc(item.observation_time, "input observation_time")
        )
        received_time = (
            None
            if item.received_time is None
            else _to_utc(item.received_time, "input received_time")
        )
        if (
            reference_time is not None
            and (
                observation_time is not None
                and observation_time > reference_time
                or received_time is not None
                and received_time > reference_time
            )
        ):
            raise ValueError("input is after the calculation reference_time")

    expected_linkage = FeatureSnapshotLinkage(
        reference_time=result.reference_time,
        input_set_digest=result.input_set_digest,
        observation_ids=tuple(
            item.observation_id
            for item in result.inputs
            if item.observation_id is not None
        ),
        upstream_references=result.upstream_references,
        p02_contract_version=(
            result.snapshot_linkage.p02_contract_version
        ),
        feature_representation_digest=result.representation_digest,
    )
    if result.snapshot_linkage != expected_linkage:
        raise ValueError("snapshot linkage does not match the calculation result")
    expected_input_digest = _feature_digest(
        {"inputs": [_reference_material(item) for item in result.inputs]}
    )
    if result.input_set_digest != expected_input_digest:
        raise ValueError("input_set_digest does not match the inputs")

    validated = FeatureCalculationResult(
        result_id=result.result_id,
        status=result.status,
        reason_codes=result.reason_codes,
        feature_id=result.feature_id,
        feature_version=result.feature_version,
        contract_version=result.contract_version,
        value=result.value,
        value_unit=result.value_unit,
        price_unit=result.price_unit,
        quote_asset=result.quote_asset,
        source_id=result.source_id,
        chain_id=result.chain_id,
        token_identity=result.token_identity,
        market_subject_id=result.market_subject_id,
        reference_time=result.reference_time,
        freshness_policy=result.freshness_policy,
        evaluation_id=result.evaluation_id,
        inputs=result.inputs,
        upstream_references=result.upstream_references,
        input_set_digest=result.input_set_digest,
        snapshot_linkage=result.snapshot_linkage,
        representation_digest=result.representation_digest,
    )
    expected_representation_digest = _feature_digest(result.canonical_representation)
    if (
        validated != result
        or result.representation_digest != expected_representation_digest
    ):
        raise ValueError("calculation result is not canonical")
    expected_result_id = _feature_digest(
        {"representation_digest": result.representation_digest}
    )
    if result.result_id != expected_result_id:
        raise ValueError("calculation result identity is invalid")


def _linkage_material(value: FeatureSnapshotLinkage) -> dict[str, Any]:
    return {
        "reference_time": _timestamp(value.reference_time),
        "input_set_digest": value.input_set_digest,
        "observation_ids": value.observation_ids,
        "upstream_references": tuple(
            _upstream_material(item) for item in value.upstream_references
        ),
        "p02_contract_version": value.p02_contract_version,
        "feature_representation_digest": value.feature_representation_digest,
    }


def _validate_snapshot_linkage(snapshot: FeatureCalculationSnapshot) -> None:
    expected_input_digest = _feature_digest(
        {"inputs": [_reference_material(item) for item in snapshot.inputs]}
    )
    if snapshot.input_set_digest != expected_input_digest:
        raise ValueError("input_set_digest does not match the snapshot inputs")
    linkage = snapshot.snapshot_linkage
    if (
        linkage.reference_time is None
        and snapshot.reference_time is not None
        or linkage.reference_time is not None
        and snapshot.reference_time is None
        or linkage.reference_time is not None
        and snapshot.reference_time is not None
        and _to_utc(linkage.reference_time, "linkage.reference_time")
        != snapshot.reference_time
    ):
        raise ValueError("snapshot linkage reference_time does not match")
    if linkage.input_set_digest != snapshot.input_set_digest:
        raise ValueError("snapshot linkage input_set_digest does not match")
    if linkage.observation_ids != tuple(
        item.observation_id
        for item in snapshot.inputs
        if item.observation_id is not None
    ):
        raise ValueError("snapshot linkage observation_ids do not match")
    if linkage.upstream_references != snapshot.upstream_references:
        raise ValueError("snapshot linkage upstream references do not match")
    if linkage.feature_representation_digest != snapshot.result_representation_digest:
        raise ValueError("snapshot linkage result digest does not match")
    if snapshot.calculation_result_id != _feature_digest(
        {"representation_digest": snapshot.result_representation_digest}
    ):
        raise ValueError("calculation result identity is invalid")
    if snapshot.reference_time is not None:
        for item in snapshot.inputs:
            for value, name in (
                (item.observation_time, "input observation_time"),
                (item.received_time, "input received_time"),
            ):
                if value is not None and _to_utc(value, name) > snapshot.reference_time:
                    raise ValueError("snapshot input is after reference_time")


def _upstream_material(value: FeatureUpstreamReference) -> dict[str, Any]:
    return {
        "observation_id": value.observation_id,
        "state_version": value.state_version,
        "state_digest": value.state_digest,
        "contract_version": value.contract_version,
    }


def _policy_material(value: FreshnessPolicy | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "stale_after_seconds": (
            None
            if value.stale_after is None
            else value.stale_after.total_seconds()
        )
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("value must be finite")
    return format(value.normalize(), "f")


def _timestamp(value: datetime | None) -> str | None:
    return None if value is None else _to_utc(value, "timestamp").isoformat()


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")


def _safe_text(value: Any, fallback: str | None) -> str | None:
    return value if _is_text(value) else fallback


def _safe_result_text(
    result: FeatureCalculationResult | None,
    field_name: str,
) -> str | None:
    if result is None:
        return None
    try:
        return _safe_text(getattr(result, field_name), None)
    except (AttributeError, TypeError, ValueError):
        return None


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


__all__ = [
    "FeatureCalculationSnapshot",
    "FeatureCalculationSnapshotStatus",
    "FeatureCalculationSnapshotResult",
    "FeatureSnapshotStatus",
    "P04_T10_CONTRACT_VERSION",
    "create_feature_calculation_snapshot",
    "create_feature_calculation_snapshot_result",
    "snapshot_feature_calculation",
    "snapshot_feature_calculation_result",
]