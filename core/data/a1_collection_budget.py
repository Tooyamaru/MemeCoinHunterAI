"""Finite collection accounting and exact collection-local request reuse; no I/O."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from urllib.parse import urlsplit
from core.data.a1_cpmm_sources import A1SourceError
from core.data.coingecko_onchain_ohlcv import OhlcvRequest, ENDPOINT_VERSION

VERSION = 'a1-collection-budget-v1'


def require(condition, reason):
    if not condition:
        raise A1SourceError(reason)


def utc(value):
    require(type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None, 'BUDGET_CLOCK_REQUIRED')
    return value.astimezone(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':')).encode()).hexdigest()


def hostname(endpoint):
    require(type(endpoint) is str, 'BUDGET_HOST_REQUIRED')
    parsed = urlsplit(endpoint)
    require(parsed.scheme == 'https' and parsed.hostname is not None, 'BUDGET_HOST_REQUIRED')
    return parsed.hostname.lower()


@dataclass(frozen=True)
class A1OperationalBudget:
    aggregate_timeout: timedelta
    max_solana_calls: int = 46
    max_http_calls: int = 115
    max_solana_host_calls: int = 46
    max_coingecko_host_calls: int = 69
    max_total_response_bytes: int = 86597632
    max_valuation_requests: int = 64
    max_diagnostics: int = 5
    max_safety_calls: int = 30
    max_discovery_candidates: int = 5
    max_pools_per_candidate: int = 20
    retries: int = 0
    scheduler: int = 0
    contract_version: str = VERSION

    def __post_init__(self):
        require(type(self.aggregate_timeout) is timedelta and timedelta(0) < self.aggregate_timeout <= timedelta(seconds=180), 'INVALID_AGGREGATE_DEADLINE')
        caps = {'max_solana_calls':46,'max_http_calls':115,'max_solana_host_calls':46,
                'max_coingecko_host_calls':69,'max_total_response_bytes':86597632,
                'max_valuation_requests':64,'max_diagnostics':5,'max_safety_calls':30,
                'max_discovery_candidates':5,'max_pools_per_candidate':20}
        for name, maximum in caps.items():
            value = getattr(self,name)
            require(type(value) is int and 0 <= value <= maximum, 'INVALID_OPERATIONAL_CAP')
        require(type(self.retries) is int and self.retries == 0 and type(self.scheduler) is int and self.scheduler == 0 and self.contract_version == VERSION, 'RETRY_OR_SCHEDULER_FORBIDDEN')


@dataclass(frozen=True)
class A1BudgetAttempt:
    identity: int
    kind: str
    host: str
    response_cap: int
    timeout: timedelta
    started_at: datetime
    received_at: datetime | None = None
    response_bytes: int | None = None


@dataclass(frozen=True)
class A1BudgetSnapshot:
    collection_id: str
    attempts: tuple[A1BudgetAttempt, ...]
    reserved_response_bytes: int
    actual_response_bytes: int
    completed_at: datetime | None
    contract_version: str = VERSION


class A1BudgetLedger:
    def __init__(self, budget, collection_id, started_at, solana_endpoint, coingecko_origin):
        require(type(budget) is A1OperationalBudget, 'CANONICAL_BUDGET_REQUIRED')
        budget.__post_init__()
        require(type(collection_id) is str and 0 < len(collection_id) <= 128, 'COLLECTION_ID_REQUIRED')
        self.budget,self.collection_id,self.started_at = budget,collection_id,utc(started_at)
        self.solana_host,self.coingecko_host = hostname(solana_endpoint),hostname(coingecko_origin)
        require(self.solana_host != self.coingecko_host, 'DISTINCT_PROVIDER_HOSTS_REQUIRED')
        self._attempts=[]
        self._reserved=self._actual=0
        self._pending=None
        self._completed=None
        self._failed=False
        self._last_clock=self.started_at

    @property
    def aggregate_timeout(self):
        return self.budget.aggregate_timeout

    def abort(self):
        """Terminal failure without refunds or another attempt."""
        self._failed=True

    def check_time(self, now):
        require(not self._failed and self._completed is None, 'COLLECTION_BUDGET_CLOSED')
        try:
            now=utc(now)
            require(self._last_clock <= now and now-self.started_at <= self.budget.aggregate_timeout,
                    'AGGREGATE_DEADLINE')
            if self._pending is not None:
                require(now-self._pending.started_at <= self._pending.timeout, 'REQUEST_DEADLINE')
        except A1SourceError:
            self._failed=True
            raise
        self._last_clock=now
        return now

    def reserve_attempt(self, *, kind, host, response_cap, timeout, now):
        require(not self._failed and self._completed is None and self._pending is None, 'COLLECTION_BUDGET_CLOSED_OR_PENDING')
        now=self.check_time(now)
        require(kind in ('solana','valuation','diagnostic','safety'), 'INVALID_BUDGET_KIND')
        is_rpc=kind in ('solana','safety')
        expected=self.solana_host if is_rpc else self.coingecko_host
        require(type(host) is str and host == expected, 'UNEXPECTED_PROVIDER_HOST')
        maximum=timedelta(seconds=30 if kind in ('valuation','diagnostic','safety') else 10)
        require(type(timeout) is timedelta and timedelta(0) < timeout <= maximum, 'INVALID_REQUEST_TIMEOUT')
        require(type(response_cap) is int and 0 < response_cap <= (262144 if kind == 'safety' else 1048576), 'INVALID_RESPONSE_CAP')
        previous=self._attempts[-1].received_at if self._attempts else self.started_at
        require(previous <= now and now-self.started_at < self.budget.aggregate_timeout
                and timeout <= self.budget.aggregate_timeout-(now-self.started_at), 'AGGREGATE_DEADLINE')
        b=self.budget
        require(len(self._attempts) < b.max_http_calls, 'HTTP_CALL_BUDGET_EXHAUSTED')
        require(sum(a.kind in ('solana','safety') for a in self._attempts) < b.max_solana_calls if is_rpc else True, 'SOLANA_CALL_BUDGET_EXHAUSTED')
        require(sum(a.host == host for a in self._attempts) < (b.max_solana_host_calls if is_rpc else b.max_coingecko_host_calls), 'HOST_CALL_BUDGET_EXHAUSTED')
        cap={'valuation':b.max_valuation_requests,'diagnostic':b.max_diagnostics,'safety':b.max_safety_calls}.get(kind)
        require(cap is None or sum(a.kind == kind for a in self._attempts) < cap, 'KIND_CALL_BUDGET_EXHAUSTED')
        require(self._reserved + response_cap <= b.max_total_response_bytes, 'AGGREGATE_BYTE_BUDGET_EXHAUSTED')
        attempt=A1BudgetAttempt(len(self._attempts)+1,kind,host,response_cap,timeout,now)
        self._attempts.append(attempt)
        self._pending=attempt
        self._reserved+=response_cap
        return attempt.identity

    def observe_receipt(self, *, now, bodylen):
        require(not self._failed and self._completed is None and self._pending is not None, 'NO_PENDING_ATTEMPT')
        attempt=self._pending
        now=self.check_time(now)
        if not (type(bodylen) is int and 0 <= bodylen <= attempt.response_cap
                and attempt.started_at <= now and now-attempt.started_at <= attempt.timeout
                and now-self.started_at <= self.budget.aggregate_timeout):
            self._failed=True
            raise A1SourceError('RECEIPT_EXCEEDS_BUDGET')
        self._attempts[-1]=A1BudgetAttempt(attempt.identity,attempt.kind,attempt.host,attempt.response_cap,attempt.timeout,attempt.started_at,now,bodylen)
        self._actual+=bodylen
        self._pending=None

    def seal(self, completed_at):
        require(not self._failed and self._completed is None and self._pending is None, 'COLLECTION_BUDGET_CANNOT_SEAL')
        completed_at=self.check_time(completed_at)
        previous=self._attempts[-1].received_at if self._attempts else self.started_at
        require(previous <= completed_at and completed_at-self.started_at <= self.budget.aggregate_timeout, 'AGGREGATE_DEADLINE')
        self._completed=completed_at
        return self.snapshot()

    def snapshot(self):
        return A1BudgetSnapshot(self.collection_id,tuple(self._attempts),self._reserved,self._actual,self._completed)


@dataclass(frozen=True)
class A1ValuationRequestKey:
    collection_id: str
    planned_cutoff: int
    endpoint_version: str
    endpoint_url: str
    network: str
    pool: str
    mint: str
    parameters: tuple[tuple[str,str], ...]
    base_mint: str
    quote_mint: str
    timeout: timedelta
    maxbytes: int

    @classmethod
    def from_parameters(cls, **kwargs):
        value=cls(**kwargs)
        value.validate()
        return value

    def validate(self):
        require(type(self.collection_id) is str and 0 < len(self.collection_id) <= 128 and type(self.planned_cutoff) is int and 0 <= self.planned_cutoff < 253402300800 and self.planned_cutoff % 60 == 0, 'INVALID_REQUEST_CONTEXT')
        require(self.endpoint_version == ENDPOINT_VERSION and type(self.parameters) is tuple
                and all(type(p) is tuple and len(p) == 2 and all(type(v) is str for v in p) for p in self.parameters), 'INVALID_REQUEST_IDENTITY')
        try:
            req=OhlcvRequest(self.network,self.mint,self.pool,self.base_mint,self.quote_mint,
                             datetime.fromtimestamp(self.planned_cutoff,timezone.utc),self.timeout,self.maxbytes)
        except (ValueError,TypeError,OverflowError,OSError):
            raise A1SourceError('INVALID_REQUEST_IDENTITY') from None
        require(self.endpoint_url == req.url and self.parameters == req.parameters and self.timeout <= timedelta(seconds=30), 'EXACT_OHLCV_CONTRACT_REQUIRED')

    @property
    def request_digest(self):
        return digest({**self.__dict__,'timeout_us':self.timeout//timedelta(microseconds=1),'timeout':None})


@dataclass(frozen=True)
class A1RequestReuse:
    request_digest: str
    response_digest: str
    started_at: datetime
    received_at: datetime
    reused: bool


class A1CollectionRequestRegistry:
    def __init__(self, collection_id, planned_cutoff):
        require(type(collection_id) is str and 0 < len(collection_id) <= 128 and type(planned_cutoff) is int and 0 <= planned_cutoff < 253402300800 and planned_cutoff % 60 == 0, 'INVALID_REQUEST_CONTEXT')
        self.collection_id,self.planned_cutoff=collection_id,planned_cutoff
        self._responses={}
        self._uses=[]
        self._closed=False
        self.reference_time=None

    def get_or_collect(self, key, collect):
        require(not self._closed and type(key) is A1ValuationRequestKey and callable(collect), 'REQUEST_REGISTRY_CLOSED')
        key.validate()
        require(key.collection_id == self.collection_id and key.planned_cutoff == self.planned_cutoff, 'CROSS_COLLECTION_REUSE_FORBIDDEN')
        reused=key in self._responses
        if reused:
            response=self._responses[key]
        else:
            try:
                response=collect()
                from core.data.a1_bounded_transport import A1HttpReceipt,A1HttpRequest
                require(type(response) is A1HttpReceipt and type(response.request) is A1HttpRequest
                        and type(response.body) is bytes and 0 < len(response.body) <= key.maxbytes
                        and type(response.status) is int and response.status == 200, 'UNAVAILABLE_COLLECTION_RESPONSE')
                req=response.request
                req.__post_init__()
                require((req.scope,req.endpoint,req.method,req.body,req.timeout,req.max_response_bytes)
                        == ('valuation',key.endpoint_url,'GET',b'',key.timeout,key.maxbytes), 'RESPONSE_REQUEST_IDENTITY')
                require(utc(response.started_at) <= utc(response.received_at)
                        and response.received_at-response.started_at <= key.timeout, 'INVALID_REUSED_RECEIPT')
                self._responses[key]=response
            except Exception:
                self._closed=True
                raise A1SourceError('COLLECTION_REQUEST_FAILED') from None
        self._uses.append(A1RequestReuse(key.request_digest,hashlib.sha256(response.body).hexdigest(),utc(response.started_at),utc(response.received_at),reused))
        return response

    def seal(self, reference_time):
        require(not self._closed, 'REQUEST_REGISTRY_CLOSED')
        # A failed finalization is terminal; it cannot choose another T.
        self._closed=True
        reference_time=utc(reference_time)
        epoch=datetime(1970,1,1,tzinfo=timezone.utc)
        elapsed=reference_time-epoch
        require((elapsed.days*86400+elapsed.seconds)//60*60 == self.planned_cutoff and all(utc(r.received_at) <= reference_time for r in self._responses.values()), 'REFERENCE_CUTOFF_OR_RECEIPT_CONFLICT')
        self._closed=True
        self.reference_time=reference_time
        return tuple(self._uses)

    @property
    def entries(self):
        return tuple(self._responses.items())

    @property
    def uses(self):
        return tuple(self._uses)
