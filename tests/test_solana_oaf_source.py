from datetime import datetime, timezone

import pytest

from core.data.solana_oaf_source import (
    SolanaJsonRpcSource,
    SolanaSourceUnavailable,
)


MINT = "So11111111111111111111111111111111111111112"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _mint_value():
    return {
        "owner": TOKEN_PROGRAM,
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 9,
                    "mintAuthority": None,
                    "freezeAuthority": None,
                    "supply": "1000",
                },
            }
        },
    }


def test_snapshot_is_bounded_finalized_and_reuses_block_time_for_same_slot():
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        if method == "getBlockTime":
            return {"jsonrpc": "2.0", "id": 1, "result": 1_700_000_000}
        values = {
            "getAccountInfo": _mint_value(),
            "getTokenLargestAccounts": [{"address": "a", "amount": "100", "decimals": 9}],
            "getTokenSupply": {"amount": "1000", "decimals": 9},
        }
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"context": {"slot": 123}, "value": values[method]},
        }

    source = SolanaJsonRpcSource(
        rpc_url="https://rpc.example.invalid",
        timeout_seconds=2,
        rpc_call=rpc,
    )
    snapshot = source.snapshot_mint(MINT)

    assert snapshot.token_mint == MINT
    assert snapshot.mint_account.slot == 123
    assert snapshot.mint_account.observed_at == datetime.fromtimestamp(
        1_700_000_000, tz=timezone.utc
    )
    assert [method for method, _ in calls] == [
        "getAccountInfo",
        "getBlockTime",
        "getTokenLargestAccounts",
        "getTokenSupply",
    ]
    for method, params in calls:
        if method != "getBlockTime":
            assert params[-1]["commitment"] == "finalized"


def test_distinct_slots_get_one_block_time_lookup_each():
    slots = iter((10, 11, 11))
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        if method == "getBlockTime":
            return {"jsonrpc": "2.0", "id": 1, "result": 1_700_000_000 + params[0]}
        slot = next(slots)
        value = _mint_value() if method == "getAccountInfo" else []
        if method == "getTokenSupply":
            value = {"amount": "1000", "decimals": 9}
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"context": {"slot": slot}, "value": value},
        }

    source = SolanaJsonRpcSource(
        rpc_url="https://rpc.example.invalid",
        timeout_seconds=2,
        rpc_call=rpc,
    )
    source.snapshot_mint(MINT)
    assert [params[0] for method, params in calls if method == "getBlockTime"] == [10, 11]


def test_missing_block_time_fails_closed_without_fabricated_timestamp():
    def rpc(method, params):
        if method == "getBlockTime":
            return {"jsonrpc": "2.0", "id": 1, "result": None}
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"context": {"slot": 123}, "value": _mint_value()},
        }

    source = SolanaJsonRpcSource(
        rpc_url="https://rpc.example.invalid",
        timeout_seconds=2,
        rpc_call=rpc,
    )
    with pytest.raises(SolanaSourceUnavailable, match="RPC_BLOCK_TIME_UNAVAILABLE"):
        source.snapshot_mint(MINT)


def test_non_mint_account_stops_before_followup_safety_reads():
    calls = []

    def rpc(method, params):
        calls.append(method)
        if method == "getBlockTime":
            return {"jsonrpc": "2.0", "id": 1, "result": 1_700_000_000}
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "context": {"slot": 123},
                "value": {"owner": "not-token-program", "data": {}},
            },
        }

    source = SolanaJsonRpcSource(
        rpc_url="https://rpc.example.invalid",
        timeout_seconds=2,
        rpc_call=rpc,
    )
    with pytest.raises(SolanaSourceUnavailable, match="MINT_PROGRAM_UNSUPPORTED"):
        source.snapshot_mint(MINT)
    assert calls == ["getAccountInfo", "getBlockTime"]


@pytest.mark.parametrize(
    "payload,reason",
    [
        ({"jsonrpc": "2.0", "id": 1, "error": {"code": -1}}, "RPC_SOURCE_ERROR"),
        ({"jsonrpc": "2.0", "id": 1}, "RPC_RESULT_MISSING"),
        ({"jsonrpc": "1.0", "id": 1, "result": {}}, "RPC_ENVELOPE_INVALID"),
    ],
)
def test_rpc_errors_fail_closed(payload, reason):
    source = SolanaJsonRpcSource(
        rpc_url="https://rpc.example.invalid",
        timeout_seconds=2,
        rpc_call=lambda method, params: payload,
    )
    with pytest.raises(SolanaSourceUnavailable, match=reason):
        source.snapshot_mint(MINT)
