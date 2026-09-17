from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.decision import DecisionAction, EntryPosture, create_decision_intent
from core.execution import (
    AuthorizationObservation,
    ExecutionObservation,
    InitialPaperStateIdentity,
    ObservationQuality,
    ObservationStatus,
    PaperSimulationInput,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.execution.paper_simulation_input import RiskCapitalAuthorizationReference
from core.execution.paper_simulation_input import (
    P07_T01_CONTRACT_VERSION,
    P07_T01_LEGACY_CONTRACT_VERSION,
)
from core.risk.paper_risk_capital_authorization import (
    evaluate_paper_risk_capital_authorization,
)
from core.opportunity import (
    OpportunityRecordHistory,
    evaluate_opportunity_score,
    materialize_opportunity_context,
    materialize_opportunity_record,
)
from tests.test_opportunity_score import _evaluation
from tests.test_paper_risk_capital_authorization import (
    _intent as _risk_intent,
    _policy as _risk_policy,
)


UTC = timezone.utc
REFERENCE = _risk_intent().context.reference_time


def _intent(**overrides):
    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))
    context = materialize_opportunity_context(record, OpportunityRecordHistory((record,)))
    values = {
        "context": context,
        "action": DecisionAction.WATCH,
        "entry_posture": EntryPosture.WAIT,
        "expected_edge_assumptions": ("paper context only",),
        "confidence": Decimal("0.75"),
        "decision_time": REFERENCE,
    }
    values.update(overrides)
    return create_decision_intent(**values)


def _authorization(**overrides):
    values = {
        "observation_id": "auth-1",
        "status": ObservationStatus.PASS,
        "scope_identity": {"candidate_id": "candidate-1"},
        "observed_at": REFERENCE - timedelta(minutes=1),
        "valid_from": REFERENCE - timedelta(minutes=2),
        "valid_until": REFERENCE + timedelta(minutes=5),
        "contract_version": "risk-auth-v1",
        "risk_governor_version": "risk-governor-v1",
        "capital_authorization_version": "capital-auth-v1",
    }
    values.update(overrides)
    return AuthorizationObservation(**values)


def _execution(**overrides):
    values = {
        "observation_id": "execution-observation-1",
        "subject_identity": {"token_identity": "token-1"},
        "observation_time": REFERENCE - timedelta(seconds=10),
        "availability_time": REFERENCE - timedelta(seconds=5),
        "quality": ObservationQuality.PASS,
        "market_context_digest": "a" * 64,
        "quote_context_digest": "b" * 64,
        "liquidity_context_digest": "c" * 64,
        "sellability_status": ObservationStatus.PASS,
        "source_contract_version": "execution-observation-v1",
        "source_provenance": {"source": "fixture"},
        "observation_replay_key": "observation-replay-1",
    }
    values.update(overrides)
    return ExecutionObservation(**values)


def _configuration(**overrides):
    values = {
        "configuration_id": "paper-config-1",
        "contract_version": "paper-config-v1",
        "simulation_version": "simulation-v1",
        "fill_model_version": "fill-model-v1",
        "friction_model_version": "friction-model-v1",
        "failure_policy_version": "failure-policy-v1",
        "seed_policy_version": "seed-policy-v1",
        "configuration_provenance": {"owner": "test"},
    }
    values.update(overrides)
    return SimulationConfigurationIdentity(**values)


def _state(**overrides):
    values = {
        "state_id": "paper-state-1",
        "state_version": "paper-state-v1",
        "portfolio_scope": {"portfolio": "test"},
        "position_state_digest": "d" * 64,
        "exposure_state_digest": "e" * 64,
        "as_of_time": REFERENCE - timedelta(seconds=20),
        "state_quality": ObservationQuality.PASS,
        "state_provenance": {"source": "fixture"},
    }
    values.update(overrides)
    return InitialPaperStateIdentity(**values)


def _replay(**overrides):
    values = {
        "replay_id": "replay-1",
        "replay_schema_version": "replay-v1",
        "replay_seed_identity": "seed-1",
        "parent_replay_id": None,
        "replay_scope": {"scope": "single-input"},
    }
    values.update(overrides)
    return ReplayIdentity(**values)


def _legacy_input(**overrides):
    values = {
        "decision_intent": _intent(),
        "authorization_observation": _authorization(),
        "execution_observation": _execution(),
        "simulation_configuration": _configuration(),
        "initial_paper_state": _state(),
        "simulation_reference_time": REFERENCE,
        "replay_identity": _replay(),
        "contract_version": P07_T01_LEGACY_CONTRACT_VERSION,
    }
    values.update(overrides)
    return PaperSimulationInput(**values)


