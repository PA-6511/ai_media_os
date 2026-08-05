#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

EVIDENCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-j-root-deployment-final-execution-approval-packet-r2-runner-source-binding-correction-preparation-and-seal-20260726T122216Z-539539"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

SEALED_SOURCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-human-review-result-registration-and-seal-20260726T094913Z-537139"
SEALED_SOURCE_ROOT="${REPO_ROOT}/${SEALED_SOURCE_REL}"

CANDIDATE_SOURCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-negative-test-mutation-indentation-correction-preparation-20260726T072647Z-534604"
CANDIDATE_SOURCE_ROOT="${REPO_ROOT}/${CANDIDATE_SOURCE_REL}"

FAILED_STAGING_1_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/.i2f3e-j-root-deployment-final-execution-approval-packet-preparation-and-seal-staging-20260726T102320Z-537656"
FAILED_STAGING_1_ROOT="${REPO_ROOT}/${FAILED_STAGING_1_REL}"

FAILED_STAGING_2_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/.i2f3e-j-root-deployment-final-execution-approval-packet-r1-staging-lifecycle-correction-preparation-and-seal-staging-20260726T110354Z-538346"
FAILED_STAGING_2_ROOT="${REPO_ROOT}/${FAILED_STAGING_2_REL}"

test -x "$PYTHON_BIN"
test -d "$EVIDENCE_ROOT"
test ! -L "$EVIDENCE_ROOT"
test -d "$SEALED_SOURCE_ROOT"
test ! -L "$SEALED_SOURCE_ROOT"
test -d "$CANDIDATE_SOURCE_ROOT"
test ! -L "$CANDIDATE_SOURCE_ROOT"
test -d "$FAILED_STAGING_1_ROOT"
test ! -L "$FAILED_STAGING_1_ROOT"
test -d "$FAILED_STAGING_2_ROOT"
test ! -L "$FAILED_STAGING_2_ROOT"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$EVIDENCE_ROOT" \
  "$SEALED_SOURCE_ROOT" \
  "$CANDIDATE_SOURCE_ROOT" \
  "$FAILED_STAGING_1_ROOT" \
  "$FAILED_STAGING_2_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

REPO = Path(sys.argv[1]).resolve(strict=True)
EVIDENCE = Path(sys.argv[2]).resolve(strict=True)
SEALED_SOURCE = Path(sys.argv[3]).resolve(strict=True)
CANDIDATE_SOURCE = Path(sys.argv[4]).resolve(strict=True)
FAILED_STAGING_1 = Path(sys.argv[5]).resolve(strict=True)
FAILED_STAGING_2 = Path(sys.argv[6]).resolve(strict=True)
FAILED_STAGINGS = (FAILED_STAGING_1, FAILED_STAGING_2)

EXPECTED_RESULT_SHA = (
    "a93e5231ce39800f663623515fa2a190c"
    "ed326915fceecbf7fb7383e6f566367"
)
EXPECTED_PACKET_MANIFEST_SHA = (
    "80e49a7afdf390ee821b1515eee39c09"
    "a7ece246f218b6f4adb33841f2ea56cc"
)
EXPECTED_CANDIDATE_BINDING_SHA = (
    "ede979a98e5171b4571c7a17a4a95e2"
    "73c799deffb0f1d3774cbc72152702fae"
)
EXPECTED_COMMAND_CONTRACT_SHA = (
    "e0a0e0f1fade49f310dcc92586dc2bf6"
    "27c7ebf434ce30570d293683da068294"
)
EXPECTED_TOKEN_TEMPLATE_SHA = (
    "50d0327e6c034ce43ff0df3cf643e6e8"
    "b8e9f69f550e67cdf050c74e42bc775d"
)
EXPECTED_EVIDENCE_MANIFEST_SHA = (
    "f8acc73d809de4530b3bcb8712b75b7f"
    "b15a45db72b6cbba8cbc17808dccdf6d"
)

EXPECTED_EVIDENCE_FILES = {
    "result.json",
    "evidence-manifest.txt",
    "packet-snapshot/approval-binding-required-values.json",
    "packet-snapshot/exact-command-contract.json",
    "packet-snapshot/execution-candidate-binding.json",
    "packet-snapshot/failed-staging-inventory.json",
    "packet-snapshot/final-execution-approval-token-template.json",
    "packet-snapshot/human-approval-verbatim.txt",
    "packet-snapshot/operation-manual.md",
    "packet-snapshot/operator-checklist.md",
    "packet-snapshot/packet-contract.json",
    "packet-snapshot/packet-manifest.json",
    "packet-snapshot/preflight-path-state-contract.json",
    "packet-snapshot/protected-sha-contract.json",
    "packet-snapshot/reviewer-assumption-corrections.json",
    "packet-snapshot/rollback-stop-contract.json",
    "packet-snapshot/runner-source-binding-correction.json",
    "packet-snapshot/seal-contract.json",
    "packet-snapshot/sealed-source-verification.json",
    "packet-snapshot/target-layout.json",
}
EXPECTED_EVIDENCE_DIRECTORIES = {"packet-snapshot"}

EXPECTED_PACKET_PAYLOAD_FILES = {
    "approval-binding-required-values.json",
    "exact-command-contract.json",
    "execution-candidate-binding.json",
    "failed-staging-inventory.json",
    "final-execution-approval-token-template.json",
    "human-approval-verbatim.txt",
    "operation-manual.md",
    "operator-checklist.md",
    "packet-contract.json",
    "preflight-path-state-contract.json",
    "protected-sha-contract.json",
    "reviewer-assumption-corrections.json",
    "rollback-stop-contract.json",
    "runner-source-binding-correction.json",
    "seal-contract.json",
    "sealed-source-verification.json",
    "target-layout.json",
}

SEALED_EXPECTED_FILES = {
    "review-result.json",
    "evidence-manifest.txt",
    "packet-snapshot/human-approval-verbatim.txt",
    "packet-snapshot/human-review-result-verbatim.txt",
    "packet-snapshot/operation-manual.md",
    "packet-snapshot/review-contract.json",
    "packet-snapshot/reviewer-ast-scope-correction.json",
    "packet-snapshot/seal-contract.json",
    "packet-snapshot/source-inventory.json",
    "packet-snapshot/source-verification.json",
    "packet-snapshot/packet-manifest.json",
}
SEALED_EXPECTED_DIRECTORIES = {"packet-snapshot"}
SEALED_FIXED_SHA = {
    "review-result.json":
        "d4ddedce041a93a46eef3c9f66a572c5885630c8225f6d29eb437036f6538437",
    "packet-snapshot/packet-manifest.json":
        "790b18408c1821eddadfa8795b1d96267f26c8983b5479ea42bd250492cdaebb",
    "evidence-manifest.txt":
        "6c6201d3543f33cca72ef16e0df1773449e60fd1c58add6d0cb4d1dde03f1747",
}

CANDIDATE_SOURCE_FIXED_SHA = {
    "result.json":
        "8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d",
    "packet-snapshot/packet-manifest.json":
        "e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "evidence-manifest.txt":
        "78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7",
}
CANDIDATE_SOURCE_TREE_SHA = (
    "f55823bdffd9198e05e1b727b78f47ed"
    "8a395b37f6f9ee7ee557d0c35cac666e"
)

CRITICAL_CANDIDATE_SHA = {
    "candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "root_deployment_execution_once_r1.py":
        "0d712c6e12dc0b98213ca1995e4f22d1e9088ab5ffc31a97a497d60ba769fa53",
    "validate_root_deployment_execution_packet_r1.py":
        "efdabbe83c61a2618128f5518a726f007062bba0e91959a01eed1f380d4b2d74",
    "test_root_deployment_execution_packet_r1_negative.py":
        "6dad37c21c35921587e1839002a2435ebab4f4b88399f6035a9dcd9569156ca7",
}

