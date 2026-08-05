#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
PACKET_REL="${BASE_REL}/i2f3e-j-final-seal-acceptance-root-deployment-packet-preparation-20260726T045508Z-528388"
PACKET_EVIDENCE_ROOT="${REPO_ROOT}/${PACKET_REL}"
PACKET_ROOT="${PACKET_EVIDENCE_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
INPUT_ROOT="${PACKET_ROOT}/deployment-input-snapshot"
FINAL_INPUT_ROOT="${INPUT_ROOT}/final-seal-evidence"
RUNNER_INPUT_ROOT="${INPUT_ROOT}/runner-candidate"
LOG_ROOT="${PACKET_ROOT}/validation-logs"

FINAL_SEAL_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-final-evidence-registration-and-seal-20260726T035208Z-527505"
FINAL_SEAL_ROOT="${REPO_ROOT}/${FINAL_SEAL_REL}"

RUNNER_SOURCE_REL="${BASE_REL}/i2f3e-j-r1-root-scan-late-exit-correction-blocked-no-execution-20260725T161929Z-515154/packet-snapshot/candidate-artifacts"
RUNNER_SOURCE_ROOT="${REPO_ROOT}/${RUNNER_SOURCE_REL}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_REVIEW_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

for path in \
  "$PYTHON_BIN" \
  "$PACKET_EVIDENCE_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$INPUT_ROOT" \
  "$FINAL_INPUT_ROOT" \
  "$RUNNER_INPUT_ROOT" \
  "$LOG_ROOT" \
  "$FINAL_SEAL_ROOT" \
  "$RUNNER_SOURCE_ROOT"
do
  test -e "$path"
done

cd "$REPO_ROOT"

