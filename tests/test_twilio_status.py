# tests/test_twilio_status.py
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, engine
from app.models import Base, Call, Lead


client = TestClient(app)


def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_twilio_status_updates_call():
    _clean_db()
    db = SessionLocal()
    try:
        lead = Lead(
            name="Lead Status",
            phone="+111111111",
            email="ls@example.com",
            company="StatusCo",
            timezone="UTC",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        call = Call(
            lead_id=lead.id,
            provider_call_id="CA_TEST_STATUS",
            status="initiated",
            direction="outbound",
        )
        db.add(call)
        db.commit()
        db.refresh(call)
    finally:
        db.close()

    data = {
        "CallSid": "CA_TEST_STATUS",
        "CallStatus": "completed",
        "From": "+111111111",
        "To": "+222222222",
    }
    resp = client.post("/twilio/status", data=data)
    assert resp.status_code == 200
    assert "<Response" in resp.text

    db2 = SessionLocal()
    try:
        updated = db2.query(Call).filter_by(provider_call_id="CA_TEST_STATUS").first()
        assert updated is not None
        assert updated.status == "completed"
    finally:
        db2.close()
