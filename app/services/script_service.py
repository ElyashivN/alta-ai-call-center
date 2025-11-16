# app/services/script_service.py
from dataclasses import dataclass
from typing import Optional

from app.models.meeting_request import MeetingRequest
from app.models.lead import Lead


@dataclass
class CallScript:
    """
    Simple container for what the voice bot will say.

    In a real system, this would be the *output* of an LLM:
    - greeting
    - main question / pitch
    - closing
    """
    greeting: str
    question: str
    closing: str


def generate_call_script(
    meeting_request: Optional[MeetingRequest],
    lead: Optional[Lead],
) -> CallScript:
    """
    Given optional MeetingRequest + Lead, produce a simple script.

    This is intentionally dumb / template-based right now, but designed so
    you can later swap in an LLM that returns the same structure.
    """
    # Defaults
    lead_name = lead.name if lead and lead.name else "there"
    company = lead.company if lead and lead.company else None

    if meeting_request:
        title = meeting_request.title or "a quick call"
        duration = meeting_request.duration_minutes or 30
    else:
        title = "a quick call"
        duration = 30

    if company:
        greeting = f"Hi {lead_name}, this is the AI assistant calling on behalf of your account manager at {company}."
    else:
        greeting = f"Hi {lead_name}, this is the AI assistant calling to help schedule a meeting with your account manager."

    question = (
        f"We'd like to find a good time for a {duration}-minute meeting about {title}. "
        "Over the next couple of weeks, when are you generally available for a short call?"
    )

    closing = (
        "Thanks for your time. "
        "We'll pick the best slot based on your availability and send you a calendar invite shortly."
    )

    return CallScript(
        greeting=greeting,
        question=question,
        closing=closing,
    )
