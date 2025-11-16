# app/routers/meeting_requests.py
from app.services.optimization_service import find_best_slot_for_meeting_request
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.services.meeting_service import confirm_best_slot_for_meeting_request
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.meeting_request import MeetingRequest
from app.models.meeting_slot import MeetingSlot
from app.services.scheduling_service import create_meeting_request_and_slots
from app.services.availability_service import record_availability_for_lead

router = APIRouter()


class SimpleMeetingRequestCreate(BaseModel):
    owner_id: str
    title: str
    duration_minutes: int
    window_start: datetime
    window_end: datetime
    max_bookings: int = 0

    @field_validator("duration_minutes")
    def validate_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("duration_minutes must be positive")
        return v


class AvailabilityWindow(BaseModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def check_end_after_start(self) -> "AvailabilityWindow":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityPayload(BaseModel):
    lead_id: int
    windows: List[AvailabilityWindow]
    source_text: Optional[str] = None


@router.post("/simple")
def create_simple_meeting_request(
        payload: SimpleMeetingRequestCreate,
        db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create a meeting request with a simple time window and auto-generated slots.

    This is the "MVP" entry point:
    - Define a time window (start/end)
    - Define duration (minutes)
    - We generate back-to-back slots inside that window
    """
    try:
        meeting_request, slots = create_meeting_request_and_slots(
            db,
            owner_id=payload.owner_id,
            title=payload.title,
            duration_minutes=payload.duration_minutes,
            window_start=payload.window_start,
            window_end=payload.window_end,
            max_bookings=payload.max_bookings,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "meeting_request": {
            "id": meeting_request.id,
            "owner_id": meeting_request.owner_id,
            "title": meeting_request.title,
            "duration_minutes": meeting_request.duration_minutes,
            "max_bookings": meeting_request.max_bookings,
            "status": meeting_request.status,
            "hard_constraints": meeting_request.hard_constraints,
        },
        "slots": [
            {
                "id": s.id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "state": s.state,
            }
            for s in slots
        ],
    }


@router.get("/{meeting_request_id}")
def get_meeting_request(
        meeting_request_id: int,
        db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Fetch a meeting request and its slots.
    """
    mr = db.query(MeetingRequest).filter_by(id=meeting_request_id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="MeetingRequest not found")

    slots = (
        db.query(MeetingSlot)
            .filter_by(meeting_request_id=meeting_request_id)
            .order_by(MeetingSlot.start_time.asc())
            .all()
    )

    return {
        "meeting_request": {
            "id": mr.id,
            "owner_id": mr.owner_id,
            "title": mr.title,
            "duration_minutes": mr.duration_minutes,
            "max_bookings": mr.max_bookings,
            "status": mr.status,
            "hard_constraints": mr.hard_constraints,
        },
        "slots": [
            {
                "id": s.id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "state": s.state,
            }
            for s in slots
        ],
    }


@router.post("/{meeting_request_id}/availability")
def submit_availability_for_meeting(
        meeting_request_id: int,
        payload: AvailabilityPayload,
        db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Simulate what the AI caller will do after a call:

    - For a given meeting_request_id and lead_id
    - Accepts multiple time windows
    - Stores them as ParticipantAvailability rows

    This is the "collection phase" for multi-person scheduling.
    """
    mr = db.query(MeetingRequest).filter_by(id=meeting_request_id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="MeetingRequest not found")

    if not payload.windows:
        raise HTTPException(status_code=400, detail="At least one window is required")

    windows = [(w.start_time, w.end_time) for w in payload.windows]

    try:
        created = record_availability_for_lead(
            db,
            meeting_request_id=meeting_request_id,
            lead_id=payload.lead_id,
            windows=windows,
            source_text=payload.source_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "meeting_request_id": meeting_request_id,
        "lead_id": payload.lead_id,
        "availabilities": [
            {
                "id": pa.id,
                "start_time": pa.start_time.isoformat(),
                "end_time": pa.end_time.isoformat(),
                "state": pa.state,
                "score": pa.score,
            }
            for pa in created
        ],
    }


@router.get("/{meeting_request_id}/suggested-slot")
def get_suggested_slot(
        meeting_request_id: int,
        db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compute the best concrete slot for this meeting request,
    based on all ParticipantAvailability rows.

    Note: This does NOT yet create a Meeting; it only suggests a slot.
    """
    mr = db.query(MeetingRequest).filter_by(id=meeting_request_id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="MeetingRequest not found")

    try:
        best = find_best_slot_for_meeting_request(db, meeting_request_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if best is None:
        # No suitable slot found (e.g. no availabilities yet)
        return {
            "meeting_request_id": meeting_request_id,
            "slot": None,
        }

    return {
        "meeting_request_id": meeting_request_id,
        "slot": {
            "start_time": best.start_time.isoformat(),
            "end_time": best.end_time.isoformat(),
            "participant_lead_ids": best.participant_lead_ids,
            "score": best.score,
        },
    }

@router.post("/{meeting_request_id}/confirm-best-slot")
def confirm_best_slot(
    meeting_request_id: int,
    min_participants: int = 1,
    db: Session = Depends(get_db),
):
    """
    Confirm (book) the best slot for this MeetingRequest:

    - Uses all ParticipantAvailability rows
    - Chooses the best overlap using the optimizer
    - Creates a Meeting (1:1, using your existing Meeting model)
    - Marks the used availability windows for that lead as SELECTED
    """
    mr = db.query(MeetingRequest).filter_by(id=meeting_request_id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="MeetingRequest not found")

    try:
        result = confirm_best_slot_for_meeting_request(
            db,
            meeting_request_id=meeting_request_id,
            min_participants=min_participants,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result is None:
        # No slot is possible given current availabilities
        raise HTTPException(
            status_code=409,
            detail="No suitable slot found to confirm",
        )

    meeting = result.meeting
    slot = result.slot

    return {
        "meeting_request_id": meeting_request_id,
        "meeting": {
            "id": meeting.id,
            "lead_id": meeting.lead_id,
            "scheduled_start_time": meeting.scheduled_start_time.isoformat(),
            "scheduled_end_time": meeting.scheduled_end_time.isoformat(),
            "meeting_request_id": meeting.meeting_request_id,
            "meeting_slot_id": meeting.meeting_slot_id,
            "call_id": meeting.call_id,
        },
        "slot": {
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "participant_lead_ids": slot.participant_lead_ids,
            "score": slot.score,
        },
    }
