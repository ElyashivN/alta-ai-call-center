# app/services/availability_service.py
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.participant_availability import (
    ParticipantAvailability,
    AvailabilityState,
)


def record_availability_for_lead(
    db: Session,
    *,
    meeting_request_id: int,
    lead_id: int,
    windows: Iterable[Tuple[datetime, datetime]],
    source_text: Optional[str] = None,
) -> List[ParticipantAvailability]:
    """
    Record availability windows for a given lead & meeting request.

    Behavior:
    - Removes existing CANDIDATE windows for that (meeting_request_id, lead_id)
      so the new set "replaces" the old one.
    - Inserts new rows for each window in `windows`.

    Returns the list of newly created ParticipantAvailability records.
    """

    # Remove existing candidate windows for idempotency
    db.query(ParticipantAvailability).filter(
        ParticipantAvailability.meeting_request_id == meeting_request_id,
        ParticipantAvailability.lead_id == lead_id,
        ParticipantAvailability.state == AvailabilityState.CANDIDATE,
    ).delete()
    db.commit()

    created: List[ParticipantAvailability] = []

    for start, end in windows:
        if end <= start:
            raise ValueError("end_time must be after start_time")

        pa = ParticipantAvailability(
            meeting_request_id=meeting_request_id,
            lead_id=lead_id,
            start_time=start,
            end_time=end,
            source_text=source_text,
            state=AvailabilityState.CANDIDATE,
            score=None,
        )
        db.add(pa)
        created.append(pa)

    db.commit()
    for pa in created:
        db.refresh(pa)

    return created
