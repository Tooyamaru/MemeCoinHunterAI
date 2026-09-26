"""Transport DTO and decoder for authenticated OAF POST prepare.

Only explicit controller-owned values cross this boundary. Internal canonical
P02/P03/RTI-11 objects and server-generated observation digests are never
accepted from the browser.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from backend.application.oaf_operator_paper_intent import OafOperatorPaperIntent
from backend.application.oaf_operator_prepare_invocation import OafOperatorPrepareInvocation
from backend.application.paper_fact_sourcing import (
    GenesisPaperDeclaration,
    PaperSimulationAssumptionPolicy,
    PaperSimulationMode,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    PaperRiskCapitalPolicySeed,
)
from backend.application.oaf_trusted_prepare import OafTrustedPrepareCommand
from core.data.coingecko_onchain_orchestration import ExactPoolDiagnosticTarget
from core.data.contracts import FreshnessPolicy
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from core.execution.paper_fill_outcome import TradeSide
from core.execution.paper_simulation_input import (
    ExecutionObservation,
    ObservationQuality,
    ObservationStatus,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.risk.paper_risk_capital_authorization import (
    PaperCapitalState,
    PaperExposureState,
    RiskState,
    RiskStateStatus,
)


class OperatorPrepareDecodeError(ValueError):
    pass


class ExactPoolTargetDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chain_id: str
    token_mint: str
    pool_address: str
    base_mint: str
    quote_mint: str
    target_reference_id: str
    target_reference_digest: str
    target_contract_version: str


class OperatorPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    token_mint: str
    target: ExactPoolTargetDto
    processing_time: datetime
    reference_time: datetime
    evaluation_time: datetime
    freshness_seconds: int = Field(gt=0, le=86400)
    max_top_holder_fraction: float = Field(ge=0, le=1)
    rti11_timeout_seconds: float = Field(gt=0, le=60)
    rti11_max_response_bytes: int = Field(ge=1, le=1_048_576)
    evaluation_id: str
    paper_intent: dict[str, Any]


class OperatorPrepareResponse(BaseModel):
    contract_version: str
    handle: str
    case_digest: str
    state: str
    candidate_id: str
    chain_id: str
    token_mint: str
    pool_address: str
    eligibility: str
    pfx_outcome: str
    pfs_outcome: str
    cip_outcome: str
    cip_digest: str
    review_path: str
    simulation_only: bool = True


def decode_operator_prepare_request(
    payload: OperatorPrepareRequest,
) -> OafOperatorPrepareInvocation:
    try:
        target = ExactPoolDiagnosticTarget(**payload.target.model_dump())
        command = OafTrustedPrepareCommand(
            candidate_id=_text(payload.candidate_id, "candidate_id"),
            token_mint=_text(payload.token_mint, "token_mint"),
            target=target,
            processing_time=_dt(payload.processing_time, "processing_time"),
            reference_time=_dt(payload.reference_time, "reference_time"),
            evaluation_time=_dt(payload.evaluation_time, "evaluation_time"),
            freshness_policy=FreshnessPolicy(
                stale_after=timedelta(seconds=payload.freshness_seconds)
            ),
            max_top_holder_fraction=payload.max_top_holder_fraction,
            rti11_timeout=timedelta(seconds=payload.rti11_timeout_seconds),
            rti11_max_response_bytes=payload.rti11_max_response_bytes,
            evaluation_id=_text(payload.evaluation_id, "evaluation_id"),
        )
        intent = _paper_intent(payload.paper_intent)
        return OafOperatorPrepareInvocation(command, intent)
    except OperatorPrepareDecodeError:
        raise
    except (TypeError, ValueError, KeyError, InvalidOperation, OverflowError):
        raise OperatorPrepareDecodeError(
            "operator prepare payload failed canonical validation"
        ) from None


def _paper_intent(raw: Mapping[str, Any]) -> OafOperatorPaperIntent:
    value = _object(
        raw,
        {
            "pfx_invocation_id",
            "cip_invocation_id",
            "decision_ruleset",
            "decision_time",
            "policy_seed",
            "execution_observation",
            "simulation_configuration",
            "replay_identity",
            "simulation_reference_time",
            "paper_evaluation_time",
            "selected_observation_time",
            "target_asset_identity",
            "simulation_policy",
            "genesis",
        },
        "paper_intent",
    )
    return OafOperatorPaperIntent(
        pfx_invocation_id=_text(value["pfx_invocation_id"], "pfx_invocation_id"),
        cip_invocation_id=_text(value["cip_invocation_id"], "cip_invocation_id"),
        decision_ruleset=_decision_ruleset(value["decision_ruleset"]),
        decision_time=_dt(value["decision_time"], "decision_time"),
        policy_seed=_policy_seed(value["policy_seed"]),
        execution_observation=_execution_observation(value["execution_observation"]),
        simulation_configuration=_simulation_configuration(
            value["simulation_configuration"]
        ),
        replay_identity=_replay_identity(value["replay_identity"]),
        simulation_reference_time=_dt(
            value["simulation_reference_time"], "simulation_reference_time"
        ),
        paper_evaluation_time=_dt(
            value["paper_evaluation_time"], "paper_evaluation_time"
        ),
        selected_observation_time=_dt(
            value["selected_observation_time"], "selected_observation_time"
        ),
        target_asset_identity=_mapping(
            value["target_asset_identity"], "target_asset_identity"
        ),
        simulation_policy=_simulation_policy(value["simulation_policy"]),
        genesis=_genesis(value["genesis"]),
    )


def _decision_ruleset(raw: Mapping[str, Any]) -> DecisionEvaluationRuleset:
    value = _object(
        raw,
        {
            "buy_score_threshold",
            "watch_score_threshold",
            "max_evidence_age_seconds",
            "version",
        },
        "decision_ruleset",
    )
    return DecisionEvaluationRuleset(
        buy_score_threshold=_decimal(
            value["buy_score_threshold"], "buy_score_threshold"
        ),
        watch_score_threshold=_decimal(
            value["watch_score_threshold"], "watch_score_threshold"
        ),
        max_evidence_age_seconds=_integer(
            value["max_evidence_age_seconds"], "max_evidence_age_seconds"
        ),
        version=_text(value["version"], "decision_ruleset.version"),
    )


def _policy_seed(raw: Mapping[str, Any]) -> PaperRiskCapitalPolicySeed:
    value = _object(
        raw,
        {
            "policy_snapshot_id",
            "risk_governor_version",
            "capital_authorization_version",
            "evaluator_version",
            "paper_lifecycle_id",
            "paper_portfolio_id",
            "simulation_reference_time",
            "policy_cutoff_time",
            "risk_state_max_age_seconds",
            "paper_capital_state_max_age_seconds",
            "paper_exposure_state_max_age_seconds",
            "valid_from",
            "valid_until",
            "risk_state",
            "paper_capital_state",
            "paper_exposure_state",
            "provenance_source",
        },
        "policy_seed",
    )
    return PaperRiskCapitalPolicySeed(
        policy_snapshot_id=_text(value["policy_snapshot_id"], "policy_snapshot_id"),
        risk_governor_version=_text(
            value["risk_governor_version"], "risk_governor_version"
        ),
        capital_authorization_version=_text(
            value["capital_authorization_version"], "capital_authorization_version"
        ),
        evaluator_version=_text(value["evaluator_version"], "evaluator_version"),
        paper_lifecycle_id=_text(
            value["paper_lifecycle_id"], "paper_lifecycle_id"
        ),
        paper_portfolio_id=_text(
            value["paper_portfolio_id"], "paper_portfolio_id"
        ),
        simulation_reference_time=_dt(
            value["simulation_reference_time"], "policy simulation_reference_time"
        ),
        policy_cutoff_time=_dt(value["policy_cutoff_time"], "policy_cutoff_time"),
        risk_state_max_age_seconds=_decimal(
            value["risk_state_max_age_seconds"], "risk_state_max_age_seconds"
        ),
        paper_capital_state_max_age_seconds=_decimal(
            value["paper_capital_state_max_age_seconds"],
            "paper_capital_state_max_age_seconds",
        ),
        paper_exposure_state_max_age_seconds=_decimal(
            value["paper_exposure_state_max_age_seconds"],
            "paper_exposure_state_max_age_seconds",
        ),
        valid_from=_dt(value["valid_from"], "valid_from"),
        valid_until=_dt(value["valid_until"], "valid_until"),
        risk_state=_risk_state(value["risk_state"]),
        paper_capital_state=_capital_state(value["paper_capital_state"]),
        paper_exposure_state=_exposure_state(value["paper_exposure_state"]),
        provenance_source=(
            None
            if value["provenance_source"] is None
            else _text(value["provenance_source"], "provenance_source")
        ),
    )


def _risk_state(raw: Mapping[str, Any]) -> RiskState:
    value = _object(
        raw,
        {"status", "emergency_stop", "risk_flags", "as_of_time", "available_at"},
        "risk_state",
    )
    flags = value["risk_flags"]
    if not isinstance(flags, list) or any(not isinstance(x, str) for x in flags):
        raise OperatorPrepareDecodeError("risk_flags must be a string list")
    return RiskState(
        status=RiskStateStatus(value["status"]),
        emergency_stop=_boolean(value["emergency_stop"], "emergency_stop"),
        risk_flags=tuple(flags),
        as_of_time=_dt(value["as_of_time"], "risk_state.as_of_time"),
        available_at=_dt(value["available_at"], "risk_state.available_at"),
    )


def _capital_state(raw: Mapping[str, Any]) -> PaperCapitalState:
    value = _object(
        raw,
        {
            "unit",
            "budget_total",
            "committed_before",
            "requested_entry",
            "max_single_entry",
            "as_of_time",
            "available_at",
        },
        "paper_capital_state",
    )
    return PaperCapitalState(
        unit=_text(value["unit"], "paper_capital_state.unit"),
        budget_total=_decimal(value["budget_total"], "budget_total"),
        committed_before=_decimal(value["committed_before"], "committed_before"),
        requested_entry=_decimal(value["requested_entry"], "requested_entry"),
        max_single_entry=_decimal(value["max_single_entry"], "max_single_entry"),
        as_of_time=_dt(value["as_of_time"], "paper_capital_state.as_of_time"),
        available_at=_dt(
            value["available_at"], "paper_capital_state.available_at"
        ),
    )


def _exposure_state(raw: Mapping[str, Any]) -> PaperExposureState:
    value = _object(
        raw,
        {
            "unit",
            "exposure_before",
            "max_total_exposure",
            "as_of_time",
            "available_at",
        },
        "paper_exposure_state",
    )
    return PaperExposureState(
        unit=_text(value["unit"], "paper_exposure_state.unit"),
        exposure_before=_decimal(value["exposure_before"], "exposure_before"),
        max_total_exposure=_decimal(
            value["max_total_exposure"], "max_total_exposure"
        ),
        as_of_time=_dt(value["as_of_time"], "paper_exposure_state.as_of_time"),
        available_at=_dt(
            value["available_at"], "paper_exposure_state.available_at"
        ),
    )


def _execution_observation(raw: Mapping[str, Any]) -> ExecutionObservation:
    value = _object(
        raw,
        {
            "observation_id",
            "subject_identity",
            "observation_time",
            "availability_time",
            "quality",
            "market_context_digest",
            "quote_context_digest",
            "liquidity_context_digest",
            "sellability_status",
            "source_contract_version",
            "source_provenance",
            "observation_replay_key",
        },
        "execution_observation",
    )
    return ExecutionObservation(
        observation_id=_text(value["observation_id"], "observation_id"),
        subject_identity=_mapping(value["subject_identity"], "subject_identity"),
        observation_time=_dt(value["observation_time"], "observation_time"),
        availability_time=_dt(value["availability_time"], "availability_time"),
        quality=ObservationQuality(value["quality"]),
        market_context_digest=_optional_digest(
            value["market_context_digest"], "market_context_digest"
        ),
        quote_context_digest=_optional_digest(
            value["quote_context_digest"], "quote_context_digest"
        ),
        liquidity_context_digest=_optional_digest(
            value["liquidity_context_digest"], "liquidity_context_digest"
        ),
        sellability_status=ObservationStatus(value["sellability_status"]),
        source_contract_version=_text(
            value["source_contract_version"], "source_contract_version"
        ),
        source_provenance=_mapping(
            value["source_provenance"], "source_provenance"
        ),
        observation_replay_key=_text(
            value["observation_replay_key"], "observation_replay_key"
        ),
    )


def _simulation_configuration(
    raw: Mapping[str, Any],
) -> SimulationConfigurationIdentity:
    value = _object(
        raw,
        {
            "configuration_id",
            "contract_version",
            "simulation_version",
            "fill_model_version",
            "friction_model_version",
            "failure_policy_version",
            "seed_policy_version",
            "configuration_provenance",
        },
        "simulation_configuration",
    )
    return SimulationConfigurationIdentity(
        configuration_id=_text(value["configuration_id"], "configuration_id"),
        contract_version=_text(value["contract_version"], "configuration contract"),
        simulation_version=_text(value["simulation_version"], "simulation_version"),
        fill_model_version=_text(value["fill_model_version"], "fill_model_version"),
        friction_model_version=_text(
            value["friction_model_version"], "friction_model_version"
        ),
        failure_policy_version=_text(
            value["failure_policy_version"], "failure_policy_version"
        ),
        seed_policy_version=_text(
            value["seed_policy_version"], "seed_policy_version"
        ),
        configuration_provenance=_mapping(
            value["configuration_provenance"], "configuration_provenance"
        ),
    )


def _replay_identity(raw: Mapping[str, Any]) -> ReplayIdentity:
    value = _object(
        raw,
        {
            "replay_id",
            "replay_schema_version",
            "replay_seed_identity",
            "parent_replay_id",
            "replay_scope",
        },
        "replay_identity",
    )
    parent = value["parent_replay_id"]
    return ReplayIdentity(
        replay_id=_text(value["replay_id"], "replay_id"),
        replay_schema_version=_text(
            value["replay_schema_version"], "replay_schema_version"
        ),
        replay_seed_identity=_text(
            value["replay_seed_identity"], "replay_seed_identity"
        ),
        parent_replay_id=(
            None if parent is None else _text(parent, "parent_replay_id")
        ),
        replay_scope=_mapping(value["replay_scope"], "replay_scope"),
    )


def _simulation_policy(raw: Mapping[str, Any]) -> PaperSimulationAssumptionPolicy:
    value = _object(
        raw,
        {
            "policy_id",
            "policy_version",
            "mode",
            "side",
            "requested_quantity",
            "quantity_unit",
            "price_unit",
            "fee_unit",
            "quote_currency",
            "reference_price_rule",
            "quantity_rounding_rule",
            "simulated_fill_time",
            "simulated_capacity",
            "allow_partial_fill",
            "friction_values",
            "valuation_max_age_seconds",
            "accounting_fee",
            "accounting_priority_fee",
            "accounting_observed_at",
            "accounting_contract_version",
            "ledger_stream_identity",
            "sequence_number",
            "previous_entry_digest",
            "expectation_id",
            "expectation_fields",
            "fill_model_version",
            "friction_model_version",
            "provenance",
        },
        "simulation_policy",
    )
    if PaperSimulationMode(value["mode"]) is not PaperSimulationMode.FRESH_GENESIS:
        raise OperatorPrepareDecodeError("first POST prepare supports FRESH_GENESIS only")
    friction_raw = value["friction_values"]
    friction = None
    if friction_raw is not None:
        friction_mapping = _mapping(friction_raw, "friction_values")
        friction = {
            key: _decimal(item, f"friction_values.{key}")
            for key, item in friction_mapping.items()
        }
    fields = value["expectation_fields"]
    if fields is not None and (
        not isinstance(fields, list) or any(not isinstance(x, str) for x in fields)
    ):
        raise OperatorPrepareDecodeError("expectation_fields must be a string list")
    return PaperSimulationAssumptionPolicy(
        policy_id=_text(value["policy_id"], "policy_id"),
        policy_version=_text(value["policy_version"], "policy_version"),
        mode=PaperSimulationMode.FRESH_GENESIS,
        side=TradeSide(value["side"]),
        requested_quantity=_decimal(
            value["requested_quantity"], "requested_quantity"
        ),
        quantity_unit=_text(value["quantity_unit"], "quantity_unit"),
        price_unit=_text(value["price_unit"], "price_unit"),
        fee_unit=_text(value["fee_unit"], "fee_unit"),
        quote_currency=_text(value["quote_currency"], "quote_currency"),
        reference_price_rule=_text(
            value["reference_price_rule"], "reference_price_rule"
        ),
        quantity_rounding_rule=_text(
            value["quantity_rounding_rule"], "quantity_rounding_rule"
        ),
        simulated_fill_time=_dt(
            value["simulated_fill_time"], "simulated_fill_time"
        ),
        simulated_capacity=(
            None
            if value["simulated_capacity"] is None
            else _decimal(value["simulated_capacity"], "simulated_capacity")
        ),
        allow_partial_fill=_boolean(
            value["allow_partial_fill"], "allow_partial_fill"
        ),
        friction_values=friction,
        valuation_max_age_seconds=_decimal(
            value["valuation_max_age_seconds"], "valuation_max_age_seconds"
        ),
        accounting_fee=(
            None
            if value["accounting_fee"] is None
            else _decimal(value["accounting_fee"], "accounting_fee")
        ),
        accounting_priority_fee=(
            None
            if value["accounting_priority_fee"] is None
            else _decimal(
                value["accounting_priority_fee"], "accounting_priority_fee"
            )
        ),
        accounting_observed_at=_dt(
            value["accounting_observed_at"], "accounting_observed_at"
        ),
        accounting_contract_version=_text(
            value["accounting_contract_version"], "accounting_contract_version"
        ),
        ledger_stream_identity=_mapping(
            value["ledger_stream_identity"], "ledger_stream_identity"
        ),
        sequence_number=_integer(value["sequence_number"], "sequence_number"),
        previous_entry_digest=_optional_digest(
            value["previous_entry_digest"], "previous_entry_digest"
        ),
        expectation_id=_text(value["expectation_id"], "expectation_id"),
        expectation_fields=None if fields is None else tuple(fields),
        fill_model_version=_text(
            value["fill_model_version"], "fill_model_version"
        ),
        friction_model_version=_text(
            value["friction_model_version"], "friction_model_version"
        ),
        provenance=_mapping(value["provenance"], "simulation policy provenance"),
    )


def _genesis(raw: Mapping[str, Any]) -> GenesisPaperDeclaration:
    value = _object(
        raw,
        {
            "state_id",
            "state_version",
            "portfolio_scope",
            "target_asset_identity",
            "as_of_time",
            "zero_quantity",
            "zero_cost_basis",
            "provenance",
        },
        "genesis",
    )
    return GenesisPaperDeclaration(
        state_id=_text(value["state_id"], "genesis.state_id"),
        state_version=_text(value["state_version"], "genesis.state_version"),
        portfolio_scope=_mapping(value["portfolio_scope"], "portfolio_scope"),
        target_asset_identity=_mapping(
            value["target_asset_identity"], "genesis.target_asset_identity"
        ),
        as_of_time=_dt(value["as_of_time"], "genesis.as_of_time"),
        zero_quantity=_decimal(value["zero_quantity"], "zero_quantity"),
        zero_cost_basis=_decimal(value["zero_cost_basis"], "zero_cost_basis"),
        provenance=_mapping(value["provenance"], "genesis.provenance"),
    )


def _object(raw: Any, keys: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise OperatorPrepareDecodeError(f"{name} must be an object")
    actual = set(raw)
    if actual != keys:
        raise OperatorPrepareDecodeError(
            f"{name} fields mismatch: expected explicit bounded schema"
        )
    return raw


def _mapping(raw: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or not raw:
        raise OperatorPrepareDecodeError(f"{name} must be a non-empty object")
    if any(not isinstance(key, str) for key in raw):
        raise OperatorPrepareDecodeError(f"{name} keys must be strings")
    return dict(raw)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise OperatorPrepareDecodeError(f"{name} must be canonical text")
    return value


def _dt(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise OperatorPrepareDecodeError(f"{name} must be RFC3339") from None
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise OperatorPrepareDecodeError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise OperatorPrepareDecodeError(f"{name} must be exact decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise OperatorPrepareDecodeError(f"{name} must be exact decimal text") from None
    if not result.is_finite():
        raise OperatorPrepareDecodeError(f"{name} must be finite")
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OperatorPrepareDecodeError(f"{name} must be an integer")
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise OperatorPrepareDecodeError(f"{name} must be boolean")
    return value


def _optional_digest(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise OperatorPrepareDecodeError(f"{name} must be SHA-256 or null")
    return value


__all__ = [
    "ExactPoolTargetDto",
    "OperatorPrepareDecodeError",
    "OperatorPrepareRequest",
    "OperatorPrepareResponse",
    "decode_operator_prepare_request",
]
