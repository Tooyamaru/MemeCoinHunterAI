from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from backend.application.market_to_opportunity_composition import (
    P01_RTI_11_CONTRACT_VERSION,
    MarketToOpportunityCompositionOutcome,
    MarketToOpportunityCompositionService,
    P01Rti11CompositionRequest,
)
from core.data.coingecko_onchain_ohlcv import OhlcvOutcome, OhlcvResult
from core.data.coingecko_onchain_orchestration import (
    ControlledDiagnosticOutcome,
    ControlledDiagnosticResult,
    ExactPoolDiagnosticTarget,
)
from core.opportunity.p04_p05_composition import CanonicalP04ToP05Composition
from core.risk.safety_eligibility import derive_token_eligibility
from core.risk.safety_evaluation import P03_T02_CONTRACT_VERSION, SafetyEvaluationResult
from core.risk.safety_evidence import SafetyDomain, SafetyProvenance, SafetyStatus
from core.signals.price_direction_policy import PriceDirectionResult, derive_price_direction
from tests.test_coingecko_onchain_ohlcv import (
    FRESHNESS,
    POOL,
    QUOTE,
    REFERENCE,
    TOKEN,
    predecessor,
    request as ohlcv_request,
    response,
)


TARGET_DIGEST = "a" * 64


def _predecessor():
    return replace(
        predecessor(),
        materializer_contract_version="p02-t06-v1",
    )


def _target(**changes: object) -> ExactPoolDiagnosticTarget:
    return replace(
        ExactPoolDiagnosticTarget(
            chain_id="solana",
            token_mint=TOKEN,
            pool_address=POOL,
            base_mint=TOKEN,
            quote_mint=QUOTE,
            target_reference_id="caller:exact-pool:1",
            target_reference_digest=TARGET_DIGEST,
            target_contract_version="exact-pool-target-v1",
        ),
        **changes,
    )


def _evaluation(**changes: object) -> SafetyEvaluationResult:
    observed_at = REFERENCE - timedelta(minutes=5)
    values = {
        "chain_id": "solana",
        "token_identity": TOKEN,
        "input_evidence_digest": "b" * 64,
        "evaluation_timestamp": REFERENCE - timedelta(minutes=1),
        "contract_version": P03_T02_CONTRACT_VERSION,
        "domain_results": {SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS},
        "evidence_references": ("safety:evidence:1",),
        "reason_codes": ("PASS_EVIDENCE",),
        "provenance": (
            SafetyProvenance(
                source_id="bounded-safety-source",
                method="p03-fixture",
                observed_at=observed_at,
                metadata={"scope": "test"},
            ),
        ),
    }
    values.update(changes)
    return SafetyEvaluationResult(**values)


def _request(**changes: object) -> P01Rti11CompositionRequest:
    evaluation = changes.pop("safety_evaluation", _evaluation())
    values = {
        "candidate_id": "candidate:caller-owned:1",
        "predecessor": _predecessor(),
        "target": _target(),
        "safety_evaluation": evaluation,
        "eligibility": derive_token_eligibility(evaluation),
        "reference_time": REFERENCE,
        "timeout": timedelta(seconds=10),
        "max_response_bytes": 16_384,
        "freshness_policy": FRESHNESS,
        "processing_time": REFERENCE,
        "evaluated_at": REFERENCE,
        "evaluation_id": "rti-11-test",
        "analytical_context": {"caller": "focused-test"},
    }
    values.update(changes)
    return P01Rti11CompositionRequest(**values)


def _produced() -> ControlledDiagnosticResult:
    request = ohlcv_request()
    diagnostic = derive_price_direction(
        request=request,
        response=response(request),
        predecessor=_predecessor(),
        freshness_policy=FRESHNESS,
        evaluation_time=REFERENCE,
    )
    assert diagnostic.outcome is OhlcvOutcome.PRODUCED
    return ControlledDiagnosticResult(
        outcome=ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED,
        reason_codes=("DIAGNOSTIC_INVOKED",),
        target=_target(),
        request=request,
        diagnostic=diagnostic,
    )


def _nested_failure(
    outcome: OhlcvOutcome = OhlcvOutcome.SOURCE_UNAVAILABLE,
) -> ControlledDiagnosticResult:
    diagnostic = PriceDirectionResult(
        OhlcvResult(outcome, (outcome.value,), False, None)
    )
    return ControlledDiagnosticResult(
        outcome=ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED,
        reason_codes=("DIAGNOSTIC_INVOKED",),
        target=_target(),
        request=ohlcv_request(),
        diagnostic=diagnostic,
    )


