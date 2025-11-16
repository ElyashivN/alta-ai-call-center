# tests/test_db_basic.py
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models import Base, Lead


def test_db_can_create_schema():
    # Ensure metadata can create tables
    Base.metadata.create_all(bind=engine)

    # Simple connectivity test
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_create_and_read_lead():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Ensure a clean slate for this test to avoid UNIQUE constraint conflicts
        db.query(Lead).delete()
        db.commit()

        lead = Lead(
            name="Test Lead",
            phone="+123456789",
            email="test@example.com",
            company="TestCo",
            timezone="UTC",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        assert lead.id is not None

        # fetch back
        fetched = db.query(Lead).filter_by(phone="+123456789").first()
        assert fetched is not None
        assert fetched.name == "Test Lead"
    finally:
        db.close()
