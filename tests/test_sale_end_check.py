"""tests/test_sale_end_check.py

sale_end_check.py のユニットテスト。

テスト方針:
  - 外部接続 (Google Sheets / OpenAI / WordPress) は一切使わない。
  - src.sheets / src.slack_notifier は unittest.mock でモックする。
  - 純粋ロジック関数 (determine_new_status / process_rows) を直接テスト。
  - main() は --dry-run で実行し exit_code の正確さを検証する。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# --- プロジェクトルートを sys.path に追加 ---
PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# --- sale_end_check モジュールをロード (scripts/ は通常パッケージ外) ---
_spec = importlib.util.spec_from_file_location(
    "sale_end_check",
    PROJECT_DIR / "scripts" / "sale_end_check.py",
)
_mod = importlib.util.module_from_spec(_spec)   # type: ignore[arg-type]
_spec.loader.exec_module(_mod)                  # type: ignore[union-attr]

# テスト対象の関数・定数を取り出す
determine_new_status = _mod.determine_new_status
process_rows = _mod.process_rows
load_local_sale_items = _mod.load_local_sale_items
_parse_date = _mod._parse_date
EXPIRED_STATUS_MAP = _mod.EXPIRED_STATUS_MAP
SKIP_STATUSES = _mod.SKIP_STATUSES
SALE_TYPES = _mod.SALE_TYPES

TODAY = date(2026, 4, 27)


# ============================================================
# _parse_date
# ============================================================
class TestParseDate(unittest.TestCase):
    def test_valid_iso(self) -> None:
        self.assertEqual(_parse_date("2026-04-01"), date(2026, 4, 1))

    def test_valid_iso8601_with_time(self) -> None:
        self.assertEqual(_parse_date("2026-04-01T12:00:00+00:00"), date(2026, 4, 1))

    def test_empty_string(self) -> None:
        self.assertIsNone(_parse_date(""))

    def test_invalid_string(self) -> None:
        self.assertIsNone(_parse_date("not-a-date"))


# ============================================================
# determine_new_status  (純粋関数)
# ============================================================
class TestDetermineNewStatus(unittest.TestCase):
    def _row(
        self,
        work_id: str = "manga_001",
        article_type: str = "sale_article",
        status: str = "PUBLISHED",
        sale_end_date: str | None = None,
    ) -> dict:
        row: dict = {
            "work_id": work_id,
            "article_type": article_type,
            "status": status,
        }
        if sale_end_date is not None:
            row["sale_end_date"] = sale_end_date
        return row

    # --- article_type フィルタ ---
    def test_non_sale_type_returns_none(self) -> None:
        row = self._row(article_type="summary_article", sale_end_date="2026-04-01")
        self.assertIsNone(determine_new_status(row, TODAY))

    def test_sale_type_alias(self) -> None:
        """'sale' でも対象になる。"""
        row = self._row(article_type="sale", status="PUBLISHED", sale_end_date="2026-04-26")
        self.assertIsNotNone(determine_new_status(row, TODAY))

    # --- status フィルタ ---
    def test_failed_skipped(self) -> None:
        for st in ("FAILED", "SKIPPED", "STATUS_CONFLICT"):
            with self.subTest(status=st):
                row = self._row(status=st, sale_end_date="2026-04-01")
                self.assertIsNone(determine_new_status(row, TODAY))

    # --- sale_end_date ---
    def test_missing_sale_end_date_returns_none(self) -> None:
        row = self._row(status="PUBLISHED")  # sale_end_date なし
        self.assertIsNone(determine_new_status(row, TODAY))

    def test_empty_sale_end_date_returns_none(self) -> None:
        row = self._row(status="PUBLISHED", sale_end_date="")
        self.assertIsNone(determine_new_status(row, TODAY))

    def test_invalid_date_returns_none(self) -> None:
        row = self._row(status="PUBLISHED", sale_end_date="invalid-date")
        self.assertIsNone(determine_new_status(row, TODAY))

    # --- 期限切れ判定 ---
    def test_published_expired_returns_needs_update(self) -> None:
        yesterday = str(TODAY - timedelta(days=1))
        row = self._row(status="PUBLISHED", sale_end_date=yesterday)
        self.assertEqual(determine_new_status(row, TODAY), "NEEDS_UPDATE")

    def test_ends_today_is_expired(self) -> None:
        """sale_end_date == today は終了扱い（NEEDS_UPDATE）。"""
        row = self._row(status="PUBLISHED", sale_end_date=str(TODAY))
        self.assertEqual(determine_new_status(row, TODAY), "NEEDS_UPDATE")

    def test_active_sale_returns_none(self) -> None:
        tomorrow = str(TODAY + timedelta(days=1))
        row = self._row(status="PUBLISHED", sale_end_date=tomorrow)
        self.assertIsNone(determine_new_status(row, TODAY))

    def test_drafted_expired_returns_sale_ended(self) -> None:
        yesterday = str(TODAY - timedelta(days=1))
        row = self._row(status="DRAFTED", sale_end_date=yesterday)
        self.assertEqual(determine_new_status(row, TODAY), "SALE_ENDED")

    def test_all_sale_ended_statuses(self) -> None:
        """SALE_ENDED に変換されるべき status 一覧。"""
        yesterday = str(TODAY - timedelta(days=1))
        for st in ("DRAFTED", "NEEDS_REVIEW", "NEW", "GENERATED", "DRAFTING"):
            with self.subTest(status=st):
                row = self._row(status=st, sale_end_date=yesterday)
                self.assertEqual(determine_new_status(row, TODAY), "SALE_ENDED")

    def test_unknown_status_returns_none(self) -> None:
        """マップにない status は None（スキップ）。"""
        yesterday = str(TODAY - timedelta(days=1))
        row = self._row(status="MYSTERY_STATUS", sale_end_date=yesterday)
        self.assertIsNone(determine_new_status(row, TODAY))


# ============================================================
# load_local_sale_items
# ============================================================
class TestLoadLocalSaleItems(unittest.TestCase):
    def test_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_local_sale_items(Path(d)), [])

    def test_nonexistent_dir(self) -> None:
        self.assertEqual(load_local_sale_items(Path("/nonexistent_xyz")), [])

    def test_loads_sale_article_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manga_0001_sale_article_plan.json"
            p.write_text(json.dumps({"work_id": "manga_0001"}), encoding="utf-8")
            # 非 sale ファイルは無視される
            q = Path(d) / "manga_0001_summary_article_output.json"
            q.write_text(json.dumps({"work_id": "manga_0001"}), encoding="utf-8")
            items = load_local_sale_items(Path(d))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["work_id"], "manga_0001")

    def test_skips_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manga_0001_sale_article_plan.json"
            p.write_text("{ broken json", encoding="utf-8")
            self.assertEqual(load_local_sale_items(Path(d)), [])

    def test_normalizes_article_type(self) -> None:
        """article_type が未設定なら 'sale_article' を補完する。"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manga_0001_sale_article_plan.json"
            p.write_text(json.dumps({"work_id": "manga_0001"}), encoding="utf-8")
            items = load_local_sale_items(Path(d))
        self.assertEqual(items[0]["article_type"], "sale_article")


