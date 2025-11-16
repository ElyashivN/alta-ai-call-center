from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class MeetingSlotState:
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"
    EXPIRED = "EXPIRED"


class MeetingSlot(Base):
    __tablename__ = "meeting_slots"

    id = Column(Integer, primary_key=True, index=True)

    meeting_request_id = Column(
        Integer,
        ForeignKey("meeting_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    state = Column(String(32), nullable=False, default=MeetingSlotState.AVAILABLE)

    # Higher score = more preferred by soft constraints
    score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    meeting_request = relationship("MeetingRequest", backref="slots")
