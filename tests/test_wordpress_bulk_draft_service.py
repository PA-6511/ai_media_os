from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.wordpress_bulk_draft_service import (
    BulkDraftItemResult,
    BulkDraftRequest,
    BulkDraftState,
    BulkWordPressDraftError,
    BulkWordPressDraftService,
)


NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)


def test_empty_selection_is_rejected() -> None:
    with pytest.raises(BulkWordPressDraftError) as error:
        BulkWordPressDraftService([])

    assert error.value.code == "BULK_DRAFT_EMPTY"


def test_more_than_five_items_is_rejected() -> None:
    with pytest.raises(BulkWordPressDraftError) as error:
        BulkWordPressDraftService(
            [f"ebook-{index}" for index in range(6)]
        )

    assert error.value.code == "BULK_DRAFT_LIMIT_EXCEEDED"


def test_selected_item_order_is_preserved() -> None:
    selected_item_ids = ["ebook-3", "ebook-1", "ebook-2"]
    service = BulkWordPressDraftService(selected_item_ids)
    request = service.create_request(now=NOW)

    assert service.selected_item_ids == tuple(selected_item_ids)
    assert request.selected_item_ids == tuple(selected_item_ids)


def test_initial_state_is_prepared() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    request = service.create_request(now=NOW)

    assert service.state is BulkDraftState.PREPARED
    assert request.used is False


def test_expired_request_is_rejected() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    request = service.create_request(now=NOW)

    assert service.is_request_expired(
        request,
        now=NOW + timedelta(minutes=15),
    )
    with pytest.raises(BulkWordPressDraftError) as error:
        service.confirm_request(
            request,
            now=NOW + timedelta(minutes=15),
        )

    assert error.value.code == "BULK_DRAFT_TOKEN_EXPIRED"
    assert request.used is False


def test_used_request_cannot_be_confirmed_again() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    request = service.create_request(now=NOW)

    service.confirm_request(request, now=NOW)

    assert request.used is True
    assert service.state is BulkDraftState.CONFIRMED
    with pytest.raises(BulkWordPressDraftError) as error:
        service.confirm_request(request, now=NOW)

    assert error.value.code == "BULK_DRAFT_TOKEN_REUSED"


def test_prepare_request_sets_request_contract() -> None:
    service = BulkWordPressDraftService(["ebook-2", "ebook-1"])

    request = service.prepare_request(now=NOW)

    assert request.request_id
    assert request.selected_item_ids == ("ebook-2", "ebook-1")
    assert request.created_at == NOW
    assert request.expires_at == NOW + timedelta(minutes=15)
    assert request.state is BulkDraftState.PREPARED
    assert request.used is False


def test_confirm_request_updates_request_and_service_state() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    request = service.prepare_request(now=NOW)

    result = service.confirm_request(request, now=NOW)

    assert result is request
    assert request.state is BulkDraftState.CONFIRMED
    assert request.used is True
    assert service.state is BulkDraftState.CONFIRMED


def test_unissued_request_is_rejected() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    service.prepare_request(now=NOW)
    unissued_request = BulkDraftRequest(
        request_id="unissued-request",
        selected_item_ids=("ebook-1",),
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )

    with pytest.raises(BulkWordPressDraftError) as error:
        service.confirm_request(unissued_request, now=NOW)

    assert error.value.code == "BULK_DRAFT_TOKEN_INVALID"
    assert unissued_request.used is False
    assert unissued_request.state is BulkDraftState.PREPARED


def test_prepare_request_cannot_replace_existing_request() -> None:
    service = BulkWordPressDraftService(["ebook-1"])
    first_request = service.prepare_request(now=NOW)

    with pytest.raises(BulkWordPressDraftError) as error:
        service.prepare_request(now=NOW + timedelta(minutes=1))

    assert error.value.code == "BULK_DRAFT_ALREADY_PREPARED"
    assert first_request.state is BulkDraftState.PREPARED


