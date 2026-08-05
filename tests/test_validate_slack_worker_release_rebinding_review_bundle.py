from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import build_slack_worker_release_rebinding_review_bundle as builder
from scripts import validate_slack_worker_release_rebinding_review_bundle as validator


CANDIDATE_ROOT = Path("/tmp/db-safe-tst-5b-candidate-20260724-02")
CREATED_AT = "2026-07-24T00:00:00Z"


def make_bundle(tmp_path: Path) -> Path:
    policy = builder.load_json_bytes(
        builder.secure_repo_bytes(builder.POLICY_PATH), "POLICY_INVALID"
    )
    candidate = json.loads((CANDIDATE_ROOT / "candidate-manifest.json").read_text())
    review_root = tmp_path / "review_requests"
    output = review_root / candidate["candidate_id"]
    builder.generate(
        CANDIDATE_ROOT,
        created_at=CREATED_AT,
        output_root=output,
        test_evidence=builder.synthetic_test_evidence(policy, CREATED_AT),
        review_request_root=review_root,
    )
    return output


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_bytes(builder.pretty_bytes(value))


def master(root: Path) -> dict:
    return read_json(root / "review-bundle-manifest.json")


def write_master(root: Path, value: dict) -> None:
    write_json(root / "review-bundle-manifest.json", value)


def rebind_packet(root: Path, unit: str, packet: dict) -> None:
    manifest = master(root)
    path = root / manifest["review_unit_paths"][unit]
    write_json(path, packet)
    manifest["review_unit_sha256"][unit] = builder.sha256_bytes(path.read_bytes())
    write_master(root, manifest)


def rebind_template(root: Path, unit: str, template: dict) -> None:
    manifest = master(root)
    path = root / manifest["decision_template_paths"][unit]
    write_json(path, template)
    manifest["decision_template_sha256"][unit] = builder.sha256_bytes(
        path.read_bytes()
    )
    write_master(root, manifest)


def assert_failed(root: Path) -> None:
    with pytest.raises(validator.ReviewBundleIntegrityError) as captured:
        validator.validate(root)
    assert str(captured.value) == validator.INTEGRITY_ERROR


def test_valid_review_bundle_passes(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    result = validator.validate(root)
    assert result["result"] == "PASS_READY_FOR_HUMAN_REVIEW_NOT_APPROVED"
    assert result["source_diff_count"] == 5
    assert result["review_unit_count"] == 3
    assert result["decision_templates_unfilled"] is True
    assert result["human_decision_recorded"] is False
    assert result["production_approval_created"] is False


def test_missing_review_unit_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    (root / manifest["review_unit_paths"]["UNIT_SLACK_RUNTIME"]).unlink()
    assert_failed(root)


def test_duplicate_review_unit_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_SLACK_RUNTIME"
    packet = read_json(root / manifest["review_unit_paths"][unit])
    packet["unit_id"] = "UNIT_DB_SAFETY"
    rebind_packet(root, unit, packet)
    assert_failed(root)


def test_source_double_membership_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_SLACK_RUNTIME"
    packet = read_json(root / manifest["review_unit_paths"][unit])
    packet["sources"].append(
        {
            "path": "app/db/config.py",
            "old_sha256": "0" * 64,
            "current_sha256": "1" * 64,
            "diff_path": "source-diffs/invalid",
            "diff_sha256": "2" * 64,
        }
    )
    rebind_packet(root, unit, packet)
    assert_failed(root)


def test_missing_changed_source_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_DB_SAFETY"
    packet = read_json(root / manifest["review_unit_paths"][unit])
    packet["sources"] = [
        item for item in packet["sources"] if item["path"] != "app/db/access_guard.py"
    ]
    rebind_packet(root, unit, packet)
    assert_failed(root)


def test_candidate_sha_tamper_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    manifest["candidate_manifest_sha256"] = "0" * 64
    write_master(root, manifest)
    assert_failed(root)


def test_diff_sha_tamper_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    source = next(iter(manifest["diff_sha256"]))
    manifest["diff_sha256"][source] = "0" * 64
    write_master(root, manifest)
    assert_failed(root)


def test_production_manifest_sha_tamper_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    manifest["production_manifest_sha256"] = "0" * 64
    write_master(root, manifest)
    assert_failed(root)


def test_review_status_approved_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_DB_SAFETY"
    packet = read_json(root / manifest["review_unit_paths"][unit])
    packet["review_status"] = "APPROVED"
    rebind_packet(root, unit, packet)
    assert_failed(root)


def test_approval_status_issued_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_WORKFLOW_STATE"
    packet = read_json(root / manifest["review_unit_paths"][unit])
    packet["approval_status"] = "ISSUED"
    rebind_packet(root, unit, packet)
    assert_failed(root)


def test_decision_without_reviewer_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_DB_SAFETY"
    template = read_json(root / manifest["decision_template_paths"][unit])
    template["decision"] = "APPROVE"
    rebind_template(root, unit, template)
    assert_failed(root)


def test_reviewer_without_decision_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    unit = "UNIT_DB_SAFETY"
    template = read_json(root / manifest["decision_template_paths"][unit])
    template["reviewer"] = "invented-reviewer"
    rebind_template(root, unit, template)
    assert_failed(root)


@pytest.mark.parametrize(
    "field",
    ["deployment_allowed", "runtime_execution_allowed"],
)
def test_execution_flag_true_is_rejected(tmp_path: Path, field: str) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    manifest[field] = True
    write_master(root, manifest)
    assert_failed(root)


def test_production_manifest_replacement_true_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    manifest["production_manifest_replacement_allowed"] = True
    write_master(root, manifest)
    assert_failed(root)


def test_candidate_production_id_impersonation_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    candidate_path = root / manifest["candidate_manifest_path"]
    candidate = read_json(candidate_path)
    production = read_json(
        builder.REPO_ROOT / "config/slack_worker_release_source_manifest.json"
    )
    candidate["candidate_id"] = production["release_id_candidate"]
    write_json(candidate_path, candidate)
    manifest["candidate_id"] = production["release_id_candidate"]
    manifest["candidate_manifest_sha256"] = builder.sha256_bytes(
        candidate_path.read_bytes()
    )
    write_master(root, manifest)
    assert_failed(root)


def test_symlink_review_packet_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    path = root / manifest["review_unit_paths"]["UNIT_SLACK_RUNTIME"]
    target = root / manifest["review_unit_paths"]["UNIT_DB_SAFETY"]
    path.unlink()
    path.symlink_to(target)
    assert_failed(root)


def test_hardlink_diff_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    path = root / next(iter(manifest["diff_paths"].values()))
    outside = tmp_path / "outside-copy.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    os.link(outside, path)
    assert_failed(root)


def test_manifest_external_file_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    (root / "unmanifested.json").write_text("{}\n", encoding="utf-8")
    assert_failed(root)


def test_secret_like_value_is_rejected(tmp_path: Path) -> None:
    root = make_bundle(tmp_path)
    manifest = master(root)
    summary_path = root / manifest["human_summary_path"]
    summary_path.write_text("xoxb-injected-secret-value\n", encoding="utf-8")
    manifest["human_summary_sha256"] = builder.sha256_bytes(
        summary_path.read_bytes()
    )
    write_master(root, manifest)
    assert_failed(root)
