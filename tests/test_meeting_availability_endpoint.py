# tests/test_meeting_availability_endpoint.py
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import engine, SessionLocal
from app.models import Base, MeetingRequest, MeetingSlot, Lead, ParticipantAvailability

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def _clean_db():
    db: Session = SessionLocal()
    try:
        db.query(ParticipantAvailability).delete()
        db.query(MeetingSlot).delete()
        db.query(MeetingRequest).delete()
        db.query(Lead).delete()
        db.commit()
    finally:
        db.close()


def test_submit_availability_for_meeting_creates_rows():
    _clean_db()

    # First, create a meeting request via simple API (to match real flows)
    payload_mr = {
        "owner_id": "am-123",
        "title": "Group intro",
        "duration_minutes": 30,
        "window_start": "2025-01-01T09:00:00",
        "window_end": "2025-01-01T11:00:00",
        "max_bookings": 3,
    }

    resp = client.post("/meeting-requests/simple", json=payload_mr)
    assert resp.status_code == 200, resp.text
    mr_id = resp.json()["meeting_request"]["id"]

    # Create a lead directly in DB
    db = SessionLocal()
    try:
        lead = Lead(
            name="Participant 1",
            phone="+222222222",
            email="p1@example.com",
            company="P1Co",
            timezone="UTC",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        lead_id = lead.id
    finally:
        db.close()

    # Submit availability windows
    payload_avail = {
        "lead_id": lead_id,
        "source_text": "Free Tue 9-11",
        "windows": [
            {
                "start_time": "2025-01-02T09:00:00",
                "end_time": "2025-01-02T11:00:00",
            }
        ],
    }

    resp2 = client.post(
        f"/meeting-requests/{mr_id}/availability",
        json=payload_avail,
    )
    assert resp2.status_code == 200, resp2.text

    data = resp2.json()
    assert data["meeting_request_id"] == mr_id
    assert data["lead_id"] == lead_id
    assert len(data["availabilities"]) == 1

    # Check DB
    db = SessionLocal()
    try:
        rows = (
            db.query(ParticipantAvailability)
            .filter_by(meeting_request_id=mr_id, lead_id=lead_id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].start_time == datetime(2025, 1, 2, 9, 0)
        assert rows[0].end_time == datetime(2025, 1, 2, 11, 0)
    finally:
        db.close()

def test_suggested_slot_endpoint_uses_availabilities():
    _clean_db()

    # Create meeting request
    payload_mr = {
        "owner_id": "am-123",
        "title": "Group intro",
        "duration_minutes": 30,
        "window_start": "2025-01-01T09:00:00",
        "window_end": "2025-01-01T11:00:00",
        "max_bookings": 3,
    }
    resp = client.post("/meeting-requests/simple", json=payload_mr)
    assert resp.status_code == 200, resp.text
    mr_id = resp.json()["meeting_request"]["id"]

    # Create two leads
    db = SessionLocal()
    try:
        lead1 = Lead(
            name="Participant 1",
            phone="+111111111",
            email="p1@example.com",
            company="P1Co",
            timezone="UTC",
        )
        lead2 = Lead(
            name="Participant 2",
            phone="+222222222",
            email="p2@example.com",
            company="P2Co",
            timezone="UTC",
        )
        db.add_all([lead1, lead2])
        db.commit()
        db.refresh(lead1)
        db.refresh(lead2)
        lead1_id = lead1.id
        lead2_id = lead2.id
    finally:
        db.close()

    # Lead1 availability: 9:00–11:00
    payload_avail1 = {
        "lead_id": lead1_id,
        "source_text": "Free 9-11",
        "windows": [
            {
                "start_time": "2025-01-01T09:00:00",
                "end_time": "2025-01-01T11:00:00",
            }
        ],
    }
    resp1 = client.post(
        f"/meeting-requests/{mr_id}/availability",
        json=payload_avail1,
    )
    assert resp1.status_code == 200, resp1.text

    # Lead2 availability: 10:00–11:00
    payload_avail2 = {
        "lead_id": lead2_id,
        "source_text": "Free 10-11",
        "windows": [
            {
                "start_time": "2025-01-01T10:00:00",
                "end_time": "2025-01-01T11:00:00",
            }
        ],
    }
    resp2 = client.post(
        f"/meeting-requests/{mr_id}/availability",
        json=payload_avail2,
    )
    assert resp2.status_code == 200, resp2.text

    # Ask for suggested slot
    resp3 = client.get(f"/meeting-requests/{mr_id}/suggested-slot")
    assert resp3.status_code == 200, resp3.text

    data = resp3.json()
    slot = data["slot"]
    assert slot is not None
    # Should be the earliest 30-min slot with both participants: 10:00–10:30
    assert slot["start_time"].startswith("2025-01-01T10:00:00")
    assert slot["end_time"].startswith("2025-01-01T10:30:00")
    assert len(slot["participant_lead_ids"]) == 2
    assert set(slot["participant_lead_ids"]) == {lead1_id, lead2_id}
