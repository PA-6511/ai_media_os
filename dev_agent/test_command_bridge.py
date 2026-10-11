from dev_agent.command_bridge import validate_command, run_command, REPO_ROOT


def test_git_status_allowed():
    allowed, argv = validate_command("git status --short")
    assert allowed is True
    assert argv == ["git", "status", "--short"]


def test_sudo_denied():
    allowed, reason = validate_command(
        "sudo systemctl restart ai-media-os"
    )
    assert allowed is False
    assert reason == "COMMAND_NOT_ALLOWED:sudo"


def test_shell_chain_denied():
    allowed, reason = validate_command(
        "git status && rm -rf something"
    )
    assert allowed is False
    assert reason.startswith("FORBIDDEN_SHELL_TOKEN:")


def test_absolute_path_denied():
    allowed, reason = validate_command(
        "ls /etc"
    )
    assert allowed is False
    assert reason == "ABSOLUTE_PATH_NOT_ALLOWED:/etc"


def test_parent_path_denied():
    allowed, reason = validate_command(
        "ls ../"
    )
    assert allowed is False
    assert reason.startswith("PARENT_PATH_NOT_ALLOWED:")


def test_git_no_index_denied():
    allowed, reason = validate_command(
        "git diff --no-index file1 file2"
    )
    assert allowed is False
    assert reason == "GIT_OPTION_NOT_ALLOWED:--no-index"


def test_repo_git_status_executes():
    result = run_command(
        "git status --short -- dev_agent/",
        str(REPO_ROOT),
        30,
    )

    assert result["status"] == "EXECUTED"
    assert result["exit_code"] == 0


def test_outside_cwd_denied():
    result = run_command(
        "pwd",
        "/tmp",
        30,
    )

    assert result["status"] == "DENIED"
    assert result["reason"] == "CWD_OUTSIDE_REPO"


def test_execution_env_prefers_dev_agent_venv():
    import os

    from dev_agent.command_bridge import (
        DEV_AGENT_VENV_BIN,
        build_execution_env,
    )

    env = build_execution_env()
    first_path = env["PATH"].split(os.pathsep)[0]

    assert first_path == str(DEV_AGENT_VENV_BIN)
    assert env["PYTHONNOUSERSITE"] == "1"
