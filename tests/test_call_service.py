# tests/test_call_service.py
from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models import Base, Lead, Call, MeetingRequest
from app.services.call_service import initiate_outbound_call    
from datetime import datetime, timedelta

def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_initiate_outbound_call_can_attach_meeting_request():
    _clean_db()
    db = SessionLocal()
    try:
        lead = Lead(
            name="Lead X",
            phone="+111111111",
            email="x@example.com",
            company="XCo",
            timezone="UTC",
        )
        mr = MeetingRequest(
            owner_id="am-voice",
            title="Voice test",
            duration_minutes=30,
            window_start=datetime(2025, 1, 1, 9, 0, 0),
            window_end=datetime(2025, 1, 3, 17, 0, 0),
            max_bookings=3,
        )
        db.add(lead)
        db.add(mr)
        db.commit()
        db.refresh(lead)
        db.refresh(mr)

        class FakeTwilioClient:
            def __init__(self):
                self.last_to = None

            def create_outbound_call(self, to_number: str) -> str:
                self.last_to = to_number
                return "CA_TEST_ATTACH"

        twilio_client = FakeTwilioClient()

        call = initiate_outbound_call(
            db=db,
            lead=lead,
            twilio_client=twilio_client,
            meeting_request=mr,
        )

        assert call.lead_id == lead.id
        assert call.meeting_request_id == mr.id
        assert call.provider_call_id == "CA_TEST_ATTACH"
    finally:
        db.close()
