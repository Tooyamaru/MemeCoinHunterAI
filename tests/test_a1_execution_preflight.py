from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.a1_execution_preflight import A1PreflightError, check_preparation, main


def manifest():
    return {"environment":"test", "expected_environment":"test", "workers":1, "reload":False,
        "database_configured":True, "operator_configured":True,
        "solana_provider_configured":True, "coingecko_provider_configured":True,
        "process_local_acknowledged":False, "simulation_only":True,
        "offline_preparation_authorized":True}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.socket = patch("socket.create_connection", side_effect=AssertionError("network prohibited"))
        self.connect = patch("socket.socket.connect", side_effect=AssertionError("network prohibited"))
        self.socket.start(); self.connect.start()
        self.addCleanup(self.socket.stop); self.addCleanup(self.connect.stop)

    def test_configuration_pass_is_never_operational_authority(self):
        result = asdict(check_preparation(manifest()))
        self.assertEqual(result["status"], "OFFLINE_CONFIGURATION_CHECKED")
        self.assertTrue(result["simulation_only"])
        self.assertFalse(result["provider_execution_authorized"])
        self.assertFalse(result["provider_contacted"])
        for name in ("database_connection", "qualifying_runtime", "cluster_verification", "program_verification",
                     "collection_budget", "reference_lifecycle", "persistence_readback"):
            self.assertEqual(result[name], "PENDING")

    def test_configuration_cannot_skip_environment_process_or_authority(self):
        for key, value in (("expected_environment","production"), ("workers",2), ("workers",True),
                           ("reload",True), ("simulation_only",False), ("offline_preparation_authorized",False),
                           ("database_configured",False), ("operator_configured",False),
                           ("solana_provider_configured",False), ("coingecko_provider_configured",False)):
            data = manifest(); data[key] = value
            with self.subTest(key=key), self.assertRaises(A1PreflightError):
                check_preparation(data)

    def test_staging_requires_local_ack(self):
        data=manifest(); data.update(environment="staging", expected_environment="staging")
        with self.assertRaisesRegex(A1PreflightError,"ACK_REQUIRED"):
            check_preparation(data)
        data["process_local_acknowledged"]=True
        self.assertEqual(check_preparation(data).environment,"staging")

    def test_unknown_fields_secrets_and_truthy_strings_rejected(self):
        for key, value in (("solana_rpc_url","https://secret.example/key"),
                           ("provider_execution_authorized",True), ("database_configured","true")):
            data=manifest(); data[key]=value
            with self.subTest(key=key), self.assertRaises(A1PreflightError):
                check_preparation(data)
        data=manifest(); data.pop("operator_configured")
        with self.assertRaises(A1PreflightError): check_preparation(data)

    def run_cli(self, raw):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"manifest.json"; path.write_bytes(raw)
            out=io.StringIO()
            with redirect_stdout(out):
                status=main(["--check-only","--manifest",str(path)])
            return status,json.loads(out.getvalue())

    def test_cli_check_only_success_without_launch_or_environment_access(self):
        with patch.dict("os.environ",{},clear=True):
            status, result=self.run_cli(json.dumps(manifest()).encode())
        self.assertEqual(status,0)
        self.assertEqual(result["status"],"OFFLINE_CONFIGURATION_CHECKED")
        self.assertFalse(result["provider_contacted"])

    def test_cli_malformed_duplicate_oversize_and_secret_are_sanitized(self):
        secret=b'private-token-must-never-print'
        for raw in (b'{',b'{"workers":1,"workers":2}', b' '*32769,
                    json.dumps({**manifest(),"api_key":secret.decode()}).encode()):
            with self.subTest(rawlen=len(raw)):
                status,result=self.run_cli(raw)
                self.assertEqual(status,2)
                self.assertFalse(result["provider_execution_authorized"])
                self.assertNotIn(secret.decode(),json.dumps(result))

    def test_cli_has_no_execution_mode(self):
        with patch("sys.stderr",new=io.StringIO()), self.assertRaises(SystemExit) as result:
            main(["--manifest","unused.json"])
        self.assertEqual(result.exception.code,2)


if __name__ == "__main__": unittest.main()
