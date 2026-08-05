#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
R3_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3b-r3-complete-shadow-20260725T152341-488959"
R4_CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-r4-candidate-20260725T153121-489639"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
R3_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r3-complete-shadow-graph-20260725T152341-488959"
R4_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r4-shadow-candidate-validation-20260725T153121-489639"

R3_RESULT="${REPO_ROOT}/${R3_ROOT_REL}/result.json"
R3_SNAPSHOT_MANIFEST="${REPO_ROOT}/${R3_ROOT_REL}/shadow-snapshot-manifest.txt"
R4_RESULT="${REPO_ROOT}/${R4_ROOT_REL}/result.json"

EXPECTED_R3_RESULT_SHA="a99f495ec37c1daa2936d63e9d67f6aaac346b1836e3d1e1ce83fa7f1774daf4"
EXPECTED_R3_SNAPSHOT_MANIFEST_SHA="8f6626c9b2940a0593933c2e76122657d36c6695d7181e3b8b9eb27a41d7795b"
EXPECTED_R4_RESULT_SHA="eb3e7f8ff7fbd2ab77179515d3b06ed3da4644d4347e437bf7f7abde2bfa14d2"

CANDIDATE_PATH="${R4_CANDIDATE_ROOT}/candidate-manifest.json"
CLOSURE_PATH="${R4_CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PATH="${R4_CANDIDATE_ROOT}/downstream-rebinding-plan.json"

EXPECTED_CANDIDATE_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"
EXPECTED_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_SHA="5fa8255966773bda7d35ba0d89b1f40c0f8b9a7df89b33578e3997f6cc22bed8"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
R3_SHADOW_MANIFEST="${R3_SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_R3_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"
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

verify_r3_snapshot() {
    while read -r expected relative; do
        [[ -n "$expected" && -n "$relative" ]] || continue
        local actual_path="${R3_SHADOW_ROOT}/${relative#./}"
        require_file_sha "$actual_path" "$expected"
    done < "$R3_SNAPSHOT_MANIFEST"
}

cd "$REPO_ROOT"

require_file_sha "$R3_RESULT" "$EXPECTED_R3_RESULT_SHA"
require_file_sha \
    "$R3_SNAPSHOT_MANIFEST" \
    "$EXPECTED_R3_SNAPSHOT_MANIFEST_SHA"
require_file_sha "$R4_RESULT" "$EXPECTED_R4_RESULT_SHA"
require_file_sha "$CANDIDATE_PATH" "$EXPECTED_CANDIDATE_SHA"
require_file_sha "$CLOSURE_PATH" "$EXPECTED_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_PATH" "$EXPECTED_DOWNSTREAM_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha \
    "$R3_SHADOW_MANIFEST" \
    "$EXPECTED_R3_SHADOW_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

if [[ ! -d "$R3_SHADOW_ROOT" ]]; then
    printf 'ERROR=R3_SHADOW_ROOT_MISSING:%s\n' "$R3_SHADOW_ROOT" >&2
    exit 1
fi
if [[ ! -d "$R4_CANDIDATE_ROOT" ]]; then
    printf 'ERROR=R4_CANDIDATE_ROOT_MISSING:%s\n' "$R4_CANDIDATE_ROOT" >&2
    exit 1
fi

verify_r3_snapshot

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
REVIEW_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3c-a-review-shadow-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3c-a-review-contract-shadow-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$REVIEW_SHADOW_ROOT" ]]; then
    printf 'ERROR=REVIEW_SHADOW_ROOT_EXISTS:%s\n' "$REVIEW_SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$REVIEW_SHADOW_ROOT/scripts/lib" \
    "$REVIEW_SHADOW_ROOT/config" \
    "$REVIEW_SHADOW_ROOT/exchange/logs" \
    "$REVIEW_SHADOW_ROOT/review_requests" \
    "$EVIDENCE_ROOT/review-shadow-snapshot"

