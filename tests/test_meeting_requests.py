# tests/test_meeting_requests.py
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import engine, SessionLocal
from app.models import Base, MeetingRequest, MeetingSlot

client = TestClient(app)


def setup_module(module):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)


def _clean_db():
    db: Session = SessionLocal()
    try:
        db.query(MeetingSlot).delete()
        db.query(MeetingRequest).delete()
        db.commit()
    finally:
        db.close()


def test_create_simple_meeting_request_generates_slots():
    _clean_db()

    payload = {
        "owner_id": "am-123",
        "title": "Intro call",
        "duration_minutes": 30,
        # 1 hour window -> 2 slots of 30 min
        "window_start": "2025-01-01T09:00:00",
        "window_end": "2025-01-01T10:00:00",
        "max_bookings": 1,
    }

    resp = client.post("/meeting-requests/simple", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    mr = data["meeting_request"]
    slots = data["slots"]

    assert mr["owner_id"] == "am-123"
    assert mr["title"] == "Intro call"
    assert mr["duration_minutes"] == 30
    assert mr["hard_constraints"]["window_start"].startswith("2025-01-01T09:00")
    assert mr["hard_constraints"]["window_end"].startswith("2025-01-01T10:00")

    # Verify 2 slots in that hour
    assert len(slots) == 2
    assert slots[0]["start_time"].startswith("2025-01-01T09:00")
    assert slots[0]["end_time"].startswith("2025-01-01T09:30")
    assert slots[1]["start_time"].startswith("2025-01-01T09:30")
    assert slots[1]["end_time"].startswith("2025-01-01T10:00")

    # Verify DB state matches
    db = SessionLocal()
    try:
        mr_row = db.query(MeetingRequest).filter_by(id=mr["id"]).first()
        assert mr_row is not None

        slots_rows = (
            db.query(MeetingSlot)
            .filter_by(meeting_request_id=mr_row.id)
            .order_by(MeetingSlot.start_time.asc())
            .all()
        )
        assert len(slots_rows) == 2
    finally:
        db.close()


def test_meeting_request_invalid_window_returns_400():
    _clean_db()

    payload = {
        "owner_id": "am-123",
        "title": "Bad window",
        "duration_minutes": 30,
        "window_start": "2025-01-01T10:00:00",
        "window_end": "2025-01-01T09:00:00",  # end before start
        "max_bookings": 1,
    }

    resp = client.post("/meeting-requests/simple", json=payload)
    assert resp.status_code == 400
