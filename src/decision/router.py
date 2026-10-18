"""
Decision Router Stage.
Evaluates validation results to route claims to auto-approval, auto-rejection,
or HITL exception review escalation.
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from src.models.schemas import (
    ClaimState,
    WorkflowStatus,
    DecisionOutcome,
    DecisionPath,
    RuleSeverity,
    HITLExceptionSummary,
    AuditEntry,
    RuleResult,
)
from datetime import datetime, timezone


class DecisionRouter:
    """
    Pure decision routing engine based on evaluation rule severity.
    """

    def route(self, state: ClaimState) -> Tuple[WorkflowStatus, Optional[DecisionOutcome], Optional[DecisionPath]]:
        results = state.validation_results
        
        reject_triggers = [r for r in results if not r.passed and r.severity == RuleSeverity.REJECT]
        escalate_triggers = [r for r in results if not r.passed and r.severity == RuleSeverity.ESCALATE]

        if reject_triggers:
            # Auto-reject due to hard policy failure
            return WorkflowStatus.AUTO_DECIDED, DecisionOutcome.REJECTED, DecisionPath.AUTO

        if escalate_triggers:
            # Halt workflow for Human-in-the-Loop review
            return WorkflowStatus.PENDING_HUMAN_REVIEW, None, None

        # Clean pass -> Auto-approve
        return WorkflowStatus.AUTO_DECIDED, DecisionOutcome.APPROVED, DecisionPath.AUTO


def generate_exception_summary(state: ClaimState) -> HITLExceptionSummary:
    """
    Generates a caseworker-facing exception review summary when claim halts.
    """
    escalate_rules = [r for r in state.validation_results if not r.passed and r.severity == RuleSeverity.ESCALATE]
    
    # Calculate risk score (0.0 - 1.0)
    risk_score = 0.3
    amt = state.extracted_entities.claim_amount or 0
    if amt > 10000:
        risk_score += 0.3
    if amt > 30000:
        risk_score += 0.2
    if state.extraction_warnings:
        risk_score += 0.2
    risk_score = min(1.0, round(risk_score, 2))

    # Suggested actions based on trigger type and extraction warnings
    actions = []
    for rule in escalate_rules:
        if rule.rule_id == "R105":  # High value
            actions.append(f"Perform senior clinical audit for claim amount (${amt:,.2f} > $10,000 threshold)")
        elif rule.rule_id == "R106":  # Data conflict / Ambiguity
            if state.extraction_warnings:
                for w in state.extraction_warnings:
                    w_lower = w.lower()
                    if "policy" in w_lower:
                        actions.append("Verify active policy ID with underwriting (Multiple policy references detected)")
                    elif "name" in w_lower or "patient" in w_lower:
                        actions.append("Verify patient identity / claimant name variance across document pages")
                    elif "amount" in w_lower or "total" in w_lower:
                        actions.append("Clarify conflicting claim totals with provider billing department")
                    else:
                        actions.append(f"Clarify extraction ambiguity: {w}")
            else:
                actions.append("Contact provider / billing department to clarify conflicting data points")
        elif rule.rule_id == "R107":  # Line item mismatch
            actions.append("Re-examine itemized medical bill schedule against claim total")
        else:
            actions.append(f"Review flagged rule: {rule.rule_name}")

    suggested_action = " | ".join(actions) if actions else "Review claim file and verify coverage details with underwriting."

    return HITLExceptionSummary(
        claim_id=state.claim_id,
        extracted_entities=state.extracted_entities,
        triggered_rules=escalate_rules,
        extraction_warnings=state.extraction_warnings,
        risk_score=risk_score,
        suggested_action=suggested_action
    )


def process_decision_stage(state: ClaimState) -> ClaimState:
    """
    Executes the Decision Router stage on a ClaimState object.
    Appends audit log entry and halts if HITL review is required.
    """
    router = DecisionRouter()
    status, outcome, path = router.route(state)

    state.status = status
    state.decision = outcome
    state.decision_path = path
    state.updated_at = datetime.now(timezone.utc).isoformat()

    if status == WorkflowStatus.PENDING_HUMAN_REVIEW:
        exception_summary = generate_exception_summary(state)
        state.exception_summary = exception_summary
        
        summary_msg = f"WORKFLOW HALTED: Triggered {len(exception_summary.triggered_rules)} escalation rule(s). Generated Exception Summary for caseworker review (Risk Score: {exception_summary.risk_score})."
        state.audit_trail.append(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="DECISION_ROUTER",
            summary=summary_msg,
            metadata={
                "halted_for_hitl": True,
                "triggered_rules": [r.rule_id for r in exception_summary.triggered_rules],
                "risk_score": exception_summary.risk_score
            }
        ))
    else:
        summary_msg = f"Auto-Decided outcome: {outcome.value.upper()} (Path: {path.value.upper()})"
        state.audit_trail.append(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="DECISION_ROUTER",
            summary=summary_msg,
            metadata={
                "halted_for_hitl": False,
                "outcome": outcome.value,
                "path": path.value
            }
        ))

    return state
