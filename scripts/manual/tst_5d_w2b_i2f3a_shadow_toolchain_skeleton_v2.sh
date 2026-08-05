#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
I2F0_ROOT_REL="${I2E_ROOT_REL}/approval-rebinding-preparation-only-20260725T142358-486003"
I2F2_ROOT_REL="${I2E_ROOT_REL}/i2f2-shadow-contract-design-20260725T144825-486854"

APPROVAL_PATH="${REPO_ROOT}/${I2F0_ROOT_REL}/human-approval.json"
I2F2_RESULT_PATH="${REPO_ROOT}/${I2F2_ROOT_REL}/result.json"
I2F2_DESIGN_PATH="${REPO_ROOT}/${I2F2_ROOT_REL}/shadow-contract-design.json"

EXPECTED_APPROVAL_SHA="a73ec08108e1add5e6aaeadd5f85e34798af237f18ced24b09bfeae2d3129026"
EXPECTED_I2F2_RESULT_SHA="2315a6e62b78c62aae09df9f8f38efeb87eb35fe272940837aff81a03a08ce72"
EXPECTED_I2F2_DESIGN_SHA="5726874a32b0bf791120fb1a84e315aab69ab28c2d33a24fdd99990cda866546"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
MANIFEST_PATH="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

SOURCE_SHADOW_MANIFEST="/tmp/tst-5d-w2b-i2d-resume-shadow-20260725T131303/config/slack_worker_release_source_manifest.json"
EXPECTED_SOURCE_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"

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

require_file_sha "$APPROVAL_PATH" "$EXPECTED_APPROVAL_SHA"
require_file_sha "$I2F2_RESULT_PATH" "$EXPECTED_I2F2_RESULT_SHA"
require_file_sha "$I2F2_DESIGN_PATH" "$EXPECTED_I2F2_DESIGN_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$MANIFEST_PATH" "$EXPECTED_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"
require_file_sha "$SOURCE_SHADOW_MANIFEST" "$EXPECTED_SOURCE_SHADOW_MANIFEST_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3a-shadow-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3a-shadow-toolchain-skeleton-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$SHADOW_ROOT" ]]; then
    printf 'ERROR=SHADOW_ROOT_ALREADY_EXISTS:%s\n' "$SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_ALREADY_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$SHADOW_ROOT/scripts/lib" \
    "$SHADOW_ROOT/config" \
    "$SHADOW_ROOT/review_requests" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/lib" \
    "$EVIDENCE_ROOT/shadow-snapshot/config"

copy_required() {
    local src="$1"
    local dst="$2"

    if [[ ! -f "$src" ]]; then
        printf 'ERROR=COPY_SOURCE_MISSING:%s\n' "$src" >&2
        exit 1
    fi
    if [[ -e "$dst" ]]; then
        printf 'ERROR=COPY_DESTINATION_EXISTS:%s\n' "$dst" >&2
        exit 1
    fi
    cp --preserve=mode,timestamps "$src" "$dst"
}

copy_required \
    "$REPO_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py"
copy_required \
    "$REPO_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py"
copy_required \
    "$REPO_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py"
copy_required \
    "$REPO_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py"
copy_required \
    "$REPO_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py"
copy_required \
    "$REPO_ROOT/scripts/lib/secure_release_file_reader.py" \
    "$SHADOW_ROOT/scripts/lib/secure_release_file_reader.py"

if [[ -f "$REPO_ROOT/scripts/__init__.py" ]]; then
    copy_required "$REPO_ROOT/scripts/__init__.py" "$SHADOW_ROOT/scripts/__init__.py"
else
    printf '' > "$SHADOW_ROOT/scripts/__init__.py"
fi

if [[ -f "$REPO_ROOT/scripts/lib/__init__.py" ]]; then
    copy_required "$REPO_ROOT/scripts/lib/__init__.py" "$SHADOW_ROOT/scripts/lib/__init__.py"
else
    printf '' > "$SHADOW_ROOT/scripts/lib/__init__.py"
