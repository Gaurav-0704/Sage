#!/usr/bin/env python3
"""
Sage — single-command launcher.

Usage:
    python run.py              # boot both backend + frontend
    python run.py --setup      # install backend + frontend deps then exit
    python run.py --backend    # only the API
    python run.py --frontend   # only the UI

What it does:
  1. Creates `backend/.venv` if missing
  2. Installs Python deps from requirements.txt if missing
  3. Runs `npm install` in `frontend/` if node_modules is missing
  4. Spawns `uvicorn main:app --reload` (port 8000)
  5. Spawns `npm start` (port 3000)
  6. Streams both outputs to your terminal with [api]/[web] prefixes
  7. Ctrl+C cleanly stops both

Requires Python 3.13+ and Node.js to be installed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"

IS_WIN = os.name == "nt"
RESET = "" if not sys.stdout.isatty() else "\033[0m"
CYAN  = "" if not sys.stdout.isatty() else "\033[36m"
GREEN = "" if not sys.stdout.isatty() else "\033[32m"
YELLOW = "" if not sys.stdout.isatty() else "\033[33m"
RED   = "" if not sys.stdout.isatty() else "\033[31m"
DIM   = "" if not sys.stdout.isatty() else "\033[2m"
BOLD  = "" if not sys.stdout.isatty() else "\033[1m"


def venv_python() -> Path:
    if IS_WIN:
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_pip() -> Path:
    if IS_WIN:
        return VENV / "Scripts" / "pip.exe"
    return VENV / "bin" / "pip"


def npm_cmd() -> str:
    """`npm` is `npm.cmd` on Windows when invoked via subprocess without shell."""
    return "npm.cmd" if IS_WIN else "npm"


def info(msg: str):  print(f"{CYAN}▶ {msg}{RESET}")
def ok(msg: str):    print(f"{GREEN}✓ {msg}{RESET}")
def warn(msg: str):  print(f"{YELLOW}! {msg}{RESET}")
def fatal(msg: str):
    print(f"{RED}✗ {msg}{RESET}", file=sys.stderr)
    sys.exit(1)


def ensure_backend(install_only: bool = False) -> Path:
    """Create venv + install deps if needed. Returns the venv python path."""
    if not BACKEND.exists():
        fatal(f"{BACKEND} not found")

    if not VENV.exists():
        info("Creating Python virtual environment in backend/.venv …")
        try:
            # Try py -3.13 first (preferred)
            try:
                subprocess.run(["py", "-3.13", "-m", "venv", str(VENV)], check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        except Exception as e:
            fatal(f"Could not create venv: {e}")
        ok("venv ready")

    py = venv_python()
    if not py.exists():
        fatal(f"venv python missing at {py}")

    # Cheap "are deps installed?" check — try importing each package we need.
    probe = subprocess.run([str(py), "-c",
        "import fastapi, uvicorn, pydantic, multipart, jose, bcrypt"],
        capture_output=True)
    if probe.returncode != 0 or install_only:
        info("Installing Python dependencies …")
        r = subprocess.run([str(venv_pip()), "install", "-q",
                            "-r", str(BACKEND / "requirements.txt")])
        if r.returncode != 0:
            fatal("pip install failed")
        ok("Python deps installed")
    return py


def ensure_frontend(install_only: bool = False):
    if not FRONTEND.exists():
        fatal(f"{FRONTEND} not found")
    if not shutil.which(npm_cmd()) and not shutil.which("npm"):
        fatal("npm not found on PATH. Install Node.js from https://nodejs.org")

    needs_install = not (FRONTEND / "node_modules" / "react-router-dom").exists() \
                    or not (FRONTEND / "node_modules" / "recharts").exists()
    if needs_install or install_only:
        info("Installing frontend dependencies (npm install) — this can take a minute …")
        r = subprocess.run([npm_cmd(), "install"], cwd=str(FRONTEND))
        if r.returncode != 0:
            fatal("npm install failed")
        ok("Frontend deps installed")


def stream(proc: subprocess.Popen, prefix: str, color: str):
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        print(f"{color}[{prefix}]{RESET} {line}", flush=True)


def run_both():
    py = ensure_backend()
    ensure_frontend()

    print()
    print(f"{BOLD}Sage — booting both servers{RESET}")
    print(f"  api  → http://127.0.0.1:8000  ({DIM}/docs for Swagger{RESET})")
    print(f"  web  → http://localhost:3000")
    print(f"{DIM}Ctrl+C to stop both.{RESET}\n")

    api_env = os.environ.copy()
    # Quiet npm-spawned BROWSER autoopen on some systems if user prefers
    web_env = os.environ.copy()
    web_env.setdefault("BROWSER", "")

    api = subprocess.Popen(
        [str(py), "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=str(BACKEND),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        env=api_env,
    )

    web = subprocess.Popen(
        [npm_cmd(), "start"],
        cwd=str(FRONTEND),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        env=web_env,
        shell=IS_WIN,
    )

    t1 = threading.Thread(target=stream, args=(api, "api", CYAN), daemon=True)
    t2 = threading.Thread(target=stream, args=(web, "web", GREEN), daemon=True)
    t1.start(); t2.start()

    def shutdown(*_):
        print(f"\n{YELLOW}Stopping…{RESET}")
        for p in (api, web):
            try:
                if IS_WIN:
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                p.terminate()
            except Exception:
                pass
        for p in (api, web):
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Wait for either to exit
    while True:
        if api.poll() is not None:
            warn(f"API exited with code {api.returncode}")
            shutdown()
        if web.poll() is not None:
            warn(f"Web exited with code {web.returncode}")
            shutdown()
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser(description="Sage — AI-first School ERP launcher")
    ap.add_argument("--setup",   action="store_true", help="Install deps then exit")
    ap.add_argument("--backend", action="store_true", help="Only run the API")
    ap.add_argument("--frontend", action="store_true", help="Only run the UI")
    args = ap.parse_args()

    if args.setup:
        ensure_backend(install_only=True)
        ensure_frontend(install_only=True)
        ok("Setup complete. Now run:  python run.py")
        return

    if args.backend:
        py = ensure_backend()
        os.execv(str(py), [str(py), "-m", "uvicorn", "main:app", "--reload", "--port", "8000"])

    if args.frontend:
        ensure_frontend()
        os.chdir(str(FRONTEND))
        os.execvp(npm_cmd(), [npm_cmd(), "start"])

    run_both()


if __name__ == "__main__":
    main()