RUNNER_CANDIDATE_MANIFEST_SHA = (
    "0677a9a9479e209a6e1ee30fdcd07996"
    "b671737850b17e79b97987578a73ec7f"
)
SOURCE_BINDING_CONTRACT_SHA = (
    "4010afe2bf6e5c8654b34d21cbd68172"
    "70e51e6a167eb792ab2b8717c653b3fa"
)
PARTIAL_SOURCE_INVENTORY_SHA = (
    "bae184212a1b72b67602eb11cc244ade"
    "30c6ba4280f133231fba52636064c213"
)

RUNNER_PAYLOAD_SHA = {
    "one_shot_writer_freeze_backup_restart_runner.py":
        "1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052",
    "root_fd_metadata_helper.py":
        "e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888",
    "runner-policy.json":
        "261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd",
    "validate_3e_j_runner_packet.py":
        "eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f",
    "test_3e_j_runner_negative.py":
        "3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e",
    "3e_j_operation_manual.md":
        "2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773",
}

PROTECTED_SHA = {
    "data/database/ebook_affiliate.db":
        "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9",
    "config/slack_worker_release_source_manifest.json":
        "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d",
    "app/db/repositories/workflow_state_repository.py":
        "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "migrations/versions/00241611109d_add_unique_wordpress_post_id.py":
        "e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a",
    "scripts/run_slack_approval_socket.py":
        "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
    "tests/test_slack_approval_socket_hold_remediation_offline.py":
        "86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72",
}

CANONICAL_RUNNER_REL = (
    "packet-snapshot/r1-r1-validator-target/"
    "packet-snapshot/source-partial-evidence-snapshot/"
    "packet-snapshot/deployment-input-snapshot/runner-candidate"
)
EXECUTION_EVIDENCE_REL = (
    "packet-snapshot/r1-r1-validator-target"
)
EXECUTION_CANDIDATE_REL = (
    "packet-snapshot/r1-r1-validator-target/"
    "packet-snapshot/candidate-artifacts"
)
OUTER_CANDIDATE_REL = "packet-snapshot/candidate-artifacts"

EXPECTED_RESULT_TEXT = (
    "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
    "PACKET_R2_RUNNER_SOURCE_BINDING_CORRECTION_"
    "PREPARED_AND_SEALED_NO_EXECUTION"
)


def require(condition: bool, marker: str) -> None:
    if not condition:
        raise AssertionError(marker)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan(
    root: Path,
) -> tuple[set[str], set[str], int, int]:
    files: set[str] = set()
    directories: set[str] = set()
    symlinks = 0
    nonregular = 0
    for path in sorted(root.rglob("*")):
        item = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(item.st_mode):
            symlinks += 1
        elif stat.S_ISREG(item.st_mode):
            files.add(relative)
        elif stat.S_ISDIR(item.st_mode):
            directories.add(relative)
        else:
            nonregular += 1
    return files, directories, symlinks, nonregular


def full_identity(root: Path) -> dict[str, tuple[object, ...]]:
    result: dict[str, tuple[object, ...]] = {}
    root_item = root.lstat()
    result["."] = (
        "DIR",
        stat.S_IMODE(root_item.st_mode),
        root_item.st_uid,
        root_item.st_gid,
        root_item.st_mtime_ns,
    )
    files, directories, symlinks, nonregular = scan(root)
    require(symlinks == 0, f"IDENTITY_SYMLINK:{root}")
    require(nonregular == 0, f"IDENTITY_NONREGULAR:{root}")
    for relative in sorted(directories):
        item = (root / relative).lstat()
        result[relative + "/"] = (
            "DIR",
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
            item.st_mtime_ns,
        )
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        result[relative] = (
            "FILE",
            item.st_size,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
            item.st_mtime_ns,
            sha256(path),
        )
    return result


def tree_identity(
    root: Path,
) -> tuple[str, list[dict[str, object]]]:
    files, _, symlinks, nonregular = scan(root)
    require(symlinks == 0 and nonregular == 0, "TREE_SPECIAL_PATH")
    entries: list[dict[str, object]] = []
    lines: list[str] = []
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        digest = sha256(path)
        mode = f"{stat.S_IMODE(item.st_mode):04o}"
        entry = {
            "relative_path": relative,
            "size_bytes": item.st_size,
            "mode": mode,
            "uid": item.st_uid,
            "gid": item.st_gid,
            "sha256": digest,
        }
        entries.append(entry)
        lines.append(
            f"{digest}  {item.st_size}  {mode}  "
            f"{item.st_uid}  {item.st_gid}  {relative}"
        )
    digest = hashlib.sha256(
        ("\n".join(lines) + "\n").encode("utf-8")
    ).hexdigest()
    return digest, entries


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_NOT_OBJECT:{path}")
    return value


def manifest_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("packet_files", "files", "artifacts", "candidate_files"):
        entries = value.get(key)
        if isinstance(entries, list):
            require(
                all(isinstance(entry, dict) for entry in entries),
                f"MANIFEST_ENTRY_TYPE:{key}",
            )
            return entries
    raise AssertionError("MANIFEST_ENTRY_LIST_NOT_FOUND")


def entry_name(entry: dict[str, Any]) -> str:
    for key in ("name", "relative_path", "path", "filename"):
        value = entry.get(key)
        if isinstance(value, str):
            return value
    raise AssertionError("MANIFEST_ENTRY_NAME_NOT_FOUND")


def read_text_manifest(root: Path) -> dict[str, str]:
    manifest_path = root / "evidence-manifest.txt"
    require(manifest_path.is_file(), f"EVIDENCE_MANIFEST_MISSING:{root}")
    mapping: dict[str, str] = {}
    for line_number, raw in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        require("  " in raw, f"EVIDENCE_MANIFEST_FORMAT:{line_number}")
        digest, relative = raw.split("  ", 1)
        require(
            relative not in mapping,
            f"EVIDENCE_MANIFEST_DUPLICATE:{relative}",
        )
        mapping[relative] = digest
    return mapping


def read_json_manifest(
    manifest_path: Path,
) -> dict[str, dict[str, Any]]:
    value = json_object(manifest_path)
    entries = manifest_entries(value)
    mapping: dict[str, dict[str, Any]] = {}
    for entry in entries:
        relative = entry_name(entry)
        require(
            relative not in mapping,
            f"JSON_MANIFEST_DUPLICATE:{relative}",
        )
        mapping[relative] = entry
    return mapping


def validate_evidence_manifest(
    root: Path,
    expected_count: int,
) -> dict[str, str]:
    files, _, symlinks, nonregular = scan(root)
    require(symlinks == 0, f"EVIDENCE_SYMLINK:{root}")
    require(nonregular == 0, f"EVIDENCE_NONREGULAR:{root}")
    mapping = read_text_manifest(root)
    require(
        len(mapping) == expected_count,
        f"EVIDENCE_MANIFEST_COUNT:{root}:{len(mapping)}",
    )
    require(
        set(mapping) == files - {"evidence-manifest.txt"},
        f"EVIDENCE_MANIFEST_EXACT_SET:{root}",
    )
    for relative, expected in mapping.items():
        require(
            sha256(root / relative) == expected,
            f"EVIDENCE_MANIFEST_SHA:{root}:{relative}",
        )
    return mapping