fi

copy_required \
    "$REPO_ROOT/config/slack_worker_release_rebinding_policy.json" \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_policy.json"
copy_required \
    "$REPO_ROOT/config/slack_worker_release_rebinding_review_policy.json" \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_review_policy.json"
copy_required \
    "$SOURCE_SHADOW_MANIFEST" \
    "$SHADOW_ROOT/config/slack_worker_release_source_manifest.json"

python3 - "$REPO_ROOT" "$SHADOW_ROOT" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
shadow = Path(sys.argv[2]).resolve()

builder_path = shadow / "scripts/build_slack_worker_release_manifest_candidate.py"
validator_path = shadow / "scripts/validate_slack_worker_release_manifest_candidate.py"
review_builder_path = shadow / "scripts/build_slack_worker_release_rebinding_review_bundle.py"
review_validator_path = shadow / "scripts/validate_slack_worker_release_rebinding_review_bundle.py"

rebinding_policy_path = shadow / "config/slack_worker_release_rebinding_policy.json"
review_policy_path = shadow / "config/slack_worker_release_rebinding_review_policy.json"
shadow_manifest_path = shadow / "config/slack_worker_release_source_manifest.json"

workflow_source = "app/db/repositories/workflow_state_repository.py"
workflow_sha = "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
production_manifest_sha = "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"


def replace_once(text: str, old: str, new: str, code: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{code}:EXPECTED_ONE_FOUND_{count}")
    return text.replace(old, new, 1)


builder = builder_path.read_text(encoding="utf-8")
builder = replace_once(
    builder,
    'REPO_ROOT = Path(__file__).resolve().parents[1]\n'
    'POLICY_PATH = REPO_ROOT / "config/slack_worker_release_rebinding_policy.json"\n'
    'PRODUCTION_MANIFEST_PATH = (\n'
    '    REPO_ROOT / "config/slack_worker_release_source_manifest.json"\n'
    ')\n',
    f'REPO_ROOT = Path({str(repo)!r})\n'
    f'SHADOW_ROOT = Path({str(shadow)!r})\n'
    'POLICY_PATH = SHADOW_ROOT / "config/slack_worker_release_rebinding_policy.json"\n'
    'PRODUCTION_MANIFEST_PATH = (\n'
    '    SHADOW_ROOT / "config/slack_worker_release_source_manifest.json"\n'
    ')\n',
    "BUILDER_CONSTANT_BLOCK_NOT_FOUND",
)
builder = builder.replace(
    '"""Build a non-deployable Slack worker release rebinding candidate under /tmp.',
    '"""Build a non-deployable shadow Slack worker release rebinding candidate under /tmp.',
    1,
)
builder_path.write_text(builder, encoding="utf-8")

validator = validator_path.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    'REPO_ROOT = Path(__file__).resolve().parents[1]\n'
    'TMP_ROOT = Path("/tmp").resolve()\n'
    'EXPECTED_REVIEW_UNITS = {\n'
    '    "UNIT_DB_SAFETY": {\n'
    '        "app/db/access_guard.py",\n'
    '        "app/db/config.py",\n'
    '        "app/db/session.py",\n'
    '    },\n'
    '    "UNIT_WORKFLOW_STATE": {\n'
    '        "app/db/repositories/workflow_state_repository.py",\n'
    '    },\n'
    '    "UNIT_SLACK_RUNTIME": {"scripts/run_slack_approval_socket.py"},\n'
    '}\n'
    'EXPECTED_CHANGED_SOURCES = set().union(*EXPECTED_REVIEW_UNITS.values())\n',
    f'REPO_ROOT = Path({str(repo)!r})\n'
    'TMP_ROOT = Path("/tmp").resolve()\n'
    'EXPECTED_REVIEW_UNITS = {\n'
    '    "UNIT_DB_SAFETY": {\n'
    '        "app/db/access_guard.py",\n'
    '        "app/db/config.py",\n'
    '        "app/db/session.py",\n'
    '    },\n'
    '    "UNIT_WORKFLOW_STATE": {\n'
    '        "app/db/repositories/workflow_state_repository.py",\n'
    '    },\n'
    '    "UNIT_SLACK_RUNTIME": {"scripts/run_slack_approval_socket.py"},\n'
    '}\n'
    'EXPECTED_REVIEW_SOURCES = set().union(*EXPECTED_REVIEW_UNITS.values())\n'
    'EXPECTED_BASELINE_ABSORBED_SOURCES = {\n'
    '    "app/db/repositories/workflow_state_repository.py",\n'
    '}\n'
    'EXPECTED_CANDIDATE_CHANGED_SOURCES = (\n'
    '    EXPECTED_REVIEW_SOURCES - EXPECTED_BASELINE_ABSORBED_SOURCES\n'
    ')\n',
    "VALIDATOR_CONSTANT_BLOCK_NOT_FOUND",
)
validator = replace_once(
    validator,
    '    if len(assigned) != len(set(assigned)) or set(assigned) != EXPECTED_CHANGED_SOURCES:\n'
    '        fail("CANDIDATE_REVIEW_SOURCE_PARTITION_INVALID")\n',
    '    if len(assigned) != len(set(assigned)) or set(assigned) != EXPECTED_REVIEW_SOURCES:\n'
    '        fail("CANDIDATE_REVIEW_SOURCE_PARTITION_INVALID")\n',
    "VALIDATOR_ASSIGNED_PARTITION_BLOCK_NOT_FOUND",
)
validator = replace_once(
    validator,
    '    if changed != EXPECTED_CHANGED_SOURCES or len(unchanged) != 12:\n'
    '        fail("CANDIDATE_SOURCE_CHANGE_CLASSIFICATION_INVALID")\n'
    '    if unchanged & set(assigned):\n'
    '        fail("CANDIDATE_UNCHANGED_SOURCE_REVIEW_MISCLASSIFIED")\n',
    '    if changed != EXPECTED_CANDIDATE_CHANGED_SOURCES or len(unchanged) != 13:\n'
    '        fail("CANDIDATE_SOURCE_CHANGE_CLASSIFICATION_INVALID")\n'
    '    assigned_unchanged = unchanged & set(assigned)\n'
    '    if assigned_unchanged != EXPECTED_BASELINE_ABSORBED_SOURCES:\n'
    '        fail("CANDIDATE_UNCHANGED_SOURCE_REVIEW_MISCLASSIFIED")\n',
    "VALIDATOR_CLASSIFICATION_BLOCK_NOT_FOUND",
)
validator_path.write_text(validator, encoding="utf-8")

