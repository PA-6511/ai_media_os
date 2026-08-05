from pathlib import Path

from phase17.approval.approval_reader import read_approval_file


def test_read_approval_file_pending_when_missing(tmp_path: Path) -> None:
    result = read_approval_file(str(tmp_path / "missing.json"))
    assert result["status"] == "WARN"
    assert result["decision"] == "PENDING"


def test_read_approval_file_accepts_approve_reject_needs_revision(tmp_path: Path) -> None:
    for decision in ("APPROVE", "REJECT", "NEEDS_REVISION"):
        path = tmp_path / f"{decision.lower()}.json"
        path.write_text('{"decision": "%s"}' % decision, encoding="utf-8")
        result = read_approval_file(str(path))
        assert result["status"] == "PASS"
        assert result["decision"] == decision


def test_read_approval_file_fails_on_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json}", encoding="utf-8")
    result = read_approval_file(str(path))
    assert result["status"] == "FAIL"
    assert result["decision"] == "INVALID"
