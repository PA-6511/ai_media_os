from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from urllib.parse import urlencode

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import EbookItem, WorkflowApprovalRequest
from app.services.workflow_action_service import (
    get_workflow_action_token,
)


def load_app_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts/new_release_multistore_app.py"
    name = "review_ready_test_app"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load GUI module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


app = load_app_module()


class DirectHandler(app.MultiStoreAppHandler):
    def __init__(
        self,
        *,
        path: str,
        values: dict[str, str],
        store,
        cookie: str,
    ) -> None:
        body = urlencode(values).encode("utf-8")
        self.path = path
        self.server = SimpleNamespace(session_store=store)
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(body)),
            "Cookie": cookie,
        }
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.response_status: int | None = None
        self.response_headers: list[tuple[str, str]] = []

    def send_response(self, code, message=None) -> None:
        self.response_status = int(code)

    def send_header(self, keyword, value) -> None:
        self.response_headers.append((str(keyword), str(value)))

    def end_headers(self) -> None:
        return None

    def header(self, name: str) -> str:
        for key, value in self.response_headers:
            if key.lower() == name.lower():
                return value
        return ""


def create_database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'review_ready_routes.db'}"
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    return engine, factory


def create_item(
    factory,
    source_item_id: str,
    *,
    is_excluded: bool = False,
) -> str:
    with factory() as session:
        item = EbookItem(
            source_name="pytest",
            source_item_id=source_item_id,
            title=source_item_id,
            item_type="tankobon",
            workflow_status="REVIEW",
            review_status="NOT_REVIEWED",
            is_excluded=is_excluded,
        )
        session.add(item)
        session.commit()
        return item.id


def browser_session():
    store = app.SessionStore()
    session = store.create()
    cookie = f"{app.SESSION_COOKIE_NAME}={session.session_id}"
    return store, session, cookie


def invoke_route(
    path: str,
    values: dict[str, str],
    *,
    store,
    cookie: str,
) -> DirectHandler:
    handler = DirectHandler(
        path=path,
        values=values,
        store=store,
        cookie=cookie,
    )
    handler.do_POST()
    return handler


def request_values(item_id: str, **overrides) -> dict[str, str]:
    values = {
        "csrf_token": get_workflow_action_token(),
        "ebook_item_id": item_id,
        "return_to": "/database-search?keyword=test",
    }
    values.update(overrides)
    return values


def decision_values(
    item_id: str,
    request_id: str,
    **overrides,
) -> dict[str, str]:
    values = {
        "csrf_token": get_workflow_action_token(),
        "ebook_item_id": item_id,
        "approval_request_id": request_id,
        "decision": "APPROVE",
        "note": "human checked",
        "return_to": "/database-search?keyword=test",
    }
    values.update(overrides)
    return values


