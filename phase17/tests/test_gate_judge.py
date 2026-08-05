from phase17.approval.gate_judge import judge_approval_gate


def test_gate_judge_approve_passes() -> None:
    result = judge_approval_gate({"status": "PASS", "decision": "APPROVE"})
    assert result["gate_status"] == "PASS_APPROVED"
    assert result["can_proceed"] is True


def test_gate_judge_reject_blocks() -> None:
    result = judge_approval_gate({"status": "PASS", "decision": "REJECT"})
    assert result["gate_status"] == "FAIL_REJECTED"
    assert result["can_proceed"] is False


def test_gate_judge_needs_revision_warns() -> None:
    result = judge_approval_gate({"status": "PASS", "decision": "NEEDS_REVISION"})
    assert result["gate_status"] == "WARN_NEEDS_REVISION"
    assert result["can_proceed"] is False


def test_gate_judge_pending_warns() -> None:
    result = judge_approval_gate({"status": "WARN", "decision": "PENDING"})
    assert result["gate_status"] == "WARN_PENDING_REVIEW"
    assert result["can_proceed"] is False


def test_gate_judge_unknown_decision_fails_invalid() -> None:
    result = judge_approval_gate({"status": "PASS", "decision": "WHATEVER"})
    assert result["gate_status"] == "FAIL_INVALID_APPROVAL"
    assert result["can_proceed"] is False


def test_no_apply_logic_in_package_approval_gate() -> None:
    import phase17.approval.approval_reader as approval_reader
    import phase17.approval.gate_judge as gate_judge
    import phase17.package.package_builder as package_builder

    forbidden_tokens = [
        "apply_file_change",
        "auto_merge",
        "merge_pull_request",
        "AUTO_POST",
        "AUTO_UPDATE",
        "AUTO_DELETE",
        "AUTO_EXPORT",
    ]

    source_blob = "\n".join(
        [
            open(approval_reader.__file__, "r", encoding="utf-8").read(),
            open(gate_judge.__file__, "r", encoding="utf-8").read(),
            open(package_builder.__file__, "r", encoding="utf-8").read(),
        ]
    )

    for token in forbidden_tokens:
        assert token not in source_blob
