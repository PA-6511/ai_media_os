# Phase 8-SVC-1: systemd service unit design for Credential Ready route

Status: DESIGN_ONLY_NO_GO

## 1. 目的
- Credential Ready ルートの再検証実行基盤を systemd で設計固定する。
- このフェーズでは unit 設計のみを行い、enable/start/restart は実行しない。
- WordPress API call / draft 作成 / publish を含む処理は対象外とする。

## 2. 観測結果（2026-06-01）
- systemd に ai_media_os 系 service は未導入。
- systemd timer に ai_media_os 専用エントリは未導入。
- /etc/cron.d などに ai_media_os 専用 cron ファイルは未導入。
- リポジトリ運用資料には cron ベース運用が記載されている。
- 実行ユーザー候補は deploy、グループ候補は deploy。

## 3. Phase 8-SVC-1 で固定する値
- SERVICE_NAME_HERE=ai-media-os-credential-ready-validator.service
- SERVICE_USER_HERE=deploy
- SERVICE_GROUP_HERE=deploy
- WorkingDirectory=/home/deploy/ai_media_os
- EnvironmentFile=/etc/ai-media-os/credential.env

## 4. ExecStart 設計方針
現時点で systemd 常駐 service は未導入のため、Credential Ready 専用の validator entrypoint を固定対象にする。

候補（設計上の固定値）:
- ExecStart=/usr/bin/python3 /home/deploy/ai_media_os/scripts/run_phase8_credential_ready_route_no_execution.py

要件:
- WordPress API call なし
- draft 作成なし
- publish なし
- DRY_RUN / NO_GO 固定
- secret 値非出力

注記:
- 上記 entrypoint は本フェーズでは設計のみ。実ファイル作成は次フェーズで実施する。

## 5. service unit 草案（DESIGN_ONLY）
配置候補:
- /etc/systemd/system/ai-media-os-credential-ready-validator.service

```ini
[Unit]
Description=ai_media_os Credential Ready validator route (NO_EXECUTION)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/ai_media_os
EnvironmentFile=/etc/ai-media-os/credential.env
ExecStart=/usr/bin/python3 /home/deploy/ai_media_os/scripts/run_phase8_credential_ready_route_no_execution.py

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/home/deploy/ai_media_os/exchange/logs /home/deploy/ai_media_os/data/logs
UMask=0027

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-media-os-credential-ready

# oneshot のため自動再起動は無効
Restart=no
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

## 6. timer 草案（必要時のみ / DESIGN_ONLY）
配置候補:
- /etc/systemd/system/ai-media-os-credential-ready-validator.timer

```ini
[Unit]
Description=Run ai_media_os Credential Ready validator route periodically

[Timer]
OnCalendar=hourly
Persistent=true
Unit=ai-media-os-credential-ready-validator.service

[Install]
WantedBy=timers.target
```

## 7. ハードニング項目
- NoNewPrivileges=true
- PrivateTmp=true
- ProtectSystem=full
- ProtectHome=true
- UMask=0027
- ReadWritePaths を exchange/logs と data/logs のみに限定

## 8. ログ設計
- 主系: journalctl（SyslogIdentifier=ai-media-os-credential-ready）
- 補助: アプリ側で exchange/logs/*.json, *.md を生成

## 9. このフェーズで実行しない操作
- systemctl daemon-reload
- systemctl enable/start/restart
- credential.env 作成
- secret 入力
- Phase 8-29〜8-40 再実行

## 10. 次フェーズ（実装前提）
1. scripts/run_phase8_credential_ready_route_no_execution.py を実装
2. python3 実行で WordPress API call が発生しないことを検証
3. unit ファイルを配置（まだ起動しない）
4. Step 1 再確認で SERVICE_NAME_HERE/User/Group を実値で確定
5. その後に Credential Ready 実整備へ遷移
