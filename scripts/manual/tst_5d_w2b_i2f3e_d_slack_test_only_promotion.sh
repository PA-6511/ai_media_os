#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

REPO_ROOT="/home/deploy/ai_media_os"
PHASE="TST-5D-W2B-I2F-3E-D"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
C1_ROOT_REL="${I2E_ROOT_REL}/i2f3e-c1-manifest-migration-semantic-correction-20260725T184357-503375"
C1_PACKET_REL="${C1_ROOT_REL}/packet-snapshot"
D3B_ROOT_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-20260725T164615-497367"
D3A_ROOT_REL="${I2E_ROOT_REL}/i2f3d-a-slack-hold-remediation-test-inventory-20260725T162021-495991"

C1_RESULT="${REPO_ROOT}/${C1_ROOT_REL}/result.json"
C1_PACKET_MANIFEST="${REPO_ROOT}/${C1_PACKET_REL}/semantic-correction-packet-manifest.json"
C1_EVIDENCE_MANIFEST="${REPO_ROOT}/${C1_ROOT_REL}/semantic-correction-evidence-manifest.txt"
CANDIDATE_TEST="${REPO_ROOT}/${C1_PACKET_REL}/test_slack_approval_socket_hold_remediation_offline.candidate.py"
D3B_RESULT="${REPO_ROOT}/${D3B_ROOT_REL}/result.json"
D3B_SUMMARY="${REPO_ROOT}/${D3B_ROOT_REL}/offline-test-summary.json"
MATCHING_TESTS="${REPO_ROOT}/${D3A_ROOT_REL}/matching-test-files.txt"
D3A_EVIDENCE_MANIFEST="${REPO_ROOT}/${D3A_ROOT_REL}/inventory-evidence-manifest.txt"

TARGET_REL="tests/test_slack_approval_socket_hold_remediation_offline.py"
TARGET_TEST="${REPO_ROOT}/${TARGET_REL}"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
MIGRATION_SOURCE="${REPO_ROOT}/migrations/versions/00241611109d_add_unique_wordpress_post_id.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_C1_RESULT_SHA="ff1449147a56adede9685fc0c42e10ebd91b796da4e6202f2eb6862714ec9f7b"
EXPECTED_C1_PACKET_MANIFEST_SHA="5158aee338a9b410639eda23f652434767e9dee607f0405d3c4af4a5b62c49cc"
EXPECTED_C1_EVIDENCE_MANIFEST_SHA="758326773933a79873fa311b7a90b0d8647778f9d1a343014de10a2162e323ab"
EXPECTED_CANDIDATE_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"
EXPECTED_D3B_RESULT_SHA="732840292f5c551d589ea8e9459fc677c9df0380fb4ef1f18d5eafa2f1c33ce0"
EXPECTED_D3B_SUMMARY_SHA="366d96fd38f85d8dda234ace2c49015386909d9baf5c23f91195b3e278fc3a31"
EXPECTED_D3A_EVIDENCE_MANIFEST_SHA="1a52fb42fec4f996e894522dcf290f0a6e1a8abf5a50b8acf05e994f417404d5"
EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SOURCE_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

fail() {
    local message="$1"
    local rc="${2:-1}"
    printf 'RESULT=BLOCKED_W2B_I2F3E_D_SLACK_TEST_ONLY_PROMOTION\n' >&2
    printf 'ERROR=%s\n' "$message" >&2
    if [[ -n "${EVIDENCE_REL:-}" ]]; then
        printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL" >&2
        printf 'FAILED_EVIDENCE_PRESERVED=true\n' >&2
    fi
    printf 'PRODUCTION_RELEASE_DECISION=HOLD\n' >&2
    printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n' >&2
    exit "$rc"
}

