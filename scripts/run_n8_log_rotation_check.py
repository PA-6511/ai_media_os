#!/usr/bin/env python3
"""N-8: ログ肥大化・ローテーション確認 DRY_RUN。

ログディレクトリのファイルサイズを読み取り専用で計測し、
肥大化の有無・ローテーション設定の存在を確認する。
実際のローテーション実行・ファイル削除は行わない。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n8_log_rotation_check_policy.json"
REQUEST = ROOT / "exchange/examples/n8_log_rotation_check_request.example.json"
OUTPUT = ROOT / "exchange/logs/n8_log_rotation_check_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_log_dir(dir_path: Path) -> dict:
    """ディレクトリ内のファイルサイズを集計する（読み取り専用）。"""
    if not dir_path.exists():
        return {
            "dir": str(dir_path),
            "exists": False,
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "file_count": 0,
            "files": [],
        }

    files = []
    total = 0
    for entry in sorted(dir_path.iterdir()):
        if entry.is_file():
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0
            total += size
            files.append({"name": entry.name, "size_bytes": size})

    return {
        "dir": str(dir_path),
        "exists": True,
        "total_size_bytes": total,
        "total_size_mb": round(total / (1024 * 1024), 4),
        "file_count": len(files),
        "files": files,
    }


def _check_logrotate(target_dir: Path) -> dict:
    """logrotate 設定の存在を read-only で確認する。"""
    candidates = [
        Path("/etc/logrotate.d"),
        target_dir.parent / "logrotate.conf",
        target_dir.parent / ".logrotate",
    ]
    found = [str(c) for c in candidates if c.exists()]
    return {"logrotate_config_found": len(found) > 0, "found_paths": found}


def run_check(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = {
        "phase": "N-8",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "wordpress_post_created": False,
        "external_state_change": False,
        "executor_action_allowed": False,
        "network_observation_only": True,
        "communication_test_only": True,
        "log_rotation_executed": False,
        "log_deleted": False,
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}", "dirs": []}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    warn_mb = float(req.get("warn_size_mb") or policy.get("warn_size_mb", 10))
    fail_mb = float(req.get("fail_size_mb") or policy.get("fail_size_mb", 100))
    raw_targets = req.get("log_target_dirs") or policy.get("log_targets", ["exchange/logs"])

    overall = "PASS"
    dirs_result = []
    warns: list[str] = []
    fails: list[str] = []

    for raw in raw_targets:
        # allow absolute paths (used in tests)
        dir_path = Path(raw) if Path(raw).is_absolute() else ROOT / raw
        scan = _scan_log_dir(dir_path)
        logrotate = _check_logrotate(dir_path)
        total_mb = float(scan.get("total_size_mb", 0.0))

        if total_mb >= fail_mb:
            dir_status = "FAIL"
            overall = "FAIL"
            fails.append(f"{raw}: {total_mb} MB >= fail threshold {fail_mb} MB")
        elif total_mb >= warn_mb:
            dir_status = "WARN"
            if overall == "PASS":
                overall = "WARN"
            warns.append(f"{raw}: {total_mb} MB >= warn threshold {warn_mb} MB")
        else:
            dir_status = "PASS"

        dirs_result.append({**scan, **logrotate, "status": dir_status})

    result = {
        **base,
        "status": overall,
        "warn_size_mb": warn_mb,
        "fail_size_mb": fail_mb,
        "dirs": dirs_result,
        "warns": warns,
        "fails": fails,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
