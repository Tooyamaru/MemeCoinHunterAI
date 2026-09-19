from core.risk.safety_diagnostic_bridge import evaluate_supplied_safety


def _assessment(evidence):
    return {
        "identity": {"chain_id": "ethereum", "token_address": "0xabc"},
        "evaluation": {
            "evaluation_timestamp": "2026-09-18T03:00:00Z",
        },
        "evidence": evidence,
    }


def test_bridge_reuses_p03_evaluators_for_qualifying_evidence():
    result = evaluate_supplied_safety(
        _assessment(
            [
                {
                    "domain": "LIQUIDITY_QUALITY",
                    "status": "PASS",
                    "quality": "VALID",
                    "freshness_status": "VALID",
                    "observed_at": "2026-09-18T02:59:00Z",
                    "source_id": "fixture",
                    "method": "fixture",
                    "evidence_reference": "fixture:liquidity",
                    "evidence_context": {"observed": True},
                    "reason_codes": [],
                }
            ]
        )
    )

    assert result["status"] == "ELIGIBLE"
    assert result["evidence_references"] == ["fixture:liquidity"]
    assert result["domain_results"] == {"LIQUIDITY_QUALITY": "PASS"}


def test_bridge_fails_closed_for_unknown_evidence():
    result = evaluate_supplied_safety(
        _assessment(
            [
                {
                    "domain": "LIQUIDITY_QUALITY",
                    "status": "UNKNOWN",
                    "quality": "INCOMPLETE",
                    "freshness_status": "INCOMPLETE",
                    "observed_at": "2026-09-18T02:59:00Z",
                    "source_id": "fixture",
                    "method": "fixture",
                    "evidence_reference": "fixture:liquidity",
                    "evidence_context": {},
                    "reason_codes": ["UNAVAILABLE"],
                }
            ]
        )
    )

    assert result["status"] == "UNKNOWN"
    assert result["domain_results"] == {"LIQUIDITY_QUALITY": "UNKNOWN"}