printf '\n===== ROOT DEPLOYMENT PACKET FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
07951222582d6dda8ae07bcef6cd920db0d7cbdf22b20b39e48593cf716f9e6f  ${PACKET_EVIDENCE_ROOT}/result.json
fae7a17137d4283d144bd3ac5352de80653adac6480c6db0e0eb776e6df3b267  ${PACKET_ROOT}/packet-manifest.json
10c5aa0b9e53bd6ed03c8a89ac99c6b87d7fc4ed00fe45dca7ccbe7939336748  ${CANDIDATE_ROOT}/candidate-manifest.json
29dca2ef58e72b40cbec06581d86d28d49b5ccc0a1a239316eebc3c380159d9c  ${PACKET_EVIDENCE_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== SOURCE FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
c9d71a2969a2ddf2a710f9e45c60327e42b5257994d613477c0ee724694d3bba  ${FINAL_SEAL_ROOT}/result.json
700a572496fb3d3c61235da276fbe668afb1a8bdf576040885f6fb07eac502c2  ${FINAL_SEAL_ROOT}/packet-snapshot/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${FINAL_SEAL_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${FINAL_SEAL_ROOT}/packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json
0c674bd9a7ea654bec9acea38a41b03a990d8dbf52b63dea23bb2562662f6d20  ${FINAL_SEAL_ROOT}/evidence-manifest.txt
0677a9a9479e209a6e1ee30fdcd07996b671737850b17e79b97987578a73ec7f  ${RUNNER_SOURCE_ROOT}/candidate-manifest.json
1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052  ${RUNNER_SOURCE_ROOT}/one_shot_writer_freeze_backup_restart_runner.py
e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888  ${RUNNER_SOURCE_ROOT}/root_fd_metadata_helper.py
eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f  ${RUNNER_SOURCE_ROOT}/validate_3e_j_runner_packet.py
3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e  ${RUNNER_SOURCE_ROOT}/test_3e_j_runner_negative.py
261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd  ${RUNNER_SOURCE_ROOT}/runner-policy.json
2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773  ${RUNNER_SOURCE_ROOT}/3e_j_operation_manual.md
SHAS

printf '\n===== ROOT DEPLOYMENT PACKET HUMAN REVIEW =====\n'

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$PACKET_EVIDENCE_ROOT" \
  "$FINAL_SEAL_ROOT" \
  "$RUNNER_SOURCE_ROOT" \
  "$PACKET_REL" \
  "$FINAL_SEAL_REL" \
  "$RUNNER_SOURCE_REL" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve(strict=True)
evidence = Path(sys.argv[2]).resolve(strict=True)
final_seal = Path(sys.argv[3]).resolve(strict=True)
runner_source = Path(sys.argv[4]).resolve(strict=True)
packet_rel = sys.argv[5]
final_rel = sys.argv[6]
runner_rel = sys.argv[7]

packet = evidence / "packet-snapshot"
candidate = packet / "candidate-artifacts"
inputs = packet / "deployment-input-snapshot"
final_input = inputs / "final-seal-evidence"
runner_input = inputs / "runner-candidate"
logs = packet / "validation-logs"

PHASE = "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-PACKET"

PACKET_SHA = {
    "result.json": "07951222582d6dda8ae07bcef6cd920db0d7cbdf22b20b39e48593cf716f9e6f",
    "packet-snapshot/packet-manifest.json": "fae7a17137d4283d144bd3ac5352de80653adac6480c6db0e0eb776e6df3b267",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": "10c5aa0b9e53bd6ed03c8a89ac99c6b87d7fc4ed00fe45dca7ccbe7939336748",
    "evidence-manifest.txt": "29dca2ef58e72b40cbec06581d86d28d49b5ccc0a1a239316eebc3c380159d9c",
}

FINAL_MAP = {
    "result.json": "result.json",
    "packet-manifest.json": "packet-snapshot/packet-manifest.json",
    "candidate-manifest.json": "packet-snapshot/candidate-artifacts/candidate-manifest.json",
    "snapshot-manifest.json": "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json",
    "evidence-manifest.txt": "evidence-manifest.txt",
}
FINAL_SHA = {
    "result.json": "c9d71a2969a2ddf2a710f9e45c60327e42b5257994d613477c0ee724694d3bba",
    "packet-manifest.json": "700a572496fb3d3c61235da276fbe668afb1a8bdf576040885f6fb07eac502c2",
    "candidate-manifest.json": "eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f",
    "snapshot-manifest.json": "afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c",
    "evidence-manifest.txt": "0c674bd9a7ea654bec9acea38a41b03a990d8dbf52b63dea23bb2562662f6d20",
}
RUNNER_SHA = {
    "candidate-manifest.json": "0677a9a9479e209a6e1ee30fdcd07996b671737850b17e79b97987578a73ec7f",
    "one_shot_writer_freeze_backup_restart_runner.py": "1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052",
    "root_fd_metadata_helper.py": "e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888",
    "validate_3e_j_runner_packet.py": "eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f",
    "test_3e_j_runner_negative.py": "3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e",
    "runner-policy.json": "261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd",
    "3e_j_operation_manual.md": "2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773",
}
PROTECTED_SHA = {
    "data/database/ebook_affiliate.db": "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9",
    "config/slack_worker_release_source_manifest.json": "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d",
    "app/db/repositories/workflow_state_repository.py": "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "migrations/versions/00241611109d_add_unique_wordpress_post_id.py": "e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a",
    "scripts/run_slack_approval_socket.py": "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
    "tests/test_slack_approval_socket_hold_remediation_offline.py": "86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72",
}

CANDIDATE_FILES = {
    "candidate-manifest.json",
    "root-deployment-policy.json",
    "target-layout.json",
    "sudoers-contract.json",
    "preflight-rollback-contract.json",
    "execution-guard-contract.json",
    "blocked_root_deployment_entrypoint.py",
    "validate_root_deployment_packet.py",
    "test_root_deployment_packet_negative.py",
    "root_deployment_operation_manual.md",
}
FINAL_INPUT_FILES = set(FINAL_MAP)
RUNNER_INPUT_FILES = set(RUNNER_SHA)
INPUT_FILES = {
    *(f"final-seal-evidence/{x}" for x in FINAL_INPUT_FILES),
    *(f"runner-candidate/{x}" for x in RUNNER_INPUT_FILES),
}
LOG_FILES = {"python-compile.log", "validator.log", "negative-tests.log"}
PACKET_FILES = {
    "packet-manifest.json",
    "human-approval-verbatim.txt",
    *(f"candidate-artifacts/{x}" for x in CANDIDATE_FILES),
    *(f"deployment-input-snapshot/{x}" for x in INPUT_FILES),
    *(f"validation-logs/{x}" for x in LOG_FILES),
}
EVIDENCE_FILES = {
    "result.json",
    "evidence-manifest.txt",
    *(f"packet-snapshot/{x}" for x in PACKET_FILES),
}
PACKET_DIRS = {
    "candidate-artifacts",
    "deployment-input-snapshot",
    "deployment-input-snapshot/final-seal-evidence",
    "deployment-input-snapshot/runner-candidate",
    "validation-logs",
}
EVIDENCE_DIRS = {"packet-snapshot", *(f"packet-snapshot/{x}" for x in PACKET_DIRS)}

EXPECTED_TARGETS = {
    "/opt/ai-media-os/3e-j/bin/one_shot_writer_freeze_backup_restart_runner.py": "0755",
    "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py": "0755",
    "/opt/ai-media-os/3e-j/runner-policy.json": "0644",
    "/opt/ai-media-os/3e-j/review/validate_3e_j_runner_packet.py": "0755",
    "/opt/ai-media-os/3e-j/review/test_3e_j_runner_negative.py": "0644",
    "/opt/ai-media-os/3e-j/docs/3e_j_operation_manual.md": "0644",
}
EXPECTED_DIRS = {
    "/opt/ai-media-os/3e-j": "0755",
    "/opt/ai-media-os/3e-j/bin": "0755",
    "/opt/ai-media-os/3e-j/libexec": "0755",
    "/opt/ai-media-os/3e-j/review": "0755",
    "/opt/ai-media-os/3e-j/docs": "0755",
}
EXPECTED_COMMANDS = [
    "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py self-check --db-path /home/deploy/ai_media_os/data/database/ebook_affiliate.db",
    "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py inspect --db-path /home/deploy/ai_media_os/data/database/ebook_affiliate.db --require-zero",
]
EXPECTED_FAILURE_STATES = [
    "NO_MUTATION_PREFLIGHT_FAILURE",
    "STAGING_CREATED_NOT_PROMOTED",
    "DEPLOYMENT_ROOT_PROMOTED_SUDOERS_NOT_INSTALLED",
    "SUDOERS_INSTALLED_POSTCHECK_FAILED",
    "ROLLBACK_COMPLETE_HUMAN_REVIEW_REQUIRED",
    "ROLLBACK_INCOMPLETE_EMERGENCY_HOLD",
]

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT:{path}")
    return value

def scan(root: Path) -> tuple[set[str], set[str], int, int]:
    files, dirs = set(), set()
    links = other = 0
    for path in root.rglob("*"):
        item = path.lstat()
        rel = path.relative_to(root).as_posix()
        if stat.S_ISLNK(item.st_mode):
            links += 1
        elif stat.S_ISREG(item.st_mode):
            files.add(rel)
        elif stat.S_ISDIR(item.st_mode):
            dirs.add(rel)
        else:
            other += 1
    return files, dirs, links, other

def identity(root: Path) -> dict[str, tuple[str, int, int, int, int]]:
    files, dirs, links, other = scan(root)
    require(links == 0 and other == 0, f"IDENTITY_SPECIAL:{root}")
    out: dict[str, tuple[str, int, int, int, int]] = {}
    ri = root.lstat()
    out["./"] = ("DIR", 0, stat.S_IMODE(ri.st_mode), ri.st_uid, ri.st_gid)
    for rel in sorted(dirs):
        item = (root / rel).lstat()
        out[rel + "/"] = ("DIR", 0, stat.S_IMODE(item.st_mode), item.st_uid, item.st_gid)
    for rel in sorted(files):
        path = root / rel
        item = path.lstat()
        out[rel] = (sha256(path), item.st_size, stat.S_IMODE(item.st_mode), item.st_uid, item.st_gid)
    return out

def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"DIGEST:{rel}")
        require(rel not in entries, f"DUPLICATE:{rel}")
        entries[rel] = digest
    return entries

# Bind exact roots.
require(evidence.relative_to(repo).as_posix() == packet_rel, "PACKET_ROOT_BINDING")
require(final_seal.relative_to(repo).as_posix() == final_rel, "FINAL_ROOT_BINDING")
require(runner_source.relative_to(repo).as_posix() == runner_rel, "RUNNER_ROOT_BINDING")

# Fixed identities.
for rel, expected in PACKET_SHA.items():
    require(sha256(evidence / rel) == expected, f"PACKET_SHA:{rel}")
for name, rel in FINAL_MAP.items():
    require(sha256(final_seal / rel) == FINAL_SHA[name], f"FINAL_SHA:{name}")
for name, expected in RUNNER_SHA.items():
    require(sha256(runner_source / name) == expected, f"RUNNER_SHA:{name}")

before_packet = identity(evidence)
before_final = identity(final_seal)
before_runner = identity(runner_source)

# Exact sets and counts.
files, dirs, links, other = scan(evidence)
require(files == EVIDENCE_FILES and dirs == EVIDENCE_DIRS, "EVIDENCE_SET")
require((len(files), len(dirs), links, other) == (29, 6, 0, 0), "EVIDENCE_COUNTS")

pfiles, pdirs, plinks, pother = scan(packet)
require(pfiles == PACKET_FILES and pdirs == PACKET_DIRS, "PACKET_SET")
require((len(pfiles), len(pdirs), plinks, pother) == (27, 5, 0, 0), "PACKET_COUNTS")

cfiles, cdirs, clinks, cother = scan(candidate)
require(cfiles == CANDIDATE_FILES and not cdirs, "CANDIDATE_SET")
require((len(cfiles), clinks, cother) == (10, 0, 0), "CANDIDATE_COUNTS")

ifiles, idirs, ilinks, iother = scan(inputs)
require(ifiles == INPUT_FILES and idirs == {"final-seal-evidence", "runner-candidate"}, "INPUT_SET")
require((len(ifiles), len(idirs), ilinks, iother) == (12, 2, 0, 0), "INPUT_COUNTS")

lfiles, ldirs, llinks, lother = scan(logs)
require(lfiles == LOG_FILES and not ldirs and llinks == 0 and lother == 0, "LOG_SET")
require(not list(evidence.rglob("*.pyc")), "PACKET_PYC")

# Source snapshots equal originals.
for name, rel in FINAL_MAP.items():
    src, snap = final_seal / rel, final_input / name
    require(src.read_bytes() == snap.read_bytes(), f"FINAL_BYTES:{name}")
    require(src.stat().st_size == snap.stat().st_size, f"FINAL_SIZE:{name}")
    require(sha256(snap) == FINAL_SHA[name], f"FINAL_INPUT_SHA:{name}")
for name, expected in RUNNER_SHA.items():
    src, snap = runner_source / name, runner_input / name
    require(src.read_bytes() == snap.read_bytes(), f"RUNNER_BYTES:{name}")
    require(src.stat().st_size == snap.stat().st_size, f"RUNNER_SIZE:{name}")
    require(sha256(snap) == expected, f"RUNNER_INPUT_SHA:{name}")

# Final Seal source remains sealed.
ffiles, fdirs, flinks, fother = scan(final_seal)
require((len(ffiles), len(fdirs), flinks, fother) == (36, 11, 0, 0), "FINAL_SEAL_COUNTS")
for rel in ffiles:
    require(stat.S_IMODE((final_seal / rel).lstat().st_mode) == 0o444, f"FINAL_FILE_MODE:{rel}")
for path in [final_seal, *(final_seal / rel for rel in fdirs)]:
    require(stat.S_IMODE(path.lstat().st_mode) == 0o555, f"FINAL_DIR_MODE:{path}")

# Candidate manifest.
cm = load_json(candidate / "candidate-manifest.json")
require(cm["phase"] == PHASE, "CM_PHASE")
require(cm["status"] == "ROOT_DEPLOYMENT_PACKET_PREPARED_NO_EXECUTION", "CM_STATUS")
require(cm["total_file_count"] == 10 and cm["file_count_excluding_manifest"] == 9, "CM_COUNTS")
require(cm["deployment_input_snapshot_file_count"] == 12, "CM_INPUT")
require(cm["negative_test_count"] == 21, "CM_NEGATIVE")
require(cm["root_deployment_execution_allowed"] is False, "CM_EXECUTION")
require(cm["sudoers_installation_allowed"] is False, "CM_SUDOERS")
require(cm["production_file_creation_allowed"] is False, "CM_PRODUCTION_FILE")
require(cm["production_release_decision"] == "HOLD", "CM_HOLD")
require({"candidate-manifest.json", *(x["name"] for x in cm["files"])} == CANDIDATE_FILES, "CM_SET")
for item in cm["files"]:
    path = candidate / item["name"]
    require(sha256(path) == item["sha256"] and path.stat().st_size == item["size_bytes"], f"CM_ITEM:{item['name']}")

# Policy.
policy = load_json(candidate / "root-deployment-policy.json")
require(policy["phase"] == PHASE, "POLICY_PHASE")
require(policy["status"] == "ROOT_DEPLOYMENT_PACKET_PREPARED_NO_EXECUTION", "POLICY_STATUS")
require(policy["final_seal_acceptance"] == "ACCEPTED_WITH_PRODUCTION_HOLD", "POLICY_ACCEPTANCE")
require(policy["final_seal_result_human_review"] == "PASS", "POLICY_REVIEW")
require(policy["packet_preparation_only"] is True, "POLICY_PACKET_ONLY")
for key in (
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "production_file_creation_allowed",
    "production_directory_creation_allowed",
    "root_helper_execution_allowed",
    "runner_execution_allowed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_production_token_created",
    "approval_binding_created",
):
    require(policy[key] is False, f"POLICY_FALSE:{key}")
require(policy["runner_status"] == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL", "POLICY_RUNNER")
require(policy["writer_freeze_execution"] == "HOLD", "POLICY_WRITER")
require(policy["production_release_decision"] == "HOLD", "POLICY_RELEASE")
require(policy["release_status"] == "CANDIDATE_NOT_APPROVED", "POLICY_STATUS_RELEASE")

# Layout.
layout = load_json(candidate / "target-layout.json")
require(layout["phase"] == PHASE and layout["deployment_root"] == "/opt/ai-media-os/3e-j", "LAYOUT_ROOT")
require(layout["owner"] == "root" and layout["group"] == "root", "LAYOUT_OWNER_GROUP")
require({x["path"]: x["mode"] for x in layout["directories"]} == EXPECTED_DIRS, "LAYOUT_DIRS")
require({x["target"]: x["mode"] for x in layout["files"]} == EXPECTED_TARGETS, "LAYOUT_TARGETS")
require(all(x["owner"] == "root" and x["group"] == "root" for x in layout["files"]), "LAYOUT_FILE_OWNER")
for item in layout["files"]:
    source = packet / item["source_snapshot"]
    require(source.is_file() and sha256(source) == item["source_sha256"], f"LAYOUT_SOURCE:{item['target']}")
st = layout["sudoers_target"]
require(st == {
    "path": "/etc/sudoers.d/ai-media-os-3e-j-root-helper",
    "mode": "0440",
    "owner": "root",
    "group": "root",
    "exclusive_create": True,
    "overwrite_allowed": False,
}, "LAYOUT_SUDOERS")
require(layout["production_creation_allowed_current_phase"] is False, "LAYOUT_CURRENT_CREATION")

# Sudoers contract stored in Packet only; no /etc access.
sudoers = load_json(candidate / "sudoers-contract.json")
require(sudoers["phase"] == PHASE, "SUDOERS_PHASE")
require(sudoers["target_path"] == "/etc/sudoers.d/ai-media-os-3e-j-root-helper", "SUDOERS_TARGET")
require((sudoers["owner"], sudoers["group"], sudoers["mode"]) == ("root", "root", "0440"), "SUDOERS_META")
require(sudoers["exclusive_create"] is True and sudoers["overwrite_allowed"] is False, "SUDOERS_CREATE")
require(sudoers["installation_allowed_current_phase"] is False, "SUDOERS_INSTALL")
require(sudoers["exact_commands"] == EXPECTED_COMMANDS, "SUDOERS_COMMANDS")
require(sudoers["tags"] == ["NOPASSWD", "NOSETENV"], "SUDOERS_TAGS")
for key in ("wildcards_allowed", "arbitrary_arguments_allowed", "python_interpreter_allowed", "shell_allowed", "editor_allowed", "setenv_allowed"):
    require(sudoers[key] is False, f"SUDOERS_FALSE:{key}")
require("*" not in sudoers["sudoers_content"], "SUDOERS_WILDCARD")
require("deploy ALL=(root) NOPASSWD:NOSETENV: AI_MEDIA_OS_3E_J_ROOT_HELPER" in sudoers["sudoers_content"], "SUDOERS_GRANT")
require(hashlib.sha256(sudoers["sudoers_content"].encode()).hexdigest() == sudoers["sudoers_content_sha256"], "SUDOERS_CONTENT_SHA")

# Preflight / staging / rollback.
contract = load_json(candidate / "preflight-rollback-contract.json")
preflight = contract["future_execution_preflight"]
for key in (
    "root_context_required",
    "deployment_root_must_be_absent",
    "sudoers_target_must_be_absent",
    "source_fixed_sha_revalidation_required",
    "final_seal_fixed_sha_revalidation_required",
    "parent_path_symlink_rejection_required",
    "target_path_symlink_rejection_required",
    "visudo_available_required",
    "one_shot_guard_absent_required",
    "production_release_must_remain_hold",
):
    require(preflight[key] is True, f"PREFLIGHT:{key}")
staging = contract["future_staging"]
require(staging == {
    "staging_parent": "/opt/ai-media-os",
    "staging_name_prefix": ".3e-j-stage-",
    "exclusive_create": True,
    "same_filesystem_atomic_rename_required": True,
    "overwrite_allowed": False,
}, "STAGING")
rb = contract["future_rollback"]
require(rb["rollback_scope"] == "CURRENT_TRANSACTION_CREATED_PATHS_ONLY", "ROLLBACK_SCOPE")
for key in ("existing_path_removal_allowed", "source_evidence_mutation_allowed", "automatic_retry_allowed", "sigkill_allowed", "process_group_signal_allowed"):
    require(rb[key] is False, f"ROLLBACK_FALSE:{key}")
require(rb["max_execution_attempts"] == 1, "ROLLBACK_ATTEMPTS")
require(rb["sudoers_removal_allowed_only_when_created_by_current_transaction"] is True, "ROLLBACK_SUDOERS_TX")
require(rb["sudoers_removal_requires_exact_content_sha_match"] is True, "ROLLBACK_SUDOERS_SHA")
require(rb["deployment_root_removal_allowed_only_when_created_by_current_transaction"] is True, "ROLLBACK_ROOT_TX")
require(rb["deployment_root_removal_requires_inode_device_and_tree_identity_match"] is True, "ROLLBACK_ROOT_ID")
require(rb["rollback_incomplete_action"] == "STOP_AND_HUMAN_REVIEW", "ROLLBACK_STOP")
require(contract["partial_failure_states"] == EXPECTED_FAILURE_STATES, "FAILURE_STATES")
require(contract["current_phase_execution"] is False, "CURRENT_EXECUTION")

# Guard.
guard = load_json(candidate / "execution-guard-contract.json")
require(guard["blocked"] is True and guard["packet_preparation_only"] is True, "GUARD_BLOCK")
require(guard["future_required_approval_token"] == "APPROVE_3E_J_ROOT_DEPLOYMENT_EXECUTION_ONCE", "GUARD_TOKEN")
require(guard["root_deployment_execution_allowed"] is False, "GUARD_EXECUTION")
require(guard["max_execution_attempts"] == 1 and guard["automatic_retry_allowed"] is False, "GUARD_ATTEMPTS")
require(guard["guard_path_future"] == "/var/lib/ai-media-os/3e-j-root-deployment-once-v1.guard", "GUARD_PATH")
require(guard["guard_exclusive_create_required"] is True and guard["guard_change_allowed_current_phase"] is False, "GUARD_CREATE")
require(guard["final_production_token_created"] is False and guard["approval_binding_created"] is False, "GUARD_FINAL")
require(guard["production_release_decision"] == "HOLD", "GUARD_HOLD")

# Blocked entrypoint static only.
blocked_path = candidate / "blocked_root_deployment_entrypoint.py"
blocked = blocked_path.read_text(encoding="utf-8")
compile(blocked, str(blocked_path), "exec")
for marker in (
    "ROOT_DEPLOYMENT_PACKET_PREPARATION_ONLY=true",
    "ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false",
    "SUDOERS_INSTALLATION_ALLOWED=false",
    "PRODUCTION_FILE_CREATION_ALLOWED=false",
    "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "return 2",
):
    require(marker in blocked, f"BLOCKED:{marker}")
for token in ("subprocess", "shutil", "socket", "sqlite3", "os.", "sudo ", "systemctl"):
    require(token not in blocked, f"BLOCKED_FORBIDDEN:{token}")

# Approval/manual.
approval = (packet / "human-approval-verbatim.txt").read_text(encoding="utf-8")
manual = (candidate / "root_deployment_operation_manual.md").read_text(encoding="utf-8")
for marker in (
    "APPROVE_3E_J_FINAL_SEAL_ACCEPTANCE_AND_ROOT_DEPLOYMENT_PACKET_PREPARATION_NO_EXECUTION",
    "ROOT_DEPLOYMENT_PACKET_PREPARATION_ONLY=true",
    "ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false",
    "SUDOERS_INSTALLATION_ALLOWED=false",
    "PRODUCTION_RELEASE_DECISION=HOLD",
):
    require(marker in approval, f"APPROVAL:{marker}")
for marker in (
    "This packet is preparation-only.",
    "Root deployment execution: `false`",
    "Sudoers installation: `false`",
    "Production release: `HOLD`",
    "APPROVE_3E_J_ROOT_DEPLOYMENT_EXECUTION_ONCE",
    "The current blocked entrypoint always exits with status 2.",
):
    require(marker in manual, f"MANUAL:{marker}")

# Manifests.
pm = load_json(packet / "packet-manifest.json")
require(pm["phase"] == PHASE and pm["status"] == "ROOT_DEPLOYMENT_PACKET_PREPARED_NO_EXECUTION", "PM_PHASE")
require(pm["packet_file_count_excluding_manifest"] == 26 and len(pm["packet_files"]) == 26, "PM_COUNT")
require({x["name"] for x in pm["packet_files"]} == PACKET_FILES - {"packet-manifest.json"}, "PM_SET")
for item in pm["packet_files"]:
    path = packet / item["name"]
    require(sha256(path) == item["sha256"] and path.stat().st_size == item["size_bytes"], f"PM_ITEM:{item['name']}")

em = parse_manifest(evidence / "evidence-manifest.txt")
require(len(em) == 28 and set(em) == EVIDENCE_FILES - {"evidence-manifest.txt"}, "EM_SET")
for rel, digest in em.items():
    require(sha256(evidence / rel) == digest, f"EM_ITEM:{rel}")

# Result.
result = load_json(evidence / "result.json")
require(result["phase"] == PHASE, "RESULT_PHASE")
require(result["result"] == "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_PACKET_PREPARED_NO_EXECUTION", "RESULT_VALUE")
require(result["evidence_root"] == packet_rel, "RESULT_ROOT")
require(result["final_seal_acceptance"] == "ACCEPTED_WITH_PRODUCTION_HOLD", "RESULT_ACCEPTANCE")
require(result["final_seal_result_human_review"] == "PASS", "RESULT_REVIEW")
require(result["source_final_seal_fixed_sha_review"] == "PASS", "RESULT_FINAL_SHA")
require(result["source_runner_candidate_fixed_sha_review"] == "PASS", "RESULT_RUNNER_SHA")
require(result["source_evidence_unchanged"] is True and result["runner_source_unchanged"] is True, "RESULT_SOURCES")
for key, expected in (
    ("evidence_file_count", 29),
    ("evidence_directory_count_excluding_root", 6),
    ("packet_file_count", 27),
    ("packet_directory_count", 5),
    ("packet_manifest_entry_count", 26),
    ("evidence_manifest_entry_count", 28),
    ("candidate_artifact_count", 10),
    ("deployment_input_snapshot_file_count", 12),
    ("final_seal_identity_file_count", 5),
    ("runner_candidate_file_count", 7),
    ("validation_log_count", 3),
    ("negative_test_count", 21),
):
    require(result[key] == expected, f"RESULT_COUNT:{key}")
require(result["validator"] == "PASS" and result["negative_tests"] == "PASS", "RESULT_VALIDATION")
require(result["packet_preparation_only"] is True, "RESULT_PACKET_ONLY")
for key in (
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "production_file_creation_allowed",
    "production_directory_creation_allowed",
    "root_helper_execution_allowed",
    "runner_execution_allowed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_production_token_created",
    "approval_binding_created",
):
    require(result[key] is False, f"RESULT_FALSE:{key}")
require(result["protected_sha_unchanged"] is True, "RESULT_PROTECTED")
require(result["runner_status"] == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL", "RESULT_RUNNER_HOLD")
require(result["writer_freeze_execution"] == "HOLD", "RESULT_WRITER_HOLD")
require(result["production_release_decision"] == "HOLD", "RESULT_RELEASE_HOLD")
require(result["release_status"] == "CANDIDATE_NOT_APPROVED", "RESULT_RELEASE_STATUS")
require(result["next_gate"] == "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_PACKET_READONLY", "RESULT_NEXT")

# Logs / test source.
compile_log = (logs / "python-compile.log").read_text(encoding="utf-8").splitlines()
require(compile_log == [
    "PYTHON_COMPILE_PASS=blocked_root_deployment_entrypoint.py",
    "PYTHON_COMPILE_PASS=validate_root_deployment_packet.py",
    "PYTHON_COMPILE_PASS=test_root_deployment_packet_negative.py",
], "COMPILE_LOG")
validator_path = candidate / "validate_root_deployment_packet.py"
negative_path = candidate / "test_root_deployment_packet_negative.py"
validator_source = validator_path.read_text(encoding="utf-8")
negative_source = negative_path.read_text(encoding="utf-8")
compile(validator_source, str(validator_path), "exec")
compile(negative_source, str(negative_path), "exec")
test_names = re.findall(r"^    def (test_[A-Za-z0-9_]+)\(self\) -> None:$", negative_source, re.MULTILINE)
require(len(test_names) == 21 and len(set(test_names)) == 21, "NEGATIVE_METHODS")
require("tempfile.TemporaryDirectory" in negative_source, "NEGATIVE_TEMP")
require("shutil.copytree(EVIDENCE_ROOT, self.root)" in negative_source, "NEGATIVE_COPY")

# Protected SHA.
for rel, expected in PROTECTED_SHA.items():
    require(sha256(repo / rel) == expected, f"PROTECTED:{rel}")

# Runtime validator read-only.
vr = subprocess.run(
    [str(repo / ".venv/bin/python"), "-B", str(validator_path), str(evidence)],
    cwd=candidate,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
vtext = vr.stdout.decode("utf-8")
require(vr.returncode == 0 and "VALIDATION=PASS" in vtext, "RUNTIME_VALIDATOR")

# Runtime negative tests on their TemporaryDirectory copy.
nr = subprocess.run(
    [str(repo / ".venv/bin/python"), "-B", str(negative_path)],
    cwd=candidate,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
ntext = nr.stdout.decode("utf-8")
require(nr.returncode == 0 and "Ran 21 tests" in ntext, "RUNTIME_NEGATIVE")
require([line.strip() for line in ntext.splitlines()].count("OK") == 1, "RUNTIME_NEGATIVE_OK")
require("FAILED" not in ntext and "Traceback" not in ntext and "ERROR:" not in ntext, "RUNTIME_NEGATIVE_FAILURE")

# No mutations or bytecode.
require(identity(evidence) == before_packet, "PACKET_MUTATION")
require(identity(final_seal) == before_final, "FINAL_MUTATION")
require(identity(runner_source) == before_runner, "RUNNER_MUTATION")
require(not list(evidence.rglob("*.pyc")), "PACKET_BYTECODE")
require(not list(final_seal.rglob("*.pyc")), "FINAL_BYTECODE")
require(not list(runner_source.rglob("*.pyc")), "RUNNER_BYTECODE")
for rel, expected in PROTECTED_SHA.items():
    require(sha256(repo / rel) == expected, f"PROTECTED_CHANGED:{rel}")

print("ROOT_DEPLOYMENT_PACKET_RESULT_SHA_REVIEW=PASS")
print("ROOT_DEPLOYMENT_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("ROOT_DEPLOYMENT_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("ROOT_DEPLOYMENT_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("ROOT_DEPLOYMENT_PACKET_EVIDENCE_ROOT_PATH_REVIEW=PASS")
print("ROOT_DEPLOYMENT_PACKET_EVIDENCE_FILE_COUNT=29")
print("ROOT_DEPLOYMENT_PACKET_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=6")
print("ROOT_DEPLOYMENT_PACKET_FILE_COUNT=27")
print("ROOT_DEPLOYMENT_PACKET_DIRECTORY_COUNT=5")
print("ROOT_DEPLOYMENT_PACKET_MANIFEST_ENTRY_COUNT=26")
print("ROOT_DEPLOYMENT_EVIDENCE_MANIFEST_ENTRY_COUNT=28")
print("ROOT_DEPLOYMENT_CANDIDATE_ARTIFACT_COUNT=10")
print("ROOT_DEPLOYMENT_INPUT_SNAPSHOT_FILE_COUNT=12")
print("ROOT_DEPLOYMENT_FINAL_SEAL_IDENTITY_FILE_COUNT=5")
print("ROOT_DEPLOYMENT_RUNNER_CANDIDATE_FILE_COUNT=7")
print("ROOT_DEPLOYMENT_VALIDATION_LOG_COUNT=3")
print("FINAL_SEAL_INPUT_BYTE_SIZE_SHA_EQUIVALENCE=PASS")
print("RUNNER_CANDIDATE_INPUT_BYTE_SIZE_SHA_EQUIVALENCE=PASS")
print("FINAL_SEAL_SOURCE_UNCHANGED=true")
print("RUNNER_CANDIDATE_SOURCE_UNCHANGED=true")
print("FINAL_SEAL_SOURCE_REMAINS_SEALED=true")
print("TARGET_LAYOUT_PATH_CONTRACT_REVIEW=PASS")
print("TARGET_LAYOUT_OWNER_GROUP_CONTRACT_REVIEW=PASS")
print("TARGET_LAYOUT_DIRECTORY_MODE_CONTRACT_REVIEW=PASS")
print("TARGET_LAYOUT_FILE_MODE_CONTRACT_REVIEW=PASS")
print("SUDOERS_TARGET_MODE_CONTRACT_REVIEW=PASS")
print("SUDOERS_EXCLUSIVE_CREATE_CONTRACT_REVIEW=PASS")
print("SUDOERS_OVERWRITE_FORBIDDEN=true")
print("SUDOERS_EXACT_COMMAND_ALLOWLIST_COUNT=2")
print("SUDOERS_NOPASSWD_NOSETENV_CONTRACT_REVIEW=PASS")
print("SUDOERS_WILDCARD_ALLOWED=false")
print("SUDOERS_ARBITRARY_ARGUMENTS_ALLOWED=false")
print("SUDOERS_PYTHON_INTERPRETER_ALLOWED=false")
print("SUDOERS_SHELL_ALLOWED=false")
print("SUDOERS_EDITOR_ALLOWED=false")
print("SUDOERS_SETENV_ALLOWED=false")
print("PREFLIGHT_CONTRACT_REVIEW=PASS")
print("STAGING_EXCLUSIVE_CREATE_CONTRACT_REVIEW=PASS")
print("ROLLBACK_SCOPE=CURRENT_TRANSACTION_CREATED_PATHS_ONLY")
print("ROLLBACK_EXISTING_PATH_REMOVAL_ALLOWED=false")
print("ROLLBACK_AUTOMATIC_RETRY_ALLOWED=false")
print("ROOT_DEPLOYMENT_MAX_EXECUTION_ATTEMPTS=1")
print("PARTIAL_FAILURE_STATE_COUNT=6")
print("PARTIAL_FAILURE_CONTRACT_REVIEW=PASS")
print("EXECUTION_GUARD_CONTRACT_REVIEW=PASS")
print("BLOCKED_ROOT_DEPLOYMENT_ENTRYPOINT_STATIC_REVIEW=PASS")
print("BLOCKED_ROOT_DEPLOYMENT_ENTRYPOINT_EXECUTED=false")
print("ROOT_DEPLOYMENT_OPERATION_MANUAL_REVIEW=PASS")
print("ROOT_DEPLOYMENT_APPROVAL_TEXT_REVIEW=PASS")
print("ROOT_DEPLOYMENT_RESULT_RECORD_REVIEW=PASS")
print("ROOT_DEPLOYMENT_VALIDATOR_SOURCE_COMPILE_REVIEW=PASS")
print("ROOT_DEPLOYMENT_NEGATIVE_TEST_SOURCE_COMPILE_REVIEW=PASS")
print("ROOT_DEPLOYMENT_NEGATIVE_TEST_METHOD_COUNT=21")
print("ROOT_DEPLOYMENT_RUNTIME_VALIDATOR_EXECUTED_READONLY=true")
print("ROOT_DEPLOYMENT_RUNTIME_VALIDATOR=PASS")
print("ROOT_DEPLOYMENT_RUNTIME_NEGATIVE_TESTS_EXECUTED_ON_TEMP_COPY=true")
print("ROOT_DEPLOYMENT_RUNTIME_NEGATIVE_TEST_COUNT=21")
print("ROOT_DEPLOYMENT_RUNTIME_NEGATIVE_TESTS=PASS")
print("ROOT_DEPLOYMENT_PACKET_EVIDENCE_MUTATION=false")
print("FINAL_SEAL_SOURCE_MUTATION=false")
print("RUNNER_CANDIDATE_SOURCE_MUTATION=false")
print("ROOT_DEPLOYMENT_BYTECODE_SIDE_EFFECT=false")
print("PROTECTED_SHA_REVIEW=PASS")
print("ROOT_DEPLOYMENT_PACKET_PREPARATION_ONLY=true")
print("ROOT_DEPLOYMENT_EXECUTION_RECORDED=false")
print("SUDOERS_INSTALLATION_RECORDED=false")
print("PRODUCTION_FILE_CREATION_RECORDED=false")
print("PRODUCTION_DIRECTORY_CREATION_RECORDED=false")
print("ROOT_HELPER_EXECUTION_RECORDED=false")
print("RUNNER_EXECUTION_RECORDED=false")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("SUDOERS_CHANGED=false")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_PRODUCTION_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("ROOT_DEPLOYMENT_PACKET_HUMAN_REVIEW_DECISION=APPROVE_ROOT_DEPLOYMENT_PACKET_WITH_EXECUTION_HOLD")
print("NEXT_GATE=HUMAN_DECISION_FOR_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARATION_OR_KEEP_HOLD")
PY

printf '\n===== FINAL ROOT DEPLOYMENT PACKET HUMAN REVIEW MARKERS =====\n'
echo "ROOT_DEPLOYMENT_PACKET_HUMAN_REVIEW=PASS"
echo "ROOT_DEPLOYMENT_PACKET_HUMAN_REVIEW_DECISION=APPROVE_ROOT_DEPLOYMENT_PACKET_WITH_EXECUTION_HOLD"
echo "ROOT_DEPLOYMENT_RUNTIME_VALIDATOR=PASS"
echo "ROOT_DEPLOYMENT_RUNTIME_NEGATIVE_TEST_COUNT=21"
echo "ROOT_DEPLOYMENT_RUNTIME_NEGATIVE_TESTS=PASS"
echo "ROOT_DEPLOYMENT_PACKET_EVIDENCE_MUTATION=false"
echo "FINAL_SEAL_SOURCE_MUTATION=false"
echo "RUNNER_CANDIDATE_SOURCE_MUTATION=false"
echo "ROOT_DEPLOYMENT_BYTECODE_SIDE_EFFECT=false"
echo "ROOT_DEPLOYMENT_PACKET_PREPARATION_ONLY=true"
echo "ROOT_DEPLOYMENT_EXECUTION_RECORDED=false"
echo "SUDOERS_INSTALLATION_RECORDED=false"
echo "PRODUCTION_FILE_CREATION_RECORDED=false"
echo "PRODUCTION_DIRECTORY_CREATION_RECORDED=false"
echo "ROOT_HELPER_EXECUTION_RECORDED=false"
echo "RUNNER_EXECUTION_RECORDED=false"
echo "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false"
echo "ONE_SHOT_GUARD_CHANGE_ALLOWED=false"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "FINAL_PRODUCTION_TOKEN_CREATED=false"
echo "APPROVAL_BINDING_CREATED=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_DECISION_FOR_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARATION_OR_KEEP_HOLD"
echo "REVIEW_COMMAND_EXIT_CODE=0"
