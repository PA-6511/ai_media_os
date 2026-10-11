from dev_agent.agent_loop import dispatch_tool


def test_dispatch_git_status():
    result = dispatch_tool(
        "run_command",
        {
            "command": "git status --short -- dev_agent/",
        },
    )

    assert result["status"] == "EXECUTED"
    assert result["exit_code"] == 0


def test_dispatch_sudo_denied():
    result = dispatch_tool(
        "run_command",
        {
            "command": "sudo systemctl restart ai-media-os",
        },
    )

    assert result["status"] == "DENIED"


def test_dispatch_absolute_path_denied():
    result = dispatch_tool(
        "run_command",
        {
            "command": "ls /etc",
        },
    )

    assert result["status"] == "DENIED"


def test_unknown_tool_denied():
    result = dispatch_tool(
        "unknown_tool",
        {
            "command": "pwd",
        },
    )

    assert result["status"] == "ERROR"
    assert result["reason"].startswith("UNKNOWN_TOOL:")


def test_dispatch_read_file():
    result = dispatch_tool(
        "read_file",
        {
            "relative_path": "dev_agent/command_bridge.py",
            "start_line": 1,
            "end_line": 10,
        },
    )

    assert result["status"] == "EXECUTED"


def test_dispatch_read_file_escape_denied():
    result = dispatch_tool(
        "read_file",
        {
            "relative_path": "../etc/passwd",
            "start_line": 1,
            "end_line": 10,
        },
    )

    assert result["status"] == "DENIED"


def test_dispatch_replace_outside_probe_denied():
    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": "dev_agent/command_bridge.py",
            "old_text": "DEFAULT_TIMEOUT = 120",
            "new_text": "DEFAULT_TIMEOUT = 999",
        },
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "WRITE_OUTSIDE_PROBE_ROOT"


def test_dispatch_replace_probe_unapproved():
    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": (
                "dev_agent/probes/"
                "intentional_failure_probe.py"
            ),
            "old_text": "actual = 7",
            "new_text": "actual = 10",
        },
    )

    assert result["status"] == "APPROVAL_REQUIRED"
    assert result["reason"] == "FILE_WRITE_APPROVAL_REQUIRED"


def test_dispatch_replace_wrong_file_approval_denied():
    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": (
                "dev_agent/probes/"
                "intentional_failure_probe.py"
            ),
            "old_text": "actual = 7",
            "new_text": "actual = 10",
        },
        approved_write_files={
            "dev_agent/probes/some_other_probe.py"
        },
    )

    assert result["status"] == "APPROVAL_REQUIRED"
    assert result["reason"] == "FILE_WRITE_APPROVAL_REQUIRED"


def test_dispatch_replace_exact_file_approval_allowed():
    from dev_agent.file_bridge import REPO_ROOT

    target = (
        REPO_ROOT
        / "dev_agent"
        / "probes"
        / "_agent_replace_test.py"
    )

    target.write_text(
        "answer = 1\n",
        encoding="utf-8",
    )

    try:
        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": (
                    "dev_agent/probes/"
                    "_agent_replace_test.py"
                ),
                "old_text": "answer = 1",
                "new_text": "answer = 2",
            },
            approved_write_files={
                "dev_agent/probes/"
                "_agent_replace_test.py"
            },
        )

        assert result["status"] == "EXECUTED"
        assert target.read_text(
            encoding="utf-8"
        ) == "answer = 2\n"

    finally:
        target.unlink(missing_ok=True)



def test_write_audit_records_approved_execution():
    from dev_agent.file_bridge import REPO_ROOT

    target = (
        REPO_ROOT
        / "dev_agent"
        / "probes"
        / "_write_audit_test.py"
    )

    target.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    audit = []

    try:
        write_result = dispatch_tool(
            "replace_text",
            {
                "relative_path": (
                    "dev_agent/probes/"
                    "_write_audit_test.py"
                ),
                "old_text": "value = 1",
                "new_text": "value = 2",
            },
            approved_write_files={
                "dev_agent/probes/"
                "_write_audit_test.py"
            },
            write_audit=audit,
        )

        assert write_result["status"] == "EXECUTED"

        audit_result = dispatch_tool(
            "get_write_audit",
            {},
            approved_write_files={
                "dev_agent/probes/"
                "_write_audit_test.py"
            },
            write_audit=audit,
        )

        assert audit_result["result"] == "PASS"
        assert audit_result["executed_write_files"] == [
            "dev_agent/probes/_write_audit_test.py"
        ]
        assert (
            audit_result[
                "unexpected_executed_write_files"
            ]
            == []
        )

    finally:
        target.unlink(missing_ok=True)


