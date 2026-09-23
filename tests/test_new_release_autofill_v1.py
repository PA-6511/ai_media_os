from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "scripts"
    / "run_new_release_autofill_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "run_new_release_autofill_v1",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def make_args(**overrides):
    values = {
        "month": "2026-09",
        "max_items": 10,
        "execute": False,
        "kobo_pacing_seconds": 0.0,
        "dmm_pacing_seconds": 0.0,
        "amazon_request_interval_seconds": 0.0,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_component_failure_does_not_stop_others(
    monkeypatch,
):
    module = load_module()
    calls = []

    monkeypatch.setattr(
        module,
        "select_month_item_ids",
        lambda **kwargs: ["item-1"],
    )

    def fail_kobo(**kwargs):
        calls.append("kobo")
        raise RuntimeError("kobo failed")

    def ok_dmm(**kwargs):
        calls.append("dmm")
        return {"ready": 1}

    def ok_amazon(**kwargs):
        calls.append("amazon")
        return {"saved": 1}

    def ok_metadata(**kwargs):
        calls.append("metadata")
        return {"applied": 1}

    monkeypatch.setattr(
        module,
        "run_kobo",
        fail_kobo,
    )
    monkeypatch.setattr(
        module,
        "run_dmm",
        ok_dmm,
    )
    monkeypatch.setattr(
        module,
        "run_amazon",
        ok_amazon,
    )
    monkeypatch.setattr(
        module,
        "run_metadata",
        ok_metadata,
    )

    result = module.run_autofill(
        make_args()
    )

    assert result["status"] == "PARTIAL"
    assert (
        result["components"]["kobo"]["status"]
        == "ERROR"
    )
    assert (
        result["components"]["dmm"]["status"]
        == "OK"
    )
    assert (
        result["components"]["amazon"]["status"]
        == "OK"
    )
    assert (
        result["components"]["metadata"]["status"]
        == "OK"
    )
    assert calls == [
        "kobo",
        "dmm",
        "amazon",
        "metadata",
    ]


def test_execute_flag_is_forwarded(
    monkeypatch,
):
    module = load_module()
    received = {}

    monkeypatch.setattr(
        module,
        "select_month_item_ids",
        lambda **kwargs: ["item-1"],
    )

    def capture(name):
        def runner(**kwargs):
            received[name] = kwargs["execute"]
            return {}
        return runner

    monkeypatch.setattr(
        module,
        "run_kobo",
        capture("kobo"),
    )
    monkeypatch.setattr(
        module,
        "run_dmm",
        capture("dmm"),
    )
    monkeypatch.setattr(
        module,
        "run_amazon",
        capture("amazon"),
    )
    monkeypatch.setattr(
        module,
        "run_metadata",
        capture("metadata"),
    )

    result = module.run_autofill(
        make_args(execute=True)
    )

    assert result["status"] == "PASS"
    assert received == {
        "kobo": True,
        "dmm": True,
        "amazon": True,
        "metadata": True,
    }


def test_metadata_targets_include_store_candidates(
    monkeypatch,
):
    module = load_module()
    captured = {}

    monkeypatch.setattr(
        module,
        "select_month_item_ids",
        lambda **kwargs: ["base-1"],
    )

    monkeypatch.setattr(
        module,
        "run_kobo",
        lambda **kwargs: {
            "results": [
                {
                    "ebook_item_id": "kobo-1",
                }
            ]
        },
    )

    monkeypatch.setattr(
        module,
        "run_dmm",
        lambda **kwargs: {
            "results": [
                {
                    "ebook_item_id": "dmm-1",
                }
            ]
        },
    )

    def metadata_runner(**kwargs):
        captured["item_ids"] = (
            kwargs["item_ids"]
        )
        return {}

    monkeypatch.setattr(
        module,
        "run_metadata",
        metadata_runner,
    )

    result = module.run_autofill(
        make_args(
            skip_amazon=True,
        )
    )

    assert result["status"] == "PASS"

    assert captured["item_ids"] == [
        "kobo-1",
        "dmm-1",
        "base-1",
    ]



def test_kobo_missing_offer_path_reuses_existing_enricher(
    monkeypatch,
):
    module = load_module()

    import app.services.monthly_comic_release_sync as monthly_mod

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def scalar(
            self,
            statement,
        ):
            # Exact target has no Kobo offer.
            return None

        def rollback(self):
            pass

        def commit(self):
            pass

    monkeypatch.setattr(
        module,
        "SessionLocal",
        lambda: FakeSession(),
    )

    calls = []

    def fake_kobo_enrich(
        ebook_item_id,
        *,
        execute,
    ):
        calls.append(
            (
                ebook_item_id,
                execute,
            )
        )

        return {
            "ebook_item_id":
                ebook_item_id,
            "status":
                "SAVED",
            "offer_id":
                "offer-1",
        }

    monkeypatch.setattr(
        monthly_mod,
        "_kobo_enrich",
        fake_kobo_enrich,
    )

    result = module.run_kobo(
        execute=True,
        start_date=module.date(
            2026,
            9,
            1,
        ),
        end_date=module.date(
            2026,
            9,
            30,
        ),
        max_items=10,
        pacing_seconds=0.0,
        item_ids=[
            "missing-kobo",
        ],
    )

    assert calls == [
        (
            "missing-kobo",
            True,
        ),
    ]

    assert result["selected_count"] == 1

    assert result["results"] == [
        {
            "ebook_item_id":
                "missing-kobo",
            "status":
                "SAVED",
            "offer_id":
                "offer-1",
        }
    ]




def test_kobo_dry_run_does_not_call_missing_offer_enricher(
    monkeypatch,
):
    module = load_module()

    import app.services.monthly_comic_release_sync as monthly_mod

    def must_not_open_session():
        raise AssertionError(
            "dry-run must not open DB session"
        )

    def must_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "_kobo_enrich must not run in dry-run"
        )

    monkeypatch.setattr(
        module,
        "SessionLocal",
        must_not_open_session,
    )

    monkeypatch.setattr(
        monthly_mod,
        "_kobo_enrich",
        must_not_run,
    )

    result = module.run_kobo(
        execute=False,
        start_date=module.date(
            2026,
            9,
            1,
        ),
        end_date=module.date(
            2026,
            9,
            30,
        ),
        max_items=10,
        pacing_seconds=0.0,
        item_ids=[
            "dry-kobo",
        ],
    )

    assert result == {
        "selected_count": 1,
        "results": [
            {
                "ebook_item_id":
                    "dry-kobo",
                "status":
                    "SKIPPED_DRY_RUN",
            }
        ],
    }



