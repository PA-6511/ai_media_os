#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-I-R2"
REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

I_R1_REL="${BASE_REL}/i2f3e-i-r1-writer-freeze-backup-execution-packet-prep-20260725T151813Z-512616"
F1_REL="${BASE_REL}/i2f3e-f1-evidence-copy-normalization-reseal-20260725T140856Z-509951"

I_R1_ROOT="${REPO_ROOT}/${I_R1_REL}"
F1_ROOT="${REPO_ROOT}/${F1_REL}"

EXPECTED_I_R1_RESULT_SHA="4ab4198efa4ba51440a355a498c004159717018e02498fbe9c6ea2d861b59439"
EXPECTED_I_R1_PACKET_MANIFEST_SHA="3d3cb6a4c781ba2562af48109198cfc7d63980e671435be75796175438ba67ea"
EXPECTED_I_R1_SEMANTIC_SHA="e6e6e28483015ecd4b89b66acce3d4d1f99099504dd0c02d45d9a8b3731b3835"
EXPECTED_I_R1_EVIDENCE_MANIFEST_SHA="ccd021015be098a087db624a863ccbeaf28d8d200e420f089f900b849937679e"

EXPECTED_F1_RESULT_SHA="05eb0ac5f36e4e8b346be8a633cecb3d5798469f5901f1d799074bb7a43450ce"
EXPECTED_F1_PROVENANCE_SHA="4e05d14be765be28e6f6ae6be147e34b917164cd50ce053ae84e09757dc662ec"
EXPECTED_F1_EVIDENCE_MANIFEST_SHA="b71be1255a523257354cf089b50eaab4ea96151fca738f97a9398e15a84d08fb"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_REL="${BASE_REL}/i2f3e-i-r2-cron-canonical-disambiguation-packet-correction-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
INPUT_ROOT="${EVIDENCE_ROOT}/input-snapshots"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "RUN_AS_ROOT_FORBIDDEN=true" >&2
  exit 1
fi

mkdir "$EVIDENCE_ROOT"
mkdir "$PACKET_ROOT"
mkdir "$INPUT_ROOT"

