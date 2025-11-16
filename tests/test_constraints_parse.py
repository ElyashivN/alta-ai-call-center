# tests/test_constraints_parse.py
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_constraints_parse_next_two_weeks_tue_thu_mornings():
    # Fix 'now' so the test is deterministic
    fixed_now = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    payload = {
        "instruction": "Try to book in the next two weeks, preferably Tue–Thu mornings",
        "timezone": "Asia/Jerusalem",
        "now": fixed_now.isoformat(),
    }

    resp = client.post("/constraints/parse", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    hc = data["hard_constraints"]
    sc = data["soft_constraints"]

    # Parse window_start and window_end back to datetimes
    ws = datetime.fromisoformat(hc["window_start"])
    we = datetime.fromisoformat(hc["window_end"])

    assert hc["timezone"] == "Asia/Jerusalem"

    # Expect exactly fixed_now → fixed_now + 14 days
    assert ws == fixed_now
    assert we == fixed_now + timedelta(days=14)

    # Soft constraints
    assert set(sc["preferred_days_of_week"]) == {"TUE", "WED", "THU"}
    assert sc["preferred_time_of_day"] == ["MORNING"]
