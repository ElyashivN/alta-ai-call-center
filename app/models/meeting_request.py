# app/models/meeting_request.py
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class MeetingRequestStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MeetingRequest(Base):
    __tablename__ = "meeting_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Who owns / created this meeting request (e.g., AM id)
    owner_id = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False)

    # Duration in minutes (e.g. 30)
    duration_minutes = Column(Integer, nullable=False)

    # Optional coarse window (old field, still used by tests)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)

    max_bookings = Column(Integer, nullable=False, default=0)

    # Store status as a simple string; MeetingRequestStatus is still used in Python
    status = Column(
        String(32),
        nullable=False,
        default=MeetingRequestStatus.ACTIVE.value,
    )

    # New: JSON constraints (non-null, with default {})
    hard_constraints = Column(JSON, nullable=False, default=dict)
    soft_constraints = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)