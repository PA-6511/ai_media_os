# Phase 8-SVC-3B Post-Install Verification Prompt

Status: DESIGN_ONLY_NO_ACTIVATION

## 目的
- SVC-3 の sudo install 実行直後に、配置結果を静的に検証する。
- activation 操作なしで PASS_UNIT_FILES_PLACED_NO_ACTIVATION 判定可否を確認する。

## 前提
- 次の2コマンドは人間が対話ターミナルで実行済みであること。

```bash
sudo install -m 0644 \
  systemd/ai-media-os-credential-ready-validator.service \
  /etc/systemd/system/ai-media-os-credential-ready-validator.service

sudo install -m 0644 \
  systemd/ai-media-os-credential-ready-validator.timer \
  /etc/systemd/system/ai-media-os-credential-ready-validator.timer
```

## 絶対禁止
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- credential.env 作成
- secret 入力
- Phase 8-29〜8-40 再実行
- WordPress API call / draft 作成 / publish

## 検証コマンド
```bash
cd /home/deploy/ai_media_os

echo "=== installed files existence ==="
ls -la /etc/systemd/system/ai-media-os-credential-ready-validator.service \
       /etc/systemd/system/ai-media-os-credential-ready-validator.timer

echo "=== repo vs installed diff: service ==="
diff -u systemd/ai-media-os-credential-ready-validator.service \
        /etc/systemd/system/ai-media-os-credential-ready-validator.service || true

echo "=== repo vs installed diff: timer ==="
diff -u systemd/ai-media-os-credential-ready-validator.timer \
        /etc/systemd/system/ai-media-os-credential-ready-validator.timer || true

echo "=== systemd-analyze verify: installed files ==="
systemd-analyze verify \
  /etc/systemd/system/ai-media-os-credential-ready-validator.service \
  /etc/systemd/system/ai-media-os-credential-ready-validator.timer

echo "verify_installed_exit=$?"

echo "=== activation unexecuted check (state only) ==="
echo "service is-enabled:" && systemctl is-enabled ai-media-os-credential-ready-validator.service || true
echo "timer is-enabled:" && systemctl is-enabled ai-media-os-credential-ready-validator.timer || true
echo "service is-active:" && systemctl is-active ai-media-os-credential-ready-validator.service || true
echo "timer is-active:" && systemctl is-active ai-media-os-credential-ready-validator.timer || true

echo "=== forbidden-operation grep ==="
grep -RInE "systemctl (enable|start|restart|daemon-reload)|requests\.(post|put|patch|delete)|curl .*wp-json|wp-json|printenv|cat /etc/ai-media-os/credential.env|echo \$WORDPRESS_|Environment=WORDPRESS_|WORDPRESS_APP_PASSWORD=" \
  systemd/ai-media-os-credential-ready-validator.service \
  systemd/ai-media-os-credential-ready-validator.timer \
  /etc/systemd/system/ai-media-os-credential-ready-validator.service \
  /etc/systemd/system/ai-media-os-credential-ready-validator.timer \
  scripts/run_phase8_credential_ready_route_no_execution.py \
  docs/runbooks/phase8_svc_1_systemd_service_unit_design.md \
  docs/runbooks/phase8_svc_2_validator_only_entrypoint.md \
  docs/runbooks/phase8_svc_4_activation_preflight_design.md || true
```

## 判定ルール
- PASS 候補:
  - installed files が2件存在
  - service/timer とも repo vs installed の diff なし
  - verify_installed_exit=0
  - enabled が enabled でない
  - active が active でない
  - forbidden-operation grep が実行コード起因の危険ヒットなし
- BLOCKED:
  - installed files が欠落
  - diff あり
  - verify_installed_exit != 0
- ABORT:
  - enable/start/restart/daemon-reload を実行してしまった
  - WordPress 実行系が検出された
  - secret 出力が検出された

## 最終報告テンプレート
```text
Phase 8-SVC-3B
status=
installed_service_file_exists=
installed_timer_file_exists=
repo_vs_installed_service_diff=
repo_vs_installed_timer_diff=
verify_installed_exit=
service_is_enabled=
timer_is_enabled=
service_is_active=
timer_is_active=
forbidden_operation_grep_result=
daemon_reload_executed=false
systemctl_enable_executed=false
systemctl_start_executed=false
systemctl_restart_executed=false
credential_env_created=false
secret_input_executed=false
phase8_29_to_8_40_rerun_executed=false
wordpress_api_call_attempted=false
wordpress_draft_created=false
wordpress_publish_executed=false
external_changes=2
external_changes_detail_1=/etc/systemd/system/ai-media-os-credential-ready-validator.service
external_changes_detail_2=/etc/systemd/system/ai-media-os-credential-ready-validator.timer
```

## 期待ステータス
- 全条件満たす: PASS_UNIT_FILES_PLACED_NO_ACTIVATION
- sudo install 未完了: REPO_UNIT_READY_INSTALL_BLOCKED_BY_SUDO_AUTH