def test_generic_workflow_post_rejects_review_to_ready(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-GENERIC-GUARD")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, _, cookie = browser_session()
    handler = invoke_route(
        "/database-workflow",
        {
            "csrf_token": get_workflow_action_token(),
            "item_id": item_id,
            "new_status": "READY",
            "return_to": "/database-search",
        },
        store=store,
        cookie=cookie,
    )

    assert handler.response_status == 303
    assert (
        "workflow_update=REVIEW_READY_REQUIRES_APPROVAL"
        in handler.header("Location")
    )
    with factory() as session:
        item = session.get(EbookItem, item_id)
        requests = session.scalars(
            select(WorkflowApprovalRequest)
        ).all()
    assert item is not None
    assert item.workflow_status == "REVIEW"
    assert item.review_status == "NOT_REVIEWED"
    assert requests == []


def test_request_route_creates_pending_and_keeps_token_in_session(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-001")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, session_data, cookie = browser_session()
    handler = invoke_route(
        "/database-review-ready-request",
        request_values(item_id),
        store=store,
        cookie=cookie,
    )

    assert handler.response_status == 303
    location = handler.header("Location")
    assert location.startswith("/database-search?keyword=test&")
    assert "review_ready_result=request_created" in location
    assert "token" not in location.lower()

    with factory() as session:
        item = session.get(EbookItem, item_id)
        requests = session.scalars(
            select(WorkflowApprovalRequest)
        ).all()

    assert item is not None
    assert item.workflow_status == "REVIEW"
    assert item.review_status == "IN_REVIEW"
    assert len(requests) == 1
    assert requests[0].status == "PENDING"
    assert requests[0].approval_type == "REVIEW_READY"
    raw_token = session_data.review_ready_tokens[requests[0].id]
    assert raw_token
    assert requests[0].request_nonce_hash != raw_token


def test_request_route_rejects_invalid_csrf_and_approval_type(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-002")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, _, cookie = browser_session()

    invalid_csrf = invoke_route(
        "/database-review-ready-request",
        request_values(item_id, csrf_token="invalid"),
        store=store,
        cookie=cookie,
    )
    assert invalid_csrf.response_status == 303
    assert (
        "review_ready_result=invalid_token"
        in invalid_csrf.header("Location")
    )

    invalid_type = invoke_route(
        "/database-review-ready-request",
        request_values(item_id, approval_type="PUBLISH_SCHEDULE"),
        store=store,
        cookie=cookie,
    )
    assert invalid_type.response_status == 303
    assert (
        "review_ready_result=invalid_approval_type"
        in invalid_type.header("Location")
    )

    with factory() as session:
        assert session.scalars(
            select(WorkflowApprovalRequest)
        ).all() == []


def test_request_route_blocks_excluded_and_open_redirect(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(
        factory,
        "ROUTE-003",
        is_excluded=True,
    )
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, _, cookie = browser_session()
    handler = invoke_route(
        "/database-review-ready-request",
        request_values(
            item_id,
            return_to="https://evil.example/steal",
        ),
        store=store,
        cookie=cookie,
    )

    assert handler.response_status == 303
    location = handler.header("Location")
    assert location.startswith("/database-search?")
    assert "evil.example" not in location
    assert "review_ready_result=excluded_item" in location


def test_decision_route_approves_and_consumes_session_token(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-004")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, session_data, cookie = browser_session()
    invoke_route(
        "/database-review-ready-request",
        request_values(item_id),
        store=store,
        cookie=cookie,
    )

    with factory() as session:
        request = session.scalar(select(WorkflowApprovalRequest))
        assert request is not None
        request_id = request.id

    approved = invoke_route(
        "/database-review-ready-decision",
        decision_values(item_id, request_id),
        store=store,
        cookie=cookie,
    )

    assert approved.response_status == 303
    assert (
        "review_ready_result=approved"
        in approved.header("Location")
    )
    assert "token" not in approved.header("Location").lower()

    with factory() as session:
        item = session.get(EbookItem, item_id)
        request = session.get(
            WorkflowApprovalRequest,
            request_id,
        )

    assert item is not None
    assert item.workflow_status == "READY"
    assert item.review_status == "APPROVED"
    assert request is not None
    assert request.status == "APPROVED"
    assert request.decided_at is not None
    assert request_id not in session_data.review_ready_tokens

    duplicate = invoke_route(
        "/database-review-ready-decision",
        decision_values(item_id, request_id),
        store=store,
        cookie=cookie,
    )
    assert duplicate.response_status == 303
    assert (
        "review_ready_result=approval_token_unavailable"
        in duplicate.header("Location")
    )


def test_decision_route_rejects_invalid_csrf_and_item_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-005-A")
    other_id = create_item(factory, "ROUTE-005-B")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, _, cookie = browser_session()
    invoke_route(
        "/database-review-ready-request",
        request_values(item_id),
        store=store,
        cookie=cookie,
    )
    with factory() as session:
        request = session.scalar(select(WorkflowApprovalRequest))
        assert request is not None
        request_id = request.id

    invalid_csrf = invoke_route(
        "/database-review-ready-decision",
        decision_values(
            item_id,
            request_id,
            csrf_token="invalid",
        ),
        store=store,
        cookie=cookie,
    )
    assert invalid_csrf.response_status == 303
    assert (
        "review_ready_result=invalid_token"
        in invalid_csrf.header("Location")
    )

    mismatch = invoke_route(
        "/database-review-ready-decision",
        decision_values(other_id, request_id),
        store=store,
        cookie=cookie,
    )
    assert mismatch.response_status == 303
    assert (
        "review_ready_result=request_item_mismatch"
        in mismatch.header("Location")
    )

    with factory() as session:
        request = session.get(WorkflowApprovalRequest, request_id)
        item = session.get(EbookItem, item_id)
    assert request is not None
    assert request.status == "PENDING"
    assert item is not None
    assert item.workflow_status == "REVIEW"


def test_decision_route_rejects_expired_request(
    tmp_path,
    monkeypatch,
) -> None:
    _, factory = create_database(tmp_path)
    item_id = create_item(factory, "ROUTE-006")
    import app.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    store, _, cookie = browser_session()
    invoke_route(
        "/database-review-ready-request",
        request_values(item_id),
        store=store,
        cookie=cookie,
    )
    with factory() as session:
        request = session.scalar(select(WorkflowApprovalRequest))
        assert request is not None
        request_id = request.id
        now = datetime.now(timezone.utc)
        request.requested_at = now - timedelta(minutes=2)
        request.expires_at = now - timedelta(minutes=1)
        session.commit()

    expired = invoke_route(
        "/database-review-ready-decision",
        decision_values(item_id, request_id),
        store=store,
        cookie=cookie,
    )

    assert expired.response_status == 303
    assert (
        "review_ready_result=expired"
        in expired.header("Location")
    )
    with factory() as session:
        request = session.get(WorkflowApprovalRequest, request_id)
    assert request is not None
    assert request.status == "EXPIRED"