def test_exact_success_delegates_once_and_preserves_all_canonical_inputs() -> None:
    controlled_calls: list[dict[str, object]] = []
    producer_calls: list[dict[str, object]] = []
    controlled_result = _produced()

    def controlled(**kwargs: object) -> ControlledDiagnosticResult:
        controlled_calls.append(kwargs)
        return controlled_result

    from core.opportunity.canonical_evidence_producer import (
        produce_canonical_p04_to_p05,
    )

    def producer(**kwargs: object) -> CanonicalP04ToP05Composition:
        producer_calls.append(kwargs)
        return produce_canonical_p04_to_p05(**kwargs)

    request = _request()
    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=controlled,
        canonical_producer=producer,
    ).compose(request)

    assert result.outcome is MarketToOpportunityCompositionOutcome.COMPOSED
    assert result.contract_version == P01_RTI_11_CONTRACT_VERSION
    assert result.reason_codes == ()
    assert result.diagnostic is controlled_result
    assert isinstance(result.composition, CanonicalP04ToP05Composition)
    assert result.composition.candidate.candidate_id == request.candidate_id
    assert result.composition.candidate.eligibility is request.eligibility
    assert len(controlled_calls) == 1
    assert len(producer_calls) == 1
    assert controlled_calls[0]["target"] is request.target
    assert controlled_calls[0]["predecessor"] is request.predecessor
    assert controlled_calls[0]["reference_time"] is request.reference_time
    assert controlled_calls[0]["freshness_policy"] is request.freshness_policy
    assert producer_calls[0]["candidate_id"] == request.candidate_id
    assert producer_calls[0]["eligibility"] is request.eligibility
    assert producer_calls[0]["signal_evidence"] is controlled_result.diagnostic.signal_evidence
    assert producer_calls[0]["market_observations"] is controlled_result.diagnostic.market.observations
    assert producer_calls[0]["processing_time"] is request.processing_time
    assert producer_calls[0]["evaluated_at"] is request.evaluated_at
    assert producer_calls[0]["evaluation_id"] == request.evaluation_id
    assert result.result_digest == result.digest
    assert len(result.result_digest) == 64


def test_token_not_current_is_preserved_without_producer_call() -> None:
    controlled = ControlledDiagnosticResult(
        outcome=ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT,
        reason_codes=("TOKEN_NOT_CURRENT",),
        target=_target(),
        request=ohlcv_request(),
    )
    producer_calls = 0

    def producer(**kwargs: object) -> CanonicalP04ToP05Composition:
        nonlocal producer_calls
        producer_calls += 1
        raise AssertionError("producer must not run")

    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: controlled,
        canonical_producer=producer,
    ).compose(_request())

    assert result.outcome is MarketToOpportunityCompositionOutcome.TOKEN_NOT_CURRENT
    assert result.diagnostic is controlled
    assert result.composition is None
    assert producer_calls == 0


@pytest.mark.parametrize(
    "controlled",
    [
        _nested_failure(),
        ControlledDiagnosticResult(
            outcome=ControlledDiagnosticOutcome.INVALID_INPUT,
            reason_codes=("INVALID_REQUEST",),
            target=_target(),
        ),
    ],
)
def test_bounded_nonproduction_never_calls_canonical_producer(
    controlled: ControlledDiagnosticResult,
) -> None:
    producer_calls = 0

    def producer(**kwargs: object) -> CanonicalP04ToP05Composition:
        nonlocal producer_calls
        producer_calls += 1
        raise AssertionError("producer must not run")

    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: controlled,
        canonical_producer=producer,
    ).compose(_request())

    assert result.outcome is MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED
    assert result.diagnostic is controlled
    assert producer_calls == 0


@pytest.mark.parametrize(
    ("controlled", "reason"),
    [
        (lambda **kwargs: object(), "CONTROLLED_DIAGNOSTIC_INVALID_RESULT"),
        (
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("private detail")),
            "CONTROLLED_DIAGNOSTIC_UNAVAILABLE",
        ),
    ],
)
def test_controlled_delegate_failure_is_safe_and_bounded(controlled, reason: str) -> None:
    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=controlled,
    ).compose(_request())

    assert result.outcome is MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE
    assert result.reason_codes == (reason,)
    assert "private detail" not in repr(result.canonical_representation)


