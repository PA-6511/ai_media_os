# Credential Ready 実整備・再検証プロンプト v2 完全版

対象: /home/deploy/ai_media_os

## 目的
- /etc/ai-media-os/credential.env を systemd EnvironmentFile 方式で安全に整備する。
- secret 非露出のまま Phase 8-29〜8-31、Phase 8-35、Phase 8-36〜8-40 を再実行する。
- PHASE8_36_TO_8_40_TRIAL_ROUTE_READY_FOR_FIRST_ONE_ITEM_TRIAL_NO_EXECUTION 到達可否を確認する。

## 絶対条件
- WordPress API call、draft作成、publish を実行しない。
- DRY_RUN、NO_GO、secret 非露出を維持する。
- service 名は必ず SERVICE_NAME_HERE を実値置換して全コマンドに明示する。
- user/group は必ず SERVICE_USER_HERE、SERVICE_GROUP_HERE を実値置換して使用する。

## 事前置換ルール
以下 3 つを最初に実値へ置換してから実行する。
- SERVICE_USER_HERE
- SERVICE_GROUP_HERE
- SERVICE_NAME_HERE

未置換のまま実行しない。

## 実行手順

1. 作業ディレクトリへ移動
```bash
cd /home/deploy/ai_media_os
```

2. 必須コマンド存在確認
```bash
command -v python3 >/dev/null
command -v sudo >/dev/null
command -v systemctl >/dev/null
```

3. credential ディレクトリ作成と権限設定
```bash
sudo install -d -m 0750 -o root -g SERVICE_GROUP_HERE /etc/ai-media-os
```

4. credential ファイル作成
```bash
sudo install -m 0640 -o root -g SERVICE_GROUP_HERE /dev/null /etc/ai-media-os/credential.env
```

5. credential 値投入
- 値を画面に表示しない。
- 以下は例。実値は端末で直接入力する。
```bash
sudo -u root tee /etc/ai-media-os/credential.env >/dev/null <<'EOF'
WORDPRESS_BASE_URL=SET_REAL_VALUE
WORDPRESS_USERNAME=SET_REAL_VALUE
WORDPRESS_APP_PASSWORD=SET_REAL_VALUE
SLACK_WEBHOOK_URL=SET_REAL_VALUE
EOF
```

6. 最終所有権とパーミッション固定
```bash
sudo chown SERVICE_USER_HERE:SERVICE_GROUP_HERE /etc/ai-media-os/credential.env
sudo chmod 0640 /etc/ai-media-os/credential.env
```

7. systemd drop-in を編集
```bash
sudo systemctl edit SERVICE_NAME_HERE
```
エディタ内に以下を記載して保存する。
```ini
[Service]
EnvironmentFile=/etc/ai-media-os/credential.env
```

8. systemd 再読込
```bash
sudo systemctl daemon-reload
```

9. 対象 service 再起動
```bash
sudo systemctl restart SERVICE_NAME_HERE
```

10. 稼働状態確認
```bash
sudo systemctl is-active SERVICE_NAME_HERE
sudo systemctl show SERVICE_NAME_HERE -p EnvironmentFiles --no-pager
```

11. secret 非露出の credential 読み込み検証
```bash
set -a
. /etc/ai-media-os/credential.env
set +a
python3 -c "
import os
keys = [
    'WORDPRESS_BASE_URL',
    'WORDPRESS_USERNAME',
    'WORDPRESS_APP_PASSWORD',
    'SLACK_WEBHOOK_URL',
]
for key in keys:
    value = os.environ.get(key, '')
    print(f'{key}: present={bool(value)} non_empty={len(value) > 0}')
"
unset WORDPRESS_BASE_URL WORDPRESS_USERNAME WORDPRESS_APP_PASSWORD SLACK_WEBHOOK_URL
```

12. Phase 8-29〜8-31 再実行
```bash
python3 scripts/generate_phase8_29_credential_readiness_recheck_no_secret_leak_gate_report.py
python3 scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py
python3 scripts/generate_phase8_30_final_operator_rerun_handoff_report.py
python3 scripts/generate_phase8_30_final_preflight_before_single_controlled_draft_creation_report.py
python3 scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py
python3 scripts/generate_phase8_31_human_execution_approval_validation_handoff_report.py
python3 scripts/validate_phase8_31_human_execution_approval_validation_handoff.py
python3 scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py
```

13. Phase 8-35 再実行
```bash
python3 scripts/generate_phase8_35_final_pre_execution_confirmation_report.py
python3 scripts/validate_phase8_35_final_pre_execution_confirmation.py
python3 scripts/generate_phase8_35_final_ready_blocked_rerun_decision.py
```

14. Phase 8-36〜8-40 再実行
```bash
python3 scripts/generate_phase8_36_one_shot_draft_creation_dry_run_handoff_report.py
python3 scripts/validate_phase8_36_one_shot_draft_creation_dry_run_handoff.py
python3 scripts/validate_phase8_37_credential_ready_revalidation.py
python3 scripts/generate_phase8_38_first_one_item_trial_preflight_report.py
python3 scripts/validate_phase8_38_first_one_item_trial_preflight.py
python3 scripts/generate_phase8_39_manual_rerun_command_bundle.py
python3 scripts/run_phase8_39_abort_rollback_freeze_simulation.py
python3 scripts/generate_phase8_40_post_rerun_branch_decision.py
python3 scripts/generate_phase8_36_to_8_40_trial_route_overall_report.py
```

15. 到達判定確認（python3 ヒアドキュメント）
```bash
python3 - <<'PY'
import glob
import json
import os

candidates = sorted(glob.glob('exchange/logs/phase8_36_to_8_40_trial_route_overall_report*.json'))
if not candidates:
    print('overall_report: MISSING')
    raise SystemExit(1)

latest = max(candidates, key=os.path.getmtime)
with open(latest, 'r', encoding='utf-8') as fh:
    data = json.load(fh)

status = data.get('overall_status')
expected = 'PHASE8_36_TO_8_40_TRIAL_ROUTE_READY_FOR_FIRST_ONE_ITEM_TRIAL_NO_EXECUTION'
print('overall_report:', latest)
print('overall_status:', status)
print('ready_reached:', status == expected)
PY
```

16. 禁止事項再確認
- WordPress API call をしていないこと。
- draft 作成・publish をしていないこと。
- secret 値をログや標準出力へ出していないこと。

## 完了条件
- credential.env が SERVICE_USER_HERE:SERVICE_GROUP_HERE / 0640 で配置済み。
- SERVICE_NAME_HERE が EnvironmentFile=/etc/ai-media-os/credential.env を参照。
- Phase 8-29〜8-31、8-35、8-36〜8-40 が再生成され、overall_status が期待値に一致。
- WordPress 実行系操作 0 件。
- secret 非露出。
