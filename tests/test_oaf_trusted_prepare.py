from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from backend.application.oaf_prepare_case import OafPrepareCaseRequest
from backend.application.oaf_trusted_prepare import (
    OafTrustedPrepareCommand,
    OafTrustedPrepareError,
    OafTrustedPrepareService,
)
from backend.application.operator_paper_case_registry import OperatorPaperCaseRegistry
from backend.application.prevalidated_decision_risk_capital_prefix import P01Pfx01Request
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from tests.test_oaf_rti11_integration import _snapshot, _upstream
from tests.test_paper_fact_sourcing import _request_pfs, _rti11
from tests.test_prevalidated_decision_risk_capital_prefix import _seed


def _factory(rti11, command):
    pfs = _request_pfs(rti11_result=rti11)
    seed = replace(
        _seed(rti11),
        simulation_reference_time=pfs.simulation_reference_time,
        policy_cutoff_time=pfs.simulation_reference_time,
        seed_digest=None,
    )
    pfx = P01Pfx01Request(
        invocation_id="oaf:pfx:trusted",
        rti11_result=rti11,
        decision_ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("50"),
            watch_score_threshold=Decimal("10"),
        ),
        decision_time=rti11.request.reference_time,
        policy_seed=seed,
    )
    pfs = replace(
        pfs,
        genesis=replace(
            pfs.genesis,
            portfolio_scope={"paper_portfolio_id": seed.paper_portfolio_id},
        ),
    )
    return OafPrepareCaseRequest(
        invocation_id="oaf:cip:trusted",
        rti11_result=rti11,
        pfx_request=pfx,
        pfs_request=pfs,
    )


def _command(rti11):
    return OafTrustedPrepareCommand(
        candidate_id=rti11.request.candidate_id,
        token_mint=rti11.request.target.token_mint,
        target=rti11.request.target,
        processing_time=rti11.request.processing_time,
        reference_time=rti11.request.reference_time,
        evaluation_time=rti11.request.evaluated_at,
        freshness_policy=rti11.request.freshness_policy,
        max_top_holder_fraction=0.2,
        rti11_timeout=rti11.request.timeout,
        rti11_max_response_bytes=rti11.request.max_response_bytes,
        evaluation_id=rti11.request.evaluation_id or "oaf:trusted",
    )


def test_trusted_prepare_runs_one_shot_chain_and_registers_exact_case():
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
    service = OafTrustedPrepareService(
        solana_source=Source(),
        prepare_request_factory=_factory,
        upstream=Upstream(),
        rti11=Rti11(),
        registry=registry,
    )

    result = service.prepare(_command(canonical_rti11))

    assert [entry[0] for entry in calls] == ["SOURCE", "UPSTREAM", "RTI11"]
    assert result.prepared.request.rti11_result is canonical_rti11
    assert result.record.prepared is result.prepared
    assert registry.get(result.record.handle) is result.record
    assert result.record.case_digest == result.record.case_digest


def test_invalid_snapshot_stops_before_upstream_and_rti11():
    canonical_rti11 = _rti11()
    calls = []

    class Source:
        def snapshot_mint(self, token):
            calls.append("SOURCE")
            return object()

    class Forbidden:
        def compose(self, *args, **kwargs):
            calls.append("FORBIDDEN")
            raise AssertionError("must not run")

    with pytest.raises(OafTrustedPrepareError, match="invalid snapshot"):
        OafTrustedPrepareService(
            solana_source=Source(),
            prepare_request_factory=_factory,
            upstream=Forbidden(),
            rti11=Forbidden(),
            registry=OperatorPaperCaseRegistry(),
        ).prepare(_command(canonical_rti11))

    assert calls == ["SOURCE"]


def test_rti11_candidate_or_target_mismatch_fails_before_factory_and_registry():
    canonical_rti11 = _rti11()
    factory_calls = []

    class Source:
        def snapshot_mint(self, token):
            return _snapshot()

    class Upstream:
        def compose(self, **kwargs):
            return _upstream()

    class Rti11:
        def compose(self, request):
            return canonical_rti11

    command = replace(_command(canonical_rti11), candidate_id="different-candidate")
    with pytest.raises(OafTrustedPrepareError, match="RTI-11 result identity mismatch"):
        OafTrustedPrepareService(
            solana_source=Source(),
            prepare_request_factory=lambda *args: factory_calls.append(args),
            upstream=Upstream(),
            rti11=Rti11(),
            registry=OperatorPaperCaseRegistry(),
        ).prepare(command)

    assert factory_calls == []


def test_factory_must_bind_exact_rti11_object():
    canonical_rti11 = _rti11()

    class Source:
        def snapshot_mint(self, token):
            return _snapshot()

    class Upstream:
        def compose(self, **kwargs):
            return _upstream()

    class Rti11:
        def compose(self, request):
            return canonical_rti11

    def bad_factory(rti11, command):
        other = _rti11()
        return _factory(other, command)

    with pytest.raises(OafTrustedPrepareError, match="exact RTI-11 identity"):
        OafTrustedPrepareService(
            solana_source=Source(),
            prepare_request_factory=bad_factory,
            upstream=Upstream(),
            rti11=Rti11(),
            registry=OperatorPaperCaseRegistry(),
        ).prepare(_command(canonical_rti11))
