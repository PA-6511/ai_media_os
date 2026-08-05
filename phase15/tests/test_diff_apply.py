from pathlib import Path

from phase15.pipeline.diff_apply import apply_file_change


def test_diff_apply_policy_violation_outside_allowlist(tmp_path: Path) -> None:
    allowlist_root = tmp_path / "allowed"
    allowlist_root.mkdir()
    outside_target = tmp_path / "outside" / "x.txt"

    result = apply_file_change(
        target_path=str(outside_target),
        content="hello",
        allowlist_root=str(allowlist_root),
        dry_run=True,
    )

    assert result["status"] == "POLICY_VIOLATION"


def test_diff_apply_dry_run_does_not_write_file(tmp_path: Path) -> None:
    allowlist_root = tmp_path / "allowed"
    target = allowlist_root / "out.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original", encoding="utf-8")

    result = apply_file_change(
        target_path=str(target),
        content="changed",
        allowlist_root=str(allowlist_root),
        dry_run=True,
    )

    assert result["status"] == "OK"
    assert result["action"] == "would_write"
    assert target.read_text(encoding="utf-8") == "original"