review_builder = review_builder_path.read_text(encoding="utf-8")
review_builder = replace_once(
    review_builder,
    'REPO_ROOT = Path(__file__).resolve().parents[1]\n'
    'POLICY_PATH = REPO_ROOT / "config/slack_worker_release_rebinding_review_policy.json"\n'
    'REVIEW_REQUEST_ROOT = (\n'
    '    REPO_ROOT / "exchange/review_requests/slack_worker_release_rebinding"\n'
    ')\n',
    f'REPO_ROOT = Path({str(repo)!r})\n'
    f'SHADOW_ROOT = Path({str(shadow)!r})\n'
    'POLICY_PATH = SHADOW_ROOT / "config/slack_worker_release_rebinding_review_policy.json"\n'
    'REVIEW_REQUEST_ROOT = SHADOW_ROOT / "review_requests"\n',
    "REVIEW_BUILDER_CONSTANT_BLOCK_NOT_FOUND",
)
review_builder_path.write_text(review_builder, encoding="utf-8")

review_validator = review_validator_path.read_text(encoding="utf-8")
review_validator = replace_once(
    review_validator,
    'REPO_ROOT = Path(__file__).resolve().parents[1]\n',
    f'REPO_ROOT = Path({str(repo)!r})\n',
    "REVIEW_VALIDATOR_REPO_ROOT_NOT_FOUND",
)
review_validator_path.write_text(review_validator, encoding="utf-8")

