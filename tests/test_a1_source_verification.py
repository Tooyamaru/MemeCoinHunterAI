import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import struct
import unittest
from unittest.mock import patch

from core.data.a1_cpmm_sources import A1SourceError, RpcEnvelope, _encode
from core.data.a1_source_verification import (
    MAINNET_GENESIS_HASH, PROGRAM, UPGRADEABLE_LOADER, cluster_params,
    program_probe_params, program_snapshot_params, program_probe_identity,
    verify_cluster, verify_program,
)

T = datetime(2026, 10, 1, 8, 5, 10, tzinfo=timezone.utc)
PROGRAMDATA = _encode(bytes([71]) * 32)
AUTHORITY = _encode(bytes([72]) * 32)


def envelope(method, params, result, offset=4, identity=1):
    return RpcEnvelope(method, json.dumps(params, sort_keys=True, separators=(",", ":")),
        identity, T-timedelta(seconds=offset+1), T-timedelta(seconds=offset),
        json.dumps({"jsonrpc": "2.0", "id": identity, "result": result}).encode())


def account(raw, executable, space):
    return {"owner": UPGRADEABLE_LOADER, "executable": executable, "space": space,
            "data": [base64.b64encode(raw).decode(), "base64"]}


def program():
    # Independent bincode enum packing: u32 Program discriminant then Pubkey.
    return account(struct.pack("<I32s", 2, bytes([71])*32), True, 36)


def programdata(option=1):
    # ProgramData discriminant, deployment slot, Option tag, authority bytes.
    return account(struct.pack("<IQB32s", 3, 110, option, bytes([72])*32), False, 1000)


def pair():
    probe = envelope("getMultipleAccounts", program_probe_params(),
        {"context": {"slot": 120}, "value": [program()]}, offset=4, identity=2)
    snapshot = envelope("getMultipleAccounts", program_snapshot_params(PROGRAMDATA, 120),
        {"context": {"slot": 121}, "value": [program(), programdata()]}, offset=2, identity=3)
    return probe, snapshot


