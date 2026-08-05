from __future__ import annotations

import json
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-11"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-11"}


def _base_ls10_result() -> dict:
    return {
        "status": "LSNEW10_EXECUTION_PREP_READY_NO_DRAFT_CREATION",
        "ready_for_ls_new_11": True,
        "ls_new9_decision_validated": True,
        "ls_new9_decision_approved": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
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


def _base_ls10_validation() -> dict:
    return {"validation_status": "LSNEW10_EXECUTION_PREP_VALIDATED_NO_DRAFT_CREATION"}


def _base_ls10_manifest() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_ls10_input_map() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_ls10_dry() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_ls10_handoff() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_ls10_safety() -> dict:
    return {"phase": "LS-NEW-10"}


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/wp-json/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"name":"ok"}')
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _start_http_server() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _OkHandler)
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
        "ls10_result": tmp_path / "in/ls10_result.json",
        "ls10_validation": tmp_path / "in/ls10_validation.json",
        "ls10_manifest": tmp_path / "in/ls10_manifest.json",
        "ls10_input_map": tmp_path / "in/ls10_input_map.json",
        "ls10_dry": tmp_path / "in/ls10_dry.json",
        "ls10_handoff": tmp_path / "in/ls10_handoff.json",
        "ls10_safety": tmp_path / "in/ls10_safety.json",
        "credential_env": tmp_path / "in/credential.env",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls10_result"], _base_ls10_result())
    _write_json(p["ls10_validation"], _base_ls10_validation())
    _write_json(p["ls10_manifest"], _base_ls10_manifest())
    _write_json(p["ls10_input_map"], _base_ls10_input_map())
    _write_json(p["ls10_dry"], _base_ls10_dry())
    _write_json(p["ls10_handoff"], _base_ls10_handoff())
    _write_json(p["ls10_safety"], _base_ls10_safety())
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


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "credential_summary": tmp_path / "out/credential_summary.json",
        "wp_result": tmp_path / "out/wp_result.json",
        "safety_contract": tmp_path / "out/safety_contract.json",
        "handoff": tmp_path / "out/handoff.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new11_credential_wp_connectivity_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new10-result",
        str(p["ls10_result"]),
        "--ls-new10-validation-result",
        str(p["ls10_validation"]),
        "--ls-new10-manifest",
        str(p["ls10_manifest"]),
        "--ls-new10-input-map",
        str(p["ls10_input_map"]),
        "--ls-new10-dry-boundary",
        str(p["ls10_dry"]),
        "--ls-new10-credential-handoff",
        str(p["ls10_handoff"]),
        "--ls-new10-safety-summary",
        str(p["ls10_safety"]),
        "--credential-env",
        str(p["credential_env"]),
        "--connect-timeout-seconds",
        "2",
        "--output-manifest",
        str(out["manifest"]),
        "--output-credential-summary",
        str(out["credential_summary"]),
        "--output-wp-connectivity-result",
        str(out["wp_result"]),
        "--output-no-write-safety-contract",
        str(out["safety_contract"]),
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
    required_flags = [
        "--allow-credential-env-existence-check",
        "--allow-credential-env-read",
        "--allow-wordpress-rest-index-get",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-wordpress-update",
        "--require-no-wordpress-delete",
        "--require-no-authenticated-wp-get",
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
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    cmd.extend(required_flags if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_build_success(tmp_path: Path) -> None:
    server, base_url = _start_http_server()
    try:
        p = _prepare(tmp_path, base_url=base_url)
        res = _run(tmp_path, p)
        assert res.returncode == 0
        out = _load(tmp_path / "out/result.json")
        assert out["status"] == "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_READY_NO_WRITE"
        assert out["wordpress_rest_index_get_succeeded"] is True
        assert out["wordpress_rest_index_status_class"] == "2xx"
        assert out["ready_for_ls_new_12"] is True
    finally:
        server.shutdown()


def test_network_error_fail(tmp_path: Path) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_FAILED_NO_WRITE"
    assert out["wordpress_rest_index_status_class"] == "NETWORK_ERROR"


@pytest.mark.parametrize("missing", ["ls10_validation", "ls10_result", "ls10_manifest", "ls10_input_map", "ls10_dry", "ls10_handoff", "ls10_safety"])
def test_missing_previous_inputs_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_FAILED_NO_WRITE"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls10_validation", "validation_status", "BAD", "ls-new10 validation status mismatch"),
        ("ls10_result", "status", "BAD", "ls-new10 run status mismatch"),
        ("ls10_result", "ready_for_ls_new_11", False, "ls-new10 ready_for_ls_new_11 mismatch"),
        ("ls10_result", "execution_allowed", True, "ls-new10 execution_allowed mismatch"),
        ("ls10_result", "runner_execution_allowed", True, "ls-new10 runner_execution_allowed mismatch"),
        ("ls10_result", "final_execution_command_created", True, "ls-new10 final_execution_command_created mismatch"),
        ("ls10_result", "wordpress_write_executed", True, "ls-new10 wordpress_write_executed mismatch"),
        ("ls10_result", "wordpress_draft_created", True, "ls-new10 wordpress_draft_created mismatch"),
        ("ls10_result", "wordpress_publish_executed", True, "ls-new10 wordpress_publish_executed mismatch"),
        ("ls10_result", "target_post_id", 1, "ls-new10 target_post_id must be null"),
        ("ls10_result", "target_post_id_allocated", True, "ls-new10 target_post_id_allocated mismatch"),
        ("ls10_result", "approval_label_consumed", True, "ls-new10 approval_label_consumed mismatch"),
        ("ls10_manifest", "phase", "BAD", "ls-new10 manifest phase mismatch"),
        ("ls10_input_map", "phase", "BAD", "ls-new10 input-map phase mismatch"),
        ("ls10_dry", "phase", "BAD", "ls-new10 dry-boundary phase mismatch"),
        ("ls10_handoff", "phase", "BAD", "ls-new10 credential-handoff phase mismatch"),
        ("ls10_safety", "phase", "BAD", "ls-new10 safety-summary phase mismatch"),
    ],
)
def test_previous_phase_gate_failures(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--allow-credential-env-existence-check",
        "--allow-credential-env-read",
        "--allow-wordpress-rest-index-get",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-wordpress-update",
        "--require-no-wordpress-delete",
        "--require-no-authenticated-wp-get",
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
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ],
)
def test_missing_flags_fail(tmp_path: Path, missing_flag: str) -> None:
    p = _prepare(tmp_path, base_url=_unused_base_url())
    all_flags = [
        "--allow-credential-env-existence-check",
        "--allow-credential-env-read",
        "--allow-wordpress-rest-index-get",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-wordpress-update",
        "--require-no-wordpress-delete",
        "--require-no-authenticated-wp-get",
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
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    flags = [f for f in all_flags if f != missing_flag]
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
    server, base_url = _start_http_server()
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
        assert out["required_url_key_present"] is True
        assert out["required_username_key_present"] is True
        assert out["required_app_password_key_present"] is True
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
        "wordpress_authenticated_get_executed",
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
        "credential_values_saved",
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ],
)
def test_result_forbidden_flags_false(tmp_path: Path, key: str) -> None:
    server, base_url = _start_http_server()
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
        ("manifest", "START_LS_NEW11_CREDENTIAL_PREFLIGHT_MANIFEST"),
        ("credential_summary", "START_LS_NEW11_CREDENTIAL_PRESENCE_SUMMARY"),
        ("wp_result", "START_LS_NEW11_WP_CONNECTIVITY_PREFLIGHT_RESULT"),
        ("safety_contract", "START_LS_NEW11_NO_WRITE_SAFETY_CONTRACT"),
        ("handoff", "START_LS_NEW11_NEXT_PHASE_HANDOFF"),
        ("result", "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_RESULT"),
        ("lock", "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_LOCK"),
    ],
)
def test_generated_document_types(tmp_path: Path, path_key: str, doc_type: str) -> None:
    server, base_url = _start_http_server()
    try:
        p = _prepare(tmp_path, base_url=base_url)
        _run(tmp_path, p)
        obj = _load(tmp_path / f"out/{path_key}.json")
        assert obj["document_type"] == doc_type
    finally:
        server.shutdown()


def test_no_credential_values_in_outputs(tmp_path: Path) -> None:
    server, base_url = _start_http_server()
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
                (tmp_path / "out/credential_summary.json").read_text(encoding="utf-8"),
                (tmp_path / "out/result.json").read_text(encoding="utf-8"),
                (tmp_path / "out/summary.md").read_text(encoding="utf-8"),
                (tmp_path / "out/report.md").read_text(encoding="utf-8"),
            ]
        )
        assert secret_user not in blob
        assert secret_pass not in blob
        assert "Authorization:" not in blob
        assert "Basic " not in blob
    finally:
        server.shutdown()


def test_source_code_no_forbidden_output_patterns() -> None:
    src = Path("scripts/build_start_ls_new11_credential_wp_connectivity_preflight.py").read_text(encoding="utf-8")
    forbidden = [
        "print(credential",
        "print(password",
        "print(secret",
        "print(Authorization",
        "print(Basic",
        "logger.credential",
        "logger.password",
        "logger.secret",
        "logger.Authorization",
        "logger.Basic",
    ]
    assert all(x not in src for x in forbidden)