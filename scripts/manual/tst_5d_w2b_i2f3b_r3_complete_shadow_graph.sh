#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
OLD_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3a-shadow-20260725T145828-487557"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
I2F3A_ROOT_REL="${I2E_ROOT_REL}/i2f3a-shadow-toolchain-skeleton-20260725T145828-487557"
I2F3B_R2_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r2-downstream-graph-binding-audit-20260725T151140-488498"

I2F3A_RESULT="${REPO_ROOT}/${I2F3A_ROOT_REL}/result.json"
I2F3A_SNAPSHOT_MANIFEST="${REPO_ROOT}/${I2F3A_ROOT_REL}/shadow-snapshot-manifest.txt"
I2F3B_R2_RESULT="${REPO_ROOT}/${I2F3B_R2_ROOT_REL}/result.json"

EXPECTED_I2F3A_RESULT_SHA="dd09b31a2499c6b7d311cc7dc1067862ecae3ececd615ce0d9917a152d78c744"
EXPECTED_I2F3A_SNAPSHOT_MANIFEST_SHA="6b3db0e4516d2f14ae6c173467896e7b9979f56f2903af2c4d174916457e8ba5"
EXPECTED_I2F3B_R2_RESULT_SHA="2f23da344846e782ce87820172afffc5a7d086d7b5ff325f42e15cb5fa9c8bfd"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
PRODUCTION_POLICY="${REPO_ROOT}/config/slack_worker_release_rebinding_policy.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

OLD_SHADOW_MANIFEST="${OLD_SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_OLD_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"
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

require_file_sha "$I2F3A_RESULT" "$EXPECTED_I2F3A_RESULT_SHA"
require_file_sha \
    "$I2F3A_SNAPSHOT_MANIFEST" \
    "$EXPECTED_I2F3A_SNAPSHOT_MANIFEST_SHA"
require_file_sha "$I2F3B_R2_RESULT" "$EXPECTED_I2F3B_R2_RESULT_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$OLD_SHADOW_MANIFEST" "$EXPECTED_OLD_SHADOW_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

if [[ ! -d "$OLD_SHADOW_ROOT" ]]; then
    printf 'ERROR=OLD_SHADOW_ROOT_MISSING:%s\n' "$OLD_SHADOW_ROOT" >&2
    exit 1
fi

while read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    actual_path="${OLD_SHADOW_ROOT}/${relative#./}"
    require_file_sha "$actual_path" "$expected"
done < "$I2F3A_SNAPSHOT_MANIFEST"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
COMPLETE_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3b-r3-complete-shadow-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3b-r3-complete-shadow-graph-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$COMPLETE_SHADOW_ROOT" ]]; then
    printf 'ERROR=COMPLETE_SHADOW_ROOT_EXISTS:%s\n' "$COMPLETE_SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$COMPLETE_SHADOW_ROOT/scripts/lib" \
    "$COMPLETE_SHADOW_ROOT/config" \
    "$COMPLETE_SHADOW_ROOT/exchange/logs" \
    "$COMPLETE_SHADOW_ROOT/review_requests" \
    "$EVIDENCE_ROOT/shadow-snapshot"

python3 - \
    "$REPO_ROOT" \
    "$OLD_SHADOW_ROOT" \
    "$COMPLETE_SHADOW_ROOT" \
    "$PRODUCTION_POLICY" \
    "$PRODUCTION_MANIFEST" <<'PY'
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
old_shadow = Path(sys.argv[2]).resolve()
complete = Path(sys.argv[3]).resolve()
production_policy_path = Path(sys.argv[4]).resolve()
production_manifest_path = Path(sys.argv[5]).resolve()

special_shadow_configs = {
    "slack_worker_release_source_manifest.json",
    "slack_worker_release_rebinding_policy.json",
    "slack_worker_release_rebinding_review_policy.json",
}

