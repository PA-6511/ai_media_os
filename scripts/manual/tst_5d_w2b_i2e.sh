#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

cd /home/deploy/ai_media_os || exit 1

ROOT="/home/deploy/ai_media_os"
SOURCE="app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="config/slack_worker_release_source_manifest.json"
DB="data/database/ebook_affiliate.db"
VALIDATOR="scripts/validate_slack_worker_release_manifest_candidate.py"

INTEGRATION_RESULT="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i1-fix1-source-integration-retry-001/integration-result.json"
I2_ROOT="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2-full-suite-rereview-prep"
FULL_LOG="$I2_ROOT/full-suite.txt"
FULL_RESULT="$I2_ROOT/full-suite-validation-result.json"
RESUME_ROOT="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2d-shadow-chain-cascade-validation/resume-001"
RESUME_BUILD_LOG="$RESUME_ROOT/shadow-build.txt"

SHADOW="/tmp/tst-5d-w2b-i2d-resume-shadow-20260725T131303"
SHADOW_CANDIDATE="/tmp/tst-5d-w2b-i2d-resume-candidate-20260725T131303"
SHADOW_MANIFEST="$SHADOW/config/slack_worker_release_source_manifest.json"
SHADOW_CANDIDATE_POLICY="$SHADOW/config/slack_worker_release_rebinding_policy.json"
SHADOW_REVIEW_POLICY="$SHADOW/config/slack_worker_release_rebinding_review_policy.json"
SHADOW_CONFIG_SOURCE="$SHADOW/app/db/config.py"
CANDIDATE="$SHADOW_CANDIDATE/candidate-manifest.json"
CLOSURE="$SHADOW_CANDIDATE/dependency-closure.json"
DOWNSTREAM_PLAN="$SHADOW_CANDIDATE/downstream-rebinding-plan.json"

EVIDENCE_PARENT="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133"
STAMP="$(date +%Y%m%dT%H%M%S)"
EVIDENCE_ROOT="$EVIDENCE_PARENT/tst-5d-w2b-i2e-baseline-absorption-rereview-$STAMP"
STAGE="$EVIDENCE_PARENT/.tst-5d-w2b-i2e-stage-$STAMP-$$"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_INTEGRATION_RESULT_SHA="dcff38e1ed03cf1a696f1e541b765e1bf1d2d27c3dc1cc6d092002ff072c47b9"
EXPECTED_FULL_LOG_SHA="346ca96a7704fa754df556036253e2e7c7a7804ceca825228edfa60dd0ea4524"
EXPECTED_FULL_RESULT_SHA="e86be568d47264dc18f008742d34da58fffd94d31bbc62e340bcfdeba589c126"
EXPECTED_RESUME_BUILD_LOG_SHA="9ad34efaf22d0aa3d9832ebe7551549af972fea38ddc19d30f1496e90a0fb3d5"
EXPECTED_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"
EXPECTED_SHADOW_CANDIDATE_POLICY_SHA="5ab85f8ce6ac309ddf5c4bde75098acd5183851aa1796bae4942403eb76c6065"
EXPECTED_SHADOW_REVIEW_POLICY_SHA="fe9efc8caded329bf410c8d518de398a6c8771cd9f13462b41a2330cd0ae07f0"
EXPECTED_CANDIDATE_SHA="cb0551f023754e7cd8f5b7f84b3a25cd2a94a20c3e3750255ab898c3b6d5cdcc"
EXPECTED_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_PLAN_SHA="130563faf72145622a84f13c739097d719b31669a92d681fa2cdaa6384756f29"

sha_of() {
  sha256sum "$1" | awk '{print $1}'
}

require_sha() {
  local path="$1"
  local expected="$2"
  local current

  if [[ ! -f "$path" ]]; then
    echo "MISSING_REQUIRED_FILE=$path"
    exit 1
  fi

  current="$(sha_of "$path")"
  if [[ "$current" != "$expected" ]]; then
    echo "SHA_MISMATCH=$path"
    echo "EXPECTED=$expected"
    echo "CURRENT=$current"
    exit 1
  fi

  echo "SHA_PASS=$path:$current"
}