def test_write_audit_records_blocked_wrong_file():
    audit = []

    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": (
                "dev_agent/probes/"
                "intentional_failure_probe.py"
            ),
            "old_text": "actual = 7",
            "new_text": "actual = 10",
        },
        approved_write_files={
            "dev_agent/probes/some_other_probe.py"
        },
        write_audit=audit,
    )

    assert result["status"] == "APPROVAL_REQUIRED"

    audit_result = dispatch_tool(
        "get_write_audit",
        {},
        approved_write_files={
            "dev_agent/probes/some_other_probe.py"
        },
        write_audit=audit,
    )

    assert audit_result["result"] == "PASS"
    assert audit_result["executed_write_files"] == []
    assert (
        audit_result[
            "unexpected_executed_write_files"
        ]
        == []
    )
    assert (
        audit_result["write_attempts"][0]["status"]
        == "APPROVAL_REQUIRED"
    )


def test_4a_canary_requires_exact_human_approval():
    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": (
                "app/services/"
                "ebook_new_release_autonomy_shadow_compare.py"
            ),
            "old_text": "old",
            "new_text": "new",
        },
    )

    assert result["status"] == "APPROVAL_REQUIRED"
    assert result["reason"] == "FILE_WRITE_APPROVAL_REQUIRED"


def test_4a_non_canary_app_file_still_denied():
    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": "app/services/csv_import_service.py",
            "old_text": "old",
            "new_text": "new",
        },
        approved_write_files={
            "app/services/csv_import_service.py"
        },
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "WRITE_OUTSIDE_PROBE_ROOT"


def test_4a_approved_canary_routes_through_exact_bridge():
    from unittest.mock import patch

    from dev_agent.write_bridge import CANARY_WRITE_FILES

    target = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    audit = []

    fake_result = {
        "status": "EXECUTED",
        "path": target,
        "replacement_count": 1,
        "before_sha256": "before",
        "after_sha256": "after",
    }

    with patch(
        "dev_agent.agent_loop.replace_approved_text",
        return_value=fake_result,
    ) as mocked:
        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": target,
                "old_text": "old",
                "new_text": "new",
            },
            approved_write_files={target},
            write_audit=audit,
        )

    assert result["status"] == "EXECUTED"

    mocked.assert_called_once_with(
        relative_path=target,
        old_text="old",
        new_text="new",
        bridge_allowed_files=CANARY_WRITE_FILES,
    )

    assert audit == [
        {
            "path": target,
            "status": "EXECUTED",
            "reason": None,
            "before_sha256": "before",
            "after_sha256": "after",
        }
    ]


def test_4b_source_approval_does_not_approve_test_file():
    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )
    test_file = (
        "tests/services/"
        "test_ebook_new_release_autonomy_shadow_compare.py"
    )

    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": test_file,
            "old_text": "old",
            "new_text": "new",
        },
        approved_write_files={source},
    )

    assert result["status"] == "APPROVAL_REQUIRED"
    assert result["reason"] == "FILE_WRITE_APPROVAL_REQUIRED"


def test_4b_test_approval_does_not_approve_source_file():
    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )
    test_file = (
        "tests/services/"
        "test_ebook_new_release_autonomy_shadow_compare.py"
    )

    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": source,
            "old_text": "old",
            "new_text": "new",
        },
        approved_write_files={test_file},
    )

    assert result["status"] == "APPROVAL_REQUIRED"
    assert result["reason"] == "FILE_WRITE_APPROVAL_REQUIRED"