def _input(**overrides):
    intent = _risk_intent()
    authorization = evaluate_paper_risk_capital_authorization(
        intent,
        _risk_policy(intent),
    )
    reference = intent.context.reference_time
    values = {
        "decision_intent": intent,
        "authorization_observation": AuthorizationObservation.from_risk_capital_result(
            authorization
        ),
        "execution_observation": _execution(
            observation_time=reference - timedelta(seconds=10),
            availability_time=reference - timedelta(seconds=5),
        ),
        "simulation_configuration": _configuration(),
        "initial_paper_state": _state(
            as_of_time=reference - timedelta(seconds=20),
        ),
        "simulation_reference_time": reference,
        "replay_identity": _replay(),
        "contract_version": P07_T01_CONTRACT_VERSION,
    }
    values.update(overrides)
    return PaperSimulationInput(**values)


def _approved_linked_input():
    intent = _risk_intent()
    authorization = evaluate_paper_risk_capital_authorization(
        intent,
        _risk_policy(intent),
    )
    reference = intent.context.reference_time
    observation = AuthorizationObservation.from_risk_capital_result(authorization)
    return _input(
        decision_intent=intent,
        authorization_observation=observation,
        execution_observation=_execution(
            observation_time=reference - timedelta(seconds=10),
            availability_time=reference - timedelta(seconds=5),
        ),
        initial_paper_state=_state(
            as_of_time=reference - timedelta(seconds=20),
        ),
        simulation_reference_time=reference,
        contract_version=P07_T01_CONTRACT_VERSION,
    ), authorization


def test_valid_input_is_immutable_and_provider_neutral():
    value = _input()

    assert value.contract_version == "p07-t01-v2"
    assert value.authorization_observation.authorization_reference is not None
    assert len(value.digest) == 64
    assert value.decision_intent.intent.is_decision is True
    assert value.decision_intent.intent.is_authorization is False
    assert value.decision_intent.intent.is_order is False
    with pytest.raises(FrozenInstanceError):
        value.simulation_reference_time = REFERENCE
    with pytest.raises(TypeError):
        value.execution_observation.source_provenance["x"] = "y"


def test_p06_digest_identity_and_version_mismatches_are_rejected():
    intent = _intent()
    with pytest.raises(ValueError, match="decision_intent_digest"):
        _legacy_input(
            decision_intent=type(_input().decision_intent)(
                intent,
                decision_intent_digest="0" * 64,
            )
        )
    with pytest.raises(ValueError, match="p06_t01_ruleset_version"):
        type(_input().decision_intent)(
            intent,
            p06_t01_ruleset_version="unsupported",
        )
    assert _legacy_input(
        decision_intent=intent
    ).decision_intent.context_digest == intent.context_digest


@pytest.mark.parametrize("status", [ObservationStatus.FAIL, ObservationStatus.UNKNOWN])
def test_authorization_fail_and_unknown_are_preserved_and_fail_closed(status):
    kwargs = {"status": status}
    if status is ObservationStatus.UNKNOWN:
        kwargs["unknown_reasons"] = ("authorization unavailable",)
    observation = _authorization(**kwargs)
    assert observation.status is status
    with pytest.raises(ValueError):
        _legacy_input(authorization_observation=observation)


def test_authorization_not_required_is_explicit():
    value = _legacy_input(
        authorization_observation=_authorization(
            status=ObservationStatus.NOT_REQUIRED,
            valid_until=REFERENCE + timedelta(minutes=5),
        )
    )
    assert value.authorization_observation.status is ObservationStatus.NOT_REQUIRED


def test_linked_approval_reference_is_immutable_and_canonical():
    value, authorization = _approved_linked_input()
    reference = value.authorization_observation.authorization_reference

    assert isinstance(reference, RiskCapitalAuthorizationReference)
    assert reference.authorization_id == authorization.authorization_id
    assert reference.authorization_digest == authorization.digest
    with pytest.raises(FrozenInstanceError):
        reference.authorization_digest = "0" * 64
    with pytest.raises(TypeError):
        reference.scope_identity["changed"] = True


