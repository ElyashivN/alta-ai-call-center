# app/routers/campaigns.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lead import Lead
from app.models.call import Call
from app.models.meeting_request import MeetingRequest
from app.services.scheduling_service import create_meeting_request_and_slots
from app.services.call_service import initiate_outbound_call
from app.services.twilio_client import TwilioClient, get_twilio_client

router = APIRouter()


class CampaignLeadIn(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None


class CampaignCreatePayload(BaseModel):
    owner_id: str
    title: str
    duration_minutes: int
    window_start: datetime
    window_end: datetime
    max_bookings: int = 0
    leads: List[CampaignLeadIn]


class CampaignCreateResponse(BaseModel):
    meeting_request_id: int
    slot_count: int
    lead_ids: List[int]
    call_ids: List[int]


@router.post("/simple", response_model=CampaignCreateResponse)
def create_campaign_simple(
    payload: CampaignCreatePayload,
    db: Session = Depends(get_db),
    twilio_client: TwilioClient = Depends(get_twilio_client),
):
    """
    One-shot 'campaign' endpoint:

    - creates a MeetingRequest + slots
    - upserts leads by phone
    - triggers outbound calls for each lead
    """

    # 1) Create meeting request + slots
    meeting_request, slots = create_meeting_request_and_slots(
        db=db,
        owner_id=payload.owner_id,
        title=payload.title,
        duration_minutes=payload.duration_minutes,
        window_start=payload.window_start,
        window_end=payload.window_end,
        max_bookings=payload.max_bookings,
    )

    lead_ids: list[int] = []
    call_ids: list[int] = []

    # 2) For each incoming lead:
    for lead_in in payload.leads:
        # Upsert by phone
        lead: Optional[Lead] = (
            db.query(Lead)
            .filter(Lead.phone == lead_in.phone)
            .first()
        )

        if not lead:
            lead = Lead(
                name=lead_in.name,
                phone=lead_in.phone,
                email=lead_in.email,
                company=lead_in.company,
                timezone=lead_in.timezone or "UTC",
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

        lead_ids.append(lead.id)

        # 3) Trigger outbound call, tying it to this meeting_request
        call: Call = initiate_outbound_call(
            db=db,
            lead=lead,
            twilio_client=twilio_client,
            meeting_request=meeting_request,
        )
        call_ids.append(call.id)

    return CampaignCreateResponse(
        meeting_request_id=meeting_request.id,
        slot_count=len(slots),
        lead_ids=lead_ids,
        call_ids=call_ids,
    )
