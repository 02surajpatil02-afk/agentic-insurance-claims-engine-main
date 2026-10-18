"""
SMTP email notifications for claim outcomes.
Used by the FastAPI pipeline and the local claims-email MCP server.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from src.models.schemas import ClaimState, WorkflowStatus

# Load project .env when present (safe no-op if missing).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

DEFAULT_NOTIFY_TO = "you@example.com"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


_PLACEHOLDER_PASSWORDS = {
    "",
    "your_16_char_gmail_app_password",
    "changeme",
    "password",
    "app_password_here",
}


def email_enabled() -> bool:
    """True when SMTP credentials are configured and EMAIL_ENABLED is not false."""
    flag = _env("EMAIL_ENABLED", "true").lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    password = _env("SMTP_PASSWORD")
    if password.lower() in _PLACEHOLDER_PASSWORDS:
        return False
    return bool(_env("SMTP_USER") and password)


def _smtp_settings() -> Dict[str, Any]:
    return {
        "host": _env("SMTP_HOST", "smtp.gmail.com"),
        "port": int(_env("SMTP_PORT", "587") or "587"),
        "user": _env("SMTP_USER"),
        "password": _env("SMTP_PASSWORD"),
        "from_addr": _env("SMTP_FROM") or _env("SMTP_USER"),
        "to_addr": _env("EMAIL_NOTIFY_TO", DEFAULT_NOTIFY_TO) or DEFAULT_NOTIFY_TO,
    }


def send_email(
    subject: str,
    body: str,
    to: Optional[str] = None,
    *,
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """
    Send a plain-text email via SMTP.
    Returns a status dict; never raises unless raise_on_error=True.
    """
    settings = _smtp_settings()
    recipient = (to or settings["to_addr"] or DEFAULT_NOTIFY_TO).strip()

    if not email_enabled():
        result = {
            "ok": False,
            "skipped": True,
            "reason": "Email disabled or SMTP_USER/SMTP_PASSWORD not configured in .env",
            "to": recipient,
            "subject": subject,
        }
        return result

    msg = MIMEMultipart()
    msg["From"] = settings["from_addr"]
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings["user"], settings["password"])
            server.sendmail(settings["from_addr"], [recipient], msg.as_string())
        return {
            "ok": True,
            "skipped": False,
            "to": recipient,
            "subject": subject,
            "from": settings["from_addr"],
        }
    except Exception as exc:
        if raise_on_error:
            raise
        return {
            "ok": False,
            "skipped": False,
            "error": str(exc),
            "to": recipient,
            "subject": subject,
        }


def build_claim_notification(state: ClaimState) -> Tuple[str, str]:
    """Build subject + body for approve / reject / HITL outcomes."""
    entities = state.extracted_entities
    name = entities.claimant_name or "Unknown Claimant"
    policy = entities.policy_number or "N/A"
    amount = entities.claim_amount
    amount_str = f"${amount:,.2f}" if amount is not None else "N/A"
    status = state.status.value if state.status else "unknown"

    if state.status == WorkflowStatus.PENDING_HUMAN_REVIEW:
        subject = f"[HITL] Claim {state.claim_id} requires caseworker sign-off"
        summary = state.exception_summary
        risk = summary.risk_score if summary else "N/A"
        suggested = summary.suggested_action if summary else "Senior caseworker review required."
        triggered = ""
        if summary and summary.triggered_rules:
            lines = []
            for rule in summary.triggered_rules:
                lines.append(f"  - [{rule.rule_id}] {rule.rule_name}: {rule.message}")
            triggered = "\n".join(lines)
        else:
            triggered = "  (no rule details available)"

        body = f"""ClaimsPulse AI — HITL Exception Notification
================================================================================
Claim ID:     {state.claim_id}
Status:       {status}
Claimant:     {name}
Policy:       {policy}
Amount:       {amount_str}
Risk Score:   {risk}

Suggested Action:
{suggested}

Triggered Escalation Rules:
{triggered}

--------------------------------------------------------------------------------
NOTE: A formal decision letter will be generated after caseworker approve/reject.
Open the dashboard HITL Exception Queue to complete sign-off.
================================================================================
"""
        return subject, body

    outcome = "APPROVED" if state.status == WorkflowStatus.RESOLVED_APPROVED else "REJECTED"
    if state.decision:
        outcome = state.decision.value.upper()

    subject = f"[{outcome}] Formal Decision Letter — Claim {state.claim_id}"
    letter = state.letter_draft or "(No formal letter body was generated for this claim.)"
    body = f"""ClaimsPulse AI — Formal Decision Letter
================================================================================
Claim ID:     {state.claim_id}
Outcome:      {outcome}
Claimant:     {name}
Policy:       {policy}
Amount:       {amount_str}
Status:       {status}
Decision Path:{state.decision_path.value if state.decision_path else 'N/A'}

--------------------------------------------------------------------------------
FORMAL DECISION LETTER
--------------------------------------------------------------------------------
{letter}
================================================================================
"""
    return subject, body


def notify_claim_outcome(state: ClaimState, to: Optional[str] = None) -> Dict[str, Any]:
    """Email claim outcome (letter or HITL summary) to the configured recipient."""
    subject, body = build_claim_notification(state)
    return send_email(subject, body, to=to)
