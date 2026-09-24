"""P01-CIP-01: prepare one exact OSC-02 request from existing paper results."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Callable, Mapping

from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalOutcome,
)
from backend.application.paper_fact_sourcing import (
    P07_PFS_01_CONTRACT_VERSION,
    PaperFactSourcingOutcome,
    PaperFactSourcingResult,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01_PFX_01_CONTRACT_VERSION,
    P01Pfx01Result,
    PrevalidatedPrefixOutcome,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    P01_OSC_02_CONTRACT_VERSION,
    P01Osc02Request,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY,
)


P01_CIP_01_CONTRACT_VERSION = "p01-cip-01-v1"


class ControlledInputPreparationOutcome(StrEnum):
    REQUEST_PREPARED = "REQUEST_PREPARED"
    PREFIX_NOT_ELIGIBLE = "PREFIX_NOT_ELIGIBLE"
    FACTS_NOT_MATERIALIZED = "FACTS_NOT_MATERIALIZED"
    PREPARATION_UNAVAILABLE = "PREPARATION_UNAVAILABLE"


def _canonical(value: Any, expected_type: type) -> bool:
    """Invoke existing immutable constructors for validation, without owner services."""
    if type(value) is not expected_type:
        return False
    try:
        _rebuild(value)
        return True
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _rebuild(value: Any) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _rebuild(getattr(value, field.name))
        if replace(value) != value:
            raise ValueError("noncanonical nested input")
    elif isinstance(value, tuple):
        for member in value:
            _rebuild(member)


def _digest(material: Mapping[str, Any]) -> str:
    def encode(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, Decimal):
            return format(Decimal("0") if value == 0 else value.normalize(), "f")
        if isinstance(value, StrEnum):
            return value.value
        if isinstance(value, Mapping):
            return {key: encode(value[key]) for key in sorted(value)}
        if isinstance(value, (tuple, list)):
            return [encode(item) for item in value]
        return value

    return hashlib.sha256(
        json.dumps(encode(material), sort_keys=True, separators=(",", ":"),
                   ensure_ascii=True).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class P01Cip01Request:
    invocation_id: str
    pfx_result: P01Pfx01Result
    pfs_result: PaperFactSourcingResult
    contract_version: str = P01_CIP_01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_CIP_01_CONTRACT_VERSION:
            raise ValueError("unsupported CIP-01 contract version")
        if type(self.invocation_id) is not str or not re.fullmatch(
            r"[A-Za-z0-9._:-]{1,128}", self.invocation_id
        ):
            raise ValueError("invalid OSC-02 invocation identity")
        if not _canonical(self.pfx_result, P01Pfx01Result):
            raise ValueError("noncanonical PFX-01 result")
        if not _canonical(self.pfs_result, PaperFactSourcingResult):
            raise ValueError("noncanonical PFS-01 result")
        if (
            self.pfx_result.contract_version != P01_PFX_01_CONTRACT_VERSION
            or self.pfs_result.contract_version != P07_PFS_01_CONTRACT_VERSION
        ):
            raise ValueError("unsupported upstream contract version")

        pfx = self.pfx_result
        rti11 = pfx.request.rti11_result
        if self.pfs_result.request.rti11_result is not rti11:
            raise ValueError("PFX/PFS RTI-11 identity mismatch")
        if pfx.rti12_result is not None and pfx.rti12_result.upstream_result is not rti11:
            raise ValueError("RTI-12 predecessor identity mismatch")
        if pfx.rti13_result is not None and (
            pfx.rti12_result is None
            or pfx.rti13_result.upstream_result is not pfx.rti12_result
        ):
            raise ValueError("RTI-13 predecessor identity mismatch")
        if pfx.rti14_result is not None and (
            pfx.rti13_result is None
            or pfx.rti14_result.upstream_result is not pfx.rti13_result
            or pfx.rti14_result.policy_snapshot is not pfx.policy_snapshot
        ):
            raise ValueError("RTI-14 predecessor identity mismatch")


def _compatible(request: P01Cip01Request) -> None:
    pfx, pfs = request.pfx_result, request.pfs_result
    rti11 = pfx.request.rti11_result
    decision = pfx.rti13_result.decision_intent
    authorization = pfx.rti14_result.authorization_result
    policy = pfx.policy_snapshot
    source_request = pfs.request
    initial = pfs.initial_state_identity
    fill = pfs.fill_instruction
    evidence = pfs.lifecycle_evidence
    if any(value is None for value in (decision, authorization, policy, initial, fill, evidence)):
        raise ValueError("incomplete canonical paper case")

    target = rti11.request.target
    subject = source_request.target_asset_identity
    stream = evidence.ledger_stream_identity
    if (
        decision.candidate_id != rti11.request.candidate_id
        or decision.chain_id != target.chain_id
        or decision.token_identity != target.token_mint
        or subject != source_request.execution_observation.subject_identity
        or subject != evidence.target_asset_identity
        or subject.get("chain_id") != target.chain_id
        or subject.get("token_identity") != target.token_mint
        or stream.get("candidate_id") != decision.candidate_id
        or stream.get("chain_id") != target.chain_id
        or stream.get("token_identity") != target.token_mint
        or stream.get("pool_address") != target.pool_address
        or stream.get("replay_id") != source_request.replay_identity.replay_id
        or stream.get("state_id") != initial.state_id
        or evidence.ledger_stream_identity != source_request.policy.ledger_stream_identity
    ):
        raise ValueError("paper subject, pool or stream identity mismatch")

    reference = source_request.simulation_reference_time
    if (
        policy.simulation_reference_time != reference
        or authorization.simulation_reference_time != reference
        or pfx.request.decision_time > reference
        or source_request.execution_observation.observation_time > reference
        or source_request.execution_observation.availability_time > reference
        or initial.as_of_time > reference
        or source_request.policy.simulated_fill_time > reference
        or source_request.paper_evaluation_time < reference
        or evidence.lifecycle_reference_time != source_request.paper_evaluation_time
        or evidence.accounting_context.observed_at > evidence.lifecycle_reference_time
    ):
        raise ValueError("paper reference or availability time mismatch")

    prior = evidence.prior_state
    scope = initial.portfolio_scope
    if (
        scope.get("paper_portfolio_id") != policy.scope_identity["paper_portfolio_id"]
        or initial.portfolio_scope != prior.portfolio_scope
        or initial.state_id != prior.state_id
        or initial.state_version != prior.state_version
        or initial.as_of_time != prior.as_of_time
        or initial.state_provenance.get("prior_state_digest") != prior.digest
        or evidence.sequence_number != source_request.policy.sequence_number
        or evidence.previous_entry_digest != source_request.policy.previous_entry_digest
        or evidence.reconciliation_expectation.replay_id != source_request.replay_identity.replay_id
    ):
        raise ValueError("paper portfolio, state or replay mismatch")

    source = [item for item in rti11.diagnostic.diagnostic.market.observations
              if item.observation_id == source_request.source_observation_id]
    if (
        len(source) != 1
        or source[0].fingerprint != source_request.source_observation_fingerprint
        or pfs.source_observation_digest != source[0].fingerprint
    ):
        raise ValueError("historical source identity mismatch")
    close = source[0].observation_time + timedelta(minutes=1)
    valuation = evidence.valuation_context.observations
    if (
        source[0].received_time < close
        or source[0].received_time > fill.fill_time
        or fill.fill_time > reference
        or fill.quote_observation_time != close
        or len(valuation) != 1
        or valuation[0].observation_id != source[0].observation_id
        or valuation[0].observed_at != close
        or valuation[0].availability_time != source[0].received_time
        or valuation[0].source_provenance.get("source_fingerprint") != source[0].fingerprint
        or valuation[0].source_provenance.get("pool_address") != target.pool_address
        or valuation[0].source_provenance.get("origin") != "observed_historical_USD_close_proxy"
        or fill.reference_quote_price != valuation[0].price
    ):
        raise ValueError("historical price proxy or availability mismatch")
    for provenance in (
        fill.friction.evidence,
        evidence.accounting_context.provenance,
        initial.state_provenance,
    ):
        if (
            provenance.get("policy_digest") != source_request.policy.digest
            or provenance.get("rti11_digest") != rti11.result_digest
            or provenance.get("replay_id") != source_request.replay_identity.replay_id
            or provenance.get("source_observation_fingerprint") != source[0].fingerprint
        ):
            raise ValueError("simulation assumption provenance mismatch")


@dataclass(frozen=True)
class P01Cip01Result:
    request: P01Cip01Request
    outcome: ControlledInputPreparationOutcome
    reason_codes: tuple[str, ...]
    terminal_stage: str
    osc02_request: P01Osc02Request | None = None
    contract_version: str = P01_CIP_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not P01Cip01Request:
            raise ValueError("invalid CIP-01 request")
        self.request.__post_init__()
        if self.contract_version != P01_CIP_01_CONTRACT_VERSION:
            raise ValueError("unsupported CIP-01 result contract")
        if type(self.outcome) is not ControlledInputPreparationOutcome:
            raise ValueError("unsupported CIP-01 outcome")
        expected = {
            ControlledInputPreparationOutcome.REQUEST_PREPARED: ("OSC-02", (), True),
            ControlledInputPreparationOutcome.PREFIX_NOT_ELIGIBLE:
                ("PFX-01", ("PREFIX_NOT_ELIGIBLE",), False),
            ControlledInputPreparationOutcome.FACTS_NOT_MATERIALIZED:
                ("PFS-01", ("FACTS_NOT_MATERIALIZED",), False),
            ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE:
                ("OSC-02", ("OSC_REQUEST_UNAVAILABLE",), False),
        }[self.outcome]
        if (
            self.terminal_stage != expected[0]
            or self.reason_codes != expected[1]
            or (self.osc02_request is not None) != expected[2]
        ):
            raise ValueError("invalid CIP-01 result shape")
        if self.osc02_request is not None:
            output = self.osc02_request
            pfx, pfs = self.request.pfx_result, self.request.pfs_result
            if (
                type(output) is not P01Osc02Request
                or output.contract_version != P01_OSC_02_CONTRACT_VERSION
                or output.invocation_id != self.request.invocation_id
                or output.rti14_result is not pfx.rti14_result
                or output.execution_observation is not pfs.request.execution_observation
                or output.simulation_configuration is not pfs.request.simulation_configuration
                or output.initial_paper_state is not pfs.initial_state_identity
                or output.replay_identity is not pfs.request.replay_identity
                or output.fill_instruction is not pfs.fill_instruction
                or output.lifecycle_evidence is not pfs.lifecycle_evidence
            ):
                raise ValueError("OSC-02 request does not preserve exact inputs")
        material = self._material()
        expected_digest = _digest(material)
        if self.result_digest is not None and self.result_digest != expected_digest:
            raise ValueError("CIP-01 result digest mismatch")
        object.__setattr__(self, "result_digest", expected_digest)

    def _material(self) -> Mapping[str, Any]:
        pfx, pfs = self.request.pfx_result, self.request.pfs_result
        authorization = pfx.rti14_result.authorization_result if pfx.rti14_result else None
        return {
            "contract_version": self.contract_version,
            "invocation_id": self.request.invocation_id,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "terminal_stage": self.terminal_stage,
            "pfx_contract": pfx.contract_version,
            "pfx_outcome": pfx.outcome.value,
            "pfx_digest": pfx.result_digest,
            "pfs_contract": pfs.contract_version,
            "pfs_outcome": pfs.outcome.value,
            "pfs_digest": pfs.result_digest,
            "rti11_digest": pfx.request.rti11_result.result_digest,
            "rti14_digest": pfx.rti14_result.digest if pfx.rti14_result else None,
            "authorization_digest": authorization.digest if authorization else None,
            "policy_digest": pfx.policy_snapshot.digest if pfx.policy_snapshot else None,
            "source_observation_id": pfs.request.source_observation_id,
            "source_observation_fingerprint": pfs.request.source_observation_fingerprint,
            "simulation_policy_digest": pfs.request.policy.digest,
            "execution_digest": pfs.request.execution_observation.observation_digest,
            "configuration_digest": pfs.request.simulation_configuration.configuration_digest,
            "initial_state_digest": pfs.initial_state_identity.state_digest if pfs.initial_state_identity else None,
            "replay_digest": _digest(pfs.request.replay_identity.canonical_representation),
            "fill_digest": pfs.fill_instruction.digest if pfs.fill_instruction else None,
            "lifecycle_digest": pfs.lifecycle_evidence.digest if pfs.lifecycle_evidence else None,
            "osc_contract": self.osc02_request.contract_version if self.osc02_request else None,
            "osc_input_digests": self.osc02_request.input_digests if self.osc02_request else None,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._material(), "result_digest": self.result_digest}


OscRequestFactory = Callable[..., P01Osc02Request]


class ControlledPaperExperimentInputPreparer:
    def __init__(self, *, request_factory: OscRequestFactory = P01Osc02Request) -> None:
        if not callable(request_factory):
            raise ValueError("invalid OSC-02 request constructor")
        self._request_factory = request_factory

    def prepare(self, request: P01Cip01Request) -> P01Cip01Result:
        if type(request) is not P01Cip01Request:
            raise ValueError("invalid CIP-01 request")
        request.__post_init__()
        pfx, pfs = request.pfx_result, request.pfs_result
        authorization = pfx.rti14_result.authorization_result if pfx.rti14_result else None
        if (
            pfx.outcome is not PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED
            or pfx.rti14_result.outcome is not DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
            or authorization is None
            or authorization.status is not AuthorizationStatus.APPROVED
            or authorization.authorization_effect != PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
        ):
            return P01Cip01Result(request, ControlledInputPreparationOutcome.PREFIX_NOT_ELIGIBLE,
                                  ("PREFIX_NOT_ELIGIBLE",), "PFX-01")
        if pfs.outcome is not PaperFactSourcingOutcome.FACTS_MATERIALIZED:
            return P01Cip01Result(request, ControlledInputPreparationOutcome.FACTS_NOT_MATERIALIZED,
                                  ("FACTS_NOT_MATERIALIZED",), "PFS-01")
        try:
            _compatible(request)
        except (AttributeError, KeyError, TypeError, ValueError, ArithmeticError):
            raise ValueError("CIP-01 compatibility validation failed") from None
        try:
            output = self._request_factory(
                invocation_id=request.invocation_id,
                rti14_result=pfx.rti14_result,
                execution_observation=pfs.request.execution_observation,
                simulation_configuration=pfs.request.simulation_configuration,
                initial_paper_state=pfs.initial_state_identity,
                replay_identity=pfs.request.replay_identity,
                fill_instruction=pfs.fill_instruction,
                lifecycle_evidence=pfs.lifecycle_evidence,
            )
        except ValueError:
            raise ValueError("OSC-02 request validation failed") from None
        except Exception:
            return P01Cip01Result(request, ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE,
                                  ("OSC_REQUEST_UNAVAILABLE",), "OSC-02")
        if type(output) is not P01Osc02Request:
            return P01Cip01Result(request, ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE,
                                  ("OSC_REQUEST_UNAVAILABLE",), "OSC-02")
        try:
            return P01Cip01Result(request, ControlledInputPreparationOutcome.REQUEST_PREPARED,
                                  (), "OSC-02", output)
        except ValueError:
            return P01Cip01Result(request, ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE,
                                  ("OSC_REQUEST_UNAVAILABLE",), "OSC-02")


__all__ = [
    "P01_CIP_01_CONTRACT_VERSION",
    "ControlledInputPreparationOutcome",
    "P01Cip01Request",
    "P01Cip01Result",
    "ControlledPaperExperimentInputPreparer",
]