tool_relatives = [
    "scripts/__init__.py",
    "scripts/lib/__init__.py",
    "scripts/lib/secure_release_file_reader.py",
    "scripts/build_slack_worker_release_manifest_candidate.py",
    "scripts/validate_slack_worker_release_manifest_candidate.py",
    "scripts/build_slack_worker_release_rebinding_review_bundle.py",
    "scripts/validate_slack_worker_release_rebinding_review_bundle.py",
    "scripts/validate_slack_worker_release_bundle_contract.py",
]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def copy_exclusive(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"COPY_SOURCE_MISSING:{src}")
    if dst.exists() or os.path.lexists(dst):
        raise SystemExit(f"COPY_DESTINATION_EXISTS:{dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst, follow_symlinks=False)


def atomic_write_new(path: Path, data: bytes, mode: int) -> None:
    temp = path.with_name(path.name + ".i2f3r3-new")
    if temp.exists() or os.path.lexists(temp):
        raise SystemExit(f"TEMP_OUTPUT_EXISTS:{temp}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(os.fspath(temp), flags, mode)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temp, path)


for relative in tool_relatives:
    copy_exclusive(old_shadow / relative, complete / relative)

for source in sorted((repo / "config").glob("slack_worker*.json")):
    destination = complete / "config" / source.name
    if source.name in special_shadow_configs:
        copy_exclusive(old_shadow / "config" / source.name, destination)
    else:
        copy_exclusive(source, destination)

production_policy = load(production_policy_path)
production_manifest = load(production_manifest_path)
shadow_manifest_path = complete / "config/slack_worker_release_source_manifest.json"
shadow_manifest = load(shadow_manifest_path)

immutable_paths = [
    value
    for value in production_policy.get("immutable_direct_evidence", [])
    if isinstance(value, str)
]
for relative in immutable_paths:
    source = repo / relative
    destination = complete / relative
    copy_exclusive(source, destination)
    destination.chmod(0o444)

builder_path = repo / "scripts/build_slack_worker_release_manifest_candidate.py"
spec = importlib.util.spec_from_file_location("i2f3r3_production_builder", builder_path)
if spec is None or spec.loader is None:
    raise SystemExit("PRODUCTION_BUILDER_IMPORT_SPEC_FAILED")
production_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(production_builder)

production_manifest_sha = sha(production_manifest_path)
shadow_manifest_sha = sha(shadow_manifest_path)
production_release_id = str(production_manifest["release_id_candidate"])
shadow_release_id = str(shadow_manifest["release_id_candidate"])

original_policy_path = production_builder.POLICY_PATH
production_builder.POLICY_PATH = production_policy_path
try:
    chain = production_builder.discover_downstream_chain(
        repo,
        production_policy,
        production_manifest_sha,
        production_release_id,
    )
finally:
    production_builder.POLICY_PATH = original_policy_path

shadow_sha_by_path: dict[str, str] = {}
for item in chain:
    relative = item["path"]
    source_path = repo / relative
    destination = complete / relative

    if not item["mutable"]:
        if sha(source_path) != sha(destination):
            raise SystemExit(f"IMMUTABLE_COPY_SHA_MISMATCH:{relative}")
        continue

    document = load(source_path)
    replacements = {
        production_manifest_sha: shadow_manifest_sha,
        production_release_id: shadow_release_id,
    }
    for upstream in item["upstream_dependencies"]:
        if upstream in shadow_sha_by_path:
            replacements[sha(repo / upstream)] = shadow_sha_by_path[upstream]

    rebound = production_builder.deep_replace(document, replacements)
    payload = production_builder.canonical_bytes(rebound)
    mode = stat.S_IMODE(source_path.stat().st_mode)
    atomic_write_new(destination, payload, mode)
    shadow_sha_by_path[relative] = sha_bytes(payload)

shadow_policy_path = complete / "config/slack_worker_release_rebinding_policy.json"
shadow_policy = load(shadow_policy_path)
shadow_policy["current_manifest"]["sha256"] = shadow_manifest_sha
shadow_policy["current_manifest"]["formal_write_allowed"] = False
atomic_write_new(
    shadow_policy_path,
    (
        json.dumps(
            shadow_policy,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8"),
    stat.S_IMODE(shadow_policy_path.stat().st_mode),
)

builder_shadow_path = complete / "scripts/build_slack_worker_release_manifest_candidate.py"
builder_text = builder_shadow_path.read_text(encoding="utf-8")
old_shadow_literal = repr(str(old_shadow))
complete_literal = repr(str(complete))
if old_shadow_literal not in builder_text:
    raise SystemExit("BUILDER_OLD_SHADOW_ROOT_NOT_FOUND")
builder_text = builder_text.replace(old_shadow_literal, complete_literal)

old_signature = "def build_candidate_documents(repo_root: Path = REPO_ROOT) -> dict[str, Any]:"
new_signature = (
    "def build_candidate_documents(\n"
    "    repo_root: Path = REPO_ROOT,\n"
    "    graph_root: Path = SHADOW_ROOT,\n"
    ") -> dict[str, Any]:"
)
if builder_text.count(old_signature) != 1:
    raise SystemExit("BUILDER_DOCUMENT_SIGNATURE_NOT_FOUND")
builder_text = builder_text.replace(old_signature, new_signature, 1)

old_chain_call = """    chain = discover_downstream_chain(
        repo_root,
        policy,
        current_manifest_sha,
        current_manifest["release_id_candidate"],
    )
"""
new_chain_call = """    chain = discover_downstream_chain(
        graph_root,
        policy,
        current_manifest_sha,
        current_manifest["release_id_candidate"],
    )
"""
if builder_text.count(old_chain_call) != 1:
    raise SystemExit("BUILDER_CHAIN_CALL_NOT_FOUND")
builder_text = builder_text.replace(old_chain_call, new_chain_call, 1)

old_parsed_chain = """    parsed_chain = {
        item["path"]: load_json(repo_root / item["path"])
        for item in chain
    }
"""
new_parsed_chain = """    parsed_chain = {
        item["path"]: load_json(graph_root / item["path"])
        for item in chain
    }
"""
if builder_text.count(old_parsed_chain) != 1:
    raise SystemExit("BUILDER_PARSED_CHAIN_BLOCK_NOT_FOUND")
builder_text = builder_text.replace(old_parsed_chain, new_parsed_chain, 1)

old_upstream_sha = "replacements[sha256_path(repo_root / upstream)] = candidate_sha_by_path["
new_upstream_sha = "replacements[sha256_path(graph_root / upstream)] = candidate_sha_by_path["
if builder_text.count(old_upstream_sha) != 1:
    raise SystemExit("BUILDER_UPSTREAM_SHA_REFERENCE_NOT_FOUND")
builder_text = builder_text.replace(old_upstream_sha, new_upstream_sha, 1)

old_tool_hash = '"sha256": sha256_path(repo_root / relative),'
new_tool_hash = '"sha256": sha256_path(SHADOW_ROOT / relative),'
if builder_text.count(old_tool_hash) != 1:
    raise SystemExit("BUILDER_TOOL_HASH_REFERENCE_NOT_FOUND")
builder_text = builder_text.replace(old_tool_hash, new_tool_hash, 1)

builder_shadow_path.write_text(builder_text, encoding="utf-8")

review_builder_path = complete / "scripts/build_slack_worker_release_rebinding_review_bundle.py"
review_text = review_builder_path.read_text(encoding="utf-8")
if old_shadow_literal not in review_text:
    raise SystemExit("REVIEW_BUILDER_OLD_SHADOW_ROOT_NOT_FOUND")
review_text = review_text.replace(old_shadow_literal, complete_literal)

old_secure_function = """def secure_repo_bytes(path: Path, *, expected_sha256: str | None = None) -> bytes:
    try:
        return read_secure_release_file(
            path,
            allowed_root=REPO_ROOT,
            expected_sha256=expected_sha256,
        ).data
    except ReleaseFileError as exc:
        raise ReviewBundleBlocked(exc.code) from exc
"""
new_secure_function = """def secure_repo_bytes(path: Path, *, expected_sha256: str | None = None) -> bytes:
    absolute = path.absolute()
    allowed_root = (
        SHADOW_ROOT
        if absolute.is_relative_to(SHADOW_ROOT)
        else REPO_ROOT
    )
    try:
        return read_secure_release_file(
            path,
            allowed_root=allowed_root,
            expected_sha256=expected_sha256,
        ).data
    except ReleaseFileError as exc:
        raise ReviewBundleBlocked(exc.code) from exc
"""
if review_text.count(old_secure_function) != 1:
    raise SystemExit("REVIEW_BUILDER_SECURE_FUNCTION_NOT_FOUND")
review_text = review_text.replace(old_secure_function, new_secure_function, 1)

review_text = review_text.replace(
    'REPO_ROOT / "scripts/validate_slack_worker_release_manifest_candidate.py"',
    'SHADOW_ROOT / "scripts/validate_slack_worker_release_manifest_candidate.py"',
)
review_text = review_text.replace(
    'REPO_ROOT\n                    / "scripts/build_slack_worker_release_rebinding_review_bundle.py"',
    'SHADOW_ROOT\n                    / "scripts/build_slack_worker_release_rebinding_review_bundle.py"',
)
review_builder_path.write_text(review_text, encoding="utf-8")

review_validator_path = complete / "scripts/validate_slack_worker_release_rebinding_review_bundle.py"
review_validator_text = review_validator_path.read_text(encoding="utf-8")
review_validator_text = review_validator_text.replace(
    "REPO_ROOT = Path('/home/deploy/ai_media_os')",
    "REPO_ROOT = Path('/home/deploy/ai_media_os')\n"
    f"SHADOW_ROOT = Path({str(complete)!r})",
    1,
)
review_validator_path.write_text(review_validator_text, encoding="utf-8")

for path in [
    complete / "scripts/build_slack_worker_release_manifest_candidate.py",
    complete / "scripts/build_slack_worker_release_rebinding_review_bundle.py",
    complete / "scripts/validate_slack_worker_release_manifest_candidate.py",
    complete / "scripts/validate_slack_worker_release_rebinding_review_bundle.py",
]:
    if str(old_shadow) in path.read_text(encoding="utf-8"):
        raise SystemExit(f"OLD_SHADOW_ROOT_REMAINS:{path}")
PY

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$COMPLETE_SHADOW_ROOT" \
python3 -m py_compile \
    "$COMPLETE_SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$COMPLETE_SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$COMPLETE_SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$COMPLETE_SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$COMPLETE_SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$COMPLETE_SHADOW_ROOT/scripts/lib/secure_release_file_reader.py"

while IFS= read -r file; do
    python3 -m json.tool "$file" >/dev/null
done < <(
    find "$COMPLETE_SHADOW_ROOT/config" -maxdepth 1 -type f -name 'slack_worker*.json' \
        | LC_ALL=C sort
)

GRAPH_AUDIT="${EVIDENCE_ROOT}/complete-shadow-graph-validation.json"
GRAPH_TXT="${EVIDENCE_ROOT}/complete-shadow-graph-validation.txt"

(
    cd "$COMPLETE_SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$COMPLETE_SHADOW_ROOT" \
    python3 - \
        "$REPO_ROOT" \
        "$COMPLETE_SHADOW_ROOT" \
        "$GRAPH_AUDIT" \
        "$GRAPH_TXT" <<'PY'
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

repo = Path(sys.argv[1]).resolve()
shadow = Path(sys.argv[2]).resolve()
audit_path = Path(sys.argv[3])
text_path = Path(sys.argv[4])

for module_name in list(sys.modules):
    if module_name == "scripts" or module_name.startswith("scripts."):
        del sys.modules[module_name]

builder = importlib.import_module("scripts.build_slack_worker_release_manifest_candidate")

production_manifest_path = repo / "config/slack_worker_release_source_manifest.json"
shadow_manifest_path = shadow / "config/slack_worker_release_source_manifest.json"
shadow_policy_path = shadow / "config/slack_worker_release_rebinding_policy.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leaves(value: object, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


production_manifest = load(production_manifest_path)
shadow_manifest = load(shadow_manifest_path)
shadow_policy = load(shadow_policy_path)

production_manifest_sha = sha(production_manifest_path)
shadow_manifest_sha = sha(shadow_manifest_path)
production_release_id = str(production_manifest["release_id_candidate"])
shadow_release_id = str(shadow_manifest["release_id_candidate"])

chain = builder.discover_downstream_chain(
    shadow,
    shadow_policy,
    shadow_manifest_sha,
    shadow_release_id,
)
graph_contract_sha = builder.finalize_rebinding_graph(chain)

mutable = [item for item in chain if item["mutable"]]
immutable = [item for item in chain if not item["mutable"]]
direct = [item for item in chain if item["depth"] == 1 and item["mutable"]]

production_identity_remaining: dict[str, list[str]] = {}
shadow_identity_fields: dict[str, list[str]] = {}
for item in mutable:
    path = shadow / item["path"]
    document = load(path)
    prod_fields = [
        field
        for field, value in leaves(document)
        if production_manifest_sha in value or production_release_id in value
    ]
    shadow_fields = [
        field
        for field, value in leaves(document)
        if shadow_manifest_sha in value or shadow_release_id in value
    ]
    if prod_fields:
        production_identity_remaining[item["path"]] = sorted(prod_fields)
    if shadow_fields:
        shadow_identity_fields[item["path"]] = sorted(shadow_fields)

direct_without_shadow_binding = sorted(
    item["path"]
    for item in direct
    if not shadow_identity_fields.get(item["path"])
)

immutable_sha_checks: dict[str, bool] = {}
for item in immutable:
    relative = item["path"]
    immutable_sha_checks[relative] = sha(shadow / relative) == sha(repo / relative)

checks = {
    "builder_repo_root_is_production": builder.REPO_ROOT == repo,
    "builder_shadow_root_is_complete": builder.SHADOW_ROOT == shadow,
    "builder_policy_is_complete_shadow": builder.POLICY_PATH
    == shadow / "config/slack_worker_release_rebinding_policy.json",
    "builder_manifest_is_complete_shadow": builder.PRODUCTION_MANIFEST_PATH
    == shadow / "config/slack_worker_release_source_manifest.json",
    "chain_total_21": len(chain) == 21,
    "chain_mutable_19": len(mutable) == 19,
    "chain_immutable_2": len(immutable) == 2,
    "direct_binder_count_9": len(direct) == 9,
    "all_direct_binders_bind_shadow_identity": not direct_without_shadow_binding,
    "no_mutable_artifact_retains_production_identity": not production_identity_remaining,
    "immutable_evidence_byte_identical": all(immutable_sha_checks.values()),
    "graph_contract_sha_is_valid": isinstance(graph_contract_sha, str)
    and len(graph_contract_sha) == 64,
}

failed = sorted(name for name, passed in checks.items() if not passed)

audit = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3B-R3",
    "result": (
        "PASS_COMPLETE_SHADOW_GRAPH_VALIDATION"
        if not failed
        else "FAIL_COMPLETE_SHADOW_GRAPH_VALIDATION"
    ),
    "roots": {
        "production_repo_root": str(repo),
        "complete_shadow_root": str(shadow),
    },
    "identity": {
        "production_manifest_sha256": production_manifest_sha,
        "shadow_manifest_sha256": shadow_manifest_sha,
        "production_release_id": production_release_id,
        "shadow_release_id": shadow_release_id,
    },
    "counts": {
        "chain_total_count": len(chain),
        "mutable_count": len(mutable),
        "immutable_count": len(immutable),
        "direct_binder_count": len(direct),
        "config_file_count": len(
            list((shadow / "config").glob("slack_worker*.json"))
        ),
    },
    "graph_contract_sha256": graph_contract_sha,
    "chain": chain,
    "shadow_identity_fields": shadow_identity_fields,
    "production_identity_remaining": production_identity_remaining,
    "direct_without_shadow_binding": direct_without_shadow_binding,
    "immutable_sha_checks": immutable_sha_checks,
    "checks": checks,
    "failed_checks": failed,
    "execution": {
        "candidate_generation_performed": False,
        "candidate_validation_performed": False,
        "review_bundle_generation_performed": False,
    },
    "safety": {
        "production_files_written": False,
        "production_database_accessed": False,
        "migration_applied": False,
        "deployment_performed": False,
        "external_network_used": False,
    },
}

audit_path.write_text(
    json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

lines = [
    f"RESULT={audit['result']}",
    f"COMPLETE_SHADOW_ROOT={shadow}",
    f"SHADOW_CONFIG_FILE_COUNT={audit['counts']['config_file_count']}",
    f"CHAIN_TOTAL_COUNT={len(chain)}",
    f"CHAIN_MUTABLE_COUNT={len(mutable)}",
    f"CHAIN_IMMUTABLE_COUNT={len(immutable)}",
    f"DIRECT_BINDER_COUNT={len(direct)}",
    f"GRAPH_CONTRACT_SHA={graph_contract_sha}",
    f"ALL_DIRECT_BINDERS_BIND_SHADOW_IDENTITY={str(not direct_without_shadow_binding).lower()}",
    f"NO_MUTABLE_ARTIFACT_RETAINS_PRODUCTION_IDENTITY={str(not production_identity_remaining).lower()}",
    f"IMMUTABLE_EVIDENCE_BYTE_IDENTICAL={str(all(immutable_sha_checks.values())).lower()}",
    "CANDIDATE_GENERATION_PERFORMED=false",
    "REVIEW_BUNDLE_GENERATION_PERFORMED=false",
]
text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

if failed:
    raise SystemExit("COMPLETE_SHADOW_GRAPH_VALIDATION_FAILED:" + ",".join(failed))
PY
)

cat "$GRAPH_TXT"

(
    cd "$COMPLETE_SHADOW_ROOT"
    while IFS= read -r file; do
        destination="${EVIDENCE_ROOT}/shadow-snapshot/${file}"
        mkdir -p "$(dirname "$destination")"
        cp --preserve=mode,timestamps "$file" "$destination"
    done < <(
        find scripts config exchange -type f \
            | LC_ALL=C sort
    )
)

SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/shadow-snapshot-manifest.txt"
(
    cd "$EVIDENCE_ROOT/shadow-snapshot"
    find . -type f -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$SNAPSHOT_MANIFEST"

GRAPH_AUDIT_SHA="$(sha256_file "$GRAPH_AUDIT")"
GRAPH_TXT_SHA="$(sha256_file "$GRAPH_TXT")"
SNAPSHOT_MANIFEST_SHA="$(sha256_file "$SNAPSHOT_MANIFEST")"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
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

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3B-R3",
  "result": "PASS_W2B_I2F3B_R3_COMPLETE_SHADOW_GRAPH_READY",
  "complete_shadow_root": "${COMPLETE_SHADOW_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "counts": {
    "shadow_config_file_count": 22,
    "chain_total_count": 21,
    "mutable_count": 19,
    "immutable_count": 2,
    "direct_binder_count": 9
  },
  "validation": {
    "python_compile_passed": true,
    "json_validation_passed": true,
    "complete_shadow_graph_validation_sha256": "${GRAPH_AUDIT_SHA}",
    "complete_shadow_graph_text_sha256": "${GRAPH_TXT_SHA}",
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
  "next_phase": "TST-5D-W2B-I2F-3B-R4_SHADOW_CANDIDATE_GENERATION_AND_VALIDATION",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3B_R3_COMPLETE_SHADOW_GRAPH_READY\n'
printf 'COMPLETE_SHADOW_ROOT=%s\n' "$COMPLETE_SHADOW_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'SHADOW_CONFIG_FILE_COUNT=22\n'
printf 'CHAIN_TOTAL_COUNT=21\n'
printf 'CHAIN_MUTABLE_COUNT=19\n'
printf 'CHAIN_IMMUTABLE_COUNT=2\n'
printf 'DIRECT_BINDER_COUNT=9\n'
printf 'ALL_DIRECT_BINDERS_BIND_SHADOW_IDENTITY=true\n'
printf 'NO_MUTABLE_ARTIFACT_RETAINS_PRODUCTION_IDENTITY=true\n'
printf 'IMMUTABLE_EVIDENCE_BYTE_IDENTICAL=true\n'
printf 'PYTHON_COMPILE_PASSED=true\n'
printf 'JSON_VALIDATION_PASSED=true\n'
printf 'GRAPH_VALIDATION_SHA=%s\n' "$GRAPH_AUDIT_SHA"
printf 'SNAPSHOT_MANIFEST_SHA=%s\n' "$SNAPSHOT_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'CANDIDATE_GENERATION_PERFORMED=false\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3B-R4_SHADOW_CANDIDATE_GENERATION_AND_VALIDATION\n'
