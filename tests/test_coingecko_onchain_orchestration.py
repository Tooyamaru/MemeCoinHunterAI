from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from typing import Iterator, Mapping

import pytest

from core.data.coingecko_onchain_diagnostic import run_ohlcv_diagnostic
from core.data.coingecko_onchain_ohlcv import (
    OhlcvOutcome,
    OhlcvResponse,
    OhlcvResult,
)
from core.data.coingecko_onchain_orchestration import (
    ControlledDiagnosticOutcome,
    ControlledDiagnosticResult,
    ExactPoolDiagnosticTarget,
    run_controlled_ohlcv_diagnostic,
)
from core.data.contracts import FreshnessPolicy
from core.signals.price_direction_policy import PriceDirectionResult
from tests.test_coingecko_onchain_ohlcv import (
    FIXTURE,
    FRESHNESS,
    POOL,
    QUOTE,
    REFERENCE,
    TOKEN,
    predecessor,
)
from tests.test_coingecko_onchain_transport import clock


REFERENCE_DIGEST = "a" * 64
SECRET = "orchestration-test-key"


def target(**changes: object) -> ExactPoolDiagnosticTarget:
    return replace(
        ExactPoolDiagnosticTarget(
            chain_id="solana",
            token_mint=TOKEN,
            pool_address=POOL,
            base_mint=TOKEN,
            quote_mint=QUOTE,
            target_reference_id="inspection:solana:pool-v1",
            target_reference_digest=REFERENCE_DIGEST,
            target_contract_version="exact-pool-target-v1",
        ),
        **changes,
    )


def nested(outcome: OhlcvOutcome = OhlcvOutcome.SOURCE_UNAVAILABLE) -> PriceDirectionResult:
    return PriceDirectionResult(OhlcvResult(outcome, (outcome.value,), False, None))


def run(**changes: object) -> ControlledDiagnosticResult:
    arguments = {
        "target": target(),
        "predecessor": predecessor(),
        "reference_time": REFERENCE,
        "timeout": timedelta(seconds=10),
        "max_response_bytes": 16_384,
        "freshness_policy": FRESHNESS,
        "environment": {"COINGECKO_DEMO_API_KEY": SECRET},
        "diagnostic": lambda **kwargs: nested(),
    }
    arguments.update(changes)
    return run_controlled_ohlcv_diagnostic(**arguments)


def test_exact_target_builds_exact_request_and_invokes_diagnostic_once() -> None:
    calls: list[dict[str, object]] = []
    expected = nested(OhlcvOutcome.TIMEOUT)

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        calls.append(kwargs)
        return expected

    selected = target()
    upstream = predecessor()
    environment = {"COINGECKO_DEMO_API_KEY": SECRET}
    result = run(
        target=selected,
        predecessor=upstream,
        environment=environment,
        diagnostic=diagnostic,
    )

    assert result.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
    assert result.reason_codes == ("DIAGNOSTIC_INVOKED",)
    assert result.target is selected
    assert result.target.target_reference_digest == REFERENCE_DIGEST
    assert result.diagnostic is expected
    assert len(calls) == 1
    assert calls[0]["predecessor"] is upstream
    assert calls[0]["environment"] is environment
    request = calls[0]["request"]
    assert request == result.request
    assert request.chain_id == selected.chain_id
    assert request.token_mint == selected.token_mint
    assert request.pool_address == selected.pool_address
    assert request.base_mint == selected.base_mint
    assert request.quote_mint == selected.quote_mint
    assert request.reference_time == REFERENCE
    assert request.timeout == timedelta(seconds=10)
    assert request.max_response_bytes == 16_384


class ExplodingEnvironment(Mapping[str, str]):
    def __getitem__(self, key: str) -> str:
        raise AssertionError("credential must not be read")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("environment must not be inspected")

    def __len__(self) -> int:
        raise AssertionError("environment must not be inspected")


def test_non_current_candidate_stops_before_secret_and_diagnostic() -> None:
    calls = 0

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        nonlocal calls
        calls += 1
        raise AssertionError("diagnostic must not run")

    result = run(
        predecessor=predecessor(QUOTE),
        environment=ExplodingEnvironment(),
        diagnostic=diagnostic,
    )

    assert result.outcome is ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT
    assert result.reason_codes == ("TOKEN_NOT_CURRENT",)
    assert result.request is not None
    assert result.diagnostic is None
    assert calls == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_reference_id", ""),
        ("target_reference_id", "bad value"),
        ("target_reference_id", "x" * 257),
        ("target_reference_digest", "A" * 64),
        ("target_reference_digest", "a" * 63),
        ("target_contract_version", ""),
        ("target_contract_version", "bad/version"),
        ("target_contract_version", "x" * 65),
    ],
)
def test_invalid_target_reference_fails_before_diagnostic(field: str, value: str) -> None:
    calls = 0

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        nonlocal calls
        calls += 1
        return nested()

    result = run(target=target(**{field: value}), diagnostic=diagnostic)
    assert result.outcome is ControlledDiagnosticOutcome.INVALID_INPUT
    assert result.reason_codes == ("INVALID_TARGET_REFERENCE",)
    assert result.request is None
    assert calls == 0