rebinding_policy = json.loads(rebinding_policy_path.read_text(encoding="utf-8"))
rebinding_policy["current_manifest"]["sha256"] = __import__("hashlib").sha256(
    shadow_manifest_path.read_bytes()
).hexdigest()
rebinding_policy["current_manifest"]["formal_write_allowed"] = False
for unit in rebinding_policy["review_units"]:
    if unit["unit"] == "UNIT_WORKFLOW_STATE":
        unit["candidate_change_role"] = "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW"
        unit["purpose"] = (
            "Human-rereview the FIX1 WordPress post-ID invariant after its source "
            "was absorbed into the shadow baseline; it is not a new candidate delta."
        )
        unit["security_impact"] = (
            "GLOBAL_POST_ID_UNIQUENESS_AND_REBIND_FAIL_CLOSED_PENDING_HUMAN_REREVIEW"
        )
        unit["runtime_impact"] = (
            "SOURCE_MATCHES_SHADOW_BASELINE_BUT_PRODUCTION_MIGRATION_REMAINS_UNAPPLIED"
        )
    else:
        unit["candidate_change_role"] = "CHANGED"
rebinding_policy_path.write_text(
    json.dumps(rebinding_policy, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

review_policy = json.loads(review_policy_path.read_text(encoding="utf-8"))
review_policy["production_manifest"]["sha256"] = production_manifest_sha
review_policy["source_contract"][workflow_source]["current_sha256"] = workflow_sha

for unit in review_policy["review_units"]:
    if unit["unit_id"] != "UNIT_WORKFLOW_STATE":
        unit["candidate_change_role"] = "CHANGED"
        continue

    unit["candidate_change_role"] = "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW"
    unit["intended_behavior"] = (
        "Validate and bind one globally unique positive ASCII decimal WordPress "
        "post ID with no ordinary clear or rebind, while preserving caller-owned "
        "transaction and DRAFT-only reconciliation boundaries."
    )
    unit["changed_public_runtime_interfaces"] = [
        "WorkflowStateRepository.set_wordpress_post_id",
        "WorkflowStateRepository.mark_wordpress_draft_created",
    ]
    dimensions = unit.setdefault("review_dimensions", {})
    dimensions["wordpress_post_id_behavior"] = (
        "Accept only int or ASCII digit string values representing a positive "
        "canonical decimal with at most 20 digits; reject bool, zero, negative, "
        "signs, decimal, whitespace, Unicode digits, leading zero, and 21+ digits."
    )
    dimensions["none_semantics"] = (
        "None is accepted only for an unbound input path and cannot clear an "
        "existing binding."
    )
    dimensions["duplicate_handling"] = (
        "The same binding is idempotent; ordinary rebind is forbidden; non-NULL "
        "WordPress post IDs are globally unique through repository precheck and "
        "a partial unique index."
    )
    dimensions["schema_boundary"] = (
        "The supporting partial unique-index migration exists as review evidence "
        "but is not applied by this shadow preparation."
    )
    unit["known_limitations"] = [
        "The production migration remains unapplied.",
        "The production manifest remains unchanged.",
    ]
    unit["unresolved_issues"] = [
        "Human review must approve the FIX1 source and migration as a production unit."
    ]
    unit["test_evidence_gaps"] = [
        "No production database is opened by this review preparation.",
        "No production migration is applied by this review preparation.",
    ]
    unit["human_review_checklist"] = [
        "ASCII正整数のみを受理し、bool・符号・空白・Unicode数字・先頭0・21桁以上を拒否するか",
        "Noneで既存bindingを解除できないか",
        "同一bindingだけがidempotentか",
        "通常rebindがfail-closedか",
        "cross-item重複をrepository precheckとpartial unique indexで拒否するか",
        "DRAFT以外へ誤遷移しないか",
        "migration未適用のまま本番承認されないか",
    ]

review_policy_path.write_text(
    json.dumps(review_policy, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

PYTHONPATH="$SHADOW_ROOT" python3 -m py_compile \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$SHADOW_ROOT/scripts/lib/secure_release_file_reader.py"

python3 -m json.tool \
    "$SHADOW_ROOT/config/slack_worker_release_source_manifest.json" >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_policy.json" >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_review_policy.json" >/dev/null

STATIC_RESULT="${EVIDENCE_ROOT}/static-contract-validation.json"

PYTHONPATH="$SHADOW_ROOT" python3 - "$REPO_ROOT" "$SHADOW_ROOT" "$STATIC_RESULT" <<'PY'
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
shadow = Path(sys.argv[2]).resolve()
result_path = Path(sys.argv[3])

# stdin execution keeps the caller's current directory at the front of sys.path.
# Remove the production repository path and force the unique shadow package first.
filtered_sys_path: list[str] = []
for entry in sys.path:
    resolved = Path(entry or ".").resolve()
    if resolved in {repo, shadow}:
        continue
    filtered_sys_path.append(entry)
sys.path[:] = [str(shadow), *filtered_sys_path]

for module_name in list(sys.modules):
    if module_name == "scripts" or module_name.startswith("scripts."):
        del sys.modules[module_name]

builder = importlib.import_module("scripts.build_slack_worker_release_manifest_candidate")
validator = importlib.import_module("scripts.validate_slack_worker_release_manifest_candidate")
review_builder = importlib.import_module(
    "scripts.build_slack_worker_release_rebinding_review_bundle"
)

workflow = "app/db/repositories/workflow_state_repository.py"
expected_changed = {
    "app/db/access_guard.py",
    "app/db/config.py",
    "app/db/session.py",
    "scripts/run_slack_approval_socket.py",
}
expected_review = expected_changed | {workflow}

rebinding_policy = json.loads(
    (shadow / "config/slack_worker_release_rebinding_policy.json").read_text(
        encoding="utf-8"
    )
)
review_policy = json.loads(
    (shadow / "config/slack_worker_release_rebinding_review_policy.json").read_text(
        encoding="utf-8"
    )
)

checks = {
    "builder_repo_root_is_production_source_tree": builder.REPO_ROOT == repo,
    "builder_policy_is_shadow": builder.POLICY_PATH
    == shadow / "config/slack_worker_release_rebinding_policy.json",
    "builder_manifest_is_shadow": builder.PRODUCTION_MANIFEST_PATH
    == shadow / "config/slack_worker_release_source_manifest.json",
    "validator_changed_sources_are_four": validator.EXPECTED_CANDIDATE_CHANGED_SOURCES
    == expected_changed,
    "validator_review_sources_are_five": validator.EXPECTED_REVIEW_SOURCES
    == expected_review,
    "validator_absorbed_source_is_workflow": validator.EXPECTED_BASELINE_ABSORBED_SOURCES
    == {workflow},
    "review_builder_policy_is_shadow": review_builder.POLICY_PATH
    == shadow / "config/slack_worker_release_rebinding_review_policy.json",
    "review_builder_output_is_shadow": review_builder.REVIEW_REQUEST_ROOT
    == shadow / "review_requests",
    "shadow_rebinding_manifest_is_bound": rebinding_policy["current_manifest"][
        "sha256"
    ]
    == hashlib.sha256(
        (shadow / "config/slack_worker_release_source_manifest.json").read_bytes()
    ).hexdigest(),
    "workflow_review_current_sha_is_fix1": review_policy["source_contract"][workflow][
        "current_sha256"
    ]
    == "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
}

failed = sorted(name for name, passed in checks.items() if not passed)
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3A",
    "result": (
        "PASS_SHADOW_TOOLCHAIN_STATIC_CONTRACT"
        if not failed
        else "FAIL_SHADOW_TOOLCHAIN_STATIC_CONTRACT"
    ),
    "checks": checks,
    "failed_checks": failed,
    "candidate_generation_performed": False,
    "review_bundle_generation_performed": False,
    "production_manifest_modified": False,
    "production_database_accessed": False,
    "migration_applied": False,
    "deployment_performed": False,
    "external_network_used": False,
}
result_path.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
if failed:
    raise SystemExit("STATIC_CONTRACT_VALIDATION_FAILED:" + ",".join(failed))
PY

cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/build_slack_worker_release_manifest_candidate.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/validate_slack_worker_release_manifest_candidate.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/build_slack_worker_release_rebinding_review_bundle.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/validate_slack_worker_release_rebinding_review_bundle.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/validate_slack_worker_release_bundle_contract.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/scripts/lib/secure_release_file_reader.py" \
    "$EVIDENCE_ROOT/shadow-snapshot/scripts/lib/secure_release_file_reader.py"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/config/slack_worker_release_source_manifest.json" \
    "$EVIDENCE_ROOT/shadow-snapshot/config/slack_worker_release_source_manifest.json"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_policy.json" \
    "$EVIDENCE_ROOT/shadow-snapshot/config/slack_worker_release_rebinding_policy.json"
cp --preserve=mode,timestamps \
    "$SHADOW_ROOT/config/slack_worker_release_rebinding_review_policy.json" \
    "$EVIDENCE_ROOT/shadow-snapshot/config/slack_worker_release_rebinding_review_policy.json"

SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/shadow-snapshot-manifest.txt"
(
    cd "$EVIDENCE_ROOT/shadow-snapshot"
    find . -type f -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$SNAPSHOT_MANIFEST"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
MANIFEST_AFTER="$(sha256_file "$MANIFEST_PATH")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$MANIFEST_AFTER" == "$EXPECTED_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CONTENT_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
STATIC_SHA="$(sha256_file "$STATIC_RESULT")"
SNAPSHOT_MANIFEST_SHA="$(sha256_file "$SNAPSHOT_MANIFEST")"

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3A",
  "result": "PASS_W2B_I2F3A_SHADOW_TOOLCHAIN_SKELETON_READY",
  "approval_scope": "APPROVE_SHADOW_CONTRACT_IMPLEMENTATION_ONLY",
  "shadow_root": "${SHADOW_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "contract": {
    "candidate_changed_source_count": 4,
    "baseline_absorbed_source_count": 1,
    "candidate_unchanged_source_count": 13,
    "human_review_source_diff_count": 5,
    "review_unit_count": 3
  },
  "validation": {
    "python_compile_passed": true,
    "json_validation_passed": true,
    "static_contract_validation_sha256": "${STATIC_SHA}",
    "shadow_snapshot_manifest_sha256": "${SNAPSHOT_MANIFEST_SHA}"
  },
  "execution": {
    "candidate_generation_performed": false,
    "candidate_validation_performed": false,
    "review_bundle_generation_performed": false,
    "review_bundle_validation_performed": false
  },
  "safety": {
    "production_source_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "next_phase": "TST-5D-W2B-I2F-3B_SHADOW_CANDIDATE_GENERATION_AND_VALIDATION",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3A_SHADOW_TOOLCHAIN_SKELETON_READY\n'
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'CANDIDATE_CHANGED_SOURCE_COUNT=4\n'
printf 'BASELINE_ABSORBED_SOURCE_COUNT=1\n'
printf 'CANDIDATE_UNCHANGED_SOURCE_COUNT=13\n'
printf 'HUMAN_REVIEW_SOURCE_DIFF_COUNT=5\n'
printf 'REVIEW_UNIT_COUNT=3\n'
printf 'PYTHON_COMPILE_PASSED=true\n'
printf 'JSON_VALIDATION_PASSED=true\n'
printf 'STATIC_CONTRACT_VALIDATION_PASSED=true\n'
printf 'CANDIDATE_GENERATION_PERFORMED=false\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=false\n'
printf 'STATIC_RESULT_SHA=%s\n' "$STATIC_SHA"
printf 'SNAPSHOT_MANIFEST_SHA=%s\n' "$SNAPSHOT_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3B_SHADOW_CANDIDATE_GENERATION_AND_VALIDATION\n'
