from __future__ import annotations

from typing import Any, Dict, List


def summarize_issue_sources(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    def _is_ai_issue(issue: Dict[str, Any]) -> bool:
        source = str(issue.get("source") or "").strip().lower()
        if source == "ai":
            return True
        if issue.get("auto_generated"):
            return True
        if str(issue.get("ruleset_domain") or "").strip().lower() == "icc.lcopilot.ai_validation":
            return True
        return False

    def _normalize_severity(value: Any) -> str:
        token = str(value or "").strip().lower()
        if token in {"warning", "warn"}:
            return "minor"
        if token in {"info", "informational"}:
            return "info"
        if token in {"minor", "major", "critical"}:
            return token
        return "minor" if token else "minor"

    def _count(issues_subset: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
        for issue in issues_subset:
            severity = _normalize_severity(issue.get("severity"))
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _rules_fired(issues_subset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        fired: List[Dict[str, Any]] = []
        for issue in issues_subset:
            rule = issue.get("rule") or issue.get("code") or issue.get("title")
            if not rule:
                continue
            key = (rule, issue.get("ruleset_domain"), issue.get("severity"))
            if key in seen:
                continue
            seen.add(key)
            fired.append({
                "rule": rule,
                "title": issue.get("title"),
                "severity": _normalize_severity(issue.get("severity")),
                "ruleset_domain": issue.get("ruleset_domain"),
                "source": issue.get("source") or ("ai" if _is_ai_issue(issue) else "deterministic"),
            })
        return fired

    deterministic_issues: List[Dict[str, Any]] = []
    ai_issues: List[Dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        if _is_ai_issue(issue):
            ai_issues.append(issue)
        else:
            deterministic_issues.append(issue)

    deterministic_counts = _count(deterministic_issues)
    ai_counts = _count(ai_issues)
    deterministic_verdict = "reject" if deterministic_counts.get("critical", 0) > 0 else (
        "review" if deterministic_counts.get("major", 0) > 0 else "pass"
    )

    return {
        "deterministic": {
            "issues": deterministic_issues,
            "counts": deterministic_counts,
            "verdict": deterministic_verdict,
            "rules_fired": _rules_fired(deterministic_issues),
        },
        "ai": {
            "issues": ai_issues,
            "counts": ai_counts,
            "rules_fired": _rules_fired(ai_issues),
        },
    }
