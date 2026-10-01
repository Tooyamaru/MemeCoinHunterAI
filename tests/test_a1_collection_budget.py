"""Exact collection-local reuse and fail-before-I/O accounting."""
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock,patch
from core.data.a1_collection_budget import (
    A1OperationalBudget,A1BudgetLedger,A1ValuationRequestKey,A1CollectionRequestRegistry,
)
from core.data.a1_cpmm_sources import A1SourceError,_encode
from core.data.coingecko_onchain_ohlcv import OhlcvRequest,ENDPOINT_VERSION
from core.data.a1_bounded_transport import A1HttpRequest,A1HttpReceipt

T=datetime(2026,10,1,8,5,10,tzinfo=timezone.utc)
POOL=_encode(bytes([3])*32)
BASE=_encode(bytes([1])*32)
QUOTE=_encode(bytes([2])*32)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.socket=patch('socket.socket.connect',side_effect=AssertionError('No network'))
        self.socket.start()
        self.addCleanup(self.socket.stop)

    def ledger(self,**caps):
        return A1BudgetLedger(A1OperationalBudget(timedelta(seconds=55),**caps),'c1',T,'https://rpc.example','https://api.coingecko.com')

    def attempt(self,ledger,**overrides):
        args=dict(kind='solana',host='rpc.example',response_cap=8192,timeout=timedelta(seconds=10),now=T)
        args.update(overrides)
        return ledger.reserve_attempt(**args)

    def test_accounting_snapshot_is_immutable(self):
        ledger=self.ledger()
        self.assertEqual(self.attempt(ledger),1)
        ledger.observe_receipt(now=T+timedelta(seconds=1),bodylen=100)
        snap=ledger.seal(T+timedelta(seconds=2))
        self.assertEqual((snap.reserved_response_bytes,snap.actual_response_bytes),(8192,100))
        self.assertEqual(snap.attempts[0].received_at,T+timedelta(seconds=1))
        with self.assertRaises(AttributeError): snap.reserved_response_bytes=1
        with self.assertRaises(A1SourceError): self.attempt(ledger)

    def test_call_budget_before_injected_call(self):
        ledger=self.ledger(max_http_calls=1)
        opener=Mock()
        for i in range(2):
            try:
                self.attempt(ledger)
            except A1SourceError:
                break
            opener()
            ledger.observe_receipt(now=T,bodylen=0)
        self.assertEqual(opener.call_count,1)
        self.assertEqual(len(ledger.snapshot().attempts),1)

    def test_no_refund_failed_attempt(self):
        ledger=self.ledger(max_http_calls=1)
        self.attempt(ledger)
        ledger.observe_receipt(now=T,bodylen=0)
        with self.assertRaises(A1SourceError): self.attempt(ledger)
        self.assertEqual(ledger.snapshot().reserved_response_bytes,8192)

    def test_host_and_kind_caps(self):
        for cap,kind,host in [('max_solana_host_calls','solana','rpc.example'),('max_solana_calls','safety','rpc.example'),('max_valuation_requests','valuation','api.coingecko.com'),('max_diagnostics','diagnostic','api.coingecko.com'),('max_safety_calls','safety','rpc.example')]:
            with self.subTest(cap=cap):
                ledger=self.ledger(**{cap:0})
                with self.assertRaises(A1SourceError): self.attempt(ledger,kind=kind,host=host)
                self.assertFalse(ledger.snapshot().attempts)

    def test_reserved_bytes_checked_before_call(self):
        ledger=self.ledger(max_total_response_bytes=8191)
        with self.assertRaises(A1SourceError): self.attempt(ledger)
        self.assertFalse(ledger.snapshot().attempts)

    def test_wrong_host_timeout_and_deadline(self):
        for values in [dict(host='wrong.example'),dict(timeout=timedelta(seconds=11)),dict(now=T+timedelta(seconds=55)),dict(now=T-timedelta(seconds=1)),dict(response_cap=True)]:
            with self.subTest(values=values):
                ledger=self.ledger()
                with self.assertRaises(A1SourceError): self.attempt(ledger,**values)
                self.assertFalse(ledger.snapshot().attempts)

    def test_receipt_size_and_deadline_stop_collection(self):
        for now,length in [(T,8193),(T+timedelta(seconds=11),1),(T-timedelta(seconds=1),1)]:
            ledger=self.ledger()
            self.attempt(ledger)
            with self.assertRaises(A1SourceError): ledger.observe_receipt(now=now,bodylen=length)
            with self.assertRaises(A1SourceError): self.attempt(ledger)
            with self.assertRaises(A1SourceError): ledger.seal(T)

    def test_aggregate_receipt_deadline(self):
        ledger=self.ledger()
        opener=Mock()
        with self.assertRaises(A1SourceError):
            self.attempt(ledger,now=T+timedelta(seconds=54))
            opener()
        self.assertEqual(opener.call_count,0)
        self.assertFalse(ledger.snapshot().attempts)

    def test_monotonic_clock_checks_and_abort(self):
        ledger=self.ledger()
        self.attempt(ledger)
        ledger.check_time(T+timedelta(seconds=2))
        with self.assertRaises(A1SourceError): ledger.check_time(T+timedelta(seconds=1))
        with self.assertRaises(A1SourceError): ledger.observe_receipt(now=T+timedelta(seconds=3),bodylen=0)
        ledger=self.ledger()
        self.attempt(ledger)
        ledger.abort()
        self.assertEqual(ledger.snapshot().reserved_response_bytes,8192)
        with self.assertRaises(A1SourceError): self.attempt(ledger)
        with self.assertRaises(A1SourceError): ledger.seal(T)

    def test_only_zero_retry_scheduler(self):
        for values in [dict(retries=1),dict(scheduler=1),dict(max_http_calls=116),dict(aggregate_timeout=timedelta(seconds=181))]:
            args=dict(aggregate_timeout=timedelta(seconds=55));args.update(values)
            with self.assertRaises(A1SourceError): A1OperationalBudget(**args)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.socket=patch('socket.socket.connect',side_effect=AssertionError('No network'))
        self.socket.start()
        self.addCleanup(self.socket.stop)

    def request(self,**values):
        args=dict(chain_id='solana',token_mint=BASE,pool_address=POOL,base_mint=BASE,quote_mint=QUOTE,reference_time=T,timeout=timedelta(seconds=10),max_response_bytes=8192)
        args.update(values)
        return OhlcvRequest(**args)

    def key(self,request=None,collection='c1'):
        req=request or self.request()
        return A1ValuationRequestKey.from_parameters(collection_id=collection,planned_cutoff=req.cutoff,endpoint_version=ENDPOINT_VERSION,endpoint_url=req.url,network=req.chain_id,pool=req.pool_address,mint=req.token_mint,parameters=req.parameters,base_mint=req.base_mint,quote_mint=req.quote_mint,timeout=req.timeout,maxbytes=req.max_response_bytes)

    def response(self,req=None):
        req=req or self.request()
        wire=A1HttpRequest('valuation',req.url,'GET',b'',req.timeout,req.max_response_bytes)
        return A1HttpReceipt(wire,T-timedelta(seconds=2),T-timedelta(seconds=1),b'{}',200)

    def test_duplicate_one_transport_and_same_lineage_object(self):
        req=self.request();key=self.key(req)
        registry=A1CollectionRequestRegistry('c1',req.cutoff)
        source=Mock(return_value=self.response(req))
        a=registry.get_or_collect(key,source)
        b=registry.get_or_collect(self.key(req),source)
        self.assertIs(a,b)
        self.assertEqual(source.call_count,1)
        uses=registry.seal(T)
        self.assertEqual([u.reused for u in uses],[False,True])
        self.assertEqual(uses[0].response_digest,uses[1].response_digest)
        self.assertEqual(uses[0].received_at,a.received_at)
        with self.assertRaises(A1SourceError): registry.get_or_collect(key,source)

    def test_non_equivalent_requests_never_collapse(self):
        reqs=[self.request(),self.request(token_mint=QUOTE),self.request(pool_address=_encode(bytes([4])*32)),self.request(timeout=timedelta(seconds=11)),self.request(max_response_bytes=8193),self.request(base_mint=QUOTE,quote_mint=BASE)]
        registry=A1CollectionRequestRegistry('c1',reqs[0].cutoff)
        sources=[Mock(return_value=self.response(req)) for req in reqs]
        for req,source in zip(reqs,sources): registry.get_or_collect(self.key(req),source)
        self.assertEqual(sum(s.call_count for s in sources),len(reqs))
        self.assertEqual(len({u.request_digest for u in registry.uses}),len(reqs))

    def test_no_cross_collection_or_cutoff_cache(self):
        req=self.request();source=Mock(return_value=self.response(req))
        a=A1CollectionRequestRegistry('c1',req.cutoff)
        b=A1CollectionRequestRegistry('c2',req.cutoff)
        a.get_or_collect(self.key(req),source)
        b.get_or_collect(self.key(req,collection='c2'),source)
        self.assertEqual(source.call_count,2)
        with self.assertRaises(A1SourceError): b.get_or_collect(self.key(req),source)
        later=self.request(reference_time=T+timedelta(minutes=1))
        with self.assertRaises(A1SourceError): b.get_or_collect(self.key(later,collection='c2'),source)
        self.assertEqual(source.call_count,2)

    def test_deterministic_key_and_unsupported_contract_rejected(self):
        key=self.key()
        self.assertEqual(key.request_digest,self.key().request_digest)
        for values in [dict(endpoint_version='pro'),dict(endpoint_url='https://other.example'),dict(parameters=key.parameters+(('extra','true'),))]:
            bad=replace(key,**values)
            with self.assertRaises(A1SourceError): bad.validate()

    def test_failed_response_no_retry(self):
        registry=A1CollectionRequestRegistry('c1',self.request().cutoff)
        source=Mock(return_value=replace(self.response(),status=429))
        with self.assertRaises(A1SourceError): registry.get_or_collect(self.key(),source)
        with self.assertRaises(A1SourceError): registry.get_or_collect(self.key(),source)
        self.assertEqual(source.call_count,1)

    def test_seal_rejects_rollover_and_future_receipt(self):
        for response,Tfinal in [(self.response(),T+timedelta(minutes=1)),(replace(self.response(),started_at=T,received_at=T+timedelta(seconds=1)),T)]:
            registry=A1CollectionRequestRegistry('c1',self.request().cutoff)
            registry.get_or_collect(self.key(),lambda:response)
            with self.assertRaises(A1SourceError): registry.seal(Tfinal)
            with self.assertRaises(A1SourceError): registry.seal(T)

    def test_request_count_tight_bound_and_dedup(self):
        mints=[_encode(bytes([i])*32) for i in range(1,6)]
        reqs=[];degrees=[0]*5
        for edge,count in enumerate((7,6,7,6,6)):
            a,b=edge,(edge+1)%5
            for offset in range(count):
                pool=_encode(bytes([10+len(reqs)//2])*32)
                for token in (mints[a],mints[b]):
                    reqs.append(self.request(token_mint=token,pool_address=pool,base_mint=mints[a],quote_mint=mints[b]))
                degrees[a]+=1;degrees[b]+=1
        self.assertEqual(sum(degrees),64)
        self.assertLessEqual(max(degrees),20)
        registry=A1CollectionRequestRegistry('c1',reqs[0].cutoff)
        source_calls=0
        # Every pool is visited by both candidate endpoints, each requesting both mint prices.
        for req in reqs+reqs:
            def collect(req=req):
                nonlocal source_calls
                source_calls+=1
                return self.response(req)
            registry.get_or_collect(self.key(req),collect)
        self.assertEqual(len(reqs+reqs),128)
        self.assertEqual(source_calls,64)
        self.assertEqual(sum(u.reused for u in registry.uses),64)


if __name__ == '__main__': unittest.main()