python3 - \
    "$REPO_ROOT" \
    "$R3_SHADOW_ROOT" \
    "$REVIEW_SHADOW_ROOT" \
    "$CANDIDATE_PATH" <<'PY'
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
source_shadow = Path(sys.argv[2]).resolve()
review_shadow = Path(sys.argv[3]).resolve()
candidate_path = Path(sys.argv[4]).resolve()

candidate_sha = __import__("hashlib").sha256(candidate_path.read_bytes()).hexdigest()
workflow_source = "app/db/repositories/workflow_state_repository.py"
workflow_sha = "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"

copy_relatives = [
    "scripts/__init__.py",
    "scripts/lib/__init__.py",
    "scripts/lib/secure_release_file_reader.py",
    "scripts/build_slack_worker_release_manifest_candidate.py",
    "scripts/validate_slack_worker_release_manifest_candidate.py",
    "scripts/build_slack_worker_release_rebinding_review_bundle.py",
    "scripts/validate_slack_worker_release_rebinding_review_bundle.py",
    "scripts/validate_slack_worker_release_bundle_contract.py",
]


def copy_exclusive(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"COPY_SOURCE_MISSING:{src}")
    if dst.exists() or os.path.lexists(dst):
        raise SystemExit(f"COPY_DESTINATION_EXISTS:{dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst, follow_symlinks=False)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def replace_once(text: str, old: str, new: str, code: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{code}:EXPECTED_ONE_FOUND_{count}")
    return text.replace(old, new, 1)


for relative in copy_relatives:
    copy_exclusive(source_shadow / relative, review_shadow / relative)

for source in sorted((source_shadow / "config").glob("slack_worker*.json")):
    copy_exclusive(source, review_shadow / "config" / source.name)

for relative in (
    "exchange/logs/sql_b2_4b_5g_3b_1d_2a_release_bundle_dry_run_result.json",
    "exchange/logs/sql_b2_4b_5g_3b_1d_2b_0_host_preinstall_discovery_result.json",
):
    copy_exclusive(source_shadow / relative, review_shadow / relative)
    (review_shadow / relative).chmod(0o444)

review_policy_path = (
    review_shadow / "config/slack_worker_release_rebinding_review_policy.json"
)
review_policy = load(review_policy_path)
review_policy["candidate_manifest_sha256"] = candidate_sha

source_contract = review_policy.get("source_contract")
if not isinstance(source_contract, dict):
    raise SystemExit("REVIEW_POLICY_SOURCE_CONTRACT_INVALID")
workflow_contract = source_contract.get(workflow_source)
if not isinstance(workflow_contract, dict):
    raise SystemExit("WORKFLOW_SOURCE_CONTRACT_MISSING")
workflow_contract["current_sha256"] = workflow_sha

found_workflow_unit = False
for unit in review_policy.get("review_units", []):
    if not isinstance(unit, dict):
        continue
    if unit.get("unit_id") == "UNIT_WORKFLOW_STATE":
        found_workflow_unit = True
        unit["candidate_change_role"] = (
            "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW"
        )
    else:
        unit["candidate_change_role"] = "CHANGED"
if not found_workflow_unit:
    raise SystemExit("WORKFLOW_REVIEW_UNIT_MISSING")

write_json(review_policy_path, review_policy)

review_builder_path = (
    review_shadow / "scripts/build_slack_worker_release_rebinding_review_bundle.py"
)
review_builder = review_builder_path.read_text(encoding="utf-8")
old_root = repr(str(source_shadow))
new_root = repr(str(review_shadow))
if old_root not in review_builder:
    raise SystemExit("REVIEW_BUILDER_SOURCE_SHADOW_ROOT_NOT_FOUND")
review_builder = review_builder.replace(old_root, new_root)

