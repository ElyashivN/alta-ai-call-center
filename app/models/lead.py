from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    timezone = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
