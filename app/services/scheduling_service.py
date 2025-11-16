# app/services/scheduling_service.py
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from sqlalchemy.orm import Session

from app.models.meeting_request import MeetingRequest, MeetingRequestStatus
from app.models.meeting_slot import MeetingSlot, MeetingSlotState


def create_meeting_request_and_slots(
    db: Session,
    *,
    owner_id: str,
    title: str,
    duration_minutes: int,
    window_start: datetime,
    window_end: datetime,
    max_bookings: int = 0,
) -> Tuple[MeetingRequest, List[MeetingSlot]]:
    """
    Create a MeetingRequest and generate time slots inside [window_start, window_end).

    For now:
    - We step by `duration_minutes`
    - Each slot is AVAILABLE
    - We don't yet enforce max_bookings, but it's stored for later logic
    """
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    hard_constraints = {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }

    meeting_request = MeetingRequest(
        owner_id=owner_id,
        title=title,
        duration_minutes=duration_minutes,
        max_bookings=max_bookings,
        status=MeetingRequestStatus.ACTIVE,
        hard_constraints=hard_constraints,
        soft_constraints=None,
    )

    db.add(meeting_request)
    db.commit()
    db.refresh(meeting_request)

    # Generate slots
    slots: List[MeetingSlot] = []
    current = window_start
    delta = timedelta(minutes=duration_minutes)

    while current + delta <= window_end:
        slot = MeetingSlot(
            meeting_request_id=meeting_request.id,
            start_time=current,
            end_time=current + delta,
            state=MeetingSlotState.AVAILABLE,
            score=None,
        )
        db.add(slot)
        slots.append(slot)
        current += delta

    db.commit()
    for slot in slots:
        db.refresh(slot)

    return meeting_request, slots
