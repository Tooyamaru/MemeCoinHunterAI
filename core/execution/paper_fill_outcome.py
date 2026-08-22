"""Deterministic, immutable P07-T02 paper fill outcome contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.execution.paper_simulation_input import PaperSimulationInput


P07_T02_CONTRACT_VERSION = "p07-t02-v1"
P07_T02_FILL_MODEL_VERSION = "p07-t02-fill-v1"
P07_T02_FRICTION_MODEL_VERSION = "p07-t02-friction-v1"

P07_T02_ROUNDING_MODE = "ROUND_HALF_EVEN"
P07_T02_MAX_DECIMAL_PLACES = 18
P07_T02_QUANT = Decimal("1e-18")


class FillOutcomeStatus(StrEnum):
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class FrictionComponents:
    """Separate supplied price/fee effects for one deterministic evaluation."""

    fees: Decimal | None = Decimal("0")
    spread: Decimal | None = Decimal("0")
    slippage: Decimal | None = Decimal("0")
    price_impact: Decimal | None = Decimal("0")
    quote_drift: Decimal | None = Decimal("0")
    priority_fees: Decimal | None = Decimal("0")
    mev_adverse_ordering: Decimal | None = Decimal("0")
    evidence: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        for value, name in (
            (self.fees, "fees"),
            (self.spread, "spread"),
            (self.slippage, "slippage"),
            (self.price_impact, "price_impact"),
            (self.quote_drift, "quote_drift"),
            (self.priority_fees, "priority_fees"),
            (self.mev_adverse_ordering, "mev_adverse_ordering"),
        ):
            if value is not None:
                _decimal(value, name, non_negative=True)

        evidence = _freeze_mapping(self.evidence, "evidence")
        if any(
            getattr(self, name) is not None
            for name in (
                "fees",
                "spread",
                "slippage",
                "price_impact",
                "quote_drift",
                "priority_fees",
                "mev_adverse_ordering",
            )
        ) and not evidence:
            raise ValueError(
                "applied friction requires supplied evidence or versioned assumption"
            )

        object.__setattr__(self, "evidence", evidence)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "fees": _decimal_text(self.fees),
                "spread": _decimal_text(self.spread),
                "slippage": _decimal_text(self.slippage),
                "price_impact": _decimal_text(self.price_impact),
                "quote_drift": _decimal_text(self.quote_drift),
                "priority_fees": _decimal_text(self.priority_fees),
                "mev_adverse_ordering": _decimal_text(self.mev_adverse_ordering),
                "evidence": self.evidence,
            }
        )

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )


@dataclass(frozen=True)
class PaperFillOutcome:
    """One immutable hypothetical fill result; never a position or ledger event."""

    status: FillOutcomeStatus | str
    side: TradeSide | str
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    quantity_unit: str
    price_unit: str
    fee_unit: str
    reference_quote_price: Decimal | None
    effective_price: Decimal | None
    executable_liquidity: Decimal | None
    friction: FrictionComponents | None
    quote_observation_time: datetime | None
    fill_time: datetime | None
    latency_seconds: Decimal | None
    reason_codes: tuple[str, ...]
    p07_t01_input_digest: str
    simulation_configuration_id: str
    simulation_configuration_digest: str
    fill_model_version: str = P07_T02_FILL_MODEL_VERSION
    friction_model_version: str = P07_T02_FRICTION_MODEL_VERSION
    replay_id: str = ""
    execution_observation_id: str = ""
    execution_observation_digest: str = ""
    contract_version: str = P07_T02_CONTRACT_VERSION
    outcome_digest: str | None = None

    def __post_init__(self) -> None:
        _enum(self.status, FillOutcomeStatus, "status")
        object.__setattr__(self, "status", FillOutcomeStatus(self.status))

        _enum(self.side, TradeSide, "side")
        object.__setattr__(self, "side", TradeSide(self.side))

        for value, name in (
            (self.requested_quantity, "requested_quantity"),
            (self.filled_quantity, "filled_quantity"),
            (self.remaining_quantity, "remaining_quantity"),
        ):
            _decimal(value, name, non_negative=True)

        if self.requested_quantity <= 0:
            raise ValueError("requested_quantity must be greater than zero")

        if self.filled_quantity + self.remaining_quantity != self.requested_quantity:
            raise ValueError("quantity conservation invariant violated")

        if (
            self.executable_liquidity is not None
            and self.filled_quantity > self.executable_liquidity
        ):
            raise ValueError(
                "filled_quantity cannot exceed executable_liquidity"
            )

        if self.status in {
            FillOutcomeStatus.FAILED,
            FillOutcomeStatus.REJECTED,
            FillOutcomeStatus.UNAVAILABLE,
            FillOutcomeStatus.INVALID,
        } and self.filled_quantity != 0:
            raise ValueError("non-success outcomes cannot report positive fill")

        _text(self.quantity_unit, "quantity_unit")
        _text(self.price_unit, "price_unit")
        _text(self.fee_unit, "fee_unit")

        if self.reference_quote_price is not None:
            _decimal(
                self.reference_quote_price,
                "reference_quote_price",
                non_negative=True,
            )

        if self.effective_price is not None:
            _decimal(self.effective_price, "effective_price", non_negative=True)

        if self.executable_liquidity is not None:
            _decimal(
                self.executable_liquidity,
                "executable_liquidity",
                non_negative=True,
            )

        if self.friction is not None and not isinstance(
            self.friction, FrictionComponents
        ):
            raise ValueError("friction must be FrictionComponents or None")

        for value, name in (
            (self.quote_observation_time, "quote_observation_time"),
            (self.fill_time, "fill_time"),
        ):
            if value is not None:
                object.__setattr__(self, name, _utc(value, name))

        if self.quote_observation_time and self.fill_time:
            derived = _decimal(
                Decimal(
                    str(
                        (
                            self.fill_time
                            - self.quote_observation_time
                        ).total_seconds()
                    )
                ),
                "latency_seconds",
                non_negative=False,
            )

            if derived < 0:
                if not (
                    self.status is FillOutcomeStatus.INVALID
                    and "NEGATIVE_LATENCY" in self.reason_codes
                ):
                    raise ValueError("latency_seconds cannot be negative")

                if self.latency_seconds is not None:
                    raise ValueError(
                        "invalid negative-latency outcomes must not "
                        "materialize latency_seconds"
                    )

                object.__setattr__(self, "latency_seconds", None)
            else:
                if self.latency_seconds is not None:
                    _decimal(
                        self.latency_seconds,
                        "latency_seconds",
                        non_negative=True,
                    )
                    if self.latency_seconds != derived:
                        raise ValueError(
                            "latency_seconds does not match timestamps"
                        )
                object.__setattr__(self, "latency_seconds", derived)
        elif self.latency_seconds is not None:
            _decimal(
                self.latency_seconds,
                "latency_seconds",
                non_negative=True,
            )

        object.__setattr__(
            self,
            "reason_codes",
            _texts(self.reason_codes, "reason_codes"),
        )

        for value, name in (
            (self.p07_t01_input_digest, "p07_t01_input_digest"),
            (
                self.simulation_configuration_digest,
                "simulation_configuration_digest",
            ),
            (
                self.execution_observation_digest,
                "execution_observation_digest",
            ),
        ):
            _digest_text(value, name)

        for value, name in (
            (self.simulation_configuration_id, "simulation_configuration_id"),
            (self.fill_model_version, "fill_model_version"),
            (self.friction_model_version, "friction_model_version"),
            (self.replay_id, "replay_id"),
            (self.execution_observation_id, "execution_observation_id"),
        ):
            _text(value, name)

        if self.contract_version != P07_T02_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T02 contract_version")

        _set_or_verify_outcome_digest(self)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "status": self.status.value,
                "side": self.side.value,
                "requested_quantity": _decimal_text(self.requested_quantity),
                "filled_quantity": _decimal_text(self.filled_quantity),
                "remaining_quantity": _decimal_text(self.remaining_quantity),
                "quantity_unit": self.quantity_unit,
                "price_unit": self.price_unit,
                "fee_unit": self.fee_unit,
                "reference_quote_price": _decimal_text(
                    self.reference_quote_price
                ),
                "effective_price": _decimal_text(self.effective_price),
                "executable_liquidity": _decimal_text(
                    self.executable_liquidity
                ),
                "friction": (
                    self.friction.canonical_representation
                    if self.friction
                    else None
                ),
                "quote_observation_time": _timestamp(
                    self.quote_observation_time
                ),
                "fill_time": _timestamp(self.fill_time),
                "latency_seconds": _decimal_text(self.latency_seconds),
                "reason_codes": self.reason_codes,
                "p07_t01_input_digest": self.p07_t01_input_digest,
                "simulation_configuration_id": self.simulation_configuration_id,
                "simulation_configuration_digest": (
                    self.simulation_configuration_digest
                ),
                "fill_model_version": self.fill_model_version,
                "friction_model_version": self.friction_model_version,
                "replay_id": self.replay_id,
                "execution_observation_id": self.execution_observation_id,
                "execution_observation_digest": (
                    self.execution_observation_digest
                ),
                "contract_version": self.contract_version,
                "rounding_mode": P07_T02_ROUNDING_MODE,
                "max_decimal_places": P07_T02_MAX_DECIMAL_PLACES,
            }
        )

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )


def evaluate_paper_fill(
    simulation_input: PaperSimulationInput,
    *,
    side: TradeSide | str,
    requested_quantity: Decimal,
    quantity_unit: str,
    price_unit: str,
    fee_unit: str,
    executable_liquidity: Decimal,
    reference_quote_price: Decimal,
    quote_observation_time: datetime,
    fill_time: datetime,
    friction: FrictionComponents,
    available_inventory: Decimal | None = None,
) -> PaperFillOutcome:
    """Evaluate one bounded hypothetical fill from supplied evidence only."""

    if not isinstance(simulation_input, PaperSimulationInput):
        raise TypeError("simulation_input must be a PaperSimulationInput")

    side_value = TradeSide(side)
    reference = simulation_input.simulation_reference_time

    base = dict(
        status=FillOutcomeStatus.INVALID,
        side=side_value,
        requested_quantity=requested_quantity,
        filled_quantity=Decimal("0"),
        remaining_quantity=requested_quantity,
        quantity_unit=quantity_unit,
        price_unit=price_unit,
        fee_unit=fee_unit,
        reference_quote_price=reference_quote_price,
        effective_price=None,
        executable_liquidity=executable_liquidity,
        friction=friction,
        quote_observation_time=quote_observation_time,
        fill_time=fill_time,
        latency_seconds=None,
        reason_codes=(),
        p07_t01_input_digest=simulation_input.input_digest,
        simulation_configuration_id=(
            simulation_input.simulation_configuration.configuration_id
        ),
        simulation_configuration_digest=(
            simulation_input.simulation_configuration.configuration_digest
        ),
        replay_id=simulation_input.replay_identity.replay_id,
        execution_observation_id=(
            simulation_input.execution_observation.observation_id
        ),
        execution_observation_digest=(
            simulation_input.execution_observation.observation_digest
        ),
    )

    if not isinstance(requested_quantity, Decimal):
        raise TypeError("requested_quantity must be a finite Decimal")
    if not requested_quantity.is_finite():
        raise ValueError("requested_quantity must be a finite Decimal")

    if not isinstance(executable_liquidity, Decimal):
        raise TypeError("executable_liquidity must be a finite Decimal")
    if not executable_liquidity.is_finite():
        raise ValueError("executable_liquidity must be a finite Decimal")

    if not isinstance(reference_quote_price, Decimal):
        raise TypeError("reference_quote_price must be a finite Decimal")
    if not reference_quote_price.is_finite():
        raise ValueError("reference_quote_price must be a finite Decimal")

    try:
        _decimal(requested_quantity, "requested_quantity", non_negative=True)
        _decimal(executable_liquidity, "executable_liquidity", non_negative=True)
        _decimal(reference_quote_price, "reference_quote_price", non_negative=True)

        _text(quantity_unit, "quantity_unit")
        _text(price_unit, "price_unit")
        _text(fee_unit, "fee_unit")

        quote_time = _utc(quote_observation_time, "quote_observation_time")
        simulated_time = _utc(fill_time, "fill_time")

        if quote_time > reference or simulated_time > reference:
            return _outcome(
                base,
                FillOutcomeStatus.REJECTED,
                ("FUTURE_TIMESTAMP",),
            )

        latency = _decimal(
            Decimal(
                str((simulated_time - quote_time).total_seconds())
            ),
            "latency_seconds",
            non_negative=False,
        )

        if latency < 0:
            invalid_base = dict(base)
            invalid_base["latency_seconds"] = None
            return _outcome(
                invalid_base,
                FillOutcomeStatus.INVALID,
                ("NEGATIVE_LATENCY",),
            )

        base["latency_seconds"] = latency

        if requested_quantity <= 0:
            return _outcome(
                base,
                FillOutcomeStatus.INVALID,
                ("INVALID_QUANTITY",),
            )

        if executable_liquidity < 0:
            return _outcome(
                base,
                FillOutcomeStatus.INVALID,
                ("INVALID_LIQUIDITY",),
            )

        if side_value is TradeSide.SELL:
            if available_inventory is None:
                return _outcome(
                    base,
                    FillOutcomeStatus.UNAVAILABLE,
                    ("INVENTORY_UNKNOWN",),
                )

            _decimal(
                available_inventory,
                "available_inventory",
                non_negative=True,
            )

            if available_inventory < requested_quantity:
                return _outcome(
                    base,
                    FillOutcomeStatus.REJECTED,
                    ("INSUFFICIENT_INVENTORY",),
                )

        if not isinstance(friction, FrictionComponents):
            return _outcome(
                base,
                FillOutcomeStatus.INVALID,
                ("INVALID_FRICTION",),
            )

        unknown = tuple(
            name
            for name in (
                "fees",
                "spread",
                "quote_drift",
                "slippage",
                "price_impact",
                "mev_adverse_ordering",
                "priority_fees",
            )
            if getattr(friction, name) is None
        )

        if unknown:
            return _outcome(
                base,
                FillOutcomeStatus.UNAVAILABLE,
                tuple(
                    f"UNKNOWN_FRICTION:{name}"
                    for name in unknown
                ),
            )

        sign = Decimal("1") if side_value is TradeSide.BUY else Decimal("-1")

        price = reference_quote_price

        for component in (
            friction.spread,
            friction.quote_drift,
            friction.slippage,
            friction.price_impact,
            friction.mev_adverse_ordering,
        ):
            price = _round(
                price + sign * component,
                "effective_price",
            )

        if price <= 0:
            return _outcome(
                base,
                FillOutcomeStatus.INVALID,
                ("NON_POSITIVE_EFFECTIVE_PRICE",),
            )

        if executable_liquidity == 0:
            return _outcome(
                base,
                FillOutcomeStatus.FAILED,
                ("NO_EXECUTABLE_LIQUIDITY",),
            )

        filled = _round(
            min(requested_quantity, executable_liquidity),
            "filled_quantity",
        )
        remaining = _round(
            requested_quantity - filled,
            "remaining_quantity",
        )

        status = (
            FillOutcomeStatus.FILLED
            if remaining == 0
            else FillOutcomeStatus.PARTIALLY_FILLED
        )

        return _outcome(
            {
                **base,
                "effective_price": price,
                "latency_seconds": latency,
                "filled_quantity": filled,
                "remaining_quantity": remaining,
            },
            status,
            (),
        )

    except (TypeError, ValueError, ArithmeticError):
        return _outcome(
            base,
            FillOutcomeStatus.INVALID,
            ("INVALID_INPUT",),
        )


simulate_paper_fill = evaluate_paper_fill


def _outcome(
    values: Mapping[str, Any],
    status: FillOutcomeStatus,
    reasons: tuple[str, ...],
    latency: Decimal | None = None,
) -> PaperFillOutcome:
    return PaperFillOutcome(
        **{
            **values,
            "status": status,
            "reason_codes": reasons,
            "latency_seconds": values.get(
                "latency_seconds",
                latency,
            ),
        }
    )


def _set_or_verify_outcome_digest(instance: PaperFillOutcome) -> None:
    expected = _digest(instance.canonical_representation)

    if (
        instance.outcome_digest is not None
        and instance.outcome_digest != expected
    ):
        raise ValueError(
            "outcome_digest does not match canonical representation"
        )

    object.__setattr__(instance, "outcome_digest", expected)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, Decimal):
        return _decimal_text(value)

    if isinstance(value, datetime):
        return _timestamp(value)

    if isinstance(value, StrEnum):
        return value.value

    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }

    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]

    raise ValueError(f"{type(value).__name__} is not canonical")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                key: _freeze(child)
                for key, child in value.items()
            }
        )

    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child) for child in value)

    return value


def _freeze_mapping(
    value: Mapping[str, Any],
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")

    return _freeze(_canonicalize(value))


def _decimal(
    value: Any,
    name: str,
    *,
    non_negative: bool,
) -> Decimal:
    if (
        isinstance(value, bool)
        or not isinstance(value, Decimal)
        or not value.is_finite()
    ):
        raise ValueError(
            f"{name} must be a finite Decimal"
        )

    if non_negative and value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )

    return value


def _round(value: Decimal, name: str) -> Decimal:
    _decimal(value, name, non_negative=False)
    return value.quantize(
        P07_T02_QUANT,
        rounding=ROUND_HALF_EVEN,
    )


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    rounded = _round(value, "decimal")
    return format(
        Decimal("0") if rounded == 0 else rounded.normalize(),
        "f",
    )


def _utc(value: Any, name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{name} must be timezone-aware"
        )

    return value.astimezone(timezone.utc)


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None

    return (
        _utc(value, "timestamp")
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _text(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(
            f"{name} must be canonical non-empty text"
        )


def _texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(
            f"{name} must be a tuple or list"
        )

    for item in value:
        _text(item, name)

    return tuple(sorted(dict.fromkeys(value)))


def _enum(
    value: Any,
    enum_type: type[StrEnum],
    name: str,
) -> None:
    try:
        enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"unsupported {name}"
        ) from error


def _digest_text(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"{name} must be a lowercase SHA-256 digest"
        )


__all__ = [
    "FillOutcomeStatus",
    "FrictionComponents",
    "P07_T02_CONTRACT_VERSION",
    "P07_T02_FILL_MODEL_VERSION",
    "P07_T02_FRICTION_MODEL_VERSION",
    "P07_T02_MAX_DECIMAL_PLACES",
    "P07_T02_ROUNDING_MODE",
    "PaperFillOutcome",
    "TradeSide",
    "evaluate_paper_fill",
    "simulate_paper_fill",
]