def change_result(env, mutate):
    body = json.loads(env.body)
    mutate(body["result"])
    return replace(env, body=json.dumps(body).encode())


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.socket = patch("socket.create_connection", side_effect=AssertionError("network prohibited"))
        self.connect = patch("socket.socket.connect", side_effect=AssertionError("network prohibited"))
        self.socket.start(); self.connect.start()
        self.addCleanup(self.socket.stop); self.addCleanup(self.connect.stop)

    def test_mainnet_identity_and_lineage(self):
        env = envelope("getGenesisHash", [], MAINNET_GENESIS_HASH)
        proof = verify_cluster(env, reference_time=T)
        self.assertEqual(proof.genesis_hash, MAINNET_GENESIS_HASH)
        self.assertEqual(proof.received_at, env.received_at)
        self.assertEqual(proof.request_lineage, tuple(env.lineage()))
        self.assertEqual(verify_cluster(env, reference_time=T), proof)

    def test_cluster_missing_mismatch_and_malformed_fail(self):
        for result in (None, {}, "", _encode(bytes([1])*32)):
            with self.subTest(result=result), self.assertRaises(A1SourceError):
                verify_cluster(envelope("getGenesisHash", [], result), reference_time=T)
        for body in (b"{", b'{"jsonrpc":"2.0","id":1,"id":1,"result":null}',
                     b'{"jsonrpc":"2.0","id":2,"result":null}'):
            with self.subTest(body=body), self.assertRaises(A1SourceError):
                verify_cluster(replace(envelope("getGenesisHash", [], MAINNET_GENESIS_HASH), body=body), reference_time=T)

    def test_cluster_request_binding_final_receipt_and_cap(self):
        env = envelope("getGenesisHash", [], MAINNET_GENESIS_HASH)
        for altered in (replace(env, params_json="[1]"), replace(env, method="getIdentity"),
                        replace(env, received_at=T+timedelta(seconds=1)),
                        replace(env, body=b" "*8193)):
            with self.subTest(altered=altered.method), self.assertRaises(A1SourceError):
                verify_cluster(altered, reference_time=T)

    def test_program_level_one_only_atomic_linkage(self):
        probe, snapshot = pair()
        proof = verify_program(probe, snapshot, reference_time=T)
        self.assertEqual(proof.program, PROGRAM)
        self.assertEqual(proof.programdata, PROGRAMDATA)
        self.assertEqual(proof.loader, UPGRADEABLE_LOADER)
        self.assertEqual((proof.probe_slot, proof.context_slot, proof.deployment_slot), (120, 121, 110))
        self.assertEqual(proof.upgrade_authority, AUTHORITY)
        self.assertEqual(proof.verification_level, "LEVEL_1")
        self.assertEqual(proof.source_equivalence, "NOT_VERIFIED")
        self.assertEqual(proof.received_at, (probe.received_at, snapshot.received_at))
        self.assertEqual(program_probe_identity(probe, reference_time=T), (PROGRAMDATA, 120))

    def test_immutable_programdata_ignores_stale_authority_allocation(self):
        probe, snapshot = pair()
        snapshot = change_result(snapshot, lambda result: result["value"].__setitem__(1, programdata(0)))
        self.assertIsNone(verify_program(probe, snapshot, reference_time=T).upgrade_authority)

    def test_program_identity_owner_executable_and_null(self):
        probe, snapshot = pair()
        for field, bad in (("owner", PROGRAM), ("executable", False), ("executable", 1),
                           ("space", 37), ("space", True), ("data", ["", "base64"])):
            altered = change_result(probe, lambda result: result["value"][0].__setitem__(field, bad))
            with self.subTest(field=field), self.assertRaises(A1SourceError):
                verify_program(altered, snapshot, reference_time=T)
        with self.assertRaises(A1SourceError):
            verify_program(change_result(probe, lambda result: result["value"].__setitem__(0, None)), snapshot, reference_time=T)
        with self.assertRaises(A1SourceError):
            verify_program(replace(probe, params_json=json.dumps([[PROGRAMDATA], {"commitment":"finalized"}])), snapshot, reference_time=T)

    def test_programdata_owner_state_allocation_and_deployslot(self):
        probe, snapshot = pair()
        for field, bad in (("owner", PROGRAM), ("executable", True), ("space", 45),
                           ("data", ["!!!", "base64"])):
            altered = change_result(snapshot, lambda result: result["value"][1].__setitem__(field, bad))
            with self.subTest(field=field), self.assertRaises(A1SourceError):
                verify_program(probe, altered, reference_time=T)
        for tag, slot, option in ((2, 110, 1), (3, 122, 1), (3, 110, 2)):
            raw = struct.pack("<IQB32s", tag, slot, option, bytes(32))
            altered = change_result(snapshot, lambda result: result["value"].__setitem__(1, account(raw, False, 100)))
            with self.subTest(tag=tag, slot=slot, option=option), self.assertRaises(A1SourceError):
                verify_program(probe, altered, reference_time=T)

    def test_atomic_program_linkage_cannot_change(self):
        probe, snapshot = pair()
        other = account(struct.pack("<I32s", 2, bytes([73])*32), True, 36)
        altered = change_result(snapshot, lambda result: result["value"].__setitem__(0, other))
        with self.assertRaisesRegex(A1SourceError, "LINKAGE_CHANGED"):
            verify_program(probe, altered, reference_time=T)

    def test_snapshot_request_slot_sequence_and_count(self):
        probe, snapshot = pair()
        bads = (change_result(snapshot, lambda result: result["context"].__setitem__("slot",119)),
                change_result(snapshot, lambda result: result["value"].pop()),
                replace(snapshot, started_at=probe.received_at-timedelta(seconds=1)),
                replace(snapshot, received_at=T+timedelta(seconds=1)),
                replace(snapshot, body=b" "*16385), replace(snapshot, params_json="[]"))
        for bad in bads:
            with self.subTest(), self.assertRaises(A1SourceError):
                verify_program(probe, bad, reference_time=T)

    def test_snapshot_params_return_fresh_exact_values(self):
        params = program_snapshot_params(PROGRAMDATA, 120)
        self.assertEqual(params[0], [PROGRAM, PROGRAMDATA])
        self.assertEqual(params[1], {"commitment":"finalized", "encoding":"base64", "minContextSlot":120,
                                     "dataSlice":{"offset":0,"length":45}})
        params[1]["dataSlice"]["length"] = 999
        self.assertEqual(program_snapshot_params(PROGRAMDATA, 120)[1]["dataSlice"]["length"],45)
        self.assertEqual(cluster_params(), [])


if __name__ == "__main__":
    unittest.main()
