from pathlib import Path

from phase18.workspace.path_guard import is_allowed_path, is_within_sandbox


def test_is_within_sandbox_false_for_outside(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside = tmp_path / "outside" / "x.txt"
    assert is_within_sandbox(str(outside), str(sandbox)) is False


def test_is_allowed_path_false_for_outside_allowlist(tmp_path: Path) -> None:
    allowlist = tmp_path / "allow"
    allowlist.mkdir()
    outside = tmp_path / "other" / "x.txt"
    assert is_allowed_path(str(outside), str(allowlist)) is False
