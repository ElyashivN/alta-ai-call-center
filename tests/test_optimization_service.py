# tests/test_optimization_service.py
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models import Base, Lead, MeetingRequest, ParticipantAvailability
from app.models.meeting_request import MeetingRequestStatus
from app.models.participant_availability import AvailabilityState
from app.services.optimization_service import find_best_slot_for_meeting_request


def _clean_db():
    db: Session = SessionLocal()
    try:
        db.query(ParticipantAvailability).delete()
        db.query(MeetingRequest).delete()
        db.query(Lead).delete()
        db.commit()
    finally:
        db.close()


def test_find_best_slot_prefers_max_participants_and_earliest():
    Base.metadata.create_all(bind=engine)
    _clean_db()

    db: Session = SessionLocal()
    try:
        # Create two leads
        lead1 = Lead(
            name="Lead 1",
            phone="+111111111",
            email="l1@example.com",
            company="L1Co",
            timezone="UTC",
        )
        lead2 = Lead(
            name="Lead 2",
            phone="+222222222",
            email="l2@example.com",
            company="L2Co",
            timezone="UTC",
        )
        db.add_all([lead1, lead2])
        db.commit()
        db.refresh(lead1)
        db.refresh(lead2)

        # MeetingRequest: 30-minute slots, 9:00–11:00
        mr = MeetingRequest(
            owner_id="am-123",
            title="Group intro",
            duration_minutes=30,
            max_bookings=3,
            status=MeetingRequestStatus.ACTIVE,
            hard_constraints={
                "window_start": "2025-01-01T09:00:00",
                "window_end": "2025-01-01T11:00:00",
            },
            soft_constraints=None,
        )
        db.add(mr)
        db.commit()
        db.refresh(mr)

        # Availabilities:
        # Lead1: 9:00–11:00
        pa1 = ParticipantAvailability(
            meeting_request_id=mr.id,
            lead_id=lead1.id,
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 11, 0),
            state=AvailabilityState.CANDIDATE,
        )
        # Lead2: 10:00–11:00
        pa2 = ParticipantAvailability(
            meeting_request_id=mr.id,
            lead_id=lead2.id,
            start_time=datetime(2025, 1, 1, 10, 0),
            end_time=datetime(2025, 1, 1, 11, 0),
            state=AvailabilityState.CANDIDATE,
        )
        db.add_all([pa1, pa2])
        db.commit()

        # Now:
        # 09:00–09:30 -> only Lead1
        # 09:30–10:00 -> only Lead1
        # 10:00–10:30 -> Lead1 + Lead2
        # 10:30–11:00 -> Lead1 + Lead2
        best = find_best_slot_for_meeting_request(db, mr.id, min_participants=1)
        assert best is not None
        assert best.start_time == datetime(2025, 1, 1, 10, 0)
        assert best.end_time == datetime(2025, 1, 1, 10, 30)
        assert len(best.participant_lead_ids) == 2
        assert set(best.participant_lead_ids) == {lead1.id, lead2.id}

    finally:
        db.close()


def test_find_best_slot_uses_time_of_day_soft_constraint():
    Base.metadata.create_all(bind=engine)

    # Clean tables
    db: Session = SessionLocal()
    try:
        db.query(ParticipantAvailability).delete()
        db.query(MeetingRequest).delete()
        db.query(Lead).delete()
        db.commit()

        # Two leads
        lead1 = Lead(
            name="Lead 1",
            phone="+111111111",
            email="l1@example.com",
            company="L1Co",
            timezone="UTC",
        )
        lead2 = Lead(
            name="Lead 2",
            phone="+222222222",
            email="l2@example.com",
            company="L2Co",
            timezone="UTC",
        )
        db.add_all([lead1, lead2])
        db.commit()
        db.refresh(lead1)
        db.refresh(lead2)

        # MeetingRequest: 60-min slots, between 09:00–17:00
        # Soft constraint: prefer AFTERNOON
        mr = MeetingRequest(
            owner_id="am-123",
            title="Soft constrained meeting",
            duration_minutes=60,
            max_bookings=3,
            status=MeetingRequestStatus.ACTIVE,
            hard_constraints={
                "window_start": "2025-01-01T09:00:00",
                "window_end": "2025-01-01T17:00:00",
            },
            soft_constraints={
                "preferred_time_of_day": ["AFTERNOON"],
            },
        )
        db.add(mr)
        db.commit()
        db.refresh(mr)

        # Both leads are available 09:00–17:00 (so participants_count == 2 for all slots)
        pa1 = ParticipantAvailability(
            meeting_request_id=mr.id,
            lead_id=lead1.id,
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 17, 0),
            state=AvailabilityState.CANDIDATE,
        )
        pa2 = ParticipantAvailability(
            meeting_request_id=mr.id,
            lead_id=lead2.id,
            start_time=datetime(2025, 1, 1, 9, 0),
            end_time=datetime(2025, 1, 1, 17, 0),
            state=AvailabilityState.CANDIDATE,
        )
        db.add_all([pa1, pa2])
        db.commit()

        # Slots: 09–10, 10–11, 11–12, 12–13, 13–14, 14–15, 15–16, 16–17
        # All have 2 participants; soft constraint should prefer AFTERNOON (12–17).
        # With our scoring, earliest AFTERNOON slot (12:00–13:00) should win.
        best = find_best_slot_for_meeting_request(db, mr.id, min_participants=1)
        assert best is not None
        assert best.start_time == datetime(2025, 1, 1, 12, 0)
        assert best.end_time == datetime(2025, 1, 1, 13, 0)
    finally:
        db.close()
