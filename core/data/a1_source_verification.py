"""Bounded supplied-envelope identity checks; no I/O, clock or binary attestation.

Primary contracts: https://docs.anza.xyz/clusters/available,
https://solana.com/docs/rpc/http/getmultipleaccounts and
https://solana.com/docs/core/programs/program-deployment.
Loader-v3 bincode state: solana_loader_v3_interface::state::UpgradeableLoaderState
(Program tag 2 + Pubkey; ProgramData tag 3 + u64 + Option<Pubkey>).
These metadata checks cannot establish deployed-binary/source equivalence.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import struct

from core.data.a1_cpmm_sources import (
    PROGRAM, RpcEnvelope, A1SourceError, _decode, _encode, _require, _slot, _utc,
)

VERIFICATION_VERSION = "a1-source-identity-v1"
MAINNET_GENESIS_HASH = "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"
UPGRADEABLE_LOADER = "BPFLoaderUpgradeab1e11111111111111111111111"


def cluster_params():
    return []


def program_probe_params():
    return [[PROGRAM], {"commitment": "finalized", "encoding": "base64",
                        "dataSlice": {"offset": 0, "length": 36}}]


def program_snapshot_params(programdata, minslot):
    _decode(programdata, 32)
    _slot(minslot)
    _require(programdata != PROGRAM, "PROGRAMDATA_IDENTITY")
    return [[PROGRAM, programdata], {"commitment": "finalized", "encoding": "base64",
            "minContextSlot": minslot, "dataSlice": {"offset": 0, "length": 45}}]


@dataclass(frozen=True)
class A1ClusterEvidence:
    genesis_hash: str
    started_at: datetime
    received_at: datetime
    body_digest: str
    request_lineage: tuple
    contract_version: str = VERIFICATION_VERSION


@dataclass(frozen=True)
class A1ProgramEvidence:
    program: str
    programdata: str
    loader: str
    probe_slot: int
    context_slot: int
    deployment_slot: int
    upgrade_authority: str | None
    received_at: tuple[datetime, datetime]
    body_digests: tuple[str, str]
    request_lineage: tuple[tuple, tuple]
    verification_level: str = "LEVEL_1"
    source_equivalence: str = "NOT_VERIFIED"
    contract_version: str = VERIFICATION_VERSION


def verify_cluster(envelope, *, reference_time):
    _require(type(envelope) is RpcEnvelope, "CLUSTER_ENVELOPE_REQUIRED")
    identity = envelope.read("getGenesisHash", cluster_params(), reference_time, 8192)
    _decode(identity, 32)
    _require(identity == MAINNET_GENESIS_HASH, "CLUSTER_IDENTITY_MISMATCH")
    return A1ClusterEvidence(identity, _utc(envelope.started_at), _utc(envelope.received_at),
        hashlib.sha256(envelope.body).hexdigest(), tuple(envelope.lineage()))


def _accounts(envelope, params, reference, limit, count):
    _require(type(envelope) is RpcEnvelope, "PROGRAM_ENVELOPE_REQUIRED")
    result = envelope.read("getMultipleAccounts", params, reference, limit)
    _require(type(result) is dict and type(result.get("context")) is dict,
             "PROGRAM_CONTEXT_REQUIRED")
    slot = _slot(result["context"].get("slot"))
    values = result.get("value")
    _require(type(values) is list and len(values) == count, "PROGRAM_ACCOUNT_SET")
    return slot, values


def _account(value, *, executable, length, programdata=False):
    _require(type(value) is dict and value.get("owner") == UPGRADEABLE_LOADER
             and value.get("executable") is executable, "PROGRAM_OWNER_OR_EXECUTABLE")
    space = value.get("space")
    _require(type(space) is int and (space > 45 if programdata else space == 36),
             "PROGRAM_ACCOUNT_SPACE")
    data = value.get("data")
    _require(type(data) is list and len(data) == 2 and data[1] == "base64"
             and type(data[0]) is str and len(data[0]) <= 64, "PROGRAM_ACCOUNT_ENCODING")
    try:
        raw = base64.b64decode(data[0], validate=True)
    except (ValueError, TypeError):
        raise A1SourceError("PROGRAM_ACCOUNT_ENCODING") from None
    _require(len(raw) == length, "PROGRAM_ACCOUNT_LAYOUT")
    return raw


def _program(value):
    raw = _account(value, executable=True, length=36)
    _require(struct.unpack_from("<I", raw)[0] == 2, "PROGRAM_STATE")
    address = _encode(raw[4:36])
    _require(address != PROGRAM and raw[4:36] != bytes(32), "PROGRAMDATA_IDENTITY")
    return address


def program_probe_identity(probe, *, reference_time):
    """Derive the exact next bounded request without trusting an arbitrary address."""
    slot, values = _accounts(probe, program_probe_params(), reference_time, 8192, 1)
    return _program(values[0]), slot


def verify_program(probe, snapshot, *, reference_time):
    programdata, probe_slot = program_probe_identity(probe, reference_time=reference_time)
    context_slot, values = _accounts(snapshot, program_snapshot_params(programdata, probe_slot),
                                    reference_time, 16384, 2)
    _require(context_slot >= probe_slot and _utc(probe.received_at) <= _utc(snapshot.started_at),
             "PROGRAM_SNAPSHOT_SEQUENCE")
    _require(_program(values[0]) == programdata, "PROGRAMDATA_LINKAGE_CHANGED")
    raw = _account(values[1], executable=False, length=45, programdata=True)
    _require(struct.unpack_from("<I", raw)[0] == 3, "PROGRAMDATA_STATE")
    deployment_slot = _slot(struct.unpack_from("<Q", raw, 4)[0])
    _require(deployment_slot <= context_slot and raw[12] in (0, 1), "PROGRAMDATA_METADATA")
    # None consumes only one byte; the remaining allocation is not authority data.
    upgrade_authority = _encode(raw[13:45]) if raw[12] == 1 else None
    return A1ProgramEvidence(PROGRAM, programdata, UPGRADEABLE_LOADER, probe_slot,
        context_slot, deployment_slot, upgrade_authority,
        (_utc(probe.received_at), _utc(snapshot.received_at)),
        tuple(hashlib.sha256(e.body).hexdigest() for e in (probe, snapshot)),
        (tuple(probe.lineage()), tuple(snapshot.lineage())))
