from dataclasses import replace
from decimal import Decimal

import pytest

from backend.application.oaf_paper_request_factory import (
    OafExplicitPaperInputs,
    OafPaperRequestFactory,
    OafPaperRequestFactoryError,
)
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_paper_fact_sourcing import _request_pfs
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _inputs(rti11):
    pfs = _request_pfs(rti11_result=rti11)
    seed = replace(
        _seed(rti11),
        simulation_reference_time=pfs.simulation_reference_time,
        policy_cutoff_time=pfs.simulation_reference_time,
        seed_digest=None,
    )
    genesis = replace(
        pfs.genesis,
        portfolio_scope={"paper_portfolio_id": seed.paper_portfolio_id},
    )
    return OafExplicitPaperInputs(
        pfx_invocation_id="oaf:pfx:factory",
        cip_invocation_id="oaf:cip:factory",
        decision_ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("50"),
            watch_score_threshold=Decimal("10"),
        ),
        decision_time=rti11.request.reference_time,
        policy_seed=seed,
        execution_observation=pfs.execution_observation,
        simulation_configuration=pfs.simulation_configuration,
        replay_identity=pfs.replay_identity,
        simulation_reference_time=pfs.simulation_reference_time,
        paper_evaluation_time=pfs.paper_evaluation_time,
        source_observation_id=pfs.source_observation_id,
        source_observation_fingerprint=pfs.source_observation_fingerprint,
        target_asset_identity=pfs.target_asset_identity,
        simulation_policy=pfs.policy,
        genesis=genesis,
        prior_state=pfs.prior_state,
        initial_state_identity=pfs.initial_state_identity,
    )


def test_factory_builds_exact_pfx_and_pfs_around_same_rti11_object():
    base = _request_pfs()
    rti11 = base.rti11_result
    inputs = _inputs(rti11)
    request = OafPaperRequestFactory().build(rti11, inputs)

    assert request.rti11_result is rti11
    assert request.pfx_request.rti11_result is rti11
    assert request.pfs_request.rti11_result is rti11
    assert request.pfx_request.decision_ruleset is not None
    assert request.pfs_request.execution_observation is inputs.execution_observation
    assert request.invocation_id == "oaf:cip:factory"


def test_target_identity_mismatch_fails_before_request_construction():
    rti11 = _request_pfs().rti11_result
    inputs = _inputs(rti11)
    bad = replace(
        inputs,
        target_asset_identity={"chain_id": "solana", "token_identity": "different"},
    )

    with pytest.raises(OafPaperRequestFactoryError, match="paper target"):
        OafPaperRequestFactory().build(rti11, bad)


def test_invalid_owner_linkage_is_bounded_without_raw_owner_error():
    rti11 = _request_pfs().rti11_result
    inputs = _inputs(rti11)
    bad_execution = replace(
        inputs.execution_observation,
        subject_identity={"chain_id": "solana", "token_identity": "different"},
        observation_digest=None,
    )
    bad = replace(inputs, execution_observation=bad_execution)

    with pytest.raises(
        OafPaperRequestFactoryError,
        match="failed canonical owner validation",
    ):
        OafPaperRequestFactory().build(rti11, bad)


def test_factory_does_not_supply_hidden_defaults():
    rti11 = _request_pfs().rti11_result
    inputs = _inputs(rti11)

    assert inputs.simulation_policy.simulated_capacity is not None
    assert inputs.simulation_policy.friction_values is not None
    assert inputs.simulation_policy.expectation_fields is not None
    assert inputs.policy_seed is not None
    assert inputs.decision_ruleset is not None