on_error() {
  local rc=$?
  set +e

  if [[ -d "$EVIDENCE_ROOT" && -w "$EVIDENCE_ROOT" ]]; then
    {
      printf 'FAILURE_PHASE=%s\n' "$PHASE"
      printf 'FAILURE_EXIT_CODE=%s\n' "$rc"
      printf 'FAILURE_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
      printf 'RAW_CRONTAB_SAVED=false\n'
      printf 'CRONTAB_SECRET_VALUES_SAVED=false\n'
      printf 'PROCESS_SIGNAL_SENT=false\n'
      printf 'WRITER_STOP_PERFORMED=false\n'
      printf 'GUI_STOPPED_OR_RESTARTED=false\n'
      printf 'CRONTAB_CHANGED=false\n'
      printf 'PRODUCTION_DB_OPENED=false\n'
      printf 'SQL_EXECUTED=false\n'
      printf 'BACKUP_CREATED=false\n'
      printf 'WRITER_FREEZE_EXECUTION=HOLD\n'
      printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
      printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
    } > "$EVIDENCE_ROOT/failure.txt" 2>/dev/null || true
  fi

  printf 'SCRIPT_EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap on_error ERR

cd "$REPO_ROOT"

required_inputs=(
  "$I_R1_ROOT/result.json"
  "$I_R1_ROOT/evidence-manifest.txt"
  "$I_R1_ROOT/packet-snapshot/packet-manifest.json"
  "$I_R1_ROOT/packet-snapshot/packet-semantic-validation.json"
  "$I_R1_ROOT/packet-snapshot/cron-window-control-plan.json"
  "$I_R1_ROOT/packet-snapshot/current-gui-identity-readonly.json"
  "$I_R1_ROOT/packet-snapshot/current-db-file-set-metadata-readonly.json"
  "$I_R1_ROOT/packet-snapshot/filesystem-backup-contract.json"
  "$I_R1_ROOT/packet-snapshot/future-gui-stop-contract.json"
  "$I_R1_ROOT/packet-snapshot/safe-minimal-restart-profile.json"
  "$I_R1_ROOT/packet-snapshot/future-freeze-backup-restart-sequence.json"

  "$F1_ROOT/corrective-result.json"
  "$F1_ROOT/provenance-record.json"
  "$F1_ROOT/evidence-manifest.txt"
  "$F1_ROOT/corrected-packet-snapshot/process-and-cron-attribution.json"
  "$F1_ROOT/corrected-packet-snapshot/freeze-window-plan.json"
)

for required in "${required_inputs[@]}"; do
  test -f "$required"
done

echo "${EXPECTED_I_R1_RESULT_SHA}  ${I_R1_ROOT}/result.json" | sha256sum -c -
echo "${EXPECTED_I_R1_PACKET_MANIFEST_SHA}  ${I_R1_ROOT}/packet-snapshot/packet-manifest.json" | sha256sum -c -
echo "${EXPECTED_I_R1_SEMANTIC_SHA}  ${I_R1_ROOT}/packet-snapshot/packet-semantic-validation.json" | sha256sum -c -
echo "${EXPECTED_I_R1_EVIDENCE_MANIFEST_SHA}  ${I_R1_ROOT}/evidence-manifest.txt" | sha256sum -c -

echo "${EXPECTED_F1_RESULT_SHA}  ${F1_ROOT}/corrective-result.json" | sha256sum -c -
echo "${EXPECTED_F1_PROVENANCE_SHA}  ${F1_ROOT}/provenance-record.json" | sha256sum -c -
echo "${EXPECTED_F1_EVIDENCE_MANIFEST_SHA}  ${F1_ROOT}/evidence-manifest.txt" | sha256sum -c -

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$I_R1_ROOT/result.json" \
  "$INPUT_ROOT/3e-i-r1-result.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$I_R1_ROOT/packet-snapshot/cron-window-control-plan.json" \
  "$INPUT_ROOT/3e-i-r1-cron-window-control-plan.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$F1_ROOT/corrective-result.json" \
  "$INPUT_ROOT/3e-f1-corrective-result.json"

cat > "$PACKET_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
I_R1_EXECUTION_EVIDENCE_REVIEW=APPROVE_WITH_CRON_HOLD
I_R1_PACKET_INTEGRITY_REVIEW=PASS
GUI_IDENTITY_AND_LISTENER_REVIEW=PASS
BACKUP_CONTRACT_REVIEW=PASS_PLAN_ONLY
EXACT_STOP_ROUTE_REVIEW=PASS_PLAN_ONLY
EXACT_RESTART_ROUTE_REVIEW=PASS_PLAN_ONLY
APPROVE_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_AND_PACKET_CORRECTION_READONLY_NO_EXECUTION

許可範囲：
1. 3E-I-R1、3E-F1 Evidenceを読み取り専用入力として使用する。
2. 3E-F1 process-and-cron-attribution.jsonのcron_jobs各項目を読み取る。
3. command/path出力時は秘密情報を必ずマスキングする。
4. 現行crontabのraw自体を保存せず、各有効行のschedule、
   redacted normalized command、normalized line SHA-256を生成する。
5. 過去WINDOW_CONTROL_ONLY 3件と現行crontabを、
   scheduleだけでなくcommand path、normalized command、SHA-256で一意照合する。
6. expected candidate SHA:
   e9610d7384a37b85a2e04e3a36b776ca64e9fae9eff29d3bf38884feea1f2810
   218fd6ba09b9bc0d425d5398d29cf940f89dfa46c983a3bc1c405bf71b4d5b18
   967688ce82407c8401af2f7eaa9e0b575cce55a8f21c07c97f2fee5e1a615fda
7. 3件が過去Attributionと一意に一致した場合だけselectionをRESOLVEDとする。
8. /opt/auto-system/runner/run_block.py ebook_affiliateが
   NOT_RELEVANTであることをcommand/path照合で証明する。
9. 確定3件だけを対象にAsia/Tokyo、freeze 600秒、
   前後guard各300秒の安全窓を再計算する。
10. cron制御方式を再判定する。
11. 一意照合と安全窓成功時のみ
    CRON_EXECUTION_CONTROL_RESOLVED=true、
    READY_FOR_HUMAN_REVIEW_NOT_EXECUTIONとする。
12. 3E-I-R1を変更せず新規R2 evidenceへ保存する。
13. I-R1のAMBIGUOUS_11_CANDIDATES_FOR_3_TARGETSを保持し、
    R2での解消根拠を記録する。

禁止事項：
process signal送信、GUI停止・再起動、writer停止、cron変更、
crontab書換え、timer変更、systemctl stop/start/restart、
service作成・変更、Production DB接続、SQL実行、backup作成、
restore、migration、manifest変更、source/test変更、git add、
git commit、deployment、外部通信、Slack Worker起動、
production approval、production release承認は禁止する。

追加条件：
1. command/path対応が一意でなければselectionはHOLD。
2. scheduleだけの一致を確定根拠にしない。
3. raw crontabと秘密値をEvidenceへ保存しない。
4. 安全窓が得られなければWriter freezeを承認可能状態にしない。
5. R2成功後も停止、backup、restartへ自動遷移しない。

EXPECTED_RELEVANT_CRON_JOB_COUNT=3
MAXIMUM_WRITER_FREEZE_SECONDS=600
CRON_GUARD_BEFORE_SECONDS=300
CRON_GUARD_AFTER_SECONDS=300
RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE
WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD
FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED
WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

python3 - \
  "$REPO_ROOT" \
  "$I_R1_ROOT" \
  "$I_R1_REL" \
  "$F1_ROOT" \
  "$F1_REL" \
  "$EVIDENCE_ROOT" \
  "$EVIDENCE_REL" \
  "$PACKET_ROOT" \
  "$EXPECTED_DB_SHA" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_WORKFLOW_SHA" \
  "$EXPECTED_MIGRATION_SHA" \
  "$EXPECTED_SLACK_RUNTIME_SHA" \
  "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import datetime as dt
import grp
import hashlib
import json
import os
import pwd
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

(
    repo_root_s,
    i_r1_root_s,
    i_r1_rel,
    f1_root_s,
    f1_rel,
    evidence_root_s,
    evidence_rel,
    packet_root_s,
    expected_db_sha,
    expected_manifest_sha,
    expected_workflow_sha,
    expected_migration_sha,
    expected_slack_runtime_sha,
    expected_promoted_test_sha,
) = sys.argv[1:]

repo_root = Path(repo_root_s).resolve()
i_r1_root = Path(i_r1_root_s).resolve()
f1_root = Path(f1_root_s).resolve()
evidence_root = Path(evidence_root_s).resolve()
packet_root = Path(packet_root_s).resolve()

phase = "TST-5D-W2B-I2F-3E-I-R2"
now_utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

EXPECTED_RELEVANT_COUNT = 3
MAX_FREEZE_SECONDS = 600
GUARD_BEFORE_SECONDS = 300
GUARD_AFTER_SECONDS = 300
SEARCH_DAYS = 7
CRON_TIMEZONE_NAME = "Asia/Tokyo"
CRON_TIMEZONE = ZoneInfo(CRON_TIMEZONE_NAME)

EXPECTED_TARGETS = [
    {
        "target_id": "WP_DRAFT_PREPUBLISH_REPORT",
        "expected_sha256": "e9610d7384a37b85a2e04e3a36b776ca64e9fae9eff29d3bf38884feea1f2810",
        "schedule": "0 2 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "identity_tokens": [
            "/home/deploy/ai_media_os",
            "tools/check_wp_draft_prepublish.py",
        ],
    },
    {
        "target_id": "PHASE2_OBSERVATION_REPORT",
        "expected_sha256": "218fd6ba09b9bc0d425d5398d29cf940f89dfa46c983a3bc1c405bf71b4d5b18",
        "schedule": "0 9 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "identity_tokens": [
            "/home/deploy/ai_media_os",
            "tools/report_phase2_observation.py",
        ],
    },
    {
        "target_id": "AI_POST_QUEUE",
        "expected_sha256": "967688ce82407c8401af2f7eaa9e0b575cce55a8f21c07c97f2fee5e1a615fda",
        "schedule": "10 8 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "identity_tokens": [
            "/home/deploy/ai_media_os",
            "scripts/run_ai_post_queue.sh",
        ],
    },
]

