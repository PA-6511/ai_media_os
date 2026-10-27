import hashlib
import json

import dev_agent.proposal_bridge as proposal_bridge


SOURCE = "allowed.py"
OLD_TEXT = 'VALUE = "broken"'
NEW_TEXT = 'VALUE = "fixed"'

SOURCE_TEXT = (
    'VALUE = "broken"\n'
    'OTHER = 1\n'
)


def prepare_repo(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    source_path = repo_root / SOURCE
    source_path.write_text(
        SOURCE_TEXT,
        encoding="utf-8",
    )

    proposal_dir = (
        repo_root
        / "dev_agent"
        / "proposals"
    )

    proposal_state_dir = (
        repo_root
        / "dev_agent"
        / "proposal_states"
    )

    monkeypatch.setattr(
        proposal_bridge,
        "REPO_ROOT",
        repo_root,
    )

    monkeypatch.setattr(
        proposal_bridge,
        "PROPOSAL_DIR",
        proposal_dir,
    )

    monkeypatch.setattr(
        proposal_bridge,
        "PROPOSAL_STATE_DIR",
        proposal_state_dir,
    )

    monkeypatch.setattr(
        proposal_bridge,
        "CANARY_WRITE_FILES",
        frozenset({SOURCE}),
    )

    return repo_root, source_path


def test_create_proposal_does_not_modify_source(
    tmp_path,
    monkeypatch,
):
    _, source_path = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    before = source_path.read_text(
        encoding="utf-8"
    )

    result = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    after = source_path.read_text(
        encoding="utf-8"
    )

    assert result["status"] == "CREATED"
    assert result["source_write_performed"] is False
    assert before == after


def test_proposal_contains_before_sha256(
    tmp_path,
    monkeypatch,
):
    _, source_path = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    source_text = source_path.read_text(
        encoding="utf-8"
    )

    result = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    expected = hashlib.sha256(
        source_text.encode("utf-8")
    ).hexdigest()

    assert result["status"] == "CREATED"
    assert result["before_sha256"] == expected


def test_proposal_id_matches_saved_payload(
    tmp_path,
    monkeypatch,
):
    repo_root, _ = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    result = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    assert result["status"] == "CREATED"

    proposal_path = (
        repo_root
        / result["proposal_file"]
    )

    saved = json.loads(
        proposal_path.read_text(
            encoding="utf-8"
        )
    )

    core = {
        "schema_version": saved["schema_version"],
        "relative_path": saved["relative_path"],
        "old_text": saved["old_text"],
        "new_text": saved["new_text"],
        "before_sha256": saved["before_sha256"],
    }

    canonical = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    expected_id = (
        "proposal_v1_"
        + hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
    )

    assert saved["proposal_id"] == expected_id


def test_unlisted_target_is_denied(
    tmp_path,
    monkeypatch,
):
    prepare_repo(
        tmp_path,
        monkeypatch,
    )

    result = proposal_bridge.create_write_proposal(
        relative_path="other.py",
        old_text="old",
        new_text="new",
    )

    assert result["status"] == "DENIED"
    assert (
        result["reason"]
        == "PROPOSAL_TARGET_NOT_ALLOWED"
    )


def test_load_write_proposal_valid(
    tmp_path,
    monkeypatch,
):
    prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    assert created["status"] == "CREATED"

    loaded = proposal_bridge.load_write_proposal(
        created["proposal_id"]
    )

    assert loaded["status"] == "VALID"
    assert loaded["relative_path"] == SOURCE
    assert loaded["old_text"] == OLD_TEXT
    assert loaded["new_text"] == NEW_TEXT

    assert (
        loaded["current_sha256"]
        == loaded["before_sha256"]
    )


def test_load_write_proposal_rejects_tampered_json(
    tmp_path,
    monkeypatch,
):
    repo_root, _ = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    assert created["status"] == "CREATED"

    proposal_path = (
        repo_root
        / created["proposal_file"]
    )

    data = json.loads(
        proposal_path.read_text(
            encoding="utf-8"
        )
    )

    data["new_text"] = "TAMPERED"

    proposal_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = proposal_bridge.load_write_proposal(
        created["proposal_id"]
    )

    assert loaded["status"] == "DENIED"
    assert (
        loaded["reason"]
        == "PROPOSAL_ID_MISMATCH"
    )


def test_load_write_proposal_rejects_stale_source(
    tmp_path,
    monkeypatch,
):
    _, source_path = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    assert created["status"] == "CREATED"

    source_path.write_text(
        'VALUE = "changed-after-proposal"\n'
        'OTHER = 1\n',
        encoding="utf-8",
    )

    loaded = proposal_bridge.load_write_proposal(
        created["proposal_id"]
    )

    assert loaded["status"] == "DENIED"
    assert (
        loaded["reason"]
        == "STALE_PROPOSAL_SOURCE_CHANGED"
    )

    assert (
        loaded["expected_sha256"]
        != loaded["current_sha256"]
    )


def test_proposal_state_defaults_to_pending(
    tmp_path,
    monkeypatch,
):
    prepare_repo(
        tmp_path,
        monkeypatch,
    )

    proposal_id = (
        "proposal_v1_" + "a" * 64
    )

    result = proposal_bridge.get_proposal_state(
        proposal_id
    )

    assert result["status"] == "VALID"
    assert (
        result["proposal_state"]
        == "PENDING"
    )
    assert result["state_file_exists"] is False


def test_proposal_state_execution_lifecycle(
    tmp_path,
    monkeypatch,
):
    prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    proposal_id = created["proposal_id"]

    approved = (
        proposal_bridge.mark_proposal_approved(
            proposal_id
        )
    )

    assert approved["status"] == "VALID"
    assert (
        approved["proposal_state"]
        == "APPROVED"
    )

    claimed = (
        proposal_bridge.claim_proposal_execution(
            proposal_id
        )
    )

    assert claimed["status"] == "VALID"
    assert (
        claimed["proposal_state"]
        == "EXECUTING"
    )

    executed = (
        proposal_bridge.mark_proposal_executed(
            proposal_id
        )
    )

    assert executed["status"] == "VALID"
    assert (
        executed["proposal_state"]
        == "EXECUTED"
    )


def test_executed_proposal_load_is_denied(
    tmp_path,
    monkeypatch,
):
    _, source_path = prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    proposal_id = created["proposal_id"]

    proposal_bridge.mark_proposal_approved(
        proposal_id
    )
    proposal_bridge.claim_proposal_execution(
        proposal_id
    )
    proposal_bridge.mark_proposal_executed(
        proposal_id
    )

    # Even if source later changes, EXECUTED wins.
    source_path.write_text(
        'VALUE = "something-else"\n',
        encoding="utf-8",
    )

    loaded = proposal_bridge.load_write_proposal(
        proposal_id
    )

    assert loaded["status"] == "DENIED"
    assert (
        loaded["reason"]
        == "PROPOSAL_ALREADY_EXECUTED"
    )


def test_executed_proposal_cannot_be_reapproved(
    tmp_path,
    monkeypatch,
):
    prepare_repo(
        tmp_path,
        monkeypatch,
    )

    created = proposal_bridge.create_write_proposal(
        relative_path=SOURCE,
        old_text=OLD_TEXT,
        new_text=NEW_TEXT,
    )

    proposal_id = created["proposal_id"]

    proposal_bridge.mark_proposal_approved(
        proposal_id
    )
    proposal_bridge.claim_proposal_execution(
        proposal_id
    )
    proposal_bridge.mark_proposal_executed(
        proposal_id
    )

    again = (
        proposal_bridge.mark_proposal_approved(
            proposal_id
        )
    )

    assert again["status"] == "DENIED"
    assert (
        again["reason"]
        == "PROPOSAL_ALREADY_EXECUTED"
    )
