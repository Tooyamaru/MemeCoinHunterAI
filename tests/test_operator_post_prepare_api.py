from contextlib import asynccontextmanager
from dataclasses import asdict
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.application.oaf_operator_prepare_invocation import (
    OafOperatorPrepareInvocationService,
)
from backend.core.config import Settings
from tests.test_oaf_operator_prepare_invocation import _intent
from tests.test_oaf_rti11_integration import _snapshot, _upstream
from tests.test_oaf_trusted_prepare import _command
from tests.test_paper_fact_sourcing import _rti11


TOKEN = "controller-secret-token-1234567890"


def _iso(value):
    return value.isoformat()


def _decimal(value):
    return format(Decimal(value), "f")


def _payload(rti11):
    command = _command(rti11)
    intent = _intent(rti11)
    seed = intent.policy_seed
    execution = intent.execution_observation
    config = intent.simulation_configuration
    replay = intent.replay_identity
    policy = intent.simulation_policy
    genesis = intent.genesis

    return {
        "candidate_id": command.candidate_id,
        "token_mint": command.token_mint,
        "target": {
            "chain_id": command.target.chain_id,
            "token_mint": command.target.token_mint,
            "pool_address": command.target.pool_address,
            "base_mint": command.target.base_mint,
            "quote_mint": command.target.quote_mint,
            "target_reference_id": command.target.target_reference_id,
            "target_reference_digest": command.target.target_reference_digest,
            "target_contract_version": command.target.target_contract_version,
        },
        "processing_time": _iso(command.processing_time),
        "reference_time": _iso(command.reference_time),
        "evaluation_time": _iso(command.evaluation_time),
        "freshness_seconds": int(command.freshness_policy.stale_after.total_seconds()),
        "max_top_holder_fraction": command.max_top_holder_fraction,
        "rti11_timeout_seconds": command.rti11_timeout.total_seconds(),
        "rti11_max_response_bytes": command.rti11_max_response_bytes,
        "evaluation_id": command.evaluation_id,
        "paper_intent": {
            "pfx_invocation_id": intent.pfx_invocation_id,
            "cip_invocation_id": intent.cip_invocation_id,
            "decision_ruleset": {
                "buy_score_threshold": _decimal(intent.decision_ruleset.buy_score_threshold),
                "watch_score_threshold": _decimal(intent.decision_ruleset.watch_score_threshold),
                "max_evidence_age_seconds": intent.decision_ruleset.max_evidence_age_seconds,
                "version": intent.decision_ruleset.version,
            },
            "decision_time": _iso(intent.decision_time),
            "policy_seed": {
                "policy_snapshot_id": seed.policy_snapshot_id,
                "risk_governor_version": seed.risk_governor_version,
                "capital_authorization_version": seed.capital_authorization_version,
                "evaluator_version": seed.evaluator_version,
                "paper_lifecycle_id": seed.paper_lifecycle_id,
                "paper_portfolio_id": seed.paper_portfolio_id,
                "simulation_reference_time": _iso(seed.simulation_reference_time),
                "policy_cutoff_time": _iso(seed.policy_cutoff_time),
                "risk_state_max_age_seconds": _decimal(seed.risk_state_max_age_seconds),
                "paper_capital_state_max_age_seconds": _decimal(seed.paper_capital_state_max_age_seconds),
                "paper_exposure_state_max_age_seconds": _decimal(seed.paper_exposure_state_max_age_seconds),
                "valid_from": _iso(seed.valid_from),
                "valid_until": _iso(seed.valid_until),
                "risk_state": {
                    "status": seed.risk_state.status.value,
                    "emergency_stop": seed.risk_state.emergency_stop,
                    "risk_flags": list(seed.risk_state.risk_flags),
                    "as_of_time": _iso(seed.risk_state.as_of_time),
                    "available_at": _iso(seed.risk_state.available_at),
                },
                "paper_capital_state": {
                    "unit": seed.paper_capital_state.unit,
                    "budget_total": _decimal(seed.paper_capital_state.budget_total),
                    "committed_before": _decimal(seed.paper_capital_state.committed_before),
                    "requested_entry": _decimal(seed.paper_capital_state.requested_entry),
                    "max_single_entry": _decimal(seed.paper_capital_state.max_single_entry),
                    "as_of_time": _iso(seed.paper_capital_state.as_of_time),
                    "available_at": _iso(seed.paper_capital_state.available_at),
                },
                "paper_exposure_state": {
                    "unit": seed.paper_exposure_state.unit,
                    "exposure_before": _decimal(seed.paper_exposure_state.exposure_before),
                    "max_total_exposure": _decimal(seed.paper_exposure_state.max_total_exposure),
                    "as_of_time": _iso(seed.paper_exposure_state.as_of_time),
                    "available_at": _iso(seed.paper_exposure_state.available_at),
                },
                "provenance_source": seed.provenance_source,
            },
            "execution_observation": {
                "observation_id": execution.observation_id,
                "subject_identity": dict(execution.subject_identity),
                "observation_time": _iso(execution.observation_time),
                "availability_time": _iso(execution.availability_time),
                "quality": execution.quality.value,
                "market_context_digest": execution.market_context_digest,
                "quote_context_digest": execution.quote_context_digest,
                "liquidity_context_digest": execution.liquidity_context_digest,
                "sellability_status": execution.sellability_status.value,
                "source_contract_version": execution.source_contract_version,
                "source_provenance": dict(execution.source_provenance),
                "observation_replay_key": execution.observation_replay_key,
            },
            "simulation_configuration": {
                "configuration_id": config.configuration_id,
                "contract_version": config.contract_version,
                "simulation_version": config.simulation_version,
                "fill_model_version": config.fill_model_version,
                "friction_model_version": config.friction_model_version,
                "failure_policy_version": config.failure_policy_version,
                "seed_policy_version": config.seed_policy_version,
                "configuration_provenance": dict(config.configuration_provenance),
            },
            "replay_identity": {
                "replay_id": replay.replay_id,
                "replay_schema_version": replay.replay_schema_version,
                "replay_seed_identity": replay.replay_seed_identity,
                "parent_replay_id": replay.parent_replay_id,
                "replay_scope": dict(replay.replay_scope),
            },
            "simulation_reference_time": _iso(intent.simulation_reference_time),
            "paper_evaluation_time": _iso(intent.paper_evaluation_time),
            "selected_observation_time": _iso(intent.selected_observation_time),
            "target_asset_identity": dict(intent.target_asset_identity),
            "simulation_policy": {
                "policy_id": policy.policy_id,
                "policy_version": policy.policy_version,
                "mode": policy.mode.value,
                "side": policy.side.value,
                "requested_quantity": _decimal(policy.requested_quantity),
                "quantity_unit": policy.quantity_unit,
                "price_unit": policy.price_unit,
                "fee_unit": policy.fee_unit,
                "quote_currency": policy.quote_currency,
                "reference_price_rule": policy.reference_price_rule,
                "quantity_rounding_rule": policy.quantity_rounding_rule,
                "simulated_fill_time": _iso(policy.simulated_fill_time),
                "simulated_capacity": _decimal(policy.simulated_capacity),
                "allow_partial_fill": policy.allow_partial_fill,
                "friction_values": {k: _decimal(v) for k, v in policy.friction_values.items()},
                "valuation_max_age_seconds": _decimal(policy.valuation_max_age_seconds),
                "accounting_fee": _decimal(policy.accounting_fee),
                "accounting_priority_fee": _decimal(policy.accounting_priority_fee),
                "accounting_observed_at": _iso(policy.accounting_observed_at),
                "accounting_contract_version": policy.accounting_contract_version,
                "ledger_stream_identity": dict(policy.ledger_stream_identity),
                "sequence_number": policy.sequence_number,
                "previous_entry_digest": policy.previous_entry_digest,
                "expectation_id": policy.expectation_id,
                "expectation_fields": list(policy.expectation_fields),
                "fill_model_version": policy.fill_model_version,
                "friction_model_version": policy.friction_model_version,
                "provenance": dict(policy.provenance),
            },
            "genesis": {
                "state_id": genesis.state_id,
                "state_version": genesis.state_version,
                "portfolio_scope": dict(genesis.portfolio_scope),
                "target_asset_identity": dict(genesis.target_asset_identity),
                "as_of_time": _iso(genesis.as_of_time),
                "zero_quantity": _decimal(genesis.zero_quantity),
                "zero_cost_basis": _decimal(genesis.zero_cost_basis),
                "provenance": dict(genesis.provenance),
            },
        },
    }


