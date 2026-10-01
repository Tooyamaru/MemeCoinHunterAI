"""Offline A1 source mapping. Supplied source bytes only; no I/O or clock.

The selected universe is legacy SPL Raydium CPMM swaps in one finalized block.
These factories establish parser/lineage contracts, not RPC deployment proof.
No transport, API credential, scheduler, eligibility or scoring owner is added.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import base64
import hashlib
import json
import struct

from core.data.bounded_cycle_sources import (
    CanonicalPoolObservation, CycleSourceError, DiscoveryBatch, DiscoveredCandidate,
)
from core.data.contracts import RawEvent
from core.data.orchestration import AdapterObservation, ObservationKind
from core.data.coingecko_onchain_ohlcv import OhlcvRequest, OhlcvResponse, _parse

VERSION = "a1-cpmm-candle-source-v1"
PROGRAM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SOURCE_PIN = "59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92"
AUTHORITY = "GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL"
AUTH_BUMP = 253
POOL_DISCRIMINATOR = bytes.fromhex("f7ede3f5d7c3de46")
SWAPS = tuple(hashlib.sha256(f"global:{n}".encode()).digest()[:8]
              for n in ("swap_base_input", "swap_base_output"))
_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class A1SourceError(CycleSourceError):
    """Bounded reason only; source bodies and secrets never enter errors."""


def _require(ok, reason):
    if not ok:
        raise A1SourceError(reason)


def _utc(value):
    _require(isinstance(value, datetime) and value.tzinfo is not None
             and value.utcoffset() is not None, "SOURCE_CLOCK_REQUIRED")
    return value.astimezone(timezone.utc)


def _decode(text, size):
    _require(type(text) is str and 1 <= len(text) <= 2 * size, "INVALID_IDENTITY")
    n = 0
    for char in text:
        _require(char in _ALPHABET, "INVALID_IDENTITY")
        n = n * 58 + _ALPHABET.index(char)
    data = b"\0" * (len(text) - len(text.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")
    _require(len(data) == size, "INVALID_IDENTITY")
    return data


def _encode(data):
    n, out = int.from_bytes(data, "big"), ""
    while n:
        n, remainder = divmod(n, 58)
        out = _ALPHABET[remainder] + out
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + out


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True).encode()).hexdigest()


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        _require(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


@dataclass(frozen=True)
class A1Policy:
    """Explicit model opt-in. No application automatically constructs this."""
    accept_event_scoped_universe: bool
    accept_candle_close_usd: bool
    stale_after: timedelta
    max_skew: timedelta

    def validate(self):
        _require(self.accept_event_scoped_universe is True
                 and self.accept_candle_close_usd is True, "MODEL_OPT_IN_REQUIRED")
        _require(type(self.stale_after) is timedelta and timedelta(0) < self.stale_after <= timedelta(seconds=180), "INVALID_FRESHNESS")
        _require(type(self.max_skew) is timedelta and timedelta(0) <= self.max_skew <= timedelta(seconds=120), "INVALID_SKEW_POLICY")


@dataclass(frozen=True)
class RpcEnvelope:
    method: str
    params_json: str
    request_id: int
    started_at: datetime
    received_at: datetime
    body: bytes = field(repr=False)

    def read(self, method, params, reference, limit):
        _require(type(self) is RpcEnvelope and self.method == method
                 and self.params_json == json.dumps(params, sort_keys=True, separators=(",", ":")), "RPC_REQUEST_BINDING")
        start, received, reference = map(_utc, (self.started_at, self.received_at, reference))
        _require(start <= received <= reference and received - start <= timedelta(seconds=10), "RPC_RECEIPT_OR_DEADLINE")
        _require(type(self.body) is bytes and 0 < len(self.body) <= limit, "RPC_BYTE_BUDGET")
        _require(type(self.request_id) is int and 0 < self.request_id < 2**31, "RPC_REQUEST_ID")
        try:
            def bad_constant(_):
                raise A1SourceError("INVALID_JSON_NUMBER")
            data = json.loads(self.body, object_pairs_hook=_pairs, parse_constant=bad_constant)
            _require(type(data) is dict and set(data) == {"jsonrpc", "id", "result"}
                     and data["jsonrpc"] == "2.0" and type(data["id"]) is int
                     and data["id"] == self.request_id, "RPC_UNAVAILABLE_OR_MALFORMED")
            return data["result"]
        except A1SourceError:
            raise
        except (ValueError, TypeError, RecursionError):
            raise A1SourceError("RPC_INVALID_JSON") from None

    def lineage(self):
        return [self.method, self.params_json, self.request_id,
                _utc(self.started_at).isoformat(), _utc(self.received_at).isoformat(),
                hashlib.sha256(self.body).hexdigest()]


def _slot(value):
    _require(type(value) is int and 0 <= value < 2**64, "SOURCE_SLOT_REQUIRED")
    return value


def _time(value):
    _require(type(value) is int and 0 <= value < 253402300800, "BLOCK_TIME_REQUIRED")
    return _EPOCH + timedelta(seconds=value)


@dataclass(frozen=True)
class SwapReference:
    pool: str
    mint_0: str
    mint_1: str
    vault_0: str
    vault_1: str
    event_id: str
    amm_config: str
    observation: str


@dataclass(frozen=True)
class A1DiscoveryFacts:
    batch: DiscoveryBatch
    swaps: tuple[SwapReference, ...]
    slot: int
    observed_at: datetime
    scope_digest: str
    rpc_lineage: tuple[tuple, ...]
    contract_version: str = VERSION


def map_discovery(envelopes, *, reference_time, policy):
    """Three source envelopes, one block, all scoped events before lexical P02 truncation."""
    _require(type(policy) is A1Policy, "CANONICAL_POLICY_REQUIRED")
    policy.validate()
    reference_time = _utc(reference_time)
    _require(type(envelopes) is tuple and len(envelopes) == 3
             and all(type(e) is RpcEnvelope for e in envelopes), "THREE_RPC_ENVELOPES_REQUIRED")
    a, b, c = envelopes
    slot = _slot(a.read("getSlot", [{"commitment": "finalized"}], reference_time, 8192))
    block = b.read("getBlock", [slot, {"commitment": "finalized", "encoding": "jsonParsed",
                   "transactionDetails": "full", "maxSupportedTransactionVersion": 0,
                   "rewards": False}], reference_time, 1048576)
    time = _time(c.read("getBlockTime", [slot], reference_time, 8192))
    _require(_utc(a.received_at) <= _utc(b.started_at)
             and _utc(b.received_at) <= _utc(c.started_at)
             and _utc(c.received_at) - _utc(a.started_at) <= timedelta(seconds=30), "RPC_SEQUENCE_OR_DEADLINE")
    _require(type(block) is dict and time == _time(block.get("blockTime")), "BLOCK_TIME_CONFLICT")
    _decode(block.get("blockhash"), 32)
    _require(time <= _utc(b.received_at) and reference_time - time <= policy.stale_after, "STALE_DISCOVERY")
    txs = block.get("transactions")
    _require(type(txs) is list and len(txs) <= 2000, "TRANSACTION_BUDGET")
    swaps, events, pool_bindings, token_events = [], {}, {}, {}
    transactions_seen = {}
    instruction_count = 0
    for tx in txs:
        _require(type(tx) is dict, "UNSUPPORTED_TRANSACTION_VERSION")
        version = tx.get("version", "legacy")
        _require(version == "legacy" or type(version) is int and version == 0,
                 "UNSUPPORTED_TRANSACTION_VERSION")
        meta, transaction = tx.get("meta"), tx.get("transaction")
        _require(type(meta) is dict and "err" in meta and type(transaction) is dict, "INCOMPLETE_TRANSACTION")
        if meta["err"] is not None:
            continue
        sigs = transaction.get("signatures")
        _require(type(sigs) is list and len(sigs) > 0, "SIGNATURE_REQUIRED")
        _decode(sigs[0], 64)
        transaction_digest = _digest(tx)
        _require(sigs[0] not in transactions_seen or transactions_seen[sigs[0]] == transaction_digest,
                 "CONFLICTING_TRANSACTION_SIGNATURE")
        transactions_seen[sigs[0]] = transaction_digest
        msg = transaction.get("message")
        _require(type(msg) is dict and type(msg.get("instructions")) is list, "INSTRUCTIONS_REQUIRED")
        top = msg["instructions"]
        instructions = [(i, None, value) for i, value in enumerate(top)]
        inner = meta.get("innerInstructions")
        _require(type(inner) is list, "INNER_RECORDING_REQUIRED")
        seen_inner = set()
        for group in inner:
            _require(type(group) is dict and type(group.get("index")) is int
                     and 0 <= group["index"] < len(top) and group["index"] not in seen_inner
                     and type(group.get("instructions")) is list, "INVALID_INNER_RECORDING")
            seen_inner.add(group["index"])
            instructions.extend((group["index"], i, v) for i, v in enumerate(group["instructions"]))
        instructions.sort(key=lambda x: (x[0], -1 if x[1] is None else x[1]))
        instruction_count += len(instructions)
        _require(instruction_count <= 8192, "INSTRUCTION_BUDGET")
        for outer, inner_index, ins in instructions:
            _require(type(ins) is dict, "INVALID_INSTRUCTION")
            if ins.get("programId") != PROGRAM:
                continue
            raw = ins.get("data")
            _require(type(raw) is str and len(raw) <= 512, "INVALID_CPMM_INSTRUCTION")
            # Only the two exact pinned swap discriminators define this universe.
            n = 0
            for char in raw:
                _require(char in _ALPHABET, "INVALID_INSTRUCTION_ENCODING")
                n = n * 58 + _ALPHABET.index(char)
            decoded = b"\0" * (len(raw) - len(raw.lstrip("1"))) + n.to_bytes((n.bit_length()+7)//8, "big")
            _require(len(decoded) >= 8, "INVALID_CPMM_DISCRIMINATOR")
            if decoded[:8] not in SWAPS:
                continue
            accounts = ins.get("accounts")
            _require(len(decoded) == 24 and type(accounts) is list and len(accounts) == 13, "INVALID_SWAP_LAYOUT")
            for address in accounts:
                _decode(address, 32)
            if accounts[8:10] != [TOKEN_PROGRAM, TOKEN_PROGRAM]:
                continue  # Explicit legacy-only source scope, never decode extensions as legacy.
            _require(accounts[1] == AUTHORITY and accounts[10] != accounts[11], "SWAP_IDENTITY_CONFLICT")
            i, j = (10, 11) if _decode(accounts[10], 32) < _decode(accounts[11], 32) else (11, 10)
            v0, v1 = (6, 7) if i == 10 else (7, 6)
            event_id = _digest([VERSION, slot, block["blockhash"], sigs[0], outer, inner_index, accounts, raw])
            swap = SwapReference(accounts[3], accounts[i], accounts[j], accounts[v0], accounts[v1],
                                 event_id, accounts[2], accounts[12])
            _require(swap.pool not in (swap.mint_0, swap.mint_1, swap.vault_0, swap.vault_1)
                     and swap.vault_0 != swap.vault_1, "SWAP_IDENTITY_CONFLICT")
            binding = (swap.mint_0, swap.mint_1, swap.vault_0, swap.vault_1,
                       swap.amm_config, swap.observation)
            _require(swap.pool not in pool_bindings or pool_bindings[swap.pool] == binding, "CONFLICTING_POOL_EVENT")
            pool_bindings[swap.pool] = binding
            if event_id in events:
                _require(events[event_id] == swap, "CONFLICTING_EVENT")
                continue
            _require(len(swaps) < 32, "SWAP_EVENT_BUDGET")
            events[event_id] = swap
            swaps.append(swap)
            for mint in (swap.mint_0, swap.mint_1):
                token_events.setdefault(mint, []).append(swap)
    _require(len(token_events) <= 64, "TOKEN_OBSERVATION_BUDGET")
    for refs in token_events.values():
        _require(len({r.pool for r in refs}) <= 20, "POOL_UNIVERSE_BUDGET")
    lineage = tuple(tuple(e.lineage()) for e in envelopes)
    scope_digest = _digest([VERSION, "legacy-cpmm-swap-block", slot, block["blockhash"], lineage,
                            [r.__dict__ for r in swaps]])
    receipt = _utc(c.received_at)
    observations = tuple(AdapterObservation(
        source_id=VERSION, kind=ObservationKind.EVENT, observed_time=receipt,
        raw_event=RawEvent(VERSION, {"discovery_kind": "DISCOVERED", "chain_id": "solana",
            "token_identity": mint, "discovery_reason": "SOURCE_ANCHORED_CPMM_SWAP",
            "metadata": {"scope_digest": scope_digest, "slot": slot,
                         "pool_addresses": sorted({r.pool for r in refs})}},
            receipt, time, "a1-event:" + _digest([scope_digest, mint, [r.event_id for r in refs]])),
    ) for mint, refs in sorted(token_events.items()))
    # No fabricated global numeric cursor. Positions are bound in event/scope digests.
    return A1DiscoveryFacts(DiscoveryBatch(VERSION, "a1-receipt:" + scope_digest, receipt, observations),
                            tuple(swaps), slot, time, scope_digest, lineage)


def pool_account_keys(facts, mint):
    _require(type(facts) is A1DiscoveryFacts, "DISCOVERY_SCOPE_REQUIRED")
    refs = [s for s in facts.swaps if mint in (s.mint_0, s.mint_1)]
    _require(facts.contract_version == VERSION and len(facts.swaps) <= 32 and refs, "DISCOVERY_SCOPE_REQUIRED")
    keys = sorted({a for s in refs for a in (s.pool, s.mint_0, s.mint_1, s.vault_0, s.vault_1)})
    _require(len({s.pool for s in refs}) <= 20 and len(keys) <= 81, "ACCOUNT_SET_BUDGET")
    return tuple(keys)


@dataclass(frozen=True)
class ReserveFact:
    pool: str
    mint_0: str
    mint_1: str
    reserve_0: int
    reserve_1: int
    decimals_0: int
    decimals_1: int
    slot: int
    observed_at: datetime
    received_at: datetime
    source_digest: str

    def __post_init__(self):
        for address in (self.pool,self.mint_0,self.mint_1):
            _decode(address,32)
        _require(self.mint_0 != self.mint_1 and self.pool not in (self.mint_0,self.mint_1), "RESERVE_IDENTITY")
        _slot(self.slot)
        _require(_utc(self.observed_at) <= _utc(self.received_at), "RESERVE_CLOCK")
        _require(all(type(n) is int and 0 < n < 2**64 for n in (self.reserve_0,self.reserve_1))
                 and all(type(n) is int and 0 <= n <= 18 for n in (self.decimals_0,self.decimals_1)), "RESERVE_NUMERIC_BOUNDS")
        _require(type(self.source_digest) is str and len(self.source_digest) == 64
                 and all(c in "0123456789abcdef" for c in self.source_digest), "RESERVE_LINEAGE_REQUIRED")


def map_reserves(facts, mint, envelopes, *, reference_time, policy):
    _require(type(policy) is A1Policy, "CANONICAL_POLICY_REQUIRED")
    policy.validate()
    keys = pool_account_keys(facts, mint)
    _require(type(envelopes) is tuple and len(envelopes) == 2
             and all(type(e) is RpcEnvelope for e in envelopes), "TWO_RESERVE_ENVELOPES_REQUIRED")
    a, b = envelopes
    result = a.read("getMultipleAccounts", [list(keys), {"commitment": "finalized", "encoding": "base64",
                   "minContextSlot": facts.slot}], reference_time, 1048576)
    _require(type(result) is dict and type(result.get("context")) is dict, "ACCOUNT_CONTEXT_REQUIRED")
    slot = _slot(result["context"].get("slot"))
    _require(slot >= facts.slot, "ACCOUNT_SLOT_PRECEDES_EVENT")
    observed = _time(b.read("getBlockTime", [slot], reference_time, 8192))
    _require(_utc(a.received_at) <= _utc(b.started_at)
             and _utc(b.received_at) - _utc(a.started_at) <= timedelta(seconds=20)
             and observed <= _utc(a.received_at) <= _utc(reference_time)
             and _utc(reference_time) - observed <= policy.stale_after, "STALE_RESERVE_OR_RECEIPT")
    _require(facts.observed_at <= observed and _utc(reference_time) - facts.observed_at <= policy.stale_after, "STALE_EVENT_SCOPE")
    values = result.get("value")
    _require(type(values) is list and len(values) == len(keys), "INCOMPLETE_ACCOUNT_SET")
    accounts = {}
    for key, value in zip(keys, values):
        _require(type(value) is dict and value.get("executable") is False
                 and type(value.get("owner")) is str and type(value.get("data")) is list
                 and len(value["data"]) == 2 and value["data"][1] == "base64", "INVALID_ACCOUNT")
        try:
            raw = base64.b64decode(value["data"][0], validate=True)
        except (ValueError, TypeError):
            raise A1SourceError("INVALID_ACCOUNT_ENCODING") from None
        _require(len(raw) <= 637, "ACCOUNT_LAYOUT_BUDGET")
        accounts[key] = (value["owner"], raw)
    digest = _digest([VERSION, SOURCE_PIN, facts.scope_digest, a.lineage(), b.lineage(), keys])
    out = []
    for pool in sorted({s.pool for s in facts.swaps if mint in (s.mint_0, s.mint_1)}):
        owner, raw = accounts[pool]
        _require(owner == PROGRAM and len(raw) == 637 and raw[:8] == POOL_DISCRIMINATOR, "UNSUPPORTED_POOL_LAYOUT")
        pubkeys = tuple(_encode(raw[8+32*i:40+32*i]) for i in range(10))
        vaults, mints = pubkeys[2:4], pubkeys[5:7]
        _require(pubkeys[7:9] == (TOKEN_PROGRAM, TOKEN_PROGRAM)
                 and raw[328] == AUTH_BUMP and raw[329] <= 7
                 and raw[330] == 9 and raw[389] in (0, 1, 2) and raw[390] in (0, 1)
                 and raw[391:397] == bytes(6) and raw[413:] == bytes(224), "UNSUPPORTED_POOL_VERSION")
        _require(_decode(mints[0],32) < _decode(mints[1],32), "POOL_MINT_ORDER")
        for ref in facts.swaps:
            if ref.pool == pool:
                _require((ref.mint_0,ref.mint_1,ref.vault_0,ref.vault_1) == (*mints,*vaults), "POOL_EVENT_BINDING")
                _require((ref.amm_config,ref.observation) == (pubkeys[0],pubkeys[9]), "POOL_EVENT_BINDING")
        reserves, decimals = [], []
        for i in (0,1):
            mint_owner, mint_raw = accounts[mints[i]]
            vault_owner, vault_raw = accounts[vaults[i]]
            _require(mint_owner == vault_owner == TOKEN_PROGRAM
                     and len(mint_raw) == 82 and len(vault_raw) == 165, "UNSUPPORTED_TOKEN_LAYOUT")
            _require(mint_raw[45] == 1 and 0 <= mint_raw[44] <= 18
                     and mint_raw[44] == raw[331+i], "INVALID_MINT_DECIMALS")
            _require(vault_raw[:32] == _decode(mints[i],32)
                     and vault_raw[32:64] == _decode(AUTHORITY,32)
                     and vault_raw[108] == 1, "INVALID_VAULT_IDENTITY_OR_STATE")
            amount = struct.unpack_from("<Q", vault_raw,64)[0]
            fees = sum(struct.unpack_from("<Q",raw,o+8*i)[0] for o in (341,357,397))
            _require(fees <= amount and (raw[390] == 1 or struct.unpack_from("<Q",raw,397+8*i)[0] == 0), "INVALID_RESERVE_FEES")
            reserves.append(amount-fees)
            decimals.append(mint_raw[44])
        _require(min(reserves) > 0, "ZERO_NET_RESERVE")
        out.append(ReserveFact(pool,*mints,*reserves,*decimals,slot,observed,_utc(b.received_at),digest))
    return tuple(out)


def _price(response, *, reference_time, policy):
    _require(type(response) is OhlcvResponse, "OHLCV_RESPONSE_REQUIRED")
    req = response.request
    _require(type(req) is OhlcvRequest, "CANONICAL_OHLCV_REQUEST_REQUIRED")
    try:
        req.__post_init__()
    except (ValueError,TypeError):
        raise A1SourceError("INVALID_OHLCV_REQUEST") from None
    _require(_utc(req.reference_time) == _utc(reference_time)
             and timedelta(0) < req.timeout <= timedelta(seconds=30), "VALUATION_REFERENCE_OR_TIMEOUT")
    start, received = map(_utc, (response.started_at,response.received_at))
    _require(start <= received <= _utc(reference_time) and received-start <= req.timeout
             and response.transport_failure is None and type(response.http_status) is int
             and response.http_status == 200 and type(response.body) is bytes
             and 0 < len(response.body) <= req.max_response_bytes <= 1048576, "VALUATION_TRANSPORT_OR_BUDGET")
    try:
        request_id, base, quote, stamps, candles = _parse(response.body,req)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise A1SourceError("INVALID_USD_SOURCE_FACTS") from None
    stamp, close = candles[-1]
    observed = _EPOCH + timedelta(seconds=stamp)
    end = observed + timedelta(seconds=60)
    _require(stamp == req.cutoff-60 and end <= received
             and _utc(reference_time)-observed <= policy.stale_after, "STALE_OR_MISSING_CLOSED_INTERVAL")
    _require(close.is_finite() and close > 0, "INVALID_USD_PRICE")
    return observed,end,Fraction(close),received,[req.chain_id,req.pool_address,req.token_mint,
        base,quote,dict(req.parameters),request_id,list(stamps),
        hashlib.sha256(response.body).hexdigest(),start.isoformat(),received.isoformat(),
        observed.isoformat(),end.isoformat(),str(Fraction(close)),"NOT_PROVIDED"]


@dataclass(frozen=True)
class A1ValuationFact:
    observation: CanonicalPoolObservation
    lineage_json: str


def map_valuation(reserve, mint, responses, *, reference_time, policy):
    """Two exact USD predecessors, one final rational round-down, canonical pool projection."""
    _require(type(policy) is A1Policy, "CANONICAL_POLICY_REQUIRED")
    policy.validate()
    _require(type(reserve) is ReserveFact and mint in (reserve.mint_0,reserve.mint_1)
             and type(responses) is tuple and len(responses) == 2, "TWO_RESERVE_VALUATIONS_REQUIRED")
    reserve.__post_init__()
    _require(reserve.observed_at <= reserve.received_at <= _utc(reference_time)
             and _utc(reference_time)-reserve.observed_at <= policy.stale_after, "STALE_RESERVE")
    prices = []
    for asset,response in zip((reserve.mint_0,reserve.mint_1),responses):
        _require(type(response) is OhlcvResponse and type(response.request) is OhlcvRequest and response.request.token_mint == asset
                 and response.request.pool_address == reserve.pool
                 and {response.request.base_mint,response.request.quote_mint} == {reserve.mint_0,reserve.mint_1}, "USD_IDENTITY_MISMATCH")
        price = _price(response,reference_time=reference_time,policy=policy)
        _require(max(abs(reserve.observed_at-price[0]),abs(reserve.observed_at-price[1])) <= policy.max_skew, "RESERVE_PRICE_SKEW")
        prices.append(price)
    _require(prices[0][:2] == prices[1][:2], "VALUATION_INTERVAL_MISMATCH")
    total = Fraction(reserve.reserve_0,10**reserve.decimals_0)*prices[0][2] + Fraction(reserve.reserve_1,10**reserve.decimals_1)*prices[1][2]
    units = total.numerator*1000000//total.denominator
    _require(units > 0, "ZERO_ROUNDED_LIQUIDITY")
    liquidity = Decimal(f"{units//1000000}.{units%1000000:06d}")
    packet = {"version":VERSION,"source_pin":SOURCE_PIN,"reserve":{
        **reserve.__dict__,"observed_at":_utc(reserve.observed_at).isoformat(),
        "received_at":_utc(reserve.received_at).isoformat()},"usd":[p[4] for p in prices],
        "reference":_utc(reference_time).isoformat(),"stale_after_us":policy.stale_after//timedelta(microseconds=1),
        "skew_us":policy.max_skew//timedelta(microseconds=1),"rounding":"sum_then_floor_6_usd",
        "liquidity_microusd":units}
    quote = reserve.mint_1 if mint == reserve.mint_0 else reserve.mint_0
    observation = CanonicalPoolObservation("solana",mint,reserve.pool,mint,quote,liquidity,
        VERSION,"a1-liquidity:"+_digest(packet),_utc(reserve.observed_at),
        max(reserve.received_at,prices[0][3],prices[1][3]))
    return A1ValuationFact(observation,json.dumps(packet,sort_keys=True,separators=(",", ":")))


def value_pool(reserve, mint, responses, *, reference_time, policy):
    return map_valuation(reserve,mint,responses,reference_time=reference_time,policy=policy).observation


class OfflineA1DiscoverySource:
    def __init__(self, envelopes, policy):
        self.envelopes, self.policy, self.called = envelopes, policy, False
        self.facts = None
        self.reference_time = None

    def discover_once(self, *, reference_time):
        _require(not self.called, "SECOND_DISCOVERY_FORBIDDEN")
        self.called = True
        self.facts = map_discovery(self.envelopes,reference_time=reference_time,policy=self.policy)
        self.reference_time = _utc(reference_time)
        return self.facts.batch


class OfflineA1PoolSource:
    """Required injected envelope suppliers; no default or operational transport.

    One reserve supplier call returns the exact two RPC envelopes. One USD
    supplier call per unique pool returns the exact two OHLCV envelopes. The
    suppliers must be server-side trusted fact providers, never browser input.
    """
    def __init__(self, discovery, reserve_supplier, usd_supplier):
        _require(type(discovery) is OfflineA1DiscoverySource and callable(reserve_supplier)
                 and callable(usd_supplier), "INJECTED_SOURCE_REQUIRED")
        self.discovery = discovery
        self.reserve_supplier = reserve_supplier
        self.usd_supplier = usd_supplier
        self.called_tokens = set()
        self.valuation_facts = {}
        self.reserve_envelopes = {}
        self.usd_envelopes = {}

    def pools_once(self, candidate, *, reference_time):
        facts = self.discovery.facts
        _require(type(facts) is A1DiscoveryFacts and self.discovery.reference_time == _utc(reference_time), "EXACT_DISCOVERY_REFERENCE_REQUIRED")
        tokens = sorted({m for s in facts.swaps for m in (s.mint_0,s.mint_1)})[:5]
        _require(type(candidate) is DiscoveredCandidate, "ADMITTED_CANDIDATE_REQUIRED")
        mint = candidate.token_mint
        event_ids = {o.raw_event.payload["token_identity"]: o.raw_event.source_event_id
                     for o in facts.batch.observations}
        _require(candidate.chain_id == "solana" and mint in tokens
                 and candidate.source_event_id == event_ids.get(mint)
                 and candidate.candidate_id == "candidate:"+hashlib.sha256(json.dumps(["solana",mint],separators=(",",":")).encode()).hexdigest(), "ADMITTED_CANDIDATE_REQUIRED")
        _require(mint not in self.called_tokens, "SECOND_POOL_INVOCATION_FORBIDDEN")
        self.called_tokens.add(mint)
        try:
            keys = pool_account_keys(facts,mint)
            envelopes = self.reserve_supplier(candidate,keys)
            reserves = map_reserves(facts,mint,envelopes,
                                    reference_time=reference_time,policy=self.discovery.policy)
            responses, valuations = [], []
            for reserve in reserves:
                response = self.usd_supplier(reserve)
                valuations.append(map_valuation(reserve,mint,response,reference_time=reference_time,
                                                 policy=self.discovery.policy))
                responses.append(response)
            self.valuation_facts[mint] = tuple(valuations)
            self.reserve_envelopes[mint] = envelopes
            self.usd_envelopes[mint] = tuple(responses)
            return tuple(v.observation for v in valuations)
        except A1SourceError:
            raise
        except Exception:
            raise A1SourceError("INJECTED_SOURCE_UNAVAILABLE") from None
