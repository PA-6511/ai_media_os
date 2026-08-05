import json
from pathlib import Path

from generic_block_ai.app.policy_versioning import (
    build_policy_version_info,
    compute_policy_hash,
    write_policy_history,
)


def _sample_policy() -> dict:
    return {
        "policy_metadata": {
            "version": "v1.2.3",
            "environment": "staging",
            "updated_at": "2026-05-23T00:00:00Z",
            "change_reason": "test",
            "policy_hash": "AUTO_COMPUTED",
        },
        "observe_only": True,
        "forbidden_actions": ["delete_block"],
    }


def test_compute_policy_hash_is_stable() -> None:
    policy = _sample_policy()
    first = compute_policy_hash(policy)
    second = compute_policy_hash(policy)
    assert first == second
    assert len(first) == 64


def test_build_policy_version_info_reads_metadata_and_hash() -> None:
    info = build_policy_version_info(_sample_policy())
    assert info["version"] == "v1.2.3"
    assert info["environment"] == "staging"
    assert info["updated_at"] == "2026-05-23T00:00:00Z"
    assert info["change_reason"] == "test"
    assert len(info["policy_hash"]) == 64


def test_write_policy_history_creates_local_file(tmp_path: Path) -> None:
    output = write_policy_history(
        base_path=tmp_path,
        policy=_sample_policy(),
        source_task_id="IR3-T2-001",
    )
    path = Path(output["history_path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["policy"]["version"] == "v1.2.3"
    assert output["external_write_executed"] is False