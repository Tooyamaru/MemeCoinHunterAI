"""Focused contract tests for P01-PFX-01."""

from dataclasses import replace
from pathlib import Path
import ast

import pytest

from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalContinuationService,
)
from backend.application.opportunity_context_to_decision_continuation import (
    OpportunityContextToDecisionContinuationService,
)
from backend.application.p05_opportunity_context_continuation import (
    P05OpportunityContextContinuationService,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01_PFX_01_CONTRACT_VERSION,
    P01Pfx01Request,
    PaperRiskCapitalPolicySeed,
    PrevalidatedDecisionRiskCapitalPrefixService,
    PrevalidatedPrefixOutcome,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PaperRiskCapitalPolicySnapshot,
    RiskStateStatus,
)
from tests.test_opportunity_context_to_decision_continuation import _ruleset
from tests.test_p05_opportunity_context_continuation import (
    _composed,
    _composition_unavailable,
)
from tests.test_paper_risk_capital_authorization import _policy


def _seed(rti11=None, *, blocked=False):
    rti11 = rti11 or _composed()
    rti12 = P05OpportunityContextContinuationService().continue_to_context(rti11)
    rti13 = OpportunityContextToDecisionContinuationService().continue_to_decision(
        rti12, _ruleset(), rti12.context.reference_time
    )
    policy = _policy(rti13.decision_intent)
    risk_state = policy.risk_state
    if blocked:
        risk_state = replace(
            risk_state,
            status=RiskStateStatus.BLOCK,
            risk_flags=("blocked",),
            state_digest=None,
        )
    return PaperRiskCapitalPolicySeed(
        policy_snapshot_id=policy.policy_snapshot_id,
        risk_governor_version=policy.risk_governor_version,
        capital_authorization_version=policy.capital_authorization_version,
        evaluator_version=policy.evaluator_version,
        paper_lifecycle_id=policy.scope_identity["paper_lifecycle_id"],
        paper_portfolio_id=policy.scope_identity["paper_portfolio_id"],
        simulation_reference_time=policy.simulation_reference_time,
        policy_cutoff_time=policy.policy_cutoff_time,
        risk_state_max_age_seconds=policy.risk_state_max_age_seconds,
        paper_capital_state_max_age_seconds=policy.paper_capital_state_max_age_seconds,
        paper_exposure_state_max_age_seconds=policy.paper_exposure_state_max_age_seconds,
        valid_from=policy.valid_from,
        valid_until=policy.valid_until,
        risk_state=risk_state,
        paper_capital_state=policy.paper_capital_state,
        paper_exposure_state=policy.paper_exposure_state,
        provenance_source="pfx-test",
    )


def _request(rti11=None, *, seed=None):
    rti11 = rti11 or _composed()
    return P01Pfx01Request(
        invocation_id="pfx:1",
        rti11_result=rti11,
        decision_ruleset=_ruleset(),
        decision_time=rti11.request.reference_time,
        policy_seed=seed or _seed(rti11),
    )


def test_exact_happy_path_calls_each_owner_and_policy_factory_once():
    request = _request()
    calls = []

    class Rti12:
        def __init__(self):
            self.owner = P05OpportunityContextContinuationService()

        def continue_to_context(self, upstream):
            calls.append(("RTI-12", upstream))
            return self.owner.continue_to_context(upstream)

    class Rti13:
        def __init__(self):
            self.owner = OpportunityContextToDecisionContinuationService()

        def continue_to_decision(self, upstream, ruleset, decision_time):
            calls.append(("RTI-13", upstream, ruleset, decision_time))
            return self.owner.continue_to_decision(upstream, ruleset, decision_time)

    class Rti14:
        def __init__(self):
            self.owner = DecisionToRiskCapitalContinuationService()

        def continue_to_risk_capital(self, upstream, policy):
            calls.append(("RTI-14", upstream, policy))
            return self.owner.continue_to_risk_capital(upstream, policy)

    def policy_factory(**kwargs):
        calls.append(("POLICY", kwargs))
        return PaperRiskCapitalPolicySnapshot(**kwargs)

    result = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Rti12(),
        rti13=Rti13(),
        policy_factory=policy_factory,
        rti14=Rti14(),
    ).run(request)

    assert result.contract_version == P01_PFX_01_CONTRACT_VERSION
    assert result.outcome is PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED
    assert result.terminal_stage == "RTI-14"
    assert [entry[0] for entry in calls] == ["RTI-12", "RTI-13", "POLICY", "RTI-14"]
    assert calls[0][1] is request.rti11_result
    assert calls[1][1] is result.rti12_result
    assert calls[1][2] is request.decision_ruleset
    assert calls[2][1]["decision_intent_digest"] == result.rti13_result.decision_intent.digest
    assert calls[2][1]["context_digest"] == result.rti13_result.decision_intent.context_digest
    assert calls[3][1] is result.rti13_result
    assert calls[3][2] is result.policy_snapshot
    assert result.rti12_result.upstream_result is request.rti11_result
    assert result.rti13_result.upstream_result is result.rti12_result
    assert result.rti14_result.upstream_result is result.rti13_result
    assert result.rti14_result.policy_snapshot is result.policy_snapshot


