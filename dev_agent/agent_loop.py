#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from dev_agent.command_bridge import REPO_ROOT, run_command
from dev_agent.file_bridge import read_repo_text
from dev_agent.proposal_bridge import (
    claim_proposal_execution,
    create_write_proposal,
    load_write_proposal,
    mark_proposal_approved,
    mark_proposal_executed,
    verify_write_contract_source,
)
from dev_agent.write_bridge import (
    CANARY_WRITE_FILES,
    PROBE_ROOT,
    replace_approved_text,
    replace_probe_text,
)


MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")

MAX_TOOL_ROUNDS = 8
COMMAND_TIMEOUT = 60


INSTRUCTIONS = """
You are the minimal AI Media OS development command agent.

Your working repository is:
/home/deploy/ai_media_os

You have five external tools:
- run_command
- read_file
- create_write_proposal
- replace_text
- get_write_audit

Rules:
- Use tools only when required.
- Tool bridges are the final authority.
- Never try to bypass a DENIED result.
- Never request sudo.
- Never request credentials, secrets, tokens, passwords,
  or credential files.
- Never use destructive git operations.
- Never use rm, systemctl, package management,
  network tools, or shell chaining.
- Prefer narrowly scoped commands.
- Do not inspect the entire repository unless explicitly requested.
- create_write_proposal only records a proposed exact replacement.
- create_write_proposal must never modify the proposed source file.
- A proposal is not write approval.
- replace_text may only be used where its bridge permits it.
- Normal prototype writes are limited to dev_agent/probes/.
- Prototype 4B permits exactly these bridge canary files:
  app/services/ebook_new_release_autonomy_shadow_compare.py
  tests/services/test_ebook_new_release_autonomy_shadow_compare.py
- Each file still requires its own exact human --allow-write-file approval.
- Approval of one file never implies approval of another file.
- Never weaken, delete, skip, or bypass a test merely to make pytest pass.
- When an exact replacement contract is supplied, old_text and new_text
  must match that contract byte-for-byte at the tool argument level.
- Never substitute a semantically equivalent expression for contracted new_text.
- Never modify any other app/, core/, scripts/, systemd/, config/, DB files,
  credentials, or other production code.
- read_file accepts at most 400 requested lines.
- Never request more than 400 lines in one read_file call.
- Use the minimum number of tool calls.
- When finished, report exactly what was executed and changed.
"""


