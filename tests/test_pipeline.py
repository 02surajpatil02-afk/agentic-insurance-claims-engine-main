"""
Integration tests for Agent Pipeline Orchestration, HITL Halted State, and Resumability.
"""

from pathlib import Path
from src.pipeline import run_pipeline, resume_pipeline, load_state
from src.models.schemas import WorkflowStatus, DecisionOutcome, CaseworkerDecision, DecisionPath


def test_end_to_end_clean_approve():
    with open("sample_claims/clean_approve.txt", "r", encoding="utf-8") as f:
        text = f.read()

    state = run_pipeline(text)
    assert state.status == WorkflowStatus.RESOLVED_APPROVED
    assert state.decision == DecisionOutcome.APPROVED
    assert state.decision_path == DecisionPath.AUTO
    assert state.letter_draft is not None
    assert "FORMAL CLAIM APPROVAL NOTICE" in state.letter_draft


def test_end_to_end_hitl_halt_and_resume():
    with open("sample_claims/over_threshold.txt", "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Run initial pipeline -> MUST HALT for HITL review
    state = run_pipeline(text)
    assert state.status == WorkflowStatus.PENDING_HUMAN_REVIEW
    assert state.decision is None
    assert state.exception_summary is not None
    assert state.exception_summary.risk_score >= 0.8

    # Verify state is persisted on disk
    persisted = load_state(state.claim_id)
    assert persisted is not None
    assert persisted.status == WorkflowStatus.PENDING_HUMAN_REVIEW

    # 2. Resume pipeline with Caseworker Sign-off
    decision = CaseworkerDecision(
        action=DecisionOutcome.APPROVED,
        notes="Verified cardiac surgery emergency authorization with attending MD.",
        caseworker_signature="Dr. Emily Vance, Chief Medical Officer"
    )

    resumed_state = resume_pipeline(state.claim_id, decision)
    assert resumed_state.status == WorkflowStatus.RESOLVED_APPROVED
    assert resumed_state.decision == DecisionOutcome.APPROVED
    assert resumed_state.decision_path == DecisionPath.HUMAN
    assert resumed_state.caseworker_decision.caseworker_signature == "Dr. Emily Vance, Chief Medical Officer"
    assert "Dr. Emily Vance" in resumed_state.letter_draft
    assert "Verified cardiac surgery emergency authorization" in resumed_state.letter_draft


def test_end_to_end_conflicting_data_hitl_halt():
    with open("sample_claims/conflicting_data.txt", "r", encoding="utf-8") as f:
        text = f.read()

    state = run_pipeline(text)
    assert state.status == WorkflowStatus.PENDING_HUMAN_REVIEW
    assert state.decision is None
    assert state.exception_summary is not None
    triggered_ids = [r.rule_id for r in state.exception_summary.triggered_rules]
    assert "R106" in triggered_ids or "R107" in triggered_ids
    assert len(state.extraction_warnings) >= 2


def test_end_to_end_clean_reject():
    with open("sample_claims/clean_reject.txt", "r", encoding="utf-8") as f:
        text = f.read()

    state = run_pipeline(text)
    assert state.status == WorkflowStatus.RESOLVED_REJECTED
    assert state.decision == DecisionOutcome.REJECTED
    assert state.decision_path == DecisionPath.AUTO
    assert state.extracted_entities.policy_number == "INVALID_9999"
    assert "INVALID_9999" in state.letter_draft
    assert "FORMAL CLAIM DENIAL NOTICE" in state.letter_draft


def test_end_to_end_policy_renewal_conflict():
    with open("sample_claims/policy_renewal_conflict.txt", "r", encoding="utf-8") as f:
        text = f.read()

    state = run_pipeline(text)
    assert state.status == WorkflowStatus.PENDING_HUMAN_REVIEW
    assert state.decision is None
    assert state.exception_summary is not None
    triggered_ids = [r.rule_id for r in state.exception_summary.triggered_rules]
    assert triggered_ids == ["R105"]  # Only R105 fires
    assert state.exception_summary.risk_score == 0.6


def test_end_to_end_multiple_policy_refs():
    with open("sample_claims/multiple_policy_refs.txt", "r", encoding="utf-8") as f:
        text = f.read()

    state = run_pipeline(text)
    assert state.status == WorkflowStatus.PENDING_HUMAN_REVIEW
    assert state.decision is None
    assert state.exception_summary is not None
    triggered_ids = [r.rule_id for r in state.exception_summary.triggered_rules]
    assert triggered_ids == ["R106"]  # Only R106 fires
    assert state.exception_summary.risk_score == 0.5
    assert "Verify active policy ID with underwriting" in state.exception_summary.suggested_action