def test_confirmed_request_executes_successfully() -> None:
    service = BulkWordPressDraftService(
        ["ebook-1"],
        item_executor=lambda item_id: BulkDraftItemResult(
            ebook_item_id=item_id,
            status="CREATED",
            wordpress_post_id=101,
        ),
    )
    request = service.prepare_request(now=NOW)
    service.confirm_request(request, now=NOW)

    result = service.execute_request(request)

    assert result.request_id == request.request_id
    assert result.completed_count == 1
    assert result.failed_count == 0
    assert result.reconciliation_required is False
    assert result.item_results[0].wordpress_post_id == 101
    assert request.state is BulkDraftState.COMPLETED
    assert service.state is BulkDraftState.COMPLETED


def test_unconfirmed_request_cannot_execute() -> None:
    executed = []
    service = BulkWordPressDraftService(
        ["ebook-1"],
        item_executor=lambda item_id: executed.append(item_id),
    )
    request = service.prepare_request(now=NOW)

    with pytest.raises(BulkWordPressDraftError) as error:
        service.execute_request(request)

    assert error.value.code == "BULK_DRAFT_NOT_CONFIRMED"
    assert executed == []
    assert request.state is BulkDraftState.PREPARED


def test_item_failure_is_preserved_in_execution_result() -> None:
    def execute(item_id: str) -> BulkDraftItemResult:
        if item_id == "ebook-1":
            raise RuntimeError("internal detail")
        return BulkDraftItemResult(
            ebook_item_id=item_id,
            status="CREATED",
            wordpress_post_id=202,
        )

    service = BulkWordPressDraftService(
        ["ebook-1", "ebook-2"],
        item_executor=execute,
    )
    request = service.prepare_request(now=NOW)
    service.confirm_request(request, now=NOW)

    result = service.execute_request(request)

    assert result.completed_count == 1
    assert result.failed_count == 1
    assert result.item_results[0] == BulkDraftItemResult(
        ebook_item_id="ebook-1",
        status="FAILED",
        error_code="BULK_DRAFT_ITEM_FAILED",
        message="Item execution failed.",
    )
    assert result.item_results[1].status == "CREATED"
    assert request.state is BulkDraftState.PARTIAL_FAILED


def test_execute_request_preserves_selected_order() -> None:
    executed = []

    def execute(item_id: str) -> BulkDraftItemResult:
        executed.append(item_id)
        return BulkDraftItemResult(
            ebook_item_id=item_id,
            status="CREATED",
        )

    selected_item_ids = ["ebook-3", "ebook-1", "ebook-2"]
    service = BulkWordPressDraftService(
        selected_item_ids,
        item_executor=execute,
    )
    request = service.prepare_request(now=NOW)
    service.confirm_request(request, now=NOW)

    result = service.execute_request(request)

    assert executed == selected_item_ids
    assert [
        item_result.ebook_item_id
        for item_result in result.item_results
    ] == selected_item_ids


def test_reconciliation_required_is_reported_and_stops_execution() -> None:
    executed = []

    def execute(item_id: str) -> BulkDraftItemResult:
        executed.append(item_id)
        return BulkDraftItemResult(
            ebook_item_id=item_id,
            status="RECONCILIATION_REQUIRED",
            error_code="reconciliation_required",
        )

    service = BulkWordPressDraftService(
        ["ebook-1", "ebook-2"],
        item_executor=execute,
    )
    request = service.prepare_request(now=NOW)
    service.confirm_request(request, now=NOW)

    result = service.execute_request(request)

    assert executed == ["ebook-1"]
    assert result.reconciliation_required is True
    assert result.completed_count == 0
    assert result.failed_count == 2
    assert result.item_results[1].error_code == (
        "BULK_ABORTED_AFTER_RECONCILIATION"
    )
    assert request.state is BulkDraftState.RECONCILIATION_REQUIRED
    assert service.state is BulkDraftState.RECONCILIATION_REQUIRED