        # アフィリエイトブロックAI

        > **Auto-generated skeleton** — IR5-T4 dry-run 生成物。人間によるレビューが必要です。

        block_id: `affiliate_block`
        version: `0.1.0`
        category: `affiliate`
        risk_level: `medium`
        mode: `dry_run`
        operation_mode: `OBSERVE`

        ## 概要

        アフィリエイト商品の収集・スコアリング・レビューパッケージ生成を担当するブロックAI。

        ## Capabilities

        - collect_data: True
- analyze: True
- generate_report: True
- notify_slack: True
- publish_content: False
- delete_data: False
- change_config: False

        ## Forbidden Actions

        - delete_block
- export_block
- sell_block
- change_core_policy
- disable_audit
- auto_publish_without_approval
- handle_adult_content
- direct_purchase
- store_payment_info
- auto_place_order

        ## 安全ゲート

        - dry_run: 維持
        - OBSERVE: 維持
        - requires_human_approval: true
        - auto_execute_allowed: false
        - external_write_executed: false