def test_policy_is_bound_only_after_exact_decision_and_preserves_seed_fields():
    request = _request()
    result = PrevalidatedDecisionRiskCapitalPrefixService().run(request)
    decision = result.rti13_result.decision_intent
    policy = result.policy_snapshot
    seed = request.policy_seed

    assert policy.decision_intent_digest == decision.digest
    assert policy.context_digest == decision.context_digest
    assert policy.scope_identity["candidate_id"] == decision.candidate_id
    assert policy.scope_identity["chain_id"] == decision.chain_id
    assert policy.scope_identity["token_identity"] == decision.token_identity
    assert policy.scope_identity["paper_lifecycle_id"] == seed.paper_lifecycle_id
    assert policy.scope_identity["paper_portfolio_id"] == seed.paper_portfolio_id
    assert policy.risk_state is seed.risk_state
    assert policy.paper_capital_state is seed.paper_capital_state
    assert policy.paper_exposure_state is seed.paper_exposure_state
    assert policy.provenance["p06_ruleset_version"] == decision.ruleset_version
    assert policy.provenance["decision_intent_digest"] == decision.digest
    assert policy.provenance["context_digest"] == decision.context_digest


def test_noncomposed_rti11_stops_before_all_prefix_owners():
    rti11 = _composition_unavailable()
    request = _request(rti11, seed=_seed())
    calls = []

    class Forbidden:
        def __getattr__(self, name):
            def fail(*args, **kwargs):
                calls.append(name)
                raise AssertionError("must not run")
            return fail

    result = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Forbidden(),
        rti13=Forbidden(),
        rti14=Forbidden(),
    ).run(request)
    assert result.outcome is PrevalidatedPrefixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-11"
    assert result.rti12_result is None
    assert calls == []


def test_nonmaterialized_rti12_stops_before_rti13_policy_and_rti14():
    request = _request()
    calls = []

    class Rti12Unavailable:
        def continue_to_context(self, upstream):
            return P05OpportunityContextContinuationService(
                record_materializer=lambda value: object()
            ).continue_to_context(upstream)

    class Forbidden13:
        def continue_to_decision(self, *args, **kwargs):
            calls.append("RTI-13")
            raise AssertionError("must not run")

    def forbidden_policy(**kwargs):
        calls.append("POLICY")
        raise AssertionError("must not run")

    class Forbidden14:
        def continue_to_risk_capital(self, *args, **kwargs):
            calls.append("RTI-14")
            raise AssertionError("must not run")

    result = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Rti12Unavailable(),
        rti13=Forbidden13(),
        policy_factory=forbidden_policy,
        rti14=Forbidden14(),
    ).run(request)
    assert result.outcome is PrevalidatedPrefixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-12"
    assert result.rti13_result is None
    assert calls == []


def test_nonmaterialized_rti13_stops_before_policy_and_rti14():
    request = _request()
    calls = []

    class Rti13Unavailable:
        def __init__(self):
            self.owner = OpportunityContextToDecisionContinuationService(
                decision_evaluator=lambda *args, **kwargs: (_ for _ in ()).throw(
                    RuntimeError("unavailable")
                )
            )

        def continue_to_decision(self, *args, **kwargs):
            return self.owner.continue_to_decision(*args, **kwargs)

    def forbidden_policy(**kwargs):
        calls.append("POLICY")
        raise AssertionError("must not run")

    class Forbidden14:
        def continue_to_risk_capital(self, *args, **kwargs):
            calls.append("RTI-14")
            raise AssertionError("must not run")

    result = PrevalidatedDecisionRiskCapitalPrefixService(
        rti13=Rti13Unavailable(),
        policy_factory=forbidden_policy,
        rti14=Forbidden14(),
    ).run(request)
    assert result.outcome is PrevalidatedPrefixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-13"
    assert result.policy_snapshot is None
    assert calls == []


def test_canonical_risk_capital_rejection_is_still_materialized_prefix():
    rti11 = _composed()
    request = _request(rti11, seed=_seed(rti11, blocked=True))
    result = PrevalidatedDecisionRiskCapitalPrefixService().run(request)
    assert result.outcome is PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED
    assert result.rti14_result.authorization_result.status is AuthorizationStatus.REJECTED
    assert "RISK_STATE_BLOCKED" in result.rti14_result.authorization_result.reason_codes


