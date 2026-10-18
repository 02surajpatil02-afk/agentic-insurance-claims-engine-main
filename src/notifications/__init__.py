"""Notification helpers (email / MCP-backed outbound messaging)."""

from src.notifications.email import (
    build_claim_notification,
    notify_claim_outcome,
    send_email,
)

__all__ = [
    "build_claim_notification",
    "notify_claim_outcome",
    "send_email",
]
