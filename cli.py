"""
Command Line Interface (CLI) for Autonomous Enterprise Workflow Agent.
Supports processing sample claims, listing persisted claims, interactive caseworker sign-offs,
and outputting formatted terminal tables and letters.
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from src.pipeline import run_pipeline, resume_pipeline, list_states, load_state
from src.models.schemas import DecisionOutcome, CaseworkerDecision, WorkflowStatus


def format_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def print_claim_summary(state):
    format_header(f"CLAIM PROCESSING SUMMARY — ID: {state.claim_id}")
    print(f"Status:             {state.status.value.upper()}")
    print(f"  * Claimant Name:        {state.extracted_entities.claimant_name or 'N/A'}")
    print(f"Policy Number:      {state.extracted_entities.policy_number or 'N/A'}")
    print(f"Claim Amount:       ${state.extracted_entities.claim_amount or 0:,.2f}")
    print(f"Extraction Conf:    {state.extraction_confidence * 100:.0f}%")
    if state.decision:
        print(f"Final Decision:     {state.decision.value.upper()} (Path: {state.decision_path.value.upper()})")
    print("-" * 80)

    print("\n[VALIDATION RULES RESULTS]")
    for r in state.validation_results:
        status_symbol = "[PASS]" if r.passed else f"[FAIL] ({r.severity.value.upper()})"
        print(f"  * [{r.rule_id}] {r.rule_name:<38} | {status_symbol:<15} | {r.message}")

    if state.status == WorkflowStatus.PENDING_HUMAN_REVIEW and state.exception_summary:
        print("\n" + "!" * 80)
        print("  WORKFLOW HALTED — HUMAN-IN-THE-LOOP (HITL) EXCEPTION REVIEW REQUIRED")
        print("!" * 80)
        print(f"Risk Score:         {state.exception_summary.risk_score} / 1.0")
        print(f"Suggested Action:   {state.exception_summary.suggested_action}")
        print("\nTriggered Escalation Rules:")
        for tr in state.exception_summary.triggered_rules:
            print(f"  - [{tr.rule_id}]: {tr.message}")
        if state.extraction_warnings:
            print("\nExtraction Warnings:")
            for w in state.extraction_warnings:
                print(f"  - {w}")
        print("\nTo resume and record caseworker sign-off, run:")
        print(f"  python cli.py --resume {state.claim_id} --action approve --notes \"Your review notes here\"")
        print("-" * 80)

    if state.letter_draft:
        print("\n[GENERATED FORMAL DECISION LETTER]")
        print(state.letter_draft)

    print("\n[AUDIT TRAIL LOGS]")
    for entry in state.audit_trail:
        print(f"  [{entry.timestamp[:19]}] [{entry.stage:<20}] {entry.summary}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Enterprise Workflow Agent CLI")
    parser.add_argument("--sample", type=str, help="Path to sample claim text file (e.g. sample_claims/clean_approve.txt)")
    parser.add_argument("--list", action="store_true", help="List all persisted claims in state storage")
    parser.add_argument("--view", type=str, help="View state of a specific claim ID")
    parser.add_argument("--resume", type=str, help="Resume a halted claim ID requiring HITL sign-off")
    parser.add_argument("--action", type=str, choices=["approve", "reject"], help="Caseworker decision action for resume (approve/reject)")
    parser.add_argument("--notes", type=str, default="Approved following manual caseworker verification.", help="Caseworker notes for sign-off")
    parser.add_argument("--signature", type=str, default="Senior Caseworker J. Smith, RN", help="Caseworker digital signature")

    args = parser.parse_args()

    if args.list:
        states = list_states()
        format_header("PERMITTED PERSISTED CLAIMS IN STATE STORE")
        if not states:
            print("No persisted claims found.")
            return
        print(f"{'CLAIM ID':<18} | {'STATUS':<24} | {'CLAIMANT':<20} | {'AMOUNT':<12} | {'DECISION'}")
        print("-" * 85)
        for s in states:
            amt_str = f"${s.extracted_entities.claim_amount or 0:,.2f}"
            dec_str = s.decision.value.upper() if s.decision else "PENDING"
            print(f"{s.claim_id:<18} | {s.status.value:<24} | {(s.extracted_entities.claimant_name or 'N/A'):<20} | {amt_str:<12} | {dec_str}")
        print("=" * 85 + "\n")
        return

    if args.view:
        state = load_state(args.view)
        if not state:
            print(f"Error: Claim ID '{args.view}' not found.")
            sys.exit(1)
        print_claim_summary(state)
        return

    if args.resume:
        if not args.action:
            print("Error: --action (approve|reject) is required when resuming a claim.")
            sys.exit(1)
        
        outcome = DecisionOutcome.APPROVED if args.action.lower() == "approve" else DecisionOutcome.REJECTED
        decision = CaseworkerDecision(
            action=outcome,
            notes=args.notes,
            caseworker_signature=args.signature
        )

        try:
            print(f"\nResuming halted claim '{args.resume}' with decision: {outcome.value.upper()}...")
            updated_state = resume_pipeline(args.resume, decision)
            print_claim_summary(updated_state)
        except Exception as e:
            print(f"Error resuming claim: {e}")
            sys.exit(1)
        return

    if args.sample:
        sample_path = Path(args.sample)
        if not sample_path.exists():
            print(f"Error: Sample file '{args.sample}' not found.")
            sys.exit(1)

        with open(sample_path, "r", encoding="utf-8") as f:
            claim_text = f.read()

        print(f"\nProcessing claim file: {args.sample}...")
        state = run_pipeline(claim_text)
        print_claim_summary(state)
        return

    # Default help message
    parser.print_help()


if __name__ == "__main__":
    main()
