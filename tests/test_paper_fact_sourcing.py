"""Focused offline P07-PFS-01 checks; real canonical RTI-11 fixture, no I/O."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
from backend.application.paper_fact_sourcing import (
    GenesisPaperDeclaration,
    PaperFactSourcingOutcome,
    PaperFactSourcingRequest,
    PaperFactSourcingService,
    PaperSimulationAssumptionPolicy,
    PaperSimulationMode,
)
from core.execution.paper_fill_outcome import P07_T02_FILL_MODEL_VERSION, P07_T02_FRICTION_MODEL_VERSION, TradeSide
from core.execution.paper_position_exposure_state import StateQuality
from core.execution.paper_simulation_input import (
    ExecutionObservation, ObservationQuality, ObservationStatus, ReplayIdentity, SimulationConfigurationIdentity,
)
from core.runtime.controlled_paper_lifecycle import PaperFillInstruction, PaperLifecycleEvidence
from tests.test_market_to_opportunity_composition import _produced, _request
from tests.test_coingecko_onchain_ohlcv import POOL, TOKEN


def _rti11():
    produced = _produced()
    return MarketToOpportunityCompositionService(controlled_diagnostic=lambda **_: produced).compose(_request())


def _policy(**changes):
    result = dict(
        policy_id="paper-policy:one", policy_version="paper-policy-v1",
        mode=PaperSimulationMode.FRESH_GENESIS, side=TradeSide.BUY, requested_quantity=Decimal("2"),
        quantity_unit="TOKEN", price_unit="USD_PER_TOKEN", fee_unit="USD", quote_currency="USD",
        reference_price_rule="OBSERVED_CLOSE_PROXY", quantity_rounding_rule="EXACT_DECIMAL_18",
        simulated_fill_time=_request().reference_time + timedelta(seconds=1),
        simulated_capacity=Decimal("3"), allow_partial_fill=False,
        friction_values={key: Decimal("0") for key in ("fees", "spread", "slippage", "price_impact",
                                                          "quote_drift", "priority_fees", "mev_adverse_ordering")},
        valuation_max_age_seconds=Decimal("300"), accounting_fee=Decimal("0"),
        accounting_priority_fee=Decimal("0"), accounting_observed_at=_request().reference_time,
        accounting_contract_version="paper-accounting-policy-v1",
        ledger_stream_identity={"stream_id": "paper:one", "replay_id": "paper:replay:one",
                                "state_id": "paper-state:one", "candidate_id": "candidate:caller-owned:1",
                                "chain_id": "solana", "token_identity": TOKEN, "pool_address": POOL},
        sequence_number=1, previous_entry_digest=None, expectation_id="paper:expectation:one",
        expectation_fields=("sequence_number", "replay_id", "prior_state_digest", "expected_ledger_reference_time",
                            "expected_presence"),
        fill_model_version=P07_T02_FILL_MODEL_VERSION, friction_model_version=P07_T02_FRICTION_MODEL_VERSION,
        provenance={"source": "controller:simulation-policy:one"},
    )
    result.update(changes)
    return PaperSimulationAssumptionPolicy(**result)


def _request_pfs(**changes):
    rti11 = changes.pop("rti11_result", _rti11())
    selected = rti11.diagnostic.diagnostic.market.observations[-1]
    target = rti11.request.target
    asset = {"chain_id": target.chain_id, "token_identity": target.token_mint}
    ref = rti11.request.reference_time
    result = dict(
        rti11_result=rti11,
        execution_observation=ExecutionObservation(
            "paper:execution-observation", asset, ref - timedelta(seconds=10), ref - timedelta(seconds=5),
            ObservationQuality.PASS, None, None, None, ObservationStatus.PASS, "paper-observation-v1",
            {"source": "explicit:controller", "meaning": "paper-only"}, "paper:observation:replay"),
        simulation_configuration=SimulationConfigurationIdentity(
            "paper:config", "paper-config-v1", "paper-simulation-v1", P07_T02_FILL_MODEL_VERSION,
            P07_T02_FRICTION_MODEL_VERSION, "failure-policy-v1", "seed-policy-v1", {"source": "controller"}),
        replay_identity=ReplayIdentity("paper:replay:one", "paper-replay-v1", "seed:one", None, {"scope": "paper"}),
        simulation_reference_time=ref + timedelta(seconds=2), paper_evaluation_time=ref + timedelta(seconds=3),
        source_observation_id=selected.observation_id, source_observation_fingerprint=selected.fingerprint,
        target_asset_identity=asset, policy=_policy(),
        genesis=GenesisPaperDeclaration("paper-state:one", "paper-state-v1", {"portfolio": "paper:one"},
                                        asset, ref - timedelta(seconds=20), Decimal("0"), Decimal("0"),
                                        {"source": "controller:genesis-declaration"}),
        prior_state=None, initial_state_identity=None,
    )
    result.update(changes)
    return PaperFactSourcingRequest(**result)


def test_materializes_exact_inputs_and_preserves_observed_vs_assumed_provenance():
    request = _request_pfs()
    result = PaperFactSourcingService().source(request)
    assert result.outcome is PaperFactSourcingOutcome.FACTS_MATERIALIZED
    assert isinstance(result.fill_instruction, PaperFillInstruction)
    assert isinstance(result.lifecycle_evidence, PaperLifecycleEvidence)
    fill, evidence = result.fill_instruction, result.lifecycle_evidence
    observation = request.rti11_result.diagnostic.diagnostic.market.observations[-1]
    assert fill.reference_quote_price == Decimal(observation.value)
    assert fill.quote_observation_time == observation.observation_time + timedelta(minutes=1)
    assert fill.executable_liquidity == request.policy.simulated_capacity
    assert fill.friction.evidence["origin"] == "explicit_simulation_assumption"
    assert evidence.valuation_context.observations[0].source_provenance["origin"] == "observed_historical_USD_close_proxy"
    assert evidence.valuation_context.observations[0].availability_time == observation.received_time
    assert evidence.accounting_context.provenance["origin"] == "explicit_simulation_assumption"
    assert evidence.prior_state.positions[0].quantity == Decimal("0")
    assert evidence.prior_state.positions[0].position_quality is StateQuality.PASS
    assert result.initial_state_identity.state_provenance["prior_state_digest"] == evidence.prior_state.digest
    assert evidence.reconciliation_expectation.expected_fields["prior_state_digest"] == evidence.prior_state.digest
    assert "entry_id" not in evidence.reconciliation_expectation.expected_fields
    assert result.result_digest == PaperFactSourcingService().source(request).result_digest
    assert evidence is not PaperFactSourcingService().source(request).lifecycle_evidence


def test_changed_policy_and_market_source_change_digest():
    request = _request_pfs()
    first = PaperFactSourcingService().source(request)
    altered = replace(request, policy=_policy(simulated_capacity=Decimal("4")))
    assert PaperFactSourcingService().source(altered).result_digest != first.result_digest
    source = request.rti11_result.diagnostic.diagnostic.market.observations[0]
    different = replace(request, source_observation_id=source.observation_id,
                        source_observation_fingerprint=source.fingerprint)
    assert PaperFactSourcingService().source(different).result_digest != first.result_digest


@pytest.mark.parametrize("policy_change,outcome", [
    ({"simulated_capacity": None}, PaperFactSourcingOutcome.CAPACITY_UNAVAILABLE),
    ({"simulated_capacity": Decimal("1")}, PaperFactSourcingOutcome.CAPACITY_UNAVAILABLE),
    ({"friction_values": None}, PaperFactSourcingOutcome.SOURCING_UNAVAILABLE),
    ({"expectation_fields": None}, PaperFactSourcingOutcome.EXPECTATION_UNAVAILABLE),
    ({"valuation_max_age_seconds": Decimal("1")}, PaperFactSourcingOutcome.MARKET_EVIDENCE_UNAVAILABLE),
])
def test_missing_assumption_or_stale_observation_refuses_without_partial_output(policy_change, outcome):
    result = PaperFactSourcingService().source(_request_pfs(policy=_policy(**policy_change)))
    assert result.outcome is outcome
    assert result.fill_instruction is result.lifecycle_evidence is result.initial_state_identity is None


def test_explicit_partial_capacity_remains_only_an_assumption():
    result = PaperFactSourcingService().source(_request_pfs(policy=_policy(
        simulated_capacity=Decimal("1"), allow_partial_fill=True)))
    assert result.outcome is PaperFactSourcingOutcome.FACTS_MATERIALIZED
    assert result.fill_instruction.executable_liquidity == Decimal("1")


def test_existing_state_projection_and_sell_inventory():
    first = PaperFactSourcingService().source(_request_pfs())
    request = _request_pfs(policy=_policy(mode=PaperSimulationMode.EXISTING_EXPLICIT_STATE,
                                          sequence_number=2, previous_entry_digest="a" * 64),
                           genesis=None, prior_state=first.lifecycle_evidence.prior_state,
                           initial_state_identity=first.initial_state_identity)
    assert PaperFactSourcingService().source(request).outcome is PaperFactSourcingOutcome.FACTS_MATERIALIZED
    assert PaperFactSourcingService().source(replace(request, policy=replace(request.policy, side=TradeSide.SELL))).outcome is PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE
    bad = replace(request.initial_state_identity, position_state_digest="b" * 64, state_digest=None)
    with pytest.raises(ValueError, match="projection"):
        PaperFactSourcingService().source(replace(request, initial_state_identity=bad))


def test_validation_missing_genesis_and_no_hidden_default():
    request = _request_pfs()
    assert PaperFactSourcingService().source(replace(request, genesis=None)).outcome is PaperFactSourcingOutcome.PRIOR_STATE_UNAVAILABLE
    with pytest.raises(ValueError, match="finite positive"):
        _policy(simulated_capacity=Decimal("-1"))
    with pytest.raises(ValueError, match="seven friction"):
        _policy(friction_values={"fees": Decimal("0")})
    with pytest.raises(ValueError, match="source observation"):
        PaperFactSourcingService().source(replace(request, source_observation_fingerprint="f" * 64))
    with pytest.raises(ValueError, match="identity mismatch"):
        replace(request, target_asset_identity={"chain_id": "solana", "token_identity": "other"})
    with pytest.raises(ValueError, match="ledger stream"):
        PaperFactSourcingService().source(replace(request, policy=_policy(
            ledger_stream_identity={"stream_id": "paper:one", "replay_id": "wrong"})))
    with pytest.raises(ValueError, match="timeline"):
        PaperFactSourcingService().source(replace(request, policy=_policy(
            simulated_fill_time=request.execution_observation.observation_time)))


def test_owner_valueerror_and_tampering_remain_validation_failures():
    request = _request_pfs()
    altered_execution = replace(request.execution_observation, observation_id="changed", observation_digest=None)
    object.__setattr__(altered_execution, "observation_digest", request.execution_observation.observation_digest)
    with pytest.raises(ValueError, match="noncanonical execution_observation"):
        replace(request, execution_observation=altered_execution)
    with pytest.raises(ValueError, match="accounting assumptions"):
        PaperFactSourcingService().source(replace(request, policy=_policy(accounting_fee=Decimal("1"))))


def test_non_composed_upstream_and_missing_source_stop_before_fact_construction():
    from backend.application.market_to_opportunity_composition import (
        MarketToOpportunityCompositionOutcome, P01Rti11CompositionResult,
    )
    request = _request_pfs()
    unavailable = P01Rti11CompositionResult(request.rti11_result.request,
                                            MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE,
                                            ("CANONICAL_COMPOSITION_UNAVAILABLE",))
    result = PaperFactSourcingService().source(replace(request, rti11_result=unavailable))
    assert result.outcome is PaperFactSourcingOutcome.UPSTREAM_NOT_COMPOSED
    assert PaperFactSourcingService().source(replace(request, source_observation_id="missing")).outcome is PaperFactSourcingOutcome.MARKET_EVIDENCE_UNAVAILABLE


def test_no_owner_or_provider_invocation(monkeypatch):
    import core.execution.paper_fill_outcome as fill_owner
    import core.execution.paper_position_exposure_state as state_owner
    import core.execution.paper_ledger as ledger_owner
    import core.execution.paper_reconciliation as reconcile_owner
    import core.runtime.controlled_paper_lifecycle as lifecycle_owner
    import backend.application.one_shot_controlled_paper_caller as osc_owner
    for module, name in ((fill_owner, "evaluate_paper_fill"), (state_owner, "transition_paper_state"),
                         (ledger_owner, "create_paper_ledger_entry"), (reconcile_owner, "reconcile_paper_ledger"),
                         (lifecycle_owner, "run_controlled_paper_lifecycle")):
        monkeypatch.setattr(module, name, lambda *args, **kwargs: pytest.fail("outcome owner invoked"))
    monkeypatch.setattr(osc_owner.OneShotControlledPaperCaller, "run", lambda *args, **kwargs: pytest.fail("OSC invoked"))
    assert PaperFactSourcingService().source(_request_pfs()).outcome is PaperFactSourcingOutcome.FACTS_MATERIALIZED


def test_exact_products_are_accepted_by_existing_osc_request_constructor_without_running_it():
    from tests.test_one_shot_controlled_paper_caller import _request as osc_request
    source_request = _request_pfs()
    sourced = PaperFactSourcingService().source(source_request)
    compatible = replace(osc_request(), rti11_result=source_request.rti11_result,
                         execution_observation=source_request.execution_observation,
                         simulation_configuration=source_request.simulation_configuration,
                         initial_paper_state=sourced.initial_state_identity,
                         replay_identity=source_request.replay_identity,
                         fill_instruction=sourced.fill_instruction,
                         lifecycle_evidence=sourced.lifecycle_evidence)
    assert compatible.fill_instruction is sourced.fill_instruction
    assert compatible.lifecycle_evidence is sourced.lifecycle_evidence