review_builder = replace_once(
    review_builder,
    '            "change_category": unit["change_category"],\n'
    '            "sources": sources,\n',
    '            "change_category": unit["change_category"],\n'
    '            "candidate_change_role": unit.get(\n'
    '                "candidate_change_role", "CHANGED"\n'
    '            ),\n'
    '            "sources": sources,\n',
    "REVIEW_PACKET_ROLE_INSERTION_POINT_NOT_FOUND",
)

review_builder = replace_once(
    review_builder,
    '    candidate = load_json_bytes(candidate_snapshot.data, "CANDIDATE_INVALID")\n'
    '    downstream = load_json_bytes(downstream_snapshot.data, "DOWNSTREAM_INVALID")\n'
    '    production_bytes = secure_repo_bytes(\n',
    '    candidate = load_json_bytes(candidate_snapshot.data, "CANDIDATE_INVALID")\n'
    '    downstream = load_json_bytes(downstream_snapshot.data, "DOWNSTREAM_INVALID")\n'
    '    candidate_audit = candidate.get("source_audit", [])\n'
    '    candidate_changed_sources = {\n'
    '        item.get("path")\n'
    '        for item in candidate_audit\n'
    '        if isinstance(item, dict)\n'
    '        and item.get("change") in {"MODIFIED", "ADDED"}\n'
    '    }\n'
    '    candidate_unchanged_sources = {\n'
    '        item.get("path")\n'
    '        for item in candidate_audit\n'
    '        if isinstance(item, dict) and item.get("change") == "UNCHANGED"\n'
    '    }\n'
    '    baseline_absorbed_sources = {\n'
    '        source\n'
    '        for unit in policy["review_units"]\n'
    '        if unit.get("candidate_change_role")\n'
    '        == "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW"\n'
    '        for source in unit["sources"]\n'
    '    }\n'
    '    review_sources = candidate_changed_sources | baseline_absorbed_sources\n'
    '    if candidate_changed_sources != {\n'
    '        "app/db/access_guard.py",\n'
    '        "app/db/config.py",\n'
    '        "app/db/session.py",\n'
    '        "scripts/run_slack_approval_socket.py",\n'
    '    }:\n'
    '        raise ReviewBundleBlocked("CANDIDATE_CHANGED_SOURCE_SET_INVALID")\n'
    '    if baseline_absorbed_sources != {\n'
    '        "app/db/repositories/workflow_state_repository.py"\n'
    '    }:\n'
    '        raise ReviewBundleBlocked("BASELINE_ABSORBED_SOURCE_SET_INVALID")\n'
    '    if not baseline_absorbed_sources.issubset(candidate_unchanged_sources):\n'
    '        raise ReviewBundleBlocked("BASELINE_ABSORPTION_CLASSIFICATION_INVALID")\n'
    '    production_bytes = secure_repo_bytes(\n',
    "REVIEW_BUILDER_CANDIDATE_ANALYSIS_INSERTION_POINT_NOT_FOUND",
)

review_builder = replace_once(
    review_builder,
    '    source_to_diff_path = {\n'
    '        relative: "source-diffs/" + relative.replace("/", "__") + ".diff.json"\n'
    '        for relative in diff_documents\n'
    '    }\n',
    '    if set(diff_documents) != review_sources:\n'
    '        raise ReviewBundleBlocked("REVIEW_SOURCE_DIFF_SET_INVALID")\n'
    '    source_to_diff_path = {\n'
    '        relative: "source-diffs/" + relative.replace("/", "__") + ".diff.json"\n'
    '        for relative in diff_documents\n'
    '    }\n',
    "REVIEW_BUILDER_DIFF_SET_INSERTION_POINT_NOT_FOUND",
)

review_builder = replace_once(
    review_builder,
    '        "review_unit_count": 3,\n'
    '        "review_unit_paths": packet_paths,\n',
    '        "review_unit_count": 3,\n'
    '        "candidate_changed_source_count": len(candidate_changed_sources),\n'
    '        "baseline_absorbed_source_count": len(baseline_absorbed_sources),\n'
    '        "human_review_source_count": len(review_sources),\n'
    '        "review_unit_paths": packet_paths,\n',
    "REVIEW_MANIFEST_COUNT_INSERTION_POINT_NOT_FOUND",
)