def test_missing_mismatched_and_tampered_approval_linkage_fails_closed():
    linked, authorization = _approved_linked_input()
    with pytest.raises(ValueError, match="MISSING_REQUIRED_INPUT"):
        _input(
            decision_intent=linked.decision_intent.intent,
            authorization_observation=linked.authorization_observation.with_authorization_reference(
                None
            ),
            execution_observation=linked.execution_observation,
            initial_paper_state=linked.initial_paper_state,
            simulation_reference_time=linked.simulation_reference_time,
            contract_version=P07_T01_CONTRACT_VERSION,
        )

    mismatched_intent = _risk_intent(
        expected_edge_assumptions=("different paper admission",),
    )
    mismatched = RiskCapitalAuthorizationReference.from_authorization_result(
        evaluate_paper_risk_capital_authorization(
            mismatched_intent,
            _risk_policy(mismatched_intent),
        )
    )
    with pytest.raises(ValueError, match="does not match observation"):
        linked.authorization_observation.with_authorization_reference(mismatched)

    tampered = linked.authorization_observation.authorization_reference
    object.__setattr__(tampered, "authorization_digest", "0" * 64)
    with pytest.raises(ValueError, match="authorization_reference|digest"):
        PaperSimulationInput(
            decision_intent=linked.decision_intent.intent,
            authorization_observation=linked.authorization_observation,
            execution_observation=linked.execution_observation,
            simulation_configuration=linked.simulation_configuration,
            initial_paper_state=linked.initial_paper_state,
            simulation_reference_time=linked.simulation_reference_time,
            replay_identity=linked.replay_identity,
            contract_version=P07_T01_CONTRACT_VERSION,
            input_digest=linked.digest,
        )


def test_pass_authorization_requires_validity_and_execution_state_quality():
    with pytest.raises(ValueError, match="valid_until"):
        AuthorizationObservation(
            observation_id="auth-invalid",
            status=ObservationStatus.PASS,
            scope_identity={"candidate_id": "candidate-1"},
            observed_at=REFERENCE,
            valid_from=REFERENCE,
            valid_until=None,
            contract_version="risk-auth-v1",
            risk_governor_version="risk-governor-v1",
            capital_authorization_version="capital-auth-v1",
        )
    with pytest.raises(ValueError, match="valid_until"):
        _authorization(valid_until=REFERENCE - timedelta(minutes=3))
    with pytest.raises(ValueError, match="execution observation"):
        _legacy_input(execution_observation=_execution(quality=ObservationQuality.INVALID))
    with pytest.raises(ValueError, match="initial paper state"):
        _legacy_input(initial_paper_state=_state(state_quality=ObservationQuality.FAIL))


def test_nested_digest_validation_and_unknown_fields():
    with pytest.raises(ValueError, match="observation_digest"):
        _execution(observation_digest="0" * 64)
    with pytest.raises(ValueError, match="configuration_digest"):
        _configuration(configuration_digest="0" * 64)
    with pytest.raises(ValueError, match="state_digest"):
        _state(state_digest="0" * 64)
    with pytest.raises(ValueError, match="unsupported PaperSimulationInput fields"):
        PaperSimulationInput.from_mapping({"unexpected": True})


def test_canonicalization_and_digest_are_stable():
    first = _input()
    second = _input(
        execution_observation=_execution(
            subject_identity={"token_identity": "token-1"},
            source_provenance={"source": "fixture"},
            observation_time=first.simulation_reference_time - timedelta(seconds=10),
            availability_time=first.simulation_reference_time - timedelta(seconds=5),
        )
    )
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest
    assert first.deterministic_representation == first.canonical_representation
    assert "0.75" not in str(first.canonical_representation)


def test_timestamp_and_decimal_canonicalization_helpers_are_deterministic():
    first = _configuration(configuration_provenance={"value": Decimal("1.00")})
    second = _configuration(configuration_provenance={"value": Decimal("1")})
    assert first.configuration_digest == second.configuration_digest
    assert first.canonical_representation["configuration_provenance"]["value"] == "1"


@pytest.mark.parametrize(
    "field",
    ["simulation_reference_time", "execution_observation", "initial_paper_state"],
)
def test_future_data_is_rejected(field):
    if field == "simulation_reference_time":
        value = _input()
        with pytest.raises(ValueError, match="future"):
            _input(
                simulation_reference_time=value.simulation_reference_time
                - timedelta(minutes=1)
            )
    elif field == "execution_observation":
        with pytest.raises(ValueError, match="future"):
            _input(
                execution_observation=_execution(
                    observation_time=REFERENCE + timedelta(seconds=1),
                    availability_time=REFERENCE + timedelta(seconds=2),
                )
            )
    else:
        with pytest.raises(ValueError, match="future"):
            _input(initial_paper_state=_state(as_of_time=REFERENCE + timedelta(seconds=1)))


def test_replay_is_deterministic_and_clock_independent():
    first = _input()
    second = _input()
    assert first.replay_identity.replay_id == second.replay_identity.replay_id
    assert first.digest == second.digest