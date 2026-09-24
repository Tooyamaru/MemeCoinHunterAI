"""Focused P01-CIP-01 checks using exact upstream owner results."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast

import pytest

from backend.application.controlled_paper_experiment_input_preparation import (
    P01_CIP_01_CONTRACT_VERSION,
    ControlledInputPreparationOutcome,
    ControlledPaperExperimentInputPreparer,
    P01Cip01Request,
    P01Cip01Result,
)
from backend.application.paper_fact_sourcing import (
    PaperFactSourcingOutcome,
    PaperFactSourcingService,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01Pfx01Request,
    PrevalidatedDecisionRiskCapitalPrefixService,
)
from backend.application.prevalidated_risk_capital_suffix_caller import P01Osc02Request
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_paper_fact_sourcing import _policy as _pfs_policy, _request_pfs
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _case(*, blocked=False, capacity=None, portfolio_id=None):
    pfs_request = _request_pfs()
    rti11 = pfs_request.rti11_result
    seed = _seed(rti11, blocked=blocked)
    seed = replace(
        seed,
        simulation_reference_time=pfs_request.simulation_reference_time,
        policy_cutoff_time=pfs_request.simulation_reference_time,
        seed_digest=None,
    )
    pfx_request = P01Pfx01Request(
        invocation_id="pfx:one", rti11_result=rti11,
        decision_ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("50"), watch_score_threshold=Decimal("10")
        ),
        decision_time=rti11.request.reference_time, policy_seed=seed,
    )
    pfx = PrevalidatedDecisionRiskCapitalPrefixService().run(pfx_request)
    genesis = replace(
        pfs_request.genesis,
        portfolio_scope={"paper_portfolio_id": portfolio_id or seed.paper_portfolio_id},
    )
    policy = _pfs_policy(simulated_capacity=capacity) if capacity is not None else pfs_request.policy
    pfs_request = replace(pfs_request, genesis=genesis, policy=policy)
    pfs = PaperFactSourcingService().source(pfs_request)
    return P01Cip01Request("osc:one", pfx, pfs)


def test_prepares_one_exact_osc_request_with_zero_owner_calls():
    request = _case()
    calls = []

    def factory(**kwargs):
        calls.append(kwargs)
        return P01Osc02Request(**kwargs)

    result = ControlledPaperExperimentInputPreparer(request_factory=factory).prepare(request)
    assert len(calls) == 1
    assert result.contract_version == P01_CIP_01_CONTRACT_VERSION
    assert result.outcome is ControlledInputPreparationOutcome.REQUEST_PREPARED
    assert result.reason_codes == ()
    assert result.terminal_stage == "OSC-02"
    output = result.osc02_request
    assert type(output) is P01Osc02Request
    assert output.invocation_id == request.invocation_id
    assert output.rti14_result is request.pfx_result.rti14_result
    assert output.execution_observation is request.pfs_result.request.execution_observation
    assert output.simulation_configuration is request.pfs_result.request.simulation_configuration
    assert output.initial_paper_state is request.pfs_result.initial_state_identity
    assert output.replay_identity is request.pfs_result.request.replay_identity
    assert output.fill_instruction is request.pfs_result.fill_instruction
    assert output.lifecycle_evidence is request.pfs_result.lifecycle_evidence
    assert result.request is request
    assert result.result_digest == ControlledPaperExperimentInputPreparer().prepare(request).result_digest
    assert output.initial_paper_state.portfolio_scope["paper_portfolio_id"] == (
        request.pfx_result.policy_snapshot.scope_identity["paper_portfolio_id"]
    )


def test_rejected_prefix_and_pfs_refusal_stop_before_request_constructor():
    constructor_calls = []

    def factory(**kwargs):
        constructor_calls.append(kwargs)
        return P01Osc02Request(**kwargs)

    service = ControlledPaperExperimentInputPreparer(request_factory=factory)
    rejected = service.prepare(_case(blocked=True))
    assert rejected.outcome is ControlledInputPreparationOutcome.PREFIX_NOT_ELIGIBLE
    assert rejected.terminal_stage == "PFX-01"
    assert rejected.osc02_request is None
    refused_case = _case(capacity=Decimal("1"))
    assert refused_case.pfs_result.outcome is PaperFactSourcingOutcome.CAPACITY_UNAVAILABLE
    refused = service.prepare(refused_case)
    assert refused.outcome is ControlledInputPreparationOutcome.FACTS_NOT_MATERIALIZED
    assert refused.terminal_stage == "PFS-01"
    assert refused.osc02_request is None
    assert constructor_calls == []


def test_exact_rti11_object_is_required_even_when_value_and_digest_match():
    request = _case()
    second = _request_pfs()
    assert second.rti11_result == request.pfx_result.request.rti11_result
    assert second.rti11_result is not request.pfx_result.request.rti11_result
    with pytest.raises(ValueError, match="RTI-11 identity"):
        replace(request, pfs_result=PaperFactSourcingService().source(second))


def test_invalid_inputs_portfolio_time_and_selected_source_fail_validation():
    request = _case()
    with pytest.raises(ValueError, match="compatibility validation failed"):
        ControlledPaperExperimentInputPreparer().prepare(_case(portfolio_id="other"))
    with pytest.raises(ValueError, match="invocation"):
        replace(request, invocation_id=" ")
    pfs = request.pfs_result
    object.__setattr__(pfs, "result_digest", "f" * 64)
    with pytest.raises(ValueError, match="noncanonical PFS"):
        ControlledPaperExperimentInputPreparer().prepare(request)

    request = _case()
    pfs = request.pfs_result
    source = pfs.request.rti11_result.diagnostic.diagnostic.market.observations[0]
    altered_request = replace(
        pfs.request,
        source_observation_id=source.observation_id,
        source_observation_fingerprint=source.fingerprint,
    )
    altered_pfs = replace(
        pfs, request=altered_request,
        source_observation_digest=source.fingerprint, result_digest=None,
    )
    with pytest.raises(ValueError, match="compatibility validation failed"):
        ControlledPaperExperimentInputPreparer().prepare(replace(request, pfs_result=altered_pfs))


def test_constructor_valueerror_stays_validation_and_unexpected_failure_is_bounded():
    request = _case()
    calls = []

    def validation_failure(**kwargs):
        calls.append("validation")
        raise ValueError("sensitive owner detail")

    with pytest.raises(ValueError, match="OSC-02 request validation failed") as error:
        ControlledPaperExperimentInputPreparer(request_factory=validation_failure).prepare(request)
    assert "sensitive" not in str(error.value)
    assert calls == ["validation"]

    def unexpected(**kwargs):
        calls.append("unexpected")
        raise RuntimeError("sensitive owner detail")

    unavailable = ControlledPaperExperimentInputPreparer(request_factory=unexpected).prepare(request)
    assert unavailable.outcome is ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE
    assert unavailable.reason_codes == ("OSC_REQUEST_UNAVAILABLE",)
    assert unavailable.osc02_request is None
    assert calls == ["validation", "unexpected"]
    assert unavailable.result_digest == ControlledPaperExperimentInputPreparer(
        request_factory=unexpected
    ).prepare(request).result_digest


def test_wrong_constructor_result_is_bounded_and_result_digest_is_checked():
    request = _case()
    unavailable = ControlledPaperExperimentInputPreparer(
        request_factory=lambda **_: object()
    ).prepare(request)
    assert unavailable.outcome is ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE
    prepared = ControlledPaperExperimentInputPreparer().prepare(request)
    with pytest.raises(ValueError, match="digest mismatch"):
        replace(prepared, result_digest="0" * 64)
    with pytest.raises(ValueError, match="exact inputs"):
        replace(prepared, osc02_request=replace(prepared.osc02_request, invocation_id="osc:other"))


def test_forbidden_owner_services_are_unreachable_in_preparer_source():
    source = Path(
        "backend/application/controlled_paper_experiment_input_preparation.py"
    ).read_text()
    tree = ast.parse(source)
    import_names = {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "PrevalidatedDecisionRiskCapitalPrefixService" not in import_names
    assert "PaperFactSourcingService" not in import_names
    assert "PrevalidatedRiskCapitalSuffixCaller" not in import_names
    assert "RiskCapitalToPaperAdmissionContinuationService" not in import_names
    assert "Rti15ToControlledPaperLifecycleContinuationService" not in import_names
    assert "ControlledPaperPersistenceService" not in import_names
    assert "OneShotPaperPersistenceService" not in import_names
    assert "run_controlled_paper_lifecycle" not in import_names