review_builder_path.write_text(review_builder, encoding="utf-8")

review_validator_path = (
    review_shadow / "scripts/validate_slack_worker_release_rebinding_review_bundle.py"
)
review_validator = review_validator_path.read_text(encoding="utf-8")
if old_root not in review_validator:
    raise SystemExit("REVIEW_VALIDATOR_SOURCE_SHADOW_ROOT_NOT_FOUND")
review_validator = review_validator.replace(old_root, new_root)

review_validator = replace_once(
    review_validator,
    'INTEGRITY_ERROR = "SLACK_WORKER_RELEASE_REVIEW_BUNDLE_INTEGRITY_FAILED"\n',
    'INTEGRITY_ERROR = "SLACK_WORKER_RELEASE_REVIEW_BUNDLE_INTEGRITY_FAILED"\n'
    'EXPECTED_CANDIDATE_CHANGED_SOURCES = {\n'
    '    "app/db/access_guard.py",\n'
    '    "app/db/config.py",\n'
    '    "app/db/session.py",\n'
    '    "scripts/run_slack_approval_socket.py",\n'
    '}\n'
    'EXPECTED_BASELINE_ABSORBED_SOURCES = {\n'
    '    "app/db/repositories/workflow_state_repository.py",\n'
    '}\n'
    'EXPECTED_REVIEW_SOURCES = (\n'
    '    EXPECTED_CANDIDATE_CHANGED_SOURCES\n'
    '    | EXPECTED_BASELINE_ABSORBED_SOURCES\n'
    ')\n'
    'EXPECTED_UNIT_ROLE = {\n'
    '    "UNIT_DB_SAFETY": "CHANGED",\n'
    '    "UNIT_WORKFLOW_STATE": (\n'
    '        "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW"\n'
    '    ),\n'
    '    "UNIT_SLACK_RUNTIME": "CHANGED",\n'
    '}\n',
    "REVIEW_VALIDATOR_CONSTANT_INSERTION_POINT_NOT_FOUND",
)

review_validator = replace_once(
    review_validator,
    '    unit_paths = manifest.get("review_unit_paths")\n',
    '    if changed_sources != EXPECTED_CANDIDATE_CHANGED_SOURCES:\n'
    '        fail("CANDIDATE_CHANGED_SOURCE_SET_INVALID")\n'
    '    if (\n'
    '        unchanged_sources & EXPECTED_REVIEW_SOURCES\n'
    '    ) != EXPECTED_BASELINE_ABSORBED_SOURCES:\n'
    '        fail("CANDIDATE_BASELINE_ABSORPTION_INVALID")\n'
    '    if manifest.get("candidate_changed_source_count") != 4:\n'
    '        fail("CANDIDATE_CHANGED_SOURCE_COUNT_INVALID")\n'
    '    if manifest.get("baseline_absorbed_source_count") != 1:\n'
    '        fail("BASELINE_ABSORBED_SOURCE_COUNT_INVALID")\n'
    '    if manifest.get("human_review_source_count") != 5:\n'
    '        fail("HUMAN_REVIEW_SOURCE_COUNT_INVALID")\n'
    '    unit_paths = manifest.get("review_unit_paths")\n',
    "REVIEW_VALIDATOR_CANDIDATE_SET_INSERTION_POINT_NOT_FOUND",
)

review_validator = replace_once(
    review_validator,
    '          if packet.get("unit_id") != unit_id:\n'
    '              fail("REVIEW_UNIT_ID_MISMATCH")\n',
    '          if packet.get("unit_id") != unit_id:\n'
    '              fail("REVIEW_UNIT_ID_MISMATCH")\n'
    '          if packet.get("candidate_change_role") != EXPECTED_UNIT_ROLE[unit_id]:\n'
    '              fail("REVIEW_UNIT_CHANGE_ROLE_INVALID")\n',
    "REVIEW_VALIDATOR_PACKET_ROLE_INSERTION_POINT_NOT_FOUND",
)