EXPECTED_EXCLUDED = {
    "target_id": "AUTO_SYSTEM_EBOOK_AFFILIATE_BLOCK",
    "expected_sha256": "5aae2b90052415f1408a16fb31e7bb763a337b3dad14856d1c436f8fdf3132a0",
    "schedule": "0 9 * * *",
    "classification": "NOT_RELEVANT",
    "identity_tokens": [
        "/opt/auto-system",
        "runner/run_block.py",
        "ebook_affiliate",
    ],
}

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(token|password|passwd|secret|credential|private[_-]?key|"
    r"api[_-]?key|access[_-]?key|cookie|authorization|bearer)"
    r"(\s*[:=]\s*)([^\s]+)"
)
URL_CREDENTIAL_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@"
)
SHELL_ASSIGNMENT_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)"
)
SECRET_NAME_RE = re.compile(
    r"(TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE|API_KEY|ACCESS_KEY|"
    r"COOKIE|AUTHORIZATION|SESSION|BEARER|SIGNING|CLIENT_SECRET)",
    re.IGNORECASE,
)
STANDARD_CRON_FIELD_RE = re.compile(r"^[A-Za-z0-9*/,\-]+$")

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path}")
    return value

def normalize_ws(value: str) -> str:
    return " ".join(value.strip().split())

def redact(value: str) -> str:
    value = SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}<REDACTED>",
        value,
    )
    value = URL_CREDENTIAL_RE.sub(
        lambda match: f"{match.group(1)}<REDACTED>:<REDACTED>@",
        value,
    )

    def replace_assignment(match: re.Match[str]) -> str:
        name = match.group(1)
        if SECRET_NAME_RE.search(name):
            return f"{name}=<REDACTED>"
        return match.group(0)

    value = SHELL_ASSIGNMENT_RE.sub(replace_assignment, value)
    return value[:5000]

