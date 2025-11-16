# tests/test_availability_nlp_service.py
from datetime import datetime, timedelta, timezone

from app.schemas.constraints import HardConstraints
from app.services.availability_nlp_service import parse_availability_from_speech


def test_parse_availability_from_speech_uses_fallback_without_openai():
    hc = HardConstraints(
        window_start=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        window_end=datetime(2025, 1, 1, 17, 0, tzinfo=timezone.utc),
        timezone="UTC",
    )

    windows = parse_availability_from_speech(
        instruction="Tomorrow morning works for me",
        hard_constraints=hc,
        duration_minutes=60,
    )

    assert len(windows) == 1
    start, end = windows[0]
    # fallback puts "morning" at the first slot
    assert start == hc.window_start
    assert end == hc.window_start + timedelta(minutes=60)