TOOLS = [
    {
        "type": "function",
        "name": "run_command",
        "description": (
            "Execute one restricted command inside "
            "/home/deploy/ai_media_os."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": (
            "Read a bounded line range from one text file "
            "inside /home/deploy/ai_media_os."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                },
                "start_line": {
                    "type": "integer",
                },
                "end_line": {
                    "type": "integer",
                },
            },
            "required": [
                "relative_path",
                "start_line",
                "end_line",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "replace_text",
        "description": (
            "Replace exactly one occurrence of text in an "
            "existing Python probe file. The write bridge "
            "allows writes only inside dev_agent/probes/."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                },
                "old_text": {
                    "type": "string",
                },
                "new_text": {
                    "type": "string",
                },
            },
            "required": [
                "relative_path",
                "old_text",
                "new_text",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "create_write_proposal",
        "description": (
            "Create an immutable proposal JSON for one exact "
            "source replacement. This does not modify the source file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                },
                "old_text": {
                    "type": "string",
                },
                "new_text": {
                    "type": "string",
                },
            },
            "required": [
                "relative_path",
                "old_text",
                "new_text",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_write_audit",
        "description": (
            "Return the write audit for the current agent session. "
            "Shows approved files, write attempts, executed writes, "
            "and unexpected executed writes."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def validate_agent_write_target(relative_path: str):
    raw_path = Path(relative_path)

    if raw_path.is_absolute():
        return {
            "status": "DENIED",
            "reason": "ABSOLUTE_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    if ".." in raw_path.parts:
        return {
            "status": "DENIED",
            "reason": "PARENT_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    resolved = (REPO_ROOT / raw_path).resolve()

    normalized_path = raw_path.as_posix()

    if normalized_path in CANARY_WRITE_FILES:
        if resolved.suffix != ".py":
            return {
                "status": "DENIED",
                "reason": "ONLY_PYTHON_FILES_ALLOWED",
                "path": relative_path,
            }
        return None

    try:
        resolved.relative_to(PROBE_ROOT)
    except ValueError:
        return {
            "status": "DENIED",
            "reason": "WRITE_OUTSIDE_PROBE_ROOT",
            "path": relative_path,
        }

    if resolved.suffix != ".py":
        return {
            "status": "DENIED",
            "reason": "ONLY_PYTHON_FILES_ALLOWED",
            "path": relative_path,
        }

    return None


def build_write_audit_report(
    approved_write_files,
    write_audit,
):
    approved = sorted(set(approved_write_files))

    executed = sorted({
        event["path"]
        for event in write_audit
        if event.get("status") == "EXECUTED"
    })

    unexpected = sorted(
        set(executed) - set(approved)
    )

    return {
        "status": "EXECUTED",
        "approved_write_files": approved,
        "write_attempts": list(write_audit),
        "executed_write_files": executed,
        "unexpected_executed_write_files": unexpected,
        "result": "PASS" if not unexpected else "FAIL",
    }


def dispatch_tool(
    name: str,
    arguments: dict,
    approved_write_files=None,
    write_audit=None,
    write_contract=None,
) -> dict:
    if approved_write_files is None:
        approved_write_files = set()

    if write_audit is None:
        write_audit = []
    if name == "run_command":
        command = arguments.get("command")

        if not isinstance(command, str):
            return {
                "status": "ERROR",
                "reason": "COMMAND_MUST_BE_STRING",
            }

        return run_command(
            command=command,
            cwd=str(REPO_ROOT),
            timeout=COMMAND_TIMEOUT,
        )

    if name == "read_file":
        relative_path = arguments.get("relative_path")
        start_line = arguments.get("start_line")
        end_line = arguments.get("end_line")

        if not isinstance(relative_path, str):
            return {
                "status": "ERROR",
                "reason": "PATH_MUST_BE_STRING",
            }

        if not isinstance(start_line, int):
            return {
                "status": "ERROR",
                "reason": "START_LINE_MUST_BE_INTEGER",
            }

        if not isinstance(end_line, int):
            return {
                "status": "ERROR",
                "reason": "END_LINE_MUST_BE_INTEGER",
            }

        return read_repo_text(
            relative_path=relative_path,
            start_line=start_line,
            end_line=end_line,
        )

    if name == "create_write_proposal":
        relative_path = arguments.get("relative_path")
        old_text = arguments.get("old_text")
        new_text = arguments.get("new_text")

        if not isinstance(relative_path, str):
            return {
                "status": "ERROR",
                "reason": "PATH_MUST_BE_STRING",
            }

        if not isinstance(old_text, str):
            return {
                "status": "ERROR",
                "reason": "OLD_TEXT_MUST_BE_STRING",
            }

        if not isinstance(new_text, str):
            return {
                "status": "ERROR",
                "reason": "NEW_TEXT_MUST_BE_STRING",
            }

        return create_write_proposal(
            relative_path=relative_path,
            old_text=old_text,
            new_text=new_text,
        )

    if name == "replace_text":
        relative_path = arguments.get("relative_path")
        old_text = arguments.get("old_text")
        new_text = arguments.get("new_text")

        if not isinstance(relative_path, str):
            return {
                "status": "ERROR",
                "reason": "PATH_MUST_BE_STRING",
            }

        if not isinstance(old_text, str):
            return {
                "status": "ERROR",
                "reason": "OLD_TEXT_MUST_BE_STRING",
            }

        if not isinstance(new_text, str):
            return {
                "status": "ERROR",
                "reason": "NEW_TEXT_MUST_BE_STRING",
            }

        normalized_path = Path(relative_path).as_posix()

        target_error = validate_agent_write_target(
            relative_path
        )

        if target_error is not None:
            write_audit.append({
                "path": normalized_path,
                "status": target_error["status"],
                "reason": target_error.get("reason"),
            })
            return target_error

        if write_contract is not None:
            contract_path = write_contract["relative_path"]

            if normalized_path != contract_path:
                result = {
                    "status": "DENIED",
                    "reason": "EXACT_PATH_MISMATCH",
                    "path": relative_path,
                    "contract_path": contract_path,
                }

                write_audit.append({
                    "path": normalized_path,
                    "status": result["status"],
                    "reason": result["reason"],
                })

                return result

            if normalized_path == contract_path:
                if old_text != write_contract["old_text"]:
                    result = {
                        "status": "DENIED",
                        "reason": "EXACT_OLD_TEXT_MISMATCH",
                        "path": relative_path,
                    }

                    write_audit.append({
                        "path": normalized_path,
                        "status": result["status"],
                        "reason": result["reason"],
                    })

                    return result

                if new_text != write_contract["new_text"]:
                    result = {
                        "status": "DENIED",
                        "reason": "EXACT_NEW_TEXT_MISMATCH",
                        "path": relative_path,
                    }

                    write_audit.append({
                        "path": normalized_path,
                        "status": result["status"],
                        "reason": result["reason"],
                    })

                    return result

        if normalized_path not in approved_write_files:
            result = {
                "status": "APPROVAL_REQUIRED",
                "reason": "FILE_WRITE_APPROVAL_REQUIRED",
                "path": relative_path,
            }

            write_audit.append({
                "path": normalized_path,
                "status": result["status"],
                "reason": result["reason"],
            })

            return result

        if (
            write_contract is not None
            and write_contract.get("before_sha256") is not None
        ):
            source_check = verify_write_contract_source(
                relative_path=normalized_path,
                expected_sha256=write_contract["before_sha256"],
            )

            if source_check["status"] != "VALID":
                write_audit.append({
                    "path": normalized_path,
                    "status": source_check["status"],
                    "reason": source_check.get("reason"),
                    "expected_sha256": (
                        source_check.get("expected_sha256")
                    ),
                    "current_sha256": (
                        source_check.get("current_sha256")
                    ),
                })

                return source_check

        proposal_id = None

        if write_contract is not None:
            proposal_id = write_contract.get(
                "proposal_id"
            )

        if proposal_id is not None:
            claim_result = claim_proposal_execution(
                proposal_id
            )

            if claim_result["status"] != "VALID":
                write_audit.append({
                    "path": normalized_path,
                    "status": claim_result["status"],
                    "reason": claim_result.get("reason"),
                })

                return claim_result

        if normalized_path in CANARY_WRITE_FILES:
            result = replace_approved_text(
                relative_path=relative_path,
                old_text=old_text,
                new_text=new_text,
                bridge_allowed_files=CANARY_WRITE_FILES,
            )
        else:
            result = replace_probe_text(
                relative_path=relative_path,
                old_text=old_text,
                new_text=new_text,
            )

        if (
            proposal_id is not None
            and result.get("status") == "EXECUTED"
        ):
            execution_state = (
                mark_proposal_executed(
                    proposal_id
                )
            )

            if execution_state["status"] != "VALID":
                write_audit.append({
                    "path": normalized_path,
                    "status": "ERROR",
                    "reason": (
                        "PROPOSAL_EXECUTION_STATE_PERSIST_FAILED"
                    ),
                    "before_sha256": result.get(
                        "before_sha256"
                    ),
                    "after_sha256": result.get(
                        "after_sha256"
                    ),
                })

                return {
                    "status": "ERROR",
                    "reason": (
                        "PROPOSAL_EXECUTION_STATE_PERSIST_FAILED"
                    ),
                    "proposal_id": proposal_id,
                    "write_result": result,
                    "state_result": execution_state,
                }

            result = {
                **result,
                "proposal_id": proposal_id,
                "proposal_state": "EXECUTED",
            }

        write_audit.append({
            "path": normalized_path,
            "status": result.get("status"),
            "reason": result.get("reason"),
            "before_sha256": result.get("before_sha256"),
            "after_sha256": result.get("after_sha256"),
        })

        return result

    if name == "get_write_audit":
        return build_write_audit_report(
            approved_write_files=approved_write_files,
            write_audit=write_audit,
        )

    return {
        "status": "ERROR",
        "reason": f"UNKNOWN_TOOL:{name}",
    }


def run_agent(
    prompt: str,
    approved_write_files=None,
    write_contract=None,
) -> str:
    if approved_write_files is None:
        approved_write_files = set()
    write_audit = []

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set."
        )

    client = OpenAI()

    input_items = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    for round_number in range(
        1,
        MAX_TOOL_ROUNDS + 1,
    ):
        response = client.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=input_items,
            tools=TOOLS,
            store=False,
            include=["reasoning.encrypted_content"],
        )

        input_items += response.output

        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text or "(no final text)"

        for tool_call in tool_calls:
            parsed_arguments = None

            try:
                parsed_arguments = json.loads(
                    tool_call.arguments
                )
            except json.JSONDecodeError as exc:
                result = {
                    "status": "ERROR",
                    "reason": (
                        f"INVALID_TOOL_ARGUMENTS:{exc}"
                    ),
                }
            else:
                result = dispatch_tool(
                    tool_call.name,
                    parsed_arguments,
                    approved_write_files=approved_write_files,
                    write_audit=write_audit,
                    write_contract=write_contract,
                )

            print(
                json.dumps(
                    {
                        "round": round_number,
                        "tool": tool_call.name,
                        "arguments": (
                            parsed_arguments
                            if parsed_arguments is not None
                            else {}
                        ),
                        "result": result,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )

            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                }
            )

    return (
        "STOPPED: MAX_TOOL_ROUNDS_REACHED "
        f"({MAX_TOOL_ROUNDS})"
    )


def main():
    parser = argparse.ArgumentParser(
        description="AI Media OS minimal OpenAI command agent"
    )

    parser.add_argument(
        "--approve-proposal-id",
        default=None,
        metavar="PROPOSAL_ID",
        help=(
            "Human approval for one persisted proposal ID. "
            "The proposal supplies the exact path/old/new contract."
        ),
    )

    parser.add_argument(
        "--execute-approved-proposal-id",
        default=None,
        metavar="PROPOSAL_ID",
        help=(
            "Execute one persisted proposal that is already APPROVED. "
            "This option never approves a PENDING proposal."
        ),
    )

    parser.add_argument(
        "--allow-write-file",
        action="append",
        default=[],
        metavar="RELATIVE_PATH",
        help=(
            "Explicit human approval for one exact repository-relative "
            "file. May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--required-write-path",
        default=None,
        help="Exact file path for the replacement contract.",
    )

    parser.add_argument(
        "--required-old-text",
        default=None,
        help="Exact old text required by the replacement contract.",
    )

    parser.add_argument(
        "--required-new-text",
        default=None,
        help="Exact new text required by the replacement contract.",
    )

    parser.add_argument(
        "prompt",
        help="Task instruction for the agent",
    )

    args = parser.parse_args()

    contract_values = (
        args.required_write_path,
        args.required_old_text,
        args.required_new_text,
    )

    if (
        args.approve_proposal_id is not None
        and args.execute_approved_proposal_id is not None
    ):
        parser.error(
            "--approve-proposal-id cannot be combined with "
            "--execute-approved-proposal-id"
        )

    if (
        args.execute_approved_proposal_id is not None
        and (
            any(value is not None for value in contract_values)
            or args.allow_write_file
        )
    ):
        parser.error(
            "--execute-approved-proposal-id cannot be combined with "
            "--allow-write-file or --required-write-path/"
            "--required-old-text/--required-new-text"
        )

    if (
        args.approve_proposal_id is not None
        and any(value is not None for value in contract_values)
    ):
        parser.error(
            "--approve-proposal-id cannot be combined with "
            "--required-write-path/--required-old-text/"
            "--required-new-text"
        )

    if (
        args.approve_proposal_id is not None
        and args.allow_write_file
    ):
        parser.error(
            "--approve-proposal-id cannot be combined with "
            "--allow-write-file"
        )

    approved_write_files = {
        Path(item).as_posix()
        for item in args.allow_write_file
    }

    if args.approve_proposal_id is not None:
        proposal_result = load_write_proposal(
            args.approve_proposal_id
        )

        print(
            "=== PROPOSAL APPROVAL PREFLIGHT ==="
        )
        print(
            json.dumps(
                proposal_result,
                ensure_ascii=False,
                indent=2,
            )
        )

        if proposal_result["status"] != "VALID":
            raise SystemExit(2)

        approval_state = mark_proposal_approved(
            proposal_result["proposal_id"]
        )

        print(
            "=== PROPOSAL STATE ==="
        )
        print(
            json.dumps(
                approval_state,
                ensure_ascii=False,
                indent=2,
            )
        )

        if approval_state["status"] != "VALID":
            raise SystemExit(2)

        approved_write_files = {
            proposal_result["relative_path"]
        }

        write_contract = {
            "relative_path": (
                proposal_result["relative_path"]
            ),
            "old_text": proposal_result["old_text"],
            "new_text": proposal_result["new_text"],
            "before_sha256": (
                proposal_result["before_sha256"]
            ),
            "proposal_id": (
                proposal_result["proposal_id"]
            ),
        }

    elif args.execute_approved_proposal_id is not None:
        proposal_result = load_write_proposal(
            args.execute_approved_proposal_id
        )

        print(
            "=== APPROVED PROPOSAL EXECUTION PREFLIGHT ==="
        )
        print(
            json.dumps(
                proposal_result,
                ensure_ascii=False,
                indent=2,
            )
        )

        if proposal_result["status"] != "VALID":
            raise SystemExit(2)

        if (
            proposal_result.get("proposal_state")
            != "APPROVED"
        ):
            denial = {
                "status": "DENIED",
                "reason": (
                    "PROPOSAL_NOT_APPROVED_FOR_EXECUTION"
                ),
                "proposal_id": proposal_result[
                    "proposal_id"
                ],
                "proposal_state": proposal_result.get(
                    "proposal_state"
                ),
            }

            print(
                "=== PROPOSAL EXECUTION DENIED ==="
            )
            print(
                json.dumps(
                    denial,
                    ensure_ascii=False,
                    indent=2,
                )
            )

            raise SystemExit(2)

        approved_write_files = {
            proposal_result["relative_path"]
        }

        write_contract = {
            "relative_path": (
                proposal_result["relative_path"]
            ),
            "old_text": proposal_result["old_text"],
            "new_text": proposal_result["new_text"],
            "before_sha256": (
                proposal_result["before_sha256"]
            ),
            "proposal_id": (
                proposal_result["proposal_id"]
            ),
        }

    elif any(
        value is not None
        for value in contract_values
    ):
        if not all(
            value is not None
            for value in contract_values
        ):
            parser.error(
                "--required-write-path, --required-old-text, and "
                "--required-new-text must be supplied together"
            )

        write_contract = {
            "relative_path": Path(
                args.required_write_path
            ).as_posix(),
            "old_text": args.required_old_text,
            "new_text": args.required_new_text,
        }

    else:
        write_contract = None

    try:
        final_text = run_agent(
            args.prompt,
            approved_write_files=approved_write_files,
            write_contract=write_contract,
        )
    except Exception as exc:
        print(
            f"AGENT_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("\n=== AGENT FINAL ===")
    print(final_text)


if __name__ == "__main__":
    main()
