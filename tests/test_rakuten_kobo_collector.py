from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import stat
import sys
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.integrations import rakuten_kobo_api_client as api
from app.integrations.rakuten_kobo_live_configuration import (
    build_live_request_configuration,
)
from app.services import rakuten_kobo_collector as collector_module
from app.services.rakuten_kobo_collector import (
    RakutenKoboCollector,
    RakutenKoboCollectorError,
    inspect_response_bytes,
    save_raw_response_bytes,
)
from scripts import collect_rakuten_kobo_response as cli


NOW = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)


def response_bytes(items: list[dict] | None = None) -> bytes:
    value = {
        "count": 1,
        "Items": items
        if items is not None
        else [
            {
                "Item": {
                    "title": "検証作品",
                    "author": "著者",
                    "publisherName": "出版社",
                    "isbn": "9781234567897",
                    "itemNumber": "2000012345678",
                    "salesDate": "2026-08-01",
                    "itemPrice": 700,
                    "itemUrl": "https://books.rakuten.co.jp/rk/fixture/",
                }
            }
        ],
    }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


class FakeTransport:
    def __init__(self, response: api.TransportResponse | None = None) -> None:
        self.response = response or api.TransportResponse(
            200,
            {"Content-Type": "application/json; charset=utf-8"},
            response_bytes(),
        )
        self.calls: list[dict[str, object]] = []

    def get(self, **kwargs) -> api.TransportResponse:
        self.calls.append(kwargs)
        return self.response


def live_config() -> api.RakutenKoboRequestConfiguration:
    return api.RakutenKoboRequestConfiguration(
        endpoint_url="https://api.example.invalid/path?opaque=secret",
        headers={"X-Opaque-Authentication": "secret-value"},
    )


def make_collector(tmp_path: Path, **overrides) -> RakutenKoboCollector:
    values = {
        "repository_root": tmp_path,
        "output_directory": tmp_path / "exchange/raw/rakuten_kobo",
        "evidence_directory": tmp_path / "exchange/logs/rakuten_kobo_collection",
        "now": lambda: NOW,
    }
    values.update(overrides)
    return RakutenKoboCollector(**values)


def live_args() -> list[str]:
    return [
        "--execute-fetch",
        "--confirm-get-only",
        "--output-directory",
        "exchange/raw/rakuten_kobo",
        "--title",
        "検証作品",
    ]


@pytest.mark.parametrize(
    "arguments,expected_status",
    [
        ([], "DRY_RUN"),
        (["--confirm-get-only"], "DRY_RUN"),
        (["--execute-fetch"], "BLOCKED_CONFIRM_GET_ONLY_REQUIRED"),
        (
            ["--execute-fetch", "--confirm-get-only"],
            "BLOCKED_OUTPUT_DIRECTORY_CONFIRMATION_REQUIRED",
        ),
    ],
)
def test_cli_gates_never_call_http(
    tmp_path: Path, arguments: list[str], expected_status: str
) -> None:
    transport = FakeTransport()
    result = cli.execute_cli(
        arguments,
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=lambda **_kwargs: live_config(),
    )
    assert result["status"] == expected_status
    assert result["external_get_attempted"] is False
    assert transport.calls == []
    assert not (tmp_path / "exchange").exists()


