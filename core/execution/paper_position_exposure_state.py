"""Immutable, deterministic P07-T03 paper state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    PaperFillOutcome,
    TradeSide,
)


P07_T03_CONTRACT_VERSION = "p07-t03-v1"
ROUNDING_MODE = "ROUND_HALF_EVEN"
MAX_DECIMAL_PLACES = 18
QUANT = Decimal("1e-18")


class StateQuality(StrEnum):
    PASS = "PASS"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


class ValuationStatus(StrEnum):
    PASS = "PASS"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


class TransitionStatus(StrEnum):
    APPLIED = "APPLIED"
    NO_CHANGE = "NO_CHANGE"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _decimal(value: Any, name: str, *, non_negative: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    if non_negative and value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _round(value: Decimal) -> Decimal:
    return _decimal(value, "calculation", non_negative=False).quantize(
        QUANT, rounding=ROUND_HALF_EVEN
    )


def _average_cost(total_cost: Decimal, quantity: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = MAX_DECIMAL_PLACES * 2
        return total_cost / quantity


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rounded = _round(value)
    return format(Decimal("0") if rounded == 0 else rounded.normalize(), "f")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    raise ValueError(f"{type(value).__name__} is not canonical")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _digest_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _texts(values: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    return tuple(sorted(dict.fromkeys(_text(item, name) for item in values)))


def _mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return _freeze(_canonical(value))


def _set_digest(instance: Any, field: str, source: Any) -> None:
    expected = _digest(source)
    supplied = getattr(instance, field)
    if supplied is not None:
        _digest_text(supplied, field)
        if supplied != expected:
            raise ValueError(f"{field} does not match canonical representation")
    object.__setattr__(instance, field, expected)


@dataclass(frozen=True)
class ValuationObservation:
    asset_identity: Mapping[str, Any]
    observation_id: str
    observed_at: datetime
    availability_time: datetime
    price: Decimal | None
    price_unit: str
    valuation_status: ValuationStatus | str
    source_contract_version: str
    source_provenance: Mapping[str, Any]
    max_age_seconds: Decimal | None = None
    observation_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_identity", _mapping(self.asset_identity, "asset_identity"))
        _text(self.observation_id, "observation_id")
        observed = _utc(self.observed_at, "observed_at")
        available = _utc(self.availability_time, "availability_time")
        if observed > available:
            raise ValueError("observed_at cannot follow availability_time")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "availability_time", available)
        try:
            object.__setattr__(self, "valuation_status", ValuationStatus(self.valuation_status))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported valuation_status") from error
        _text(self.price_unit, "price_unit")
        _text(self.source_contract_version, "source_contract_version")
        object.__setattr__(self, "source_provenance", _mapping(self.source_provenance, "source_provenance"))
        if self.price is not None:
            object.__setattr__(self, "price", _decimal(self.price, "price"))
        if self.max_age_seconds is not None:
            object.__setattr__(self, "max_age_seconds", _decimal(self.max_age_seconds, "max_age_seconds"))
        if self.valuation_status is ValuationStatus.PASS and self.price is None:
            raise ValueError("PASS valuation requires price")
        _set_digest(self, "observation_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "asset_identity": self.asset_identity, "observation_id": self.observation_id,
            "observed_at": self.observed_at, "availability_time": self.availability_time,
            "price": self.price, "price_unit": self.price_unit,
            "valuation_status": self.valuation_status, "source_contract_version": self.source_contract_version,
            "source_provenance": self.source_provenance, "max_age_seconds": self.max_age_seconds,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "observation_digest": self.observation_digest})


@dataclass(frozen=True)
class ValuationContext:
    observations: tuple[ValuationObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observations, (tuple, list)):
            raise ValueError("observations must be a tuple or list")
        values = tuple(self.observations)
        if any(not isinstance(item, ValuationObservation) for item in values):
            raise ValueError("observations must contain ValuationObservation values")
        keys = [_digest(item.asset_identity) for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate valuation asset identity")
        object.__setattr__(self, "observations", tuple(sorted(values, key=lambda item: _digest(item.asset_identity))))

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"observations": tuple(item.canonical_representation for item in self.observations)})


@dataclass(frozen=True)
class AccountingContext:
    fee_amount: Decimal
    priority_fee_amount: Decimal
    fee_unit: str
    observation_id: str
    accounting_contract_version: str
    provenance: Mapping[str, Any]
    observed_at: datetime
    availability_time: datetime
    context_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fee_amount", _decimal(self.fee_amount, "fee_amount"))
        object.__setattr__(self, "priority_fee_amount", _decimal(self.priority_fee_amount, "priority_fee_amount"))
        for value, name in ((self.fee_unit, "fee_unit"), (self.observation_id, "observation_id"),
                            (self.accounting_contract_version, "accounting_contract_version")):
            _text(value, name)
        object.__setattr__(self, "provenance", _mapping(self.provenance, "provenance"))
        observed, available = _utc(self.observed_at, "observed_at"), _utc(self.availability_time, "availability_time")
        if observed > available:
            raise ValueError("observed_at cannot follow availability_time")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "availability_time", available)
        _set_digest(self, "context_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {"fee_amount": self.fee_amount, "priority_fee_amount": self.priority_fee_amount,
                "fee_unit": self.fee_unit, "observation_id": self.observation_id,
                "accounting_contract_version": self.accounting_contract_version,
                "provenance": self.provenance, "observed_at": self.observed_at,
                "availability_time": self.availability_time}

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "context_digest": self.context_digest})


@dataclass(frozen=True)
class PaperPositionState:
    asset_identity: Mapping[str, Any]
    quantity_unit: str
    quantity: Decimal
    cost_basis_unit: str
    total_cost_basis: Decimal
    average_cost: Decimal | None
    position_quality: StateQuality | str = StateQuality.PASS
    position_provenance: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_identity", _mapping(self.asset_identity, "asset_identity"))
        _text(self.quantity_unit, "quantity_unit")
        _text(self.cost_basis_unit, "cost_basis_unit")
        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))
        object.__setattr__(self, "total_cost_basis", _decimal(self.total_cost_basis, "total_cost_basis"))
        if self.average_cost is not None:
            object.__setattr__(self, "average_cost", _decimal(self.average_cost, "average_cost"))
        if self.quantity == 0:
            if self.total_cost_basis != 0 or self.average_cost is not None:
                raise ValueError("zero position must have zero cost and null average_cost")
        elif self.average_cost is None or _round(self.average_cost * self.quantity) != _round(self.total_cost_basis):
            raise ValueError("average_cost does not match total_cost_basis")
        try:
            object.__setattr__(self, "position_quality", StateQuality(self.position_quality))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported position_quality") from error
        object.__setattr__(self, "position_provenance", _mapping(self.position_provenance, "position_provenance"))

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"asset_identity": self.asset_identity, "quantity_unit": self.quantity_unit,
                        "quantity": self.quantity, "cost_basis_unit": self.cost_basis_unit,
                        "total_cost_basis": self.total_cost_basis, "average_cost": self.average_cost,
                        "position_quality": self.position_quality, "position_provenance": self.position_provenance})


@dataclass(frozen=True)
class PaperExposureAsset:
    asset_identity: Mapping[str, Any]
    quantity: Decimal
    valuation_price: Decimal | None
    price_unit: str
    notional: Decimal | None
    valuation_timestamp: datetime | None
    valuation_status: ValuationStatus | str
    source_identity: str | None
    source_digest: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_identity", _mapping(self.asset_identity, "asset_identity"))
        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))
        if self.valuation_price is not None:
            object.__setattr__(self, "valuation_price", _decimal(self.valuation_price, "valuation_price"))
        if self.notional is not None:
            object.__setattr__(self, "notional", _decimal(self.notional, "notional"))
        _text(self.price_unit, "price_unit")
        if self.valuation_timestamp is not None:
            object.__setattr__(self, "valuation_timestamp", _utc(self.valuation_timestamp, "valuation_timestamp"))
        object.__setattr__(self, "valuation_status", ValuationStatus(self.valuation_status))
        if self.source_identity is not None:
            _text(self.source_identity, "source_identity")
        if self.source_digest is not None:
            _digest_text(self.source_digest, "source_digest")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"asset_identity": self.asset_identity, "quantity": self.quantity,
                        "valuation_price": self.valuation_price, "price_unit": self.price_unit,
                        "notional": self.notional, "valuation_timestamp": self.valuation_timestamp,
                        "valuation_status": self.valuation_status, "source_identity": self.source_identity,
                        "source_digest": self.source_digest})


@dataclass(frozen=True)
class PaperExposureState:
    portfolio_scope: Mapping[str, Any]
    asset_exposures: tuple[PaperExposureAsset, ...]
    gross_quantity_exposure: Decimal | None
    gross_notional_exposure: Decimal | None
    valuation_status: ValuationStatus | str
    exposure_provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "portfolio_scope", _mapping(self.portfolio_scope, "portfolio_scope"))
        values = tuple(self.asset_exposures)
        if any(not isinstance(item, PaperExposureAsset) for item in values):
            raise ValueError("asset_exposures must contain PaperExposureAsset values")
        if len({_digest(item.asset_identity) for item in values}) != len(values):
            raise ValueError("duplicate exposure asset identity")
        object.__setattr__(self, "asset_exposures", tuple(sorted(values, key=lambda item: _digest(item.asset_identity))))
        if self.gross_quantity_exposure is not None:
            object.__setattr__(self, "gross_quantity_exposure", _decimal(self.gross_quantity_exposure, "gross_quantity_exposure"))
        if self.gross_notional_exposure is not None:
            object.__setattr__(self, "gross_notional_exposure", _decimal(self.gross_notional_exposure, "gross_notional_exposure"))
        object.__setattr__(self, "valuation_status", ValuationStatus(self.valuation_status))
        object.__setattr__(self, "exposure_provenance", _mapping(self.exposure_provenance, "exposure_provenance"))

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"portfolio_scope": self.portfolio_scope,
                        "asset_exposures": tuple(item.canonical_representation for item in self.asset_exposures),
                        "gross_quantity_exposure": self.gross_quantity_exposure,
                        "gross_notional_exposure": self.gross_notional_exposure,
                        "valuation_status": self.valuation_status,
                        "exposure_provenance": self.exposure_provenance})


@dataclass(frozen=True)
class PaperPositionExposureState:
    state_id: str
    state_version: str
    portfolio_scope: Mapping[str, Any]
    positions: tuple[PaperPositionState, ...]
    exposure: PaperExposureState
    as_of_time: datetime
    state_quality: StateQuality | str = StateQuality.PASS
    state_provenance: Mapping[str, Any] = MappingProxyType({})
    state_digest: str | None = None

    def __post_init__(self) -> None:
        _text(self.state_id, "state_id")
        _text(self.state_version, "state_version")
        object.__setattr__(self, "portfolio_scope", _mapping(self.portfolio_scope, "portfolio_scope"))
        values = tuple(self.positions)
        if any(not isinstance(item, PaperPositionState) for item in values):
            raise ValueError("positions must contain PaperPositionState values")
        if len({_digest(item.asset_identity) for item in values}) != len(values):
            raise ValueError("duplicate position asset identity")
        object.__setattr__(self, "positions", tuple(sorted(values, key=lambda item: _digest(item.asset_identity))))
        if not isinstance(self.exposure, PaperExposureState):
            raise ValueError("exposure must be PaperExposureState")
        if self.exposure.portfolio_scope != self.portfolio_scope:
            raise ValueError("exposure portfolio scope mismatch")
        object.__setattr__(self, "as_of_time", _utc(self.as_of_time, "as_of_time"))
        object.__setattr__(self, "state_quality", StateQuality(self.state_quality))
        object.__setattr__(self, "state_provenance", _mapping(self.state_provenance, "state_provenance"))
        _set_digest(self, "state_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {"state_id": self.state_id, "state_version": self.state_version,
                "portfolio_scope": self.portfolio_scope,
                "positions": tuple(item.canonical_representation for item in self.positions),
                "exposure": self.exposure.canonical_representation,
                "as_of_time": self.as_of_time, "state_quality": self.state_quality,
                "state_provenance": self.state_provenance}

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "state_digest": self.state_digest})

    @property
    def digest(self) -> str:
        return self.state_digest  # type: ignore[return-value]


@dataclass(frozen=True)
class QuantityEffect:
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    prior_quantity: Decimal
    next_quantity: Decimal | None
    quantity_unit: str

    def __post_init__(self) -> None:
        for value, name in ((self.requested_quantity, "requested_quantity"), (self.filled_quantity, "filled_quantity"),
                            (self.remaining_quantity, "remaining_quantity"), (self.prior_quantity, "prior_quantity")):
            _decimal(value, name)
        if self.filled_quantity + self.remaining_quantity != self.requested_quantity:
            raise ValueError("quantity conservation invariant violated")
        if self.next_quantity is not None:
            object.__setattr__(self, "next_quantity", _decimal(self.next_quantity, "next_quantity"))
        _text(self.quantity_unit, "quantity_unit")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"requested_quantity": self.requested_quantity, "filled_quantity": self.filled_quantity,
                        "remaining_quantity": self.remaining_quantity, "prior_quantity": self.prior_quantity,
                        "next_quantity": self.next_quantity, "quantity_unit": self.quantity_unit})


@dataclass(frozen=True)
class AccountingEffect:
    fee_amount: Decimal
    priority_fee_amount: Decimal
    trade_value: Decimal | None
    acquisition_cost: Decimal | None
    removed_cost: Decimal | None
    proceeds: Decimal | None
    unit: str

    def __post_init__(self) -> None:
        for value, name in ((self.fee_amount, "fee_amount"), (self.priority_fee_amount, "priority_fee_amount")):
            object.__setattr__(self, name, _decimal(value, name))
        for value, name in ((self.trade_value, "trade_value"), (self.acquisition_cost, "acquisition_cost"),
                            (self.removed_cost, "removed_cost"), (self.proceeds, "proceeds")):
            if value is not None:
                object.__setattr__(self, name, _decimal(value, name, non_negative=False))
        _text(self.unit, "unit")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"fee_amount": self.fee_amount, "priority_fee_amount": self.priority_fee_amount,
                        "trade_value": self.trade_value, "acquisition_cost": self.acquisition_cost,
                        "removed_cost": self.removed_cost, "proceeds": self.proceeds, "unit": self.unit})


@dataclass(frozen=True)
class ExposureEffect:
    prior_exposure: PaperExposureState
    next_exposure: PaperExposureState | None

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({"prior_exposure": self.prior_exposure.canonical_representation,
                        "next_exposure": self.next_exposure.canonical_representation if self.next_exposure else None})


@dataclass(frozen=True)
class PaperStateTransitionResult:
    transition_status: TransitionStatus | str
    transition_reference_time: datetime
    prior_state: PaperPositionExposureState
    outcome_identity: Mapping[str, Any]
    next_state: PaperPositionExposureState | None
    quantity_effect: QuantityEffect
    accounting_effect: AccountingEffect
    exposure_effect: ExposureEffect
    reason_codes: tuple[str, ...]
    provenance: Mapping[str, Any]
    contract_version: str = P07_T03_CONTRACT_VERSION
    transition_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "transition_status", TransitionStatus(self.transition_status))
        object.__setattr__(self, "transition_reference_time", _utc(self.transition_reference_time, "transition_reference_time"))
        if not isinstance(self.prior_state, PaperPositionExposureState):
            raise ValueError("prior_state must be PaperPositionExposureState")
        if self.next_state is not None and not isinstance(self.next_state, PaperPositionExposureState):
            raise ValueError("next_state must be PaperPositionExposureState or None")
        if not isinstance(self.quantity_effect, QuantityEffect) or not isinstance(self.accounting_effect, AccountingEffect):
            raise ValueError("invalid transition effects")
        if not isinstance(self.exposure_effect, ExposureEffect):
            raise ValueError("exposure_effect must be ExposureEffect")
        object.__setattr__(self, "outcome_identity", _mapping(self.outcome_identity, "outcome_identity"))
        object.__setattr__(self, "reason_codes", _texts(self.reason_codes, "reason_codes"))
        object.__setattr__(self, "provenance", _mapping(self.provenance, "provenance"))
        if self.contract_version != P07_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T03 contract_version")
        _set_digest(self, "transition_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {"contract_version": self.contract_version, "transition_status": self.transition_status,
                "transition_reference_time": self.transition_reference_time,
                "prior_state": self.prior_state.canonical_representation,
                "outcome_identity": self.outcome_identity,
                "next_state": self.next_state.canonical_representation if self.next_state else None,
                "quantity_effect": self.quantity_effect.canonical_representation,
                "accounting_effect": self.accounting_effect.canonical_representation,
                "exposure_effect": self.exposure_effect.canonical_representation,
                "reason_codes": self.reason_codes, "provenance": self.provenance,
                "rounding_mode": ROUNDING_MODE, "max_decimal_places": MAX_DECIMAL_PLACES}

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "transition_digest": self.transition_digest,
                        "rounding_mode": ROUNDING_MODE, "max_decimal_places": MAX_DECIMAL_PLACES})

    @property
    def digest(self) -> str:
        return self.transition_digest  # type: ignore[return-value]


def _outcome_identity(outcome: PaperFillOutcome) -> Mapping[str, Any]:
    return {"outcome_digest": outcome.outcome_digest, "contract_version": outcome.contract_version,
            "fill_model_version": outcome.fill_model_version, "friction_model_version": outcome.friction_model_version,
            "p07_t01_input_digest": outcome.p07_t01_input_digest, "replay_id": outcome.replay_id,
            "execution_observation_id": outcome.execution_observation_id,
            "execution_observation_digest": outcome.execution_observation_digest,
            "side": outcome.side, "quantity_unit": outcome.quantity_unit}


def transition_paper_state(
    outcome: PaperFillOutcome,
    prior_state: PaperPositionExposureState,
    *,
    target_asset_identity: Mapping[str, Any],
    valuation_context: ValuationContext,
    accounting_context: AccountingContext,
    transition_reference_time: datetime,
) -> PaperStateTransitionResult:
    """Apply one accepted T02 outcome to one immutable paper state."""
    if not isinstance(outcome, PaperFillOutcome):
        raise TypeError("outcome must be PaperFillOutcome")
    _digest_text(outcome.outcome_digest, "outcome_digest")
    if not isinstance(prior_state, PaperPositionExposureState):
        raise TypeError("prior_state must be PaperPositionExposureState")
    reference = _utc(transition_reference_time, "transition_reference_time")
    target = _mapping(target_asset_identity, "target_asset_identity")
    position = next((item for item in prior_state.positions if item.asset_identity == target), None)
    if position is None or sum(item.asset_identity == target for item in prior_state.positions) != 1:
        raise ValueError("target asset identity must match exactly one position")
    if not isinstance(valuation_context, ValuationContext) or not isinstance(accounting_context, AccountingContext):
        raise TypeError("valuation_context and accounting_context have invalid types")
    if prior_state.as_of_time > reference:
        raise ValueError("prior state is future relative to transition reference time")
    if outcome.quote_observation_time and _utc(outcome.quote_observation_time, "quote_observation_time") > reference:
        return _result(TransitionStatus.REJECTED, reference, prior_state, outcome, position, reason=("FUTURE_TIMESTAMP",))
    if outcome.fill_time and _utc(outcome.fill_time, "fill_time") > reference:
        return _result(TransitionStatus.REJECTED, reference, prior_state, outcome, position, reason=("FUTURE_TIMESTAMP",))
    if accounting_context.availability_time > reference:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("ACCOUNTING_FUTURE",))
    if outcome.quantity_unit != position.quantity_unit:
        raise ValueError("quantity unit mismatch")
    if outcome.status is FillOutcomeStatus.FAILED:
        return _result(TransitionStatus.NO_CHANGE, reference, prior_state, outcome, position, reason=outcome.reason_codes)
    if outcome.status is FillOutcomeStatus.REJECTED:
        if "INSUFFICIENT_INVENTORY" in outcome.reason_codes:
            return _result(TransitionStatus.REJECTED, reference, prior_state, outcome, position, reason=outcome.reason_codes)
        return _result(TransitionStatus.NO_CHANGE, reference, prior_state, outcome, position, reason=outcome.reason_codes)
    if outcome.status is FillOutcomeStatus.UNAVAILABLE:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=outcome.reason_codes)
    if outcome.status is FillOutcomeStatus.INVALID:
        return _result(TransitionStatus.INVALID, reference, prior_state, outcome, position, reason=outcome.reason_codes)
    if outcome.filled_quantity <= 0:
        raise ValueError("successful outcome requires positive filled quantity")
    if position.position_quality is not StateQuality.PASS:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("INVENTORY_UNKNOWN",))
    if outcome.effective_price is None:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("EFFECTIVE_PRICE_UNKNOWN",))
    if accounting_context.fee_unit != outcome.fee_unit or accounting_context.fee_unit != position.cost_basis_unit:
        raise ValueError("accounting fee unit mismatch")
    if outcome.side is TradeSide.SELL and outcome.filled_quantity > position.quantity:
        return _result(TransitionStatus.REJECTED, reference, prior_state, outcome, position, reason=("INSUFFICIENT_INVENTORY",))
    valuation = next((item for item in valuation_context.observations if item.asset_identity == target), None)
    if valuation is None:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("VALUATION_UNKNOWN",))
    if valuation.availability_time > reference or valuation.observed_at > reference:
        return _result(TransitionStatus.REJECTED, reference, prior_state, outcome, position, reason=("FUTURE_VALUATION",))
    if valuation.max_age_seconds is None and valuation.valuation_status is ValuationStatus.PASS:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("FRESHNESS_POLICY_UNKNOWN",))
    if valuation.max_age_seconds is not None:
        delta = reference - valuation.observed_at
        age_seconds = (
            Decimal(delta.days * 86400 + delta.seconds)
            + (Decimal(delta.microseconds) / Decimal("1000000"))
        )
        if age_seconds >= valuation.max_age_seconds:
            return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("STALE_VALUATION",))
    if valuation.valuation_status is not ValuationStatus.PASS:
        return _result(TransitionStatus.UNAVAILABLE, reference, prior_state, outcome, position, reason=("VALUATION_UNKNOWN",))
    filled = _round(outcome.filled_quantity)
    trade_value = _round(filled * outcome.effective_price)
    fees = _round(accounting_context.fee_amount + accounting_context.priority_fee_amount)
    if outcome.side is TradeSide.BUY:
        next_quantity = _round(position.quantity + filled)
        acquisition = _round(trade_value + fees)
        next_cost = _round(position.total_cost_basis + acquisition)
        average = _average_cost(next_cost, next_quantity)
        accounting = AccountingEffect(accounting_context.fee_amount, accounting_context.priority_fee_amount,
                                      trade_value, acquisition, None, None, position.cost_basis_unit)
    else:
        next_quantity = _round(position.quantity - filled)
        removed = _round(filled * position.average_cost)  # type: ignore[operator]
        next_cost = Decimal("0") if next_quantity == 0 else _round(position.total_cost_basis - removed)
        proceeds = _round(trade_value - fees)
        average = None if next_quantity == 0 else _average_cost(next_cost, next_quantity)
        accounting = AccountingEffect(accounting_context.fee_amount, accounting_context.priority_fee_amount,
                                      trade_value, None, removed, proceeds, position.cost_basis_unit)
    next_position = PaperPositionState(target, position.quantity_unit, next_quantity, position.cost_basis_unit,
                                       next_cost, average, StateQuality.PASS,
                                       {"parent_state_digest": prior_state.digest, "outcome_digest": outcome.outcome_digest})
    next_exposure = _derive_exposure(prior_state, next_position, valuation, reference)
    next_state = PaperPositionExposureState(prior_state.state_id, prior_state.state_version, prior_state.portfolio_scope,
                                            tuple(next_position if item.asset_identity == target else item for item in prior_state.positions),
                                            next_exposure, reference, StateQuality.PASS,
                                            {"parent_state_digest": prior_state.digest, "outcome_digest": outcome.outcome_digest})
    quantity = QuantityEffect(outcome.requested_quantity, filled, _round(outcome.remaining_quantity),
                              position.quantity, next_quantity, position.quantity_unit)
    return PaperStateTransitionResult(TransitionStatus.APPLIED, reference, prior_state, _outcome_identity(outcome),
                                      next_state, quantity, accounting, ExposureEffect(prior_state.exposure, next_exposure),
                                      (), {"prior_state_digest": prior_state.digest, "outcome_digest": outcome.outcome_digest,
                                           "valuation_digest": valuation.observation_digest,
                                           "accounting_digest": accounting_context.context_digest})


def _derive_exposure(prior: PaperPositionExposureState, position: PaperPositionState,
                     valuation: ValuationObservation, reference: datetime) -> PaperExposureState:
    assets = []
    for item in prior.positions:
        if item.asset_identity == position.asset_identity:
            notional = _round(position.quantity * valuation.price)  # type: ignore[operator]
            assets.append(PaperExposureAsset(position.asset_identity, position.quantity, valuation.price,
                                             valuation.price_unit, notional, valuation.observed_at,
                                             valuation.valuation_status, valuation.observation_id,
                                             valuation.observation_digest))
        else:
            old = next(asset for asset in prior.exposure.asset_exposures if asset.asset_identity == item.asset_identity)
            assets.append(old)
    known = [item.notional for item in assets if item.notional is not None]
    status = ValuationStatus.PASS if len(known) == len(assets) else ValuationStatus.UNKNOWN
    return PaperExposureState(prior.portfolio_scope, tuple(assets),
                              _round(sum((item.quantity for item in assets), Decimal("0"))),
                              _round(sum(known, Decimal("0"))) if status is ValuationStatus.PASS else None,
                              status, {"valuation_observation": valuation.observation_digest})


def _result(status: TransitionStatus, reference: datetime, prior: PaperPositionExposureState,
            outcome: PaperFillOutcome, position: PaperPositionState, *, reason: tuple[str, ...]) -> PaperStateTransitionResult:
    quantity = QuantityEffect(outcome.requested_quantity, Decimal("0"), outcome.requested_quantity,
                              position.quantity, None, position.quantity_unit)
    accounting = AccountingEffect(Decimal("0"), Decimal("0"), None, None, None, None, position.cost_basis_unit)
    return PaperStateTransitionResult(status, reference, prior, _outcome_identity(outcome), prior if status is TransitionStatus.NO_CHANGE else None,
                                      quantity, accounting, ExposureEffect(prior.exposure, prior if status is TransitionStatus.NO_CHANGE else None),
                                      reason, {"prior_state_digest": prior.digest, "outcome_digest": outcome.outcome_digest})


apply_paper_state_transition = transition_paper_state
materialize_paper_state_transition = transition_paper_state

__all__ = [
    "AccountingContext", "AccountingEffect", "ExposureEffect", "MAX_DECIMAL_PLACES",
    "PaperExposureAsset", "PaperExposureState", "PaperPositionExposureState",
    "PaperPositionState", "PaperStateTransitionResult", "P07_T03_CONTRACT_VERSION",
    "QuantityEffect", "ROUNDING_MODE", "StateQuality", "TransitionStatus",
    "ValuationContext", "ValuationObservation", "ValuationStatus",
    "apply_paper_state_transition", "materialize_paper_state_transition",
    "transition_paper_state",
]