#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
DECISION_ROOT_REL="${I2E_ROOT_REL}/i2f3c-c-human-review-decision-record-20260725T161539-495634"
BUNDLE_ROOT_REL="${I2E_ROOT_REL}/i2f3c-b-review-bundle-validation-20260725T160528-494244"

DECISION_RESULT="${REPO_ROOT}/${DECISION_ROOT_REL}/result.json"
DECISION_SET="${REPO_ROOT}/${DECISION_ROOT_REL}/human-review-decision-set.json"
DECISION_VALIDATION="${REPO_ROOT}/${DECISION_ROOT_REL}/human-review-decision-validation.json"
APPROVAL_VERBATIM="${REPO_ROOT}/${DECISION_ROOT_REL}/human-approval-verbatim.txt"
DECISION_EVIDENCE_MANIFEST="${REPO_ROOT}/${DECISION_ROOT_REL}/decision-evidence-manifest.txt"
BUNDLE_RESULT="${REPO_ROOT}/${BUNDLE_ROOT_REL}/result.json"

EXPECTED_DECISION_RESULT_SHA="1790eedbf06d94c29c7dbe03e7aa3dd9bea4b4343f5cd3a1c4ea42d6ed732cba"
EXPECTED_DECISION_SET_SHA="4c72b8b39f30961741c47702e00d9dd4062168bf943fe96ffcbea63d29e65cf6"
EXPECTED_DECISION_VALIDATION_SHA="d4fa57d22ec2d5f3d149755f37035f06fb54f2392404cfaabc59021d8ae7da86"
EXPECTED_APPROVAL_VERBATIM_SHA="77f43f601c043e41a07b8bcf0c8f4fe3a0074eda19a8ef9a8ac9b010f7116116"
EXPECTED_DECISION_EVIDENCE_MANIFEST_SHA="ee41601f75c8e5afd9ea7d1255957395f4e62a0323484690805812b7ab78d79d"
EXPECTED_BUNDLE_RESULT_SHA="5a56b1df319d1a056a0ba3c4a86c3edcf3ceca2b0c74b97cde4a6133041275e8"

SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