def safe_run(command: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except FileNotFoundError as exc:
        return {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }

def protected_sha_inventory() -> dict[str, Any]:
    items = [
        (
            "production_database",
            repo_root / "data/database/ebook_affiliate.db",
            expected_db_sha,
        ),
        (
            "production_manifest",
            repo_root / "config/slack_worker_release_source_manifest.json",
            expected_manifest_sha,
        ),
        (
            "workflow_source",
            repo_root / "app/db/repositories/workflow_state_repository.py",
            expected_workflow_sha,
        ),
        (
            "migration_source",
            repo_root / "migrations/versions/00241611109d_add_unique_wordpress_post_id.py",
            expected_migration_sha,
        ),
        (
            "slack_runtime_source",
            repo_root / "scripts/run_slack_approval_socket.py",
            expected_slack_runtime_sha,
        ),
        (
            "promoted_test",
            repo_root / "tests/test_slack_approval_socket_hold_remediation_offline.py",
            expected_promoted_test_sha,
        ),
    ]

    records = []
    for label, path, expected in items:
        require(path.is_file(), f"PROTECTED_FILE_MISSING:{path}")
        actual = sha256(path)
        require(actual == expected, f"PROTECTED_SHA_MISMATCH:{label}:{actual}")
        metadata = path.stat()
        records.append(
            {
                "label": label,
                "path": str(path),
                "sha256": actual,
                "size_bytes": metadata.st_size,
                "inode": metadata.st_ino,
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            }
        )

    return {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "files": records,
        "production_database_opened": False,
        "sql_executed": False,
    }

def split_cron_line(line: str) -> tuple[str, str] | None:
    tokens = line.split()
    if not tokens:
        return None

    if tokens[0].startswith("@") and len(tokens) >= 2:
        return tokens[0], " ".join(tokens[1:])

    if len(tokens) < 6:
        return None

    fields = tokens[:5]
    if not all(STANDARD_CRON_FIELD_RE.fullmatch(field) for field in fields):
        return None

    return " ".join(fields), " ".join(tokens[5:])

def current_crontab_inventory(raw: str) -> list[dict[str, Any]]:
    inventory = []

    for raw_line in raw.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", stripped):
            continue

        normalized = normalize_ws(stripped)
        split = split_cron_line(normalized)
        if split is None:
            inventory.append(
                {
                    "line_sha256": sha256_text(normalized),
                    "schedule": "UNPARSEABLE",
                    "redacted_normalized_command": redact(normalized),
                    "redacted_normalized_line": redact(normalized),
                    "parse_status": "UNPARSEABLE",
                    "raw_line_saved": False,
                }
            )
            continue

        schedule, command = split
        inventory.append(
            {
                "line_sha256": sha256_text(normalized),
                "schedule": schedule,
                "redacted_normalized_command": redact(command),
                "redacted_normalized_line": redact(normalized),
                "parse_status": "PARSED",
                "raw_line_saved": False,
            }
        )

    inventory.sort(
        key=lambda item: (
            item["schedule"],
            item["line_sha256"],
        )
    )
    return inventory

def flatten_scalars(
    value: Any,
    path: str = "$",
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            records.extend(flatten_scalars(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            records.extend(flatten_scalars(child, f"{path}[{index}]"))
    elif isinstance(value, (str, int, float, bool)) or value is None:
        records.append(
            {
                "path": path,
                "value": str(value),
            }
        )

    return records

def job_identity_text(job: dict[str, Any]) -> str:
    selected = []

    for record in flatten_scalars(job):
        path_lower = record["path"].lower()
        if any(
            token in path_lower
            for token in (
                "command",
                "cmd",
                "path",
                "script",
                "argv",
                "line",
                "working",
                "logical_writer",
                "target",
            )
        ):
            selected.append(record["value"])

    if not selected:
        selected = [record["value"] for record in flatten_scalars(job)]

    return normalize_ws(" ".join(selected))

def historical_job_records(
    attribution: dict[str, Any],
) -> list[dict[str, Any]]:
    jobs = attribution.get("cron_jobs")
    require(isinstance(jobs, list), "HISTORICAL_CRON_JOBS_LIST_REQUIRED")

    records = []
    for index, job in enumerate(jobs):
        require(isinstance(job, dict), f"HISTORICAL_CRON_JOB_OBJECT_REQUIRED:{index}")

        schedule = job.get("schedule")
        classification = job.get("classification")
        identity_text = job_identity_text(job)

        records.append(
            {
                "historical_index": index,
                "schedule": str(schedule),
                "classification": str(classification),
                "redacted_identity_text": redact(identity_text),
                "identity_text_for_internal_match": identity_text,
                "scalar_field_paths": sorted(
                    {
                        record["path"]
                        for record in flatten_scalars(job)
                        if any(
                            token in record["path"].lower()
                            for token in (
                                "command",
                                "cmd",
                                "path",
                                "script",
                                "argv",
                                "logical_writer",
                            )
                        )
                    }
                ),
            }
        )

    return records

def tokens_present(value: str, tokens: Iterable[str]) -> bool:
    return all(token in value for token in tokens)

def resolve_target(
    specification: dict[str, Any],
    current_inventory: list[dict[str, Any]],
    historical_records: list[dict[str, Any]],
) -> dict[str, Any]:
    current_matches = [
        item
        for item in current_inventory
        if item["line_sha256"] == specification["expected_sha256"]
        and item["schedule"] == specification["schedule"]
        and tokens_present(
            item["redacted_normalized_line"],
            specification["identity_tokens"],
        )
    ]

    historical_matches = [
        item
        for item in historical_records
        if item["schedule"] == specification["schedule"]
        and item["classification"] == specification["classification"]
        and tokens_present(
            item["identity_text_for_internal_match"],
            specification["identity_tokens"],
        )
    ]

    resolved = len(current_matches) == 1 and len(historical_matches) == 1

    current_record = current_matches[0] if len(current_matches) == 1 else None
    historical_record = (
        historical_matches[0]
        if len(historical_matches) == 1
        else None
    )

    return {
        "target_id": specification["target_id"],
        "expected_sha256": specification["expected_sha256"],
        "expected_schedule": specification["schedule"],
        "expected_classification": specification["classification"],
        "identity_tokens": specification["identity_tokens"],
        "current_match_count": len(current_matches),
        "historical_match_count": len(historical_matches),
        "resolved": resolved,
        "current_match": current_record,
        "historical_match": (
            {
                key: value
                for key, value in historical_record.items()
                if key != "identity_text_for_internal_match"
            }
            if historical_record is not None
            else None
        ),
        "schedule_only_match_forbidden": True,
        "raw_command_saved": False,
        "secret_values_saved": False,
    }

def parse_exact_schedule(schedule: str) -> tuple[int, int]:
    tokens = schedule.split()
    require(len(tokens) == 5, f"STANDARD_SCHEDULE_REQUIRED:{schedule}")
    minute, hour, dom, month, dow = tokens
    require(dom == "*" and month == "*" and dow == "*", f"DAILY_SCHEDULE_REQUIRED:{schedule}")
    require(minute.isdigit() and hour.isdigit(), f"EXACT_HOUR_MINUTE_REQUIRED:{schedule}")

    minute_value = int(minute)
    hour_value = int(hour)
    require(0 <= minute_value <= 59, f"MINUTE_INVALID:{schedule}")
    require(0 <= hour_value <= 23, f"HOUR_INVALID:{schedule}")
    return hour_value, minute_value

def schedule_events(
    schedules: list[str],
) -> list[dt.datetime]:
    current = dt.datetime.now(CRON_TIMEZONE)
    start_date = current.date()
    events = []

    for day_offset in range(0, SEARCH_DAYS + 1):
        date = start_date + dt.timedelta(days=day_offset)
        for schedule in schedules:
            hour, minute = parse_exact_schedule(schedule)
            moment = dt.datetime(
                date.year,
                date.month,
                date.day,
                hour,
                minute,
                tzinfo=CRON_TIMEZONE,
            )
            if moment >= current - dt.timedelta(minutes=1):
                events.append(moment)

    return sorted(set(events))

def find_safe_window(
    events: list[dt.datetime],
) -> dict[str, Any] | None:
    cursor = dt.datetime.now(CRON_TIMEZONE).replace(second=0, microsecond=0)
    cursor += dt.timedelta(minutes=5)

    end_search = cursor + dt.timedelta(days=SEARCH_DAYS)
    freeze_delta = dt.timedelta(seconds=MAX_FREEZE_SECONDS)
    guard_before = dt.timedelta(seconds=GUARD_BEFORE_SECONDS)
    guard_after = dt.timedelta(seconds=GUARD_AFTER_SECONDS)

    while cursor + freeze_delta <= end_search:
        freeze_end = cursor + freeze_delta
        guarded_start = cursor - guard_before
        guarded_end = freeze_end + guard_after

        conflicts = [
            event
            for event in events
            if guarded_start <= event <= guarded_end
        ]

        if not conflicts:
            previous_events = [event for event in events if event < guarded_start]
            next_events = [event for event in events if event > guarded_end]

            return {
                "candidate_freeze_start": cursor.isoformat(),
                "candidate_freeze_end": freeze_end.isoformat(),
                "guarded_interval_start": guarded_start.isoformat(),
                "guarded_interval_end": guarded_end.isoformat(),
                "previous_selected_cron_event": (
                    max(previous_events).isoformat()
                    if previous_events
                    else None
                ),
                "next_selected_cron_event": (
                    min(next_events).isoformat()
                    if next_events
                    else None
                ),
                "conflicting_event_count": 0,
                "max_freeze_seconds": MAX_FREEZE_SECONDS,
                "guard_before_seconds": GUARD_BEFORE_SECONDS,
                "guard_after_seconds": GUARD_AFTER_SECONDS,
                "timezone": CRON_TIMEZONE_NAME,
            }

        cursor += dt.timedelta(minutes=1)

    return None

def shared_lock_tokens(
    selected_records: list[dict[str, Any]],
) -> list[str]:
    token_sets = []

    for record in selected_records:
        current = record["current_match"]
        if current is None:
            return []

        command = current["redacted_normalized_command"]
        try:
            tokens = set(shlex.split(command, comments=False, posix=True))
        except ValueError:
            tokens = set(command.split())

        lock_tokens = {
            token
            for token in tokens
            if (
                "flock" in token
                or token.endswith(".lock")
                or "maintenance" in token.lower()
                or "freeze" in token.lower()
            )
        }
        token_sets.append(lock_tokens)

    if not token_sets:
        return []

    return sorted(set.intersection(*token_sets))

i_r1_result = read_json(i_r1_root / "result.json")
i_r1_semantic = read_json(
    i_r1_root / "packet-snapshot/packet-semantic-validation.json"
)
i_r1_cron = read_json(
    i_r1_root / "packet-snapshot/cron-window-control-plan.json"
)
i_r1_identity = read_json(
    i_r1_root / "packet-snapshot/current-gui-identity-readonly.json"
)
i_r1_db = read_json(
    i_r1_root / "packet-snapshot/current-db-file-set-metadata-readonly.json"
)
i_r1_backup = read_json(
    i_r1_root / "packet-snapshot/filesystem-backup-contract.json"
)
i_r1_stop = read_json(
    i_r1_root / "packet-snapshot/future-gui-stop-contract.json"
)
i_r1_restart = read_json(
    i_r1_root / "packet-snapshot/safe-minimal-restart-profile.json"
)
i_r1_sequence = read_json(
    i_r1_root / "packet-snapshot/future-freeze-backup-restart-sequence.json"
)

f1_attribution = read_json(
    f1_root
    / "corrected-packet-snapshot/process-and-cron-attribution.json"
)
f1_freeze_plan = read_json(
    f1_root
    / "corrected-packet-snapshot/freeze-window-plan.json"
)

require(
    i_r1_result.get("result")
    == "PASS_W2B_I2F3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARED_NO_EXECUTION",
    "I_R1_RESULT_INVALID",
)
require(i_r1_result.get("cron_control_method") == "UNRESOLVED", "I_R1_CRON_STATE_INVALID")
require(i_r1_result.get("cron_execution_control_resolved") is False, "I_R1_CRON_RESOLUTION_INVALID")
require(i_r1_result.get("matched_relevant_cron_job_count") == 11, "I_R1_MATCH_COUNT_INVALID")
require(i_r1_result.get("expected_relevant_cron_job_count") == 3, "I_R1_EXPECTED_COUNT_INVALID")
require(i_r1_result.get("execution_eligibility") is False, "I_R1_ELIGIBILITY_INVALID")
require(i_r1_result.get("writer_freeze_execution") == "HOLD", "I_R1_FREEZE_STATE_INVALID")
require(i_r1_cron.get("raw_crontab_saved") is False, "I_R1_RAW_CRONTAB_FLAG_INVALID")
require(i_r1_cron.get("secret_values_saved") is False, "I_R1_SECRET_FLAG_INVALID")
require(f1_freeze_plan.get("relevant_cron_job_count") == 3, "F1_RELEVANT_COUNT_INVALID")

protected_before = protected_sha_inventory()
write_json(packet_root / "protected-sha-before.json", protected_before)

crontab_result = safe_run(["crontab", "-l"])
require(crontab_result["exit_code"] == 0, "CRONTAB_READ_FAILED")
raw_crontab = str(crontab_result["stdout"])

current_inventory = current_crontab_inventory(raw_crontab)
write_json(
    packet_root / "current-crontab-redacted-inventory.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "crontab_command_exit_code": crontab_result["exit_code"],
        "raw_crontab_sha256": sha256_text(raw_crontab),
        "raw_crontab_saved": False,
        "secret_values_saved": False,
        "active_line_count": len(current_inventory),
        "active_lines": current_inventory,
        "crontab_changed": False,
    },
)

historical_records = historical_job_records(f1_attribution)

target_resolutions = [
    resolve_target(specification, current_inventory, historical_records)
    for specification in EXPECTED_TARGETS
]
excluded_resolution = resolve_target(
    EXPECTED_EXCLUDED,
    current_inventory,
    historical_records,
)

selected_sha_set = {
    item["expected_sha256"]
    for item in target_resolutions
    if item["resolved"]
}
all_target_resolved = (
    len(target_resolutions) == EXPECTED_RELEVANT_COUNT
    and all(item["resolved"] for item in target_resolutions)
    and len(selected_sha_set) == EXPECTED_RELEVANT_COUNT
)
excluded_proven = excluded_resolution["resolved"]

window_control_historical_count = sum(
    1
    for item in historical_records
    if item["classification"] == "WINDOW_CONTROL_ONLY"
)
not_relevant_historical_count = sum(
    1
    for item in historical_records
    if item["classification"] == "NOT_RELEVANT"
)

cron_selection_resolved = (
    all_target_resolved
    and excluded_proven
    and window_control_historical_count == EXPECTED_RELEVANT_COUNT
)

selected_schedules = [
    item["expected_schedule"]
    for item in target_resolutions
    if item["resolved"]
]
events = (
    schedule_events(selected_schedules)
    if cron_selection_resolved
    else []
)
safe_window = (
    find_safe_window(events)
    if cron_selection_resolved
    else None
)

shared_locks = (
    shared_lock_tokens(target_resolutions)
    if cron_selection_resolved
    else []
)

if not cron_selection_resolved:
    cron_control_method = "UNRESOLVED"
elif shared_locks:
    cron_control_method = "EXISTING_MAINTENANCE_LOCK"
elif safe_window is not None:
    cron_control_method = "SCHEDULE_AVOIDANCE_ONLY"
else:
    cron_control_method = (
        "TEMPORARY_CRONTAB_CONTROL_REQUIRES_SEPARATE_APPROVAL"
    )

cron_execution_control_resolved = (
    cron_selection_resolved
    and safe_window is not None
    and cron_control_method in {
        "SCHEDULE_AVOIDANCE_ONLY",
        "EXISTING_MAINTENANCE_LOCK",
    }
)

write_json(
    packet_root / "canonical-cron-disambiguation.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "source_i_r1_ambiguity": "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS",
        "source_i_r1_matched_candidate_count": 11,
        "expected_relevant_cron_job_count": EXPECTED_RELEVANT_COUNT,
        "historical_window_control_only_count": window_control_historical_count,
        "historical_not_relevant_count": not_relevant_historical_count,
        "target_resolutions": target_resolutions,
        "excluded_candidate_resolution": excluded_resolution,
        "all_expected_targets_resolved": all_target_resolved,
        "excluded_candidate_proven_not_relevant": excluded_proven,
        "cron_relevant_job_selection": (
            "RESOLVED"
            if cron_selection_resolved
            else "HOLD_NON_UNIQUE_OR_UNPROVEN"
        ),
        "schedule_only_match_used": False,
        "raw_crontab_saved": False,
        "secret_values_saved": False,
    },
)

write_json(
    packet_root / "corrected-cron-window-control-plan.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "timezone": CRON_TIMEZONE_NAME,
        "selected_target_count": len(selected_schedules),
        "selected_schedules": selected_schedules,
        "selected_line_sha256": sorted(selected_sha_set),
        "cron_relevant_job_selection": (
            "RESOLVED"
            if cron_selection_resolved
            else "HOLD_NON_UNIQUE_OR_UNPROVEN"
        ),
        "candidate_safe_window": safe_window,
        "shared_lock_tokens": shared_locks,
        "control_method": cron_control_method,
        "execution_control_resolved": cron_execution_control_resolved,
        "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
        "guard_before_seconds": GUARD_BEFORE_SECONDS,
        "guard_after_seconds": GUARD_AFTER_SECONDS,
        "future_execution_requirements": [
            "Re-read crontab immediately before execution.",
            "Require the three selected normalized line SHA-256 values to match this packet.",
            "Require the excluded /opt/auto-system ebook_affiliate line to remain NOT_RELEVANT by canonical command/path identity.",
            "Recompute a fresh Asia/Tokyo guarded window.",
            "Abort before SIGTERM if any selected event intersects the guarded interval.",
            "Do not modify crontab under this packet.",
        ],
        "raw_crontab_saved": False,
        "secret_values_saved": False,
        "crontab_changed": False,
        "writer_freeze_execution": "HOLD",
    },
)

inherited_conditions = {
    "gui_identity_and_listener_ready": (
        i_r1_result.get("current_identity_matches_g_r1") is True
        and i_r1_result.get("listener_owned_by_current_gui") is True
        and i_r1_identity.get("identity_matches_prior") is True
    ),
    "backup_copy_conditions_resolved": (
        i_r1_result.get("backup_copy_conditions_resolved") is True
        and i_r1_db.get("db_sha_verified") is True
        and i_r1_backup.get("status") == "PLAN_ONLY_NOT_EXECUTED"
        and i_r1_backup.get("execution_allowed") is False
    ),
    "exact_stop_route_resolved_plan_only": (
        i_r1_stop.get("status")
        == "RESOLVED_PENDING_SEPARATE_EXECUTION_APPROVAL"
        and i_r1_stop.get("execution_allowed") is False
    ),
    "exact_restart_route_resolved_plan_only": (
        i_r1_result.get("exact_restart_route_status")
        == "RESOLVED_PENDING_HUMAN_REVIEW"
        and i_r1_restart.get("profile")
        == "SAFE_MINIMAL_MAINTENANCE_MODE"
        and i_r1_restart.get("execution_allowed") is False
    ),
    "maximum_writer_freeze_seconds": i_r1_sequence.get(
        "maximum_writer_freeze_seconds"
    ),
    "automatic_retry_allowed": i_r1_sequence.get(
        "automatic_retry_allowed"
    ),
    "automatic_restore_allowed": i_r1_sequence.get(
        "automatic_restore_allowed"
    ),
}

execution_eligibility = (
    cron_execution_control_resolved
    and inherited_conditions["gui_identity_and_listener_ready"]
    and inherited_conditions["backup_copy_conditions_resolved"]
    and inherited_conditions["exact_stop_route_resolved_plan_only"]
    and inherited_conditions["exact_restart_route_resolved_plan_only"]
    and inherited_conditions["maximum_writer_freeze_seconds"]
    == MAX_FREEZE_SECONDS
    and inherited_conditions["automatic_retry_allowed"] is False
    and inherited_conditions["automatic_restore_allowed"] is False
)

eligibility_status = (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
    if execution_eligibility
    else "BLOCKED_PENDING_CONDITION_RESOLUTION"
)

write_json(
    packet_root / "corrected-execution-eligibility.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "source_i_r1_execution_eligibility": False,
        "source_i_r1_execution_eligibility_status": (
            "BLOCKED_PENDING_CONDITION_RESOLUTION"
        ),
        "source_i_r1_ambiguity": (
            "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
        ),
        "cron_relevant_job_selection": (
            "RESOLVED"
            if cron_selection_resolved
            else "HOLD_NON_UNIQUE_OR_UNPROVEN"
        ),
        "cron_control_method": cron_control_method,
        "cron_execution_control_resolved": cron_execution_control_resolved,
        "candidate_safe_window_available": safe_window is not None,
        "inherited_conditions": inherited_conditions,
        "execution_eligibility": execution_eligibility,
        "execution_eligibility_status": eligibility_status,
        "execution_allowed": False,
        "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
        "wordpress_external_actions_after_restart": "HOLD",
        "full_operational_parity_after_restart": "NOT_ESTABLISHED",
        "writer_freeze_execution": "HOLD",
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
    },
)

