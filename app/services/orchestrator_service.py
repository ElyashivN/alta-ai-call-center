# app/services/orchestrator_service.py

from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.call_service import initiate_outbound_call
from app.services.twilio_client import TwilioClient


class OutboundOrchestrator:
    """
    Thin orchestration layer over the existing call service.

    Responsibility:
    - Given a set of leads and a meeting_request_id,
      trigger outbound calls for each lead via Twilio.
    - All per-call business logic (DB rows, Twilio payload, etc.)
      remains in initiate_outbound_call.
    """

    def __init__(self, db: Session, twilio_client: TwilioClient):
        self.db = db
        self.twilio_client = twilio_client

    def call_leads_for_meeting(
        self,
        *,
        meeting_request_id: int,
        leads: Iterable[Lead],
        max_calls: int | None = None,
    ) -> int:
        """
        Trigger outbound calls for the given leads.

        Returns how many calls were enqueued/created.
        """
        count = 0
        for lead in leads:
            if max_calls is not None and count >= max_calls:
                break

            initiate_outbound_call(
                db=self.db,
                twilio_client=self.twilio_client,
                lead=lead,
                meeting_request_id=meeting_request_id,
            )
            count += 1

        return count