require_file_sha() {
    local path="$1"
    local expected="$2"
    local actual

    [[ -f "$path" ]] || fail "MISSING_FILE:${path}"
    actual="$(sha256_file "$path")"
    [[ "$actual" == "$expected" ]] || fail "SHA_MISMATCH:${path}:expected=${expected}:actual=${actual}"
    printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

[[ -x "$PYTHON_BIN" ]] || fail "PYTHON_NOT_EXECUTABLE:${PYTHON_BIN}"
[[ -d "${REPO_ROOT}/.git" ]] || fail "GIT_REPOSITORY_REQUIRED"
[[ -d "${REPO_ROOT}/tests" ]] || fail "TEST_DIRECTORY_MISSING"
[[ ! -e "$TARGET_TEST" ]] || fail "TARGET_TEST_ALREADY_EXISTS:${TARGET_REL}"
if git ls-files --error-unmatch "$TARGET_REL" >/dev/null 2>&1; then
    fail "TARGET_PATH_ALREADY_TRACKED:${TARGET_REL}"
fi
if git check-ignore -q "$TARGET_REL"; then
    fail "TARGET_PATH_IS_GIT_IGNORED:${TARGET_REL}"
fi

require_file_sha "$C1_RESULT" "$EXPECTED_C1_RESULT_SHA"
require_file_sha "$C1_PACKET_MANIFEST" "$EXPECTED_C1_PACKET_MANIFEST_SHA"
require_file_sha "$C1_EVIDENCE_MANIFEST" "$EXPECTED_C1_EVIDENCE_MANIFEST_SHA"
require_file_sha "$CANDIDATE_TEST" "$EXPECTED_CANDIDATE_SHA"
require_file_sha "$D3B_RESULT" "$EXPECTED_D3B_RESULT_SHA"
require_file_sha "$D3B_SUMMARY" "$EXPECTED_D3B_SUMMARY_SHA"
require_file_sha "$D3A_EVIDENCE_MANIFEST" "$EXPECTED_D3A_EVIDENCE_MANIFEST_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$MIGRATION_SOURCE" "$EXPECTED_MIGRATION_SOURCE_SHA"
require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

MATCHING_BASENAME="$(basename "$MATCHING_TESTS")"
MATCHING_EXPECTED_SHA="$(${PYTHON_BIN} - "$D3A_EVIDENCE_MANIFEST" "$MATCHING_BASENAME" <<'PY'
from __future__ import annotations
import re
import sys
from pathlib import Path
manifest = Path(sys.argv[1])
name = sys.argv[2]
pattern = re.compile(r"^([0-9a-f]{64})\s+\*?(?:\./)?(.+)$")
matches = []
for line in manifest.read_text(encoding="utf-8").splitlines():
    match = pattern.match(line.strip())
    if match and Path(match.group(2)).name == name:
        matches.append(match.group(1))
if len(matches) != 1:
    raise SystemExit(f"MATCHING_TEST_INVENTORY_HASH_LOOKUP_FAILED:{len(matches)}")
print(matches[0])
PY
)" || fail "MATCHING_TEST_INVENTORY_HASH_LOOKUP_FAILED"
require_file_sha "$MATCHING_TESTS" "$MATCHING_EXPECTED_SHA"

"$PYTHON_BIN" - \
    "$C1_RESULT" \
    "$C1_PACKET_MANIFEST" \
    "$D3B_RESULT" \
    "$D3B_SUMMARY" \
    "$CANDIDATE_TEST" \
    "$EXPECTED_CANDIDATE_SHA" \
    "$MATCHING_TESTS" <<'PY'
from __future__ import annotations
import ast
import hashlib
import json
import sys
from pathlib import Path

c1_result_path = Path(sys.argv[1])
c1_packet_path = Path(sys.argv[2])
d3b_result_path = Path(sys.argv[3])
d3b_summary_path = Path(sys.argv[4])
candidate_path = Path(sys.argv[5])
expected_candidate_sha = sys.argv[6]
matching_tests_path = Path(sys.argv[7])

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

c1_result = load(c1_result_path)
c1_packet = load(c1_packet_path)
d3b_result = load(d3b_result_path)
d3b_summary = load(d3b_summary_path)

if c1_result.get("result") != "PASS_W2B_I2F3E_C1_MANIFEST_MIGRATION_SEMANTIC_CORRECTION_READY":
    raise SystemExit("C1_RESULT_INVALID")
if c1_result.get("production_release_decision") != "HOLD":
    raise SystemExit("C1_RELEASE_DECISION_INVALID")
if c1_packet.get("result") != "PASS_3E_C1_SEMANTIC_CORRECTION_PACKET_GENERATED":
    raise SystemExit("C1_PACKET_RESULT_INVALID")
if c1_packet.get("status") != "SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION":
    raise SystemExit("C1_PACKET_STATUS_INVALID")
