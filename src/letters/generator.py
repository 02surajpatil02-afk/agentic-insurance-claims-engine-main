"""
Letter Drafting Stage.
Generates formal, professional approval and rejection letters.
"""

from __future__ import annotations
from src.models.schemas import ClaimState, DecisionOutcome, DecisionPath, AuditEntry
from datetime import datetime, timezone


class LetterGenerator:
    """
    Generates formal claimant decision letters.
    """

    def generate_approval_letter(self, state: ClaimState) -> str:
        entities = state.extracted_entities
        name = entities.claimant_name or "Valued Policyholder"
        pol = entities.policy_number or "N/A"
        amt = entities.claim_amount or 0.0
        provider = entities.provider_name or "Healthcare Provider"
        date_str = datetime.now().strftime("%B %d, %Y")
        
        path_desc = "Automated Rules Engine Verification"
        if state.decision_path == DecisionPath.HUMAN:
            cw_sig = state.caseworker_decision.caseworker_signature if state.caseworker_decision else "Senior Claims Specialist"
            path_desc = f"Caseworker Sign-off & Senior Review ({cw_sig})"

        caseworker_notes_section = ""
        if state.caseworker_decision and state.caseworker_decision.notes:
            caseworker_notes_section = f"\nCASEWORKER REVIEWER NOTES:\n\"{state.caseworker_decision.notes}\"\n"

        letter = f"""================================================================================
                    FORMAL CLAIM APPROVAL NOTICE
================================================================================
Date: {date_str}
Claim Reference ID: {state.claim_id}
Policy Number: {pol}

TO:
{name}

RE: Notice of Claim Approval and Benefit Authorization

Dear {name},

We are pleased to inform you that your health insurance claim submitted for services rendered by {provider} has been fully reviewed and APPROVED.

CLAIM BENEFIT SUMMARY:
--------------------------------------------------------------------------------
• Claimant Name:        {name}
• Policy Number:        {pol}
• Approved Claim Amount: ${amt:,.2f}
• Service Provider:     {provider}
• Review Pathway:       {path_desc}
--------------------------------------------------------------------------------
{caseworker_notes_section}
PAYMENT & DISBURSEMENT INSTRUCTIONS:
Reimbursement in the amount of ${amt:,.2f} has been authorized and queued for payment disbursement in accordance with your policy benefit terms. Direct deposit or check delivery will be completed within 3 to 5 business days.

If you have any questions regarding this benefit determination, please contact our Customer Care Team with your Claim Reference ID ({state.claim_id}).

Sincerely,

Enterprise Claims Processing Directorate
Health & Life Insurance Assurance Corp.
================================================================================
"""
        return letter

    def generate_rejection_letter(self, state: ClaimState) -> str:
        entities = state.extracted_entities
        name = entities.claimant_name or "Valued Policyholder"
        pol = entities.policy_number or "N/A"
        date_str = datetime.now().strftime("%B %d, %Y")

        # Gather specific rejection reasons
        reject_reasons = []
        for r in state.validation_results:
            if not r.passed and r.severity == "reject":
                reject_reasons.append(f"• [{r.rule_id} - {r.rule_name}]: {r.message}")

        if not reject_reasons and state.caseworker_decision:
            reject_reasons.append(f"• [Caseworker Rejection]: {state.caseworker_decision.notes or 'Denied following caseworker review.'}")

        reasons_text = "\n".join(reject_reasons) if reject_reasons else "• Claim does not satisfy active policy coverage criteria."

        # Gather and deduplicate policy citations
        raw_citations = list(state.policy_citations)
        for r in state.validation_results:
            raw_citations.extend(r.citations)

        seen_keys = set()
        all_citations = []
        for c in raw_citations:
            key = (c.document_name, c.page_number, c.excerpt)
            if key not in seen_keys:
                seen_keys.add(key)
                all_citations.append(c)

        citations_section = ""
        if all_citations:
            citation_lines = []
            for c in all_citations:
                sec_str = f" - {c.section_title}" if c.section_title else ""
                pg_str = f" (Page {c.page_number})" if c.page_number else ""
                citation_lines.append(f"• Document: {c.document_name}{pg_str}{sec_str}\n  Excerpt: \"{c.excerpt}\"")
            citations_section = f"\nAPPLICABLE POLICY PROVISIONS & CITATIONS:\n--------------------------------------------------------------------------------\n" + "\n".join(citation_lines) + "\n--------------------------------------------------------------------------------\n"

        letter = f"""================================================================================
                    FORMAL CLAIM DENIAL NOTICE
================================================================================
Date: {date_str}
Claim Reference ID: {state.claim_id}
Policy Number: {pol}

TO:
{name}

RE: Notice of Adverse Claim Determination

Dear {name},

This letter serves as formal notification that your claim submission (Reference ID: {state.claim_id}) under Policy Number {pol} has been reviewed and CANNOT BE APPROVED at this time.

SPECIFIC REASONS FOR DENIAL:
--------------------------------------------------------------------------------
{reasons_text}
--------------------------------------------------------------------------------
{citations_section}
APPEAL & RECONSIDERATION RIGHTS:
If you believe this determination was made in error or if you have supplemental clinical documentation (e.g. corrected invoice, active policy certificate, or provider medical notes), you have the right to file a formal appeal within 60 calendar days.

To initiate an appeal, please submit your request referencing Claim ID {state.claim_id} to our Appeals Board.

Sincerely,

Enterprise Claims Processing Directorate
Health & Life Insurance Assurance Corp.
================================================================================
"""
        return letter

    def generate(self, state: ClaimState) -> str:
        if state.decision == DecisionOutcome.APPROVED:
            return self.generate_approval_letter(state)
        else:
            return self.generate_rejection_letter(state)


def process_letter_drafting_stage(state: ClaimState) -> ClaimState:
    """
    Executes the Letter Drafting stage on a ClaimState object.
    Appends audit log entry and updates state.
    """
    generator = LetterGenerator()
    letter = generator.generate(state)
    state.letter_draft = letter
    state.updated_at = datetime.now(timezone.utc).isoformat()

    state.audit_trail.append(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        stage="LETTER_DRAFTING",
        summary=f"Generated formal decision letter ({state.decision.value.upper()}) for claimant '{state.extracted_entities.claimant_name or 'Unknown'}'.",
        metadata={
            "letter_length": len(letter),
            "outcome": state.decision.value
        }
    ))
    return state
