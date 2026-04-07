from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_mock_server_check_markdown() -> str:
    generated_at = _now_iso()

    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append("#" * level + " " + text)
        lines.append("")

    def para(*text: str) -> None:
        for t in text:
            lines.append(t)
        lines.append("")

    def warn(text: str) -> None:
        lines.append(f"> **⚠️ 注意:** {text}")
        lines.append("")

    def tip(text: str) -> None:
        lines.append(f"> **💡 ポイント:** {text}")
        lines.append("")

    def code(lang: str, *cmds: str) -> None:
        lines.append(f"```{lang}")
        for c in cmds:
            lines.append(c)
        lines.append("```")
        lines.append("")

    # ------------------------------------------------------------------ header
    h(1, "Mock Server 確認手順")
    para(
        f"generated_at: `{generated_at}`",
        "",
        "このドキュメントは AI Media OS GUI mock server の",
        "**正しい起動・確認・停止手順**をまとめたものです。",
        "",
        "「起動後に Ctrl+C で止めてから curl してしまう」運用ミスを防ぐため、",
        "foreground / background それぞれの手順を明記しています。",
    )

    # --------------------------------------------------------- よくある誤操作
    h(2, "⛔ よくある誤操作（やってはいけないこと）")
    warn(
        "foreground 起動したターミナルで **Ctrl+C を押してから** 同じターミナルで "
        "`curl` を打っても、サーバーはすでに停止しているため "
        "`Connection refused` になります。"
    )
    para(
        "```",
        "# ❌ 誤った操作の流れ",
        "$ python3 -m gui.run_mock_server   # 同じターミナルで起動",
        "^C                                 # ← Ctrl+C で停止してしまう",
        "$ curl http://127.0.0.1:8766/health  # ← Connection refused",
        "```",
        "",
        "**正しい操作は「サーバーを起動したまま」別ターミナルから `curl` することです。**",
    )

    # ------------------------------------------------------- 方法 1: foreground
    h(2, "方法 1: Foreground 起動（開発時推奨）")
    para(
        "ログをリアルタイムで目視したい開発時に使います。",
        "**ターミナルを 2 つ用意してください。**",
    )

    h(3, "ターミナル 1 ── サーバー起動")
    tip("Ctrl+C は確認が終わるまで押さないでください。")
    code(
        "bash",
        "cd ~/ai_media_os",
        "python3 -m gui.run_mock_server",
    )
    para(
        "起動成功時の出力例:",
        "",
        "```",
        "============================================================",
        "  MOCK SERVER READY",
        "  final_port  : 8766",
        "  server_url  : http://127.0.0.1:8766/",
        "  pid         : 12345",
        "  stop        : Ctrl+C or SIGTERM",
        "============================================================",
        "```",
        "",
        "`final_port` の値（例: `8766`）を控えてください。",
        "この値を以降の確認コマンドで使います。",
    )

    h(3, "ターミナル 2 ── 確認コマンド（サーバーを止めずに実行）")
    warn(
        "ターミナル 1 の Ctrl+C は **確認がすべて終わるまで押さない**でください。"
    )
    code(
        "bash",
        "cd ~/ai_media_os",
        "",
        "# 確定ポートの確認",
        "cat data/reports/mock_server_runtime_latest.json",
        "",
        "# ポートが LISTEN しているか確認",
        "ss -ltnp | grep 8766",
        "",
        "# 案内エンドポイント",
        "curl http://127.0.0.1:8766/",
        "curl http://127.0.0.1:8766/docs",
        "",
        "# ヘルスチェック",
        "curl http://127.0.0.1:8766/health",
        "",
        "# JSON endpoint index",
        "curl http://127.0.0.1:8766/api/index",
        "",
        "# データ API",
        "curl http://127.0.0.1:8766/api/home",
        "curl http://127.0.0.1:8766/api/bootstrap",
    )

    h(3, "ターミナル 1 ── 確認後の停止")
    para("確認がすべて終わったら、ターミナル 1 で:")
    code("bash", "# Ctrl+C を押す")

    # ---------------------------------------------------- 方法 2: background
    h(2, "方法 2: Background 起動（CI・長時間運用推奨）")
    para(
        "ターミナルを 1 つで完結させたい場合や、",
        "停止せず並行作業したい場合に使います。",
    )

    h(3, "起動")
    code(
        "bash",
        "cd ~/ai_media_os",
        "bash gui/run_mock_server_bg.sh",
    )
    para(
        "起動成功時の出力例:",
        "",
        "```",
        "============================================================",
        "  MOCK SERVER BACKGROUND",
        "  pid         : 12345",
        "  final_port  : 8766",
        "  server_url  : http://127.0.0.1:8766/",
        "  log         : data/logs/mock_server.out",
        "  pid_file    : data/run/mock_server.pid",
        "  confirm:  curl http://127.0.0.1:8766/health",
        "  stop:     bash gui/stop_mock_server.sh",
        "============================================================",
        "```",
    )

    h(3, "確認")
    code(
        "bash",
        "cd ~/ai_media_os",
        "",
        "# 確定ポートを runtime JSON から確認",
        "cat data/reports/mock_server_runtime_latest.json",
        "",
        "# ポートが LISTEN しているか確認",
        "PORT=$(python3 -c \"import json; print(json.load(open('data/reports/mock_server_runtime_latest.json'))['final_port'])\")",
        "ss -ltnp | grep $PORT",
        "",
        "# ヘルスチェック",
        "curl http://127.0.0.1:$PORT/health",
        "",
        "# endpoint index",
        "curl http://127.0.0.1:$PORT/api/index",
        "",
        "# ログ確認",
        "tail -20 data/logs/mock_server.out",
    )

    h(3, "停止")
    code(
        "bash",
        "cd ~/ai_media_os",
        "bash gui/stop_mock_server.sh",
    )

    h(3, "PID 手動確認・手動停止")
    code(
        "bash",
        "# PID の確認",
        "cat data/run/mock_server.pid",
        "",
        "# プロセスが生きているか確認",
        "kill -0 $(cat data/run/mock_server.pid) && echo running || echo stopped",
        "",
        "# 手動 SIGTERM（stop スクリプトと同等）",
        "kill -TERM $(cat data/run/mock_server.pid)",
    )

    # ----------------------------------------------------------- 確認観点
    h(2, "確認観点チェックリスト")
    para(
        "| 確認項目 | コマンド | 期待値 |",
        "|---|---|---|",
        "| ポート LISTEN | `ss -ltnp \\| grep 8766` | `LISTEN 127.0.0.1:8766` が出る |",
        "| runtime JSON 存在 | `cat data/reports/mock_server_runtime_latest.json` | `final_port` / `server_url` が入っている |",
        "| ヘルスチェック | `curl .../health` | `{\"ok\": true}` |",
        "| endpoint index | `curl .../api/index` | `endpoint_count` が 9 以上 |",
        "| 案内ページ | `curl .../` | `available_endpoints` 一覧が返る |",
        "| docs | `curl .../docs` | plain text で endpoint 一覧が返る |",
        "| データ API | `curl .../api/home` | `ok: true` の JSON が返る |",
    )
    lines.append("")

    # -------------------------------------------------------- ポート競合対応
    h(2, "ポート競合が起きた場合")
    para(
        "起動スクリプトは `8766` から順に `8775` まで自動的に空きポートを探します。",
        "採用されたポートは必ず起動ログと `mock_server_runtime_latest.json` に記録されます。",
    )
    code(
        "bash",
        "# 実際に採用されたポートを確認",
        "python3 -c \"import json; d=json.load(open('data/reports/mock_server_runtime_latest.json')); print(d['server_url'])\"",
        "",
        "# スキップされたポートも確認可能",
        "python3 -c \"import json; d=json.load(open('data/reports/mock_server_runtime_latest.json')); print('skipped:', d['skipped_ports'])\"",
    )

    # -------------------------------------------------------- トラブルシュート
    h(2, "トラブルシュート")

    h(3, "Connection refused が出る")
    para(
        "1. サーバーがまだ起動していない → 起動ログで `MOCK SERVER READY` を確認",
        "2. **Ctrl+C でサーバーを止めてから curl している** → サーバーを再起動してから別ターミナルで curl",
        "3. ポートがずれている → `cat data/reports/mock_server_runtime_latest.json` で `final_port` を確認",
        "4. プロセスが異常終了している → `cat data/logs/mock_server.out` でエラーを確認",
    )

    h(3, "Ctrl+C を押してしまった後の復旧")
    code(
        "bash",
        "# foreground の場合: そのまま再起動",
        "python3 -m gui.run_mock_server",
        "",
        "# background の場合",
        "bash gui/stop_mock_server.sh  # 念のりにクリーンアップ",
        "bash gui/run_mock_server_bg.sh",
    )

    h(3, "サーバープロセスが残留している場合")
    code(
        "bash",
        "# mock server プロセスをすべて確認",
        "ps aux | grep run_mock_server | grep -v grep",
        "",
        "# PID を指定して停止",
        "kill -TERM <PID>",
    )

    # ------------------------------------------------------------------ footer
    h(2, "関連ファイル")
    para(
        "| ファイル | 説明 |",
        "|---|---|",
        "| `gui/mock_server.py` | HTTP ハンドラ・エンドポイント定義 |",
        "| `gui/run_mock_server.py` | foreground 起動エントリポイント |",
        "| `gui/run_mock_server_bg.sh` | background 起動スクリプト |",
        "| `gui/stop_mock_server.sh` | 停止スクリプト |",
        "| `data/run/mock_server.pid` | 稼働中 PID（停止後は削除） |",
        "| `data/logs/mock_server.out` | サーバーログ |",
        "| `data/reports/mock_server_runtime_latest.json` | 確定ポート・URL（停止後は削除） |",
    )
    lines.append("")
    lines.append(f"*generated_at: {generated_at}*")
    lines.append("")

    return "\n".join(lines)
