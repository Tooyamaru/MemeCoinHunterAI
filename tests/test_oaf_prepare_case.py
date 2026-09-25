from dataclasses import replace
from decimal import Decimal

import pytest

from backend.application.oaf_prepare_case import (
    OafPrepareCaseError,
    OafPrepareCaseRequest,
    OafPrepareCaseService,
)
from backend.application.paper_fact_sourcing import PaperFactSourcingService
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01Pfx01Request,
    PrevalidatedDecisionRiskCapitalPrefixService,
)
from backend.application.controlled_paper_experiment_input_preparation import (
    ControlledInputPreparationOutcome,
    ControlledPaperExperimentInputPreparer,
)
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_paper_fact_sourcing import _request_pfs
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _request():
    pfs_request = _request_pfs()
    rti11 = pfs_request.rti11_result
    seed = replace(
        _seed(rti11),
        simulation_reference_time=pfs_request.simulation_reference_time,
        policy_cutoff_time=pfs_request.simulation_reference_time,
        seed_digest=None,
    )
    pfx_request = P01Pfx01Request(
        invocation_id="oaf-pfx:one",
        rti11_result=rti11,
        decision_ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("50"),
            watch_score_threshold=Decimal("10"),
        ),
        decision_time=rti11.request.reference_time,
        policy_seed=seed,
    )
    genesis = replace(
        pfs_request.genesis,
        portfolio_scope={"paper_portfolio_id": seed.paper_portfolio_id},
    )
    pfs_request = replace(pfs_request, genesis=genesis)
    return OafPrepareCaseRequest(
        invocation_id="oaf-cip:one",
        rti11_result=rti11,
        pfx_request=pfx_request,
        pfs_request=pfs_request,
    )


def test_prepare_runs_exact_owners_once_and_returns_prepared_cip():
    calls = []

    class Pfx:
        def __init__(self):
            self.owner = PrevalidatedDecisionRiskCapitalPrefixService()

        def run(self, request):
            calls.append(("PFX", request))
            return self.owner.run(request)

    class Pfs:
        def __init__(self):
            self.owner = PaperFactSourcingService()

        def source(self, request):
            calls.append(("PFS", request))
            return self.owner.source(request)

    class Cip:
        def __init__(self):
            self.owner = ControlledPaperExperimentInputPreparer()

        def prepare(self, request):
            calls.append(("CIP", request))
            return self.owner.prepare(request)

    request = _request()
    result = OafPrepareCaseService(pfx=Pfx(), pfs=Pfs(), cip=Cip()).prepare(request)

    assert [item[0] for item in calls] == ["PFX", "PFS", "CIP"]
    assert calls[0][1] is request.pfx_request
    assert calls[1][1] is request.pfs_request
    assert result.pfx_result.request is request.pfx_request
    assert result.pfs_result.request is request.pfs_request
    assert result.cip_result.outcome is ControlledInputPreparationOutcome.REQUEST_PREPARED
    assert result.cip_result.osc02_request is not None
    assert result.cip_result.request.pfx_result is result.pfx_result
    assert result.cip_result.request.pfs_result is result.pfs_result


def test_mismatched_rti11_identity_fails_before_any_owner():
    request = _request()
    other = _request().pfs_request
    with pytest.raises(OafPrepareCaseError, match="PFS request"):
        replace(request, pfs_request=other)


def test_noncanonical_owner_result_fails_closed():
    class BadPfx:
        def run(self, request):
            return object()

    request = _request()
    with pytest.raises(OafPrepareCaseError, match="PFX returned noncanonical"):
        OafPrepareCaseService(pfx=BadPfx()).prepare(request)
