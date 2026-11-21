"""CLI entry point for the network diagnostics portfolio project."""
import argparse
from pathlib import Path
import sys

from netdiag import build_report, check_dns, check_http, check_ping, check_tcp, demo_results, save_report


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-target network diagnostics: DNS, TCP, HTTP HEAD, and ping. Only test authorized systems."
    )
    parser.add_argument("--demo", action="store_true", help="Run deterministic example without sending network packets")
    parser.add_argument("--host", help="Explicit hostname or IP for DNS/TCP/ping checks")
    parser.add_argument("--port", type=int, help="Single TCP service port; requires --host")
    parser.add_argument("--url", help="Single http:// or https:// URL for HTTP HEAD check")
    parser.add_argument("--ping", action="store_true", help="Send one ICMP ping; requires --host")
    parser.add_argument("--output", default="output", help="Report folder, default: output")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.demo and any((args.host, args.port is not None, args.url, args.ping)):
        parser.error("--demo cannot be combined with live diagnostic targets")
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if (args.port is not None or args.ping) and not args.host:
        parser.error("--port and --ping require --host")
    if not args.demo and not args.host and not args.url:
        parser.error("Provide --demo, --host, or --url. No automatic network probes are performed.")

    try:
        if args.demo:
            results = demo_results()
        else:
            results = []
            if args.host:
                results.append(check_dns(args.host))
                if args.port is not None:
                    results.append(check_tcp(args.host, args.port))
                if args.ping:
                    results.append(check_ping(args.host))
            if args.url:
                results.append(check_http(args.url))
        report = build_report(results, demo=args.demo)
        json_path, html_path = save_report(report, Path(args.output))
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Mode: {report['mode']}")
    for result in results:
        print(f"[{result.status}] {result.check:<4} {result.target} — {result.detail} ({result.elapsed_ms:.2f} ms)")
    print(f"\nSaved JSON: {json_path.resolve()}")
    print(f"Saved HTML: {html_path.resolve()}")
    print('Windows: start "" "output\\report.html"')
    return 0 if args.demo or all(item.status == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
