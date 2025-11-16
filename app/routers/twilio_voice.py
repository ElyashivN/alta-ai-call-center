# app/routers/twilio_voice.py
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse

from app.db.session import get_db
from app.models.call import Call
from app.models.meeting_request import MeetingRequest
from app.schemas.constraints import HardConstraints
from app.services.availability_service import record_availability_for_lead
from app.services.availability_nlp_service import parse_availability_from_transcript

router = APIRouter(prefix="/twilio", tags=["twilio-voice"])


def _windows_from_gather_input(
    *,
    hard_constraints: HardConstraints,
    duration_minutes: int,
    digits: Optional[str],
) -> List[Tuple[datetime, datetime]]:
    """
    Very simple digits-based heuristic:

    - We split the hard-constraint window into fixed-length slots.
    - Digit '1' → first slot, '2' → second, etc.
    - Clamp to the last slot if N is too large.
    """
    slot_len = timedelta(minutes=duration_minutes)
    window_start = hard_constraints.window_start
    window_end = hard_constraints.window_end

    total_slots = max(1, int((window_end - window_start) / slot_len))

    idx = 1
    if digits and digits[0].isdigit():
        idx = max(1, int(digits[0]))
    if idx > total_slots:
        idx = total_slots

    start = window_start + (idx - 1) * slot_len
    end = start + slot_len
    if end > window_end:
        end = window_end

    return [(start, end)]


@router.post("/voice", response_class=Response)
def twilio_voice(
    CallSid: str = Form(...),
):
    """
    Initial Twilio webhook when an outbound call is answered.

    We greet the lead and start a <Gather> that will POST speech/DTMF
    to /twilio/voice/gather.
    """
    vr = VoiceResponse()

    gather = vr.gather(
        input="speech dtmf",
        action="/twilio/voice/gather",
        method="POST",
        timeout=6,
        num_digits=1,
    )
    gather.say(
        "Hi, this is Alta, calling to schedule your meeting. "
        "Please say one time that works for you in the requested window, "
        "or press 1 for the earliest available time, "
        "2 for a later time in the window, and then wait."
    )

    vr.say(
        "If I did not get your availability, we will follow up by message. Goodbye."
    )

    return Response(content=str(vr), media_type="application/xml")


@router.post("/voice/gather", response_class=Response)
def twilio_voice_gather(
    db: Session = Depends(get_db),
    CallSid: str = Form(...),
    SpeechResult: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None),
):
    """
    Twilio <Gather> callback:

    - Look up Call by provider_call_id (CallSid).
    - Use its lead + meeting_request.
    - Create ParticipantAvailability rows.
    - For speech input we call OpenAI via parse_availability_from_transcript.
      For digits-only we fall back to a simple slot heuristic.
    """
    user_input = (SpeechResult or Digits or "").strip()
    vr = VoiceResponse()

    # Look up the Call row
    call = db.query(Call).filter(Call.provider_call_id == CallSid).first()
    if not call:
        vr.say(
            "Thanks. I could not match this call, but we will follow up manually. Goodbye."
        )
        return Response(content=str(vr), media_type="application/xml")

    if not call.lead_id or not call.meeting_request_id:
        vr.say(
            "Thanks. I could not find a matching meeting for this call, "
            "but we will follow up. Goodbye."
        )
        return Response(content=str(vr), media_type="application/xml")

    # Load meeting request + hard constraints
    mr: Optional[MeetingRequest] = db.get(MeetingRequest, call.meeting_request_id)
    if not mr or not mr.hard_constraints:
        vr.say(
            "Thanks. The meeting request configuration is missing, "
            "so we will follow up later. Goodbye."
        )
        return Response(content=str(vr), media_type="application/xml")

    hc = HardConstraints.model_validate(mr.hard_constraints)

    # --- NEW: speech → LLM parser, digits → heuristic ---
    if SpeechResult and SpeechResult.strip():
        windows = parse_availability_from_transcript(
            transcript=SpeechResult,
            hard_constraints=hc,
            duration_minutes=mr.duration_minutes,
        )
    else:
        windows = _windows_from_gather_input(
            hard_constraints=hc,
            duration_minutes=mr.duration_minutes,
            digits=Digits,
        )

    # If for any reason we got nothing, fall back to the first slot
    if not windows:
        windows = _windows_from_gather_input(
            hard_constraints=hc,
            duration_minutes=mr.duration_minutes,
            digits="1",
        )

    # Persist as ParticipantAvailability rows
    record_availability_for_lead(
        db=db,
        meeting_request_id=mr.id,
        lead_id=call.lead_id,
        windows=windows,
        source_text=user_input,
    )

    # Simple confirmation sentence using local timezone
    tz = ZoneInfo(hc.timezone)
    start_local = windows[0][0].astimezone(tz)
    friendly = start_local.strftime("%A %B %d at %H:%M")

    vr.say(
        f"Great. I have recorded that you are available on {friendly}. "
        "We will confirm the final meeting time shortly. Goodbye."
    )

    return Response(content=str(vr), media_type="application/xml")
