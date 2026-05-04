"""Phase2 health check runner.

Runs a fixed verification set for Phase2 governance and block-connection safety.

Usage:
    python3 tools/phase2_health_check.py --input data/logs/phase2_runtime.log
    python3 tools/phase2_health_check.py --input /tmp/phase2_runtime.ndjson --strict-log
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG_INPUT = BASE_DIR / "data" / "logs" / "phase2_runtime.log"


def _run(cmd: list[str], *, cwd: Path = BASE_DIR, env: dict[str, str] | None = None) -> int:
    printable = " ".join(cmd)
    print(f"\n$ {printable}")
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, check=False)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase2 integrated health checks")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_LOG_INPUT,
        help=f"Phase2 runtime log path (default: {DEFAULT_LOG_INPUT})",
    )
    parser.add_argument(
        "--strict-log",
        action="store_true",
        help="Fail when --input log is missing (default: skip log checks)",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    skipped: list[str] = []

    print("=" * 68)
    print("Phase2 Health Check")
    print("=" * 68)
    print(f"base_dir : {BASE_DIR}")
    print(f"log_input: {args.input}")

    # 1) Compile checks
    compile_targets = [
        "main.py",
        "core/verification/__init__.py",
        "core/verification/verification_result.py",
        "core/verification/failure_report.py",
        "core/verification/escalation.py",
        "core/governance/__init__.py",
        "core/governance/authority_guard.py",
        "core/governance/auto_freeze_judge.py",
        "blocks/dummy_block/block.py",
        "blocks/ebook_affiliate_block/block.py",
        "tools/validate_phase2_logs.py",
        "tools/phase2_kpi_report.py",
        "tools/phase2_health_check.py",
    ]
    rc = _run([sys.executable, "-m", "py_compile", *compile_targets])
    if rc != 0:
        failures.append("py_compile")

    # 2) Core Phase2 block connection tests
    env = dict(os.environ)
    env["PYTHONPATH"] = f".{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    rc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_dummy_block_connection.py",
            "tests/test_ebook_affiliate_block_connection.py",
        ],
        env=env,
    )
    if rc != 0:
        failures.append("pytest_phase2_block_connections")

    # 3) Runtime log validation + KPI report
    if args.input.exists():
        rc = _run(
            [
                sys.executable,
                "tools/validate_phase2_logs.py",
                "--input",
                str(args.input),
            ]
        )
        if rc != 0:
            failures.append("validate_phase2_logs")

        rc = _run(
            [
                sys.executable,
                "tools/phase2_kpi_report.py",
                "--input",
                str(args.input),
            ]
        )
        if rc != 0:
            failures.append("phase2_kpi_report")
    else:
        msg = f"runtime log not found: {args.input}"
        if args.strict_log:
            failures.append(msg)
        else:
            skipped.append(msg)
            print(f"[SKIP] {msg}")

    print("\n" + "=" * 68)
    print("Health Check Summary")
    print("=" * 68)
    print(f"failures: {len(failures)}")
    if failures:
        for f in failures:
            print(f"- {f}")
    print(f"skipped: {len(skipped)}")
    if skipped:
        for s in skipped:
            print(f"- {s}")

    if failures:
        print("result: NG")
        return 1

    print("result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