if d3b_result.get("result") != "PASS_W2B_I2F3D_B_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS":
    raise SystemExit("D3B_RESULT_INVALID")
if d3b_result.get("pytest", {}).get("focused_passed_count") != 4:
    raise SystemExit("D3B_FOCUSED_COUNT_INVALID")
if d3b_result.get("pytest", {}).get("related_passed_count") != 17:
    raise SystemExit("D3B_RELATED_COUNT_INVALID")
if d3b_summary.get("pytest", {}).get("focused_passed_count") != 4:
    raise SystemExit("D3B_SUMMARY_FOCUSED_COUNT_INVALID")
if d3b_summary.get("pytest", {}).get("related_passed_count") != 17:
    raise SystemExit("D3B_SUMMARY_RELATED_COUNT_INVALID")
if sha(candidate_path) != expected_candidate_sha:
    raise SystemExit("CANDIDATE_SHA_INVALID")

tree = ast.parse(candidate_path.read_text(encoding="utf-8"))
tests = [
    node.name
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]
if len(tests) != 4:
    raise SystemExit(f"CANDIDATE_TEST_COUNT_INVALID:{len(tests)}")
expected_tests = {
    "test_main_returns_fixed_dependency_error_without_network_or_db_when_slack_bolt_missing",
    "test_main_default_factories_preserve_app_and_handler_arguments_offline",
    "test_worker_stop_controller_close_once_is_idempotent_offline",
    "test_worker_stop_controller_sigterm_requests_stop_and_closes_once_offline",
}
if set(tests) != expected_tests:
    raise SystemExit("CANDIDATE_TEST_NAMES_INVALID")
text = candidate_path.read_text(encoding="utf-8")
if 'REPO_ROOT = Path(__file__).resolve().parents[1]' not in text:
    raise SystemExit("REPOSITORY_RELATIVE_ROOT_MISSING")
if 'Path("/home/deploy/ai_media_os")' in text:
    raise SystemExit("ABSOLUTE_REPOSITORY_ROOT_REMAINS")
if not matching_tests_path.is_file() or not matching_tests_path.read_text(encoding="utf-8").strip():
    raise SystemExit("MATCHING_TEST_INVENTORY_EMPTY")

print("PRE_PROMOTION_SEMANTIC_CHECK=PASS")
print("CANDIDATE_TEST_COUNT=4")
print("PRIOR_RELATED_TEST_COUNT=17")
PY

RUN_ID="$(date -u +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-d-slack-test-promotion-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-d-slack-test-only-promotion-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

[[ ! -e "$SHADOW_ROOT" ]] || fail "SHADOW_ROOT_EXISTS:${SHADOW_ROOT}"
[[ ! -e "$EVIDENCE_ROOT" ]] || fail "EVIDENCE_ROOT_EXISTS:${EVIDENCE_REL}"
mkdir -p "$SHADOW_ROOT/guard" "$SHADOW_ROOT/pycache" "$EVIDENCE_ROOT/snapshots"

APPROVAL_FILE="${EVIDENCE_ROOT}/human-approval-verbatim.txt"
cat > "$APPROVAL_FILE" <<'APPROVAL'
承認：
PACKET_REVIEW=APPROVE
3E_C1_SEMANTIC_CORRECTION_REVIEW=PASS
APPROVE_3E_D_SLACK_TEST_ONLY_PROMOTION_AND_FOCUSED_OFFLINE_TESTS

許可範囲：
1. Evidence内の承認済みcandidate testを、
   tests/test_slack_approval_socket_hold_remediation_offline.py
   として新規追加する。
2. 昇格前後でcandidate SHA
   86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72
   の一致を検証する。
3. 変更対象はテストファイル1件の新規追加だけとする。
4. py_compile、対象4テスト、既存関連17テストのみ実行する。
5. 外部通信とproduction DB接続をテスト中も禁止する。
6. 失敗時は停止し、source・manifest・DB・migrationへ進まない。
7. 実行証跡は新しい一意なevidence領域へ保存する。

禁止事項：
runtime source変更、production manifest変更、production DB接続、
SQL実行、production migration、full pytest suite、deployment、
production approval、外部通信、Slack Worker起動、
production release承認は禁止する。

PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

