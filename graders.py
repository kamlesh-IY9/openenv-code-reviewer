"""
Deterministic graders for Code Reviewer Environment tasks.

This module provides explicit grader entry points so external validators can
discover and run grading logic without depending on the live HTTP API.
"""

from typing import Any, Dict

from models import CodeIssue
from tasks import TASKS


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    for char in "{}[](),.:;!?\n\t\r'\"`":
        lowered = lowered.replace(char, " ")
    return " ".join(lowered.split())


def _issue_keywords(issue: CodeIssue) -> list[str]:
    keywords: set[str] = {
        issue.issue_type.value,
        issue.issue_type.value.replace("_", " "),
        issue.severity.value,
        f"line {issue.line_number}",
    }

    for source_text in (issue.description, issue.suggested_fix or ""):
        for word in _normalize_text(source_text).split():
            if len(word) >= 4:
                keywords.add(word)

    return sorted(keywords)


def _answer_matches_issue(answer_text: str, issue: CodeIssue) -> bool:
    normalized = _normalize_text(answer_text)
    if not normalized:
        return False

    line_hit = any(
        marker in normalized
        for marker in (
            f"line {issue.line_number}",
            f"line_number {issue.line_number}",
            f"line:{issue.line_number}",
        )
    )
    type_hit = any(
        marker in normalized
        for marker in (
            issue.issue_type.value,
            issue.issue_type.value.replace("_", " "),
        )
    )
    fix_hit = bool(issue.suggested_fix) and _normalize_text(issue.suggested_fix) in normalized
    keyword_hits = sum(1 for keyword in _issue_keywords(issue) if keyword in normalized)

    return bool(
        (line_hit and (type_hit or keyword_hits >= 3 or fix_hit))
        or (type_hit and keyword_hits >= 4)
        or keyword_hits >= 5
        or fix_hit
    )


def grade_task(task_id: str, answer: str = "") -> Dict[str, Any]:
    """Grade a task answer and return a score in the 0.0-1.0 range."""
    if task_id not in TASKS:
        raise KeyError(f"Unknown task_id: {task_id}")

    task = TASKS[task_id]
    matched_lines = []
    for expected_issue in task.expected_issues:
        if _answer_matches_issue(answer, expected_issue):
            matched_lines.append(expected_issue.line_number)

    expected_count = len(task.expected_issues)
    matched_count = len(set(matched_lines))
    raw_score = min(matched_count / expected_count, 1.0) if expected_count > 0 else 1.0
    score = max(0.001, min(raw_score, 0.999))

    return {
        "task_id": task_id,
        "score": score,
        "success": score >= 0.7,
        "reward": score,
        "max_reward": 1.0,
        "matched_issues": matched_count,
        "expected_issues": expected_count,
    }


def grade_syntax_check(answer: str = "") -> Dict[str, Any]:
    return grade_task("syntax_check", answer)


def grade_logic_bug_detection(answer: str = "") -> Dict[str, Any]:
    return grade_task("logic_bug_detection", answer)


def grade_security_audit(answer: str = "") -> Dict[str, Any]:
    return grade_task("security_audit", answer)


def list_graders() -> Dict[str, str]:
    """Return explicit grader mappings for all tasks."""
    return {
        "syntax_check": "graders.grade_syntax_check",
        "logic_bug_detection": "graders.grade_logic_bug_detection",
        "security_audit": "graders.grade_security_audit",
    }
