from __future__ import annotations

import base64
import json
import re
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest


LAST_AUTH_HEADER = ""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _base_policy() -> dict[str, Any]:
    return {"phase": "LS-NEW-12"}


def _base_schema() -> dict[str, Any]:
    return {"phase": "LS-NEW-12"}


def _base_ls11_result() -> dict[str, Any]:
    return {
        "status": "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_READY_NO_WRITE",
        "ready_for_ls_new_12": True,
        "credential_env_exists": True,
        "credential_existence_check_executed": True,
        "credential_env_read_executed": True,
        "required_url_key_present": True,
        "required_username_key_present": True,
        "required_app_password_key_present": True,
        "required_url_value_nonempty": True,
        "required_username_value_nonempty": True,
        "required_app_password_value_nonempty": True,
        "wordpress_rest_index_get_succeeded": True,
        "wordpress_rest_response_body_saved": False,
        "wordpress_authenticated_get_executed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
    }


def _base_ls11_validation() -> dict[str, Any]:
    return {"validation_status": "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"}


def _base_ls11_manifest() -> dict[str, Any]:
    return {"phase": "LS-NEW-11"}


def _base_ls11_credential_summary() -> dict[str, Any]:
    return {"phase": "LS-NEW-11"}


def _base_ls11_wp_connectivity() -> dict[str, Any]:
    return {"phase": "LS-NEW-11"}


def _base_ls11_no_write_contract() -> dict[str, Any]:
    return {"phase": "LS-NEW-11"}


def _base_ls11_handoff() -> dict[str, Any]:
    return {"phase": "LS-NEW-11"}


class _AuthHandler(BaseHTTPRequestHandler):
    status_code = 200
    expected_endpoint = "/wp-json/wp/v2/users/me?context=edit"

    def do_GET(self) -> None:  # noqa: N802
        global LAST_AUTH_HEADER
        if self.path != self.expected_endpoint:
            self.send_response(404)
            self.end_headers()
            return

        LAST_AUTH_HEADER = str(self.headers.get("Authorization", ""))
        if not LAST_AUTH_HEADER.startswith("Basic "):
            self.send_response(401)
            self.end_headers()
            return

        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"id": 123, "name": "hidden"}')

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def _start_http_server(status_code: int = 200, endpoint: str = "/wp-json/wp/v2/users/me?context=edit") -> tuple[HTTPServer, str]:
    _AuthHandler.status_code = status_code
    _AuthHandler.expected_endpoint = endpoint
    server = HTTPServer(("127.0.0.1", 0), _AuthHandler)
    host, port = server.server_address
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    return server, f"http://{host}:{port}"


def _unused_base_url() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def _prepare(tmp_path: Path, base_url: str | None = None) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls11_result": tmp_path / "in/ls11_result.json",
        "ls11_validation": tmp_path / "in/ls11_validation.json",
        "ls11_manifest": tmp_path / "in/ls11_manifest.json",
        "ls11_credential_summary": tmp_path / "in/ls11_credential_summary.json",
        "ls11_wp_connectivity": tmp_path / "in/ls11_wp_connectivity.json",
        "ls11_no_write_contract": tmp_path / "in/ls11_no_write_contract.json",
        "ls11_handoff": tmp_path / "in/ls11_handoff.json",
        "credential_env": tmp_path / "in/credential.env",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls11_result"], _base_ls11_result())
    _write_json(p["ls11_validation"], _base_ls11_validation())
    _write_json(p["ls11_manifest"], _base_ls11_manifest())
    _write_json(p["ls11_credential_summary"], _base_ls11_credential_summary())
    _write_json(p["ls11_wp_connectivity"], _base_ls11_wp_connectivity())
    _write_json(p["ls11_no_write_contract"], _base_ls11_no_write_contract())
    _write_json(p["ls11_handoff"], _base_ls11_handoff())
    url = base_url or "http://127.0.0.1:9"
    _write_env(
        p["credential_env"],
        [
            f"WP_BASE_URL={url}",
            "WP_USERNAME=test-user",
            "WP_APP_PASSWORD=test-password",
        ],
    )
    return p


