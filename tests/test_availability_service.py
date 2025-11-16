# tests/test_availability_service.py
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models import Base, Lead, MeetingRequest
from app.models.meeting_request import MeetingRequestStatus
from app.models.participant_availability import ParticipantAvailability
from app.services.availability_service import record_availability_for_lead


def test_record_availability_for_lead_replaces_existing():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Clean relevant tables
        db.query(ParticipantAvailability).delete()
        db.query(MeetingRequest).delete()
        db.query(Lead).delete()
        db.commit()

        # Create a lead
        lead = Lead(
            name="Participant 1",
            phone="+111111111",
            email="p1@example.com",
            company="P1Co",
            timezone="UTC",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Create a minimal MeetingRequest
        mr = MeetingRequest(
            owner_id="am-123",
            title="Group session",
            duration_minutes=30,
            max_bookings=0,
            status=MeetingRequestStatus.ACTIVE,
            hard_constraints={},
            soft_constraints=None,
        )
        db.add(mr)
        db.commit()
        db.refresh(mr)

        # First set of windows
        windows1 = [
            (
                datetime(2025, 1, 1, 9, 0),
                datetime(2025, 1, 1, 10, 0),
            )
        ]
        created1 = record_availability_for_lead(
            db,
            meeting_request_id=mr.id,
            lead_id=lead.id,
            windows=windows1,
            source_text="first pass",
        )
        assert len(created1) == 1

        # Second set of windows should replace the first
        windows2 = [
            (
                datetime(2025, 1, 2, 9, 0),
                datetime(2025, 1, 2, 10, 0),
            ),
            (
                datetime(2025, 1, 2, 14, 0),
                datetime(2025, 1, 2, 15, 0),
            ),
        ]
        created2 = record_availability_for_lead(
            db,
            meeting_request_id=mr.id,
            lead_id=lead.id,
            windows=windows2,
            source_text="second pass",
        )
        assert len(created2) == 2

        # Only 2 rows should exist for that (meeting_request, lead)
        count = (
            db.query(ParticipantAvailability)
            .filter_by(meeting_request_id=mr.id, lead_id=lead.id)
            .count()
        )
        assert count == 2
    finally:
        db.close()