def test_canonical_producer_failure_is_safe_and_bounded() -> None:
    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: _produced(),
        canonical_producer=lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("private producer detail")
        ),
    ).compose(_request())

    assert result.outcome is MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE
    assert result.reason_codes == ("CANONICAL_COMPOSITION_UNAVAILABLE",)
    assert "private producer detail" not in repr(result.canonical_representation)


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_id": ""},
        {"reference_time": REFERENCE.replace(tzinfo=None)},
        {"processing_time": REFERENCE.replace(tzinfo=None)},
        {"evaluated_at": REFERENCE.replace(tzinfo=None)},
        {"timeout": timedelta(0)},
        {"max_response_bytes": 0},
        {"contract_version": "p01-rti-11-v2"},
        {"target": _target(target_reference_digest="A" * 64)},
        {"target": _target(base_mint=QUOTE)},
        {"analytical_context": {"bad": object()}},
    ],
)
def test_malformed_input_is_validation_failure_before_delegation(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _request(**change)


@pytest.mark.parametrize(
    "evaluation_change",
    [
        {"chain_id": "ethereum"},
        {"token_identity": QUOTE},
        {"contract_version": "p03-t02-v2"},
        {"evaluation_timestamp": REFERENCE + timedelta(seconds=1)},
    ],
)
def test_p03_identity_version_and_time_mismatch_fail_before_delegation(
    evaluation_change: dict[str, object],
) -> None:
    evaluation = _evaluation(**evaluation_change)
    with pytest.raises(ValueError):
        _request(safety_evaluation=evaluation)


@pytest.mark.parametrize(
    "eligibility_change",
    [
        {"evaluator_id": "other-evaluator"},
        {"contract_version": "p03-t01-v1"},
        {"evaluated_at": REFERENCE - timedelta(minutes=2)},
        {"evidence_references": ("other",)},
    ],
)
def test_p03_paired_handoff_structural_mismatch_fails_before_delegation(
    eligibility_change: dict[str, object],
) -> None:
    evaluation = _evaluation()
    eligibility = replace(derive_token_eligibility(evaluation), **eligibility_change)
    with pytest.raises(ValueError):
        _request(safety_evaluation=evaluation, eligibility=eligibility)


def test_completed_but_tampered_provenance_is_not_success() -> None:
    produced = _produced()
    assert produced.diagnostic is not None
    market = produced.diagnostic.market
    tampered = replace(
        produced,
        diagnostic=replace(
            produced.diagnostic,
            market=replace(
                market,
                provenance=replace(market.provenance, provider_id="other-provider"),
            ),
        ),
    )
    producer_calls = 0

    def producer(**kwargs: object) -> CanonicalP04ToP05Composition:
        nonlocal producer_calls
        producer_calls += 1
        raise AssertionError("producer must not run")

    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: tampered,
        canonical_producer=producer,
    ).compose(_request())
    assert result.outcome is MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED
    assert producer_calls == 0


def test_controlled_result_identity_mismatch_is_safe_unavailable() -> None:
    mismatched = replace(_nested_failure(), target=_target(token_mint=QUOTE))
    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: mismatched,
    ).compose(_request())

    assert result.outcome is MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE
    assert result.reason_codes == ("CONTROLLED_DIAGNOSTIC_IDENTITY_MISMATCH",)
    assert result.diagnostic is None


def test_completed_but_wrong_signal_policy_is_not_success() -> None:
    produced = _produced()
    evidence = produced.diagnostic.signal_evidence.evidence[0]
    tampered_evidence = replace(
        evidence,
        provenance=replace(evidence.provenance, method="price-direction-v2"),
    )
    tampered = replace(
        produced,
        diagnostic=replace(
            produced.diagnostic,
            signal_evidence=replace(
                produced.diagnostic.signal_evidence,
                evidence=(tampered_evidence,),
            ),
        ),
    )
    result = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: tampered,
    ).compose(_request())
    assert result.outcome is MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED


def test_result_digest_is_deterministic_and_sensitive_to_explicit_time() -> None:
    service = MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: _nested_failure(OhlcvOutcome.TIMEOUT),
    )
    request = _request()
    first = service.compose(request)
    second = service.compose(request)
    changed = service.compose(
        _request(processing_time=REFERENCE + timedelta(seconds=1))
    )

    assert first == second
    assert first.result_digest == second.result_digest
    assert changed.result_digest != first.result_digest
    with pytest.raises(TypeError):
        request.analytical_context["caller"] = "mutated"


def test_environment_clock_and_diagnostic_are_forwarded_once_without_inspection() -> None:
    environment = {"COINGECKO_DEMO_API_KEY": "not-used-by-focused-test"}
    clock = lambda: REFERENCE
    diagnostic = lambda **kwargs: None
    calls: list[dict[str, object]] = []

    def controlled(**kwargs: object) -> ControlledDiagnosticResult:
        calls.append(kwargs)
        return _nested_failure()

    MarketToOpportunityCompositionService(
        environment=environment,
        clock=clock,
        diagnostic=diagnostic,
        controlled_diagnostic=controlled,
    ).compose(_request())

    assert len(calls) == 1
    assert calls[0]["environment"] is environment
    assert calls[0]["clock"] is clock
    assert calls[0]["diagnostic"] is diagnostic


def test_module_has_no_forbidden_runtime_or_downstream_imports() -> None:
    source = Path(
        "backend/application/market_to_opportunity_composition.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "sqlalchemy",
        "backend.core.database",
        "backend.core.repositories",
        "opportunity_record",
        "opportunity_record_history",
        "opportunity_context",
        "core.decision",
        "paper_lifecycle",
        "fastapi",
        "workers",
        "scheduler",
        "queue",
        "wallet",
        "execution",
        "broadcast",
        "settlement",
    )
    assert all(value not in source for value in forbidden)
    assert "while " not in source
    assert "for attempt" not in source


def test_exact_outcome_vocabulary_contains_no_economic_or_execution_semantics() -> None:
    assert tuple(value.value for value in MarketToOpportunityCompositionOutcome) == (
        "COMPOSED",
        "TOKEN_NOT_CURRENT",
        "DIAGNOSTIC_NOT_PRODUCED",
        "COMPOSITION_UNAVAILABLE",
    )
    assert not {
        "WIN",
        "LOSS",
        "BUY",
        "SELL",
        "PROFIT",
        "REALIZED",
        "SETTLED",
    }.intersection(value.value for value in MarketToOpportunityCompositionOutcome)
