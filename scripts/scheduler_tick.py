# scripts/scheduler_tick.py
"""
Simple scheduler "tick" script.

In a real deployment this logic would run inside a queue worker (Celery, RQ,
Kubernetes CronJob, etc.). For the assignment we keep it synchronous and small.

Flow:
1. Pick a MeetingRequest by ID (from CLI for now).
2. Fetch leads that should be called (here: all leads, or you can filter).
3. Hand that batch to the OutboundOrchestrator, which uses Twilio to place calls.
"""

from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.models.lead import Lead
from app.models.meeting_request import MeetingRequest
from app.services.twilio_client import TwilioClient
from app.services.orchestrator_service import OutboundOrchestrator


def run_once(meeting_request_id: int, max_calls: int | None = None) -> None:
    db = SessionLocal()
    try:
        mr = db.get(MeetingRequest, meeting_request_id)
        if not mr:
            print(f"[scheduler_tick] MeetingRequest {meeting_request_id} not found")
            return

        # For the assignment: keep it simple and just call *all* leads.
        # In a real system you'd likely filter by campaign, timezone, etc.
        leads = db.query(Lead).all()

        twilio_client = TwilioClient()
        orchestrator = OutboundOrchestrator(db=db, twilio_client=twilio_client)

        placed = orchestrator.call_leads_for_meeting(
            meeting_request_id=meeting_request_id,
            leads=leads,
            max_calls=max_calls,
        )

        print(
            f"[scheduler_tick] Placed {placed} calls "
            f"for meeting_request_id={meeting_request_id}"
        )

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--meeting-request-id",
        type=int,
        required=True,
        help="Which MeetingRequest to schedule calls for",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=None,
        help="Optional max number of calls to place in this tick",
    )
    args = parser.parse_args()
    run_once(meeting_request_id=args.meeting_request_id, max_calls=args.max_calls)


if __name__ == "__main__":
    main()
