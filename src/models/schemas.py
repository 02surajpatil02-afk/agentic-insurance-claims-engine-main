"""
Pydantic schemas and state object definitions for the Claims Review Workflow.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class RuleSeverity(str, Enum):
    REJECT = "reject"
    ESCALATE = "escalate"
    WARN = "warn"


class WorkflowStatus(str, Enum):
    PENDING_EXTRACTION = "pending_extraction"
    PENDING_VALIDATION = "pending_validation"
    AUTO_DECIDED = "auto_decided"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    RESOLVED_APPROVED = "resolved_approved"
    RESOLVED_REJECTED = "resolved_rejected"


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionPath(str, Enum):
    AUTO = "auto"
    HUMAN = "human"


class LineItem(BaseModel):
    description: str
    amount: float


class ExtractedEntities(BaseModel):
    claimant_name: Optional[str] = None
    policy_number: Optional[str] = None
    claim_amount: Optional[float] = None
    date_of_service: Optional[str] = None
    provider_name: Optional[str] = None
    diagnosis_code: Optional[str] = None
    procedure_code: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    raw_amount_candidates: List[float] = Field(default_factory=list)
    raw_name_candidates: List[str] = Field(default_factory=list)


class PolicyCitation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    excerpt: str
    relevance_score: float = 1.0


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    severity: RuleSeverity
    message: str
    citations: List[PolicyCitation] = Field(default_factory=list)


class AuditEntry(BaseModel):
    timestamp: str
    stage: str
    summary: str
    metadata: Optional[Dict[str, Any]] = None


class HITLExceptionSummary(BaseModel):
    claim_id: str
    extracted_entities: ExtractedEntities
    triggered_rules: List[RuleResult]
    extraction_warnings: List[str]
    risk_score: float = 0.0  # 0.0 to 1.0 risk scale
    suggested_action: str


class CaseworkerDecision(BaseModel):
    action: DecisionOutcome  # APPROVED or REJECTED
    notes: Optional[str] = ""
    caseworker_signature: str = "Caseworker Sign-off"
    timestamp: Optional[str] = None


class ClaimState(BaseModel):
    claim_id: str
    raw_text: str
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    extraction_confidence: float = 1.0  # 0.0 to 1.0 confidence score
    extraction_warnings: List[str] = Field(default_factory=list)
    validation_results: List[RuleResult] = Field(default_factory=list)
    policy_citations: List[PolicyCitation] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING_EXTRACTION
    decision: Optional[DecisionOutcome] = None
    decision_path: Optional[DecisionPath] = None
    exception_summary: Optional[HITLExceptionSummary] = None
    letter_draft: Optional[str] = None
    caseworker_decision: Optional[CaseworkerDecision] = None
    audit_trail: List[AuditEntry] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
