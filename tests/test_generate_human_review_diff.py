import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_human_review_diff import generate_human_review_diff


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_before() -> dict:
    return {
        "package_type": "review_result",
        "status": "WARN",
        "reason": "confidence is below threshold",
        "score": 0.62,
        "execution": "DRY_RUN",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def base_after() -> dict:
    return {
        "package_type": "review_result",
        "status": "WARN",
        "reason": "confidence is below threshold but manually accepted",
        "score": 0.66,
        "execution": "DRY_RUN",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "reviewer_note": "score adjusted after human inspection",
    }


def test_generate_diff_writes_required_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        before_path = Path(tmpdir) / "before.json"
        after_path = Path(tmpdir) / "after.json"
        output_path = Path(tmpdir) / "human_review_diff.json"

        write_json(before_path, base_before())
        write_json(after_path, base_after())

        result = generate_human_review_diff(
            before_path=before_path,
            after_path=after_path,
            output_path=output_path,
            reviewer_note="human approved with edits",
        )

        assert result["status"] == "PASS"
        assert result["review_diff_generated"] is True
        assert output_path.exists()

        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert "before_json" in saved
        assert "after_json" in saved
        assert "changed_fields" in saved
        assert saved["reviewer_note"] == "human approved with edits"
        assert len(saved["changed_fields"]) >= 1


def test_generate_diff_contains_expected_changed_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        before_path = Path(tmpdir) / "before.json"
        after_path = Path(tmpdir) / "after.json"
        output_path = Path(tmpdir) / "human_review_diff.json"

        write_json(before_path, base_before())
        write_json(after_path, base_after())

        result = generate_human_review_diff(before_path, after_path, output_path=output_path)

        paths = {item["path"] for item in result["changed_fields"]}
        assert "reason" in paths
        assert "score" in paths
        assert "reviewer_note" in paths


def test_dangerous_operation_results_in_abort():
    with tempfile.TemporaryDirectory() as tmpdir:
        before_path = Path(tmpdir) / "before.json"
        after_path = Path(tmpdir) / "after.json"
        output_path = Path(tmpdir) / "human_review_diff.json"

        after = base_after()
        after["auto_post"] = True

        write_json(before_path, base_before())
        write_json(after_path, after)

        result = generate_human_review_diff(before_path, after_path, output_path=output_path)

        assert result["status"] == "ABORT"
        assert "dangerous" in result["reason"]
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["production_status"] == "NO_GO"


def test_existing_output_without_overwrite_aborts():
    with tempfile.TemporaryDirectory() as tmpdir:
        before_path = Path(tmpdir) / "before.json"
        after_path = Path(tmpdir) / "after.json"
        output_path = Path(tmpdir) / "human_review_diff.json"

        write_json(before_path, base_before())
        write_json(after_path, base_after())
        write_json(output_path, {"existing": True})

        result = generate_human_review_diff(before_path, after_path, output_path=output_path, overwrite=False)

        assert result["status"] == "ABORT"
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved == {"existing": True}