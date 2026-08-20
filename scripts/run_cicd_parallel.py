#!/usr/bin/env python3
"""
Fork Original Parallel CI/CD Orchestrator (6-Core / 12-Thread Parallel Execution)
Validates:
  1. Python Lint (Ruff multi-core)
  2. Windows Footgun Check (check-windows-footguns.py --all)
  3. TypeScript Typecheck (apps/desktop tsc - clean type definitions)
  4. Go Modules Vet & Compilation Verification
  5. Python Unit Test Verification

Follows MILSPECLLMOps & Hermes Agent Engineering Standards:
  - logging only (no print statements)
  - 12 worker concurrency
  - Fast execution and clear summary
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

# Configure logging
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
logging.basicConfig(
    level=logging.INFO, format=LOG_FORMAT, handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ForkCICDParallel")

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class JobResult:
    name: str
    category: str
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def run_job(
    name: str, category: str, cmd: list[str], cwd: Path | None = None
) -> JobResult:
    work_dir = cwd or REPO_ROOT
    cmd_str = " ".join(cmd)
    logger.info("Starting job [%s] (%s): %s in %s", name, category, cmd_str, work_dir)

    start_time = time.perf_counter()
    try:
        env = os.environ.copy()
        env["GOPROXY"] = "off"
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            env=env,
            timeout=180,
        )
        duration = time.perf_counter() - start_time
        result = JobResult(
            name=name,
            category=category,
            command=cmd_str,
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_s=duration,
        )
    except Exception as exc:
        duration = time.perf_counter() - start_time
        logger.error("Exception running job [%s]: %s", name, exc, exc_info=True)
        result = JobResult(
            name=name,
            category=category,
            command=cmd_str,
            return_code=-1,
            stdout="",
            stderr=str(exc),
            duration_s=duration,
        )

    if result.passed:
        logger.info("Job [%s] COMPLETED in %.2fs -> PASS", name, duration)
    else:
        logger.warning(
            "Job [%s] FAILED with code %d in %.2fs. Output:\n%s\nError:\n%s",
            name,
            result.return_code,
            duration,
            result.stdout.strip() or "(no stdout)",
            result.stderr.strip() or "(no stderr)",
        )
    return result


def find_go_binary() -> str:
    standard_paths = [
        Path(r"C:\Program Files\Go\bin\go.exe"),
        Path(r"C:\Go\bin\go.exe"),
    ]
    for p in standard_paths:
        if p.exists():
            return str(p)
    return "go"


def find_python_binary() -> str:
    venv_py = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def main() -> int:
    logger.info("=" * 75)
    logger.info("HERMES FORK CI/CD PARALLEL RUNNER (6 CORES / 12 THREADS)")
    logger.info("Workspace: %s", REPO_ROOT)
    logger.info("=" * 75)

    python_exe = find_python_binary()
    go_exe = find_go_binary()

    jobs: list[tuple[str, str, list[str], Path]] = []

    # 1. Python Ruff Lint (Multi-threaded)
    jobs.append((
        "Ruff Lint (Python)",
        "Python",
        [python_exe, "-m", "ruff", "check", "."],
        REPO_ROOT,
    ))

    # 2. Windows Footgun Check
    footgun_script = REPO_ROOT / "scripts" / "check-windows-footguns.py"
    if footgun_script.exists():
        jobs.append((
            "Windows Footguns Security Check",
            "Security",
            [python_exe, str(footgun_script), "--all"],
            REPO_ROOT,
        ))

    # 3. TypeScript Typecheck
    desktop_dir = REPO_ROOT / "apps" / "desktop"
    if desktop_dir.exists():
        pnpm_cmd = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
        jobs.append((
            "Desktop TypeScript Check",
            "TypeScript",
            [pnpm_cmd, "typecheck"],
            desktop_dir,
        ))

    # 4. Go Modules Vet
    go_modules = [
        ("Go Vet (Watchdog)", REPO_ROOT / "scripts" / "windows" / "watchdog-go"),
        ("Go Vet (Memory Graph)", REPO_ROOT / "tools" / "memory-graph-server"),
        ("Go Vet (Heygen CLI)", REPO_ROOT / "vendor" / "heygen-cli"),
    ]
    for name, mod_dir in go_modules:
        if mod_dir.exists() and (mod_dir / "go.mod").exists():
            jobs.append((name, "Go", [go_exe, "vet", "./..."], mod_dir))

    # 5. Core Python Tests (Fast smoke verification)
    jobs.append((
        "Core Skill Verification Tests",
        "Pytest",
        [python_exe, "-m", "pytest", "tests/test_plugin_skills.py", "-q"],
        REPO_ROOT,
    ))

    start_all = time.perf_counter()
    results: list[JobResult] = []

    max_workers = 12
    logger.info(
        "Dispatching %d jobs concurrently across %d threads...", len(jobs), max_workers
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(run_job, name, category, cmd, cwd): name
            for name, category, cmd, cwd in jobs
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                logger.error("Job [%s] crashed: %s", name, exc, exc_info=True)

    total_duration = time.perf_counter() - start_all
    logger.info("=" * 75)
    logger.info(
        "PARALLEL CI/CD VALIDATION SUMMARY (Total Duration: %.2fs)", total_duration
    )
    logger.info("=" * 75)

    all_passed = True
    for res in sorted(results, key=lambda r: (r.category, r.name)):
        status = "PASS [OK]" if res.passed else f"FAIL [Exit {res.return_code}]"
        logger.info(
            "%-35s | %-12s | %-15s | %.2fs",
            res.name,
            res.category,
            status,
            res.duration_s,
        )
        if not res.passed:
            all_passed = False

    logger.info("=" * 75)
    if all_passed:
        logger.info(
            "ALL %d CHECKS PASSED WITH ZERO WARNINGS/ERRORS! (ALL GREEN)", len(results)
        )
        return 0
    else:
        logger.error("ONE OR MORE CHECKS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
