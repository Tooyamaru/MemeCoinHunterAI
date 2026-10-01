"""Synthetic transport contracts; socket access is forbidden."""
import json
import socket
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from core.data.a1_bounded_transport import A1BoundedTransport, A1HttpRequest
from core.data.a1_cpmm_sources import A1SourceError

NOW = datetime(2026, 10, 1, 12, 0, 10, tzinfo=timezone.utc)


class Ledger:
    def __init__(self, limit=10):
        self.attempts, self.receipts, self.limit = [], [], limit
        self.aborted = False

    def check_time(self, now):
        if self.aborted:
            raise A1SourceError("COLLECTION_BUDGET_CLOSED")
        return now

    def abort(self):
        self.aborted = True

    def reserve_attempt(self, **values):
        self.check_time(values["now"])
        if len(self.attempts) >= self.limit:
            raise A1SourceError("BUDGET_EXHAUSTED")
        self.attempts.append(values)

    def observe_receipt(self, **values):
        self.receipts.append(values)


class Response:
    def __init__(self, body=b'{}', status=200, final_url=None, error=None):
        self.body, self.status, self.final_url, self.error = body, status, final_url, error
        self.closed, self.read_sizes = False, []
        self.headers = {}

    def read(self, amount):
        self.read_sizes.append(amount)
        if self.error:
            raise self.error
        value, self.body = self.body[:amount], self.body[amount:]
        return value

    def close(self):
        self.closed = True


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.socket_guard = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self.socket_guard.start()
        self.addCleanup(self.socket_guard.stop)
        self.calls = []
        self.ledger = Ledger()

    def transport(self, response=None, clock=lambda: NOW, error=None):
        def opener(request, *, timeout):
            attempts = self.ledger.attempts if hasattr(self.ledger, "attempts") else self.ledger.snapshot().attempts
            self.calls.append((request, timeout, len(attempts)))
            if error:
                raise error
            return response
        return A1BoundedTransport(rpc_endpoint="https://rpc.example.test", opener=opener,
                                  clock=clock, ledger=self.ledger)

    def request(self, cap=8192):
        return A1HttpRequest("valuation", "https://api.coingecko.com/test", "GET", b"", timedelta(seconds=3), cap)

    def test_success_exact_timeout_and_charge_before_opener(self):
        response = Response(b'{}')
        receipt = self.transport(response).http(self.request())
        self.assertEqual(receipt.body, b'{}')
        self.assertEqual(self.calls[0][1:], (3.0, 1))
        self.assertFalse(self.calls[0][0].follow_redirects)
        self.assertEqual(self.calls[0][0].retries, 0)
        self.assertTrue(response.closed)
        self.assertEqual(self.ledger.receipts, [{"now": NOW, "bodylen": 2}])

    def test_error_does_not_retry(self):
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_TIMEOUT$'):
            self.transport(error=TimeoutError('secret detail')).http(self.request())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.ledger.attempts), 1)

    def test_redirect_and_http_errors_refused_without_body_read(self):
        for status in (301, 302, 307, 308, 400, 401, 429, 500):
            with self.subTest(status=status):
                self.ledger = Ledger()
                response = Response(status=status)
                with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_HTTP_ERROR$'):
                    self.transport(response).http(self.request())
                self.assertFalse(response.read_sizes)
                self.assertTrue(response.closed)

    def test_final_location_mismatch_refused(self):
        response = Response(final_url='https://other.test/')
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_REDIRECT_REFUSED$'):
            self.transport(response).http(self.request())
        self.assertFalse(response.read_sizes)
        self.assertTrue(response.closed)

    def test_streaming_byte_cap(self):
        response = Response(b'123456')
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_RESPONSE_TOO_LARGE$'):
            self.transport(response).http(self.request(cap=5))
        self.assertEqual(response.read_sizes, [6])
        self.assertTrue(response.closed)
        self.assertEqual(len(self.calls), 1)

    def test_deadline_after_slow_read(self):
        times = iter((NOW, NOW, NOW, NOW+timedelta(seconds=4), NOW+timedelta(seconds=4)))
        response = Response(b'{}')
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_TIMEOUT$'):
            self.transport(response, clock=lambda: next(times)).http(self.request())
        self.assertTrue(response.closed)
        self.assertEqual(len(self.calls), 1)

    def test_budget_exhausted_before_transport(self):
        self.ledger.limit = 0
        with self.assertRaisesRegex(A1SourceError, '^BUDGET_EXHAUSTED$'):
            self.transport(Response()).http(self.request())
        self.assertEqual(self.calls, [])

    def test_rpc_exact_id_and_parameters(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 17, "result": 12}).encode()
        envelope = self.transport(Response(body)).rpc('getSlot', [{"commitment": "finalized"}], request_id=17)
        self.assertEqual(envelope.read('getSlot', [{"commitment": "finalized"}], NOW, 8192), 12)
        submitted = json.loads(self.calls[0][0].body)
        self.assertEqual(submitted, {"jsonrpc": "2.0", "id": 17, "method": "getSlot", "params": [{"commitment": "finalized"}]})

    def test_rpc_invalid_id_and_json_fail_closed(self):
        for body in (b'{', b'{"jsonrpc":"2.0","id":18,"result":1}',
                     b'{"jsonrpc":"2.0","id":17,"result":NaN}',
                     b'{"jsonrpc":"2.0","id":17,"result":1,"result":2}',
                     b'{"jsonrpc":"2.0","id":17,"error":{"secret":"x"}}'):
            with self.subTest(body=body):
                self.ledger = Ledger()
                with self.assertRaises(A1SourceError):
                    self.transport(Response(body)).rpc('getSlot', [], request_id=17)

    def test_rpc_invalid_config_before_io(self):
        for method, request_id, params in [('sendTransaction', 1, []), ('getSlot', True, []), ('getSlot', 0, []), ('getSlot', 1, [float('nan')])]:
            with self.subTest(method=method, request_id=request_id):
                with self.assertRaises(A1SourceError):
                    self.transport(Response()).rpc(method, params, request_id=request_id)
        self.assertEqual(self.calls, [])

    def test_request_identity_deterministic_and_bounded(self):
        a, b = self.request(), self.request()
        self.assertEqual(a.request_identity, b.request_identity)
        self.assertNotEqual(a.request_identity, self.request(100).request_identity)
        with self.assertRaises(A1SourceError):
            A1HttpRequest('solana', 'https://rpc.test', 'POST', b'{}', timedelta(seconds=11), 8192)
        with self.assertRaises(A1SourceError):
            A1HttpRequest('solana', 'http://rpc.test', 'POST', b'{}', timedelta(seconds=10), 8192)

    def real_ledger(self, aggregate=timedelta(seconds=20)):
        from core.data.a1_collection_budget import A1BudgetLedger, A1OperationalBudget
        return A1BudgetLedger(A1OperationalBudget(aggregate), "test:transport", NOW,
                              "https://rpc.example.test", "https://api.coingecko.com")

    def test_real_ledger_aborts_http_failure_and_refuses_next_call(self):
        self.ledger = self.real_ledger()
        runner = self.transport(Response(status=429))
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_HTTP_ERROR$'):
            runner.http(self.request())
        with self.assertRaisesRegex(A1SourceError, 'COLLECTION_BUDGET_CLOSED'):
            runner.http(self.request())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.ledger.snapshot().attempts), 1)

    def test_real_ledger_aborts_malformed_rpc_and_refuses_next_call(self):
        self.ledger = self.real_ledger()
        runner = self.transport(Response(b'{'))
        with self.assertRaises(A1SourceError):
            runner.rpc('getSlot', [], request_id=17)
        with self.assertRaisesRegex(A1SourceError, 'COLLECTION_BUDGET_CLOSED'):
            runner.rpc('getSlot', [], request_id=18)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.ledger.snapshot().attempts), 1)

    def test_real_ledger_declared_deadline_before_opener(self):
        self.ledger = self.real_ledger(timedelta(seconds=2))
        with self.assertRaisesRegex(A1SourceError, 'AGGREGATE_DEADLINE'):
            self.transport(Response()).http(self.request())
        self.assertEqual(self.calls, [])

    def test_real_ledger_checks_slow_opener_and_closes(self):
        self.ledger = self.real_ledger()
        response = Response()
        times = iter((NOW, NOW+timedelta(seconds=4), NOW+timedelta(seconds=4)))
        with self.assertRaisesRegex(A1SourceError, 'REQUEST_DEADLINE'):
            self.transport(response, clock=lambda: next(times)).http(self.request())
        self.assertTrue(response.closed)
        self.assertEqual(response.read_sizes, [])
        self.assertEqual(len(self.calls), 1)

    def test_missing_injections_refused_without_io(self):
        with self.assertRaises(A1SourceError):
            A1BoundedTransport(rpc_endpoint='https://rpc.test', opener=None, clock=lambda: NOW, ledger=self.ledger)
        self.assertEqual(self.calls, [])

    def test_backwards_clock_refused(self):
        times = iter((NOW, NOW, NOW-timedelta(seconds=1), NOW-timedelta(seconds=1)))
        with self.assertRaisesRegex(A1SourceError, '^TRANSPORT_TIMEOUT$'):
            self.transport(Response(), clock=lambda: next(times)).http(self.request())
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
