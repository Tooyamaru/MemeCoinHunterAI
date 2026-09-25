"""Operator-facing paper intent builder for one trusted OAF prepare.

The operator selects one historical observation by its exact source candle time.
After RTI-11 has produced canonical observations server-side, this builder binds
that selector to exactly one admitted observation and constructs the canonical
paper-input bundle. Browser input never supplies an internal observation digest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from backend.application.oaf_paper_request_factory import OafExplicitPaperInputs
from backend.application.paper_fact_sourcing import (
    GenesisPaperDeclaration,
    PaperSimulationAssumptionPolicy,
    PaperSimulationMode,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    PaperRiskCapitalPolicySeed,
)
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from core.execution.paper_simulation_input import (
    ExecutionObservation,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)


P01_OAF_OPERATOR_PAPER_INTENT_VERSION = "p01-oaf-01-operator-paper-intent-v1"


class OafOperatorPaperIntentError(ValueError):
    """Fail-closed operator paper-intent linkage error."""


@dataclass(frozen=True)
class OafOperatorPaperIntent:
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
    selected_observation_time: datetime
    target_asset_identity: Mapping[str, Any]
    simulation_policy: PaperSimulationAssumptionPolicy
    genesis: GenesisPaperDeclaration
    contract_version: str = P01_OAF_OPERATOR_PAPER_INTENT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_OPERATOR_PAPER_INTENT_VERSION:
            raise OafOperatorPaperIntentError("unsupported operator paper-intent contract")
        for name in ("pfx_invocation_id", "cip_invocation_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise OafOperatorPaperIntentError(f"{name} is required")
        for name in (
            "decision_time",
            "simulation_reference_time",
            "paper_evaluation_time",
            "selected_observation_time",
        ):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise OafOperatorPaperIntentError(f"{name} must be timezone-aware")
        if not isinstance(self.decision_ruleset, DecisionEvaluationRuleset):
            raise OafOperatorPaperIntentError("canonical decision_ruleset is required")
        if not isinstance(self.policy_seed, PaperRiskCapitalPolicySeed):
            raise OafOperatorPaperIntentError("canonical policy_seed is required")
        if not isinstance(self.execution_observation, ExecutionObservation):
            raise OafOperatorPaperIntentError("canonical execution_observation is required")
        if not isinstance(self.simulation_configuration, SimulationConfigurationIdentity):
            raise OafOperatorPaperIntentError("canonical simulation_configuration is required")
        if not isinstance(self.replay_identity, ReplayIdentity):
            raise OafOperatorPaperIntentError("canonical replay_identity is required")
        if not isinstance(self.simulation_policy, PaperSimulationAssumptionPolicy):
            raise OafOperatorPaperIntentError("canonical simulation_policy is required")
        if self.simulation_policy.mode is not PaperSimulationMode.FRESH_GENESIS:
            raise OafOperatorPaperIntentError(
                "first operator prepare transport supports FRESH_GENESIS only"
            )
        if not isinstance(self.genesis, GenesisPaperDeclaration):
            raise OafOperatorPaperIntentError("canonical genesis declaration is required")
        if not isinstance(self.target_asset_identity, Mapping) or not self.target_asset_identity:
            raise OafOperatorPaperIntentError("target_asset_identity is required")


class OafOperatorPaperIntentBuilder:
    """Resolve one explicit candle selector against exact RTI-11 output."""

    def build(
        self,
        rti11_result: P01Rti11CompositionResult,
        intent: OafOperatorPaperIntent,
    ) -> OafExplicitPaperInputs:
        if not isinstance(rti11_result, P01Rti11CompositionResult):
            raise OafOperatorPaperIntentError("canonical RTI-11 result is required")
        if not isinstance(intent, OafOperatorPaperIntent):
            raise OafOperatorPaperIntentError("operator paper intent is required")
        intent.__post_init__()

        if rti11_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
            raise OafOperatorPaperIntentError(
                "RTI-11 did not produce selectable historical evidence"
            )
        diagnostic = rti11_result.diagnostic
        if diagnostic is None or diagnostic.diagnostic is None:
            raise OafOperatorPaperIntentError("RTI-11 diagnostic evidence is unavailable")
        target = rti11_result.request.target
        if (
            intent.target_asset_identity.get("chain_id") != target.chain_id
            or intent.target_asset_identity.get("token_identity") != target.token_mint
        ):
            raise OafOperatorPaperIntentError("paper target does not match RTI-11 target")

        matches = [
            observation
            for observation in diagnostic.diagnostic.market.observations
            if observation.observation_time == intent.selected_observation_time
            and observation.chain_id == target.chain_id
            and observation.token_identity == target.token_mint
            and observation.market_subject_id == target.pool_address
        ]
        if len(matches) != 1:
            raise OafOperatorPaperIntentError(
                "selected historical observation must resolve exactly once"
            )
        selected = matches[0]

        return OafExplicitPaperInputs(
            pfx_invocation_id=intent.pfx_invocation_id,
            cip_invocation_id=intent.cip_invocation_id,
            decision_ruleset=intent.decision_ruleset,
            decision_time=intent.decision_time,
            policy_seed=intent.policy_seed,
            execution_observation=intent.execution_observation,
            simulation_configuration=intent.simulation_configuration,
            replay_identity=intent.replay_identity,
            simulation_reference_time=intent.simulation_reference_time,
            paper_evaluation_time=intent.paper_evaluation_time,
            source_observation_id=selected.observation_id,
            source_observation_fingerprint=selected.fingerprint,
            target_asset_identity=intent.target_asset_identity,
            simulation_policy=intent.simulation_policy,
            genesis=intent.genesis,
            prior_state=None,
            initial_state_identity=None,
        )


__all__ = [
    "OafOperatorPaperIntent",
    "OafOperatorPaperIntentBuilder",
    "OafOperatorPaperIntentError",
    "P01_OAF_OPERATOR_PAPER_INTENT_VERSION",
]