PRE_STATUS="${EVIDENCE_ROOT}/git-status-scope-before.txt"
POST_STATUS="${EVIDENCE_ROOT}/git-status-scope-after.txt"
git status --porcelain=v1 --untracked-files=all -- app config migrations scripts tests > "$PRE_STATUS"

cp --preserve=mode,timestamps "$CANDIDATE_TEST" "${EVIDENCE_ROOT}/snapshots/approved-candidate-test.py"
cp --preserve=mode,timestamps "$MATCHING_TESTS" "${EVIDENCE_ROOT}/snapshots/matching-test-files.txt"
cp --preserve=mode,timestamps "$C1_RESULT" "${EVIDENCE_ROOT}/snapshots/c1-result.json"
cp --preserve=mode,timestamps "$C1_PACKET_MANIFEST" "${EVIDENCE_ROOT}/snapshots/c1-packet-manifest.json"
cp --preserve=mode,timestamps "$D3B_RESULT" "${EVIDENCE_ROOT}/snapshots/prior-offline-test-result.json"
cp --preserve=mode,timestamps "$D3B_SUMMARY" "${EVIDENCE_ROOT}/snapshots/prior-offline-test-summary.json"

PROTECTED_SHA_BEFORE="${EVIDENCE_ROOT}/protected-sha-before.txt"
{
    sha256sum "$SLACK_SOURCE"
    sha256sum "$WORKFLOW_SOURCE"
    sha256sum "$MIGRATION_SOURCE"
    sha256sum "$PRODUCTION_MANIFEST"
    sha256sum "$DB_PATH"
    sha256sum "$C1_RESULT"
    sha256sum "$C1_PACKET_MANIFEST"
    sha256sum "$C1_EVIDENCE_MANIFEST"
} > "$PROTECTED_SHA_BEFORE"

GUARD_LOG="${EVIDENCE_ROOT}/blocked-operation-attempts.log"
: > "$GUARD_LOG"
SITE_CUSTOMIZE="${SHADOW_ROOT}/guard/sitecustomize.py"
cat > "$SITE_CUSTOMIZE" <<'PY'
from __future__ import annotations

import os
import socket
import sqlite3
from pathlib import Path
from typing import Any

LOG_PATH = Path(os.environ["TST_3E_D_GUARD_LOG"])
PRODUCTION_DB = Path(os.environ["TST_3E_D_PRODUCTION_DB"]).resolve()


def log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def db_targets_production(value: Any) -> bool:
    if not isinstance(value, (str, os.PathLike)):
        return False
    raw = os.fspath(value)
    if raw == ":memory:":
        return False
    if raw.startswith("file:"):
        raw = raw[5:].split("?", 1)[0]
    try:
        return Path(raw).expanduser().resolve() == PRODUCTION_DB
    except (OSError, RuntimeError, ValueError):
        return str(PRODUCTION_DB) in raw


_original_connect = sqlite3.connect


def guarded_connect(database: Any, *args: Any, **kwargs: Any) -> Any:
    if db_targets_production(database):
        log(f"PRODUCTION_DB_CONNECT_BLOCKED:{database}")
        raise AssertionError("PRODUCTION_DATABASE_CONNECTION_FORBIDDEN")
    return _original_connect(database, *args, **kwargs)


sqlite3.connect = guarded_connect
try:
    sqlite3.dbapi2.connect = guarded_connect
except AttributeError:
    pass

_original_socket_connect = socket.socket.connect
_original_socket_connect_ex = socket.socket.connect_ex
_original_create_connection = socket.create_connection


def guarded_socket_connect(self: socket.socket, address: Any) -> Any:
    log(f"NETWORK_CONNECT_BLOCKED:{address!r}")
    raise AssertionError("EXTERNAL_NETWORK_CONNECTION_FORBIDDEN")


def guarded_socket_connect_ex(self: socket.socket, address: Any) -> int:
    log(f"NETWORK_CONNECT_EX_BLOCKED:{address!r}")
    raise AssertionError("EXTERNAL_NETWORK_CONNECTION_FORBIDDEN")


def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    log(f"NETWORK_CREATE_CONNECTION_BLOCKED:{address!r}")
    raise AssertionError("EXTERNAL_NETWORK_CONNECTION_FORBIDDEN")


