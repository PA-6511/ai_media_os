# Low Token Dev Mode

Auto Builder Block AI Level 5 is limited to design-only and dry-run-only development support.

## Guarantees

- production_status is fixed to NO_GO.
- execution_mode is fixed to DRY_RUN_ONLY.
- credential access, external API calls, WordPress writes, and systemd changes stay disabled.
- generated prompts stay inside the listed file scope.

## Components

- LOW_TOKEN_DEV_MODE policy JSON
- Copilot prompt generator
- Codex preprocessor
- Phase dev pack generator
- Level5 status report generator

## Intended Use

Use the generated dev pack artifacts only for low-token development phases that remain inside the allowed files and validation commands.