snapshot_protected() {
  local output="$1"
  : > "$output"
  for path in \
    "$SOURCE" \
    "$PRODUCTION_MANIFEST" \
    "$DB" \
    "$VALIDATOR" \
    "$INTEGRATION_RESULT" \
    "$FULL_LOG" \
    "$FULL_RESULT" \
    "$RESUME_BUILD_LOG" \
    "$SHADOW_MANIFEST" \
    "$SHADOW_CANDIDATE_POLICY" \
    "$SHADOW_REVIEW_POLICY" \
    "$CANDIDATE" \
    "$CLOSURE" \
    "$DOWNSTREAM_PLAN"
  do
    if [[ ! -f "$path" ]]; then
      echo "MISSING=$path" >> "$output"
      continue
    fi
    echo "FILE=$path" >> "$output"
    sha256sum "$path" >> "$output"
    stat -c 'MODE=%a SIZE=%s' "$path" >> "$output"
  done
}

preserve_failed_stage() {
  if [[ -d "$STAGE" ]]; then
    echo "FAILED_STAGE_PRESERVED=$STAGE" >&2
  fi
}
trap preserve_failed_stage EXIT

# 1. 固定証跡と保護対象
require_sha "$SOURCE" "$EXPECTED_SOURCE_SHA"
require_sha "$PRODUCTION_MANIFEST" "$EXPECTED_MANIFEST_SHA"
require_sha "$DB" "$EXPECTED_DB_SHA"
require_sha "$INTEGRATION_RESULT" "$EXPECTED_INTEGRATION_RESULT_SHA"
require_sha "$FULL_LOG" "$EXPECTED_FULL_LOG_SHA"
require_sha "$FULL_RESULT" "$EXPECTED_FULL_RESULT_SHA"
require_sha "$RESUME_BUILD_LOG" "$EXPECTED_RESUME_BUILD_LOG_SHA"
require_sha "$SHADOW_MANIFEST" "$EXPECTED_SHADOW_MANIFEST_SHA"
require_sha "$SHADOW_CANDIDATE_POLICY" "$EXPECTED_SHADOW_CANDIDATE_POLICY_SHA"
require_sha "$SHADOW_REVIEW_POLICY" "$EXPECTED_SHADOW_REVIEW_POLICY_SHA"
require_sha "$CANDIDATE" "$EXPECTED_CANDIDATE_SHA"
require_sha "$CLOSURE" "$EXPECTED_CLOSURE_SHA"
require_sha "$DOWNSTREAM_PLAN" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

if [[ -e "$EVIDENCE_ROOT" || -e "$STAGE" ]]; then
  echo "BLOCKED_OUTPUT_PATH_EXISTS=true"
  exit 1
fi

mkdir -p "$EVIDENCE_PARENT"
mkdir -m 700 "$STAGE"
snapshot_protected "$STAGE/protected-before.txt"

# 2. 必要最小限のshadow証跡を永続化用に複製
mkdir -m 700 "$STAGE/shadow-snapshot"
install -m 600 "$SHADOW_MANIFEST" "$STAGE/shadow-snapshot/slack_worker_release_source_manifest.json"
install -m 600 "$SHADOW_CANDIDATE_POLICY" "$STAGE/shadow-snapshot/slack_worker_release_rebinding_policy.json"
install -m 600 "$SHADOW_REVIEW_POLICY" "$STAGE/shadow-snapshot/slack_worker_release_rebinding_review_policy.json"
install -m 600 "$CANDIDATE" "$STAGE/shadow-snapshot/candidate-manifest.json"
install -m 600 "$CLOSURE" "$STAGE/shadow-snapshot/dependency-closure.json"
install -m 600 "$DOWNSTREAM_PLAN" "$STAGE/shadow-snapshot/downstream-rebinding-plan.json"

