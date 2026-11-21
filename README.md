# Linux Network Diagnostics Toolkit

A cross-platform **Python command-line network diagnostics toolkit** for systems integration, network support, and test automation practice. Runs on Windows and Linux using Python's standard library, without installing additional Python packages.

> **Authorization:** Only run live checks against systems you own or are explicitly authorized to test. The toolkit checks one named host, one TCP port, and/or one URL per invocation, not entire networks.

## Features

- DNS lookup for a specified hostname or IP address
- Single-port TCP connectivity check with connection timeout
- HTTP HEAD response validation
- One ICMP ping with OS-specific commands
- Safe offline demo mode (four simulated examples; no actual network checks)
- HTML dashboard and structured JSON report
- **21 unit tests**, including simulated errors and CLI input validation
- GitHub Actions continuous integration

## Quick start on Windows

Download the repository ZIP and **Extract All**. Open the folder containing `main.py` and `netdiag.py`, click the File Explorer address bar, type `cmd`, and press Enter.

**Offline demo:**

```cmd
python main.py --demo
start "" "output\report.html"
```

**Automated tests:**

```cmd
python -m unittest discover -s tests -v
```

**Live DNS check:**

```cmd
python main.py --host example.com
```

**Other single-target live checks:**

```cmd
python main.py --host example.com --port 443
python main.py --url https://example.com
python main.py --host example.com --ping
```

For Linux, use `python3` instead of `python`; open the report file in your browser. A failed ping alone does not prove that a host is unreachable.

## Example results

- Offline demo: 4 **DEMO** checks covering DNS, TCP, HTTP, and ICMP scenarios
- Live DNS demonstration: Successfully resolved `example.com` on Windows
- Automated tests: **21 passed** in the provided local run
- Report files: `output/report.json` and `output/report.html`

The demo response times are example values, **not measured network latency**.

## Screenshot evidence

### Terminal: demo and unit tests

![Windows console showing the offline demo and tests](Screenshot%202026-11-21%20142449.png)

![Windows console with all 21 tests passing and live DNS resolution](Screenshot%202026-11-21%20142514.png)

![Additional command-line unit test output](Screenshot%202026-11-21%20142610.png)

### HTML diagnostic dashboard — simulated demonstration

![Simulated network diagnostics report dashboard](Screenshot%202026-11-21%20142639.png)

### HTML diagnostic dashboard — actual DNS lookup

![Live successful DNS resolution dashboard for example.com](Screenshot%202026-11-21%20142657.png)

## Repository layout

```text
main.py                   CLI argument handling and orchestration
netdiag.py                DNS, TCP, HTTP, ping, reports
tests/test_netdiag.py     21 automated unit tests
.github/workflows/tests.yml   GitHub Actions
README.md
.gitignore
```

## Engineering concepts

Python scripting, TCP/IP fundamentals, DNS, HTTP, ICMP, error handling, input validation, automated testing, reporting and CI/CD.

This is a portfolio project for troubleshooting and learning, not a vulnerability scanner or network monitoring service.
