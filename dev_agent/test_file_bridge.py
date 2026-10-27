from dev_agent.file_bridge import read_repo_text


def test_repo_file_can_be_read():
    result = read_repo_text(
        "dev_agent/command_bridge.py",
        1,
        20,
    )

    assert result["status"] == "EXECUTED"
    assert "command_bridge.py" in result["path"]


def test_absolute_path_denied():
    result = read_repo_text(
        "/etc/passwd",
        1,
        10,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "ABSOLUTE_PATH_NOT_ALLOWED"


def test_parent_path_denied():
    result = read_repo_text(
        "../something.txt",
        1,
        10,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "PARENT_PATH_NOT_ALLOWED"


def test_sensitive_path_denied():
    result = read_repo_text(
        "config/credential.env",
        1,
        10,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "SENSITIVE_PATH"


def test_invalid_range_denied():
    result = read_repo_text(
        "dev_agent/command_bridge.py",
        20,
        10,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "INVALID_LINE_RANGE"


def test_large_range_denied():
    result = read_repo_text(
        "dev_agent/command_bridge.py",
        1,
        1000,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "LINE_RANGE_TOO_LARGE"
