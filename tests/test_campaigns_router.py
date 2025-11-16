# tests/test_campaigns_router.py
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import engine, SessionLocal
from app.models import Base, Lead, Call, MeetingRequest
from app.services.twilio_client import get_twilio_client


class FakeTwilioClient:
    def __init__(self):
        self.called_numbers: list[str] = []

    def create_outbound_call(self, to_number: str) -> str:
        self.called_numbers.append(to_number)
        # Return a deterministic fake CallSid
        return f"CA_FAKE_{to_number[-4:]}"


def override_twilio_client():
    return FakeTwilioClient()


app.dependency_overrides[get_twilio_client] = override_twilio_client

client = TestClient(app)


def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_campaign_simple_creates_meeting_request_leads_calls():
    _clean_db()

    now = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)

    payload = {
        "owner_id": "am-999",
        "title": "Demo campaign",
        "duration_minutes": 30,
        "window_start": now.isoformat(),
        "window_end": (now + timedelta(hours=2)).isoformat(),
        "max_bookings": 3,
        "leads": [
            {"name": "Lead A", "phone": "+11111111111"},
            {"name": "Lead B", "phone": "+22222222222"},
        ],
    }

    resp = client.post("/campaigns/simple", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "meeting_request_id" in data
    assert len(data["lead_ids"]) == 2
    assert len(data["call_ids"]) == 2

    db = SessionLocal()
    try:
        mr = db.query(MeetingRequest).filter_by(id=data["meeting_request_id"]).first()
        assert mr is not None

        leads = db.query(Lead).all()
        assert len(leads) == 2

        calls = db.query(Call).all()
        assert len(calls) == 2
        for c in calls:
            assert c.meeting_request_id == mr.id
    finally:
        db.close()