def test_tampered_request_fails_before_owner_call():
    request = _request()
    object.__setattr__(request.rti11_result, "result_digest", "0" * 64)
    calls = []

    class Rti12:
        def continue_to_context(self, *args):
            calls.append(True)

    with pytest.raises(ValueError, match="noncanonical rti11_result"):
        PrevalidatedDecisionRiskCapitalPrefixService(rti12=Rti12()).run(request)
    assert calls == []


@pytest.mark.parametrize("stage", ["RTI-12", "RTI-13", "POLICY", "RTI-14"])
def test_value_error_is_standardized_without_raw_detail(stage):
    request = _request()

    class Bad12:
        def continue_to_context(self, *args):
            raise ValueError("private")

    class Bad13:
        def continue_to_decision(self, *args):
            raise ValueError("private")

    class Bad14:
        def continue_to_risk_capital(self, *args):
            raise ValueError("private")

    def bad_policy(**kwargs):
        raise ValueError("private")

    service = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Bad12() if stage == "RTI-12" else None,
        rti13=Bad13() if stage == "RTI-13" else None,
        policy_factory=bad_policy if stage == "POLICY" else PaperRiskCapitalPolicySnapshot,
        rti14=Bad14() if stage == "RTI-14" else None,
    )
    expected = "PFX-01 policy validation failed" if stage == "POLICY" else f"{stage} validation failed"
    with pytest.raises(ValueError) as error:
        service.run(request)
    assert str(error.value) == expected
    assert "private" not in str(error.value)


@pytest.mark.parametrize("stage", ["RTI-12", "RTI-13", "POLICY", "RTI-14"])
def test_unexpected_owner_failure_is_bounded_without_retry(stage):
    request = _request()
    calls = []

    class Fail12:
        def continue_to_context(self, *args):
            calls.append("RTI-12")
            raise RuntimeError("private")

    class Fail13:
        def continue_to_decision(self, *args):
            calls.append("RTI-13")
            raise RuntimeError("private")

    class Fail14:
        def continue_to_risk_capital(self, *args):
            calls.append("RTI-14")
            raise RuntimeError("private")

    def fail_policy(**kwargs):
        calls.append("POLICY")
        raise RuntimeError("private")

    service = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Fail12() if stage == "RTI-12" else None,
        rti13=Fail13() if stage == "RTI-13" else None,
        policy_factory=fail_policy if stage == "POLICY" else PaperRiskCapitalPolicySnapshot,
        rti14=Fail14() if stage == "RTI-14" else None,
    )
    result = service.run(request)
    assert calls == [stage]
    assert result.outcome is PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE
    expected_reason = "POLICY_SNAPSHOT_UNAVAILABLE" if stage == "POLICY" else f"{stage}_UNAVAILABLE"
    assert result.reason_codes == (expected_reason,)
    assert "private" not in str(result.canonical_representation)


@pytest.mark.parametrize("stage", ["RTI-12", "RTI-13", "POLICY", "RTI-14"])
def test_invalid_owner_return_is_bounded(stage):
    request = _request()

    class Invalid12:
        def continue_to_context(self, *args):
            return object()

    class Invalid13:
        def continue_to_decision(self, *args):
            return object()

    class Invalid14:
        def continue_to_risk_capital(self, *args):
            return object()

    def invalid_policy(**kwargs):
        return object()

    service = PrevalidatedDecisionRiskCapitalPrefixService(
        rti12=Invalid12() if stage == "RTI-12" else None,
        rti13=Invalid13() if stage == "RTI-13" else None,
        policy_factory=invalid_policy if stage == "POLICY" else PaperRiskCapitalPolicySnapshot,
        rti14=Invalid14() if stage == "RTI-14" else None,
    )
    result = service.run(request)
    assert result.outcome is PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE


def test_deterministic_digest_and_invocation_binding():
    request = _request()
    first = PrevalidatedDecisionRiskCapitalPrefixService().run(request)
    second = PrevalidatedDecisionRiskCapitalPrefixService().run(request)
    changed = PrevalidatedDecisionRiskCapitalPrefixService().run(
        replace(request, invocation_id="pfx:2")
    )
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation
    assert first.digest != changed.digest
    with pytest.raises(ValueError, match="digest"):
        replace(first, result_digest="0" * 64)


def test_module_has_no_suffix_pfs_persistence_provider_or_runtime_imports():
    path = Path("backend/application/prevalidated_decision_risk_capital_prefix.py")
    tree = ast.parse(path.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "risk_capital_to_paper_admission",
        "rti15_to_controlled",
        "one_shot_controlled",
        "prevalidated_risk_capital_suffix",
        "paper_fact_sourcing",
        "one_shot_paper_persistence",
        "paper_lifecycle_persistence",
        "httpx",
        "requests",
        "fastapi",
        "sqlalchemy",
        "worker",
        "scheduler",
    }
    assert not any(any(part in name for part in forbidden) for name in imports)