socket.socket.connect = guarded_socket_connect
socket.socket.connect_ex = guarded_socket_connect_ex
socket.create_connection = guarded_create_connection
PY

"$PYTHON_BIN" -m py_compile "$SITE_CUSTOMIZE"

STAGED_TARGET="${SHADOW_ROOT}/$(basename "$TARGET_TEST")"
cp "$CANDIDATE_TEST" "$STAGED_TARGET"
[[ "$(sha256_file "$STAGED_TARGET")" == "$EXPECTED_CANDIDATE_SHA" ]] || fail "STAGED_CANDIDATE_SHA_MISMATCH"
install -m 0644 "$STAGED_TARGET" "$TARGET_TEST"
[[ "$(sha256_file "$TARGET_TEST")" == "$EXPECTED_CANDIDATE_SHA" ]] || fail "PROMOTED_TARGET_SHA_MISMATCH"

cp --preserve=mode,timestamps "$TARGET_TEST" "${EVIDENCE_ROOT}/snapshots/promoted-test.py"

PYCOMPILE_LOG="${EVIDENCE_ROOT}/py-compile.log"
set +e
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPYCACHEPREFIX="${SHADOW_ROOT}/pycache" \
"$PYTHON_BIN" -m py_compile "$TARGET_TEST" >"$PYCOMPILE_LOG" 2>&1
PYCOMPILE_RC=$?
set -e
cat "$PYCOMPILE_LOG"
[[ "$PYCOMPILE_RC" -eq 0 ]] || fail "PY_COMPILE_FAILED:${PYCOMPILE_RC}" "$PYCOMPILE_RC"

RELATED_LIST="${EVIDENCE_ROOT}/related-test-files-executed.txt"
: > "$RELATED_LIST"
while IFS= read -r raw_path; do
    path="${raw_path%%[[:space:]]*}"
    [[ -n "$path" ]] || continue
    [[ "$path" != "$TARGET_REL" ]] || continue
    if [[ -f "${REPO_ROOT}/${path}" ]]; then
        printf '%s\n' "${REPO_ROOT}/${path}" >> "$RELATED_LIST"
    fi
done < "$MATCHING_TESTS"
LC_ALL=C sort -u -o "$RELATED_LIST" "$RELATED_LIST"
[[ -s "$RELATED_LIST" ]] || fail "NO_RELATED_TEST_FILES_DISCOVERED"
mapfile -t RELATED_TEST_FILES < "$RELATED_LIST"

FOCUSED_LOG="${EVIDENCE_ROOT}/pytest-focused.log"
RELATED_LOG="${EVIDENCE_ROOT}/pytest-related.log"

COMMON_ENV=(
    "PYTHONDONTWRITEBYTECODE=1"
    "PYTHONPYCACHEPREFIX=${SHADOW_ROOT}/pycache"
    "PYTHONPATH=${SHADOW_ROOT}/guard:${REPO_ROOT}"
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"
    "TST_3E_D_GUARD_LOG=${GUARD_LOG}"
    "TST_3E_D_PRODUCTION_DB=${DB_PATH}"
)

set +e
env "${COMMON_ENV[@]}" timeout 180s \
    "$PYTHON_BIN" -m pytest -q -p no:cacheprovider "$TARGET_TEST" \
    > "$FOCUSED_LOG" 2>&1
FOCUSED_RC=$?
set -e
cat "$FOCUSED_LOG"
[[ "$FOCUSED_RC" -eq 0 ]] || fail "FOCUSED_TESTS_FAILED:${FOCUSED_RC}" "$FOCUSED_RC"

set +e
env "${COMMON_ENV[@]}" timeout 180s \
    "$PYTHON_BIN" -m pytest -q -p no:cacheprovider "${RELATED_TEST_FILES[@]}" \
    > "$RELATED_LOG" 2>&1
RELATED_RC=$?
set -e
cat "$RELATED_LOG"
[[ "$RELATED_RC" -eq 0 ]] || fail "RELATED_TESTS_FAILED:${RELATED_RC}" "$RELATED_RC"

TEST_COUNTS_JSON="${EVIDENCE_ROOT}/test-count-validation.json"
"$PYTHON_BIN" - \
    "$TARGET_TEST" \
    "$FOCUSED_LOG" \
    "$RELATED_LOG" \
    "$TEST_COUNTS_JSON" <<'PY'