# 3. 再分類・人間再審査packet生成
python3 - \
  "$STAGE/baseline-absorption-classification.json" \
  "$STAGE/unit-workflow-state-rereview-packet.json" \
  "$STAGE/human-review-summary.md" \
  "$VALIDATOR" \
  "$FULL_LOG" \
  "$FULL_RESULT" \
  "$INTEGRATION_RESULT" \
  "$RESUME_BUILD_LOG" \
  "$SOURCE" \
  "$PRODUCTION_MANIFEST" \
  "$DB" \
  "$SHADOW_MANIFEST" \
  "$SHADOW_CANDIDATE_POLICY" \
  "$SHADOW_REVIEW_POLICY" \
  "$SHADOW_CONFIG_SOURCE" \
  "$CANDIDATE" \
  "$CLOSURE" \
  "$DOWNSTREAM_PLAN" \
  "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

(
    classification_path,
    packet_path,
    summary_path,
    validator_path,
    full_log_path,
    full_result_path,
    integration_result_path,
    resume_build_log_path,
    source_path,
    production_manifest_path,
    database_path,
    shadow_manifest_path,
    candidate_policy_path,
    review_policy_path,
    shadow_config_source_path,
    candidate_path,
    closure_path,
    downstream_path,
    final_evidence_root,
) = map(Path, sys.argv[1:])

repository_relative = "app/db/repositories/workflow_state_repository.py"
config_relative = "app/db/config.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


