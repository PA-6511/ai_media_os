# Phase 1W valid_until deprecation note

valid_until は実行可否の主ゲートとして使用しない。
代替ゲートは IMMEDIATE_PRE_WRITE_GET_MATCH を採用する。

今回の実行では、true承認ファイル参照の pre-live snapshot/result が存在しなかったため、
WordPress write を実行せずに安全停止した。

本ノートの結論:
- valid_until_deprecated: true
- valid_until_used_as_execution_gate: false
- replacement_gate: IMMEDIATE_PRE_WRITE_GET_MATCH