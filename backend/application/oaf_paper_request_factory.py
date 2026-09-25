"""Server-side factory for exact OAF PFX/PFS/CIP preparation requests.

This boundary accepts only explicit, already-decoded canonical paper assumptions and
server-held RTI-11 output. It never accepts a client-authored RTI-11/P02/P03 object,
does not invent defaults, and performs no provider/runtime/persistence work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Any

from backend.application.market_to_opportunity_composition import P01Rti11CompositionResult
from backend.application.oaf_prepare_case import OafPrepareCaseRequest
from backend.application.paper_fact_sourcing import (
    GenesisPaperDeclaration,
    PaperFactSourcingRequest,
    PaperSimulationAssumptionPolicy,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01Pfx01Request,
    PaperRiskCapitalPolicySeed,
)
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from core.execution.paper_position_exposure_state import PaperPositionExposureState
from core.execution.paper_simulation_input import (
    ExecutionObservation,
    InitialPaperStateIdentity,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)


P01_OAF_PAPER_REQUEST_FACTORY_VERSION = "p01-oaf-01-paper-request-factory-v1"


class OafPaperRequestFactoryError(ValueError):
    """Fail-closed error while linking explicit paper inputs to exact RTI-11."""


@dataclass(frozen=True)
class OafExplicitPaperInputs:
    """Explicit paper-only assumptions/facts for one prepare invocation.

    All values are caller-decoded and canonical. This type owns no default
    thresholds, no clock reads, no source/provider facts and no economic/live
    semantics.
    """

    pfx_invocation_id: str
    cip_invocation_id: str
    decision_ruleset: DecisionEvaluationRuleset
    decision_time: datetime
    policy_seed: PaperRiskCapitalPolicySeed
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    replay_identity: ReplayIdentity
    simulation_reference_time: datetime
    paper_evaluation_time: datetime
    source_observation_id: str
    source_observation_fingerprint: str
    target_asset_identity: Mapping[str, Any]
    simulation_policy: PaperSimulationAssumptionPolicy
    genesis: GenesisPaperDeclaration | None
    prior_state: PaperPositionExposureState | None
    initial_state_identity: InitialPaperStateIdentity | None
    contract_version: str = P01_OAF_PAPER_REQUEST_FACTORY_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_PAPER_REQUEST_FACTORY_VERSION:
            raise OafPaperRequestFactoryError("unsupported paper-input contract")
        for name in ("pfx_invocation_id", "cip_invocation_id", "source_observation_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise OafPaperRequestFactoryError(f"{name} is required")
        if not isinstance(self.decision_ruleset, DecisionEvaluationRuleset):
            raise OafPaperRequestFactoryError("canonical decision_ruleset is required")
        if not isinstance(self.policy_seed, PaperRiskCapitalPolicySeed):
            raise OafPaperRequestFactoryError("canonical policy_seed is required")
        if not isinstance(self.execution_observation, ExecutionObservation):
            raise OafPaperRequestFactoryError("canonical execution_observation is required")
        if not isinstance(self.simulation_configuration, SimulationConfigurationIdentity):
            raise OafPaperRequestFactoryError("canonical simulation_configuration is required")
        if not isinstance(self.replay_identity, ReplayIdentity):
            raise OafPaperRequestFactoryError("canonical replay_identity is required")
        if not isinstance(self.simulation_policy, PaperSimulationAssumptionPolicy):
            raise OafPaperRequestFactoryError("canonical simulation_policy is required")
        if not isinstance(self.target_asset_identity, Mapping) or not self.target_asset_identity:
            raise OafPaperRequestFactoryError("target_asset_identity is required")
        for name in ("decision_time", "simulation_reference_time", "paper_evaluation_time"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise OafPaperRequestFactoryError(f"{name} must be timezone-aware")
        if (
            not isinstance(self.source_observation_fingerprint, str)
            or len(self.source_observation_fingerprint) != 64
            or any(c not in "0123456789abcdef" for c in self.source_observation_fingerprint)
        ):
            raise OafPaperRequestFactoryError(
                "source_observation_fingerprint must be SHA-256"
            )


class OafPaperRequestFactory:
    """Build exact PFX/PFS/CIP prepare request around one server-held RTI-11."""

    def build(
        self,
        rti11_result: P01Rti11CompositionResult,
        inputs: OafExplicitPaperInputs,
    ) -> OafPrepareCaseRequest:
        if not isinstance(rti11_result, P01Rti11CompositionResult):
            raise OafPaperRequestFactoryError("canonical RTI-11 result is required")
        if not isinstance(inputs, OafExplicitPaperInputs):
            raise OafPaperRequestFactoryError("explicit paper inputs are required")
        inputs.__post_init__()

        target = rti11_result.request.target
        if (
            inputs.target_asset_identity.get("chain_id") != target.chain_id
            or inputs.target_asset_identity.get("token_identity") != target.token_mint
        ):
            raise OafPaperRequestFactoryError("paper target does not match RTI-11 target")
        if inputs.decision_time < rti11_result.request.reference_time:
            raise OafPaperRequestFactoryError("decision_time precedes RTI-11 reference")

        try:
            pfx = P01Pfx01Request(
                invocation_id=inputs.pfx_invocation_id,
                rti11_result=rti11_result,
                decision_ruleset=inputs.decision_ruleset,
                decision_time=inputs.decision_time,
                policy_seed=inputs.policy_seed,
            )
            pfs = PaperFactSourcingRequest(
                rti11_result=rti11_result,
                execution_observation=inputs.execution_observation,
                simulation_configuration=inputs.simulation_configuration,
                replay_identity=inputs.replay_identity,
                simulation_reference_time=inputs.simulation_reference_time,
                paper_evaluation_time=inputs.paper_evaluation_time,
                source_observation_id=inputs.source_observation_id,
                source_observation_fingerprint=inputs.source_observation_fingerprint,
                target_asset_identity=inputs.target_asset_identity,
                policy=inputs.simulation_policy,
                genesis=inputs.genesis,
                prior_state=inputs.prior_state,
                initial_state_identity=inputs.initial_state_identity,
            )
            return OafPrepareCaseRequest(
                invocation_id=inputs.cip_invocation_id,
                rti11_result=rti11_result,
                pfx_request=pfx,
                pfs_request=pfs,
            )
        except OafPaperRequestFactoryError:
            raise
        except ValueError as exc:
            raise OafPaperRequestFactoryError(
                "explicit paper inputs failed canonical owner validation"
            ) from None


__all__ = [
    "OafExplicitPaperInputs",
    "OafPaperRequestFactory",
    "OafPaperRequestFactoryError",
    "P01_OAF_PAPER_REQUEST_FACTORY_VERSION",
]