write_json(
    packet_root / "input-provenance-and-correction-record.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "created_at_utc": now_utc(),
        "input_evidence_roots": {
            "3e_i_r1": i_r1_rel,
            "3e_f1": f1_rel,
        },
        "input_fixed_sha": {
            "3e_i_r1_result": sha256(i_r1_root / "result.json"),
            "3e_i_r1_packet_manifest": sha256(
                i_r1_root / "packet-snapshot/packet-manifest.json"
            ),
            "3e_i_r1_semantic": sha256(
                i_r1_root
                / "packet-snapshot/packet-semantic-validation.json"
            ),
            "3e_i_r1_evidence_manifest": sha256(
                i_r1_root / "evidence-manifest.txt"
            ),
            "3e_f1_result": sha256(f1_root / "corrective-result.json"),
            "3e_f1_provenance": sha256(
                f1_root / "provenance-record.json"
            ),
            "3e_f1_evidence_manifest": sha256(
                f1_root / "evidence-manifest.txt"
            ),
        },
        "original_ambiguity": (
            "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
        ),
        "correction_method": (
            "CANONICAL_SCHEDULE_PLUS_COMMAND_PATH_PLUS_NORMALIZED_LINE_SHA256"
        ),
        "expected_target_sha256": sorted(
            specification["expected_sha256"]
            for specification in EXPECTED_TARGETS
        ),
        "expected_excluded_sha256": (
            EXPECTED_EXCLUDED["expected_sha256"]
        ),
        "source_evidence_mutated": False,
        "raw_crontab_saved": False,
        "secret_values_saved": False,
    },
)

