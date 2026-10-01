"""Synthetic offline source bytes, independently packed from pinned Rust fields.

These are parser fixtures, not evidence of a deployed program or live pool.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import base64
import hashlib
import json
import socket
import struct
import unittest
from unittest.mock import patch

from core.data import a1_cpmm_sources as a1
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from core.data.coingecko_onchain_ohlcv import OhlcvRequest, OhlcvResponse
from core.data.contracts import FreshnessPolicy

T = datetime(2026, 10, 1, 8, 5, 10, tzinfo=timezone.utc)
POLICY = a1.A1Policy(True, True, timedelta(seconds=180), timedelta(seconds=120))
FRESH = FreshnessPolicy(stale_after=timedelta(seconds=180))


def key(n):
    return a1._encode(bytes([n]) * 32)


M0, M1, POOL, V0, V1 = map(key, range(1, 6))


def encode(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def rpc(method, params, result, start, request_id=1):
    return a1.RpcEnvelope(method, encode(params).decode(), request_id,
                          T + timedelta(seconds=start), T + timedelta(seconds=start + 1),
                          encode({"jsonrpc": "2.0", "id": request_id, "result": result}))


def swap(pool=POOL, m0=M0, m1=M1, v0=V0, v1=V1, discriminator=None):
    accounts = [key(7), a1.AUTHORITY, key(8), pool, key(9), key(10),
                v0, v1, a1.TOKEN_PROGRAM, a1.TOKEN_PROGRAM, m0, m1, key(11)]
    return {"programId": a1.PROGRAM, "accounts": accounts,
            "data": a1._encode((discriminator or a1.SWAPS[0]) + struct.pack("<QQ", 10, 9))}


def transaction(instructions=None, signature=12, inner=None, err=None):
    return {"version": "legacy", "transaction": {
        "signatures": [a1._encode(bytes([signature]) * 64)],
        "message": {"instructions": [swap()] if instructions is None else instructions}},
        "meta": {"err": err, "innerInstructions": [] if inner is None else inner}}


def discovery_envelopes(txs=None, block_time=None):
    stamp = int((T - timedelta(seconds=20)).timestamp()) if block_time is None else block_time
    block = {"blockhash": key(13), "blockTime": stamp,
             "transactions": [transaction()] if txs is None else txs}
    return (rpc("getSlot", [{"commitment": "finalized"}], 123, -12),
            rpc("getBlock", [123, {"commitment": "finalized", "encoding": "jsonParsed",
                "transactionDetails": "full", "maxSupportedTransactionVersion": 0,
                "rewards": False}], block, -10),
            rpc("getBlockTime", [123], stamp, -8))


def facts(envelopes=None, policy=POLICY):
    return a1.map_discovery(envelopes or discovery_envelopes(), reference_time=T, policy=policy)


def pool_bytes():
    # PoolState: ten Pubkeys; bump/status/three decimals; seven u64s;
    # creator selection/enabled; six pad bytes; two creator fees; 28 pad u64s.
    pubs = [key(8), key(14), V0, V1, key(15), M0, M1,
            a1.TOKEN_PROGRAM, a1.TOKEN_PROGRAM, key(11)]
    return (hashlib.sha256(b"account:PoolState").digest()[:8] + struct.pack(
        "<" + "32s" * 10 + "BBBBB" + "Q" * 7 + "BB6xQQ224x",
        *(a1._decode(k, 32) for k in pubs), 253, 0, 9, 6, 6,
        100, 100, 100, 200, 200, 0, 0, 0, 1, 300, 300))


def mint_bytes(decimals=6):
    return struct.pack("<I32sQBBI32s", 0, bytes(32), 10_000_000, decimals, 1, 0, bytes(32))


def vault_bytes(mint, amount):
    return struct.pack("<32s32sQI32sBIQQI32s", a1._decode(mint, 32),
                       a1._decode(a1.AUTHORITY, 32), amount, 0, bytes(32), 1,
                       0, 0, 0, 0, bytes(32))


def reserve_envelopes(discovery=None, mutate=None):
    discovery = discovery or facts()
    raw = {POOL: (a1.PROGRAM, pool_bytes()), M0: (a1.TOKEN_PROGRAM, mint_bytes()),
           M1: (a1.TOKEN_PROGRAM, mint_bytes()),
           V0: (a1.TOKEN_PROGRAM, vault_bytes(M0, 2_000_000)),
           V1: (a1.TOKEN_PROGRAM, vault_bytes(M1, 3_000_000))}
    if mutate:
        mutate(raw)
    keys = a1.pool_account_keys(discovery, M0)
    values = [{"owner": raw[k][0], "executable": False,
               "data": [base64.b64encode(raw[k][1]).decode(), "base64"]} for k in keys]
    return (rpc("getMultipleAccounts", [list(keys), {"commitment": "finalized",
                "encoding": "base64", "minContextSlot": 123}],
                {"context": {"slot": 124}, "value": values}, -3),
            rpc("getBlockTime", [124], int((T - timedelta(seconds=3)).timestamp()), -2))


def reserves(mutate=None):
    discovery = facts()
    return a1.map_reserves(discovery, M0, reserve_envelopes(discovery, mutate),
                           reference_time=T, policy=POLICY)


def usd(mint=M0, close="13", shift=0):
    req = OhlcvRequest("solana", mint, POOL, M0, M1, T, timedelta(seconds=10), 16384)
    # Numeric JSON literals preserve the entire supplied decimal coefficient.
    rows = ",".join(f"[{req.cutoff - i * 60 + shift},{close},{close},{close},{close},100]"
                    for i in (1, 2, 3))
    body = ('{"data":{"id":"synthetic-a1","type":"ohlcv_request_response",'
            '"attributes":{"ohlcv_list":[' + rows + ']}},"meta":{"base":{"address":"'
            + M0 + '"},"quote":{"address":"' + M1 + '"}}}').encode()
    return OhlcvResponse(req, T - timedelta(seconds=2), T - timedelta(seconds=1), body)


def valued(reserve=None, responses=None, policy=POLICY, mint=M0):
    return a1.value_pool(reserve or reserves()[0], mint,
                        responses or (usd(), usd(M1, "1.000001")), reference_time=T, policy=policy)


def change_result(envelope, mutate):
    body = json.loads(envelope.body)
    mutate(body)
    return replace(envelope, body=encode(body))


class A1SourceTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "socket.create_connection"):
            p = patch(target, side_effect=AssertionError("offline network forbidden"))
            p.start()
            self.addCleanup(p.stop)

    def rejected(self, fn, reason):
        with self.assertRaisesRegex(a1.A1SourceError, "^" + reason + "$"):
            fn()

    def test_original_clock_real_p02_and_replay(self):
        source = a1.OfflineA1DiscoverySource(discovery_envelopes(), POLICY)
        snapshot = BoundedDiscoveryOwner(source).discover(reference_time=T, processing_time=T,
            freshness_policy=FRESH, evaluation_id="offline-a1")
        self.assertEqual([c.token_mint for c in snapshot.candidates], sorted((M0, M1)))
        self.assertEqual(source.facts, facts())
        for o in source.facts.batch.observations:
            self.assertEqual(o.raw_event.event_time, T - timedelta(seconds=20))
            self.assertEqual(o.raw_event.received_time, T - timedelta(seconds=7))
            self.assertIsNone(o.cursor)
        self.rejected(lambda: source.discover_once(reference_time=T), "SECOND_DISCOVERY_FORBIDDEN")

    def test_both_explicit_model_opt_ins_required(self):
        for changes in ({"accept_event_scoped_universe": False}, {"accept_candle_close_usd": False}):
            self.rejected(lambda: facts(policy=replace(POLICY, **changes)), "MODEL_OPT_IN_REQUIRED")

    def test_missing_original_time_never_replaced_by_receipt(self):
        es = discovery_envelopes()
        for value in (None, True, "123"):
            changed = (*es[:2], change_result(es[2], lambda b: b.update(result=value)))
            self.rejected(lambda: facts(changed), "BLOCK_TIME_REQUIRED")

    def test_stale_conflicting_and_future_discovery_time(self):
        self.rejected(lambda: facts(discovery_envelopes(block_time=int((T-timedelta(seconds=181)).timestamp()))), "STALE_DISCOVERY")
        self.rejected(lambda: facts(discovery_envelopes(block_time=int(T.timestamp()))), "STALE_DISCOVERY")
        es = discovery_envelopes()
        changed = (es[0], change_result(es[1], lambda b: b["result"].update(blockTime=1)), es[2])
        self.rejected(lambda: facts(changed), "BLOCK_TIME_CONFLICT")

    def test_rpc_binding_finality_ids_byte_limits_and_duplicates(self):
        es = discovery_envelopes()
        cases = [(replace(es[0], params_json='[{"commitment":"confirmed"}]'), "RPC_REQUEST_BINDING"),
                 (replace(es[0], body=b"x"*8193), "RPC_BYTE_BUDGET"),
                 (change_result(es[0], lambda b: b.update(id=True)), "RPC_UNAVAILABLE_OR_MALFORMED"),
                 (replace(es[0], body=b'{"jsonrpc":"2.0","id":1,"id":1,"result":123}'), "DUPLICATE_JSON_KEY"),
                 (replace(es[0], received_at=T+timedelta(seconds=1)), "RPC_RECEIPT_OR_DEADLINE")]
        for env, reason in cases:
            with self.subTest(reason=reason):
                self.rejected(lambda: facts((env,*es[1:])), reason)

    def test_inner_swap_and_reverse_direction_preserve_composition(self):
        instruction = swap(m0=M1, m1=M0, v0=V1, v1=V0, discriminator=a1.SWAPS[1])
        result = facts(discovery_envelopes([transaction([{"programId": key(20)}],
            inner=[{"index":0,"instructions":[instruction]}])]))
        self.assertEqual((result.swaps[0].mint_0,result.swaps[0].vault_0), (M0,V0))
        self.assertEqual(len(result.batch.observations),2)

    def test_failed_unknown_and_token2022_swaps_are_outside_scope(self):
        other = swap()
        other["accounts"][8] = key(22)
        result = facts(discovery_envelopes([transaction(err={"InstructionError":[0,"error"]}),
            transaction([swap(discriminator=bytes(8))],signature=16),transaction([other],signature=17)]))
        self.assertEqual(result.swaps,())
        self.assertEqual(result.batch.observations,())

    def test_incomplete_inner_recording_is_not_silently_empty(self):
        tx = transaction()
        tx["meta"]["innerInstructions"] = None
        self.rejected(lambda: facts(discovery_envelopes([tx])), "INNER_RECORDING_REQUIRED")
        for version in (False, True, "0", 1):
            tx=transaction();tx["version"]=version
            self.rejected(lambda:facts(discovery_envelopes([tx])), "UNSUPPORTED_TRANSACTION_VERSION")

    def test_duplicate_event_collapse_and_conflicting_pool_fail_closed(self):
        tx = transaction()
        self.assertEqual(len(facts(discovery_envelopes([tx,tx])).swaps),1)
        self.rejected(lambda: facts(discovery_envelopes([transaction([swap(),swap(v0=key(21))])])), "CONFLICTING_POOL_EVENT")

    def test_conflicting_duplicate_signature_rejects_whole_block(self):
        self.rejected(lambda:facts(discovery_envelopes([transaction(),transaction([swap(v0=key(21))])])),
                      "CONFLICTING_TRANSACTION_SIGNATURE")

    def test_all_events_bounded_before_lexical_five(self):
        swaps = [swap(key(60+i),M0,key(30+i),key(90+i),key(120+i)) for i in range(21)]
        self.rejected(lambda: facts(discovery_envelopes([transaction(swaps)])), "POOL_UNIVERSE_BUDGET")
        self.rejected(lambda: facts(discovery_envelopes([transaction([swap()]*33)])), "SWAP_EVENT_BUDGET")
        source = a1.OfflineA1DiscoverySource(discovery_envelopes([transaction(swaps[:6])]),POLICY)
        snapshot = BoundedDiscoveryOwner(source).discover(reference_time=T, processing_time=T,
            freshness_policy=FRESH,evaluation_id="lexical-five")
        self.assertEqual(len(source.facts.batch.observations),7)
        self.assertEqual([c.token_mint for c in snapshot.candidates],sorted([M0]+[key(30+i) for i in range(6)])[:5])

    def test_independent_binary_layout_net_three_fee_reserves(self):
        self.assertEqual(len(pool_bytes()),637)
        self.assertEqual(len(mint_bytes()),82)
        self.assertEqual(len(vault_bytes(M0,1)),165)
        r = reserves()[0]
        self.assertEqual((r.reserve_0,r.reserve_1,r.decimals_0,r.decimals_1),(1_999_400,2_999_400,6,6))
        self.assertEqual((r.slot,r.observed_at),(124,T-timedelta(seconds=3)))

    def test_binary_owner_layout_version_and_identity_rejections(self):
        cases = [(POOL, "owner", a1.TOKEN_PROGRAM, "UNSUPPORTED_POOL_LAYOUT"),
                 (POOL, 328, 252, "UNSUPPORTED_POOL_VERSION"),
                 (POOL, 413, 1, "UNSUPPORTED_POOL_VERSION"),
                 (M0, 44, 7, "INVALID_MINT_DECIMALS"),
                 (M0, 45, 0, "INVALID_MINT_DECIMALS"),
                 (V0, 108, 2, "INVALID_VAULT_IDENTITY_OR_STATE"),
                 (V0, 32, 0, "INVALID_VAULT_IDENTITY_OR_STATE")]
        for address, offset, value, reason in cases:
            def mutation(raw):
                owner, data = raw[address]
                if offset == "owner":
                    raw[address] = (value,data)
                else:
                    data = bytearray(data); data[offset] = value
                    raw[address] = (owner,bytes(data))
            with self.subTest(reason=reason,offset=offset):
                self.rejected(lambda: reserves(mutation),reason)

    def test_fee_underflow_zero_and_disabled_creator_fail_closed(self):
        for amount,reason in ((599,"INVALID_RESERVE_FEES"),(600,"ZERO_NET_RESERVE")):
            self.rejected(lambda: reserves(lambda d: d.update({V0:(a1.TOKEN_PROGRAM,vault_bytes(M0,amount))})),reason)
        def disable(d):
            owner,raw=d[POOL]; raw=bytearray(raw);raw[390]=0;d[POOL]=(owner,bytes(raw))
        self.rejected(lambda: reserves(disable),"INVALID_RESERVE_FEES")

    def test_atomic_account_set_and_context_clock_binding(self):
        f=facts(); es=reserve_envelopes(f)
        for mutation,reason in ((lambda b:b["result"]["value"].pop(),"INCOMPLETE_ACCOUNT_SET"),
                                (lambda b:b["result"]["context"].update(slot=122),"ACCOUNT_SLOT_PRECEDES_EVENT"),
                                (lambda b:b["result"]["value"].__setitem__(0,None),"INVALID_ACCOUNT")):
            changed=(change_result(es[0],mutation),es[1])
            self.rejected(lambda:a1.map_reserves(f,M0,changed,reference_time=T,policy=POLICY),reason)
        changed=(es[0],change_result(es[1],lambda b:b.update(result=None)))
        self.rejected(lambda:a1.map_reserves(f,M0,changed,reference_time=T,policy=POLICY),"BLOCK_TIME_REQUIRED")

    def test_two_explicit_prices_exact_sum_then_round_and_quote_orientation(self):
        result=valued()
        self.assertEqual(result.liquidity_usd,Decimal("28.991602"))
        self.assertEqual((result.base_mint,result.quote_mint),(M0,M1))
        reverse=valued(mint=M1)
        self.assertEqual(reverse.liquidity_usd,result.liquidity_usd)
        self.assertEqual((reverse.base_mint,reverse.quote_mint),(M1,M0))
        self.assertNotEqual(result.reference_id,valued(responses=(usd(),usd(M1,"1"))).reference_id)

    def test_exact_decimal_does_not_depend_on_ambient_precision(self):
        responses=(usd(close="13.12345678901234567890123456789"),usd(M1,"1.000001"))
        result=valued(responses=responses)
        with localcontext() as ctx:
            ctx.prec=2
            self.assertEqual(valued(responses=responses),result)

    def test_price_clock_interval_history_and_identity_are_not_receipt_time(self):
        self.rejected(lambda:valued(responses=(usd(shift=-60),usd(M1,"1"))),"STALE_OR_MISSING_CLOSED_INTERVAL")
        self.rejected(lambda:valued(responses=(usd(),usd(M0,"1"))),"USD_IDENTITY_MISMATCH")
        self.rejected(lambda:valued(policy=replace(POLICY,max_skew=timedelta(seconds=66))),"RESERVE_PRICE_SKEW")
        self.rejected(lambda:valued(responses=(replace(usd(),http_status=429,body=b"untrusted-secret"),usd(M1))),"VALUATION_TRANSPORT_OR_BUDGET")
        self.rejected(lambda:valued(responses=(replace(usd(),body=usd().body.replace(b'"ohlcv_list":[',b'"ohlcv_list":[[1,1,1,1,1,1],')),usd(M1))),"INVALID_USD_SOURCE_FACTS")

    def test_source_lineage_changes_on_source_bytes_or_receipts(self):
        original=valued()
        moved=replace(usd(),received_at=T)
        self.assertNotEqual(original.reference_id,valued(responses=(moved,usd(M1,"1.000001"))).reference_id)
        r=replace(reserves()[0],source_digest="a"*64)
        self.assertNotEqual(original.reference_id,valued(r).reference_id)

    def test_retained_valuation_packet_binds_both_original_intervals(self):
        fact=a1.map_valuation(reserves()[0],M0,(usd(),usd(M1,"1.000001")),reference_time=T,policy=POLICY)
        packet=json.loads(fact.lineage_json)
        self.assertEqual(packet["rounding"],"sum_then_floor_6_usd")
        self.assertEqual(packet["liquidity_microusd"],28_991_602)
        self.assertEqual([p[-1] for p in packet["usd"]],["NOT_PROVIDED"]*2)
        self.assertEqual(packet["usd"][0][-4:-2],packet["usd"][1][-4:-2])
        self.assertEqual(fact.observation.reference_id,"a1-liquidity:"+a1._digest(packet))

    def test_source_bounds_missing_response_and_mutated_reserve(self):
        self.rejected(lambda:valued(responses=(usd(),)),"TWO_RESERVE_VALUATIONS_REQUIRED")
        r=reserves()[0];object.__setattr__(r,"reserve_0",True)
        self.rejected(lambda:valued(r),"RESERVE_NUMERIC_BOUNDS")
        self.rejected(lambda:valued(policy=replace(POLICY,stale_after=timedelta(seconds=69))),"STALE_OR_MISSING_CLOSED_INTERVAL")
        self.rejected(lambda:valued(responses=(replace(usd(),body=b"x"*16385),usd(M1))),"VALUATION_TRANSPORT_OR_BUDGET")

    def test_event_config_and_snapshot_vault_binding(self):
        def config(d):
            owner,raw=d[POOL];raw=bytearray(raw);raw[8:40]=a1._decode(key(25),32);d[POOL]=(owner,bytes(raw))
        self.rejected(lambda:reserves(config),"POOL_EVENT_BINDING")

    def test_wrong_candidate_lineage_and_reference_do_not_call_suppliers(self):
        source=a1.OfflineA1DiscoverySource(discovery_envelopes(),POLICY)
        snap=BoundedDiscoveryOwner(source).discover(reference_time=T,processing_time=T,
            freshness_policy=FRESH,evaluation_id="candidate-binding")
        def forbidden(*args):raise AssertionError("supplier must not be called")
        adapter=a1.OfflineA1PoolSource(source,forbidden,forbidden)
        self.rejected(lambda:adapter.pools_once(replace(snap.candidates[0],source_event_id="forged"),reference_time=T),"ADMITTED_CANDIDATE_REQUIRED")
        self.rejected(lambda:adapter.pools_once(snap.candidates[0],reference_time=T+timedelta(seconds=1)),"EXACT_DISCOVERY_REFERENCE_REQUIRED")

    def test_injected_interfaces_call_once_and_never_retry(self):
        source=a1.OfflineA1DiscoverySource(discovery_envelopes(),POLICY)
        snapshot=BoundedDiscoveryOwner(source).discover(reference_time=T,processing_time=T,
            freshness_policy=FRESH,evaluation_id="injected")
        candidate=next(c for c in snapshot.candidates if c.token_mint==M0)
        calls=[]
        def reserve_supplier(c,keys):
            calls.append(("reserve",keys));return reserve_envelopes(source.facts)
        def price_supplier(r):
            calls.append(("usd",r.pool));return (usd(),usd(M1,"1.000001"))
        adapter=a1.OfflineA1PoolSource(source,reserve_supplier,price_supplier)
        result=BoundedPoolCandidateOwner(adapter).select(candidate,reference_time=T,freshness_policy=FRESH)
        self.assertEqual(result,valued())
        self.assertEqual([c[0] for c in calls],["reserve","usd"])
        self.assertEqual(adapter.valuation_facts[M0][0].observation,result)
        self.rejected(lambda:adapter.pools_once(candidate,reference_time=T),"SECOND_POOL_INVOCATION_FORBIDDEN")
        def unavailable(*args):
            raise RuntimeError("secret provider error")
        bad=a1.OfflineA1PoolSource(source,unavailable,price_supplier)
        self.rejected(lambda:bad.pools_once(candidate,reference_time=T),"INJECTED_SOURCE_UNAVAILABLE")
        self.rejected(lambda:bad.pools_once(candidate,reference_time=T),"SECOND_POOL_INVOCATION_FORBIDDEN")
        self.assertEqual(len(calls),2)

    def test_pool_selection_preserves_close_liquidity_at_low_precision(self):
        source=a1.OfflineA1DiscoverySource(discovery_envelopes(),POLICY)
        snap=BoundedDiscoveryOwner(source).discover(reference_time=T,processing_time=T,
            freshness_policy=FRESH,evaluation_id="precision")
        candidate=next(c for c in snap.candidates if c.token_mint==M0)
        first=replace(valued(),pool_address="a",liquidity_usd=Decimal("28.991601"))
        best=replace(valued(),pool_address="z",liquidity_usd=Decimal("28.991602"))
        class Pools:
            def pools_once(self,*args,**kwargs):return (first,best)
        with localcontext() as ctx:
            ctx.prec=2
            self.assertEqual(BoundedPoolCandidateOwner(Pools()).select(candidate,
                reference_time=T,freshness_policy=FRESH),best)


if __name__ == "__main__":
    unittest.main()
