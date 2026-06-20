#!/usr/bin/env python3
"""
NHS School ERP — dev-time error scanner.

Runs three scans on your code and prints a tidy, color-coded report:
    1. ruff      -> Python lint (style, unused imports, common bugs)
    2. pyflakes  -> Python static analysis (undefined names, etc.)
    3. eslint    -> JavaScript/JSX lint (uses CRA's built-in config)

Then groups every issue by file and prints it with a single-line summary
at the top so you know exactly where to look.

Usage:
    python tools/scan.py                # scan everything
    python tools/scan.py --backend      # only Python
    python tools/scan.py --frontend     # only JS
    python tools/scan.py --explain      # AI-explain each error in plain English
                                          (set ANTHROPIC_API_KEY to enable)

Auto-installs ruff/pyflakes if missing. ESLint is invoked via npx so you
don't need a global install — it uses what react-scripts already provides.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# ---------- Pretty printing ----------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"


def _color(s: str, c: str) -> str:
    if not sys.stdout.isatty():
        return s
    return f"{c}{s}{RESET}"


def _section(title: str):
    bar = "─" * (len(title) + 2)
    print()
    print(_color(f"┌{bar}┐", CYAN))
    print(_color(f"│ {title} │", CYAN + BOLD))
    print(_color(f"└{bar}┘", CYAN))


# ---------- Tooling ensure ----------
def _pip_install(pkg: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg],
            check=True,
        )
        return True
    except Exception as e:
        print(_color(f"  ! could not install {pkg}: {e}", RED))
        return False


def _ensure(module: str, pip_name: str | None = None) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return _pip_install(pip_name or module)


# ---------- Issue model ----------
class Issue:
    __slots__ = ("file", "line", "col", "code", "message", "severity", "tool")

    def __init__(self, file: str, line: int, col: int, code: str, msg: str,
                 severity: str, tool: str):
        self.file = file
        self.line = line
        self.col = col
        self.code = code
        self.message = msg
        self.severity = severity
        self.tool = tool

    def loc(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


# ---------- Scanners ----------
def scan_ruff() -> list[Issue]:
    if not _ensure("ruff", "ruff"):
        return []
    try:
        out = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(BACKEND), "--output-format=json"],
            capture_output=True, text=True,
        )
    except Exception as e:
        print(_color(f"  ruff failed: {e}", RED))
        return []
    if not out.stdout.strip():
        return []
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []
    issues = []
    for d in data:
        issues.append(Issue(
            file=d.get("filename", "?"),
            line=(d.get("location") or {}).get("row", 0),
            col=(d.get("location") or {}).get("column", 0),
            code=d.get("code", "RUF"),
            msg=d.get("message", ""),
            severity="warning",
            tool="ruff",
        ))
    return issues


def scan_pyflakes() -> list[Issue]:
    if not _ensure("pyflakes", "pyflakes"):
        return []
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pyflakes", str(BACKEND)],
            capture_output=True, text=True,
        )
    except Exception as e:
        print(_color(f"  pyflakes failed: {e}", RED))
        return []
    issues = []
    for line in out.stdout.splitlines():
        m = re.match(r"^(.*?):(\d+):(?:(\d+):)?\s*(.*)$", line)
        if not m:
            continue
        file, ln, col, msg = m.group(1), int(m.group(2)), int(m.group(3) or 0), m.group(4)
        issues.append(Issue(file, ln, col, "F", msg, "error", "pyflakes"))
    return issues


def scan_eslint() -> list[Issue]:
    if not (FRONTEND / "package.json").exists():
        return []
    if not shutil.which("npx"):
        print(_color("  npx not found — skipping ESLint", YELLOW))
        return []
    try:
        out = subprocess.run(
            ["npx", "--no-install", "eslint", "src", "--ext", ".js,.jsx", "--format", "json"],
            cwd=str(FRONTEND), capture_output=True, text=True,
        )
    except Exception as e:
        print(_color(f"  eslint failed: {e}", RED))
        return []
    if not out.stdout.strip():
        return []
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        # eslint sometimes prints a banner before json — try to recover.
        m = re.search(r"\[.*\]", out.stdout, flags=re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except Exception:
            return []
    issues = []
    for f in data:
        for msg in f.get("messages", []):
            issues.append(Issue(
                file=f.get("filePath", "?"),
                line=msg.get("line", 0),
                col=msg.get("column", 0),
                code=msg.get("ruleId") or "eslint",
                msg=msg.get("message", ""),
                severity="error" if msg.get("severity") == 2 else "warning",
                tool="eslint",
            ))
    return issues


# ---------- Optional AI explain ----------
def explain_with_claude(issue: Issue) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        import urllib.request
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 220,
            "messages": [{
                "role": "user",
                "content": (
                    f"Explain this lint/static-analysis issue in 2 short sentences "
                    f"and suggest a fix.\n\nTool: {issue.tool}\nCode: {issue.code}\n"
                    f"File: {issue.file}:{issue.line}\nMessage: {issue.message}"
                ),
            }],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"].strip()
    except Exception as e:
        return f"(AI explain failed: {e})"


# ---------- Report ----------
def report(issues: Iterable[Issue], explain: bool):
    issues = list(issues)
    if not issues:
        print(_color("\n✓ Clean — no issues found.", GREEN + BOLD))
        return 0

    by_file: dict[str, list[Issue]] = defaultdict(list)
    for i in issues:
        by_file[i.file].append(i)

    n_err = sum(1 for i in issues if i.severity == "error")
    n_warn = len(issues) - n_err
    print()
    print(_color(
        f"⚠ {len(issues)} issue(s)  ·  {n_err} error(s)  ·  {n_warn} warning(s)",
        RED + BOLD if n_err else YELLOW + BOLD,
    ))

    for file in sorted(by_file):
        rel = os.path.relpath(file, ROOT)
        print()
        print(_color(f"▸ {rel}  ", BOLD) + _color(f"({len(by_file[file])})", DIM))
        for i in sorted(by_file[file], key=lambda x: (x.line, x.col)):
            sev_c = RED if i.severity == "error" else YELLOW
            tag = _color(f"[{i.severity:>7}]", sev_c)
            tool = _color(f"{i.tool}/{i.code}", MAGENTA)
            loc = _color(f":{i.line}:{i.col}", DIM)
            print(f"  {tag} {loc} {tool}  {i.message}")
            if explain:
                ex = explain_with_claude(i)
                if ex:
                    for line in ex.splitlines():
                        print(_color(f"      ↳ {line}", DIM))

    return 1 if n_err else 0


def main():
    ap = argparse.ArgumentParser(description="Static-analysis scanner for the NHS School ERP.")
    ap.add_argument("--backend", action="store_true", help="Only scan Python.")
    ap.add_argument("--frontend", action="store_true", help="Only scan JS/JSX.")
    ap.add_argument("--explain", action="store_true",
                    help="Use Claude (ANTHROPIC_API_KEY) to explain each issue.")
    args = ap.parse_args()

    do_back = args.backend or not args.frontend
    do_front = args.frontend or not args.backend

    issues: list[Issue] = []
    if do_back:
        _section("Backend · ruff")
        ruff_issues = scan_ruff()
        print(f"  {len(ruff_issues)} issue(s)")
        issues.extend(ruff_issues)

        _section("Backend · pyflakes")
        pf_issues = scan_pyflakes()
        print(f"  {len(pf_issues)} issue(s)")
        issues.extend(pf_issues)

    if do_front:
        _section("Frontend · ESLint")
        es_issues = scan_eslint()
        print(f"  {len(es_issues)} issue(s)")
        issues.extend(es_issues)

    code = report(issues, args.explain)
    sys.exit(code)


if __name__ == "__main__":
    main()
