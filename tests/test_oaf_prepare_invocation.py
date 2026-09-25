from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from backend.application.oaf_prepare_invocation import (
    OafPrepareInvocation,
    OafPrepareInvocationError,
    OafPrepareInvocationService,
)
from backend.application.oaf_paper_request_factory import OafExplicitPaperInputs
from backend.application.operator_paper_case_registry import OperatorPaperCaseRegistry
from backend.application.prevalidated_decision_risk_capital_prefix import P01Pfx01Request
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_oaf_rti11_integration import _snapshot, _upstream
from tests.test_oaf_trusted_prepare import _command
from tests.test_paper_fact_sourcing import _request_pfs, _rti11
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _paper_inputs(rti11):
    pfs = _request_pfs(rti11_result=rti11)
    seed = replace(
        _seed(rti11),
        simulation_reference_time=pfs.simulation_reference_time,
        policy_cutoff_time=pfs.simulation_reference_time,
        seed_digest=None,
    )
    return OafExplicitPaperInputs(
        pfx_invocation_id="oaf:pfx:invocation",
        cip_invocation_id="oaf:cip:invocation",
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
        genesis=replace(
            pfs.genesis,
            portfolio_scope={"paper_portfolio_id": seed.paper_portfolio_id},
        ),
        prior_state=pfs.prior_state,
        initial_state_identity=pfs.initial_state_identity,
    )


def test_invocation_binds_exact_explicit_inputs_into_one_trusted_prepare():
    canonical_rti11 = _rti11()
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
            return canonical_rti11

    registry = OperatorPaperCaseRegistry(capacity=4, ttl=timedelta(minutes=10))
    inputs = _paper_inputs(canonical_rti11)
    invocation = OafPrepareInvocation(_command(canonical_rti11), inputs)
    result = OafPrepareInvocationService(
        solana_source=Source(),
        registry=registry,
        upstream=Upstream(),
        rti11=Rti11(),
    ).prepare(invocation)

    assert [entry[0] for entry in calls] == ["SOURCE", "UPSTREAM", "RTI11"]
    assert result.prepared.request.rti11_result is canonical_rti11
    assert result.prepared.request.pfx_request.rti11_result is canonical_rti11
    assert result.prepared.request.pfs_request.rti11_result is canonical_rti11
    assert result.prepared.request.pfs_request.execution_observation is inputs.execution_observation
    assert result.prepared.request.pfs_request.simulation_configuration is inputs.simulation_configuration
    assert result.record.prepared is result.prepared
    assert registry.get(result.record.handle) is result.record


def test_invalid_invocation_stops_before_source():
    canonical_rti11 = _rti11()
    calls = []

    class Source:
        def snapshot_mint(self, token):
            calls.append("SOURCE")
            raise AssertionError("must not run")

    service = OafPrepareInvocationService(
        solana_source=Source(),
        registry=OperatorPaperCaseRegistry(),
    )
    with pytest.raises(OafPrepareInvocationError, match="invalid prepare invocation"):
        service.prepare(object())

    assert calls == []


def test_target_mismatch_in_paper_inputs_fails_before_case_registration():
    canonical_rti11 = _rti11()
    inputs = _paper_inputs(canonical_rti11)
    bad = replace(
        inputs,
        target_asset_identity={"chain_id": "solana", "token_identity": "different"},
    )

    class Source:
        def snapshot_mint(self, token):
            return _snapshot()

    class Upstream:
        def compose(self, **kwargs):
            return _upstream()

    class Rti11:
        def compose(self, request):
            return canonical_rti11

    registry = OperatorPaperCaseRegistry()
    with pytest.raises(ValueError, match="paper target"):
        OafPrepareInvocationService(
            solana_source=Source(),
            registry=registry,
            upstream=Upstream(),
            rti11=Rti11(),
        ).prepare(OafPrepareInvocation(_command(canonical_rti11), bad))

    assert registry.size() == 0