review_validator = replace_once(
    review_validator,
    '    if len(assigned) != len(set(assigned)):\n'
    '        fail("REVIEW_SOURCE_DUPLICATE")\n'
    '    if set(assigned) != changed_sources or set(assigned) & unchanged_sources:\n'
    '        fail("REVIEW_SOURCE_COVERAGE_INVALID")\n',
    '    if len(assigned) != len(set(assigned)):\n'
    '        fail("REVIEW_SOURCE_DUPLICATE")\n'
    '    assigned_set = set(assigned)\n'
    '    if assigned_set != EXPECTED_REVIEW_SOURCES:\n'
    '        fail("REVIEW_SOURCE_COVERAGE_INVALID")\n'
    '    if (\n'
    '        assigned_set & unchanged_sources\n'
    '    ) != EXPECTED_BASELINE_ABSORBED_SOURCES:\n'
    '        fail("REVIEW_BASELINE_ABSORBED_COVERAGE_INVALID")\n',
    "REVIEW_VALIDATOR_COVERAGE_BLOCK_NOT_FOUND",
)

review_validator = replace_once(
    review_validator,
    '    if not isinstance(diff_paths, dict) or set(diff_paths) != changed_sources:\n'
    '        fail("DIFF_SET_INVALID")\n',
    '    if (\n'
    '        not isinstance(diff_paths, dict)\n'
    '        or set(diff_paths) != EXPECTED_REVIEW_SOURCES\n'
    '    ):\n'
    '        fail("DIFF_SET_INVALID")\n',
    "REVIEW_VALIDATOR_DIFF_SET_BLOCK_NOT_FOUND",
)

review_validator = replace_once(
    review_validator,
    '        "source_diff_count": 5,\n'
    '        "source_diff_provenance_verified": True,\n',
    '        "source_diff_count": 5,\n'
    '        "candidate_changed_source_count": 4,\n'
    '        "baseline_absorbed_source_count": 1,\n'
    '        "human_review_source_count": 5,\n'
    '        "source_diff_provenance_verified": True,\n',
    "REVIEW_VALIDATOR_RESULT_COUNT_INSERTION_POINT_NOT_FOUND",
)

review_validator_path.write_text(review_validator, encoding="utf-8")
PY

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$REVIEW_SHADOW_ROOT" \
python3 -m py_compile \
    "$REVIEW_SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$REVIEW_SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$REVIEW_SHADOW_ROOT/scripts/lib/secure_release_file_reader.py"

while IFS= read -r file; do
    python3 -m json.tool "$file" >/dev/null
done < <(
    find "$REVIEW_SHADOW_ROOT/config" -maxdepth 1 -type f -name 'slack_worker*.json' \
        | LC_ALL=C sort
)

STATIC_RESULT="${EVIDENCE_ROOT}/review-contract-static-validation.json"
STATIC_TEXT="${EVIDENCE_ROOT}/review-contract-static-validation.txt"
APPROVAL_RECORD="${EVIDENCE_ROOT}/human-approval-shadow-contract-implementation-only.json"

cat > "$APPROVAL_RECORD" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3C-A",
  "approval_text": "APPROVE_SHADOW_CONTRACT_IMPLEMENTATION_ONLY",
  "approval_scope": {
    "shadow_contract_implementation": true,
    "shadow_candidate_preparation": true,
    "shadow_review_bundle_preparation": true,
    "production_manifest_update": false,
    "production_database_access": false,
    "production_migration": false,
    "deployment": false,
    "wordpress_network": false,
    "x_network": false,
    "slack_network": false,
    "slack_worker_start": false,
    "automatic_approval": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION"
}
JSON

