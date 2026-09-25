from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from backend.application.oaf_operator_paper_intent import (
    OafOperatorPaperIntent,
    OafOperatorPaperIntentBuilder,
    OafOperatorPaperIntentError,
)
from backend.application.oaf_operator_prepare_invocation import (
    OafOperatorPrepareInvocation,
    OafOperatorPrepareInvocationService,
)
from backend.application.operator_paper_case_registry import OperatorPaperCaseRegistry
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_oaf_rti11_integration import _snapshot, _upstream
from tests.test_oaf_trusted_prepare import _command
from tests.test_paper_fact_sourcing import _request_pfs, _rti11
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _intent(rti11):
    pfs = _request_pfs(rti11_result=rti11)
    seed = replace(
        _seed(rti11),
        simulation_reference_time=pfs.simulation_reference_time,
        policy_cutoff_time=pfs.simulation_reference_time,
        seed_digest=None,
    )
    selected = rti11.diagnostic.diagnostic.market.observations[-1]
    return OafOperatorPaperIntent(
        pfx_invocation_id="oaf:pfx:operator",
        cip_invocation_id="oaf:cip:operator",
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
        selected_observation_time=selected.observation_time,
        target_asset_identity=pfs.target_asset_identity,
        simulation_policy=pfs.policy,
        genesis=replace(
            pfs.genesis,
            portfolio_scope={"paper_portfolio_id": seed.paper_portfolio_id},
        ),
    )


def test_intent_builder_resolves_exact_server_observation_once():
    rti11 = _rti11()
    intent = _intent(rti11)
    explicit = OafOperatorPaperIntentBuilder().build(rti11, intent)
    selected = rti11.diagnostic.diagnostic.market.observations[-1]

    assert explicit.source_observation_id == selected.observation_id
    assert explicit.source_observation_fingerprint == selected.fingerprint
    assert explicit.prior_state is None
    assert explicit.initial_state_identity is None
    assert explicit.execution_observation is intent.execution_observation


def test_nonmatching_observation_selector_fails_closed():
    rti11 = _rti11()
    intent = replace(
        _intent(rti11),
        selected_observation_time=rti11.request.reference_time + timedelta(days=1),
    )
    with pytest.raises(
        OafOperatorPaperIntentError,
        match="must resolve exactly once",
    ):
        OafOperatorPaperIntentBuilder().build(rti11, intent)


def test_operator_invocation_runs_trusted_chain_and_registers_case():
    rti11 = _rti11()
    calls = []

    class Source:
        def snapshot_mint(self, token):
            calls.append(("SOURCE", token))
            return _snapshot()

    class Upstream:
        def compose(self, **kwargs):
            calls.append(("UPSTREAM", kwargs["snapshot"]))
            return _upstream()

    class Rti11:
        def compose(self, request):
            calls.append(("RTI11", request))
            return rti11

    registry = OperatorPaperCaseRegistry(capacity=4, ttl=timedelta(minutes=10))
    result = OafOperatorPrepareInvocationService(
        solana_source=Source(),
        registry=registry,
        upstream=Upstream(),
        rti11=Rti11(),
    ).prepare(OafOperatorPrepareInvocation(_command(rti11), _intent(rti11)))

    assert [entry[0] for entry in calls] == ["SOURCE", "UPSTREAM", "RTI11"]
    assert result.record.prepared is result.prepared
    assert registry.get(result.record.handle) is result.record
    assert result.prepared.request.rti11_result is rti11