# ============================================================
# process_rows
# ============================================================
class TestProcessRows(unittest.TestCase):
    def _make_row(self, work_id: str, status: str, sale_end_date: str | None,
                  row_index: int = 2) -> dict:
        row: dict = {
            "work_id": work_id,
            "article_type": "sale_article",
            "status": status,
            "_row_index": row_index,
        }
        if sale_end_date is not None:
            row["sale_end_date"] = sale_end_date
        return row

    def test_update_fn_called_for_expired(self) -> None:
        yesterday = str(TODAY - timedelta(days=1))
        rows = [self._make_row("manga_001", "PUBLISHED", yesterday, row_index=2)]
        update_calls: list[tuple] = []
        result = process_rows(
            rows, TODAY,
            update_fn=lambda ri, st: update_calls.append((ri, st)),
        )
        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(update_calls, [(2, "NEEDS_UPDATE")])

    def test_update_fn_not_called_in_dry_run(self) -> None:
        """update_fn=None のとき Sheets 更新は発生しない（dry-run 相当）。"""
        yesterday = str(TODAY - timedelta(days=1))
        rows = [self._make_row("manga_001", "PUBLISHED", yesterday)]
        result = process_rows(rows, TODAY, update_fn=None)
        # updated には記録される
        self.assertEqual(len(result["updated"]), 1)

    def test_skipped_items_not_in_updated(self) -> None:
        """active なアイテムは skipped に入る。"""
        tomorrow = str(TODAY + timedelta(days=1))
        rows = [self._make_row("manga_002", "PUBLISHED", tomorrow)]
        result = process_rows(rows, TODAY)
        self.assertIn("manga_002", result["skipped"])
        self.assertEqual(len(result["updated"]), 0)

    def test_failed_status_skipped(self) -> None:
        yesterday = str(TODAY - timedelta(days=1))
        rows = [self._make_row("manga_003", "FAILED", yesterday)]
        result = process_rows(rows, TODAY)
        self.assertIn("manga_003", result["skipped"])

    def test_error_fn_called_on_exception(self) -> None:
        """update_fn が例外を投げたとき error_fn が呼ばれ errors に記録される。"""
        yesterday = str(TODAY - timedelta(days=1))
        rows = [self._make_row("manga_004", "PUBLISHED", yesterday, row_index=3)]
        error_calls: list[tuple] = []

        def bad_update(ri: int, st: str) -> None:
            raise RuntimeError("sheets error")

        result = process_rows(
            rows, TODAY,
            update_fn=bad_update,
            error_fn=lambda ri, msg: error_calls.append((ri, msg)),
        )
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["work_id"], "manga_004")
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0][0], 3)

    def test_continues_after_single_error(self) -> None:
        """1行エラーでも次の行を処理する。"""
        yesterday = str(TODAY - timedelta(days=1))
        rows = [
            self._make_row("manga_005", "PUBLISHED", yesterday, row_index=2),
            self._make_row("manga_006", "DRAFTED", yesterday, row_index=3),
        ]
        call_count = 0

        def flaky_update(ri: int, st: str) -> None:
            nonlocal call_count
            call_count += 1
            if ri == 2:
                raise RuntimeError("first row fail")

        result = process_rows(rows, TODAY, update_fn=flaky_update)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["updated"][0]["work_id"], "manga_006")

    def test_mixed_rows(self) -> None:
        yesterday = str(TODAY - timedelta(days=1))
        tomorrow = str(TODAY + timedelta(days=1))
        rows = [
            self._make_row("ended_01", "PUBLISHED", yesterday),
            self._make_row("active_01", "PUBLISHED", tomorrow),
            self._make_row("skip_01", "FAILED", yesterday),
            self._make_row("nodate_01", "PUBLISHED", None),
        ]
        result = process_rows(rows, TODAY)
        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["updated"][0]["work_id"], "ended_01")
        self.assertEqual(len(result["skipped"]), 3)