from __future__ import annotations
import ast
import json
import re
import sys
from pathlib import Path

target = Path(sys.argv[1])
focused_log = Path(sys.argv[2])
related_log = Path(sys.argv[3])
output = Path(sys.argv[4])

def passed_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    values = [int(value) for value in re.findall(r"(?m)(\d+)\s+passed(?:\s|,|$)", text)]
    if len(values) != 1:
        raise SystemExit(f"PYTEST_PASS_COUNT_UNRESOLVED:{path}:{values}")
    return values[0]

tree = ast.parse(target.read_text(encoding="utf-8"))
test_names = [
    node.name for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]
focused = passed_count(focused_log)
related = passed_count(related_log)
if len(test_names) != 4 or focused != 4 or related != 17:
    raise SystemExit(
        f"TEST_COUNT_CONTRACT_FAILED:test_names={len(test_names)}:focused={focused}:related={related}"
    )
report = {
    "schema_version": "1.0",
    "result": "PASS_TEST_COUNT_CONTRACT",
    "target_test_count": len(test_names),
    "target_test_names": test_names,
    "focused_passed_count": focused,
    "related_passed_count": related,
    "full_suite_executed": False,
}
output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print("FOCUSED_TEST_PASSED_COUNT=4")
print("RELATED_TEST_PASSED_COUNT=17")
PY

if [[ -s "$GUARD_LOG" ]]; then
    cat "$GUARD_LOG" >&2
    fail "PROHIBITED_OPERATION_ATTEMPT_DETECTED"
fi

PROTECTED_SHA_AFTER="${EVIDENCE_ROOT}/protected-sha-after.txt"
{
    sha256sum "$SLACK_SOURCE"
    sha256sum "$WORKFLOW_SOURCE"
    sha256sum "$MIGRATION_SOURCE"
    sha256sum "$PRODUCTION_MANIFEST"
    sha256sum "$DB_PATH"
    sha256sum "$C1_RESULT"
    sha256sum "$C1_PACKET_MANIFEST"
    sha256sum "$C1_EVIDENCE_MANIFEST"
} > "$PROTECTED_SHA_AFTER"
cmp -s "$PROTECTED_SHA_BEFORE" "$PROTECTED_SHA_AFTER" || fail "PROTECTED_SHA_SET_CHANGED"

git status --porcelain=v1 --untracked-files=all -- app config migrations scripts tests > "$POST_STATUS"
"$PYTHON_BIN" - "$PRE_STATUS" "$POST_STATUS" "$TARGET_REL" <<'PY'
from __future__ import annotations
import sys
from pathlib import Path

before = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
after = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
target = sys.argv[3]
expected_line = f"?? {target}"
expected = before + [expected_line]
if sorted(after) != sorted(expected):
    raise SystemExit(
        "REPOSITORY_SCOPE_CHANGE_SET_INVALID:"
        f"before={before!r}:after={after!r}:expected_added={expected_line!r}"
    )
print("REPOSITORY_SCOPE_CHANGE_SET=TARGET_TEST_ADD_ONLY")
PY

[[ "$(sha256_file "$TARGET_TEST")" == "$EXPECTED_CANDIDATE_SHA" ]] || fail "FINAL_TARGET_SHA_MISMATCH"

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
"$PYTHON_BIN" - \
    "$RESULT_JSON" \
    "$EVIDENCE_REL" \
    "$TARGET_REL" \
    "$EXPECTED_CANDIDATE_SHA" \
    "$PYCOMPILE_LOG" \
    "$FOCUSED_LOG" \
    "$RELATED_LOG" \
    "$TEST_COUNTS_JSON" \
    "$APPROVAL_FILE" \
    "$PRE_STATUS" \
    "$POST_STATUS" \
    "$PROTECTED_SHA_BEFORE" \
    "$PROTECTED_SHA_AFTER" \
    "$GUARD_LOG" <<'PY'
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    result_path,
    evidence_rel,
    target_rel,
    expected_sha,
    pycompile_log,
    focused_log,
    related_log,
    counts_json,
    approval_file,
    pre_status,
    post_status,
    protected_before,
    protected_after,
    guard_log,
) = sys.argv[1:]

def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

