# app/models/participant_availability.py
from datetime import datetime
import enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Enum

from app.models.base import Base


class AvailabilityState(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    SELECTED = "SELECTED"
    DISCARDED = "DISCARDED"


class ParticipantAvailability(Base):
    """
    Availability window proposed by a single participant (lead)
    for a given MeetingRequest.

    Example: "I'm free Tuesday 10–13 and Thursday 15–17"
    turns into 2 ParticipantAvailability rows.
    """

    __tablename__ = "participant_availabilities"

    id = Column(Integer, primary_key=True, index=True)

    meeting_request_id = Column(
        Integer,
        ForeignKey("meeting_requests.id"),
        index=True,
        nullable=False,
    )

    lead_id = Column(
        Integer,
        ForeignKey("leads.id"),
        index=True,
        nullable=False,
    )

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Original wording or LLM-parsed description (optional)
    source_text = Column(String, nullable=True)

    # Score for later optimization (soft constraints)
    score = Column(Float, nullable=True)

    state = Column(
        Enum(AvailabilityState),
        default=AvailabilityState.CANDIDATE,
        nullable=False,
    )
