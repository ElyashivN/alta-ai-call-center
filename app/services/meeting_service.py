# app/services/meeting_service.py
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.participant_availability import (
    ParticipantAvailability,
    AvailabilityState,
)
from app.services.optimization_service import (
    find_best_slot_for_meeting_request,
    CandidateSlot,
)


@dataclass
class ConfirmedMeetingResult:
    meeting: Meeting
    slot: CandidateSlot


def confirm_best_slot_for_meeting_request(
    db: Session,
    meeting_request_id: int,
    min_participants: int = 1,
) -> Optional[ConfirmedMeetingResult]:
    """
    Use the optimizer to pick the best slot, then:
      - Create a Meeting (using your existing Meeting model)
      - Mark the used ParticipantAvailability rows as SELECTED

    Returns:
      - ConfirmedMeetingResult on success
      - None if no suitable slot exists
    """
    best = find_best_slot_for_meeting_request(
        db,
        meeting_request_id=meeting_request_id,
        min_participants=min_participants,
    )

    if best is None:
        return None

    if not best.participant_lead_ids:
        return None

    # Pick a primary lead deterministically (smallest ID)
    primary_lead_id = sorted(best.participant_lead_ids)[0]

    meeting = Meeting(
        lead_id=primary_lead_id,
        meeting_request_id=meeting_request_id,
        meeting_slot_id=None,
        call_id=None,
        scheduled_start_time=best.start_time,
        scheduled_end_time=best.end_time,
    )
    db.add(meeting)

    # Mark availabilities for the primary lead that cover this slot as SELECTED
    avails = (
        db.query(ParticipantAvailability)
        .filter(
            ParticipantAvailability.meeting_request_id == meeting_request_id,
            ParticipantAvailability.lead_id == primary_lead_id,
            ParticipantAvailability.state == AvailabilityState.CANDIDATE,
        )
        .all()
    )

    for pa in avails:
        if best.start_time >= pa.start_time and best.end_time <= pa.end_time:
            pa.state = AvailabilityState.SELECTED

    db.commit()
    db.refresh(meeting)

    return ConfirmedMeetingResult(meeting=meeting, slot=best)
