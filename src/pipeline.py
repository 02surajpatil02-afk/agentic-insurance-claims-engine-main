"""
State Machine Orchestrator & Resumable Pipeline.
Implements run_pipeline and resume_pipeline contracts with full state persistence.
"""

from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from src.models.schemas import (
    ClaimState,
    WorkflowStatus,
    DecisionOutcome,
    DecisionPath,
    CaseworkerDecision,
    AuditEntry,
)
from src.extraction.extractor import process_extraction_stage
from src.validation.evaluator import process_validation_stage
from src.decision.router import process_decision_stage
from src.letters.generator import process_letter_drafting_stage
from src.notifications.email import notify_claim_outcome

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)


def _notify_and_audit(state: ClaimState) -> ClaimState:
    """
    Email formal letter (or HITL summary) after every terminal/halt outcome.
    Failures are recorded in the audit trail and never break the pipeline.
    """
    result = notify_claim_outcome(state)
    if result.get("ok"):
        summary = f"Decision notification emailed to {result.get('to')} ({result.get('subject')})."
    elif result.get("skipped"):
        summary = f"Email notification skipped: {result.get('reason')}"
    else:
        summary = f"Email notification failed: {result.get('error', 'unknown error')}"

    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="EMAIL_NOTIFICATION",
        summary=summary,
        metadata=result,
    ))
    state.updated_at = datetime.now(timezone.utc).isoformat()
    return state


def save_state(state: ClaimState) -> None:
    """Persists a ClaimState object to JSON file on disk."""
    filepath = STATE_DIR / f"{state.claim_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(state.model_dump_json(indent=2))


def load_state(claim_id: str) -> Optional[ClaimState]:
    """Loads a persisted ClaimState object from disk."""
    filepath = STATE_DIR / f"{claim_id}.json"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        return ClaimState.model_validate(data)


def list_states() -> List[ClaimState]:
    """Lists all persisted claims from state storage."""
    states = []
    if not STATE_DIR.exists():
        return states
    for file in STATE_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                states.append(ClaimState.model_validate(data))
        except Exception:
            pass
    return sorted(states, key=lambda s: s.created_at, reverse=True)


def run_pipeline(claim_text: str, claim_id: Optional[str] = None) -> ClaimState:
    """
    Executes the multi-step agent workflow:
    Extraction -> Validation -> Decision Router -> (Halt for HITL or Generate Letter -> Resolve).
    
    Returns the updated ClaimState. If halted for HITL, status will be PENDING_HUMAN_REVIEW.
    """
    if not claim_id:
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

    state = ClaimState(
        claim_id=claim_id,
        raw_text=claim_text,
        status=WorkflowStatus.PENDING_EXTRACTION,
        audit_trail=[
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="INGESTION",
                summary=f"Claim document ingested successfully (ID: {claim_id}). Length: {len(claim_text)} chars."
            )
        ]
    )

    # 1. Extraction Stage
    state = process_extraction_stage(state)

    # 2. Validation Stage (Rules Engine)
    state = process_validation_stage(state)

    # 3. Decision Router Stage
    state = process_decision_stage(state)

    # 4. Check if Halted for Human-in-the-Loop (HITL)
    if state.status == WorkflowStatus.PENDING_HUMAN_REVIEW:
        # Halt execution, email HITL summary, persist state to disk, return state
        state = _notify_and_audit(state)
        save_state(state)
        return state

    # 5. Otherwise Auto-Decided -> Draft Letter and Resolve
    state = process_letter_drafting_stage(state)
    
    if state.decision == DecisionOutcome.APPROVED:
        state.status = WorkflowStatus.RESOLVED_APPROVED
    else:
        state.status = WorkflowStatus.RESOLVED_REJECTED

    state.updated_at = datetime.now(timezone.utc).isoformat()
    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="COMPLETION",
        summary=f"Pipeline completed automatically. Final Outcome: {state.decision.value.upper()} ({state.status.value})."
    ))

    # Email formal decision letter (approve / reject)
    state = _notify_and_audit(state)

    # Persist state
    save_state(state)
    return state