require_file_sha() {
    local path="$1"
    local expected="$2"
    local actual

    if [[ ! -f "$path" ]]; then
        printf 'ERROR=MISSING_FILE:%s\n' "$path" >&2
        exit 1
    fi

    actual="$(sha256_file "$path")"
    if [[ "$actual" != "$expected" ]]; then
        printf 'ERROR=SHA_MISMATCH:%s\nEXPECTED=%s\nACTUAL=%s\n' \
            "$path" "$expected" "$actual" >&2
        exit 1
    fi

    printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

require_file_sha "$DECISION_RESULT" "$EXPECTED_DECISION_RESULT_SHA"
require_file_sha "$DECISION_SET" "$EXPECTED_DECISION_SET_SHA"
require_file_sha "$DECISION_VALIDATION" "$EXPECTED_DECISION_VALIDATION_SHA"
require_file_sha "$APPROVAL_VERBATIM" "$EXPECTED_APPROVAL_VERBATIM_SHA"
require_file_sha \
    "$DECISION_EVIDENCE_MANIFEST" \
    "$EXPECTED_DECISION_EVIDENCE_MANIFEST_SHA"
require_file_sha "$BUNDLE_RESULT" "$EXPECTED_BUNDLE_RESULT_SHA"

require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3d-a-slack-hold-remediation-test-inventory-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_ROOT"

INVENTORY_JSON="${EVIDENCE_ROOT}/slack-hold-remediation-test-inventory.json"
INVENTORY_TEXT="${EVIDENCE_ROOT}/slack-hold-remediation-test-inventory.txt"
SOURCE_SYMBOLS="${EVIDENCE_ROOT}/slack-runtime-source-symbols.json"
MATCHING_TESTS="${EVIDENCE_ROOT}/matching-test-files.txt"
IMPLEMENTATION_PLAN="${EVIDENCE_ROOT}/offline-test-implementation-plan.json"

python3 - \
    "$REPO_ROOT" \
    "$SLACK_SOURCE" \
    "$DECISION_SET" \
    "$INVENTORY_JSON" \
    "$INVENTORY_TEXT" \
    "$SOURCE_SYMBOLS" \
    "$MATCHING_TESTS" \
    "$IMPLEMENTATION_PLAN" <<'PY'
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
source_path = Path(sys.argv[2]).resolve()
decision_set_path = Path(sys.argv[3]).resolve()
inventory_json_path = Path(sys.argv[4])
inventory_text_path = Path(sys.argv[5])
source_symbols_path = Path(sys.argv[6])
matching_tests_path = Path(sys.argv[7])
implementation_plan_path = Path(sys.argv[8])

source_text = source_path.read_text(encoding="utf-8")
source_tree = ast.parse(source_text, filename=str(source_path))
source_lines = source_text.splitlines()
decision_set = json.loads(decision_set_path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def function_metadata(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = []
    for arg in node.args.posonlyargs:
        args.append({"name": arg.arg, "kind": "positional_only"})
    for arg in node.args.args:
        args.append({"name": arg.arg, "kind": "positional_or_keyword"})
    for arg in node.args.kwonlyargs:
        args.append({"name": arg.arg, "kind": "keyword_only"})
    if node.args.vararg is not None:
        args.append({"name": node.args.vararg.arg, "kind": "var_positional"})
    if node.args.kwarg is not None:
        args.append({"name": node.args.kwarg.arg, "kind": "var_keyword"})
    return {
        "name": node.name,
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", node.lineno),
        "arguments": args,
    }


symbols: dict[str, Any] = {
    "functions": {},
    "classes": {},
    "constants": {},
}

for node in source_tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        symbols["functions"][node.name] = function_metadata(node)
    elif isinstance(node, ast.ClassDef):
        methods = {}
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods[child.name] = function_metadata(child)
        symbols["classes"][node.name] = {
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "methods": methods,
        }
    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        else:
            targets.append(node.target)
        for target in targets:
            if isinstance(target, ast.Name):
                symbols["constants"][target.id] = {
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", node.lineno),
                }

required_source_contract = {
    "functions": {
        "load_slack_runtime",
        "build_app",
        "main",
    },
    "classes": {
        "SlackBoltDependencyNotAvailable",
        "WorkerStopController",
    },
    "constants": {
        "SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE",
    },
}

source_contract_checks = {
    f"function:{name}": name in symbols["functions"]
    for name in sorted(required_source_contract["functions"])
}
source_contract_checks.update(
    {
        f"class:{name}": name in symbols["classes"]
        for name in sorted(required_source_contract["classes"])
    }
)
source_contract_checks.update(
    {
        f"constant:{name}": name in symbols["constants"]
        for name in sorted(required_source_contract["constants"])
    }
)

main_args = {
    item["name"]: item["kind"]
    for item in symbols["functions"].get("main", {}).get("arguments", [])
}
build_app_args = {
    item["name"]: item["kind"]
    for item in symbols["functions"].get("build_app", {}).get("arguments", [])
}

source_contract_checks.update(
    {
        "main_handler_factory_keyword_only": (
            main_args.get("handler_factory") == "keyword_only"
        ),
        "build_app_app_factory_keyword_only": (
            build_app_args.get("app_factory") == "keyword_only"
        ),
        "worker_stop_close_once_present": (
            "close_once"
            in symbols["classes"]
            .get("WorkerStopController", {})
            .get("methods", {})
        ),
        "worker_stop_request_stop_present": (
            "request_stop"
            in symbols["classes"]
            .get("WorkerStopController", {})
            .get("methods", {})
        ),
    }
)

test_files = sorted(
    path
    for path in (repo / "tests").rglob("*.py")
    if path.is_file() and "__pycache__" not in path.parts
)

search_tokens = {
    "load_slack_runtime",
    "SlackBoltDependencyNotAvailable",
    "SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE",
    "app_factory",
    "handler_factory",
    "WorkerStopController",
    "run_slack_approval_socket",
    "SocketModeHandler",
}

matching: list[dict[str, Any]] = []
for path in test_files:
    text = path.read_text(encoding="utf-8", errors="replace")
    present = sorted(token for token in search_tokens if token in text)
    if not present:
        continue
    relative = path.relative_to(repo).as_posix()
    test_names = re.findall(r"^def\s+(test_[A-Za-z0-9_]+)\s*\(", text, re.MULTILINE)
    matching.append(
        {
            "path": relative,
            "sha256": sha(path),
            "matching_tokens": present,
            "test_names": test_names,
            "line_count": len(text.splitlines()),
            "text": text,
        }
    )

matching_tests_path.write_text(
    "\n".join(
        f"{item['path']} {item['sha256']} "
        f"tokens={','.join(item['matching_tokens'])} "
        f"tests={','.join(item['test_names'])}"
        for item in matching
    )
    + ("\n" if matching else ""),
    encoding="utf-8",
)

import_error_required = {
    "ImportError",
    "SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE",
    "load_slack_runtime",
}
factory_required = {
    "app_factory",
    "handler_factory",
}
lifecycle_required = {
    "handler_factory",
    "start",
    "close",
}

import_error_candidates = []
factory_candidates = []
lifecycle_candidates = []

for item in matching:
    text = item["text"]
    tokens = set(item["matching_tokens"])

    import_signals = {
        signal
        for signal in import_error_required
        if signal in text
    }
    factory_signals = {
        signal
        for signal in factory_required
        if signal in text
    }
    lifecycle_signals = {
        signal
        for signal in lifecycle_required
        if signal in text
    }

    if import_signals:
        import_error_candidates.append(
            {
                "path": item["path"],
                "signals": sorted(import_signals),
                "test_names": item["test_names"],
            }
        )
    if factory_signals:
        factory_candidates.append(
            {
                "path": item["path"],
                "signals": sorted(factory_signals),
                "test_names": item["test_names"],
            }
        )
    if lifecycle_signals:
        lifecycle_candidates.append(
            {
                "path": item["path"],
                "signals": sorted(lifecycle_signals),
                "test_names": item["test_names"],
            }
        )

# Conservative inventory rule:
# Existing coverage is considered sufficient only when one focused test file
# contains all required observable signals for the approved HOLD condition.
import_error_full_match = [
    item
    for item in matching
    if all(token in item["text"] for token in import_error_required)
    and (
        "return_value" in item["text"]
        or "== 3" in item["text"]
        or "exit_code" in item["text"]
    )
    and (
        "not_called" in item["text"]
        or "assert_not_called" in item["text"]
        or "called is False" in item["text"]
    )
]

factory_full_match = [
    item
    for item in matching
    if all(token in item["text"] for token in factory_required)
    and (
        "assert_called_once_with" in item["text"]
        or "call_args" in item["text"]
        or "captured" in item["text"]
    )
    and "bot_token" in item["text"]
    and "app_token" in item["text"]
]

hold_conditions = (
    decision_set.get("decisions", {})
    .get("UNIT_SLACK_RUNTIME", {})
    .get("requested_decision_label")
)
overall_decision = decision_set.get("overall_candidate_decision")

if hold_conditions != "HOLD":
    raise SystemExit("UNIT_SLACK_RUNTIME_DECISION_NOT_HOLD")
if overall_decision != "HOLD":
    raise SystemExit("OVERALL_CANDIDATE_DECISION_NOT_HOLD")

recommended_test_file = (
    "tests/test_slack_approval_socket_hold_remediation_offline.py"
)

planned_tests = [
    {
        "test_name": (
            "test_main_returns_fixed_dependency_error_without_network_or_db_"
            "when_slack_bolt_missing"
        ),
        "hold_condition": "SLACK_BOLT_IMPORT_ERROR_FIXED_ERROR",
        "required_assertions": [
            "force load_slack_runtime to raise SlackBoltDependencyNotAvailable",
            "main returns 3",
            "stderr contains only the fixed dependency error token",
            "handler factory is not called",
            "handler.start is not reached",
            "SessionLocal is not called",
            "no external network operation is invoked",
        ],
        "execution_boundary": "OFFLINE_TMP_ONLY_NO_PRODUCTION_DB",
    },
    {
        "test_name": (
            "test_main_default_factories_preserve_app_and_handler_arguments_"
            "offline"
        ),
        "hold_condition": "PRODUCTION_DEFAULT_FACTORY_EQUIVALENCE",
        "required_assertions": [
            "default app factory receives token=config.bot_token",
            "default handler factory receives app and config.app_token",
            "handler.start is called exactly once",
            "handler.close is called at most once",
            "SIGTERM handler is restored",
            "no external Slack communication occurs because all factories are fakes",
            "no production database is opened",
        ],
        "execution_boundary": "OFFLINE_FAKE_FACTORIES_TMP_ONLY",
    },
]

gaps = {
    "slack_bolt_import_error_fixed_error_test_missing": (
        len(import_error_full_match) == 0
    ),
    "production_default_factory_equivalence_test_missing": (
        len(factory_full_match) == 0
    ),
}

inventory_result = (
    "PASS_SLACK_HOLD_REMEDIATION_INVENTORY_READY"
    if all(source_contract_checks.values())
    else "FAIL_SLACK_SOURCE_CONTRACT_INVENTORY"
)

inventory = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3D-A",
    "result": inventory_result,
    "source": {
        "path": source_path.relative_to(repo).as_posix(),
        "sha256": sha(source_path),
        "contract_checks": source_contract_checks,
        "symbols": symbols,
    },
    "human_decision": {
        "decision_set_path": decision_set_path.relative_to(repo).as_posix(),
        "decision_set_sha256": sha(decision_set_path),
        "unit_slack_runtime": hold_conditions,
        "overall_candidate_decision": overall_decision,
        "release_status": decision_set.get("release_status"),
    },
    "test_inventory": {
        "python_test_file_count": len(test_files),
        "matching_test_file_count": len(matching),
        "matching_test_files": [
            {
                key: value
                for key, value in item.items()
                if key != "text"
            }
            for item in matching
        ],
        "import_error_candidates": import_error_candidates,
        "factory_candidates": factory_candidates,
        "lifecycle_candidates": lifecycle_candidates,
        "import_error_full_match_count": len(import_error_full_match),
        "factory_full_match_count": len(factory_full_match),
    },
    "gaps": gaps,
    "recommended_test_file": recommended_test_file,
    "planned_tests": planned_tests,
    "execution": {
        "source_modified": False,
        "test_file_created": False,
        "pytest_executed": False,
        "production_database_opened": False,
        "external_network_used": False,
    },
    "governance": {
        "unit_slack_runtime": "HOLD_PENDING_OFFLINE_FOCUSED_TESTS",
        "overall_candidate_decision": "HOLD",
        "production_approval_created": False,
        "production_manifest_update_allowed": False,
        "production_database_access_allowed": False,
        "production_migration_allowed": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "external_network_allowed": False,
    },
    "next_phase": (
        "TST-5D-W2B-I2F-3D-B_SLACK_HOLD_REMEDIATION_"
        "OFFLINE_TEST_IMPLEMENTATION"
    ),
}

write_json(inventory_json_path, inventory)
write_json(
    source_symbols_path,
    {
        "source_path": source_path.relative_to(repo).as_posix(),
        "source_sha256": sha(source_path),
        "symbols": symbols,
        "contract_checks": source_contract_checks,
    },
)

implementation_plan = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3D-B-PLAN",
    "status": "DESIGN_ONLY_NOT_IMPLEMENTED",
    "target_source": source_path.relative_to(repo).as_posix(),
    "target_source_sha256": sha(source_path),
    "recommended_test_file": recommended_test_file,
    "planned_tests": planned_tests,
    "implementation_rules": [
        "Do not modify production runtime source.",
        "Create the test first in a unique shadow test root.",
        "Use monkeypatch/fake factories only.",
        "Block SessionLocal and assert it is not called for ImportError.",
        "Do not import or start a real SocketModeHandler.",
        "Do not open the production database.",
        "Do not read credential contents.",
        "Do not use Slack, WordPress, X, or other external network.",
        "Run only the two focused tests plus directly related existing Slack runtime tests.",
        "Preserve all failed attempts as immutable evidence.",
    ],
    "approval_boundary": {
        "test_implementation_allowed_by_hold_condition": True,
        "runtime_source_change_allowed": False,
        "production_manifest_update_allowed": False,
        "deployment_allowed": False,
    },
}
write_json(implementation_plan_path, implementation_plan)

text_lines = [
    f"RESULT={inventory_result}",
    f"SLACK_SOURCE_SHA={sha(source_path)}",
    f"PYTHON_TEST_FILE_COUNT={len(test_files)}",
    f"MATCHING_TEST_FILE_COUNT={len(matching)}",
    f"IMPORT_ERROR_FULL_MATCH_COUNT={len(import_error_full_match)}",
    f"FACTORY_EQUIVALENCE_FULL_MATCH_COUNT={len(factory_full_match)}",
    (
        "IMPORT_ERROR_FIXED_ERROR_TEST_MISSING="
        + str(gaps["slack_bolt_import_error_fixed_error_test_missing"]).lower()
    ),
    (
        "DEFAULT_FACTORY_EQUIVALENCE_TEST_MISSING="
        + str(
            gaps["production_default_factory_equivalence_test_missing"]
        ).lower()
    ),
    f"RECOMMENDED_TEST_FILE={recommended_test_file}",
    "SOURCE_MODIFIED=false",
    "TEST_FILE_CREATED=false",
    "PYTEST_EXECUTED=false",
    "PRODUCTION_DB_OPENED=false",
    "EXTERNAL_NETWORK_USED=false",
    "UNIT_SLACK_RUNTIME=HOLD_PENDING_OFFLINE_FOCUSED_TESTS",
    "OVERALL_CANDIDATE_DECISION=HOLD",
    (
        "NEXT_PHASE=TST-5D-W2B-I2F-3D-B_"
        "SLACK_HOLD_REMEDIATION_OFFLINE_TEST_IMPLEMENTATION"
    ),
]
inventory_text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

if inventory_result.startswith("FAIL"):
    failed = sorted(
        name for name, passed in source_contract_checks.items() if not passed
    )
    raise SystemExit(
        "SLACK_SOURCE_CONTRACT_INVENTORY_FAILED:" + ",".join(failed)
    )
PY

python3 -m json.tool "$INVENTORY_JSON" >/dev/null
python3 -m json.tool "$SOURCE_SYMBOLS" >/dev/null
python3 -m json.tool "$IMPLEMENTATION_PLAN" >/dev/null

cat "$INVENTORY_TEXT"

INVENTORY_JSON_SHA="$(sha256_file "$INVENTORY_JSON")"
INVENTORY_TEXT_SHA="$(sha256_file "$INVENTORY_TEXT")"
SOURCE_SYMBOLS_SHA="$(sha256_file "$SOURCE_SYMBOLS")"
MATCHING_TESTS_SHA="$(sha256_file "$MATCHING_TESTS")"
IMPLEMENTATION_PLAN_SHA="$(sha256_file "$IMPLEMENTATION_PLAN")"

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/inventory-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'inventory-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"

EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

SLACK_SOURCE_AFTER="$(sha256_file "$SLACK_SOURCE")"
WORKFLOW_SOURCE_AFTER="$(sha256_file "$WORKFLOW_SOURCE")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"
DECISION_RESULT_AFTER="$(sha256_file "$DECISION_RESULT")"

[[ "$SLACK_SOURCE_AFTER" == "$EXPECTED_SLACK_SOURCE_SHA" ]] || {
    printf 'ERROR=SLACK_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$WORKFLOW_SOURCE_AFTER" == "$EXPECTED_WORKFLOW_SOURCE_SHA" ]] || {
    printf 'ERROR=WORKFLOW_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}
[[ "$DECISION_RESULT_AFTER" == "$EXPECTED_DECISION_RESULT_SHA" ]] || {
    printf 'ERROR=HUMAN_DECISION_RECORD_CHANGED\n' >&2
    exit 1
}

IMPORT_ERROR_MISSING="$(
    python3 -c \
        'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["gaps"]["slack_bolt_import_error_fixed_error_test_missing"]).lower())' \
        "$INVENTORY_JSON"
)"
FACTORY_EQUIVALENCE_MISSING="$(
    python3 -c \
        'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["gaps"]["production_default_factory_equivalence_test_missing"]).lower())' \
        "$INVENTORY_JSON"
)"
MATCHING_TEST_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["test_inventory"]["matching_test_file_count"])' \
        "$INVENTORY_JSON"
)"
IMPORT_FULL_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["test_inventory"]["import_error_full_match_count"])' \
        "$INVENTORY_JSON"
)"
FACTORY_FULL_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["test_inventory"]["factory_full_match_count"])' \
        "$INVENTORY_JSON"
)"

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3D-A",
  "result": "PASS_W2B_I2F3D_A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY_READY",
  "evidence_root": "${EVIDENCE_REL}",
  "human_decision_result_sha256": "${EXPECTED_DECISION_RESULT_SHA}",
  "slack_source_sha256": "${EXPECTED_SLACK_SOURCE_SHA}",
  "inventory": {
    "matching_test_file_count": ${MATCHING_TEST_COUNT},
    "import_error_full_match_count": ${IMPORT_FULL_COUNT},
    "factory_equivalence_full_match_count": ${FACTORY_FULL_COUNT},
    "import_error_fixed_error_test_missing": ${IMPORT_ERROR_MISSING},
    "production_default_factory_equivalence_test_missing": ${FACTORY_EQUIVALENCE_MISSING},
    "recommended_test_file": "tests/test_slack_approval_socket_hold_remediation_offline.py"
  },
  "artifacts": {
    "inventory_json_sha256": "${INVENTORY_JSON_SHA}",
    "inventory_text_sha256": "${INVENTORY_TEXT_SHA}",
    "source_symbols_sha256": "${SOURCE_SYMBOLS_SHA}",
    "matching_test_files_sha256": "${MATCHING_TESTS_SHA}",
    "implementation_plan_sha256": "${IMPLEMENTATION_PLAN_SHA}",
    "inventory_evidence_manifest_sha256": "${EVIDENCE_MANIFEST_SHA}"
  },
  "execution": {
    "source_modified": false,
    "test_file_created": false,
    "pytest_executed": false,
    "production_database_opened": false,
    "external_network_used": false
  },
  "governance": {
    "unit_slack_runtime": "HOLD_PENDING_OFFLINE_FOCUSED_TESTS",
    "overall_candidate_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": false,
    "production_manifest_update_allowed": false,
    "production_database_access_allowed": false,
    "production_migration_allowed": false,
    "deployment_allowed": false,
    "runtime_execution_allowed": false,
    "external_network_allowed": false
  },
  "safety": {
    "slack_source_changed": false,
    "workflow_source_changed": false,
    "human_decision_record_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "next_phase": "TST-5D-W2B-I2F-3D-B_SLACK_HOLD_REMEDIATION_OFFLINE_TEST_IMPLEMENTATION",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3D_A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY_READY\n'
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'SLACK_SOURCE_SHA=%s\n' "$EXPECTED_SLACK_SOURCE_SHA"
printf 'MATCHING_TEST_FILE_COUNT=%s\n' "$MATCHING_TEST_COUNT"
printf 'IMPORT_ERROR_FULL_MATCH_COUNT=%s\n' "$IMPORT_FULL_COUNT"
printf 'FACTORY_EQUIVALENCE_FULL_MATCH_COUNT=%s\n' "$FACTORY_FULL_COUNT"
printf 'IMPORT_ERROR_FIXED_ERROR_TEST_MISSING=%s\n' "$IMPORT_ERROR_MISSING"
printf 'DEFAULT_FACTORY_EQUIVALENCE_TEST_MISSING=%s\n' "$FACTORY_EQUIVALENCE_MISSING"
printf 'RECOMMENDED_TEST_FILE=tests/test_slack_approval_socket_hold_remediation_offline.py\n'
printf 'INVENTORY_JSON_SHA=%s\n' "$INVENTORY_JSON_SHA"
printf 'IMPLEMENTATION_PLAN_SHA=%s\n' "$IMPLEMENTATION_PLAN_SHA"
printf 'EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'SOURCE_MODIFIED=false\n'
printf 'TEST_FILE_CREATED=false\n'
printf 'PYTEST_EXECUTED=false\n'
printf 'HUMAN_DECISION_RECORD_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_SLACK_RUNTIME=HOLD_PENDING_OFFLINE_FOCUSED_TESTS\n'
printf 'OVERALL_CANDIDATE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3D-B_SLACK_HOLD_REMEDIATION_OFFLINE_TEST_IMPLEMENTATION\n'
printf 'SCRIPT_EXIT_CODE=0\n'
