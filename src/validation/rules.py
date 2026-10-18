"""
Declarative Business Rules for Healthcare & Insurance Claim Processing.
"""

from __future__ import annotations
import re
from typing import Callable, List, Optional, Tuple, Union
from src.models.schemas import ClaimState, RuleResult, RuleSeverity, ExtractedEntities, PolicyCitation
from src.rag.retriever import PolicyKnowledgeRetriever

policy_retriever = PolicyKnowledgeRetriever()


class BusinessRule:
    """
    Declarative representation of a business rule.
    """
    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        severity: RuleSeverity,
        description: str,
        eval_fn: Callable[[ClaimState], Tuple[bool, str]]
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.severity = severity
        self.description = description
        self.eval_fn = eval_fn

    def evaluate(self, state: ClaimState) -> RuleResult:
        res = self.eval_fn(state)
        citations: List[PolicyCitation] = []
        if isinstance(res, tuple) and len(res) == 3:
            passed, failure_msg, citations = res
        else:
            passed, failure_msg = res

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=passed,
            severity=self.severity,
            message="Rule passed." if passed else failure_msg,
            citations=citations
        )


# --- Rule Evaluation Functions ---

def eval_policy_number_present_and_valid(state: ClaimState) -> Tuple[bool, str]:
    pol = state.extracted_entities.policy_number
    if not pol:
        return False, "Policy number is missing from claim submission."
    # Valid policy format is POL-XXXXXXX (e.g. POL-8829104)
    if not re.match(r'^POL-[A-Za-z0-9]{4,10}$', pol, re.IGNORECASE):
        return False, f"Policy number '{pol}' is invalid or does not match expected active policy format (POL-XXXXXXX)."
    return True, ""


def eval_claim_amount_numeric_and_positive(state: ClaimState) -> Tuple[bool, str]:
    amt = state.extracted_entities.claim_amount
    if amt is None:
        return False, "Claim amount is missing or could not be parsed."
    if amt <= 0:
        return False, f"Claim amount ${amt:,.2f} is non-positive or zero."
    return True, ""


def eval_claimant_name_present(state: ClaimState) -> Tuple[bool, str]:
    name = state.extracted_entities.claimant_name
    if not name or len(name.strip()) < 2:
        return False, "Claimant name is missing or incomplete."
    return True, ""


def eval_high_value_threshold(state: ClaimState) -> Tuple[bool, str]:
    amt = state.extracted_entities.claim_amount or 0.0
    THRESHOLD = 10000.00
    if amt > THRESHOLD:
        return False, f"Claim amount (${amt:,.2f}) exceeds the automated threshold limit of ${THRESHOLD:,.2f}. Escalating for mandatory caseworker sign-off."
    return True, ""


def eval_conflicting_or_ambiguous_data(state: ClaimState) -> Tuple[bool, str]:
    warnings = state.extraction_warnings
    confidence = state.extraction_confidence
    if warnings:
        warn_str = "; ".join(warnings)
        return False, f"Conflicting data or extraction ambiguity detected: {warn_str}."
    if confidence < 0.80:
        return False, f"Extraction confidence ({confidence*100:.0f}%) is below acceptable automated approval threshold (80%)."
    return True, ""


def eval_line_item_math_consistency(state: ClaimState) -> Tuple[bool, str]:
    line_items = state.extracted_entities.line_items
    total_amt = state.extracted_entities.claim_amount
    if not line_items or total_amt is None:
        return True, ""  # Skip math check if no itemized list available
    
    item_sum = sum(item.amount for item in line_items)
    if abs(item_sum - total_amt) > 1.00:  # Allow $1 rounding tolerance
        return False, f"Line item math mismatch: itemized sum (${item_sum:,.2f}) does not match total claimed amount (${total_amt:,.2f})."
    return True, ""


def eval_coverage_and_excluded_services(state: ClaimState) -> Tuple[bool, str, List[PolicyCitation]]:
    entities = state.extracted_entities
    diag = entities.diagnosis_code or ""
    proc = entities.procedure_code or ""

    is_excluded, citation = policy_retriever.check_exclusion(
        raw_text=state.raw_text,
        diagnosis_code=diag,
        procedure_code=proc
    )

    if is_excluded and citation:
        citations = [citation]
        state.policy_citations.extend(citations)
        return (
            False,
            f"Claim involves an excluded service category per {citation.document_name} (Page {citation.page_number}): {citation.section_title}.",
            citations
        )

    return True, "", []


# --- Default Ruleset Registry ---

DEFAULT_RULESET: List[BusinessRule] = [
    BusinessRule(
        rule_id="R101",
        rule_name="Policy Format & Active Status",
        severity=RuleSeverity.REJECT,
        description="Verifies policy number presence and active format (POL-XXXXXXX).",
        eval_fn=eval_policy_number_present_and_valid
    ),
    BusinessRule(
        rule_id="R102",
        rule_name="Valid Claim Amount",
        severity=RuleSeverity.REJECT,
        description="Verifies claim amount is present and greater than zero.",
        eval_fn=eval_claim_amount_numeric_and_positive
    ),
    BusinessRule(
        rule_id="R103",
        rule_name="Claimant Name Required",
        severity=RuleSeverity.REJECT,
        description="Verifies claimant name is present for decision letter generation.",
        eval_fn=eval_claimant_name_present
    ),
    BusinessRule(
        rule_id="R104",
        rule_name="Policy Handbook Coverage & Exclusion Verification (RAG)",
        severity=RuleSeverity.REJECT,
        description="Verifies non-covered categories and policy exclusions via RAG over policy handbooks.",
        eval_fn=eval_coverage_and_excluded_services
    ),
    BusinessRule(
        rule_id="R105",
        rule_name="High-Value Threshold Escalation (>$10,000)",
        severity=RuleSeverity.ESCALATE,
        description="Escalates claims exceeding $10,000 for caseworker sign-off.",
        eval_fn=eval_high_value_threshold
    ),
    BusinessRule(
        rule_id="R106",
        rule_name="Data Integrity & Conflict Detection",
        severity=RuleSeverity.ESCALATE,
        description="Escalates claims with extraction warnings, ambiguous values, or low confidence.",
        eval_fn=eval_conflicting_or_ambiguous_data
    ),
    BusinessRule(
        rule_id="R107",
        rule_name="Line Item Math Verification",
        severity=RuleSeverity.ESCALATE,
        description="Verifies itemized charges match total requested claim amount.",
        eval_fn=eval_line_item_math_consistency
    ),
]