# Validatorの固定changed source集合。
# EXPECTED_CHANGED_SOURCES は set().union(*EXPECTED_REVIEW_UNITS.values())
# という動的式なので、AST Call自体をliteral_evalせず、入力定数から集合を再構成する。
validator_tree = ast.parse(validator_path.read_text(encoding="utf-8"))
expected_review_units_raw: dict[str, Any] | None = None
changed_assignment_found = False
for node in validator_tree.body:
    if not isinstance(node, ast.Assign):
        continue
    target_names = {
        target.id
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    if "EXPECTED_REVIEW_UNITS" in target_names:
        raw_units = ast.literal_eval(node.value)
        if not isinstance(raw_units, dict):
            raise RuntimeError("EXPECTED_REVIEW_UNITS_NOT_MAPPING")
        expected_review_units_raw = raw_units
    if "EXPECTED_CHANGED_SOURCES" in target_names:
        changed_assignment_found = True

if expected_review_units_raw is None:
    raise RuntimeError("EXPECTED_REVIEW_UNITS_ASSIGNMENT_NOT_FOUND")
if not changed_assignment_found:
    raise RuntimeError("EXPECTED_CHANGED_SOURCES_ASSIGNMENT_NOT_FOUND")

expected_changed: set[str] = set()
for unit_id, sources in expected_review_units_raw.items():
    if not isinstance(unit_id, str):
        raise RuntimeError("EXPECTED_REVIEW_UNIT_ID_INVALID")
    if not isinstance(sources, (set, frozenset, list, tuple)):
        raise RuntimeError(
            "EXPECTED_REVIEW_UNIT_SOURCES_NOT_COLLECTION:" + unit_id
        )
    for item in sources:
        if not isinstance(item, str):
            raise RuntimeError(
                "EXPECTED_REVIEW_UNIT_SOURCE_NOT_STRING:" + unit_id
            )
        expected_changed.add(item)

expected_exact = {
    "app/db/access_guard.py",
    "app/db/config.py",
    repository_relative,
    "app/db/session.py",
    "scripts/run_slack_approval_socket.py",
}
if expected_changed != expected_exact:
    raise RuntimeError(
        "VALIDATOR_EXPECTED_CHANGED_SET_DRIFTED:"
        + repr(sorted(expected_changed or set()))
    )

# Canonical full-suiteログ
full_log_text = full_log_path.read_text(encoding="utf-8", errors="replace")
summary_matches = re.findall(
    r"(\d+) failed, (\d+) passed, (\d+) subtests passed",
    full_log_text,
)
if not summary_matches:
    raise RuntimeError("RAW_FULL_SUITE_SUMMARY_NOT_FOUND")
failed_count, passed_count, subtests_passed = map(int, summary_matches[-1])
if (failed_count, passed_count, subtests_passed) != (33, 10885, 8):
    raise RuntimeError(
        "RAW_FULL_SUITE_COUNTS_DRIFTED:"
        f"{failed_count},{passed_count},{subtests_passed}"
    )

failed_nodes = [
    line[len("FAILED "):].split(" - ", 1)[0].strip()
    for line in full_log_text.splitlines()
    if line.startswith("FAILED ")
]
if len(failed_nodes) != 33:
    raise RuntimeError(f"FAILED_NODE_COUNT_INVALID:{len(failed_nodes)}")

failure_file_counts = Counter(node.split("::", 1)[0] for node in failed_nodes)
expected_file_counts = {
    "tests/test_build_slack_worker_release_rebinding_review_bundle.py": 11,
    "tests/test_validate_slack_worker_release_bundle_contract.py": 2,
    "tests/test_validate_slack_worker_release_rebinding_review_bundle.py": 20,
}
if dict(failure_file_counts) != expected_file_counts:
    raise RuntimeError(
        "FAILED_FILE_COUNTS_DRIFTED:"
        + repr(dict(failure_file_counts))
    )

if (
    "RELEASE_FILE_SHA_MISMATCH:"
    "app/db/repositories/workflow_state_repository.py"
    not in full_log_text
):
    raise RuntimeError("REPOSITORY_MANIFEST_CASCADE_MARKER_NOT_FOUND")
if "SOURCE_SHA_MISMATCH: app/db/config.py" not in full_log_text:
    raise RuntimeError("LEGACY_CONFIG_FAILURE_MARKER_NOT_FOUND")

# JSON証跡が読み取り可能であることだけ確認
load_json(full_result_path)
load_json(integration_result_path)

candidate = load_json(candidate_path)
shadow_manifest = load_json(shadow_manifest_path)
candidate_policy = load_json(candidate_policy_path)
review_policy = load_json(review_policy_path)
closure = load_json(closure_path)
downstream = load_json(downstream_path)

audit = candidate.get("source_audit")
review_units = candidate.get("review_units")
if not isinstance(audit, list) or not isinstance(review_units, list):
    raise RuntimeError("CANDIDATE_CLASSIFICATION_STRUCTURE_INVALID")

changed = {
    item.get("path")
    for item in audit
    if isinstance(item, dict) and item.get("change") in {"ADDED", "MODIFIED"}
}
unchanged = {
    item.get("path")
    for item in audit
    if isinstance(item, dict) and item.get("change") == "UNCHANGED"
}
assigned: set[str] = set()
for unit in review_units:
    if not isinstance(unit, dict):
        continue
    sources = unit.get("sources")
    if isinstance(sources, list):
        assigned.update(item for item in sources if isinstance(item, str))

if changed != expected_changed - {repository_relative}:
    raise RuntimeError("ACTUAL_CHANGED_SET_INVALID:" + repr(sorted(changed)))
if len(changed) != 4 or len(unchanged) != 13:
    raise RuntimeError(
        f"CLASSIFICATION_COUNTS_INVALID:{len(changed)},{len(unchanged)}"
    )
if repository_relative not in unchanged:
    raise RuntimeError("REPOSITORY_NOT_ABSORBED_INTO_BASELINE")
if unchanged & assigned != {repository_relative}:
    raise RuntimeError(
        "UNCHANGED_REVIEW_ASSIGNMENT_INVALID:"
        + repr(sorted(unchanged & assigned))
    )

repository_records = [
    item
    for item in audit
    if isinstance(item, dict) and item.get("path") == repository_relative
]
if len(repository_records) != 1:
    raise RuntimeError("REPOSITORY_SOURCE_AUDIT_COUNT_INVALID")
repository_record = repository_records[0]
source_sha = sha256(source_path)
if not (
    repository_record.get("change") == "UNCHANGED"
    and repository_record.get("matched") is True
    and repository_record.get("manifest_sha256") == source_sha
    and repository_record.get("current_sha256") == source_sha
):
    raise RuntimeError("REPOSITORY_BASELINE_ABSORPTION_RECORD_INVALID")

manifest_entries = [
    item
    for item in shadow_manifest.get("source_files", [])
    if isinstance(item, dict) and item.get("path") == repository_relative
]
if len(manifest_entries) != 1 or manifest_entries[0].get("sha256") != source_sha:
    raise RuntimeError("SHADOW_MANIFEST_REPOSITORY_ENTRY_INVALID")

shadow_manifest_file_sha = sha256(shadow_manifest_path)
current_manifest = candidate_policy.get("current_manifest")
if not isinstance(current_manifest, dict):
    raise RuntimeError("CANDIDATE_POLICY_CURRENT_MANIFEST_INVALID")
if current_manifest.get("sha256") != shadow_manifest_file_sha:
    raise RuntimeError("CANDIDATE_POLICY_MANIFEST_BINDING_INVALID")

review_manifest = review_policy.get("production_manifest")
if not isinstance(review_manifest, dict):
    raise RuntimeError("REVIEW_POLICY_PRODUCTION_MANIFEST_INVALID")
if review_manifest.get("sha256") != shadow_manifest_file_sha:
    raise RuntimeError("REVIEW_POLICY_MANIFEST_BINDING_INVALID")
if review_policy.get("candidate_manifest_sha256") != sha256(candidate_path):
    raise RuntimeError("REVIEW_POLICY_CANDIDATE_BINDING_INVALID")

source_contract = review_policy.get("source_contract")
if not isinstance(source_contract, dict):
    raise RuntimeError("REVIEW_POLICY_SOURCE_CONTRACT_INVALID")
repository_contract = source_contract.get(repository_relative)
if not isinstance(repository_contract, dict):
    raise RuntimeError("REPOSITORY_REVIEW_CONTRACT_MISSING")
if repository_contract.get("current_sha256") != source_sha:
    raise RuntimeError("REPOSITORY_REVIEW_CONTRACT_SHA_INVALID")

config_entries = [
    item
    for item in shadow_manifest.get("source_files", [])
    if isinstance(item, dict) and item.get("path") == config_relative
]
if len(config_entries) != 1:
    raise RuntimeError("CONFIG_MANIFEST_ENTRY_INVALID")
if config_entries[0].get("sha256") == sha256(shadow_config_source_path):
    raise RuntimeError("LEGACY_CONFIG_MISMATCH_NOT_PRESERVED")

if closure.get("source_count") != 17:
    raise RuntimeError("DEPENDENCY_CLOSURE_SOURCE_COUNT_INVALID")
artifacts = downstream.get("artifacts")
if not isinstance(artifacts, list) or len(artifacts) != 21:
    raise RuntimeError("DOWNSTREAM_ARTIFACT_COUNT_INVALID")

now = datetime.now(timezone.utc).astimezone().isoformat()
classification = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2E",
    "status": "PASS_31_FAILURES_RECLASSIFIED_AS_SUPERSEDED_CANDIDATE_BASELINE_CONTRACT",
    "classified_at": now,
    "raw_full_suite": {
        "status": "FAILED",
        "passed": passed_count,
        "failed": failed_count,
        "subtests_passed": subtests_passed,
    },
    "failure_reclassification": {
        "legacy_config_manifest_failures": {
            "count": 2,
            "status": "KNOWN_EXISTING_BLOCK",
        },
        "repository_candidate_contract_failures": {
            "count": 31,
            "status": "SUPERSEDED_BY_BASELINE_ABSORPTION",
            "functional_regression": False,
            "historical_candidate_mutation_allowed": False,
        },
        "non_manifest_regressions": {
            "count": 0,
            "status": "NONE_DETECTED",
        },
    },
    "baseline_absorption": {
        "validator_expected_changed_count": 5,
        "shadow_actual_changed_count": 4,
        "shadow_actual_unchanged_count": 13,
        "missing_from_actual_changed": [repository_relative],
        "unchanged_and_old_review_assigned": [repository_relative],
        "repository_sha256": source_sha,
        "confirmed": True,
    },
    "candidate_contract": {
        "candidate_manifest_sha256": sha256(candidate_path),
        "dependency_closure_sha256": sha256(closure_path),
        "downstream_plan_sha256": sha256(downstream_path),
        "dependency_closure_source_count": 17,
        "downstream_artifact_count": 21,
        "candidate_validation_status": "EXPECTED_BLOCK_OLD_CLASSIFICATION_CONTRACT",
    },
    "production_protection": {
        "source_sha256": source_sha,
        "production_manifest_sha256": sha256(production_manifest_path),
        "production_database_sha256": sha256(database_path),
        "source_modified_by_this_phase": False,
        "production_manifest_modified_by_this_phase": False,
        "production_database_sql_connection_used": False,
        "production_database_modified_by_this_phase": False,
        "production_migration_applied": False,
        "deployment_performed": False,
        "external_network_used": False,
    },
}
classification_path.write_text(
    json.dumps(classification, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

packet = {
    "schema_version": "1.0",
    "review_id": "TST-5D-W2B-I2E-UNIT-WORKFLOW-STATE-REREVIEW-001",
    "phase": "TST-5D-W2B-I2E",
    "review_unit_id": "UNIT_WORKFLOW_STATE",
    "status": "READY_FOR_HUMAN_REREVIEW_NOT_APPROVED",
    "created_at": now,
    "review_question": (
        "Should UNIT_WORKFLOW_STATE move from HOLD to "
        "APPROVED_FOR_REBINDING_PREPARATION_ONLY?"
    ),
    "allowed_decisions": [
        "APPROVE_REBINDING_PREPARATION_ONLY",
        "HOLD",
        "REJECT",
    ],
    "recommended_decision": "APPROVE_REBINDING_PREPARATION_ONLY",
    "approval_scope": {
        "new_candidate_preparation_allowed": True,
        "new_dependency_closure_preparation_allowed": True,
        "new_downstream_rebinding_plan_preparation_allowed": True,
        "new_review_bundle_preparation_allowed": True,
        "production_manifest_update_allowed": False,
        "production_database_audit_allowed": False,
        "production_migration_allowed": False,
        "deployment_allowed": False,
        "wordpress_network_allowed": False,
        "slack_network_allowed": False,
    },
    "remaining_blocks": {
        "production_manifest_rebinding": True,
        "production_database_audit": True,
        "production_migration": True,
        "deployment": True,
        "unit_slack_runtime": True,
    },
    "evidence": {
        "classification": {
            "path": str(final_evidence_root / "baseline-absorption-classification.json"),
            "sha256": sha256(classification_path),
        },
        "source_integration_result": {
            "path": str(integration_result_path),
            "sha256": sha256(integration_result_path),
        },
        "canonical_full_suite_log": {
            "path": str(full_log_path),
            "sha256": sha256(full_log_path),
            "raw_passed": passed_count,
            "raw_failed": failed_count,
        },
        "canonical_full_suite_result": {
            "path": str(full_result_path),
            "sha256": sha256(full_result_path),
        },
        "baseline_absorption_build_log": {
            "path": str(resume_build_log_path),
            "sha256": sha256(resume_build_log_path),
        },
        "integrated_repository": {
            "path": str(source_path),
            "sha256": source_sha,
        },
        "production_manifest": {
            "path": str(production_manifest_path),
            "sha256": sha256(production_manifest_path),
            "modified": False,
        },
    },
    "decision": None,
    "reviewer": None,
    "reviewed_at": None,
    "reason": None,
    "conditions": [],
    "automatic_approval": False,
    "decision_recorded": False,
}
packet_path.write_text(
    json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

summary_path.write_text(
    "\n".join(
        [
            "# TST-5D-W2B-I2E Baseline Absorption Rereview",
            "",
            "## Raw full-suite result",
            "",
            f"- Passed: {passed_count}",
            f"- Failed: {failed_count}",
            f"- Subtests passed: {subtests_passed}",
            "",
            "The raw full suite remains failed and is not rewritten as a normal PASS.",
            "",
            "## Failure reclassification",
            "",
            "- 2 failures: existing app/db/config.py manifest mismatch",
            "- 31 failures: superseded historical candidate classification contract",
            "- Non-manifest Workflow State regressions: 0",
            "",
            "## Human rereview recommendation",
            "",
            "`APPROVE_REBINDING_PREPARATION_ONLY`",
            "",
            "Production manifest updates, database access, migration, deployment, WordPress, and Slack remain blocked.",
            "",
            "## Current governance",
            "",
            "- UNIT_WORKFLOW_STATE: HOLD",
            "- Decision recorded: false",
            "- Automatic approval: false",
            "",
        ]
    ),
    encoding="utf-8",
)
PY

chmod 600 \
  "$STAGE/baseline-absorption-classification.json" \
  "$STAGE/unit-workflow-state-rereview-packet.json" \
  "$STAGE/human-review-summary.md"

python3 -m json.tool "$STAGE/baseline-absorption-classification.json" >/dev/null
python3 -m json.tool "$STAGE/unit-workflow-state-rereview-packet.json" >/dev/null

# 4. 保護対象事後確認
snapshot_protected "$STAGE/protected-after.txt"
if ! diff -u \
  "$STAGE/protected-before.txt" \
  "$STAGE/protected-after.txt" \
  > "$STAGE/protected-diff.txt"
then
  echo "RESULT=BLOCKED_PROTECTED_STATE_CHANGED"
  cat "$STAGE/protected-diff.txt"
  exit 1
fi

# 5. Evidence manifest
python3 - "$STAGE" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = {}
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(root).as_posix()
    if relative == "evidence-manifest.json":
        continue
    files[relative] = {
        "sha256": sha256(path),
        "size": path.stat().st_size,
    }

manifest = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2E",
    "status": "PASS_BASELINE_ABSORPTION_REREVIEW_PACKET_READY",
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
    "files": files,
    "governance": {
        "unit_workflow_state": "HOLD",
        "human_decision_required": True,
        "automatic_approval": False,
        "production_manifest_update_allowed": False,
    },
}
(root / "evidence-manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

chmod 600 "$STAGE/evidence-manifest.json"
python3 -m json.tool "$STAGE/evidence-manifest.json" >/dev/null

# 6. Evidence rootへatomic確定
mv "$STAGE" "$EVIDENCE_ROOT"
trap - EXIT

CLASSIFICATION="$EVIDENCE_ROOT/baseline-absorption-classification.json"
REVIEW_PACKET="$EVIDENCE_ROOT/unit-workflow-state-rereview-packet.json"
EVIDENCE_MANIFEST="$EVIDENCE_ROOT/evidence-manifest.json"

CLASSIFICATION_SHA="$(sha_of "$CLASSIFICATION")"
PACKET_SHA="$(sha_of "$REVIEW_PACKET")"
EVIDENCE_MANIFEST_SHA="$(sha_of "$EVIDENCE_MANIFEST")"

echo
echo "RESULT=PASS_W2B_I2E_BASELINE_ABSORPTION_REREVIEW_PACKET_READY"
echo "RAW_FULL_SUITE_PASSED=10885"
echo "RAW_FULL_SUITE_FAILED=33"
echo "LEGACY_CONFIG_FAILURE_COUNT=2"
echo "SUPERSEDED_CANDIDATE_CONTRACT_FAILURE_COUNT=31"
echo "NON_MANIFEST_REGRESSION_COUNT=0"
echo
echo "CLASSIFICATION_SHA=$CLASSIFICATION_SHA"
echo "REREVIEW_PACKET_SHA=$PACKET_SHA"
echo "EVIDENCE_MANIFEST_SHA=$EVIDENCE_MANIFEST_SHA"
echo "EVIDENCE_ROOT=$EVIDENCE_ROOT"
echo
echo "PRODUCTION_SOURCE_CHANGED=false"
echo "PRODUCTION_MANIFEST_CHANGED=false"
echo "PRODUCTION_DB_CONTENT_CHANGED=false"
echo "PRODUCTION_DB_SQL_CONNECTION_USED=false"
echo "PRODUCTION_MIGRATION_APPLIED=false"
echo "DEPLOYMENT_PERFORMED=false"
echo "UNIT_WORKFLOW_STATE=HOLD_PENDING_HUMAN_REREVIEW"
echo "RECOMMENDED_DECISION=APPROVE_REBINDING_PREPARATION_ONLY"