def test_rakuten_detail_fallback_is_blank_only(
    monkeypatch,
):
    module = load_module()

    from dataclasses import replace

    import app.services.monthly_comic_release_sync as monthly_mod

    class FakeItem:
        id = "item-1"
        source_item_id = "rb-12345678"
        title = "テスト漫画 7"
        release_date = module.date(
            2026,
            9,
            24,
        )
        source_url = (
            "https://books.rakuten.co.jp/"
            "rb/12345678/"
        )

        isbn = None
        author_name = None

        # Existing non-empty value must survive.
        publisher_name = "既存出版社"

        series_name = "既存シリーズ"
        volume_label = "7"

    item = FakeItem()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def get(
            self,
            model,
            ebook_item_id,
        ):
            assert ebook_item_id == "item-1"
            return item

        def rollback(self):
            pass

        def commit(self):
            pass

    monkeypatch.setattr(
        module,
        "SessionLocal",
        lambda: FakeSession(),
    )

    def fake_enrich(
        records,
        **kwargs,
    ):
        record = list(records)[0]

        return [
            replace(
                record,
                isbn="9784040000000",
                author_name="取得著者",
                publisher_name="上書き禁止出版社",
                series_name="上書き禁止シリーズ",
                volume_label="99",
            )
        ]

    monkeypatch.setattr(
        monthly_mod,
        "enrich_rakuten_product_metadata",
        fake_enrich,
    )

    result = (
        module._run_rakuten_detail_fallback(
            ebook_item_id="item-1",
            execute=True,
        )
    )

    assert result["status"] == "APPLIED"

    assert result["applied_fields"] == [
        "author_name",
        "isbn",
    ]

    assert item.isbn == "9784040000000"
    assert item.author_name == "取得著者"

    assert (
        item.publisher_name
        == "既存出版社"
    )
    assert item.series_name == "既存シリーズ"
    assert item.volume_label == "7"


def test_rakuten_detail_fallback_dry_run_does_not_write(
    monkeypatch,
):
    module = load_module()

    from dataclasses import replace

    import app.services.monthly_comic_release_sync as monthly_mod

    class FakeItem:
        id = "item-2"
        source_item_id = "rb-87654321"
        title = "テスト漫画 8"
        release_date = module.date(
            2026,
            9,
            24,
        )
        source_url = (
            "https://books.rakuten.co.jp/"
            "rb/87654321/"
        )

        isbn = None
        author_name = None
        publisher_name = None
        series_name = None
        volume_label = "8"

    item = FakeItem()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def get(
            self,
            model,
            ebook_item_id,
        ):
            return item

        def rollback(self):
            pass

        def commit(self):
            raise AssertionError(
                "dry-run must not commit"
            )

    monkeypatch.setattr(
        module,
        "SessionLocal",
        lambda: FakeSession(),
    )

    def fake_enrich(
        records,
        **kwargs,
    ):
        record = list(records)[0]

        return [
            replace(
                record,
                isbn="9784041111111",
                author_name="著者A",
                publisher_name="出版社A",
                series_name="シリーズA",
            )
        ]

    monkeypatch.setattr(
        monthly_mod,
        "enrich_rakuten_product_metadata",
        fake_enrich,
    )

    result = (
        module._run_rakuten_detail_fallback(
            ebook_item_id="item-2",
            execute=False,
        )
    )

    assert (
        result["status"]
        == "DRY_RUN_READY"
    )

    assert item.isbn is None
    assert item.author_name is None
    assert item.publisher_name is None
    assert item.series_name is None
    assert item.volume_label == "8"


def test_selected_ids_are_forwarded_to_every_store(
    monkeypatch,
):
    module = load_module()

    selected = [
        "scope-1",
        "scope-2",
    ]

    received = {}

    monkeypatch.setattr(
        module,
        "select_month_item_ids",
        lambda **kwargs: selected,
    )

    def capture(name):
        def runner(**kwargs):
            received[name] = list(
                kwargs["item_ids"]
            )

            return {
                "results": [],
            }

        return runner

    monkeypatch.setattr(
        module,
        "run_kobo",
        capture("kobo"),
    )

    monkeypatch.setattr(
        module,
        "run_dmm",
        capture("dmm"),
    )

    monkeypatch.setattr(
        module,
        "run_amazon",
        capture("amazon"),
    )

    monkeypatch.setattr(
        module,
        "run_metadata",
        lambda **kwargs: {
            "selected_count":
                len(
                    kwargs["item_ids"]
                ),
        },
    )

    result = module.run_autofill(
        make_args()
    )

    assert result["status"] == "PASS"

    assert received == {
        "kobo": selected,
        "dmm": selected,
        "amazon": selected,
    }
