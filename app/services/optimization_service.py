# app/services/optimization_service.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.meeting_request import MeetingRequest
from app.models.participant_availability import (
    ParticipantAvailability,
    AvailabilityState,
)

DAY_CODES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _time_of_day_label(dt: datetime) -> str:
    """
    Simple time-of-day bucketing.

    MORNING:    06:00–12:00
    AFTERNOON:  12:00–17:00
    EVENING:    17:00–22:00
    OFF_HOURS:  everything else
    """
    h = dt.hour
    if 6 <= h < 12:
        return "MORNING"
    if 12 <= h < 17:
        return "AFTERNOON"
    if 17 <= h < 22:
        return "EVENING"
    return "OFF_HOURS"


def _compute_slot_score(
    *,
    slot_start: datetime,
    participants_count: int,
    soft_constraints: Dict,
) -> float:
    """
    Score = participants * 100
            + 10 if time-of-day matches preference
            + 5  if day-of-week matches preference

    This keeps participants as the dominant factor,
    and uses soft constraints to break ties between equally good overlaps.
    """
    base = participants_count * 100
    bonus = 0

    sc = soft_constraints or {}

    # Normalize preferences to uppercase lists
    tod_prefs = sc.get("preferred_time_of_day") or []
    if isinstance(tod_prefs, str):
        tod_prefs = [tod_prefs]
    tod_prefs = [s.upper() for s in tod_prefs]

    dow_prefs = sc.get("preferred_days_of_week") or []
    if isinstance(dow_prefs, str):
        dow_prefs = [dow_prefs]
    dow_prefs = [s.upper() for s in dow_prefs]

    # Time-of-day bonus
    tod_label = _time_of_day_label(slot_start)
    if tod_label in tod_prefs:
        bonus += 10

    # Day-of-week bonus
    day_code = DAY_CODES[slot_start.weekday()]  # 0=MON,...,6=SUN
    if day_code in dow_prefs:
        bonus += 5

    return float(base + bonus)


@dataclass
class CandidateSlot:
    start_time: datetime
    end_time: datetime
    participant_lead_ids: List[int]
    score: float


def find_best_slot_for_meeting_request(
    db: Session,
    meeting_request_id: int,
    min_participants: int = 1,
) -> Optional[CandidateSlot]:
    """
    Given:
      - a MeetingRequest (with duration + window_start/window_end in hard_constraints)
      - all ParticipantAvailability rows (CANDIDATE) for that meeting_request_id

    Returns:
      - the best CandidateSlot (max participants, earliest in case of tie)
      - or None if no suitable slot exists

    Strategy for MVP:
      - Build a time grid in [window_start, window_end) with step = duration_minutes
      - For each slot, count how many leads can attend (slot fully inside at least
        one of their availability windows)
      - Score = number of participants
      - Pick highest score; tie-breaker: earliest start_time
    """
    mr = db.query(MeetingRequest).filter_by(id=meeting_request_id).first()
    if not mr:
        raise ValueError("MeetingRequest not found")

    if not mr.duration_minutes or mr.duration_minutes <= 0:
        raise ValueError("MeetingRequest.duration_minutes must be positive")

    hard_constraints = mr.hard_constraints or {}
    try:
        window_start = datetime.fromisoformat(hard_constraints["window_start"])
        window_end = datetime.fromisoformat(hard_constraints["window_end"])
    except Exception as e:
        raise ValueError(
            "MeetingRequest.hard_constraints must contain "
            "'window_start' and 'window_end' in ISO format"
        ) from e

    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    soft_constraints = mr.soft_constraints or {}

    # Fetch all candidate availabilities
    avails: List[ParticipantAvailability] = (
        db.query(ParticipantAvailability)
        .filter(
            ParticipantAvailability.meeting_request_id == meeting_request_id,
            ParticipantAvailability.state == AvailabilityState.CANDIDATE,
        )
        .all()
    )

    if not avails:
        # No availabilities recorded yet
        return None

    duration = timedelta(minutes=mr.duration_minutes)
    step = duration  # simple choice for MVP,might change latera

    # Group availabilities per lead for more efficient checks
    avails_by_lead: Dict[int, List[ParticipantAvailability]] = {}
    for pa in avails:
        avails_by_lead.setdefault(pa.lead_id, []).append(pa)

    best: Optional[CandidateSlot] = None

    t = window_start
    while t + duration <= window_end:
        slot_start = t
        slot_end = t + duration
        participant_ids: List[int] = []

        # For each lead, check if this slot fits inside any of their windows
        for lead_id, lead_avails in avails_by_lead.items():
            for pa in lead_avails:
                # slot must be fully contained in the availability window
                if slot_start >= pa.start_time and slot_end <= pa.end_time:
                    participant_ids.append(lead_id)
                    break

        if len(participant_ids) >= min_participants:
            score = _compute_slot_score(
                slot_start=slot_start,
                participants_count=len(participant_ids),
                soft_constraints=soft_constraints,
            )
            candidate = CandidateSlot(
                start_time=slot_start,
                end_time=slot_end,
                participant_lead_ids=participant_ids,
                score=score,
            )

            if best is None:
                best = candidate
            else:
                if candidate.score > best.score or (
                    candidate.score == best.score
                    and candidate.start_time < best.start_time
                ):
                    best = candidate

        t += step

    return best