protected_after = protected_sha_inventory()
write_json(packet_root / "protected-sha-after.json", protected_after)
require(
    [item["sha256"] for item in protected_before["files"]]
    == [item["sha256"] for item in protected_after["files"]],
    "PROTECTED_SHA_CHANGED",
)

execution_flags = {
    "process_signal_sent": False,
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "crontab_changed": False,
    "timer_changed": False,
    "systemd_changed": False,
    "production_database_opened": False,
    "production_database_sql_connection_used": False,
    "sql_executed": False,
    "backup_created": False,
    "restore_executed": False,
    "migration_executed": False,
    "production_manifest_modified": False,
    "source_modified": False,
    "test_modified": False,
    "git_add_performed": False,
    "git_commit_performed": False,
    "deployment_performed": False,
    "external_network_used": False,
    "slack_worker_started": False,
    "production_approval_created": False,
    "production_release_approved": False,
}

semantic_validation = {
    "schema_version": "1.0",
    "phase": phase,
    "result": (
        "PASS_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_AND_PACKET_CORRECTION_READONLY_NO_EXECUTION"
    ),
    "source_i_r1_ambiguity": (
        "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
    ),
    "expected_relevant_cron_job_count": EXPECTED_RELEVANT_COUNT,
    "resolved_relevant_cron_job_count": sum(
        1 for item in target_resolutions if item["resolved"]
    ),
    "all_expected_targets_resolved": all_target_resolved,
    "excluded_candidate_proven_not_relevant": excluded_proven,
    "cron_relevant_job_selection": (
        "RESOLVED"
        if cron_selection_resolved
        else "HOLD_NON_UNIQUE_OR_UNPROVEN"
    ),
    "schedule_only_match_used": False,
    "cron_control_method": cron_control_method,
    "cron_execution_control_resolved": cron_execution_control_resolved,
    "candidate_safe_window_available": safe_window is not None,
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "guard_before_seconds": GUARD_BEFORE_SECONDS,
    "guard_after_seconds": GUARD_AFTER_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "raw_crontab_saved": False,
    "crontab_secret_values_saved": False,
    "protected_sha_unchanged": True,
    **execution_flags,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(
    packet_root / "packet-semantic-validation.json",
    semantic_validation,
)

packet_files_before_manifest = sorted(
    path
    for path in packet_root.iterdir()
    if path.is_file()
)
manifest_entries = [
    {
        "name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }
    for path in packet_files_before_manifest
]

packet_manifest = {
    "schema_version": "1.0",
    "phase": phase,
    "created_at_utc": now_utc(),
    "status": (
        "READONLY_CRON_DISAMBIGUATION_PACKET_WRITER_FREEZE_NOT_APPROVED"
    ),
    "result": (
        "PASS_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET_GENERATED"
    ),
    "packet_file_count_excluding_manifest": len(manifest_entries),
    "packet_files": manifest_entries,
    "source_i_r1_ambiguity": (
        "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
    ),
    "cron_relevant_job_selection": (
        "RESOLVED"
        if cron_selection_resolved
        else "HOLD_NON_UNIQUE_OR_UNPROVEN"
    ),
    "cron_control_method": cron_control_method,
    "cron_execution_control_resolved": cron_execution_control_resolved,
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": (
        "HUMAN_REVIEW_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET"
    ),
}
write_json(packet_root / "packet-manifest.json", packet_manifest)

result = {
    "schema_version": "1.0",
    "phase": phase,
    "completed_at_utc": now_utc(),
    "result": (
        "PASS_W2B_I2F3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET_CORRECTED_NO_EXECUTION"
    ),
    "evidence_root": evidence_rel,
    "input_evidence_roots": {
        "3e_i_r1": i_r1_rel,
        "3e_f1": f1_rel,
    },
    "source_i_r1_ambiguity": (
        "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
    ),
    "current_active_cron_line_count": len(current_inventory),
    "expected_relevant_cron_job_count": EXPECTED_RELEVANT_COUNT,
    "resolved_relevant_cron_job_count": sum(
        1 for item in target_resolutions if item["resolved"]
    ),
    "all_expected_targets_resolved": all_target_resolved,
    "excluded_candidate_proven_not_relevant": excluded_proven,
    "cron_relevant_job_selection": (
        "RESOLVED"
        if cron_selection_resolved
        else "HOLD_NON_UNIQUE_OR_UNPROVEN"
    ),
    "cron_control_method": cron_control_method,
    "cron_execution_control_resolved": cron_execution_control_resolved,
    "candidate_safe_window_available": safe_window is not None,
    "candidate_safe_window": safe_window,
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "guard_before_seconds": GUARD_BEFORE_SECONDS,
    "guard_after_seconds": GUARD_AFTER_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "raw_crontab_saved": False,
    "crontab_secret_values_saved": False,
    "packet_file_count": len(manifest_entries) + 1,
    "packet_manifest_sha256": sha256(
        packet_root / "packet-manifest.json"
    ),
    "packet_semantic_validation_sha256": sha256(
        packet_root / "packet-semantic-validation.json"
    ),
    "execution": execution_flags,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": (
        "HUMAN_REVIEW_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET"
    ),
}
write_json(evidence_root / "result.json", result)

manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines = []

for artifact in sorted(
    evidence_root.rglob("*"),
    key=lambda item: item.relative_to(evidence_root).as_posix(),
):
    if artifact.is_file() and artifact != manifest_path:
        manifest_lines.append(
            f"{sha256(artifact)}  "
            f"{artifact.relative_to(evidence_root).as_posix()}"
        )

manifest_path.write_text(
    "\n".join(manifest_lines) + "\n",
    encoding="utf-8",
)

for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative_path = line.split("  ", 1)
    artifact = evidence_root / relative_path
    require(
        artifact.is_file(),
        f"EVIDENCE_MANIFEST_FILE_MISSING:{relative_path}",
    )
    require(
        sha256(artifact) == expected,
        f"EVIDENCE_MANIFEST_SHA_MISMATCH:{relative_path}",
    )

files = sorted(
    path
    for path in evidence_root.rglob("*")
    if path.is_file()
)
directories = sorted(
    (
        path
        for path in evidence_root.rglob("*")
        if path.is_dir()
    ),
    key=lambda path: len(path.relative_to(evidence_root).parts),
    reverse=True,
)

repo_stat = repo_root.stat()

for artifact in [*files, *directories, evidence_root]:
    metadata = artifact.lstat()
    require(
        not stat.S_ISLNK(metadata.st_mode),
        f"EVIDENCE_SYMLINK_FORBIDDEN:{artifact}",
    )
    require(
        metadata.st_uid == repo_stat.st_uid,
        f"EVIDENCE_UID_INVALID:{artifact}",
    )
    require(
        metadata.st_gid == repo_stat.st_gid,
        f"EVIDENCE_GID_INVALID:{artifact}",
    )