@asynccontextmanager
async def _api(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'oaf-post.db'}",
        operator_bearer_token=TOKEN,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_authenticated_post_prepare_returns_handle_without_run(tmp_path):
    rti11 = _rti11()

    class Source:
        def snapshot_mint(self, token):
            return _snapshot()

    class Upstream:
        def compose(self, **kwargs):
            return _upstream()

    class Rti11:
        def compose(self, request):
            return rti11

    async with _api(tmp_path) as (app, client):
        app.state.operator_prepare_service = OafOperatorPrepareInvocationService(
            solana_source=Source(),
            registry=app.state.operator_case_registry,
            upstream=Upstream(),
            rti11=Rti11(),
        )
        response = await client.post(
            "/api/v1/operator/paper-cases",
            json=_payload(rti11),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 201
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["state"] == "REVIEW_READY"
        assert body["candidate_id"] == rti11.request.candidate_id
        assert body["simulation_only"] is True
        assert body["review_path"].endswith(body["handle"])
        assert app.state.operator_case_registry.get(body["handle"]) is not None


@pytest.mark.asyncio
async def test_post_prepare_requires_auth_before_service_call(tmp_path):
    calls = []

    class Forbidden:
        def prepare(self, invocation):
            calls.append(True)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        app.state.operator_prepare_service = Forbidden()
        response = await client.post(
            "/api/v1/operator/paper-cases",
            json=_payload(_rti11()),
        )

        assert response.status_code == 401
        assert calls == []


@pytest.mark.asyncio
async def test_post_prepare_unconfigured_source_is_503(tmp_path):
    async with _api(tmp_path) as (_app, client):
        response = await client.post(
            "/api/v1/operator/paper-cases",
            json=_payload(_rti11()),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "operator_prepare_unavailable"


@pytest.mark.asyncio
async def test_invalid_nested_payload_is_422_without_service_call(tmp_path):
    calls = []

    class Forbidden:
        def prepare(self, invocation):
            calls.append(True)
            raise AssertionError("must not run")

    payload = _payload(_rti11())
    payload["paper_intent"]["decision_ruleset"]["unexpected"] = True

    async with _api(tmp_path) as (app, client):
        app.state.operator_prepare_service = Forbidden()
        response = await client.post(
            "/api/v1/operator/paper-cases",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert response.status_code == 422
        assert calls == []