counts = json.loads(Path(counts_json).read_text(encoding="utf-8"))
completed = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-D",
    "result": "PASS_W2B_I2F3E_D_SLACK_TEST_ONLY_PROMOTED_AND_FOCUSED_OFFLINE_TESTS",
    "evidence_root": evidence_rel,
    "approval": {
        "approval_label": "APPROVE_3E_D_SLACK_TEST_ONLY_PROMOTION_AND_FOCUSED_OFFLINE_TESTS",
        "approval_verbatim_sha256": sha(approval_file),
    },
    "promotion": {
        "target_path": target_rel,
        "candidate_sha256": expected_sha,
        "promoted_sha256": expected_sha,
        "candidate_promoted_sha_match": True,
        "operation": "ADD_TEST_FILE_ONLY",
        "repository_scope_change_set": "TARGET_TEST_ADD_ONLY",
    },
    "tests": {
        "py_compile": "PASS",
        "py_compile_log_sha256": sha(pycompile_log),
        "focused_passed_count": counts["focused_passed_count"],
        "related_passed_count": counts["related_passed_count"],
        "focused_log_sha256": sha(focused_log),
        "related_log_sha256": sha(related_log),
        "test_count_validation_sha256": sha(counts_json),
        "full_suite_executed": False,
    },
    "guards": {
        "external_network_guard_active": True,
        "production_database_guard_active": True,
        "blocked_operation_attempt_count": 0,
        "guard_log_sha256": sha(guard_log),
    },
    "evidence": {
        "git_status_before_sha256": sha(pre_status),
        "git_status_after_sha256": sha(post_status),
        "protected_sha_before_sha256": sha(protected_before),
        "protected_sha_after_sha256": sha(protected_after),
    },
    "safety": {
        "runtime_source_modified": False,
        "workflow_source_modified": False,
        "migration_source_modified": False,
        "production_manifest_modified": False,
        "production_database_content_changed": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
        "production_migration_applied": False,
        "full_pytest_suite_executed": False,
        "deployment_performed": False,
        "production_approval_created": False,
        "external_network_used": False,
        "slack_worker_started": False,
        "production_release_approved": False,
    },
    "governance": {
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate": "HUMAN_REVIEW_3E_D_TEST_PROMOTION_EVIDENCE",
    },
    "completed_at_utc": completed,
}
Path(result_path).write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/test-promotion-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'test-promotion-evidence-manifest.txt' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"

RESULT_SHA="$(sha256_file "$RESULT_JSON")"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"
TARGET_SHA="$(sha256_file "$TARGET_TEST")"

find "$EVIDENCE_ROOT" -type f -exec chmod 0444 {} +

printf '\nRESULT=PASS_W2B_I2F3E_D_SLACK_TEST_ONLY_PROMOTED_AND_FOCUSED_OFFLINE_TESTS\n'
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'TARGET_TEST=%s\n' "$TARGET_REL"
printf 'TARGET_TEST_CREATED=true\n'
printf 'CANDIDATE_SHA=%s\n' "$EXPECTED_CANDIDATE_SHA"
printf 'PROMOTED_TEST_SHA=%s\n' "$TARGET_SHA"
printf 'CANDIDATE_PROMOTED_SHA_MATCH=true\n'
printf 'REPOSITORY_SCOPE_CHANGE_SET=TARGET_TEST_ADD_ONLY\n'
printf 'PY_COMPILE=PASS\n'
printf 'FOCUSED_TEST_PASSED_COUNT=4\n'
printf 'RELATED_TEST_PASSED_COUNT=17\n'
printf 'FULL_PYTEST_SUITE_EXECUTED=false\n'
printf 'NETWORK_GUARD_ACTIVE=true\n'
printf 'PRODUCTION_DB_GUARD_ACTIVE=true\n'
printf 'GUARD_VIOLATION_COUNT=0\n'
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RUNTIME_SOURCE_MODIFIED=false\n'
printf 'WORKFLOW_SOURCE_MODIFIED=false\n'
printf 'MIGRATION_SOURCE_MODIFIED=false\n'
printf 'PRODUCTION_MANIFEST_MODIFIED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'SQL_EXECUTED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'PRODUCTION_RELEASE_APPROVED=false\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_GATE=HUMAN_REVIEW_3E_D_TEST_PROMOTION_EVIDENCE\n'
printf 'SCRIPT_EXIT_CODE=0\n'
