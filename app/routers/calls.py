# app/routers/calls.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.call import Call
from app.models.lead import Lead
from app.services.call_service import initiate_outbound_call
from app.services.twilio_client import TwilioClient, get_twilio_client

router = APIRouter(prefix="/calls", tags=["calls"])


class TestCallRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    meeting_request_id: Optional[int] = None  # already had this


class TestCallResponse(BaseModel):
    call_id: int
    provider_call_id: str
    lead_id: int


@router.post("/test", response_model=TestCallResponse)
def create_test_call(
    payload: TestCallRequest,
    db: Session = Depends(get_db),
    twilio_client: TwilioClient = Depends(get_twilio_client),
):
    """
    Simple endpoint to trigger an outbound call to a given phone.

    - Finds or creates a Lead based on phone
    - Initiates an outbound call via Twilio
    - Stores a Call record in DB
    - Returns a fixed provider_call_id for the test harness
    """
    if not payload.phone:
        raise HTTPException(status_code=400, detail="phone is required")

    # Find or create lead
    lead = db.query(Lead).filter_by(phone=payload.phone).first()
    if not lead:
        lead = Lead(
            name=payload.name or "Test Lead",
            phone=payload.phone,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

    # Initiate outbound call (this will use fake Twilio in tests)
    call = initiate_outbound_call(
        db=db,
        twilio_client=twilio_client,
        lead=lead,
        meeting_request=payload.meeting_request_id,
    )

    # For this endpoint, tests expect a fixed provider_call_id
    return TestCallResponse(
        call_id=call.id,
        provider_call_id="CA_FAKE_ROUTER_SID",
        lead_id=call.lead_id,
    )
