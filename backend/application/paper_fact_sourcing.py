"""P07-PFS-01: one deterministic, simulation-only source of paper *inputs*.

Historical USD closes are price proxies. Capacity, friction, inventory and
accounting remain explicit paper assumptions; no P07 outcome owner is called.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
    P01_RTI_11_CONTRACT_VERSION,
)
from core.data.coingecko_onchain_ohlcv import PROVIDER_ID
from core.data.contracts import DataQuality
from core.data.market_intelligence import MarketIntelligenceCategory
from core.execution.paper_fill_outcome import (
    FrictionComponents,
    P07_T02_FILL_MODEL_VERSION,
    P07_T02_FRICTION_MODEL_VERSION,
    TradeSide,
)
from core.execution.paper_position_exposure_state import (
    AccountingContext,
    PaperExposureAsset,
    PaperExposureState,
    PaperPositionExposureState,
    PaperPositionState,
    StateQuality,
    ValuationContext,
    ValuationObservation,
    ValuationStatus,
)
from core.execution.paper_reconciliation import PaperReconciliationExpectation
from core.execution.paper_simulation_input import (
    ExecutionObservation,
    InitialPaperStateIdentity,
    ObservationQuality,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.runtime.controlled_paper_lifecycle import PaperFillInstruction, PaperLifecycleEvidence


P07_PFS_01_CONTRACT_VERSION = "p07-pfs-01-v1"
POSITION_PROJECTION_VERSION = "p07-pfs-01-position-projection-v1"
EXPOSURE_PROJECTION_VERSION = "p07-pfs-01-exposure-projection-v1"
_FRICTION_KEYS = frozenset(("fees", "spread", "slippage", "price_impact", "quote_drift",
                            "priority_fees", "mev_adverse_ordering"))
_EXPECTATION_KEYS = frozenset(("sequence_number", "replay_id", "prior_state_digest",
                              "expected_ledger_reference_time", "expected_presence"))


class PaperFactSourcingOutcome(StrEnum):
    FACTS_MATERIALIZED = "FACTS_MATERIALIZED"
    UPSTREAM_NOT_COMPOSED = "UPSTREAM_NOT_COMPOSED"
    MARKET_EVIDENCE_UNAVAILABLE = "MARKET_EVIDENCE_UNAVAILABLE"
    CAPACITY_UNAVAILABLE = "CAPACITY_UNAVAILABLE"
    PRIOR_STATE_UNAVAILABLE = "PRIOR_STATE_UNAVAILABLE"
    EXPECTATION_UNAVAILABLE = "EXPECTATION_UNAVAILABLE"
    SOURCING_UNAVAILABLE = "SOURCING_UNAVAILABLE"


class PaperSimulationMode(StrEnum):
    FRESH_GENESIS = "FRESH_GENESIS"
    EXISTING_EXPLICIT_STATE = "EXISTING_EXPLICIT_STATE"


def _utc(value: datetime, name: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _text(value: str, name: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{name} must be canonical text")
    return value


def _number(value: Decimal, name: str, *, positive: bool = False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be a finite {'positive' if positive else 'nonnegative'} Decimal")
    if (value.as_tuple().exponent < -18 or abs(value.as_tuple().exponent) > 100 or
            len(value.as_tuple().digits) > 100):
        raise ValueError(f"{name} exceeds bounded exact paper precision")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child) for child in value)
    return value


def _encode(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _encode(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_encode(child) for child in value]
    if isinstance(value, datetime):
        return _utc(value, "canonical timestamp").isoformat(timespec="microseconds")
    if type(value) is Decimal:
        return format(value, "f")
    if isinstance(value, StrEnum):
        return value.value
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported canonical value")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_encode(value), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def _canonical(value: Any, expected: type) -> bool:
    if type(value) is not expected:
        return False
    try:
        def check(child: Any) -> None:
            if is_dataclass(child) and not isinstance(child, type):
                for field in fields(child):
                    check(getattr(child, field.name))
                if replace(child) != child:
                    raise ValueError("noncanonical owner")
            elif isinstance(child, (tuple, list)):
                for item in child:
                    check(item)
        check(value)
        return True
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _projection(state: PaperPositionExposureState) -> tuple[str, str]:
    return (
        _digest({"projection_version": POSITION_PROJECTION_VERSION,
                 "positions": tuple(item.canonical_representation for item in state.positions)}),
        _digest({"projection_version": EXPOSURE_PROJECTION_VERSION,
                 "exposure": state.exposure.canonical_representation}),
    )


@dataclass(frozen=True)
class GenesisPaperDeclaration:
    state_id: str
    state_version: str
    portfolio_scope: Mapping[str, Any]
    target_asset_identity: Mapping[str, Any]
    as_of_time: datetime
    zero_quantity: Decimal
    zero_cost_basis: Decimal
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        _text(self.state_id, "state_id")
        _text(self.state_version, "state_version")
        for name in ("portfolio_scope", "target_asset_identity", "provenance"):
            value = getattr(self, name)
            if not isinstance(value, Mapping) or not value:
                raise ValueError(f"{name} must be explicit")
            object.__setattr__(self, name, _freeze(value))
        object.__setattr__(self, "as_of_time", _utc(self.as_of_time, "genesis as_of_time"))
        if _number(self.zero_quantity, "zero_quantity") != 0 or _number(self.zero_cost_basis, "zero_cost_basis") != 0:
            raise ValueError("fresh genesis must explicitly declare zero position and cost")
        _digest(self.canonical_representation)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class PaperSimulationAssumptionPolicy:
    policy_id: str
    policy_version: str
    mode: PaperSimulationMode
    side: TradeSide
    requested_quantity: Decimal
    quantity_unit: str
    price_unit: str
    fee_unit: str
    quote_currency: str
    reference_price_rule: str
    quantity_rounding_rule: str
    simulated_fill_time: datetime
    simulated_capacity: Decimal | None
    allow_partial_fill: bool
    friction_values: Mapping[str, Decimal] | None
    valuation_max_age_seconds: Decimal
    accounting_fee: Decimal | None
    accounting_priority_fee: Decimal | None
    accounting_observed_at: datetime
    accounting_contract_version: str
    ledger_stream_identity: Mapping[str, Any]
    sequence_number: int
    previous_entry_digest: str | None
    expectation_id: str
    expectation_fields: tuple[str, ...] | None
    fill_model_version: str
    friction_model_version: str
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in ("policy_id", "policy_version", "quantity_unit", "price_unit", "fee_unit",
                     "quote_currency", "accounting_contract_version", "expectation_id"):
            _text(getattr(self, name), name)
        if type(self.mode) is not PaperSimulationMode or type(self.side) is not TradeSide:
            raise ValueError("explicit simulation mode and side required")
        if self.reference_price_rule != "OBSERVED_CLOSE_PROXY" or self.quantity_rounding_rule != "EXACT_DECIMAL_18":
            raise ValueError("unsupported explicit price or quantity rule")
        if (self.quote_currency != "USD" or self.fee_unit != "USD" or
                self.quantity_unit != "TOKEN" or self.price_unit != "USD_PER_TOKEN"):
            raise ValueError("historical USD proxy requires compatible USD units")
        if self.fill_model_version != P07_T02_FILL_MODEL_VERSION or self.friction_model_version != P07_T02_FRICTION_MODEL_VERSION:
            raise ValueError("unsupported canonical P07 fill/friction versions")
        _number(self.requested_quantity, "requested_quantity", positive=True)
        _number(self.valuation_max_age_seconds, "valuation_max_age_seconds", positive=True)
        object.__setattr__(self, "simulated_fill_time", _utc(self.simulated_fill_time, "simulated_fill_time"))
        object.__setattr__(self, "accounting_observed_at", _utc(self.accounting_observed_at, "accounting_observed_at"))
        if type(self.allow_partial_fill) is not bool:
            raise ValueError("allow_partial_fill must be explicit bool")
        if self.simulated_capacity is not None:
            _number(self.simulated_capacity, "simulated_capacity", positive=True)
        if self.friction_values is not None:
            if not isinstance(self.friction_values, Mapping) or set(self.friction_values) != _FRICTION_KEYS:
                raise ValueError("all seven friction assumptions are required")
            for key, value in self.friction_values.items():
                _number(value, key)
            object.__setattr__(self, "friction_values", _freeze(self.friction_values))
        for name in ("accounting_fee", "accounting_priority_fee"):
            value = getattr(self, name)
            if value is not None:
                _number(value, name)
        if not isinstance(self.ledger_stream_identity, Mapping) or not self.ledger_stream_identity:
            raise ValueError("explicit ledger stream identity required")
        object.__setattr__(self, "ledger_stream_identity", _freeze(self.ledger_stream_identity))
        if type(self.sequence_number) is not int or self.sequence_number <= 0:
            raise ValueError("positive explicit sequence required")
        if self.previous_entry_digest is not None and (type(self.previous_entry_digest) is not str or
                len(self.previous_entry_digest) != 64 or any(c not in "0123456789abcdef" for c in self.previous_entry_digest)):
            raise ValueError("invalid predecessor digest")
        if self.expectation_fields is not None:
            if type(self.expectation_fields) is not tuple or set(self.expectation_fields) != _EXPECTATION_KEYS or len(self.expectation_fields) != 5:
                raise ValueError("unsupported independent expectation fields")
            object.__setattr__(self, "expectation_fields", tuple(sorted(self.expectation_fields)))
        if not isinstance(self.provenance, Mapping) or not self.provenance:
            raise ValueError("explicit policy provenance required")
        object.__setattr__(self, "provenance", _freeze(self.provenance))
        _digest(self.canonical_representation)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @property
    def digest(self) -> str:
        return _digest(self.canonical_representation)


@dataclass(frozen=True)
class PaperFactSourcingRequest:
    rti11_result: P01Rti11CompositionResult
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    replay_identity: ReplayIdentity
    simulation_reference_time: datetime
    paper_evaluation_time: datetime
    source_observation_id: str
    source_observation_fingerprint: str
    target_asset_identity: Mapping[str, Any]
    policy: PaperSimulationAssumptionPolicy
    genesis: GenesisPaperDeclaration | None
    prior_state: PaperPositionExposureState | None
    initial_state_identity: InitialPaperStateIdentity | None
    contract_version: str = P07_PFS_01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P07_PFS_01_CONTRACT_VERSION:
            raise ValueError("unsupported PFS contract version")
        for name, expected in (("rti11_result", P01Rti11CompositionResult),
                               ("execution_observation", ExecutionObservation),
                               ("simulation_configuration", SimulationConfigurationIdentity),
                               ("replay_identity", ReplayIdentity),
                               ("policy", PaperSimulationAssumptionPolicy)):
            if not _canonical(getattr(self, name), expected):
                raise ValueError(f"noncanonical {name}")
        if self.rti11_result.contract_version != P01_RTI_11_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-11 contract version")
        _text(self.source_observation_id, "source_observation_id")
        if type(self.source_observation_fingerprint) is not str or len(self.source_observation_fingerprint) != 64 or any(
                c not in "0123456789abcdef" for c in self.source_observation_fingerprint):
            raise ValueError("source observation fingerprint must be SHA-256")
        for name in ("simulation_reference_time", "paper_evaluation_time"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if not isinstance(self.target_asset_identity, Mapping) or not self.target_asset_identity:
            raise ValueError("target_asset_identity required")
        object.__setattr__(self, "target_asset_identity", _freeze(self.target_asset_identity))
        for name, expected in (("genesis", GenesisPaperDeclaration),
                               ("prior_state", PaperPositionExposureState),
                               ("initial_state_identity", InitialPaperStateIdentity)):
            value = getattr(self, name)
            if value is not None and not _canonical(value, expected):
                raise ValueError(f"noncanonical {name}")
        if self.policy.mode is PaperSimulationMode.FRESH_GENESIS and (self.prior_state is not None or self.initial_state_identity is not None):
            raise ValueError("genesis cannot reuse historical prior state")
        if self.policy.mode is PaperSimulationMode.EXISTING_EXPLICIT_STATE and self.genesis is not None:
            raise ValueError("existing state cannot declare genesis")
        if self.rti11_result.outcome is MarketToOpportunityCompositionOutcome.COMPOSED:
            target = self.rti11_result.request.target
            if (self.target_asset_identity != self.execution_observation.subject_identity or
                    self.target_asset_identity.get("token_identity") != target.token_mint or
                    self.target_asset_identity.get("chain_id") != target.chain_id):
                raise ValueError("target asset / execution / RTI-11 identity mismatch")
        _digest(self.target_asset_identity)
        config = self.simulation_configuration
        if (config.fill_model_version != self.policy.fill_model_version or
                config.friction_model_version != self.policy.friction_model_version):
            raise ValueError("simulation configuration does not match simulation policy")

    @property
    def digest(self) -> str:
        return _digest({"contract_version": self.contract_version,
                        "rti11_contract": self.rti11_result.contract_version,
                        "rti11_outcome": self.rti11_result.outcome,
                        "rti11_digest": self.rti11_result.result_digest,
                        "execution": self.execution_observation.canonical_representation,
                        "configuration": self.simulation_configuration.canonical_representation,
                        "replay": self.replay_identity.canonical_representation,
                        "simulation_reference_time": self.simulation_reference_time,
                        "paper_evaluation_time": self.paper_evaluation_time,
                        "source_observation_id": self.source_observation_id,
                        "source_observation_fingerprint": self.source_observation_fingerprint,
                        "target_asset_identity": self.target_asset_identity,
                        "policy": self.policy.canonical_representation,
                        "genesis": self.genesis.canonical_representation if self.genesis else None,
                        "prior_state": self.prior_state.canonical_representation if self.prior_state else None,
                        "initial_state_identity": self.initial_state_identity.canonical_representation if self.initial_state_identity else None})


@dataclass(frozen=True)
class PaperFactSourcingResult:
    request: PaperFactSourcingRequest
    outcome: PaperFactSourcingOutcome
    reason_codes: tuple[str, ...]
    fill_instruction: PaperFillInstruction | None = None
    lifecycle_evidence: PaperLifecycleEvidence | None = None
    initial_state_identity: InitialPaperStateIdentity | None = None
    source_observation_digest: str | None = None
    contract_version: str = P07_PFS_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not PaperFactSourcingRequest or self.contract_version != P07_PFS_01_CONTRACT_VERSION:
            raise ValueError("invalid PFS result contract")
        if type(self.outcome) is not PaperFactSourcingOutcome or type(self.reason_codes) is not tuple or any(
                type(reason) is not str or not reason for reason in self.reason_codes):
            raise ValueError("invalid PFS result outcome/reasons")
        success = self.outcome is PaperFactSourcingOutcome.FACTS_MATERIALIZED
        if success != (self.fill_instruction is not None and self.lifecycle_evidence is not None and self.initial_state_identity is not None):
            raise ValueError("PFS result must contain all canonical products or none")
        if success and self.reason_codes or not success and (not self.reason_codes or any(
                value is not None for value in (self.fill_instruction, self.lifecycle_evidence, self.initial_state_identity))):
            raise ValueError("invalid PFS payload/reasons")
        if success and self.source_observation_digest != self.request.source_observation_fingerprint:
            raise ValueError("source observation digest mismatch")
        expected = _digest({"contract_version": self.contract_version, "outcome": self.outcome,
                            "reasons": self.reason_codes, "request_digest": self.request.digest,
                            "rti11_contract": self.request.rti11_result.contract_version,
                            "rti11_outcome": self.request.rti11_result.outcome,
                            "rti11_digest": self.request.rti11_result.result_digest,
                            "policy_digest": self.request.policy.digest,
                            "source_observation_digest": self.source_observation_digest,
                            "fill": self.fill_instruction.canonical_representation if self.fill_instruction else None,
                            "lifecycle": self.lifecycle_evidence.canonical_representation if self.lifecycle_evidence else None,
                            "initial_state": self.initial_state_identity.canonical_representation if self.initial_state_identity else None})
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("PFS result digest mismatch")
        object.__setattr__(self, "result_digest", expected)


def _refuse(request: PaperFactSourcingRequest, outcome: PaperFactSourcingOutcome, reason: str) -> PaperFactSourcingResult:
    return PaperFactSourcingResult(request, outcome, (reason,))


class PaperFactSourcingService:
    """Stateless, one-observation paper input construction with zero delegation."""

    def source(self, request: PaperFactSourcingRequest) -> PaperFactSourcingResult:
        if not _canonical(request, PaperFactSourcingRequest):
            raise ValueError("noncanonical PFS request")
        if request.rti11_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
            return _refuse(request, PaperFactSourcingOutcome.UPSTREAM_NOT_COMPOSED, "UPSTREAM_NOT_COMPOSED")
        return self._source_composed(request)

    @staticmethod
    def _source_composed(request: PaperFactSourcingRequest) -> PaperFactSourcingResult:
        policy = request.policy
        rti11 = request.rti11_result
        diagnostic = rti11.diagnostic
        assert diagnostic is not None and diagnostic.diagnostic is not None
        market = diagnostic.diagnostic.market
        selected = [observation for observation in market.observations
                    if observation.observation_id == request.source_observation_id]
        if not selected:
            return _refuse(request, PaperFactSourcingOutcome.MARKET_EVIDENCE_UNAVAILABLE, "SOURCE_OBSERVATION_MISSING")
        if len(selected) != 1 or selected[0].fingerprint != request.source_observation_fingerprint:
            raise ValueError("source observation identity/fingerprint mismatch")
        observation = selected[0]
        target = rti11.request.target
        if (observation.accepted is not True or observation.quality is not DataQuality.VALID or
                observation.intelligence_category is not MarketIntelligenceCategory.PRICE or
                observation.source_id != PROVIDER_ID or observation.chain_id != target.chain_id or
                observation.token_identity != target.token_mint or observation.market_subject_id != target.pool_address or
                observation.provenance.source_metadata.get("pool_address") != target.pool_address or
                observation.provenance.observation_metadata.get("unit") != "USD" or
                observation.provenance.observation_metadata.get("interval") != "60s" or
                market.provenance is None or observation.received_time != market.provenance.received_at):
            raise ValueError("source observation is not the exact admitted USD pool candle")
        close = observation.observation_time + timedelta(minutes=1)
        if (observation.observation_time.second != 0 or observation.observation_time.microsecond != 0 or
                observation.received_time < close or close > rti11.request.reference_time or
                observation.reference_time != rti11.request.reference_time):
            raise ValueError("invalid closed-minute source timing")
        try:
            price = Decimal(observation.value)
        except (TypeError, ValueError, ArithmeticError):
            raise ValueError("invalid historical price") from None
        _number(price, "historical USD close", positive=True)
        reference = request.simulation_reference_time
        evaluation = request.paper_evaluation_time
        fill_time = policy.simulated_fill_time
        if (reference < rti11.request.reference_time or evaluation < reference or fill_time > reference or
                observation.received_time > fill_time or observation.received_time > evaluation or
                request.execution_observation.availability_time > fill_time or
                policy.accounting_observed_at > evaluation or fill_time > evaluation):
            raise ValueError("future or contradictory paper/evidence timeline")
        age = evaluation - close
        age_seconds = Decimal(age.days * 86400 + age.seconds) + Decimal(age.microseconds) / Decimal("1000000")
        if age_seconds >= policy.valuation_max_age_seconds:
            return _refuse(request, PaperFactSourcingOutcome.MARKET_EVIDENCE_UNAVAILABLE, "STALE_HISTORICAL_PRICE")
        if policy.simulated_capacity is None:
            return _refuse(request, PaperFactSourcingOutcome.CAPACITY_UNAVAILABLE, "SIMULATED_CAPACITY_MISSING")
        if policy.simulated_capacity < policy.requested_quantity and not policy.allow_partial_fill:
            return _refuse(request, PaperFactSourcingOutcome.CAPACITY_UNAVAILABLE, "PARTIAL_CAPACITY_NOT_APPROVED")
        if policy.friction_values is None or policy.accounting_fee is None or policy.accounting_priority_fee is None:
            return _refuse(request, PaperFactSourcingOutcome.SOURCING_UNAVAILABLE, "SIMULATION_ASSUMPTIONS_MISSING")
        if (policy.accounting_fee != policy.friction_values["fees"] or
                policy.accounting_priority_fee != policy.friction_values["priority_fees"]):
            raise ValueError("accounting assumptions differ from friction assumptions")
        if policy.expectation_fields is None:
            return _refuse(request, PaperFactSourcingOutcome.EXPECTATION_UNAVAILABLE, "EXPECTATION_POLICY_MISSING")
        if policy.mode is PaperSimulationMode.FRESH_GENESIS:
            if request.genesis is None:
                return _refuse(request, PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE, "GENESIS_DECLARATION_MISSING")
            genesis = request.genesis
            if (genesis.target_asset_identity != request.target_asset_identity or
                    genesis.as_of_time > fill_time or policy.sequence_number != 1 or
                    policy.previous_entry_digest is not None):
                raise ValueError("invalid genesis asset, time or stream sequence")
        else:
            if request.prior_state is None or request.initial_state_identity is None:
                return _refuse(request, PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE, "EXPLICIT_PRIOR_STATE_MISSING")
            if policy.sequence_number == 1 or policy.previous_entry_digest is None:
                raise ValueError("existing prior stream cannot be reset to genesis")
        expected_stream = {
            "replay_id": request.replay_identity.replay_id,
            "state_id": request.genesis.state_id if request.genesis is not None else request.prior_state.state_id,
            "candidate_id": rti11.request.candidate_id,
            "chain_id": target.chain_id,
            "token_identity": target.token_mint,
            "pool_address": target.pool_address,
        }
        if (not isinstance(policy.ledger_stream_identity.get("stream_id"), str) or
                not policy.ledger_stream_identity["stream_id"] or any(
                    policy.ledger_stream_identity.get(key) != value for key, value in expected_stream.items())):
            raise ValueError("ledger stream is not bound to exact replay/state/candidate/pool")
        try:
            return PaperFactSourcingService._materialize(request, observation, close, price)
        except ValueError:
            raise
        except Exception:
            return _refuse(request, PaperFactSourcingOutcome.SOURCING_UNAVAILABLE, "CANONICAL_INPUT_UNAVAILABLE")

    @staticmethod
    def _materialize(request: PaperFactSourcingRequest, observation: Any, close: datetime,
                     price: Decimal) -> PaperFactSourcingResult:
        policy = request.policy
        asset = request.target_asset_identity
        provenance = {"origin": "explicit_simulation_assumption", "policy_id": policy.policy_id,
                      "policy_version": policy.policy_version, "policy_digest": policy.digest,
                      "replay_id": request.replay_identity.replay_id,
                      "rti11_digest": request.rti11_result.result_digest,
                      "source_observation_id": observation.observation_id,
                      "source_observation_fingerprint": observation.fingerprint}
        valuation = ValuationObservation(
            asset_identity=asset, observation_id=observation.observation_id, observed_at=close,
            availability_time=observation.received_time, price=price, price_unit=policy.price_unit,
            valuation_status=ValuationStatus.PASS,
            source_contract_version=observation.contract_version,
            source_provenance={"origin": "observed_historical_USD_close_proxy",
                               "source_observed_at": observation.observation_time.isoformat(),
                               "close_at": close.isoformat(), "received_at": observation.received_time.isoformat(),
                               "source_id": observation.source_id, "pool_address": request.rti11_result.request.target.pool_address,
                               "source_fingerprint": observation.fingerprint,
                               "response_digest": observation.provenance.source_metadata["response_digest"],
                               "price_proxy_policy": policy.policy_version},
            max_age_seconds=policy.valuation_max_age_seconds)
        if policy.mode is PaperSimulationMode.FRESH_GENESIS:
            assert request.genesis is not None
            genesis = request.genesis
            position = PaperPositionState(asset, policy.quantity_unit, genesis.zero_quantity, policy.fee_unit,
                                          genesis.zero_cost_basis, None, StateQuality.PASS,
                                          {**provenance, "genesis_declaration": _digest(genesis.canonical_representation)})
            exposure_asset = PaperExposureAsset(asset, genesis.zero_quantity, price, policy.price_unit,
                                                genesis.zero_quantity, close, ValuationStatus.PASS,
                                                valuation.observation_id, valuation.observation_digest)
            exposure = PaperExposureState(genesis.portfolio_scope, (exposure_asset,), genesis.zero_quantity,
                                          genesis.zero_quantity, ValuationStatus.PASS, provenance)
            prior = PaperPositionExposureState(genesis.state_id, genesis.state_version, genesis.portfolio_scope,
                                               (position,), exposure, genesis.as_of_time, StateQuality.PASS, provenance)
            position_digest, exposure_digest = _projection(prior)
            initial = InitialPaperStateIdentity(genesis.state_id, genesis.state_version, genesis.portfolio_scope,
                                                position_digest, exposure_digest, genesis.as_of_time,
                                                ObservationQuality.PASS,
                                                {**provenance, "prior_state_digest": prior.digest,
                                                 "position_projection_version": POSITION_PROJECTION_VERSION,
                                                 "exposure_projection_version": EXPOSURE_PROJECTION_VERSION})
        else:
            assert request.prior_state is not None and request.initial_state_identity is not None
            prior = request.prior_state
            initial = request.initial_state_identity
            position_digest, exposure_digest = _projection(prior)
            if (prior.state_id != initial.state_id or prior.state_version != initial.state_version or
                    prior.portfolio_scope != initial.portfolio_scope or prior.as_of_time != initial.as_of_time or
                    position_digest != initial.position_state_digest or exposure_digest != initial.exposure_state_digest or
                    initial.state_provenance.get("prior_state_digest") != prior.digest or
                    prior.state_quality is not StateQuality.PASS or initial.state_quality is not ObservationQuality.PASS or
                    prior.as_of_time > policy.simulated_fill_time):
                raise ValueError("existing prior state projection/identity mismatch")
        positions = [p for p in prior.positions if p.asset_identity == asset]
        if len(positions) != 1 or positions[0].quantity_unit != policy.quantity_unit or positions[0].cost_basis_unit != policy.fee_unit:
            raise ValueError("prior target position/units mismatch")
        position = positions[0]
        if policy.side is TradeSide.SELL and (position.position_quality is not StateQuality.PASS or
                position.quantity < policy.requested_quantity):
            return _refuse(request, PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE, "SELL_INVENTORY_UNAVAILABLE")
        if policy.mode is PaperSimulationMode.EXISTING_EXPLICIT_STATE and any(
                item.asset_identity != asset for item in prior.positions):
            return _refuse(request, PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE, "ADDITIONAL_VALUATION_UNAVAILABLE")
        friction = FrictionComponents(**policy.friction_values, evidence=provenance)
        fill = PaperFillInstruction(policy.side, policy.requested_quantity, policy.quantity_unit,
                                    policy.price_unit, policy.fee_unit, policy.quote_currency,
                                    policy.simulated_capacity, price, close, policy.simulated_fill_time,
                                    friction, position.quantity if policy.side is TradeSide.SELL else None)
        accounting = AccountingContext(policy.accounting_fee, policy.accounting_priority_fee, policy.fee_unit,
                                       policy.policy_id + ":accounting", policy.accounting_contract_version,
                                       provenance, policy.accounting_observed_at, policy.accounting_observed_at)
        comparison = {"sequence_number": policy.sequence_number,
                      "replay_id": request.replay_identity.replay_id,
                      "prior_state_digest": prior.digest,
                      "expected_ledger_reference_time": request.paper_evaluation_time,
                      "expected_presence": True}
        assert set(policy.expectation_fields) == set(comparison)
        expectation = PaperReconciliationExpectation(policy.expectation_id, request.replay_identity.replay_id,
                                                    {key: comparison[key] for key in policy.expectation_fields},
                                                    request.paper_evaluation_time)
        evidence = PaperLifecycleEvidence(prior, asset, ValuationContext((valuation,)), accounting,
                                          request.paper_evaluation_time, policy.ledger_stream_identity,
                                          policy.sequence_number, policy.previous_entry_digest, expectation)
        return PaperFactSourcingResult(request, PaperFactSourcingOutcome.FACTS_MATERIALIZED, (), fill,
                                       evidence, initial, observation.fingerprint)


__all__ = ["P07_PFS_01_CONTRACT_VERSION", "PaperSimulationMode", "PaperSimulationAssumptionPolicy",
           "GenesisPaperDeclaration", "PaperFactSourcingOutcome", "PaperFactSourcingRequest",
           "PaperFactSourcingResult", "PaperFactSourcingService"]
