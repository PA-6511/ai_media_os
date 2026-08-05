from __future__ import annotations


def _extract_evidence(stdout: str, stderr: str, markers: list[str]) -> str:
    combined = "\n".join([stdout or "", stderr or ""]).splitlines()
    for line in combined:
        for marker in markers:
            if marker.lower() in line.lower():
                return line.strip()
    return ""


def triage_failure(stdout: str, stderr: str, returncode: int) -> dict:
    """Classify verification results into a small, explicit set of categories."""
    stdout = stdout or ""
    stderr = stderr or ""
    merged = f"{stdout}\n{stderr}".lower()

    if returncode == 0:
        return {
            "category": "PASS",
            "confidence": 0.99,
            "key_evidence": "verify command returned 0",
            "suggested_next_action": "Proceed to reporting.",
        }

    if "policy_violation" in merged or "allowlist" in merged:
        evidence = _extract_evidence(stdout, stderr, ["POLICY_VIOLATION", "allowlist"])
        return {
            "category": "POLICY_VIOLATION",
            "confidence": 0.95,
            "key_evidence": evidence or "policy guardrail marker detected",
            "suggested_next_action": "Restrict updates to allowlist scope and retry.",
        }

    if "timeout" in merged or "timed out" in merged:
        evidence = _extract_evidence(stdout, stderr, ["timeout", "timed out"])
        return {
            "category": "TIMEOUT",
            "confidence": 0.9,
            "key_evidence": evidence or "timeout marker detected",
            "suggested_next_action": "Increase timeout or optimize failing step.",
        }

    if "importerror" in merged or "modulenotfounderror" in merged:
        evidence = _extract_evidence(stdout, stderr, ["ImportError", "ModuleNotFoundError"])
        return {
            "category": "IMPORT_ERROR",
            "confidence": 0.97,
            "key_evidence": evidence or "import failure detected",
            "suggested_next_action": "Fix imports/dependencies, then rerun tests.",
        }

    if "syntaxerror" in merged:
        evidence = _extract_evidence(stdout, stderr, ["SyntaxError"])
        return {
            "category": "SYNTAX_ERROR",
            "confidence": 0.97,
            "key_evidence": evidence or "syntax failure detected",
            "suggested_next_action": "Fix syntax issue and rerun tests.",
        }

    if "assertionerror" in merged or "assert " in merged or " failed" in merged:
        evidence = _extract_evidence(stdout, stderr, ["AssertionError", "assert", "FAILED"])
        return {
            "category": "TEST_ASSERTION_FAILED",
            "confidence": 0.86,
            "key_evidence": evidence or "assertion-related failure detected",
            "suggested_next_action": "Inspect failing assertion and update code or test.",
        }

    return {
        "category": "UNKNOWN",
        "confidence": 0.5,
        "key_evidence": "no known marker matched",
        "suggested_next_action": "Inspect stdout/stderr and classify manually.",
    }
