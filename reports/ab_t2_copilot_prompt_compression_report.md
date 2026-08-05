# AB-T2 Copilot Prompt Compression Report

- phase: AB-T2
- final_status: PASS_DESIGN_ONLY_NO_EXECUTION
- execution_mode: DESIGN_ONLY
- production_status: NO_GO
- safety_state: DRY_RUN_ONLY
- max_files_per_ai_context: 5
- max_lines_per_file_excerpt: 120
- generated_prompt_template_exists: True
- forbidden_operations_all_blocked: True
- ready_for_ab_t3: True

## Next Phase
- phase: AB-T3
- name: Related File Selector
- execution_allowed: False

## Prompt Template
```text
---
Task:
Implement only the smallest safe design-only patch for the requested phase.

Context Budget:
- Max files: 5
- Max lines per file excerpt: 120

Safety Constraints:
- DRY_RUN only
- NO_GO production status
- No WordPress write
- No credential read/output
- No external API call
- No destructive operation

Relevant Files:
- config/auto_builder_copilot_prompt_compression_policy.json
- scripts/build_auto_builder_copilot_prompt_compression.py
- tests/test_build_auto_builder_copilot_prompt_compression.py
- scripts/validate_auto_builder_token_efficiency_policy.py
- scripts/validate_auto_builder_token_budget_and_snapshot_digest.py

Instructions:
- Use minimal diff only
- Do not refactor unrelated code
- Do not modify production execution gates
- Do not read or output secrets
- Return patch proposal only
- Include limited pytest command suggestion

Expected Output:
- Changed files
- Patch summary
- Safety confirmation
- Suggested limited tests
---
```

## Errors
- none
