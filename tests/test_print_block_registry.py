import json

from tools.print_block_registry import format_block_registry_report, main


def test_format_block_registry_report_includes_blocks_and_summary() -> None:
    registry = {
        "blocks": [
            {"block_id": "ebook_affiliate_block", "risk_level": "medium", "valid": True},
            {"block_id": "generic_block", "risk_level": "low", "valid": True},
        ],
        "summary": {
            "total": 2,
            "valid": 2,
            "invalid": 0,
            "warnings": 0,
            "errors": 0,
        },
    }

    report = format_block_registry_report(registry)

    assert "BLOCK REGISTRY" in report
    assert "- ebook_affiliate_block | medium | valid" in report
    assert "- generic_block | low | valid" in report
    assert "summary:" in report
    assert "total: 2" in report
    assert "valid: 2" in report
    assert "invalid: 0" in report
    assert "warnings: 0" in report
    assert "errors: 0" in report


def test_main_prints_report_for_repo_root(capsys) -> None:
    exit_code = main(["--root", "."])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "BLOCK REGISTRY" in captured.out
    assert "- ebook_affiliate_block | medium | valid" in captured.out
    assert "- generic_block | low | valid" in captured.out
    assert "summary:" in captured.out


def test_main_marks_invalid_manifest(tmp_path, capsys) -> None:
    good_dir = tmp_path / "valid_block"
    good_dir.mkdir(parents=True, exist_ok=True)
    (good_dir / "block_manifest.json").write_text(
        json.dumps(
            {
                "block_id": "valid_block",
                "risk_level": "low",
                "mode": "dry_run",
                "approval_policy": {
                    "requires_human_approval": True,
                    "auto_execute_allowed": False,
                },
                "forbidden_actions": ["delete_block"],
                "capabilities": {
                    "publish_content": False,
                    "delete_data": False,
                    "change_config": False,
                },
            }
        ),
        encoding="utf-8",
    )

    bad_dir = tmp_path / "invalid_block"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "block_manifest.json").write_text("{not json", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "- valid_block | low | valid" in captured.out
    assert "- unknown | unknown | invalid" in captured.out
    assert "total: 2" in captured.out
    assert "valid: 1" in captured.out
    assert "invalid: 1" in captured.out