def _all_flags() -> list[str]:
    return [
        "--allow-credential-env-existence-check",
        "--allow-credential-env-read",
        "--allow-authenticated-wp-read-get",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-wordpress-update",
        "--require-no-wordpress-delete",
        "--require-no-runner-execution",
        "--require-no-final-execution-command",
        "--require-no-generic-external-fetch",
        "--require-no-web-scraping",
        "--require-no-rss-fetch",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-credential-value-output",
        "--require-no-credential-secret-output",
        "--require-no-credential-length-output",
        "--require-no-credential-hash-output",
        "--require-no-authorization-output",
        "--require-no-basic-auth-output",
        "--require-no-base64-auth-output",
        "--require-no-response-body-output",
        "--require-no-user-identity-output",
        "--require-no-response-body-save",
        "--require-no-user-identity-save",
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None, endpoint: str | None = None) -> subprocess.CompletedProcess[str]:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "authenticated_read_result": tmp_path / "out/authenticated_read_result.json",
        "secret_non_output_summary": tmp_path / "out/secret_non_output_summary.json",
        "safety_contract": tmp_path / "out/safety_contract.json",
        "draft_hold": tmp_path / "out/draft_hold.json",
        "handoff": tmp_path / "out/handoff.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new12_authenticated_wp_read_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new11-result",
        str(p["ls11_result"]),
        "--ls-new11-validation-result",
        str(p["ls11_validation"]),
        "--ls-new11-manifest",
        str(p["ls11_manifest"]),
        "--ls-new11-credential-summary",
        str(p["ls11_credential_summary"]),
        "--ls-new11-wp-connectivity-result",
        str(p["ls11_wp_connectivity"]),
        "--ls-new11-no-write-safety-contract",
        str(p["ls11_no_write_contract"]),
        "--ls-new11-next-phase-handoff",
        str(p["ls11_handoff"]),
        "--credential-env",
        str(p["credential_env"]),
        "--connect-timeout-seconds",
        "2",
        "--output-manifest",
        str(out["manifest"]),
        "--output-authenticated-read-result",
        str(out["authenticated_read_result"]),
        "--output-secret-non-output-summary",
        str(out["secret_non_output_summary"]),
        "--output-no-write-safety-contract",
        str(out["safety_contract"]),
        "--output-draft-creation-hold-boundary",
        str(out["draft_hold"]),
        "--output-next-phase-handoff",
        str(out["handoff"]),
        "--output-summary",
        str(out["summary"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]
    if endpoint:
        cmd.extend(["--authenticated-read-endpoint", endpoint])
    cmd.extend(_all_flags() if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_build_success(tmp_path: Path) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        res = _run(tmp_path, p)
        assert res.returncode == 0
        out = _load(tmp_path / "out/result.json")
        assert out["status"] == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE"
        assert out["wordpress_authenticated_read_get_succeeded"] is True
        assert out["wordpress_authenticated_read_status_class"] == "2xx"
        assert out["ready_for_ls_new_13"] is True
    finally:
        server.shutdown()


def test_authenticated_read_network_error_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_FAILED_NO_WRITE"
    assert out["wordpress_authenticated_read_status_class"] == "NETWORK_ERROR"


@pytest.mark.parametrize("status_code,cls", [(401, "4xx"), (403, "4xx")])
def test_authenticated_read_4xx_fails(tmp_path: Path, status_code: int, cls: str) -> None:
    server, base_url = _start_http_server(status_code)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        res = _run(tmp_path, p)
        assert res.returncode != 0
        out = _load(tmp_path / "out/result.json")
        assert out["wordpress_authenticated_read_status_class"] == cls
        assert out["wordpress_authenticated_read_get_succeeded"] is False
    finally:
        server.shutdown()


def test_authenticated_header_is_built_and_sent(tmp_path: Path) -> None:
    global LAST_AUTH_HEADER
    LAST_AUTH_HEADER = ""
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _write_env(
            p["credential_env"],
            [
                f"WP_BASE_URL={base_url}",
                "WP_USERNAME=user-a",
                "WP_APP_PASSWORD=pass-a",
            ],
        )
        res = _run(tmp_path, p)
        assert res.returncode == 0
        assert LAST_AUTH_HEADER.startswith("Basic ")
        decoded = base64.b64decode(LAST_AUTH_HEADER.split(" ", 1)[1]).decode("utf-8")
        assert decoded == "user-a:pass-a"
    finally:
        server.shutdown()


@pytest.mark.parametrize("missing", [
    "ls11_validation",
    "ls11_result",
    "ls11_manifest",
    "ls11_credential_summary",
    "ls11_wp_connectivity",
    "ls11_no_write_contract",
    "ls11_handoff",
])
def test_missing_previous_inputs_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_FAILED_NO_WRITE"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls11_validation", "validation_status", "BAD", "ls-new11 validation status mismatch"),
        ("ls11_result", "status", "BAD", "ls-new11 run status mismatch"),
        ("ls11_result", "ready_for_ls_new_12", False, "ls-new11 ready_for_ls_new_12 mismatch"),
        ("ls11_result", "credential_env_exists", False, "ls-new11 credential_env_exists mismatch"),
        ("ls11_result", "credential_existence_check_executed", False, "ls-new11 credential_existence_check_executed mismatch"),
        ("ls11_result", "credential_env_read_executed", False, "ls-new11 credential_env_read_executed mismatch"),
        ("ls11_result", "required_url_key_present", False, "ls-new11 required_url_key_present mismatch"),
        ("ls11_result", "required_username_key_present", False, "ls-new11 required_username_key_present mismatch"),
        ("ls11_result", "required_app_password_key_present", False, "ls-new11 required_app_password_key_present mismatch"),
        ("ls11_result", "required_url_value_nonempty", False, "ls-new11 required_url_value_nonempty mismatch"),
        ("ls11_result", "required_username_value_nonempty", False, "ls-new11 required_username_value_nonempty mismatch"),
        ("ls11_result", "required_app_password_value_nonempty", False, "ls-new11 required_app_password_value_nonempty mismatch"),
        ("ls11_result", "wordpress_rest_index_get_succeeded", False, "ls-new11 wordpress_rest_index_get_succeeded mismatch"),
        ("ls11_result", "wordpress_rest_response_body_saved", True, "ls-new11 wordpress_rest_response_body_saved mismatch"),
        ("ls11_result", "wordpress_authenticated_get_executed", True, "ls-new11 wordpress_authenticated_get_executed mismatch"),
        ("ls11_result", "execution_allowed", True, "ls-new11 execution_allowed mismatch"),
        ("ls11_result", "runner_execution_allowed", True, "ls-new11 runner_execution_allowed mismatch"),
        ("ls11_result", "final_execution_command_created", True, "ls-new11 final_execution_command_created mismatch"),
        ("ls11_result", "wordpress_write_executed", True, "ls-new11 wordpress_write_executed mismatch"),
        ("ls11_result", "wordpress_draft_created", True, "ls-new11 wordpress_draft_created mismatch"),
        ("ls11_result", "wordpress_publish_executed", True, "ls-new11 wordpress_publish_executed mismatch"),
        ("ls11_result", "wordpress_update_executed", True, "ls-new11 wordpress_update_executed mismatch"),
        ("ls11_result", "wordpress_delete_executed", True, "ls-new11 wordpress_delete_executed mismatch"),
        ("ls11_result", "target_post_id", 100, "ls-new11 target_post_id must be null"),
        ("ls11_result", "target_post_id_allocated", True, "ls-new11 target_post_id_allocated mismatch"),
        ("ls11_result", "approval_label_consumed", True, "ls-new11 approval_label_consumed mismatch"),
        ("ls11_manifest", "phase", "BAD", "ls-new11 manifest phase mismatch"),
        ("ls11_credential_summary", "phase", "BAD", "ls-new11 credential-summary phase mismatch"),
        ("ls11_wp_connectivity", "phase", "BAD", "ls-new11 wp-connectivity-result phase mismatch"),
        ("ls11_no_write_contract", "phase", "BAD", "ls-new11 no-write-safety-contract phase mismatch"),
        ("ls11_handoff", "phase", "BAD", "ls-new11 next-phase-handoff phase mismatch"),
    ],
)
def test_previous_phase_gate_failures(tmp_path: Path, target: str, key: str, value: Any, error: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert error in out["errors"]


@pytest.mark.parametrize("missing_flag", _all_flags())
def test_missing_flags_fail(tmp_path: Path, missing_flag: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    flags = [f for f in _all_flags() if f != missing_flag]
    res = _run(tmp_path, p, flags=flags)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert any(missing_flag in e for e in out["errors"])


def test_missing_credential_env_fail(tmp_path: Path) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    p["credential_env"].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert "credential env missing" in out["errors"]


@pytest.mark.parametrize(
    "env_lines,error",
    [
        (["WP_USERNAME=u", "WP_APP_PASSWORD=p"], "required URL key missing"),
        (["WP_BASE_URL=http://127.0.0.1:9", "WP_APP_PASSWORD=p"], "required username key missing"),
        (["WP_BASE_URL=http://127.0.0.1:9", "WP_USERNAME=u"], "required app password key missing"),
        (["WP_BASE_URL=", "WP_USERNAME=u", "WP_APP_PASSWORD=p"], "required URL empty"),
        (["WP_BASE_URL=http://127.0.0.1:9", "WP_USERNAME=", "WP_APP_PASSWORD=p"], "required username empty"),
        (["WP_BASE_URL=http://127.0.0.1:9", "WP_USERNAME=u", "WP_APP_PASSWORD="], "required app password empty"),
    ],
)
def test_credential_key_and_nonempty_failures(tmp_path: Path, env_lines: list[str], error: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    _write_env(p["credential_env"], env_lines)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "url_key,user_key,pass_key",
    [
        ("WP_BASE_URL", "WP_USERNAME", "WP_APP_PASSWORD"),
        ("WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"),
        ("WP_SITE_URL", "WP_USER", "WP_APPLICATION_PASSWORD"),
        ("WORDPRESS_SITE_URL", "WORDPRESS_USER", "WORDPRESS_APPLICATION_PASSWORD"),
    ],
)
def test_credential_aliases_supported(tmp_path: Path, url_key: str, user_key: str, pass_key: str) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _write_env(
            p["credential_env"],
            [
                f"{url_key}={base_url}",
                f"{user_key}=u",
                f"{pass_key}=p",
            ],
        )
        res = _run(tmp_path, p)
        assert res.returncode == 0
        out = _load(tmp_path / "out/result.json")
        assert out["credential_env_exists"] is True
        assert out["credential_existence_check_executed"] is True
        assert out["credential_env_read_executed"] is True
    finally:
        server.shutdown()


def test_custom_authenticated_endpoint_supported(tmp_path: Path) -> None:
    endpoint = "/wp-json/wp/v2/users/me?context=edit"
    server, base_url = _start_http_server(200, endpoint=endpoint)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        res = _run(tmp_path, p, endpoint=endpoint)
        assert res.returncode == 0
        out = _load(tmp_path / "out/result.json")
        assert out["wordpress_authenticated_read_endpoint_kind"] == "users_me"
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    "key",
    [
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
        "x_api_call_executed",
        "x_post_executed",
        "generic_external_fetch_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "response_body_output",
        "user_identity_output",
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ],
)
def test_result_forbidden_flags_false(tmp_path: Path, key: str) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _run(tmp_path, p)
        out = _load(tmp_path / "out/result.json")
        assert out[key] is False
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    "path_key,doc_type",
    [
        ("manifest", "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_MANIFEST"),
        ("authenticated_read_result", "START_LS_NEW12_AUTHENTICATED_WP_READ_RESULT"),
        ("secret_non_output_summary", "START_LS_NEW12_SECRET_NON_OUTPUT_SUMMARY"),
        ("safety_contract", "START_LS_NEW12_NO_WRITE_SAFETY_CONTRACT"),
        ("draft_hold", "START_LS_NEW12_DRAFT_CREATION_HOLD_BOUNDARY"),
        ("handoff", "START_LS_NEW12_NEXT_PHASE_HANDOFF"),
        ("result", "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_RESULT"),
        ("lock", "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCK"),
    ],
)
def test_generated_document_types(tmp_path: Path, path_key: str, doc_type: str) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _run(tmp_path, p)
        obj = _load(tmp_path / f"out/{path_key}.json")
        assert obj["document_type"] == doc_type
    finally:
        server.shutdown()


