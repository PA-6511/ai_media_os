from pathlib import Path

from dev_agent.file_bridge import REPO_ROOT
from dev_agent.write_bridge import replace_probe_text


TEST_FILE = (
    REPO_ROOT
    / "dev_agent"
    / "probes"
    / "_write_bridge_test_target.py"
)


def test_allowed_probe_replacement():
    TEST_FILE.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    try:
        result = replace_probe_text(
            "dev_agent/probes/_write_bridge_test_target.py",
            "value = 1",
            "value = 2",
        )

        assert result["status"] == "EXECUTED"
        assert TEST_FILE.read_text(
            encoding="utf-8"
        ) == "value = 2\n"

    finally:
        TEST_FILE.unlink(missing_ok=True)


def test_write_outside_probe_root_denied():
    result = replace_probe_text(
        "dev_agent/command_bridge.py",
        "DEFAULT_TIMEOUT = 120",
        "DEFAULT_TIMEOUT = 999",
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "WRITE_OUTSIDE_PROBE_ROOT"


def test_non_python_denied():
    result = replace_probe_text(
        "dev_agent/probes/test.txt",
        "a",
        "b",
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "ONLY_PYTHON_FILES_ALLOWED"


def test_missing_old_text_rejected():
    TEST_FILE.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    try:
        result = replace_probe_text(
            "dev_agent/probes/_write_bridge_test_target.py",
            "does_not_exist",
            "value = 2",
        )

        assert result["status"] == "ERROR"
        assert result["reason"] == "OLD_TEXT_NOT_FOUND"

    finally:
        TEST_FILE.unlink(missing_ok=True)


def test_non_unique_old_text_rejected():
    TEST_FILE.write_text(
        "value = 1\nvalue = 1\n",
        encoding="utf-8",
    )

    try:
        result = replace_probe_text(
            "dev_agent/probes/_write_bridge_test_target.py",
            "value = 1",
            "value = 2",
        )

        assert result["status"] == "ERROR"
        assert result["reason"] == "OLD_TEXT_NOT_UNIQUE:2"

    finally:
        TEST_FILE.unlink(missing_ok=True)


def test_exact_file_bridge_allows_only_listed_file():
    from dev_agent.write_bridge import replace_approved_text

    target = (
        REPO_ROOT
        / "dev_agent"
        / "probes"
        / "_exact_bridge_test.py"
    )

    target.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    try:
        result = replace_approved_text(
            "dev_agent/probes/_exact_bridge_test.py",
            "value = 1",
            "value = 2",
            {
                "dev_agent/probes/_exact_bridge_test.py"
            },
        )

        assert result["status"] == "EXECUTED"
        assert target.read_text(
            encoding="utf-8"
        ) == "value = 2\n"

    finally:
        target.unlink(missing_ok=True)


def test_exact_file_bridge_denies_unlisted_file():
    from dev_agent.write_bridge import replace_approved_text

    result = replace_approved_text(
        "dev_agent/command_bridge.py",
        "DEFAULT_TIMEOUT = 120",
        "DEFAULT_TIMEOUT = 999",
        {
            "dev_agent/probes/"
            "intentional_failure_probe.py"
        },
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "BRIDGE_FILE_NOT_ALLOWED"
