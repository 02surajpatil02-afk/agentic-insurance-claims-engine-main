"""
Local MCP server: send claim decision emails via SMTP (Gmail App Password).

Cursor config: .cursor/mcp.json
Tools:
  - send_email
  - send_claim_decision_letter
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is importable when Cursor launches this script.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

load_dotenv(ROOT / ".env")

from src.notifications.email import (  # noqa: E402
    DEFAULT_NOTIFY_TO,
    build_claim_notification,
    email_enabled,
    send_email,
)
from src.pipeline import load_state  # noqa: E402

server = MCPServer(
    "claims-email",
    instructions=(
        "Send ClaimsPulse AI decision letters and HITL notifications by email. "
        "Recipient defaults to EMAIL_NOTIFY_TO from .env (see .env.example)."
    ),
)


@server.tool(name="send_email")
def send_email_mcp(subject: str, body: str, to: str = DEFAULT_NOTIFY_TO) -> str:
    """Send a plain-text email via configured SMTP credentials."""
    result = send_email(subject=subject, body=body, to=to or DEFAULT_NOTIFY_TO)
    return json.dumps(result, indent=2)


@server.tool(name="send_claim_decision_letter")
def send_claim_decision_letter(claim_id: str, to: str = DEFAULT_NOTIFY_TO) -> str:
    """
    Load a persisted claim by ID and email its formal decision letter
    (or HITL exception summary if still pending human review).
    """
    state = load_state(claim_id)
    if not state:
        return json.dumps({"ok": False, "error": f"Claim '{claim_id}' not found in state/"})

    subject, body = build_claim_notification(state)
    result = send_email(subject=subject, body=body, to=to or DEFAULT_NOTIFY_TO)
    result["claim_id"] = claim_id
    result["status"] = state.status.value if state.status else None
    result["email_configured"] = email_enabled()
    return json.dumps(result, indent=2)


@server.tool()
def email_status() -> str:
    """Check whether SMTP email sending is configured and enabled."""
    import os

    return json.dumps(
        {
            "email_configured": email_enabled(),
            "notify_to": (os.getenv("EMAIL_NOTIFY_TO") or DEFAULT_NOTIFY_TO).strip(),
            "hint": "Set SMTP_USER, SMTP_PASSWORD, and EMAIL_NOTIFY_TO in .env",
        },
        indent=2,
    )


if __name__ == "__main__":
    server.run()