async def run_pipeline_stream(claim_text: str, claim_id: Optional[str] = None):
    """
    Async generator yielding real-time backend agent execution progress events for each stage:
    Ingestion -> Extraction -> Validation -> Decision Router -> (HITL Halt or Draft Letter) -> Resolution.
    """
    import asyncio

    if not claim_id:
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

    state = ClaimState(
        claim_id=claim_id,
        raw_text=claim_text,
        status=WorkflowStatus.PENDING_EXTRACTION,
        audit_trail=[
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="INGESTION",
                summary=f"Claim document ingested successfully (ID: {claim_id}). Length: {len(claim_text)} chars."
            )
        ]
    )

    # 1. Ingestion Event
    yield {
        "event": "step_progress",
        "step_index": 0,
        "step_id": "ingest",
        "message": f"Document Ingested ({len(claim_text)} chars)",
        "state": state.model_dump()
    }
    await asyncio.sleep(0.35)

    # 2. Extraction Stage
    state = process_extraction_stage(state)
    yield {
        "event": "step_progress",
        "step_index": 1,
        "step_id": "extract",
        "message": f"Extracted Name: '{state.extracted_entities.claimant_name}', Amount: ${state.extracted_entities.claim_amount or 0:,.2f}",
        "state": state.model_dump()
    }
    await asyncio.sleep(0.45)

    # 3. Validation Stage (Rules Engine)
    state = process_validation_stage(state)
    yield {
        "event": "step_progress",
        "step_index": 2,
        "step_id": "validate",
        "message": f"Evaluated {len(state.validation_results)} Rules",
        "state": state.model_dump()
    }
    await asyncio.sleep(0.45)

    # 4. Decision Router Stage
    state = process_decision_stage(state)
    yield {
        "event": "step_progress",
        "step_index": 3,
        "step_id": "route",
        "message": f"Routing Evaluated (Status: {state.status.value})",
        "state": state.model_dump()
    }
    await asyncio.sleep(0.35)

    # 5. Check if Halted for Human-in-the-Loop (HITL)
    if state.status == WorkflowStatus.PENDING_HUMAN_REVIEW:
        state = _notify_and_audit(state)
        save_state(state)
        yield {
            "event": "step_progress",
            "step_index": 4,
            "step_id": "hitl_or_draft",
            "message": "WORKFLOW HALTED: Exception Review Required (email notified)",
            "state": state.model_dump()
        }
        await asyncio.sleep(0.3)

        yield {
            "event": "completed",
            "step_index": 5,
            "step_id": "completed",
            "message": "Halted for Human-in-the-Loop Review",
            "state": state.model_dump()
        }
        return

    # 6. Letter Drafting Stage & Auto Resolution
    state = process_letter_drafting_stage(state)
    if state.decision == DecisionOutcome.APPROVED:
        state.status = WorkflowStatus.RESOLVED_APPROVED
    else:
        state.status = WorkflowStatus.RESOLVED_REJECTED

    state.updated_at = datetime.now(timezone.utc).isoformat()
    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="COMPLETION",
        summary=f"Pipeline completed automatically. Final Outcome: {state.decision.value.upper()} ({state.status.value})."
    ))
    state = _notify_and_audit(state)
    save_state(state)

    yield {
        "event": "step_progress",
        "step_index": 4,
        "step_id": "hitl_or_draft",
        "message": f"Generated Formal Letter ({state.decision.value.upper()})",
        "state": state.model_dump()
    }
    await asyncio.sleep(0.35)

    yield {
        "event": "completed",
        "step_index": 5,
        "step_id": "completed",
        "message": f"Completed: {state.status.value.upper()}",
        "state": state.model_dump()
    }


def resume_pipeline(claim_id: str, caseworker_decision: CaseworkerDecision) -> ClaimState:
    """
    Resumes a halted claim workflow following human caseworker review & sign-off.
    Applies decision, records audit trail, synthesizes final decision letter, and resolves.
    """
    state = load_state(claim_id)
    if not state:
        raise ValueError(f"Claim ID '{claim_id}' not found in state persistence.")

    if state.status != WorkflowStatus.PENDING_HUMAN_REVIEW:
        raise ValueError(f"Cannot resume claim '{claim_id}' — current status is '{state.status.value}', not 'pending_human_review'.")

    # Set caseworker decision metadata
    if not caseworker_decision.timestamp:
        caseworker_decision.timestamp = datetime.now(timezone.utc).isoformat()

    state.caseworker_decision = caseworker_decision
    state.decision = caseworker_decision.action
    state.decision_path = DecisionPath.HUMAN

    if caseworker_decision.action == DecisionOutcome.APPROVED:
        state.status = WorkflowStatus.RESOLVED_APPROVED
    else:
        state.status = WorkflowStatus.RESOLVED_REJECTED

    state.updated_at = datetime.now(timezone.utc).isoformat()

    # Append audit log
    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="HITL_CASEWORKER_SIGNOFF",
        summary=f"Human Caseworker Sign-off recorded: {caseworker_decision.action.value.upper()} by '{caseworker_decision.caseworker_signature}'. Notes: '{caseworker_decision.notes}'",
        metadata={
            "action": caseworker_decision.action.value,
            "signature": caseworker_decision.caseworker_signature,
            "notes": caseworker_decision.notes
        }
    ))

    # Generate final customized letter reflecting human sign-off
    state = process_letter_drafting_stage(state)

    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="COMPLETION",
        summary=f"Pipeline resumed and completed via Caseworker Sign-off. Final Status: {state.status.value}."
    ))

    # Email final letter after HITL resolve (approve / reject)
    state = _notify_and_audit(state)

    # Save updated state
    save_state(state)
    return state
