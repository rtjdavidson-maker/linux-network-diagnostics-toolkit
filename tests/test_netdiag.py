import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import main
from netdiag import (
    CheckResult, build_report, check_dns, check_http, check_ping,
    check_tcp, demo_results, ping_command, render_html, save_report,
)


class NetworkDiagnosticsTests(unittest.TestCase):
    def test_demo_has_four_clearly_labeled_examples(self):
        self.assertEqual(len(demo_results()), 4)
        self.assertTrue(all(result.status == "DEMO" for result in demo_results()))

    def test_dns_success(self):
        records = [(None, None, None, None, ("203.0.113.1", 0)),
                   (None, None, None, None, ("203.0.113.1", 0))]
        with patch("netdiag.socket.getaddrinfo", return_value=records):
            result = check_dns("example.test")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.detail, "Resolved: 203.0.113.1")

    def test_dns_failure(self):
        with patch("netdiag.socket.getaddrinfo", side_effect=OSError("no DNS")):
            self.assertEqual(check_dns("bad.test").status, "FAIL")

    def test_tcp_success(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        with patch("netdiag.socket.create_connection", return_value=connection) as connect:
            result = check_tcp("localhost", 443)
        self.assertEqual(result.status, "PASS")
        connect.assert_called_once_with(("localhost", 443), timeout=3.0)

    def test_tcp_refused(self):
        with patch("netdiag.socket.create_connection", side_effect=OSError("refused")):
            self.assertEqual(check_tcp("localhost", 10).status, "FAIL")

    def test_tcp_invalid_port(self):
        with self.assertRaises(ValueError):
            check_tcp("localhost", 65536)

    def test_http_success(self):
        response = Mock(status=204)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("netdiag.request.urlopen", return_value=response):
            self.assertEqual(check_http("https://example.test/").status, "PASS")

    def test_http_error_status(self):
        from urllib.error import HTTPError
        exc = HTTPError("https://example.test/", 404, "Missing", {}, None)
        with patch("netdiag.request.urlopen", side_effect=exc):
            result = check_http("https://example.test/")
        self.assertEqual(result.status, "FAIL")
        self.assertIn("404", result.detail)

    def test_http_rejects_invalid_url(self):
        with self.assertRaises(ValueError):
            check_http("file:///somewhere")

    def test_ping_command_windows(self):
        self.assertEqual(ping_command("example.test", system="Windows"),
                         ["ping", "-n", "1", "-w", "2000", "example.test"])

    def test_ping_command_linux(self):
        self.assertEqual(ping_command("example.test", system="Linux"),
                         ["ping", "-c", "1", "-W", "2", "example.test"])

    def test_ping_rejects_option_injection(self):
        with self.assertRaises(ValueError):
            ping_command("-help", system="Linux")

    def test_ping_success(self):
        with patch("netdiag.subprocess.run", return_value=Mock(returncode=0)):
            self.assertEqual(check_ping("localhost").status, "PASS")

    def test_ping_timeout(self):
        import subprocess
        with patch("netdiag.subprocess.run", side_effect=subprocess.TimeoutExpired("ping", 5)):
            self.assertEqual(check_ping("localhost").status, "ERROR")

    def test_report_counts(self):
        r = [CheckResult("DNS", "a", "PASS", "ok", 1),
             CheckResult("TCP", "b", "FAIL", "bad", 2),
             CheckResult("PING", "c", "ERROR", "err", 3)]
        report = build_report(r)
        self.assertEqual((report["checks_total"], report["passed"], report["failed"], report["errors"]), (3, 1, 1, 1))

    def test_report_empty_rejected(self):
        with self.assertRaises(ValueError):
            build_report([])

    def test_html_escapes_target(self):
        report = build_report([CheckResult("DNS", "<script>alert(1)</script>", "FAIL", "<bad>", 2)])
        html = render_html(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;bad&gt;", html)

    def test_save_report_creates_html_and_json(self):
        with TemporaryDirectory() as folder:
            report = build_report(demo_results(), demo=True)
            j, h = save_report(report, Path(folder) / "nested")
            self.assertTrue(j.is_file() and h.is_file())
            self.assertEqual(json.loads(j.read_text())["mode"], "SIMULATED DEMO — NO NETWORK CHECKS")

    def test_cli_demo_creates_reports(self):
        with TemporaryDirectory() as folder:
            self.assertEqual(main.run(["--demo", "--output", folder]), 0)
            self.assertTrue((Path(folder) / "report.html").exists())

    def test_cli_needs_explicit_target(self):
        with self.assertRaises(SystemExit):
            main.run([])

    def test_cli_rejects_incomplete_port(self):
        with self.assertRaises(SystemExit):
            main.run(["--port", "443"])


if __name__ == "__main__":
    unittest.main()
