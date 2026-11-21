"""Network diagnostics for explicitly supplied, authorized single targets."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib import request, error
from urllib.parse import urlsplit
import json
import platform
import socket
import subprocess
import time


@dataclass(frozen=True)
class CheckResult:
    check: str
    target: str
    status: str
    detail: str
    elapsed_ms: float


def _elapsed(start):
    return round((time.perf_counter() - start) * 1000, 2)


def check_dns(host):
    start = time.perf_counter()
    try:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = sorted({r[4][0] for r in records})
        if not addresses:
            return CheckResult("DNS", host, "FAIL", "No DNS addresses returned", _elapsed(start))
        return CheckResult("DNS", host, "PASS", "Resolved: " + ", ".join(addresses), _elapsed(start))
    except (OSError, UnicodeError) as exc:
        return CheckResult("DNS", host, "FAIL", f"Resolution failed: {exc}", _elapsed(start))


def check_tcp(host, port, timeout=3.0):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    start = time.perf_counter()
    target = f"{host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return CheckResult("TCP", target, "PASS", "TCP connection established", _elapsed(start))
    except OSError as exc:
        return CheckResult("TCP", target, "FAIL", f"Connection failed: {exc}", _elapsed(start))


def check_http(url, timeout=5.0):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must begin with http:// or https:// and contain a hostname")
    start = time.perf_counter()
    try:
        req = request.Request(url, method="HEAD", headers={"User-Agent": "NetworkDiagnosticsPortfolio/1.0"})
        with request.urlopen(req, timeout=timeout) as response:
            status = response.status
            return CheckResult("HTTP", url, "PASS" if 200 <= status < 400 else "FAIL",
                               f"HTTP status {status}", _elapsed(start))
    except error.HTTPError as exc:
        return CheckResult("HTTP", url, "FAIL", f"HTTP status {exc.code}", _elapsed(start))
    except (error.URLError, OSError, ValueError) as exc:
        return CheckResult("HTTP", url, "FAIL", f"HTTP request failed: {exc}", _elapsed(start))


def ping_command(host, system=None):
    if not host or host.startswith("-") or any(c.isspace() for c in host):
        raise ValueError("Host cannot be blank, start with '-', or contain whitespace")
    system = system or platform.system()
    if system == "Windows":
        return ["ping", "-n", "1", "-w", "2000", host]
    if system == "Linux":
        return ["ping", "-c", "1", "-W", "2", host]
    if system == "Darwin":
        return ["ping", "-c", "1", "-W", "2000", host]
    raise ValueError(f"Unsupported platform for ping: {system}")


def check_ping(host):
    command = ping_command(host)
    start = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        passed = completed.returncode == 0
        note = "ICMP reply received" if passed else "No ICMP reply (host or firewall may block ping)"
        return CheckResult("PING", host, "PASS" if passed else "FAIL", note, _elapsed(start))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return CheckResult("PING", host, "ERROR", f"Unable to execute ping: {exc}", _elapsed(start))


def demo_results():
    return [
        CheckResult("DNS", "demo.example", "DEMO", "Example resolution: 192.0.2.10 (documentation-only IP)", 12.5),
        CheckResult("TCP", "demo.example:443", "DEMO", "Example: TCP connection established", 30.7),
        CheckResult("HTTP", "https://demo.example", "DEMO", "Example: HTTP status 200", 59.2),
        CheckResult("PING", "demo.example", "DEMO", "Example: ICMP blocked by firewall", 2000.0),
    ]


def build_report(results, *, demo=False):
    if not results:
        raise ValueError("Report requires at least one result")
    return {
        "project": "Linux Network Diagnostics Toolkit",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "SIMULATED DEMO — NO NETWORK CHECKS" if demo else "LIVE CHECKS",
        "checks_total": len(results),
        "passed": sum(r.status == "PASS" for r in results),
        "failed": sum(r.status == "FAIL" for r in results),
        "errors": sum(r.status == "ERROR" for r in results),
        "results": [asdict(r) for r in results],
    }


def render_html(report):
    rows = []
    for item in report["results"]:
        status = item["status"]
        cls = "pass" if status == "PASS" else "fail" if status in {"FAIL", "ERROR"} else "demo"
        rows.append(
            "<tr>"
            f"<td>{escape(item['check'])}</td><td>{escape(item['target'])}</td>"
            f'<td class="{cls}">{escape(status)}</td>'
            f"<td>{escape(item['detail'])}</td><td>{item['elapsed_ms']:.2f}</td></tr>"
        )
    head = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Network Diagnostics Report</title><style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#e9eff8;background:#0e1728}
*{box-sizing:border-box}main{max-width:1100px;margin:36px auto;padding:0 18px}
h1{font-size:clamp(1.55rem,4vw,2.25rem)}.muted{color:#aec0d4}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin:24px 0}
.card,.panel{background:#1b2a40;border:1px solid #354860;border-radius:14px;padding:20px}
.card strong{display:block;font-size:2.1rem}.panel{overflow-x:auto}
table{width:100%;min-width:720px;border-collapse:collapse}
th,td{text-align:left;padding:12px;border-bottom:1px solid #394c60;font-size:.9rem}
th{color:#bed0e2}.pass{color:#4ed8a1;font-weight:700}
.fail{color:#ffa0a0;font-weight:700}.demo{color:#f3cc7d;font-weight:700}
</style></head><body><main><h1>Network Diagnostics Report</h1>"""
    cards = "".join(
        f'<div class="card">{label}<strong>{report[key]}</strong></div>'
        for label, key in [("Total checks", "checks_total"), ("Passed", "passed"),
                           ("Failed", "failed"), ("Errors", "errors")]
    )
    table = """<div class="panel"><h2>Check results</h2><table><thead>
<tr><th>Check</th><th>Target</th><th>Status</th><th>Details</th><th>Time (ms)</th></tr>
</thead><tbody>"""
    return (head + '<p class="muted">' + escape(report["mode"]) + ' · '
            + escape(report["generated_utc"]) + '</p><div class="cards">' + cards + '</div>'
            + table + "".join(rows) + """</tbody></table></div>
<p class="muted">Use only on systems you own or are authorized to test.
Ping failure alone is not proof a host is offline.</p></main></body></html>""")


def save_report(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "report.json"
    html_path = directory / "report.html"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    return json_path, html_path