(
    cd "$REVIEW_SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$REVIEW_SHADOW_ROOT" \
    python3 - \
        "$REPO_ROOT" \
        "$R3_SHADOW_ROOT" \
        "$REVIEW_SHADOW_ROOT" \
        "$CANDIDATE_PATH" \
        "$STATIC_RESULT" \
        "$STATIC_TEXT" <<'PY'
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
r3_shadow = Path(sys.argv[2]).resolve()
review_shadow = Path(sys.argv[3]).resolve()
candidate_path = Path(sys.argv[4]).resolve()
result_path = Path(sys.argv[5])
text_path = Path(sys.argv[6])

for module_name in list(sys.modules):
    if module_name == "scripts" or module_name.startswith("scripts."):
        del sys.modules[module_name]

candidate_builder = importlib.import_module(
    "scripts.build_slack_worker_release_manifest_candidate"
)
candidate_validator = importlib.import_module(
    "scripts.validate_slack_worker_release_manifest_candidate"
)
review_builder = importlib.import_module(
    "scripts.build_slack_worker_release_rebinding_review_bundle"
)
review_validator = importlib.import_module(
    "scripts.validate_slack_worker_release_rebinding_review_bundle"
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


candidate = load(candidate_path)
policy = load(review_builder.POLICY_PATH)
workflow = "app/db/repositories/workflow_state_repository.py"

validator_contract = candidate.get("validator_contract", {}).get("files", [])
candidate_tool_sha_checks = {
    item["path"]: (
        item.get("sha256") == sha(review_shadow / item["path"])
    )
    for item in validator_contract
    if isinstance(item, dict)
    and isinstance(item.get("path"), str)
    and (review_shadow / item["path"]).is_file()
}

workflow_units = [
    unit
    for unit in policy.get("review_units", [])
    if isinstance(unit, dict) and unit.get("unit_id") == "UNIT_WORKFLOW_STATE"
]

checks = {
    "review_policy_is_derived_shadow": review_builder.POLICY_PATH
    == review_shadow / "config/slack_worker_release_rebinding_review_policy.json",
    "review_output_root_is_derived_shadow": review_builder.REVIEW_REQUEST_ROOT
    == review_shadow / "review_requests",
    "review_builder_shadow_root_is_derived": review_builder.SHADOW_ROOT
    == review_shadow,
    "candidate_builder_deterministic_anchor_is_r3": candidate_builder.SHADOW_ROOT
    == r3_shadow,
    "candidate_validator_repo_root_is_production": candidate_validator.REPO_ROOT
    == repo,
    "candidate_sha_binding_is_r4": policy.get("candidate_manifest_sha256")
    == sha(candidate_path),
    "production_manifest_binding_remains_production": policy.get(
        "production_manifest", {}
    ).get("sha256")
    == "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d",
    "workflow_source_contract_is_fix1": policy.get("source_contract", {}).get(
        workflow, {}
    ).get("current_sha256")
    == "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "workflow_review_unit_unique": len(workflow_units) == 1,
    "workflow_role_is_baseline_absorbed": bool(workflow_units)
    and workflow_units[0].get("candidate_change_role")
    == "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW",
    "review_validator_changed_set_is_four": review_validator.EXPECTED_CANDIDATE_CHANGED_SOURCES
    == {
        "app/db/access_guard.py",
        "app/db/config.py",
        "app/db/session.py",
        "scripts/run_slack_approval_socket.py",
    },
    "review_validator_absorbed_set_is_workflow": review_validator.EXPECTED_BASELINE_ABSORBED_SOURCES
    == {workflow},
    "review_validator_review_set_is_five": len(
        review_validator.EXPECTED_REVIEW_SOURCES
    )
    == 5,
    "candidate_validator_contract_still_matches": bool(candidate_tool_sha_checks)
    and all(candidate_tool_sha_checks.values()),
}

failed = sorted(name for name, passed in checks.items() if not passed)

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3C-A",
    "result": (
        "PASS_REVIEW_CONTRACT_SHADOW_STATIC_VALIDATION"
        if not failed
        else "FAIL_REVIEW_CONTRACT_SHADOW_STATIC_VALIDATION"
    ),
    "roots": {
        "production_repo_root": str(repo),
        "r3_candidate_deterministic_anchor": str(r3_shadow),
        "review_shadow_root": str(review_shadow),
    },
    "candidate": {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_manifest_sha256": sha(candidate_path),
    },
    "contract": {
        "candidate_changed_source_count": 4,
        "baseline_absorbed_source_count": 1,
        "human_review_source_count": 5,
        "review_unit_count": 3,
        "source_diff_count": 5,
    },
    "candidate_tool_sha_checks": candidate_tool_sha_checks,
    "checks": checks,
    "failed_checks": failed,
    "execution": {
        "review_bundle_generation_performed": False,
        "review_bundle_validation_performed": False,
        "pytest_executed": False,
    },
    "safety": {
        "production_files_written": False,
        "production_database_accessed": False,
        "migration_applied": False,
        "deployment_performed": False,
        "external_network_used": False,
    },
}

result_path.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

lines = [
    f"RESULT={result['result']}",
    f"REVIEW_SHADOW_ROOT={review_shadow}",
    f"CANDIDATE_ID={candidate.get('candidate_id')}",
    f"CANDIDATE_MANIFEST_SHA={sha(candidate_path)}",
    "CANDIDATE_CHANGED_SOURCE_COUNT=4",
    "BASELINE_ABSORBED_SOURCE_COUNT=1",
    "HUMAN_REVIEW_SOURCE_COUNT=5",
    "REVIEW_UNIT_COUNT=3",
    "SOURCE_DIFF_COUNT=5",
    f"CANDIDATE_TOOL_SHA_MATCH={str(all(candidate_tool_sha_checks.values())).lower()}",
    "REVIEW_BUNDLE_GENERATION_PERFORMED=false",
    "REVIEW_BUNDLE_VALIDATION_PERFORMED=false",
    "PYTEST_EXECUTED=false",
]
text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

if failed:
    raise SystemExit(
        "REVIEW_CONTRACT_STATIC_VALIDATION_FAILED:" + ",".join(failed)
    )
PY
)

