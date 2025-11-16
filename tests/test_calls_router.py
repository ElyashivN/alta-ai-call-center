# tests/test_calls_router.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import engine, SessionLocal
from app.models import Base, Lead, Call
from app.services.twilio_client import get_twilio_client


class FakeTwilioClient:
    def __init__(self):
        self.called_numbers = []

    def create_outbound_call(self, to_number: str) -> str:
        self.called_numbers.append(to_number)
        return "CA_FAKE_ROUTER_SID"


def override_twilio_client():
    # A new fake per request is fine for our tests
    return FakeTwilioClient()


# Override the real Twilio dependency with our fake
app.dependency_overrides[get_twilio_client] = override_twilio_client

client = TestClient(app)


def test_create_test_call_endpoint_creates_lead_and_call():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Clean tables
        db.query(Call).delete()
        db.query(Lead).delete()
        db.commit()
    finally:
        db.close()

    payload = {
        "phone": "+22222222222",
        "name": "Router Test Lead",
    }

    response = client.post("/calls/test", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "call_id" in data
    assert "provider_call_id" in data
    assert "lead_id" in data
    assert data["provider_call_id"] == "CA_FAKE_ROUTER_SID"

    # Verify DB state
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(phone="+22222222222").first()
        assert lead is not None
        call = db.query(Call).filter_by(id=data["call_id"]).first()
        assert call is not None
        assert call.lead_id == lead.id
    finally:
        db.close()
