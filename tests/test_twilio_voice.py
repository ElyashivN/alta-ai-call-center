# tests/test_twilio_voice.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_twilio_voice_webhook_basic():
    # Simulate a Twilio POST with form-encoded data
    payload = {
        "CallSid": "CA1234567890abcdef",
        "From": "+15551234567",
        "To": "+15557654321",
    }

    response = client.post("/twilio/voice", data=payload)

    assert response.status_code == 200
    # XML / TwiML content type
    assert response.headers["content-type"].startswith("application/xml")

    body = response.text
    assert "<Response>" in body
    assert "<Say>" in body
    assert "</Response>" in body