for artifact in files:
    os.chmod(artifact, 0o444)

for directory in directories:
    os.chmod(directory, 0o555)

os.chmod(evidence_root, 0o555)

for artifact in files:
    require(
        stat.S_IMODE(artifact.stat().st_mode) == 0o444,
        f"FILE_SEAL_FAILED:{artifact}",
    )

for directory in [*directories, evidence_root]:
    require(
        stat.S_IMODE(directory.stat().st_mode) == 0o555,
        f"DIRECTORY_SEAL_FAILED:{directory}",
    )

print(f"RESULT={result['result']}")
print(f"EVIDENCE_ROOT={evidence_rel}")
print("SOURCE_I_R1_AMBIGUITY=AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS")
print(f"CURRENT_ACTIVE_CRON_LINE_COUNT={len(current_inventory)}")
print(f"EXPECTED_RELEVANT_CRON_JOB_COUNT={EXPECTED_RELEVANT_COUNT}")
print(
    "RESOLVED_RELEVANT_CRON_JOB_COUNT="
    + str(result["resolved_relevant_cron_job_count"])
)
print(
    "ALL_EXPECTED_TARGETS_RESOLVED="
    + ("true" if all_target_resolved else "false")
)
print(
    "EXCLUDED_CANDIDATE_PROVEN_NOT_RELEVANT="
    + ("true" if excluded_proven else "false")
)
print(
    "CRON_RELEVANT_JOB_SELECTION="
    + result["cron_relevant_job_selection"]
)
print(f"CRON_CONTROL_METHOD={cron_control_method}")
print(
    "CRON_EXECUTION_CONTROL_RESOLVED="
    + ("true" if cron_execution_control_resolved else "false")
)
print(
    "CANDIDATE_SAFE_WINDOW_AVAILABLE="
    + ("true" if safe_window is not None else "false")
)
if safe_window is not None:
    print(
        "CANDIDATE_FREEZE_START="
        + safe_window["candidate_freeze_start"]
    )
    print(
        "CANDIDATE_FREEZE_END="
        + safe_window["candidate_freeze_end"]
    )
    print(
        "CANDIDATE_GUARDED_INTERVAL_START="
        + safe_window["guarded_interval_start"]
    )
    print(
        "CANDIDATE_GUARDED_INTERVAL_END="
        + safe_window["guarded_interval_end"]
    )
print(
    "EXECUTION_ELIGIBILITY="
    + ("true" if execution_eligibility else "false")
)
print(f"EXECUTION_ELIGIBILITY_STATUS={eligibility_status}")
print(f"MAXIMUM_WRITER_FREEZE_SECONDS={MAX_FREEZE_SECONDS}")
print(f"CRON_GUARD_BEFORE_SECONDS={GUARD_BEFORE_SECONDS}")
print(f"CRON_GUARD_AFTER_SECONDS={GUARD_AFTER_SECONDS}")
print("RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE")
print("WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD")
print("FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED")
print(f"PACKET_FILE_COUNT={result['packet_file_count']}")
print(f"PACKET_MANIFEST_SHA={result['packet_manifest_sha256']}")
print(
    "PACKET_SEMANTIC_VALIDATION_SHA="
    + result["packet_semantic_validation_sha256"]
)
print(f"RESULT_SHA={sha256(evidence_root / 'result.json')}")
print(
    "EVIDENCE_MANIFEST_SHA="
    + sha256(evidence_root / "evidence-manifest.txt")
)
print("RAW_CRONTAB_SAVED=false")
print("CRONTAB_SECRET_VALUES_SAVED=false")
print("PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("CRONTAB_CHANGED=false")
print("SYSTEMD_CHANGED=false")
print("TIMER_CHANGED=false")
print("PRODUCTION_DB_OPENED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("SQL_EXECUTED=false")
print("BACKUP_CREATED=false")
print("RESTORE_EXECUTED=false")
print("MIGRATION_EXECUTED=false")
print("PRODUCTION_MANIFEST_MODIFIED=false")
print("SOURCE_MODIFIED=false")
print("TEST_MODIFIED=false")
print("GIT_ADD_PERFORMED=false")
print("GIT_COMMIT_PERFORMED=false")
print("DEPLOYMENT_PERFORMED=false")
print("EXTERNAL_NETWORK_USED=false")
print("SLACK_WORKER_STARTED=false")
print("PRODUCTION_APPROVAL_CREATED=false")
print("PRODUCTION_RELEASE_APPROVED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE="
    "HUMAN_REVIEW_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET"
)
PY

trap - ERR
printf 'SCRIPT_EXIT_CODE=0\n'
