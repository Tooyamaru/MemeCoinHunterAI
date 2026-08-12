from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from core.risk.safety_evaluation import (
    P03_T02_CONTRACT_VERSION,
    SafetyEvaluationResult,
)
from core.risk.safety_eligibility import (
    P03_T03_EVALUATOR_ID,
    REASON_ALL_DOMAINS_PASS,
    REASON_FAIL_DOMAIN,
    REASON_NO_DOMAIN_RESULT,
    REASON_UNKNOWN_DOMAIN,
    derive_token_eligibility,
)
from core.risk.safety_evidence import (
    EligibilityStatus,
    SafetyDomain,
    SafetyProvenance,
    SafetyStatus,
)


EVALUATION_TIMESTAMP = datetime(2026, 8, 12, 12, 1, tzinfo=timezone.utc)


def _evaluation(
    domain_results: dict[SafetyDomain, SafetyStatus],
    *,
    evidence_references: tuple[str, ...] = ("evidence-1",),
) -> SafetyEvaluationResult:
    return SafetyEvaluationResult(
        chain_id="solana",
        token_identity="mint-A",
        input_evidence_digest="digest",
        evaluation_timestamp=EVALUATION_TIMESTAMP,
        contract_version=P03_T02_CONTRACT_VERSION,
        domain_results=domain_results,
        evidence_references=evidence_references,
        reason_codes=("UPSTREAM_REASON",),
        provenance=tuple(
            SafetyProvenance(
                source_id=f"source-{index}",
                method="test-fixture",
                observed_at=EVALUATION_TIMESTAMP,
            )
            for index, _ in enumerate(evidence_references)
        ),
    )


def test_all_represented_pass_domains_are_eligible():
    result = derive_token_eligibility(
        _evaluation(
            {
                SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS,
                SafetyDomain.TOP_HOLDER_CONCENTRATION: SafetyStatus.PASS,
            }
        )
    )

    assert result.status is EligibilityStatus.ELIGIBLE
    assert result.reason_codes == (REASON_ALL_DOMAINS_PASS,)


def test_any_fail_domain_is_ineligible():
    result = derive_token_eligibility(
        _evaluation(
            {
                SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS,
                SafetyDomain.TOP_HOLDER_CONCENTRATION: SafetyStatus.FAIL,
            }
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE
    assert result.reason_codes == (REASON_FAIL_DOMAIN,)


def test_unknown_domain_blocks_eligibility():
    result = derive_token_eligibility(
        _evaluation(
            {
                SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS,
                SafetyDomain.TOP_HOLDER_CONCENTRATION: SafetyStatus.UNKNOWN,
            }
        )
    )

    assert result.status is EligibilityStatus.UNKNOWN
    assert result.reason_codes == (REASON_UNKNOWN_DOMAIN,)


def test_empty_domain_results_are_unknown():
    result = derive_token_eligibility(_evaluation({}))

    assert result.status is EligibilityStatus.UNKNOWN
    assert result.reason_codes == (REASON_NO_DOMAIN_RESULT,)


def test_fail_takes_precedence_over_unknown():
    result = derive_token_eligibility(
        _evaluation(
            {
                SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.FAIL,
                SafetyDomain.TOP_HOLDER_CONCENTRATION: SafetyStatus.UNKNOWN,
            }
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE
    assert result.reason_codes == (REASON_FAIL_DOMAIN,)


def test_timestamp_and_references_are_inherited_exactly():
    evaluation = _evaluation(
        {SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS},
        evidence_references=("first", "duplicate", "duplicate"),
    )

    result = derive_token_eligibility(evaluation)

    assert result.evaluated_at is evaluation.evaluation_timestamp
    assert result.evidence_references == evaluation.evidence_references
    assert result.contract_version == evaluation.contract_version
    assert result.evaluator_id == P03_T03_EVALUATOR_ID


def test_zero_evidence_references_remain_valid():
    result = derive_token_eligibility(
        _evaluation(
            {SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.UNKNOWN},
            evidence_references=(),
        )
    )

    assert result.evidence_references == ()


def test_repeated_derivation_is_deterministic():
    evaluation = _evaluation(
        {
            SafetyDomain.TOP_HOLDER_CONCENTRATION: SafetyStatus.PASS,
            SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS,
        }
    )

    first = derive_token_eligibility(evaluation)
    second = derive_token_eligibility(evaluation)

    assert first == second
    assert first.reason_codes == tuple(sorted(first.reason_codes))


def test_input_evaluation_is_not_mutated():
    evaluation = _evaluation(
        {SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS}
    )
    before = evaluation

    derive_token_eligibility(evaluation)

    assert evaluation == before
    assert evaluation.domain_results == before.domain_results
    assert evaluation.evidence_references == before.evidence_references
    assert evaluation.reason_codes == before.reason_codes


def test_output_is_immutable_and_non_authoritative():
    result = derive_token_eligibility(
        _evaluation({SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS})
    )

    with pytest.raises(FrozenInstanceError):
        result.status = EligibilityStatus.UNKNOWN
    with pytest.raises(FrozenInstanceError):
        result.reason_codes = ("changed",)

    assert result.is_authoritative is False
    assert not any(
        name in result.__dataclass_fields__
        for name in (
            "authorization",
            "buy",
            "sell",
            "trade_intent",
            "execution_permission",
            "wallet_action",
        )
    )


def test_non_evaluation_input_is_rejected():
    with pytest.raises(ValueError):
        derive_token_eligibility(object())
