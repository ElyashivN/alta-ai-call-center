# scripts/manual_twilio_gather_smoke.py
from datetime import datetime, timedelta, timezone

import os
import sys

# Make sure project root is on sys.path so `import app` works
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal, engine
from app.models import Base, Lead, Call, MeetingRequest
from app.schemas.constraints import HardConstraints
from app.models.meeting_request import MeetingRequestStatus


client = TestClient(app)


def setup_dummy_data() -> str:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Clean-ish
    db.query(Call).delete()
    db.query(Lead).delete()
    db.query(MeetingRequest).delete()
    db.commit()

    # Owner meeting request: next 2 days, 30-minute slots
    now = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    hc = HardConstraints(
        window_start=now,
        window_end=now + timedelta(days=2),
        timezone="UTC",
    )

    mr = MeetingRequest(
        owner_id="manual-test",
        title="Manual Twilio test",
        duration_minutes=30,
        max_bookings=1,
        status=MeetingRequestStatus.ACTIVE,
        hard_constraints=hc.model_dump(mode="json"),
        soft_constraints=None,
    )

    lead = Lead(
        name="Manual Lead",
        phone="+15551234567",
        email="manual@example.com",
        company="TestCo",
        timezone="UTC",
    )

    db.add(lead)
    db.add(mr)
    db.commit()
    db.refresh(lead)
    db.refresh(mr)

    # Fake call linking lead + meeting_request
    fake_sid = "CA_FAKE_GATHER_1"
    call = Call(
        lead_id=lead.id,
        meeting_request_id=mr.id,
        provider_call_id=fake_sid,
        direction="outbound-api",
        status="in-progress",
    )
    db.add(call)
    db.commit()
    db.close()

    return fake_sid


def main():
    sid = setup_dummy_data()

    # Simulate Twilio calling /twilio/voice/gather with DTMF "1"
    payload = {
        "CallSid": sid,
        "Digits": "1",
        "SpeechResult": "",
    }
    resp = client.post("/twilio/voice/gather", data=payload)
    print("Status:", resp.status_code)
    print("Twiml:\n", resp.text)


if __name__ == "__main__":
    main()