def test_4b_two_exact_approvals_are_independent():
    from unittest.mock import patch

    from dev_agent.write_bridge import CANARY_WRITE_FILES

    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )
    test_file = (
        "tests/services/"
        "test_ebook_new_release_autonomy_shadow_compare.py"
    )

    approved = {
        source,
        test_file,
    }

    audit = []

    with patch(
        "dev_agent.agent_loop.replace_approved_text"
    ) as mocked:
        mocked.side_effect = [
            {
                "status": "EXECUTED",
                "path": source,
                "replacement_count": 1,
                "before_sha256": "source-before",
                "after_sha256": "source-after",
            },
            {
                "status": "EXECUTED",
                "path": test_file,
                "replacement_count": 1,
                "before_sha256": "test-before",
                "after_sha256": "test-after",
            },
        ]

        source_result = dispatch_tool(
            "replace_text",
            {
                "relative_path": source,
                "old_text": "source-old",
                "new_text": "source-new",
            },
            approved_write_files=approved,
            write_audit=audit,
        )

        test_result = dispatch_tool(
            "replace_text",
            {
                "relative_path": test_file,
                "old_text": "test-old",
                "new_text": "test-new",
            },
            approved_write_files=approved,
            write_audit=audit,
        )

    assert source_result["status"] == "EXECUTED"
    assert test_result["status"] == "EXECUTED"

    assert mocked.call_count == 2

    for call in mocked.call_args_list:
        assert (
            call.kwargs["bridge_allowed_files"]
            == CANARY_WRITE_FILES
        )

    audit_result = dispatch_tool(
        "get_write_audit",
        {},
        approved_write_files=approved,
        write_audit=audit,
    )

    assert audit_result["result"] == "PASS"
    assert audit_result["executed_write_files"] == sorted(
        [
            source,
            test_file,
        ]
    )
    assert audit_result["unexpected_executed_write_files"] == []


def test_4c_semantic_equivalent_replacement_denied():
    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    audit = []

    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": source,
            "old_text": "_COMPARE_FIELDS = _REQUIRED_TEXT_FIELDS",
            "new_text": (
                '_COMPARE_FIELDS = '
                '_REQUIRED_TEXT_FIELDS + ("image_url",)'
            ),
        },
        approved_write_files={source},
        write_audit=audit,
        write_contract={
            "relative_path": source,
            "old_text": "_COMPARE_FIELDS = _REQUIRED_TEXT_FIELDS",
            "new_text": (
                '_COMPARE_FIELDS = '
                '(*_REQUIRED_TEXT_FIELDS, "image_url")'
            ),
        },
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "EXACT_NEW_TEXT_MISMATCH"

    assert audit[-1]["status"] == "DENIED"
    assert (
        audit[-1]["reason"]
        == "EXACT_NEW_TEXT_MISMATCH"
    )


def test_4c_exact_contract_routes_to_bridge():
    from unittest.mock import patch

    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    old_text = "_COMPARE_FIELDS = _REQUIRED_TEXT_FIELDS"
    new_text = (
        '_COMPARE_FIELDS = '
        '(*_REQUIRED_TEXT_FIELDS, "image_url")'
    )

    audit = []

    with patch(
        "dev_agent.agent_loop.replace_approved_text"
    ) as mocked:
        mocked.return_value = {
            "status": "EXECUTED",
            "path": source,
            "replacement_count": 1,
            "before_sha256": "before",
            "after_sha256": "after",
        }

        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": source,
                "old_text": old_text,
                "new_text": new_text,
            },
            approved_write_files={source},
            write_audit=audit,
            write_contract={
                "relative_path": source,
                "old_text": old_text,
                "new_text": new_text,
            },
        )

    assert result["status"] == "EXECUTED"
    assert mocked.call_count == 1


def test_4e_a_proposal_tool_does_not_require_write_approval():
    from unittest.mock import patch

    target = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    audit = []

    with patch(
        "dev_agent.agent_loop.create_write_proposal"
    ) as mocked:
        mocked.return_value = {
            "status": "CREATED",
            "proposal_id": "proposal_v1_test",
            "relative_path": target,
            "old_text": "old",
            "new_text": "new",
            "before_sha256": "before",
            "source_write_performed": False,
        }

        result = dispatch_tool(
            "create_write_proposal",
            {
                "relative_path": target,
                "old_text": "old",
                "new_text": "new",
            },
            approved_write_files=set(),
            write_audit=audit,
        )

    assert result["status"] == "CREATED"
    assert result["source_write_performed"] is False
    assert audit == []


def test_4e_a_proposal_tool_passes_exact_fields():
    from unittest.mock import patch

    target = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    with patch(
        "dev_agent.agent_loop.create_write_proposal"
    ) as mocked:
        mocked.return_value = {
            "status": "CREATED",
            "proposal_id": "proposal_v1_test",
            "source_write_performed": False,
        }

        dispatch_tool(
            "create_write_proposal",
            {
                "relative_path": target,
                "old_text": "exact-old",
                "new_text": "exact-new",
            },
        )

    mocked.assert_called_once_with(
        relative_path=target,
        old_text="exact-old",
        new_text="exact-new",
    )