cat "$STATIC_TEXT"

(
    cd "$REVIEW_SHADOW_ROOT"
    while IFS= read -r file; do
        destination="${EVIDENCE_ROOT}/review-shadow-snapshot/${file}"
        mkdir -p "$(dirname "$destination")"
        cp --preserve=mode,timestamps "$file" "$destination"
    done < <(
        find scripts config exchange -type f \
            ! -path '*/__pycache__/*' \
            ! -name '*.pyc' \
            | LC_ALL=C sort
    )
)

SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/review-shadow-snapshot-manifest.txt"
(
    cd "$EVIDENCE_ROOT/review-shadow-snapshot"
    find . -type f -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$SNAPSHOT_MANIFEST"

STATIC_SHA="$(sha256_file "$STATIC_RESULT")"
STATIC_TEXT_SHA="$(sha256_file "$STATIC_TEXT")"
APPROVAL_SHA="$(sha256_file "$APPROVAL_RECORD")"
SNAPSHOT_MANIFEST_SHA="$(sha256_file "$SNAPSHOT_MANIFEST")"

verify_r3_snapshot

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
R3_SHADOW_MANIFEST_AFTER="$(sha256_file "$R3_SHADOW_MANIFEST")"
CANDIDATE_AFTER="$(sha256_file "$CANDIDATE_PATH")"
CLOSURE_AFTER="$(sha256_file "$CLOSURE_PATH")"
DOWNSTREAM_AFTER="$(sha256_file "$DOWNSTREAM_PATH")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$R3_SHADOW_MANIFEST_AFTER" == "$EXPECTED_R3_SHADOW_MANIFEST_SHA" ]] || {
    printf 'ERROR=R3_SHADOW_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$CANDIDATE_AFTER" == "$EXPECTED_CANDIDATE_SHA" ]] || {
    printf 'ERROR=R4_CANDIDATE_CHANGED\n' >&2
    exit 1
}
[[ "$CLOSURE_AFTER" == "$EXPECTED_CLOSURE_SHA" ]] || {
    printf 'ERROR=R4_CLOSURE_CHANGED\n' >&2
    exit 1
}
[[ "$DOWNSTREAM_AFTER" == "$EXPECTED_DOWNSTREAM_SHA" ]] || {
    printf 'ERROR=R4_DOWNSTREAM_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3C-A",
  "result": "PASS_W2B_I2F3C_A_REVIEW_CONTRACT_SHADOW_READY",
  "approval_scope": "APPROVE_SHADOW_CONTRACT_IMPLEMENTATION_ONLY",
  "review_shadow_root": "${REVIEW_SHADOW_ROOT}",
  "r3_candidate_deterministic_anchor": "${R3_SHADOW_ROOT}",
  "r4_candidate_root": "${R4_CANDIDATE_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "contract": {
    "candidate_changed_source_count": 4,
    "baseline_absorbed_source_count": 1,
    "human_review_source_count": 5,
    "review_unit_count": 3,
    "source_diff_count": 5
  },
  "validation": {
    "python_compile_passed": true,
    "json_validation_passed": true,
    "static_validation_sha256": "${STATIC_SHA}",
    "static_validation_text_sha256": "${STATIC_TEXT_SHA}",
    "approval_record_sha256": "${APPROVAL_SHA}",
    "review_shadow_snapshot_manifest_sha256": "${SNAPSHOT_MANIFEST_SHA}"
  },
  "execution": {
    "review_bundle_generation_performed": false,
    "review_bundle_validation_performed": false,
    "pytest_executed": false
  },
  "safety": {
    "production_source_changed": false,
    "production_manifest_changed": false,
    "r3_shadow_changed": false,
    "r4_candidate_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "next_phase": "TST-5D-W2B-I2F-3C-B_SHADOW_REVIEW_BUNDLE_GENERATION_AND_VALIDATION",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3C_A_REVIEW_CONTRACT_SHADOW_READY\n'
printf 'REVIEW_SHADOW_ROOT=%s\n' "$REVIEW_SHADOW_ROOT"
printf 'R3_CANDIDATE_DETERMINISTIC_ANCHOR=%s\n' "$R3_SHADOW_ROOT"
printf 'R4_CANDIDATE_ROOT=%s\n' "$R4_CANDIDATE_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'STATIC_VALIDATION_SHA=%s\n' "$STATIC_SHA"
printf 'APPROVAL_RECORD_SHA=%s\n' "$APPROVAL_SHA"
printf 'SNAPSHOT_MANIFEST_SHA=%s\n' "$SNAPSHOT_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'CANDIDATE_CHANGED_SOURCE_COUNT=4\n'
printf 'BASELINE_ABSORBED_SOURCE_COUNT=1\n'
printf 'HUMAN_REVIEW_SOURCE_COUNT=5\n'
printf 'REVIEW_UNIT_COUNT=3\n'
printf 'SOURCE_DIFF_COUNT=5\n'
printf 'PYTHON_COMPILE_PASSED=true\n'
printf 'JSON_VALIDATION_PASSED=true\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=false\n'
printf 'REVIEW_BUNDLE_VALIDATION_PERFORMED=false\n'
printf 'PYTEST_EXECUTED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'R3_SHADOW_CHANGED=false\n'
printf 'R4_CANDIDATE_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3C-B_SHADOW_REVIEW_BUNDLE_GENERATION_AND_VALIDATION\n'
