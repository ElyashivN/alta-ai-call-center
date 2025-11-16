# tests/test_meeting_confirm_best_slot.py
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import engine, SessionLocal
from app.models import (
    Base,
    MeetingRequest,
    MeetingSlot,
    Lead,
    ParticipantAvailability,
    Meeting,
)
from app.models.participant_availability import AvailabilityState

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def _clean_db():
    db: Session = SessionLocal()
    try:
        db.query(Meeting).delete()
        db.query(ParticipantAvailability).delete()
        db.query(MeetingSlot).delete()
        db.query(MeetingRequest).delete()
        db.query(Lead).delete()
        db.commit()
    finally:
        db.close()


def test_confirm_best_slot_creates_meeting_and_marks_availability():
    _clean_db()

    # 1) Create meeting request
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

    # 2) Create two leads
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

    # 3) Record their availabilities (same overlap scenario as before)

    # Lead1: 9:00–11:00
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

    # Lead2: 10:00–11:00
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

    # 4) Confirm best slot
    resp3 = client.post(f"/meeting-requests/{mr_id}/confirm-best-slot")
    assert resp3.status_code == 200, resp3.text

    data = resp3.json()
    meeting = data["meeting"]
    slot = data["slot"]

    # Slot should be earliest 30-min window where both are available: 10:00–10:30
    assert slot["start_time"].startswith("2025-01-01T10:00:00")
    assert slot["end_time"].startswith("2025-01-01T10:30:00")

    # Meeting should be booked on that slot
    assert meeting["scheduled_start_time"].startswith("2025-01-01T10:00:00")
    assert meeting["scheduled_end_time"].startswith("2025-01-01T10:30:00")

    # Lead of the meeting should be one of the participants
    assert meeting["lead_id"] in {lead1_id, lead2_id}

    # 5) Verify DB state
    db = SessionLocal()
    try:
        meetings = db.query(Meeting).all()
        assert len(meetings) == 1
        m = meetings[0]
        assert m.scheduled_start_time == datetime(2025, 1, 1, 10, 0)
        assert m.scheduled_end_time == datetime(2025, 1, 1, 10, 30)
        assert m.lead_id in {lead1_id, lead2_id}

        pas = (
            db.query(ParticipantAvailability)
            .filter_by(meeting_request_id=mr_id)
            .all()
        )
        selected = [pa for pa in pas if pa.state == AvailabilityState.SELECTED]

        # Given our implementation, only the primary lead's window is marked SELECTED
        assert len(selected) == 1
        assert selected[0].lead_id == meeting["lead_id"]
    finally:
        db.close()
