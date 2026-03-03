from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import importlib.util


def _load_deterministic_gate():
    module_path = API_ROOT / "app" / "services" / "validation" / "deterministic_gate.py"
    spec = importlib.util.spec_from_file_location("deterministic_gate", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec and spec.loader:
        spec.loader.exec_module(module)
    return module


deterministic_gate = _load_deterministic_gate()

summarize_issue_sources = deterministic_gate.summarize_issue_sources


def _issue(rule: str, severity: str, source: str, ruleset_domain: str) -> dict:
    return {
        "rule": rule,
        "title": rule,
        "severity": severity,
        "source": source,
        "ruleset_domain": ruleset_domain,
        "auto_generated": source == "ai",
    }


def test_deterministic_critical_hit_blocks_submission():
    issues = [
        _issue("SANCTIONS-1", "critical", "deterministic", "sanctions.screening"),
        _issue("AI-NOTE", "major", "ai", "icc.lcopilot.ai_validation"),
    ]
    summary = summarize_issue_sources(issues)
    assert summary["deterministic"]["counts"]["critical"] == 1
    assert summary["deterministic"]["verdict"] == "reject"


def test_deterministic_major_hit_requires_review():
    issues = [
        _issue("TBML-2", "major", "deterministic", "aml.tbml"),
    ]
    summary = summarize_issue_sources(issues)
    assert summary["deterministic"]["counts"]["major"] == 1
    assert summary["deterministic"]["verdict"] == "review"


def test_deterministic_minor_only_does_not_block():
    issues = [
        _issue("SHELL-3", "minor", "deterministic", "aml.shell_risk"),
    ]
    summary = summarize_issue_sources(issues)
    assert summary["deterministic"]["counts"]["minor"] == 1
    assert summary["deterministic"]["verdict"] == "pass"


def test_ai_findings_do_not_override_deterministic_block():
    issues = [
        _issue("SANCTIONS-2", "critical", "deterministic", "sanctions.screening"),
        _issue("AI-CRITICAL", "critical", "ai", "icc.lcopilot.ai_validation"),
    ]
    summary = summarize_issue_sources(issues)
    assert summary["deterministic"]["verdict"] == "reject"
    assert summary["ai"]["counts"]["critical"] == 1
