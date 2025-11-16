# app/models/call.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # NEW: link each call to an optional MeetingRequest
    meeting_request_id = Column(
        Integer,
        ForeignKey("meeting_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider_call_id = Column(String(64), unique=True, index=True, nullable=True)
    direction = Column(String(16), nullable=False, default="outbound")
    status = Column(String(32), nullable=False, default="initiated")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    lead = relationship("Lead", backref="calls")
    meeting_request = relationship("MeetingRequest", backref="calls")
