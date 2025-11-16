from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    meeting_request_id = Column(
        Integer,
        ForeignKey("meeting_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    meeting_slot_id = Column(
        Integer,
        ForeignKey("meeting_slots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    call_id = Column(
        Integer,
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    scheduled_start_time = Column(DateTime, nullable=False)
    scheduled_end_time = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lead = relationship("Lead", backref="meetings")
    meeting_request = relationship("MeetingRequest", backref="meetings")
    meeting_slot = relationship("MeetingSlot", backref="meeting")
    call = relationship("Call", backref="meeting")


