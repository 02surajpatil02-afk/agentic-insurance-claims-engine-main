"""
Rules Engine Evaluator.
Executes the declarative ruleset against a ClaimState object.
"""

from __future__ import annotations
from typing import List
from src.models.schemas import ClaimState, RuleResult, AuditEntry, WorkflowStatus
from src.validation.rules import DEFAULT_RULESET, BusinessRule
from datetime import datetime, timezone


class RulesEngine:
    def __init__(self, rules: List[BusinessRule] = None):
        self.rules = rules or DEFAULT_RULESET

    def evaluate_all(self, state: ClaimState) -> List[RuleResult]:
        results: List[RuleResult] = []
        for rule in self.rules:
            result = rule.evaluate(state)
            results.append(result)
        return results


def process_validation_stage(state: ClaimState, engine: RulesEngine = None) -> ClaimState:
    """
    Executes the Validation stage on a ClaimState object.
    Appends audit log entry and updates state.
    """
    if engine is None:
        engine = RulesEngine()

    results = engine.evaluate_all(state)
    state.validation_results = results
    state.status = WorkflowStatus.PENDING_VALIDATION

    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count
    
    reject_triggers = [r for r in results if not r.passed and r.severity == "reject"]
    escalate_triggers = [r for r in results if not r.passed and r.severity == "escalate"]

    summary = f"Evaluated {len(results)} rules: {passed_count} passed, {failed_count} triggered ({len(reject_triggers)} REJECT, {len(escalate_triggers)} ESCALATE)"

    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="VALIDATION",
        summary=summary,
        metadata={
            "passed_rules": passed_count,
            "reject_rules_triggered": [r.rule_id for r in reject_triggers],
            "escalate_rules_triggered": [r.rule_id for r in escalate_triggers],
            "policy_citations_count": len(state.policy_citations)
        }
    ))
    return state