def validate_json_manifest(
    content_root: Path,
    manifest_relative: str,
    expected_count: int,
) -> dict[str, dict[str, Any]]:
    files, _, symlinks, nonregular = scan(content_root)
    require(symlinks == 0, f"JSON_MANIFEST_SYMLINK:{content_root}")
    require(nonregular == 0, f"JSON_MANIFEST_NONREGULAR:{content_root}")
    manifest_path = content_root / manifest_relative
    mapping = read_json_manifest(manifest_path)
    require(
        len(mapping) == expected_count,
        f"JSON_MANIFEST_COUNT:{manifest_path}:{len(mapping)}",
    )
    require(
        set(mapping) == files - {manifest_relative},
        f"JSON_MANIFEST_EXACT_SET:{manifest_path}",
    )
    for relative, entry in mapping.items():
        path = content_root / relative
        require(path.is_file(), f"JSON_MANIFEST_FILE_MISSING:{relative}")
        if "sha256" in entry:
            require(
                entry["sha256"] == sha256(path),
                f"JSON_MANIFEST_SHA:{manifest_path}:{relative}",
            )
        if "size_bytes" in entry:
            require(
                entry["size_bytes"] == path.stat().st_size,
                f"JSON_MANIFEST_SIZE:{manifest_path}:{relative}",
            )
    return mapping


for name, path in (
    ("EVIDENCE", EVIDENCE),
    ("SEALED_SOURCE", SEALED_SOURCE),
    ("CANDIDATE_SOURCE", CANDIDATE_SOURCE),
    ("FAILED_STAGING_1", FAILED_STAGING_1),
    ("FAILED_STAGING_2", FAILED_STAGING_2),
):
    require(path.is_relative_to(REPO), f"{name}_OUTSIDE_REPO")
    item = path.lstat()
    require(
        stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode),
        f"{name}_TYPE",
    )

evidence_identity_before = full_identity(EVIDENCE)
sealed_identity_before = full_identity(SEALED_SOURCE)
candidate_identity_before = full_identity(CANDIDATE_SOURCE)
failed_identity_before = tuple(
    full_identity(path) for path in FAILED_STAGINGS
)

print("===== R2 SEALED EVIDENCE EXACT STRUCTURE =====")

evidence_files, evidence_dirs, evidence_links, evidence_other = scan(EVIDENCE)
require(evidence_files == EXPECTED_EVIDENCE_FILES, "EVIDENCE_EXACT_FILE_SET")
require(
    evidence_dirs == EXPECTED_EVIDENCE_DIRECTORIES,
    "EVIDENCE_EXACT_DIRECTORY_SET",
)
require(evidence_links == 0, "EVIDENCE_SYMLINK_COUNT")
require(evidence_other == 0, "EVIDENCE_NONREGULAR_COUNT")
require(
    stat.S_IMODE(EVIDENCE.lstat().st_mode) == 0o555,
    "EVIDENCE_ROOT_MODE",
)
for relative in sorted(evidence_files):
    require(
        stat.S_IMODE((EVIDENCE / relative).lstat().st_mode) == 0o444,
        f"EVIDENCE_FILE_MODE:{relative}",
    )
for relative in sorted(evidence_dirs):
    require(
        stat.S_IMODE((EVIDENCE / relative).lstat().st_mode) == 0o555,
        f"EVIDENCE_DIRECTORY_MODE:{relative}",
    )