def test_target_post_id_stays_null(tmp_path: Path) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _run(tmp_path, p)
        out = _load(tmp_path / "out/result.json")
        assert out["target_post_id"] is None
        assert out["target_post_id_allocated"] is False
    finally:
        server.shutdown()


def test_sensitive_data_not_in_outputs(tmp_path: Path) -> None:
    server, base_url = _start_http_server(200)
    try:
        p = _prepare(tmp_path, base_url=base_url)
        secret_user = "user-secret-value"
        secret_pass = "pass-secret-value"
        _write_env(
            p["credential_env"],
            [
                f"WP_BASE_URL={base_url}",
                f"WP_USERNAME={secret_user}",
                f"WP_APP_PASSWORD={secret_pass}",
            ],
        )
        _run(tmp_path, p)
        blob = "\n".join(
            [
                (tmp_path / "out/manifest.json").read_text(encoding="utf-8"),
                (tmp_path / "out/authenticated_read_result.json").read_text(encoding="utf-8"),
                (tmp_path / "out/secret_non_output_summary.json").read_text(encoding="utf-8"),
                (tmp_path / "out/result.json").read_text(encoding="utf-8"),
                (tmp_path / "out/summary.md").read_text(encoding="utf-8"),
                (tmp_path / "out/report.md").read_text(encoding="utf-8"),
            ]
        )
        assert secret_user not in blob
        assert secret_pass not in blob
        assert "Authorization:" not in blob
        assert re.search(r"Basic [A-Za-z0-9+/=]{20,}", blob) is None
        assert '"id": 123' not in blob
        assert "hidden" not in blob
    finally:
        server.shutdown()


def test_source_code_no_forbidden_output_patterns() -> None:
    src = Path("scripts/build_start_ls_new12_authenticated_wp_read_preflight.py").read_text(encoding="utf-8")
    forbidden = [
        "print(credential",
        "print(password",
        "print(secret",
        "print(Authorization",
        "print(Basic",
        "logger.credential",
        "logger.password",
        "logger.secret",
        "response.read().write",
    ]
    assert all(x not in src for x in forbidden)


def test_auth_endpoint_path_shape() -> None:
    p = urlparse("http://x/wp-json/wp/v2/users/me?context=edit")
    assert p.path == "/wp-json/wp/v2/users/me"
    assert p.query == "context=edit"