def test_4e_b_contract_path_mismatch_denied():
    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    other = (
        "tests/services/"
        "test_ebook_new_release_autonomy_shadow_compare.py"
    )

    result = dispatch_tool(
        "replace_text",
        {
            "relative_path": other,
            "old_text": "old",
            "new_text": "new",
        },
        approved_write_files={other},
        write_contract={
            "relative_path": source,
            "old_text": "old",
            "new_text": "new",
        },
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "EXACT_PATH_MISMATCH"


def test_4e_b_write_time_stale_sha_denied():
    from unittest.mock import patch

    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    audit = []

    with (
        patch(
            "dev_agent.agent_loop.verify_write_contract_source"
        ) as verify,
        patch(
            "dev_agent.agent_loop.replace_approved_text"
        ) as replace,
    ):
        verify.return_value = {
            "status": "DENIED",
            "reason": "STALE_PROPOSAL_SOURCE_CHANGED",
            "path": source,
            "expected_sha256": "expected",
            "current_sha256": "current",
        }

        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
            },
            approved_write_files={source},
            write_audit=audit,
            write_contract={
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
                "before_sha256": "expected",
                "proposal_id": "proposal_v1_test",
            },
        )

    assert result["status"] == "DENIED"
    assert (
        result["reason"]
        == "STALE_PROPOSAL_SOURCE_CHANGED"
    )
    replace.assert_not_called()

    assert audit[-1]["status"] == "DENIED"
    assert (
        audit[-1]["reason"]
        == "STALE_PROPOSAL_SOURCE_CHANGED"
    )


def test_4e_c_execution_claim_denial_blocks_write():
    from unittest.mock import patch

    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    audit = []

    with (
        patch(
            "dev_agent.agent_loop.verify_write_contract_source"
        ) as verify,
        patch(
            "dev_agent.agent_loop.claim_proposal_execution"
        ) as claim,
        patch(
            "dev_agent.agent_loop.replace_approved_text"
        ) as replace,
    ):
        verify.return_value = {
            "status": "VALID",
            "path": source,
            "expected_sha256": "a" * 64,
            "current_sha256": "a" * 64,
        }

        claim.return_value = {
            "status": "DENIED",
            "reason": "PROPOSAL_ALREADY_EXECUTED",
            "proposal_id": "proposal_v1_test",
        }

        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
            },
            approved_write_files={source},
            write_audit=audit,
            write_contract={
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
                "before_sha256": "a" * 64,
                "proposal_id": "proposal_v1_test",
            },
        )

    assert result["status"] == "DENIED"
    assert (
        result["reason"]
        == "PROPOSAL_ALREADY_EXECUTED"
    )
    replace.assert_not_called()


def test_4e_c_successful_write_marks_executed():
    from unittest.mock import patch

    source = (
        "app/services/"
        "ebook_new_release_autonomy_shadow_compare.py"
    )

    with (
        patch(
            "dev_agent.agent_loop.verify_write_contract_source"
        ) as verify,
        patch(
            "dev_agent.agent_loop.claim_proposal_execution"
        ) as claim,
        patch(
            "dev_agent.agent_loop.replace_approved_text"
        ) as replace,
        patch(
            "dev_agent.agent_loop.mark_proposal_executed"
        ) as mark_executed,
    ):
        verify.return_value = {
            "status": "VALID",
            "path": source,
            "expected_sha256": "a" * 64,
            "current_sha256": "a" * 64,
        }

        claim.return_value = {
            "status": "VALID",
            "proposal_state": "EXECUTING",
        }

        replace.return_value = {
            "status": "EXECUTED",
            "path": source,
            "replacement_count": 1,
            "before_sha256": "a" * 64,
            "after_sha256": "b" * 64,
        }

        mark_executed.return_value = {
            "status": "VALID",
            "proposal_state": "EXECUTED",
        }

        result = dispatch_tool(
            "replace_text",
            {
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
            },
            approved_write_files={source},
            write_contract={
                "relative_path": source,
                "old_text": "old",
                "new_text": "new",
                "before_sha256": "a" * 64,
                "proposal_id": "proposal_v1_test",
            },
        )

    assert result["status"] == "EXECUTED"
    assert (
        result["proposal_state"]
        == "EXECUTED"
    )

    claim.assert_called_once_with(
        "proposal_v1_test"
    )

    mark_executed.assert_called_once_with(
        "proposal_v1_test"
    )