require(len(evidence_files) == 20, "EVIDENCE_FILE_COUNT")
require(len(evidence_dirs) == 1, "EVIDENCE_DIRECTORY_COUNT")
print("EVIDENCE_FILE_COUNT=20")
print("EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("EVIDENCE_EXACT_FILE_SET=PASS")
print("EVIDENCE_EXACT_DIRECTORY_SET=PASS")
print("SEALED_FILE_MODE=0444")
print("SEALED_DIRECTORY_MODE=0555")
print("EVIDENCE_SYMLINK_COUNT=0")
print("EVIDENCE_NONREGULAR_COUNT=0")

print("\n===== FIXED SHA REVIEW =====")

fixed_sha = {
    "result.json": EXPECTED_RESULT_SHA,
    "packet-snapshot/packet-manifest.json":
        EXPECTED_PACKET_MANIFEST_SHA,
    "packet-snapshot/execution-candidate-binding.json":
        EXPECTED_CANDIDATE_BINDING_SHA,
    "packet-snapshot/exact-command-contract.json":
        EXPECTED_COMMAND_CONTRACT_SHA,
    "packet-snapshot/final-execution-approval-token-template.json":
        EXPECTED_TOKEN_TEMPLATE_SHA,
    "evidence-manifest.txt": EXPECTED_EVIDENCE_MANIFEST_SHA,
}
for relative, expected in fixed_sha.items():
    require(
        sha256(EVIDENCE / relative) == expected,
        f"FIXED_SHA:{relative}",
    )
    print(f"FIXED_SHA_PASS={relative}")
print("FIXED_SHA_REVALIDATION=PASS")

print("\n===== EVIDENCE AND PACKET MANIFESTS =====")

evidence_map = validate_evidence_manifest(EVIDENCE, 19)
packet_root = EVIDENCE / "packet-snapshot"
packet_map = validate_json_manifest(
    packet_root,
    "packet-manifest.json",
    17,
)
require(
    set(packet_map) == EXPECTED_PACKET_PAYLOAD_FILES,
    "PACKET_EXPECTED_PAYLOAD_SET",
)
print("EVIDENCE_MANIFEST_ENTRY_COUNT=19")
print("EVIDENCE_MANIFEST_REVALIDATION=PASS")
print("PACKET_MANIFEST_ENTRY_COUNT=17")
print("PACKET_MANIFEST_REVALIDATION=PASS")
print("PACKET_EXPECTED_PAYLOAD_SET=PASS")

print("\n===== RESULT AND PACKET STATUS =====")

result = json_object(EVIDENCE / "result.json")
require(result.get("result") == EXPECTED_RESULT_TEXT, "RESULT_TEXT")
require(
    result.get("r2_runner_source_binding_correction_only") is True,
    "RESULT_R2_ONLY",
)
require(
    result.get("r1_python_only_staging_lifecycle_maintained") is True,
    "RESULT_R1_LIFECYCLE",
)
require(
    result.get("canonical_runner_source_binding") == "PASS",
    "RESULT_RUNNER_BINDING",
)
require(
    result.get("three_level_runner_manifest_binding") == "PASS",
    "RESULT_THREE_LEVEL_BINDING",
)
require(
    result.get("runner_candidate_manifest_revalidation") == "PASS",
    "RESULT_RUNNER_MANIFEST",
)
require(
    result.get("source_binding_record_schema_review") == "PASS",
    "RESULT_BINDING_SCHEMA",
)
require(
    result.get("source_binding_contract_literal_path_required") is False,
    "RESULT_LITERAL_PATH",
)
require(result.get("failed_staging_count") == 2, "RESULT_FAILED_STAGING_COUNT")
require(result.get("failed_staging_unchanged") is True, "RESULT_FAILED_STAGING")
require(
    result.get("candidate_source_identity_revalidation") == "PASS",
    "RESULT_CANDIDATE_SOURCE",
)
require(
    result.get("execution_evidence_file_count") == 65,
    "RESULT_EXECUTION_EVIDENCE_FILES",
)
require(
    result.get("execution_packet_file_count") == 63,
    "RESULT_EXECUTION_PACKET_FILES",
)
require(
    result.get("execution_packet_manifest_entry_count") == 62,
    "RESULT_EXECUTION_PACKET_ENTRIES",
)
require(
    result.get("execution_evidence_manifest_entry_count") == 64,
    "RESULT_EXECUTION_EVIDENCE_ENTRIES",
)
require(
    result.get("outer_and_execution_candidate_equivalence") == "PASS",
    "RESULT_CANDIDATE_EQUIVALENCE",
)
require(
    result.get("protected_sha_revalidation") == "PASS",
    "RESULT_PROTECTED_SHA",
)
require(
    result.get("target_state_inspected_during_preparation") is False,
    "RESULT_TARGET_INSPECTION",
)
require(
    result.get("final_execution_approval_packet_preparation_only") is True,
    "RESULT_PREPARATION_ONLY",
)
for key in (
    "final_execution_approval_issued",
    "final_execution_token_consumed",
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "corrected_wrapper_execution_allowed",
    "approval_binding_created",
    "one_shot_deployment_guard_created",
):
    require(result.get(key) is False, f"RESULT_FALSE_FLAG:{key}")
require(result.get("writer_freeze_execution") == "HOLD", "RESULT_WRITER_HOLD")
require(
    result.get("production_release_decision") == "HOLD",
    "RESULT_PRODUCTION_HOLD",
)
require(
    result.get("release_status") == "CANDIDATE_NOT_APPROVED",
    "RESULT_RELEASE_STATUS",
)
require(result.get("sealed") is True, "RESULT_SEALED")
require(result.get("seal_file_mode") == "0444", "RESULT_SEAL_FILE_MODE")
require(
    result.get("seal_directory_mode") == "0555",
    "RESULT_SEAL_DIRECTORY_MODE",
)

packet_manifest = json_object(packet_root / "packet-manifest.json")
require(
    packet_manifest.get("status")
    == (
        "FINAL_EXECUTION_APPROVAL_PACKET_R2_RUNNER_SOURCE_BINDING_"
        "CORRECTION_PREPARED_AND_SEALED_NO_EXECUTION"
    ),
    "PACKET_STATUS",
)
require(
    packet_manifest.get("r2_runner_source_binding_correction_only") is True,
    "PACKET_R2_ONLY",
)
require(
    packet_manifest.get("canonical_runner_source_binding") == "PASS",
    "PACKET_RUNNER_BINDING",
)
require(
    packet_manifest.get("three_level_runner_manifest_binding") == "PASS",
    "PACKET_THREE_LEVEL",
)
require(
    packet_manifest.get("reviewer_assumption_corrections_registered") is True,
    "PACKET_REVIEWER_CORRECTIONS",
)
require(packet_manifest.get("failed_staging_count") == 2, "PACKET_STAGING_COUNT")
require(
    packet_manifest.get("packet_file_count_excluding_manifest") == 17,
    "PACKET_FILE_COUNT",
)
require(
    packet_manifest.get("candidate_artifact_count") == 18,
    "PACKET_CANDIDATE_COUNT",
)
require(
    packet_manifest.get("target_directory_count") == 5,
    "PACKET_TARGET_DIRECTORY_COUNT",
)
require(
    packet_manifest.get("target_file_count") == 6,
    "PACKET_TARGET_FILE_COUNT",
)
require(
    packet_manifest.get("protected_sha_count") == 6,
    "PACKET_PROTECTED_COUNT",
)
require(
    packet_manifest.get("final_execution_approval_issued") is False,
    "PACKET_APPROVAL_ISSUED",
)
require(
    packet_manifest.get("final_execution_token_consumed") is False,
    "PACKET_TOKEN_CONSUMED",
)
require(
    packet_manifest.get("root_deployment_execution_allowed") is False,
    "PACKET_ROOT_EXECUTION",
)
require(
    packet_manifest.get("production_release_decision") == "HOLD",
    "PACKET_PRODUCTION_HOLD",
)
require(packet_manifest.get("sealed") is True, "PACKET_SEALED")
print("RESULT_SEMANTIC_REVIEW=PASS")
print("PACKET_STATUS_SEMANTIC_REVIEW=PASS")

print("\n===== SEALED HUMAN REVIEW SOURCE =====")

sealed_files, sealed_dirs, sealed_links, sealed_other = scan(SEALED_SOURCE)
require(sealed_files == SEALED_EXPECTED_FILES, "SEALED_SOURCE_FILE_SET")
require(sealed_dirs == SEALED_EXPECTED_DIRECTORIES, "SEALED_SOURCE_DIR_SET")
require(sealed_links == 0 and sealed_other == 0, "SEALED_SOURCE_SPECIAL")
require(
    stat.S_IMODE(SEALED_SOURCE.lstat().st_mode) == 0o555,
    "SEALED_SOURCE_ROOT_MODE",
)
for relative in sealed_files:
    require(
        stat.S_IMODE((SEALED_SOURCE / relative).lstat().st_mode) == 0o444,
        f"SEALED_SOURCE_FILE_MODE:{relative}",
    )
for relative in sealed_dirs:
    require(
        stat.S_IMODE((SEALED_SOURCE / relative).lstat().st_mode) == 0o555,
        f"SEALED_SOURCE_DIR_MODE:{relative}",
    )
for relative, expected in SEALED_FIXED_SHA.items():
    require(
        sha256(SEALED_SOURCE / relative) == expected,
        f"SEALED_SOURCE_FIXED_SHA:{relative}",
    )
sealed_evidence_map = validate_evidence_manifest(SEALED_SOURCE, 10)
sealed_packet_map = validate_json_manifest(
    SEALED_SOURCE / "packet-snapshot",
    "packet-manifest.json",
    8,
)
sealed_review_result = json_object(SEALED_SOURCE / "review-result.json")
require(
    sealed_review_result.get("human_review_result") == "PASS",
    "SEALED_HUMAN_REVIEW_RESULT",
)
require(sealed_review_result.get("sealed") is True, "SEALED_SOURCE_SEALED")
require(
    sealed_review_result.get("source_tree_identity_sha256")
    == CANDIDATE_SOURCE_TREE_SHA,
    "SEALED_SOURCE_TREE_BINDING",
)
require(
    sealed_review_result.get("root_deployment_execution_allowed") is False,
    "SEALED_SOURCE_ROOT_EXECUTION",
)
require(
    sealed_review_result.get("production_release_decision") == "HOLD",
    "SEALED_SOURCE_PRODUCTION_HOLD",
)
print("SEALED_REVIEW_EVIDENCE_FILE_COUNT=11")
print("SEALED_REVIEW_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("SEALED_REVIEW_EVIDENCE_MANIFEST_ENTRY_COUNT=10")
print("SEALED_REVIEW_PACKET_MANIFEST_ENTRY_COUNT=8")
print("SEALED_REVIEW_EVIDENCE_REVALIDATION=PASS")

print("\n===== CANDIDATE SOURCE IDENTITY =====")

candidate_files, candidate_dirs, candidate_links, candidate_other = scan(
    CANDIDATE_SOURCE
)
require(len(candidate_files) == 245, "CANDIDATE_SOURCE_FILE_COUNT")
require(len(candidate_dirs) == 46, "CANDIDATE_SOURCE_DIRECTORY_COUNT")
require(
    candidate_links == 0 and candidate_other == 0,
    "CANDIDATE_SOURCE_SPECIAL",
)
for relative, expected in CANDIDATE_SOURCE_FIXED_SHA.items():
    require(
        sha256(CANDIDATE_SOURCE / relative) == expected,
        f"CANDIDATE_SOURCE_FIXED_SHA:{relative}",
    )
candidate_tree_sha, candidate_tree_entries = tree_identity(CANDIDATE_SOURCE)
require(
    candidate_tree_sha == CANDIDATE_SOURCE_TREE_SHA,
    "CANDIDATE_SOURCE_TREE_IDENTITY",
)
print("CANDIDATE_SOURCE_FILE_COUNT=245")
print("CANDIDATE_SOURCE_DIRECTORY_COUNT_EXCLUDING_ROOT=46")
print(f"CANDIDATE_SOURCE_TREE_IDENTITY_SHA256={candidate_tree_sha}")
print("CANDIDATE_SOURCE_IDENTITY_REVALIDATION=PASS")

print("\n===== EXECUTION EVIDENCE AND CANDIDATE ARTIFACTS =====")

execution_evidence = CANDIDATE_SOURCE / EXECUTION_EVIDENCE_REL
execution_packet = execution_evidence / "packet-snapshot"
outer_candidate = CANDIDATE_SOURCE / OUTER_CANDIDATE_REL
execution_candidate = CANDIDATE_SOURCE / EXECUTION_CANDIDATE_REL
runner_root = CANDIDATE_SOURCE / CANONICAL_RUNNER_REL

execution_files, execution_dirs, execution_links, execution_other = scan(
    execution_evidence
)
require(len(execution_files) == 65, "EXECUTION_EVIDENCE_FILE_COUNT")
require(len(execution_dirs) == 12, "EXECUTION_EVIDENCE_DIR_COUNT")
require(
    execution_links == 0 and execution_other == 0,
    "EXECUTION_EVIDENCE_SPECIAL",
)
execution_evidence_map = validate_evidence_manifest(execution_evidence, 64)

execution_packet_files, execution_packet_dirs, packet_links, packet_other = scan(
    execution_packet
)
require(len(execution_packet_files) == 63, "EXECUTION_PACKET_FILE_COUNT")
require(len(execution_packet_dirs) == 11, "EXECUTION_PACKET_DIR_COUNT")
require(packet_links == 0 and packet_other == 0, "EXECUTION_PACKET_SPECIAL")
execution_packet_map = validate_json_manifest(
    execution_packet,
    "packet-manifest.json",
    62,
)

outer_files, outer_dirs, outer_links, outer_other = scan(outer_candidate)
nested_files, nested_dirs, nested_links, nested_other = scan(
    execution_candidate
)
require(len(outer_files) == 18, "OUTER_CANDIDATE_FILE_COUNT")
require(len(nested_files) == 18, "EXECUTION_CANDIDATE_FILE_COUNT")
require(len(outer_dirs) == 0, "OUTER_CANDIDATE_DIRECTORY_COUNT")
require(len(nested_dirs) == 0, "EXECUTION_CANDIDATE_DIRECTORY_COUNT")
require(
    outer_links == 0 and outer_other == 0,
    "OUTER_CANDIDATE_SPECIAL",
)
require(
    nested_links == 0 and nested_other == 0,
    "EXECUTION_CANDIDATE_SPECIAL",
)
require(outer_files == nested_files, "CANDIDATE_FILE_SET_EQUIVALENCE")
for relative in sorted(outer_files):
    outer_path = outer_candidate / relative
    nested_path = execution_candidate / relative
    require(
        sha256(outer_path) == sha256(nested_path),
        f"CANDIDATE_SHA_EQUIVALENCE:{relative}",
    )
    require(
        outer_path.stat().st_size == nested_path.stat().st_size,
        f"CANDIDATE_SIZE_EQUIVALENCE:{relative}",
    )

outer_candidate_map = validate_json_manifest(
    outer_candidate,
    "candidate-manifest.json",
    17,
)
execution_candidate_map = validate_json_manifest(
    execution_candidate,
    "candidate-manifest.json",
    17,
)
require(
    set(outer_candidate_map) == set(execution_candidate_map),
    "CANDIDATE_MANIFEST_SET_EQUIVALENCE",
)
for relative, expected in CRITICAL_CANDIDATE_SHA.items():
    require(
        sha256(execution_candidate / relative) == expected,
        f"CRITICAL_CANDIDATE_SHA:{relative}",
    )

print("EXECUTION_EVIDENCE_FILE_COUNT=65")
print("EXECUTION_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=12")
print("EXECUTION_EVIDENCE_MANIFEST_ENTRY_COUNT=64")
print("EXECUTION_PACKET_FILE_COUNT=63")
print("EXECUTION_PACKET_DIRECTORY_COUNT_EXCLUDING_ROOT=11")
print("EXECUTION_PACKET_MANIFEST_ENTRY_COUNT=62")
print("CANDIDATE_ARTIFACT_COUNT=18")
print("CANDIDATE_MANIFEST_ENTRY_COUNT=17")
print("CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("OUTER_AND_EXECUTION_CANDIDATE_EQUIVALENCE=PASS")
print("CORRECTED_WRAPPER_EXECUTED=false")

print("\n===== CANONICAL RUNNER AND THREE-LEVEL BINDING =====")

runner_files, runner_dirs, runner_links, runner_other = scan(runner_root)
require(len(runner_files) == 7, "RUNNER_FILE_COUNT")
require(len(runner_dirs) == 0, "RUNNER_DIRECTORY_COUNT")
require(runner_links == 0 and runner_other == 0, "RUNNER_SPECIAL")
require(
    sha256(runner_root / "candidate-manifest.json")
    == RUNNER_CANDIDATE_MANIFEST_SHA,
    "RUNNER_CANDIDATE_MANIFEST_SHA",
)
runner_map = validate_json_manifest(
    runner_root,
    "candidate-manifest.json",
    6,
)
require(set(runner_map) == set(RUNNER_PAYLOAD_SHA), "RUNNER_EXACT_PAYLOAD_SET")
for filename, expected in RUNNER_PAYLOAD_SHA.items():
    path = runner_root / filename
    require(path.is_file(), f"RUNNER_FILE_MISSING:{filename}")
    require(sha256(path) == expected, f"RUNNER_FIXED_SHA:{filename}")
    entry = runner_map[filename]
    require(entry.get("sha256") == expected, f"RUNNER_MANIFEST_SHA:{filename}")
    require(
        entry.get("size_bytes") == path.stat().st_size,
        f"RUNNER_MANIFEST_SIZE:{filename}",
    )

    packet_relative = (
        "source-partial-evidence-snapshot/packet-snapshot/"
        f"deployment-input-snapshot/runner-candidate/{filename}"
    )
    evidence_relative = f"packet-snapshot/{packet_relative}"
    require(
        packet_relative in execution_packet_map,
        f"THREE_LEVEL_PACKET_BINDING:{filename}",
    )
    require(
        evidence_relative in execution_evidence_map,
        f"THREE_LEVEL_EVIDENCE_BINDING:{filename}",
    )
    packet_entry = execution_packet_map[packet_relative]
    require(
        packet_entry.get("sha256") == expected,
        f"THREE_LEVEL_PACKET_SHA:{filename}",
    )
    require(
        packet_entry.get("size_bytes") == path.stat().st_size,
        f"THREE_LEVEL_PACKET_SIZE:{filename}",
    )
    require(
        execution_evidence_map[evidence_relative] == expected,
        f"THREE_LEVEL_EVIDENCE_SHA:{filename}",
    )

source_binding_path = (
    execution_candidate / "source-binding-contract.json"
)
partial_inventory_path = (
    execution_candidate / "partial-source-inventory.json"
)
require(
    sha256(source_binding_path) == SOURCE_BINDING_CONTRACT_SHA,
    "SOURCE_BINDING_CONTRACT_SHA",
)
require(
    sha256(partial_inventory_path) == PARTIAL_SOURCE_INVENTORY_SHA,
    "PARTIAL_SOURCE_INVENTORY_SHA",
)

source_binding = json_object(source_binding_path)
runner_candidate_record = source_binding.get("runner_candidate")
require(
    isinstance(runner_candidate_record, dict),
    "SOURCE_BINDING_RUNNER_OBJECT",
)
require(
    runner_candidate_record.get("fixed_file_count") == 7,
    "SOURCE_BINDING_RUNNER_COUNT",
)
fixed_runner_sha = runner_candidate_record.get("fixed_sha256")
require(
    isinstance(fixed_runner_sha, dict),
    "SOURCE_BINDING_FIXED_SHA_OBJECT",
)
require(
    fixed_runner_sha.get("candidate-manifest.json")
    == RUNNER_CANDIDATE_MANIFEST_SHA,
    "SOURCE_BINDING_RUNNER_MANIFEST_SHA",
)
for filename, expected in RUNNER_PAYLOAD_SHA.items():
    require(
        fixed_runner_sha.get(filename) == expected,
        f"SOURCE_BINDING_RUNNER_SHA:{filename}",
    )

partial_inventory = json_object(partial_inventory_path)
partial_file_entries = partial_inventory.get("files")
require(isinstance(partial_file_entries, list), "PARTIAL_INVENTORY_FILES")
partial_map: dict[str, dict[str, Any]] = {}
for entry in partial_file_entries:
    require(isinstance(entry, dict), "PARTIAL_INVENTORY_ENTRY")
    relative = entry.get("relative_path")
    require(isinstance(relative, str), "PARTIAL_INVENTORY_PATH")
    require(
        relative not in partial_map,
        f"PARTIAL_INVENTORY_DUPLICATE:{relative}",
    )
    partial_map[relative] = entry
for filename, expected in RUNNER_PAYLOAD_SHA.items():
    relative = (
        "packet-snapshot/deployment-input-snapshot/"
        f"runner-candidate/{filename}"
    )
    require(relative in partial_map, f"PARTIAL_RUNNER_PATH:{filename}")
    require(
        partial_map[relative].get("sha256") == expected,
        f"PARTIAL_RUNNER_SHA:{filename}",
    )

print(f"CANONICAL_RUNNER_ROOT={CANONICAL_RUNNER_REL}")
print("CANONICAL_RUNNER_SOURCE_BINDING=PASS")
print("RUNNER_CANDIDATE_FILE_COUNT=7")
print("RUNNER_CANDIDATE_MANIFEST_ENTRY_COUNT=6")
print("RUNNER_CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("THREE_LEVEL_RUNNER_MANIFEST_BINDING=PASS")
print("SOURCE_BINDING_RECORD_SCHEMA_REVIEW=PASS")
print("SOURCE_BINDING_CONTRACT_LITERAL_PATH_REQUIRED=false")

print("\n===== R2 CORRECTION RECORDS =====")

runner_correction = json_object(
    packet_root / "runner-source-binding-correction.json"
)
require(
    runner_correction.get("correction_scope") == "RUNNER_SOURCE_BINDING_ONLY",
    "RUNNER_CORRECTION_SCOPE",
)
require(
    runner_correction.get("canonical_runner_source_relative_path")
    == CANONICAL_RUNNER_REL,
    "RUNNER_CORRECTION_PATH",
)
require(
    runner_correction.get("execution_candidate_relative_path")
    == EXECUTION_CANDIDATE_REL,
    "RUNNER_CORRECTION_CANDIDATE_PATH",
)
require(
    runner_correction.get("execution_evidence_file_count") == 65,
    "RUNNER_CORRECTION_EVIDENCE_COUNT",
)
require(
    runner_correction.get("execution_evidence_manifest_entry_count") == 64,
    "RUNNER_CORRECTION_EVIDENCE_MANIFEST",
)
require(
    runner_correction.get("execution_packet_file_count") == 63,
    "RUNNER_CORRECTION_PACKET_COUNT",
)
require(
    runner_correction.get("execution_packet_manifest_entry_count") == 62,
    "RUNNER_CORRECTION_PACKET_MANIFEST",
)
require(
    runner_correction.get("runner_candidate_file_count") == 7,
    "RUNNER_CORRECTION_RUNNER_COUNT",
)
require(
    runner_correction.get("runner_candidate_manifest_entry_count") == 6,
    "RUNNER_CORRECTION_RUNNER_MANIFEST",
)
require(
    runner_correction.get("runner_candidate_manifest_sha256")
    == RUNNER_CANDIDATE_MANIFEST_SHA,
    "RUNNER_CORRECTION_RUNNER_MANIFEST_SHA",
)
require(
    runner_correction.get("three_level_runner_manifest_binding") == "PASS",
    "RUNNER_CORRECTION_THREE_LEVEL",
)
require(
    runner_correction.get("source_binding_contract_literal_path_required")
    is False,
    "RUNNER_CORRECTION_LITERAL_PATH",
)
for key in (
    "candidate_code_changed",
    "corrected_wrapper_changed",
    "corrected_wrapper_executed",
):
    require(runner_correction.get(key) is False, f"RUNNER_CORRECTION_FLAG:{key}")

reviewer_corrections = json_object(
    packet_root / "reviewer-assumption-corrections.json"
)
require(
    reviewer_corrections.get("initial_reviewer_error_was_packet_defect")
    is False,
    "REVIEWER_CORRECTION_PACKET_DEFECT",
)
corrections = reviewer_corrections.get("corrections")
require(isinstance(corrections, list), "REVIEWER_CORRECTION_LIST")
require(len(corrections) == 3, "REVIEWER_CORRECTION_COUNT")
expected_error_classes = {
    "REVIEWER_PARTIAL_SNAPSHOT_ROOT_TYPE_ASSUMPTION",
    "REVIEWER_EXTRA_INTERMEDIATE_PACKET_MANIFEST_ASSUMPTION",
    "REVIEWER_BINDING_RECORD_SCHEMA_ASSUMPTION",
}
actual_error_classes = {
    item.get("error_class")
    for item in corrections
    if isinstance(item, dict)
}
require(
    actual_error_classes == expected_error_classes,
    "REVIEWER_CORRECTION_EXACT_CLASSES",
)
for item in corrections:
    require(isinstance(item, dict), "REVIEWER_CORRECTION_OBJECT")
    require(item.get("packet_defect") is False, "REVIEWER_PACKET_DEFECT_FLAG")
for key in (
    "reviewer_root_type_correction_registered",
    "reviewer_intermediate_manifest_correction_registered",
    "reviewer_binding_schema_correction_registered",
):
    require(reviewer_corrections.get(key) is True, f"REVIEWER_FLAG:{key}")

print("RUNNER_SOURCE_BINDING_CORRECTION_RECORD=PASS")
print("REVIEWER_ASSUMPTION_CORRECTION_COUNT=3")
print("REVIEWER_ROOT_TYPE_CORRECTION_REGISTERED=true")
print("REVIEWER_INTERMEDIATE_MANIFEST_CORRECTION_REGISTERED=true")
print("REVIEWER_BINDING_SCHEMA_CORRECTION_REGISTERED=true")
print("INITIAL_REVIEWER_ERROR_WAS_PACKET_DEFECT=false")

print("\n===== FAILED STAGING IMMUTABILITY =====")

expected_failed = (
    {
        "mode": 0o750,
        "uid": 1001,
        "gid": 1001,
        "mtime_ns": 1785061400585610693,
        "failure_class": "STAGING_LIFECYCLE_CONTRACT_CONTRADICTION",
        "failure_marker": "STAGING_PATH_ENTRY_EXISTS",
    },
    {
        "mode": 0o750,
        "uid": 1001,
        "gid": 1001,
        "mtime_ns": 1785063834302475917,
        "failure_class": "EXECUTION_RUNNER_SOURCE_PATH_BINDING_MISMATCH",
        "failure_marker": "FileNotFoundError",
    },
)
failed_inventory = json_object(
    packet_root / "failed-staging-inventory.json"
)
require(failed_inventory.get("failed_staging_count") == 2, "STAGING_RECORD_COUNT")
require(failed_inventory.get("readonly_inventory") == "PASS", "STAGING_RECORD_REVIEW")
require(
    failed_inventory.get("failed_staging_mutation") is False,
    "STAGING_RECORD_MUTATION",
)
records = failed_inventory.get("records")
require(isinstance(records, list), "STAGING_RECORD_LIST")
require(len(records) == 2, "STAGING_RECORD_LIST_COUNT")

for index, (root, expected, record) in enumerate(
    zip(FAILED_STAGINGS, expected_failed, records),
    start=1,
):
    require(isinstance(record, dict), f"STAGING_RECORD_OBJECT:{index}")
    item = root.lstat()
    files, directories, links, other = scan(root)
    require(
        stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode),
        f"FAILED_STAGING_TYPE:{index}",
    )
    require(
        stat.S_IMODE(item.st_mode) == expected["mode"],
        f"FAILED_STAGING_MODE:{index}",
    )
    require(item.st_uid == expected["uid"], f"FAILED_STAGING_UID:{index}")
    require(item.st_gid == expected["gid"], f"FAILED_STAGING_GID:{index}")
    require(
        item.st_mtime_ns == expected["mtime_ns"],
        f"FAILED_STAGING_MTIME:{index}",
    )
    require(len(files) == 0, f"FAILED_STAGING_FILES:{index}")
    require(len(directories) == 0, f"FAILED_STAGING_DIRS:{index}")
    require(links == 0, f"FAILED_STAGING_LINKS:{index}")
    require(other == 0, f"FAILED_STAGING_OTHER:{index}")
    require(record.get("index") == index, f"STAGING_RECORD_INDEX:{index}")
    require(
        record.get("relative_path") == root.relative_to(REPO).as_posix(),
        f"STAGING_RECORD_PATH:{index}",
    )
    require(
        record.get("failure_class") == expected["failure_class"],
        f"STAGING_RECORD_FAILURE_CLASS:{index}",
    )
    require(
        record.get("failure_marker") == expected["failure_marker"],
        f"STAGING_RECORD_FAILURE_MARKER:{index}",
    )
    require(record.get("mode") == "0750", f"STAGING_RECORD_MODE:{index}")
    require(record.get("uid") == 1001, f"STAGING_RECORD_UID:{index}")
    require(record.get("gid") == 1001, f"STAGING_RECORD_GID:{index}")
    require(
        record.get("mtime_ns") == expected["mtime_ns"],
        f"STAGING_RECORD_MTIME:{index}",
    )
    require(record.get("file_count") == 0, f"STAGING_RECORD_FILES:{index}")
    require(
        record.get("directory_count_excluding_root") == 0,
        f"STAGING_RECORD_DIRS:{index}",
    )
    require(record.get("symlink_count") == 0, f"STAGING_RECORD_LINKS:{index}")
    require(
        record.get("nonregular_count") == 0,
        f"STAGING_RECORD_OTHER:{index}",
    )
    require(
        record.get("immutable_partial_failure_record") is True,
        f"STAGING_RECORD_IMMUTABLE:{index}",
    )
    print(f"FAILED_STAGING_{index}_IDENTITY=PASS")
    print(f"FAILED_STAGING_{index}_EMPTY=true")

print("FAILED_STAGING_COUNT=2")
print("FAILED_STAGING_UNCHANGED=true")

print("\n===== PROTECTED PRODUCTION SHA =====")

protected_contract = json_object(
    packet_root / "protected-sha-contract.json"
)
require(
    protected_contract.get("protected_sha256") == PROTECTED_SHA,
    "PROTECTED_CONTRACT_EXACT_SET",
)
require(
    protected_contract.get("revalidation_result") == "PASS",
    "PROTECTED_CONTRACT_RESULT",
)
require(
    protected_contract.get("database_connection_performed") is False,
    "PROTECTED_DATABASE_CONNECTION",
)
require(
    protected_contract.get("sql_performed") is False,
    "PROTECTED_SQL",
)
require(
    protected_contract.get("production_manifest_changed") is False,
    "PROTECTED_MANIFEST_CHANGE",
)
for relative, expected in PROTECTED_SHA.items():
    path = REPO / relative
    require(path.is_file(), f"PROTECTED_FILE_MISSING:{relative}")
    require(
        not path.is_symlink(),
        f"PROTECTED_FILE_SYMLINK:{relative}",
    )
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")
print("PROTECTED_SHA_COUNT=6")
print("PROTECTED_SHA_REVALIDATION=PASS")
print("DATABASE_CONNECTION_PERFORMED=false")
print("SQL_PERFORMED=false")
print("PRODUCTION_MANIFEST_CHANGED=false")

print("\n===== SAFETY CONTRACTS =====")

candidate_binding = json_object(
    packet_root / "execution-candidate-binding.json"
)
require(
    candidate_binding.get("candidate_source_tree_identity_sha256")
    == CANDIDATE_SOURCE_TREE_SHA,
    "BINDING_CANDIDATE_TREE_SHA",
)
require(
    candidate_binding.get("candidate_source_file_count") == 245,
    "BINDING_CANDIDATE_FILE_COUNT",
)
require(
    candidate_binding.get("candidate_source_directory_count_excluding_root")
    == 46,
    "BINDING_CANDIDATE_DIR_COUNT",
)
require(
    candidate_binding.get("execution_evidence_file_count") == 65,
    "BINDING_EXECUTION_EVIDENCE_COUNT",
)
require(
    candidate_binding.get("execution_packet_file_count") == 63,
    "BINDING_EXECUTION_PACKET_COUNT",
)
require(
    candidate_binding.get("candidate_artifact_count") == 18,
    "BINDING_CANDIDATE_ARTIFACT_COUNT",
)
require(
    candidate_binding.get("candidate_manifest_entry_count") == 17,
    "BINDING_CANDIDATE_ENTRY_COUNT",
)
require(
    candidate_binding.get("canonical_runner_source_relative_path")
    == CANONICAL_RUNNER_REL,
    "BINDING_CANONICAL_RUNNER_PATH",
)
require(
    candidate_binding.get("three_level_runner_manifest_binding") == "PASS",
    "BINDING_THREE_LEVEL",
)
require(
    candidate_binding.get("source_binding_contract_literal_path_required")
    is False,
    "BINDING_LITERAL_PATH",
)
require(
    candidate_binding.get("candidate_source_unchanged") is True,
    "BINDING_CANDIDATE_UNCHANGED",
)
require(
    candidate_binding.get("corrected_wrapper_executed") is False,
    "BINDING_WRAPPER_EXECUTED",
)

seal_contract = json_object(packet_root / "seal-contract.json")
require(seal_contract.get("staging_required") is True, "SEAL_STAGING_REQUIRED")
require(
    seal_contract.get("file_mode_after_seal") == "0444",
    "SEAL_FILE_MODE",
)
require(
    seal_contract.get("directory_mode_after_seal") == "0555",
    "SEAL_DIRECTORY_MODE",
)
require(
    seal_contract.get("final_promotion")
    == "renameat2(RENAME_NOREPLACE)",
    "SEAL_FINAL_PROMOTION",
)
require(
    seal_contract.get("source_evidence_mutation_allowed") is False,
    "SEAL_SOURCE_MUTATION",
)
require(
    seal_contract.get("candidate_source_mutation_allowed") is False,
    "SEAL_CANDIDATE_MUTATION",
)
require(
    seal_contract.get("root_deployment_execution_allowed") is False,
    "SEAL_ROOT_EXECUTION",
)
require(
    seal_contract.get("production_release_decision") == "HOLD",
    "SEAL_PRODUCTION_HOLD",
)

preflight = json_object(
    packet_root / "preflight-path-state-contract.json"
)
require(
    preflight.get("target_state_inspected_during_preparation") is False,
    "PREFLIGHT_TARGET_INSPECTED",
)
require(
    preflight.get(
        "target_state_verification_deferred_to_final_execution_preflight"
    ) is True,
    "PREFLIGHT_TARGET_DEFERRED",
)
require(
    preflight.get("protected_sha_revalidation_before_guard_required") is True,
    "PREFLIGHT_PROTECTED_SHA",
)
require(
    preflight.get("evidence_manifest_revalidation_before_guard_required")
    is True,
    "PREFLIGHT_EVIDENCE_MANIFEST",
)
require(
    preflight.get(
        "renameat2_rename_noreplace_availability_before_guard_required"
    ) is True,
    "PREFLIGHT_RENAME_NOREPLACE",
)
require(
    preflight.get("production_release_must_remain_hold") is True,
    "PREFLIGHT_PRODUCTION_HOLD",
)

rollback = json_object(packet_root / "rollback-stop-contract.json")
require(
    rollback.get("rollback_scope") == "CURRENT_TRANSACTION_CREATED_PATHS_ONLY",
    "ROLLBACK_SCOPE",
)
require(
    rollback.get("automatic_retry_allowed") is False,
    "ROLLBACK_RETRY",
)
require(rollback.get("max_execution_attempts") == 1, "ROLLBACK_MAX_ATTEMPTS")
require(
    rollback.get("guard_removal_allowed") is False,
    "ROLLBACK_GUARD_REMOVAL",
)
require(
    rollback.get("existing_path_removal_allowed") is False,
    "ROLLBACK_EXISTING_PATH",
)
require(
    rollback.get("production_release_after_success") == "HOLD",
    "ROLLBACK_PRODUCTION_HOLD",
)

command_contract = json_object(
    packet_root / "exact-command-contract.json"
)
require(
    command_contract.get("current_phase_execution_allowed") is False,
    "COMMAND_CURRENT_EXECUTION",
)
require(
    command_contract.get("future_command_requires_separate_final_human_approval")
    is True,
    "COMMAND_FUTURE_APPROVAL",
)
require(
    command_contract.get("future_command_requires_valid_approval_binding")
    is True,
    "COMMAND_APPROVAL_BINDING",
)
require(command_contract.get("shell") is False, "COMMAND_SHELL")
require(
    command_contract.get("arbitrary_arguments_allowed") is False,
    "COMMAND_ARBITRARY_ARGS",
)
require(
    command_contract.get("wrapper_sha256")
    == CRITICAL_CANDIDATE_SHA["root_deployment_execution_once_r1.py"],
    "COMMAND_WRAPPER_SHA",
)
require(
    command_contract.get("root_helper_executed_by_wrapper") is False,
    "COMMAND_ROOT_HELPER",
)
require(
    command_contract.get("runner_executed_by_wrapper") is False,
    "COMMAND_RUNNER",
)
require(
    command_contract.get("production_release_after_wrapper") == "HOLD",
    "COMMAND_PRODUCTION_HOLD",
)

token_template = json_object(
    packet_root / "final-execution-approval-token-template.json"
)
require(token_template.get("template_only") is True, "TOKEN_TEMPLATE_ONLY")
require(token_template.get("valid_approval") is False, "TOKEN_VALID_APPROVAL")
require(
    token_template.get("final_execution_approval_issued") is False,
    "TOKEN_APPROVAL_ISSUED",
)
require(
    token_template.get("final_execution_token_consumed") is False,
    "TOKEN_CONSUMED",
)
require(
    token_template.get("literal_presence_does_not_issue_approval") is True,
    "TOKEN_LITERAL_APPROVAL",
)
require(
    token_template.get("requires_new_explicit_human_message") is True,
    "TOKEN_NEW_HUMAN_MESSAGE",
)
require(
    token_template.get("requires_valid_root_owned_approval_binding") is True,
    "TOKEN_ROOT_BINDING",
)
require(
    token_template.get("do_not_execute_from_this_template") is True,
    "TOKEN_DO_NOT_EXECUTE",
)

approval_values = json_object(
    packet_root / "approval-binding-required-values.json"
)
require(approval_values.get("template_only") is True, "BINDING_TEMPLATE_ONLY")
require(approval_values.get("binding_created") is False, "BINDING_CREATED")
require(
    approval_values.get("requires_separate_human_approval") is True,
    "BINDING_SEPARATE_APPROVAL",
)
require(
    approval_values.get("current_packet_may_create_binding") is False,
    "BINDING_CURRENT_PACKET_CREATE",
)
require(
    approval_values.get("max_execution_attempts") == 1,
    "BINDING_MAX_ATTEMPTS",
)

target_layout = json_object(packet_root / "target-layout.json")
require(
    target_layout.get("target_state_inspected") is False,
    "TARGET_LAYOUT_INSPECTED",
)
require(
    target_layout.get("target_state_inspection_allowed_current_phase") is False,
    "TARGET_LAYOUT_INSPECTION_ALLOWED",
)
require(
    target_layout.get("target_directory_count") == 5,
    "TARGET_LAYOUT_DIRECTORY_COUNT",
)
require(
    target_layout.get("target_file_count") == 6,
    "TARGET_LAYOUT_FILE_COUNT",
)
require(
    target_layout.get("root_deployment_execution_allowed") is False,
    "TARGET_LAYOUT_EXECUTION",
)

print("TARGET_LAYOUT_REGISTERED=true")
print("TARGET_STATE_INSPECTED_DURING_REVIEW=false")
print("TARGET_STATE_INSPECTION_ALLOWED=false")
print("ROLLBACK_STOP_CONTRACT_REVALIDATION=PASS")
print("EXACT_COMMAND_CONTRACT_REVALIDATION=PASS")
print("TOKEN_TEMPLATE_REVALIDATION=PASS")
print("APPROVAL_BINDING_TEMPLATE_REVALIDATION=PASS")
print("SEAL_CONTRACT_REVALIDATION=PASS")
print("FINAL_PROMOTION=RENAMEAT2_RENAME_NOREPLACE")

print("\n===== READONLY INVARIANCE =====")

require(
    full_identity(EVIDENCE) == evidence_identity_before,
    "EVIDENCE_CHANGED_DURING_REVIEW",
)
require(
    full_identity(SEALED_SOURCE) == sealed_identity_before,
    "SEALED_SOURCE_CHANGED_DURING_REVIEW",
)
require(
    full_identity(CANDIDATE_SOURCE) == candidate_identity_before,
    "CANDIDATE_SOURCE_CHANGED_DURING_REVIEW",
)
for index, (root, expected_identity) in enumerate(
    zip(FAILED_STAGINGS, failed_identity_before),
    start=1,
):
    require(
        full_identity(root) == expected_identity,
        f"FAILED_STAGING_CHANGED_DURING_REVIEW:{index}",
    )

require(not list(EVIDENCE.rglob("*.pyc")), "EVIDENCE_BYTECODE")
require(not list(SEALED_SOURCE.rglob("*.pyc")), "SEALED_SOURCE_BYTECODE")
require(not list(CANDIDATE_SOURCE.rglob("*.pyc")), "CANDIDATE_SOURCE_BYTECODE")

print("EVIDENCE_MUTATION=false")
print("SEALED_SOURCE_MUTATION=false")
print("CANDIDATE_SOURCE_MUTATION=false")
print("FAILED_STAGING_MUTATION=false")
print("BYTECODE_SIDE_EFFECT=false")

print("\n===== FINAL READONLY REVIEW RESULT =====")

print(
    "ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_PACKET_"
    "R2_SEAL_READONLY_REVIEW=PASS"
)
print("SEAL_REVIEW_READONLY_ONLY=true")
print("R2_RUNNER_SOURCE_BINDING_CORRECTION_ONLY=true")
print("EVIDENCE_EXACT_STRUCTURE_REVALIDATION=PASS")
print("EVIDENCE_AND_PACKET_MANIFEST_REVALIDATION=PASS")
print("CANONICAL_RUNNER_SOURCE_BINDING=PASS")
print("THREE_LEVEL_RUNNER_MANIFEST_BINDING=PASS")
print("OUTER_AND_EXECUTION_CANDIDATE_EQUIVALENCE=PASS")
print("REVIEWER_ASSUMPTION_CORRECTIONS=PASS")
print("FAILED_STAGING_IMMUTABILITY=PASS")
print("PROTECTED_SHA_REVALIDATION=PASS")
print("SEALED_SOURCE_REVALIDATION=PASS")
print("CANDIDATE_SOURCE_REVALIDATION=PASS")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("CORRECTED_WRAPPER_EXECUTION_ALLOWED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("FINAL_EXECUTION_APPROVAL_ISSUED=false")
print("FINAL_EXECUTION_TOKEN_CONSUMED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
PY

printf 'R2_SEAL_READONLY_REVIEW_EXIT_CODE=%s\n' "$?"