def test_live_configuration_absence_is_not_configured_before_http(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()
    result = cli.execute_cli(
        live_args(),
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=lambda **_kwargs: None,
    )
    assert result["status"] == "NOT_CONFIGURED"
    assert result["external_get_attempted"] is False
    assert transport.calls == []


def test_live_selector_is_required_before_configuration_or_http(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()

    def forbidden_loader(**_kwargs):
        pytest.fail("configuration must not load without a search selector")

    result = cli.execute_cli(
        [
            "--execute-fetch",
            "--confirm-get-only",
            "--output-directory",
            "exchange/raw/rakuten_kobo",
        ],
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=forbidden_loader,
    )
    assert result["status"] == "BLOCKED_SEARCH_SELECTOR_REQUIRED"
    assert result["external_get_attempted"] is False
    assert result["raw_response_saved"] is False
    assert transport.calls == []


def test_official_configuration_fake_get_uses_secret_header_only(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()
    access_key = "collector-secret-access-key"
    application_id = "collector-application-id"
    affiliate_id = "collector-affiliate-id"
    observed_selectors: list[tuple[str | None, str | None]] = []

    def loader(*, title=None, item_number=None):
        observed_selectors.append((title, item_number))
        return build_live_request_configuration(
            application_id=application_id,
            access_key=access_key,
            affiliate_id=affiliate_id,
            title=title,
            item_number=item_number,
        )

    result = cli.execute_cli(
        live_args() + ["--item-number", "4321000000028"],
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=loader,
    )

    assert result["status"] == "PASS"
    assert observed_selectors == [("検証作品", "4321000000028")]
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["headers"]["accessKey"] == access_key
    assert access_key not in call["url"]
    assert "formatVersion=1" in call["url"]
    assert "title=%E6%A4%9C%E8%A8%BC%E4%BD%9C%E5%93%81" in call["url"]
    assert "itemNumber=4321000000028" in call["url"]
    evidence_text = Path(str(result["evidence_path"])).read_text(
        encoding="utf-8"
    )
    for forbidden in (access_key, application_id, affiliate_id, "?", "accessKey"):
        assert forbidden not in evidence_text


def test_request_configuration_rejects_non_https() -> None:
    with pytest.raises(api.RakutenKoboApiError) as exc:
        api.RakutenKoboRequestConfiguration(endpoint_url="http://example.invalid/api")
    assert exc.value.code == "HTTPS_REQUIRED"


def test_api_client_uses_only_get_with_timeout_and_hides_secrets() -> None:
    transport = FakeTransport()
    client = api.RakutenKoboApiClient(transport, timeout_seconds=7.5)
    configuration = live_config()
    result = client.fetch(configuration)
    assert result.endpoint_host == "api.example.invalid"
    assert len(transport.calls) == 1
    assert transport.calls[0]["timeout_seconds"] == 7.5
    assert "secret-value" not in repr(configuration)
    assert "opaque=secret" not in repr(configuration)
    assert not hasattr(transport, "post")
    assert not hasattr(client, "post")


def test_requests_transport_disables_redirects_and_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        status_code = 200
        headers = {"Content-Type": "application/json", "Content-Length": "2"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_content(self, *, chunk_size: int):
            assert chunk_size == 64 * 1024
            yield b"{}"

    class Session:
        def get(self, _url, **kwargs):
            calls.append(kwargs)
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(api.requests, "Session", Session)
    result = api.RequestsGetTransport().get(
        url="https://example.invalid/api",
        headers={},
        timeout_seconds=3,
        maximum_bytes=10,
    )
    assert result.body == b"{}"
    assert calls == [
        {
            "headers": {},
            "timeout": 3,
            "allow_redirects": False,
            "stream": True,
        }
    ]


def test_transport_exception_traceback_suppresses_request_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_id = "traceback-application-id-must-not-leak"
    access_key = "traceback-access-key-must-not-leak"
    configuration = build_live_request_configuration(
        application_id=application_id,
        access_key=access_key,
        title="検証作品",
    )

    class Session:
        def get(self, url, **kwargs):
            raise api.requests.ConnectionError(
                f"unsafe transport detail: {url} {kwargs['headers']['accessKey']}"
            )

        def close(self):
            pass

    monkeypatch.setattr(api.requests, "Session", Session)
    client = api.RakutenKoboApiClient(api.RequestsGetTransport())

    with pytest.raises(api.RakutenKoboApiError) as caught:
        client.fetch(configuration)

    rendered = "".join(
        traceback.format_exception(
            type(caught.value), caught.value, caught.value.__traceback__
        )
    )
    assert caught.value.failure_details is not None
    assert caught.value.failure_details.failure_category == "CONNECTION_FAILURE"
    assert application_id not in rendered
    assert access_key not in rendered
    assert configuration.endpoint_url not in rendered


@pytest.mark.parametrize(
    "response,expected_code",
    [
        (api.TransportResponse(302, {"Content-Type": "application/json"}, b"{}"), "REDIRECT_REFUSED"),
        (api.TransportResponse(500, {"Content-Type": "application/json"}, b"{}"), "HTTP_STATUS_ERROR"),
        (api.TransportResponse(200, {"Content-Type": "text/html"}, b"{}"), "JSON_CONTENT_TYPE_REQUIRED"),
        (api.TransportResponse(200, {"Content-Type": "application/json"}, b"12345"), "RESPONSE_SIZE_LIMIT_EXCEEDED"),
    ],
)
def test_api_response_safety_limits(
    response: api.TransportResponse, expected_code: str
) -> None:
    client = api.RakutenKoboApiClient(
        FakeTransport(response), maximum_response_bytes=4
    )
    with pytest.raises(api.RakutenKoboApiError) as exc:
        client.fetch(live_config())
    assert exc.value.code == expected_code
    assert "secret" not in exc.value.safe_summary
    assert "https://" not in exc.value.safe_summary


def test_http_403_fake_response_exposes_only_allowlisted_diagnostics() -> None:
    application_id = "real-application-id-must-not-leak"
    access_key = "real-access-key-must-not-leak"
    body = json.dumps(
        {
            "error": "ACCESS_DENIED",
            "error_description": (
                f"application {application_id} with key {access_key} is forbidden"
            ),
        }
    ).encode()
    configuration = build_live_request_configuration(
        application_id=application_id,
        access_key=access_key,
        title="検証作品",
    )
    client = api.RakutenKoboApiClient(
        FakeTransport(
            api.TransportResponse(
                403,
                {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Length": str(len(body)),
                    "Set-Cookie": "must-not-be-recorded",
                },
                body,
            )
        )
    )

    with pytest.raises(api.RakutenKoboApiError) as caught:
        client.fetch(configuration)

    error = caught.value
    details = error.failure_details
    assert error.code == "HTTP_STATUS_ERROR"
    assert error.safe_summary == "HTTP_STATUS_ERROR;status=403"
    assert details is not None
    assert details.response_status == 403
    assert details.response_content_type == "application/json"
    assert details.response_content_length_present is True
    assert details.response_content_length == len(body)
    assert details.provider_error_code == "ACCESS_DENIED"
    assert details.provider_error_message == (
        "application [REDACTED] with key [REDACTED] is forbidden"
    )
    assert details.failure_category == "HTTP_403"
    assert details.retryable is False
    assert details.request_host == "openapi.rakuten.co.jp"
    assert details.request_path == "/services/api/Kobo/EbookSearch/20170426"
    assert details.request_query_key_names == (
        "applicationId",
        "format",
        "formatVersion",
        "language",
        "hits",
        "page",
        "elements",
        "title",
    )
    assert details.request_header_names == (
        "Accept",
        "Accept-Encoding",
        "accessKey",
        "User-Agent",
    )
    assert details.response_body_sha256 == hashlib.sha256(body).hexdigest()
    assert details.response_body_byte_count == len(body)
    rendered = repr(error) + repr(details) + error.safe_summary
    assert application_id not in rendered
    assert access_key not in rendered
    assert "Set-Cookie" not in rendered
    assert "must-not-be-recorded" not in rendered
    assert configuration.endpoint_url not in rendered


def test_items_item_structure_is_converter_ready() -> None:
    result = inspect_response_bytes(response_bytes())
    assert result.converter_ready is True
    assert result.item_count == 1
    assert result.error_summary is None


@pytest.mark.parametrize(
    "value,expected",
    [
        ({}, "ITEMS_LIST_REQUIRED"),
        ({"Items": [{}]}, "ITEM_OBJECT_REQUIRED:index=0"),
        ({"Items": ["bad"]}, "ITEM_WRAPPER_OBJECT_REQUIRED:index=0"),
        ([], "ROOT_OBJECT_REQUIRED"),
    ],
)
def test_invalid_response_structure(value: object, expected: str) -> None:
    raw = json.dumps(value).encode()
    result = inspect_response_bytes(raw)
    assert result.converter_ready is False
    assert result.error_summary == expected


def test_item_count_depth_and_size_limits() -> None:
    too_many = response_bytes([{"Item": {}} for _ in range(3)])
    assert inspect_response_bytes(too_many, maximum_items=2).error_summary == "ITEM_COUNT_LIMIT_EXCEEDED"
    nested: object = "leaf"
    for _ in range(10):
        nested = {"nested": nested}
    deep = json.dumps({"Items": [{"Item": {"value": nested}}]}).encode()
    assert inspect_response_bytes(deep, maximum_depth=6).error_summary == "JSON_DEPTH_LIMIT_EXCEEDED"
    assert inspect_response_bytes(b"12345", maximum_bytes=4).error_summary == "RESPONSE_SIZE_LIMIT_EXCEEDED"


def test_raw_bytes_are_unchanged_sha_verified_and_mode_600(tmp_path: Path) -> None:
    raw = b'{ "Items" : [ { "Item" : {} } ] }\n'
    saved = save_raw_response_bytes(
        raw,
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW,
    )
    assert saved.path.read_bytes() == raw
    assert saved.sha256 == hashlib.sha256(raw).hexdigest()
    assert stat.S_IMODE(os.lstat(saved.path).st_mode) == 0o600
    assert saved.duplicate_detected is False


def test_atomic_publication_observes_temp_then_noreplace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[tuple[bool, bool]] = []
    real = collector_module._atomic_rename_noreplace

    def inspect_then_rename(*, directory_fd: int, source_name: str, destination_name: str):
        names = set(os.listdir(directory_fd))
        observed.append((source_name in names, destination_name in names))
        return real(
            directory_fd=directory_fd,
            source_name=source_name,
            destination_name=destination_name,
        )

    monkeypatch.setattr(collector_module, "_atomic_rename_noreplace", inspect_then_rename)
    save_raw_response_bytes(
        response_bytes(),
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW,
    )
    assert observed == [(True, False)]


def test_duplicate_sha_reuses_existing_file_without_overwrite(tmp_path: Path) -> None:
    raw = response_bytes()
    first = save_raw_response_bytes(
        raw,
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW,
    )
    second = save_raw_response_bytes(
        raw,
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW.replace(hour=13),
    )
    assert second.duplicate_detected is True
    assert second.path == first.path
    assert list(first.path.parent.glob("*.json")) == [first.path]


def test_existing_target_is_never_overwritten(tmp_path: Path) -> None:
    raw = response_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    directory = tmp_path / "exchange/raw/rakuten_kobo"
    directory.mkdir(parents=True)
    target = directory / f"20260801T120000Z-rakuten-kobo-{digest[:16]}.json"
    target.write_bytes(b"different")
    target.chmod(0o600)
    with pytest.raises(RakutenKoboCollectorError) as exc:
        save_raw_response_bytes(
            raw,
            repository_root=tmp_path,
            output_directory=directory,
            fetched_at=NOW,
        )
    assert exc.value.code == "OUTPUT_ALREADY_EXISTS"
    assert target.read_bytes() == b"different"


def test_symlink_output_and_raw_targets_are_rejected(tmp_path: Path) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    linked_directory = tmp_path / "exchange/raw/rakuten_kobo"
    linked_directory.parent.mkdir(parents=True)
    linked_directory.symlink_to(real_directory, target_is_directory=True)
    with pytest.raises(RakutenKoboCollectorError) as directory_exc:
        save_raw_response_bytes(
            response_bytes(),
            repository_root=tmp_path,
            output_directory=linked_directory,
            fetched_at=NOW,
        )
    assert directory_exc.value.code == "SYMLINK_PATH_REJECTED"

    linked_directory.unlink()
    linked_directory.mkdir()
    raw = response_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    target = linked_directory / f"20260801T120000Z-rakuten-kobo-{digest[:16]}.json"
    target.symlink_to(tmp_path / "outside.json")
    with pytest.raises(RakutenKoboCollectorError):
        save_raw_response_bytes(
            raw,
            repository_root=tmp_path,
            output_directory=linked_directory,
            fetched_at=NOW,
        )


def test_invalid_structure_is_saved_but_not_converter_ready(tmp_path: Path) -> None:
    service = make_collector(tmp_path)
    raw = b'{"message":"not a converter payload","application_id":"raw-only"}'
    outcome = service.collect_fetched_response(
        api.FetchedRakutenKoboResponse(
            endpoint_host="api.example.invalid",
            status_code=200,
            content_type="application/json",
            body=raw,
        )
    )
    assert outcome.status == "SAVED_NOT_CONVERTER_READY"
    assert outcome.raw_response_path is not None
    assert outcome.raw_response_path.read_bytes() == raw
    assert outcome.converter_ready is False
    assert outcome.evidence["error_summary"] == "ITEMS_LIST_REQUIRED"
    evidence_text = outcome.evidence_path.read_text(encoding="utf-8")
    assert set(json.loads(evidence_text)) == {
        "operation",
        "collection_id",
        "fetched_at",
        "http_method",
        "endpoint_host",
        "response_status",
        "content_type",
        "response_size_bytes",
        "raw_response_sha256",
        "raw_response_path",
        "response_content_length_present",
        "response_content_length",
        "provider_error_code",
        "provider_error_message",
        "failure_category",
        "retryable",
        "request_path",
        "request_query_key_names",
        "request_header_names",
        "search_selector_type",
        "search_result_count",
        "duplicate_detected",
        "external_get_attempted",
        "external_get_succeeded",
        "raw_save_attempted",
        "raw_save_succeeded",
        "converter_ready",
        "database_write_performed",
        "wordpress_write_performed",
        "error_summary",
    }
    assert "raw-only" not in evidence_text
    assert "application_id" not in evidence_text
    assert "response_body" not in evidence_text
    assert stat.S_IMODE(os.lstat(outcome.evidence_path).st_mode) == 0o600


def test_http_403_fake_get_records_safe_failure_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_id = "evidence-application-id-must-not-leak"
    access_key = "evidence-access-key-must-not-leak"
    affiliate_id = "evidence-affiliate-id-must-not-leak"
    title = "evidence-title-query-value-must-not-leak"
    body = json.dumps(
        {
            "errors": [
                {
                    "code": "FORBIDDEN",
                    "message": f"credential {access_key} is not permitted",
                }
            ]
        }
    ).encode()
    transport = FakeTransport(
        api.TransportResponse(
            403,
            {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(body)),
                "Set-Cookie": "private-cookie",
            },
            body,
        )
    )
    monkeypatch.setattr(sqlite3, "connect", lambda *_a, **_k: pytest.fail("SQLite opened"))
    monkeypatch.setattr(socket, "create_connection", lambda *_a, **_k: pytest.fail("socket opened"))
    monkeypatch.setattr(cli, "write_response_csv", lambda *_a, **_k: pytest.fail("CSV generated"))

    def loader(*, title=None, item_number=None):
        return build_live_request_configuration(
            application_id=application_id,
            access_key=access_key,
            affiliate_id=affiliate_id,
            title=title,
            item_number=item_number,
        )

    result = cli.execute_cli(
        [
            "--execute-fetch",
            "--confirm-get-only",
            "--output-directory",
            "exchange/raw/rakuten_kobo",
            "--title",
            title,
        ],
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=loader,
    )

    assert result["status"] == "FETCH_FAILED"
    assert len(transport.calls) == 1
    assert result["raw_response_saved"] is False
    assert result["csv_created"] is False
    assert result["database_write_performed"] is False
    assert result["wordpress_write_performed"] is False
    evidence_path = Path(str(result["evidence_path"]))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["response_status"] == 403
    assert evidence["content_type"] == "application/json"
    assert evidence["response_content_length_present"] is True
    assert evidence["response_content_length"] == len(body)
    assert evidence["provider_error_code"] == "FORBIDDEN"
    assert evidence["provider_error_message"] == (
        "credential [REDACTED] is not permitted"
    )
    assert evidence["failure_category"] == "HTTP_403"
    assert evidence["retryable"] is False
    assert evidence["endpoint_host"] == "openapi.rakuten.co.jp"
    assert evidence["request_path"] == "/services/api/Kobo/EbookSearch/20170426"
    assert evidence["request_query_key_names"] == [
        "applicationId",
        "format",
        "formatVersion",
        "language",
        "hits",
        "page",
        "elements",
        "affiliateId",
        "title",
    ]
    assert evidence["request_header_names"] == [
        "Accept",
        "Accept-Encoding",
        "accessKey",
        "User-Agent",
    ]
    assert evidence["raw_response_sha256"] == hashlib.sha256(body).hexdigest()
    assert evidence["response_size_bytes"] == len(body)
    serialized = json.dumps(evidence, ensure_ascii=False)
    configuration_url = transport.calls[0]["url"]
    assert isinstance(configuration_url, str)
    for forbidden in (
        application_id,
        access_key,
        affiliate_id,
        title,
        "private-cookie",
        "Set-Cookie",
        configuration_url,
    ):
        assert forbidden not in serialized
    assert "response_body" not in serialized
    assert not (tmp_path / "exchange/raw/rakuten_kobo").exists()


def test_live_fake_get_collects_without_database_wordpress_or_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(sqlite3, "connect", lambda *_a, **_k: pytest.fail("SQLite opened"))
    monkeypatch.setattr(socket, "create_connection", lambda *_a, **_k: pytest.fail("socket opened"))
    monkeypatch.setattr(cli, "write_response_csv", lambda *_a, **_k: pytest.fail("CSV generated"))
    wordpress_sentinel = types.ModuleType("app.integrations.wordpress_rest_client")
    wordpress_sentinel.WordPressRestClient = lambda *_a, **_k: pytest.fail(
        "WordPress client generated"
    )
    monkeypatch.setitem(
        sys.modules,
        "app.integrations.wordpress_rest_client",
        wordpress_sentinel,
    )
    result = cli.execute_cli(
        live_args(),
        repository_root=tmp_path,
        transport=transport,
        live_configuration_loader=lambda **_kwargs: live_config(),
    )
    assert result["status"] == "PASS"
    assert result["external_get_attempted"] is True
    assert result["external_get_succeeded"] is True
    assert result["csv_created"] is False
    assert result["database_write_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert len(transport.calls) == 1
    evidence_path = Path(str(result["evidence_path"]))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["raw_response_sha256"] == hashlib.sha256(response_bytes()).hexdigest()
    assert evidence["search_selector_type"] == "title"
    assert evidence["search_result_count"] == 1
    assert evidence["database_write_performed"] is False
    assert evidence["wordpress_write_performed"] is False
    serialized = json.dumps(evidence, ensure_ascii=False)
    assert "opaque=secret" not in serialized
    assert "secret-value" not in serialized
    assert "api.example.invalid/path" not in serialized


def test_saved_collector_json_can_use_existing_converter(tmp_path: Path) -> None:
    saved = save_raw_response_bytes(
        response_bytes(),
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW,
    )
    output_csv = tmp_path / "exchange/converted/kobo.csv"
    result = cli.execute_cli(
        [
            "--input-json",
            str(saved.path),
            "--output-directory",
            "exchange/raw/rakuten_kobo",
            "--convert-csv",
            str(output_csv),
            "--batch-id",
            "RK-COLLECTOR-TEST",
            "--verified-at",
            "2026-08-01T12:00:00Z",
        ],
        repository_root=tmp_path,
    )
    assert result["status"] == "CSV_CREATED"
    assert output_csv.is_file()
    assert "rakuten_kobo_url" in output_csv.read_text(encoding="utf-8-sig")
    with pytest.raises(FileExistsError):
        cli.execute_cli(
            [
                "--input-json",
                str(saved.path),
                "--convert-csv",
                str(output_csv),
                "--batch-id",
                "RK-COLLECTOR-TEST",
                "--verified-at",
                "2026-08-01T12:00:00Z",
            ],
            repository_root=tmp_path,
        )


def test_tampered_saved_raw_is_rejected_before_converter(tmp_path: Path) -> None:
    saved = save_raw_response_bytes(
        response_bytes(),
        repository_root=tmp_path,
        output_directory=tmp_path / "exchange/raw/rakuten_kobo",
        fetched_at=NOW,
    )
    saved.path.write_bytes(response_bytes([]))
    result = cli.execute_cli(
        ["--input-json", str(saved.path)],
        repository_root=tmp_path,
    )
    assert result["status"] == "VALIDATION_FAILED"
    assert result["error_summary"] == "RAW_FILENAME_SHA256_MISMATCH"


def test_default_cli_never_generates_csv_or_imports_wordpress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "write_response_csv", lambda *_a, **_k: pytest.fail("converter called"))
    result = cli.execute_cli([], repository_root=tmp_path, transport=FakeTransport())
    assert result["status"] == "DRY_RUN"
    assert result["csv_created"] is False
    assert result["database_write_performed"] is False
    assert result["wordpress_write_performed"] is False


def test_client_source_contains_no_non_get_request_path() -> None:
    source = Path(api.__file__).read_text(encoding="utf-8")
    for forbidden in (".post(", ".put(", ".patch(", ".delete("):
        assert forbidden not in source.lower()
    assert ".get(" in source.lower()
