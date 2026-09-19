from datetime import datetime, timezone

import pytest

from core.risk.goplus_token_safety import (
    GoPlusSafetyError,
    ProviderResponse,
    compose_safety_assessment,
    fetch_goplus_token_security,
)


UTC = timezone.utc
ASSESSMENT_TIME = datetime(2026, 9, 18, 3, 0, tzinfo=UTC)


def _provider(payload: dict) -> ProviderResponse:
    return ProviderResponse(
        endpoint=(
            "https://api.gopluslabs.io/api/v1/token_security/1"
            "?contract_addresses=0xabc"
        ),
        status_code=200,
        response_bytes=512,
        received_at=ASSESSMENT_TIME,
        payload=payload,
    )


def _payload(record: dict | None = None, *, token: str = "0xabc") -> dict:
    return {
        "code": 1,
        "message": "OK",
        "result": {token: record or {}},
    }


def test_normal_response_composes_through_p03_and_keeps_favorable_flags_unknown():
    result = compose_safety_assessment(
        chain_id="ethereum",
        token_address="0xabc",
        provider=_provider(
            _payload(
                {
                    "is_open_source": "1",
                    "is_proxy": "0",
                    "is_mintable": "0",
                    "is_freezable": "0",
                    "is_honeypot": "0",
                    "cannot_sell_all": "0",
                    "is_blacklisted": "0",
                    "is_whitelisted": "0",
                    "is_airdrop_scam": "0",
                }
            )
        ),
        assessment_time=ASSESSMENT_TIME,
    )

    assert result["identity"] == {"chain_id": "ethereum", "token_address": "0xabc"}
    assert result["evaluation"]["status"] == "UNKNOWN"
    assert set(result["evaluation"]["domain_results"].values()) == {"UNKNOWN"}
    assert all(
        item["status"] == "UNKNOWN" for item in result["evidence"]
    )
    assert result["source"]["source_observed_at"] is None
    assert any(
        "does not document a source observation timestamp" in limitation
        for limitation in result["limitations"]
    )


def test_explicit_provider_risk_flag_is_fail_closed():
    result = compose_safety_assessment(
        chain_id="ethereum",
        token_address="0xabc",
        provider=_provider(_payload({"is_honeypot": "1"})),
        assessment_time=ASSESSMENT_TIME,
    )

    honeypot = next(
        item
        for item in result["evidence"]
        if item["evidence_context"]["provider_field"] == "is_honeypot"
    )
    assert honeypot["status"] == "FAIL"
    assert result["evaluation"]["domain_results"]["TRADABILITY_SELLABILITY"] == "FAIL"
    assert result["evaluation"]["status"] == "INELIGIBLE"


def test_incomplete_response_preserves_unknown_evidence():
    result = compose_safety_assessment(
        chain_id="ethereum",
        token_address="0xabc",
        provider=_provider(_payload()),
        assessment_time=ASSESSMENT_TIME,
    )

    assert result["evaluation"]["status"] == "UNKNOWN"
    assert all(item["status"] == "UNKNOWN" for item in result["evidence"])
    assert any(
        item["reason_codes"] == ["MISSING_PROVIDER_FIELD"]
        for item in result["evidence"]
    )


def test_malformed_and_contradictory_identity_responses_fail_closed():
    with pytest.raises(GoPlusSafetyError, match="invalid token-security result"):
        compose_safety_assessment(
            chain_id="ethereum",
            token_address="0xabc",
            provider=_provider({"code": 1, "result": []}),
            assessment_time=ASSESSMENT_TIME,
        )

    with pytest.raises(GoPlusSafetyError, match="different identity"):
        compose_safety_assessment(
            chain_id="ethereum",
            token_address="0xabc",
            provider=_provider(_payload({}, token="0xdef")),
            assessment_time=ASSESSMENT_TIME,
        )


def test_unsupported_chain_is_rejected_before_provider_access():
    with pytest.raises(GoPlusSafetyError) as error:
        compose_safety_assessment(
            chain_id="solana",
            token_address="mint",
            provider=_provider(_payload()),
            assessment_time=ASSESSMENT_TIME,
        )
    assert error.value.code == "UNSUPPORTED_CHAIN"


def test_provider_errors_and_timeout_are_sanitized():
    class ProviderErrorResponse:
        status = 502

        def __init__(self):
            self._read = False

        def read(self, _limit):
            if self._read:
                return b""
            self._read = True
            return b'{"not": "a response"}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def opener(*_args, **_kwargs):
        return ProviderErrorResponse()

    with pytest.raises(GoPlusSafetyError) as error:
        fetch_goplus_token_security(
            "ethereum",
            "0xabc",
            opener=opener,
            received_at=lambda: ASSESSMENT_TIME,
        )
    assert error.value.code == "PROVIDER_HTTP_ERROR"
    assert error.value.status_code == 502

    def timeout(*_args, **_kwargs):
        raise TimeoutError("provider timeout")

    with pytest.raises(GoPlusSafetyError) as error:
        fetch_goplus_token_security(
            "ethereum",
            "0xabc",
            opener=timeout,
            received_at=lambda: ASSESSMENT_TIME,
        )
    assert error.value.code == "PROVIDER_TIMEOUT"