@pytest.mark.parametrize(
    "selected",
    [
        target(chain_id="ethereum"),
        target(token_mint=POOL),
        target(pool_address="../pool"),
        target(base_mint=QUOTE),
        target(quote_mint=TOKEN),
    ],
)
def test_invalid_target_identity_or_composition_fails_before_diagnostic(
    selected: ExactPoolDiagnosticTarget,
) -> None:
    calls = 0

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        nonlocal calls
        calls += 1
        return nested()

    result = run(target=selected, diagnostic=diagnostic)
    assert result.outcome is ControlledDiagnosticOutcome.INVALID_INPUT
    assert result.reason_codes == ("INVALID_REQUEST",)
    assert calls == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"reference_time": REFERENCE.replace(tzinfo=None)},
        {"timeout": timedelta(0)},
        {"timeout": 10},
        {"max_response_bytes": 0},
        {"max_response_bytes": True},
        {"max_response_bytes": 1_048_577},
    ],
)
def test_invalid_request_limits_fail_before_diagnostic(changes: dict[str, object]) -> None:
    calls = 0

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        nonlocal calls
        calls += 1
        return nested()

    result = run(diagnostic=diagnostic, **changes)
    assert result.outcome is ControlledDiagnosticOutcome.INVALID_INPUT
    assert result.reason_codes == ("INVALID_REQUEST",)
    assert calls == 0


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"target": object()}, "EXACT_TARGET_REQUIRED"),
        ({"predecessor": object()}, "P02_PREDECESSOR_REQUIRED"),
        ({"freshness_policy": object()}, "EXPLICIT_FRESHNESS_REQUIRED"),
        ({"freshness_policy": FreshnessPolicy()}, "EXPLICIT_FRESHNESS_REQUIRED"),
        ({"diagnostic": object()}, "DIAGNOSTIC_CALLABLE_REQUIRED"),
        ({"clock": object()}, "CLOCK_CALLABLE_REQUIRED"),
        ({"environment": object()}, "ENVIRONMENT_MAPPING_REQUIRED"),
    ],
)
def test_invalid_boundary_inputs_fail_closed(
    changes: dict[str, object], reason: str,
) -> None:
    result = run(**changes)
    assert result.outcome is ControlledDiagnosticOutcome.INVALID_INPUT
    assert result.reason_codes == (reason,)
    assert result.diagnostic is None


@pytest.mark.parametrize("outcome", list(OhlcvOutcome))
def test_nested_diagnostic_outcome_is_never_reinterpreted(outcome: OhlcvOutcome) -> None:
    result = run(diagnostic=lambda **kwargs: nested(outcome))
    assert result.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
    assert result.diagnostic.outcome is outcome


def test_injected_clock_is_forwarded_without_orchestration_calling_it() -> None:
    calls = 0

    def injected_clock():
        nonlocal calls
        calls += 1
        return REFERENCE

    captured: dict[str, object] = {}

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        captured.update(kwargs)
        return nested()

    result = run(clock=injected_clock, diagnostic=diagnostic)
    assert result.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
    assert captured["clock"] is injected_clock
    assert calls == 0


def test_wrong_diagnostic_return_type_is_a_programming_error() -> None:
    with pytest.raises(TypeError, match="PriceDirectionResult"):
        run(diagnostic=lambda **kwargs: object())


def test_real_diagnostic_path_reaches_p02_and_p04_with_mocked_transport() -> None:
    started = REFERENCE + timedelta(seconds=1)
    received = REFERENCE + timedelta(seconds=2)
    evaluated = REFERENCE + timedelta(seconds=3)
    transport_calls = 0

    def transport(authenticated, *, clock):
        nonlocal transport_calls
        transport_calls += 1
        return OhlcvResponse(
            authenticated.request,
            started,
            received,
            FIXTURE.read_bytes(),
            200,
        )

    def diagnostic(**kwargs: object) -> PriceDirectionResult:
        return run_ohlcv_diagnostic(**kwargs, transport=transport)

    result = run(
        diagnostic=diagnostic,
        clock=clock(evaluated),
    )

    assert transport_calls == 1
    assert result.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
    assert result.diagnostic.outcome is OhlcvOutcome.PRODUCED
    assert result.diagnostic.signal_evidence.evidence[0].signal_status == "RISING"
    assert result.diagnostic.market.provenance.request == result.request
    assert all(
        item.reference_time == evaluated
        for item in result.diagnostic.market.observations
    )


def test_replay_is_deterministic_and_target_is_immutable() -> None:
    selected = target()
    left = run(target=selected)
    right = run(target=selected)
    assert left == right
    with pytest.raises(FrozenInstanceError):
        selected.pool_address = QUOTE


def test_result_invariants_reject_impossible_states() -> None:
    with pytest.raises(ValueError, match="target, request, and diagnostic"):
        ControlledDiagnosticResult(
            ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED,
            ("DIAGNOSTIC_INVOKED",),
            target(),
        )
    with pytest.raises(ValueError, match="cannot contain a diagnostic"):
        ControlledDiagnosticResult(
            ControlledDiagnosticOutcome.INVALID_INPUT,
            ("INVALID_INPUT",),
            target(),
            diagnostic=nested(),
        )
