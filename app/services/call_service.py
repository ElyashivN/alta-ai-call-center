# app/services/call_service.py
from typing import Optional

from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.lead import Lead
from app.models.meeting_request import MeetingRequest
from app.services.twilio_client import TwilioClient


def initiate_outbound_call(
    db: Session,
    lead: Lead,
    twilio_client: TwilioClient,
    meeting_request: Optional[MeetingRequest] = None,
) -> Call:
    """
    Trigger an outbound call via Twilio and persist a Call row.

    `meeting_request` is optional so existing tests & routes that don't
    have one yet keep working.

    Later, campaign flows will always pass a MeetingRequest here.
    """
    call_sid = twilio_client.create_outbound_call(to_number=lead.phone)

    call = Call(
        lead_id=lead.id,
        meeting_request_id=meeting_request.id if meeting_request else None,
        provider_call_id=call_sid,
        direction="outbound",
        status="initiated",
    )

    if meeting_request is not None:
        call.meeting_request_id = meeting_request.id

    db.add(call)
    db.commit()
    db.refresh(call)
    return call


