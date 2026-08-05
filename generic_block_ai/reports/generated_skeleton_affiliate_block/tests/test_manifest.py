"""Manifest smoke-tests for affiliate_block."""


def test_manifest_block_id(manifest_data):
    assert manifest_data["block_id"] == "affiliate_block"


def test_manifest_mode(manifest_data):
    assert manifest_data["mode"] == "dry_run"


def test_manifest_operation_mode(manifest_data):
    assert manifest_data["operation_mode"] == "OBSERVE"


def test_manifest_requires_human_approval(manifest_data):
    assert manifest_data["approval_policy"]["requires_human_approval"] is True


def test_manifest_auto_execute_not_allowed(manifest_data):
    assert manifest_data["approval_policy"]["auto_execute_allowed"] is False


def test_manifest_capabilities(manifest_data):
    assert manifest_data["capabilities"]["collect_data"] is True
    assert manifest_data["capabilities"]["analyze"] is True
    assert manifest_data["capabilities"]["generate_report"] is True
    assert manifest_data["capabilities"]["notify_slack"] is True
    assert manifest_data["capabilities"]["publish_content"] is False
    assert manifest_data["capabilities"]["delete_data"] is False
    assert manifest_data["capabilities"]["change_config"] is False
