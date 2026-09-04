#!/usr/bin/env python3
"""
Master Heartbeat Orchestrator (Async)
=======================================
Default profile coordinates bot profiles via hermes chat -q.

Do not treat process exit 0 as real work. Auth/init failures are FAIL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERMES_CMD = r"C:\Users\downl\Documents\New project\hermes-agent\.venv\Scripts\hermes.exe"
CERT_BUNDLE = r"C:\Users\downl\certs\combined-ca-bundle.pem"
PROVIDER = "nvidia"
MODEL = "nvidia/nemotron-3-super-120b-a12b"
A2A_RESULTS_DIR = Path.home() / ".hermes" / "a2a_results"

FAILURE_MARKERS = (
    "No access token found",
    "Failed to initialize agent",
    "Failed to initialize OpenAI client",
    "No module named",
    "SSL_CERT_FILE points to a missing",
    "re-authenticate",
    "Could not parse your authentication token",
    "unauthorized_unknown",
    "model 'huihui-gemma-4-12b' not found",
    "HTTP 400: model",
    "HTTP 401",
    "HTTP 403",
    "HTTP 404",
    "HTTP 429",
    "Service temporarily overloaded",
    "API call failed after 3 retries",
    "Primary auth failed",
)

PROFILES = {
    "job-seeker": {
        "tasks": [
            "Scan BizReach and Findy for new AI engineering roles in Tokyo. Report matches.",
            "Check LAPRAS for new AI/ML job postings. Summarize top 3 matches.",
            "Review job application status and follow up on pending applications.",
        ]
    },
    "secretary": {
        "tasks": [
            "Check Google Calendar for upcoming events in next 24 hours. Summarize.",
            "Check Gmail for urgent unread emails. Flag important ones.",
            "Review Kanban board for blocked tasks. Report status.",
        ]
    },
    "sedori-buyer": {
        "tasks": [
            "Scan Yahoo Auctions and Mercari for GPU arbitrage opportunities.",
            "Check Kakaku.com for price drops on electronics categories.",
            "Scan Amazon Japan for underpriced items with resale potential.",
        ]
    },
    "sedori-ledger": {
        "tasks": [
            "Update profit/loss ledger with today's transaction data.",
            "Generate weekly profit summary report.",
            "Reconcile inventory records with actual listings.",
        ]
    },
    "sedori-lister": {
        "tasks": [
            "Update pricing on active Mercari listings based on market data.",
            "Check for sold items and update inventory status.",
            "Optimize listing titles and descriptions for search visibility.",
        ]
    },
    "sedori-researcher": {
        "tasks": [
            "Research trending products on Yahoo Auctions for resale potential.",
            "Analyze competitor pricing in electronics category.",
            "Find new supplier sources for high-margin products.",
        ]
    },
    "sedori-shipper": {
        "tasks": [
            "Check shipment tracking status for all pending deliveries.",
            "Update delivery confirmation in the ledger.",
            "Report any delivery delays or issues.",
        ]
    },
    "delivery-worker": {
        "tasks": [
            "Check ongoing delivery tasks and update status.",
            "Report completion status of assigned tasks.",
            "Flag any blocked or delayed items in the Kanban board.",
        ]
    },
    "self-improver": {
        "tasks": [
            "Review skill library for outdated skills. Suggest improvements.",
            "Check for new Hermes features to adopt.",
            "Audit cron job health and report any failing jobs.",
        ]
    },
}


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if Path(CERT_BUNDLE).is_file():
        env["SSL_CERT_FILE"] = CERT_BUNDLE
        env["REQUESTS_CA_BUNDLE"] = CERT_BUNDLE
    # Heartbeat one-shots must not block on MCP discovery / codegraph.
    env["HERMES_WATCHDOG_MANAGED"] = "1"
    return env


def classify_output(returncode: int, stdout: str, stderr: str) -> tuple[bool, str]:
    text = f"{stdout}\n{stderr}"
    for marker in FAILURE_MARKERS:
        if marker in text:
            return False, marker
    if returncode != 0:
        snippet = (stderr or stdout).strip().replace("\r", "")[:160]
        return False, snippet or f"exit {returncode}"
    body = stdout.strip()
    if not body:
        return False, "empty stdout"
    return True, ""


def clip(text: str, limit: int = 700) -> str:
    text = (text or "").replace("\r", "")
    return text[:limit]


async def run_hermes_task(profile: str, task: str, timeout: int) -> dict:
    cmd = [
        HERMES_CMD,
        "-p",
        profile,
        "--provider",
        PROVIDER,
        "-m",
        MODEL,
        "chat",
        "-q",
        task,
        "-Q",
        "-t",
        "web,terminal,file",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_subprocess_env(),
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
        stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
        ok, reason = classify_output(proc.returncode, stdout, stderr)
        return {
            "ok": ok,
            "profile": profile,
            "task": task[:80],
            "returncode": proc.returncode,
            "provider": PROVIDER,
            "model": MODEL,
            "output": clip(stdout),
            "error": "" if ok else (reason or clip(stderr, 200)),
        }
    except TimeoutError:
        try:
            proc.kill()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception:
            pass
        return {
            "ok": False,
            "profile": profile,
            "task": task[:80],
            "returncode": None,
            "provider": PROVIDER,
            "model": MODEL,
            "output": "",
            "error": "timeout",
        }
    except Exception as exc:
        return {
            "ok": False,
            "profile": profile,
            "task": task[:80],
            "returncode": None,
            "provider": PROVIDER,
            "model": MODEL,
            "output": "",
            "error": str(exc),
        }


async def run_with_retry(profile: str, task: str, timeout: int, retries: int) -> dict:
    result = {"ok": False, "error": "not started", "profile": profile, "task": task[:80]}
    for attempt in range(retries + 1):
        result = await run_hermes_task(profile, task, timeout=timeout)
        if result["ok"] or result.get("error") != "timeout":
            return result
        if attempt < retries:
            print(f"  [retry {attempt + 1}/{retries}] {profile} timed out, retrying...")
    return result


def persist_results(results: list, now: datetime, smoke: bool) -> Path:
    A2A_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%Y%m%d_%H%M%S")
    out_path = A2A_RESULTS_DIR / f"{ts}.json"
    ok_count = sum(1 for item in results if item["ok"])
    run_mode = "heartbeat" if smoke else "real-work"
    payload = {
        "timestamp": now.isoformat(),
        "profile": "default",
        "provider": PROVIDER,
        "model": MODEL,
        "result": {
            "ok": ok_count == len(results) and bool(results),
            "task": f"master-heartbeat-{ts}",
            "output": f"{ok_count}/{len(results)} {run_mode} succeeded",
        },
        "sub_results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")
    return out_path


def print_report(results: list, now: datetime, out_path: Path, smoke: bool) -> None:
    ok_count = sum(1 for item in results if item["ok"])
    fail_count = len(results) - ok_count
    print(f"=== Master Heartbeat {now.strftime('%Y-%m-%d %H:%M')} JST ===")
    print(f"provider={PROVIDER} model={MODEL}")
    print(f"hermes={HERMES_CMD}")
    label = "生存確認" if smoke else "実作業"
    print(f"{label}: {ok_count}/{len(results)} succeeded, {fail_count} failed")
    print()
    for item in results:
        status = "OK" if item["ok"] else "FAIL"
        err = item.get("error") or ""
        print(f"- {item['profile']}: {status} | {item['task']}")
        if err:
            print(f"  error: {err}")
    print()
    print(f"result_file: {out_path}")
    print()
    print("---JSON---")
    print(json.dumps(results, ensure_ascii=False, indent=2))


async def run_all(
    profiles: list[str],
    timeout: int,
    retries: int,
    smoke: bool,
    concurrency: int,
) -> list:
    selected = {}
    for name in profiles:
        if name not in PROFILES:
            raise SystemExit(f"unknown profile: {name}")
        if smoke:
            selected[name] = "Reply with exactly PONG and nothing else."
        else:
            selected[name] = random.choice(PROFILES[name]["tasks"])

    gate = asyncio.Semaphore(max(1, concurrency))

    async def _guarded(profile: str, task: str) -> dict:
        async with gate:
            print(f"[{profile}] start")
            result = await run_with_retry(profile, task, timeout=timeout, retries=retries)
            status = "OK" if result["ok"] else "FAIL"
            print(f"[{profile}] {status}")
            return result

    return await asyncio.gather(
        *[_guarded(profile, task) for profile, task in selected.items()],
        return_exceptions=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Master heartbeat orchestrator")
    parser.add_argument(
        "--profiles",
        default="",
        help="comma-separated profile subset (default: all)",
    )
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument(
        "--smoke",
        dest="smoke",
        action="store_true",
        default=True,
        help="send a one-line PONG probe instead of role tasks",
    )
    parser.add_argument(
        "--real-work",
        dest="smoke",
        action="store_false",
        help="run one role task per profile instead of the default heartbeat probe",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    now = datetime.now(timezone(timedelta(hours=9)))
    names = [item.strip() for item in args.profiles.split(",") if item.strip()] or list(PROFILES)
    if not Path(HERMES_CMD).is_file():
        print(f"FAIL: hermes executable missing: {HERMES_CMD}", file=sys.stderr)
        return 2
    results = await run_all(
        names,
        timeout=args.timeout,
        retries=args.retries,
        smoke=args.smoke,
        concurrency=args.concurrency,
    )
    out_path = persist_results(results, now, smoke=args.smoke)
    print_report(results, now, out_path, smoke=args.smoke)
    return 0 if results and all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