# ============================================================
# main()  exit code
# ============================================================
class TestMainExitCode(unittest.TestCase):
    """main() の終了コードと Sheets 連携の組み合わせを検証する。"""

    def _run_main_dry_run(self, items_dir: Path) -> int:
        return _mod.main(["--dry-run", "--items-dir", str(items_dir)])

    def test_no_ended_sales_returns_0(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tomorrow = str(datetime.now(timezone.utc).date() + timedelta(days=1))
            (Path(d) / "m_sale_article_plan.json").write_text(
                json.dumps({"work_id": "m_001", "sale_end_date": tomorrow, "status": "PUBLISHED"}),
                encoding="utf-8",
            )
            # Sheets 接続は失敗させて fallback させる
            with patch.object(_mod, "importlib") as mock_imp:
                mock_imp.import_module.side_effect = ValueError("env not set")
                exit_code = self._run_main_dry_run(Path(d))
        self.assertEqual(exit_code, 0)

    def test_ended_sales_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            yesterday = str(datetime.now(timezone.utc).date() - timedelta(days=1))
            (Path(d) / "m_sale_article_plan.json").write_text(
                json.dumps({
                    "work_id": "m_002",
                    "sale_end_date": yesterday,
                    "status": "PUBLISHED",
                    "article_type": "sale_article",
                }),
                encoding="utf-8",
            )
            with patch.object(_mod, "importlib") as mock_imp:
                mock_imp.import_module.side_effect = ValueError("env not set")
                exit_code = self._run_main_dry_run(Path(d))
        self.assertEqual(exit_code, 1)

    def test_main_uses_sheets_when_available(self) -> None:
        """Sheets 接続が成功したとき fetch_all_rows が呼ばれる。"""
        mock_sheets = MagicMock()
        mock_sheet = MagicMock()
        mock_sheets.get_sheet.return_value = mock_sheet
        mock_sheets.fetch_all_rows.return_value = []  # 空 = 変更なし
        mock_notifier = MagicMock()
        mock_notifier.notify_sale_ended.return_value = True

        def fake_import(name: str):
            if name == "src.sheets":
                return mock_sheets
            if name == "src.slack_notifier":
                return mock_notifier
            return importlib.import_module(name)

        with patch.object(_mod, "importlib") as mock_imp:
            mock_imp.import_module.side_effect = fake_import
            exit_code = _mod.main(["--items-dir", "/tmp"])
        mock_sheets.get_sheet.assert_called_once()
        mock_sheets.fetch_all_rows.assert_called_once_with(mock_sheet)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()

